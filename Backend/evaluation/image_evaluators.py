"""Real image-classification and YOLO adapters, with no weight downloads."""
import math
from pathlib import Path

from .constants import IMAGE_EXTENSIONS, MAX_SAMPLES, MAX_ANNOTATION_LINE_CHARS
from .evaluators import _checkpoint, classification_metrics


def image_samples(dataset, classes, split='test'):
    root = Path(dataset)
    if not root.is_dir():
        raise ValueError('图像分类需要已登记、解包后的标注目录。')
    base = root / split
    if not base.is_dir():
        base = root / 'val' if (root / 'val').is_dir() else root
    unknown = [path.name for path in base.iterdir() if path.is_dir() and not path.name.startswith('.') and path.name not in classes]
    if unknown:
        raise ValueError('测试目录包含模型未登记的类别，未静默丢弃这些样本。')
    samples = []
    for label, name in enumerate(classes):
        directory = base / str(name)
        if directory.is_dir():
            for image in sorted(directory.rglob('*')):
                if image.is_file() and image.suffix.lower() in IMAGE_EXTENSIONS:
                    samples.append((image, label))
    if not samples or len(samples) > MAX_SAMPLES:
        raise ValueError('没有与模型真实类别匹配的测试图像，或样本数超过限制。')
    return samples


def evaluate_clip(model_path, dataset, params, classes):
    import torch
    from PIL import Image
    from torchvision import transforms
    classes = [str(name) for name in classes]
    if not classes or len(set(classes)) != len(classes):
        raise ValueError('CLIP 分类产物必须包含真实且唯一的类别。')
    samples = image_samples(dataset, classes, params.get('split', 'test'))
    size = params.get('image_size', 224)
    zero_shot = False
    if Path(model_path).suffix.lower() == '.torchscript':
        model = torch.jit.load(str(model_path), map_location='cpu').eval()
        transform = transforms.Compose([transforms.Resize((size, size)), transforms.ToTensor()])
        classify = model
    else:
        checkpoint = _checkpoint(model_path)
        if checkpoint.get('class_names') and list(checkpoint['class_names']) != classes:
            raise ValueError('CLIP 产物类别与训练记录不一致。')
        encoder = checkpoint.get('encoder_type')
        mode = checkpoint.get('mode')
        if encoder in ('fallback_manifest', 'json_manifest') or not any(
                key in checkpoint for key in ('state_dict', 'classifier_state_dict')):
            raise ValueError('此 CLIP 产物只有说明清单，没有可推理权重；请完成真实编码器训练或导出。')
        if mode == 'zero_shot':
            try:
                import clip
                from clip.model import build_model
            except ImportError:
                raise ValueError('当前环境缺少 CLIP 适配器，不能把清单当作模型评分。') from None
            model = build_model(checkpoint['state_dict']).float().cpu().eval()
            resolution = int(model.visual.input_resolution)
            transform = transforms.Compose([transforms.Resize(resolution), transforms.CenterCrop(resolution),
                transforms.ToTensor(), transforms.Normalize((.48145466, .4578275, .40821073), (.26862954, .26130258, .27577711))])
            texts = clip.tokenize(checkpoint.get('text_prompts') or [f'a photo of a {name}' for name in classes])
            classify = lambda images: model(images, texts)[0]
            zero_shot = True
        elif mode == 'finetune':
            base_file = (params.get('base_encoder_files') or {}).get(encoder)
            if not base_file:
                raise ValueError('线性探针产物只保存分类头，缺少匹配的真实基础编码器，未下载或生成替代权重。')
            head = torch.nn.Linear(int(checkpoint['feature_dim']), len(classes))
            head.load_state_dict(checkpoint['classifier_state_dict'], strict=True)
            head.eval()
            if encoder == 'resnet18_fallback':
                from torchvision.models import resnet18
                backbone = resnet18(weights=None)
                backbone.load_state_dict(_checkpoint(base_file), strict=True)
                backbone.fc = torch.nn.Identity()
                backbone.eval()
                classify = lambda images: head(backbone(images))
                transform = transforms.Compose([transforms.Resize(256), transforms.CenterCrop(224), transforms.ToTensor(),
                    transforms.Normalize((.485, .456, .406), (.229, .224, .225))])
            elif encoder == 'clip':
                from clip.model import build_model
                if params.get('base_encoder_model') != checkpoint.get('base_model'):
                    raise ValueError('CLIP 基础编码器与训练记录不匹配。')
                base = torch.jit.load(base_file, map_location='cpu')
                backbone = build_model(base.state_dict()).float().cpu().eval()
                resolution = int(backbone.visual.input_resolution)
                classify = lambda images: head(backbone.encode_image(images).float())
                transform = transforms.Compose([transforms.Resize(resolution), transforms.CenterCrop(resolution), transforms.ToTensor(),
                    transforms.Normalize((.48145466, .4578275, .40821073), (.26862954, .26130258, .27577711))])
            else:
                raise ValueError('CLIP 线性探针编码器类型不可用。')
        else:
            raise ValueError('CLIP 产物的推理模式不受支持。')
    expected, predicted, probabilities = [], [], []
    with torch.inference_mode():
        for path, label in samples:
            with Image.open(path) as image:
                tensor = transform(image.convert('RGB')).unsqueeze(0)
            logits = classify(tensor)
            if tuple(logits.shape) != (1, len(classes)) or not torch.isfinite(logits).all():
                raise ValueError('图像模型返回无效 logits 或类别数不一致。')
            probabilities.extend(logits.softmax(dim=1).tolist())
            predicted.extend(logits.argmax(dim=1).tolist())
            expected.append(label)
    result = classification_metrics(expected, predicted, probabilities, classes)
    result['mode'] = 'zero_shot' if zero_shot else 'classification'
    return result


def _yolo_data(dataset, params, classes):
    import yaml
    root = Path(dataset)
    if not root.is_dir():
        raise ValueError('YOLO 评测需要已登记的完整 images/labels/data.yaml 目录。')
    filename = next((root / name for name in ('data.yaml', 'dataset.yaml', 'data.yml') if (root / name).is_file()), None)
    if not filename:
        raise ValueError('YOLO 数据集中缺少 data.yaml。')
    data = yaml.safe_load(filename.read_text(encoding='utf-8'))
    if not isinstance(data, dict):
        raise ValueError('YOLO 数据配置无效。')
    names = data.get('names') or classes
    if isinstance(names, dict):
        names = [names[key] for key in sorted(names, key=lambda value: int(value))]
    if not isinstance(names, list) or not names or classes and list(names) != list(classes):
        raise ValueError('数据集类别与模型的已登记类别不一致。')
    split = params.get('split', 'test')
    split_path = data.get(split)
    if not isinstance(split_path, str) or not split_path or '://' in split_path:
        raise ValueError('请选择数据集中真实存在的 test/val 划分。')
    original_root = Path(str(data.get('path', '')))
    selected = Path(split_path)
    if selected.is_absolute():
        try:
            selected = selected.relative_to(original_root)
        except ValueError:
            raise ValueError('YOLO 划分不能引用数据集之外的路径。') from None
    selected = (root / selected).resolve()
    if not selected.is_relative_to(root.resolve()) or not selected.is_dir():
        raise ValueError('YOLO 划分必须位于登记的数据集目录内。')
    images = [path for path in selected.rglob('*') if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS]
    if not images or len(images) > MAX_SAMPLES:
        raise ValueError('YOLO 测试图像为空或超过限制。')
    objects = 0
    for image in images:
        from PIL import Image
        with Image.open(image) as decoded:
            decoded.verify()
        parts = list(image.relative_to(root).parts)
        if 'images' not in parts:
            raise ValueError('YOLO 图像须采用 images/labels 对应布局。')
        parts[parts.index('images')] = 'labels'
        label_file = root.joinpath(*parts).with_suffix('.txt')
        if not label_file.is_file():
            raise ValueError('YOLO 图像缺少对应标注文件。')
        for line in label_file.read_text().splitlines():
            if not line.strip():
                continue
            if len(line) > MAX_ANNOTATION_LINE_CHARS:
                raise ValueError('YOLO 单条标注超过限制。')
            values = [float(value) for value in line.split()]
            if len(values) < 5 or any(not math.isfinite(value) for value in values) or not values[0].is_integer() or not 0 <= values[0] < len(names):
                raise ValueError('YOLO 标注包含无效类别或坐标。')
            task = params.get('task', 'detect')
            if task == 'detect' and len(values) != 5:
                raise ValueError('检测标注必须包含 class x_center y_center width height。')
            if task in ('detect', 'pose') and (any(not 0 <= value <= 1 for value in values[1:5]) or not all(values[index] > 0 for index in (3, 4))):
                raise ValueError('YOLO 边界框必须是有效的归一化坐标。')
            if task in ('segment', 'obb'):
                if task == 'obb' and len(values) != 9 or task == 'segment' and (len(values) < 7 or len(values) % 2 != 1):
                    raise ValueError('YOLO 多边形标注点数无效。')
                if any(not 0 <= value <= 1 for value in values[1:]):
                    raise ValueError('YOLO 多边形必须使用归一化坐标。')
            if task == 'pose':
                shape = data.get('kpt_shape')
                if not isinstance(shape, list) or len(shape) != 2 or not all(isinstance(value, int) and not isinstance(value, bool) for value in shape) or shape[1] not in (2, 3) or len(values) != 5 + shape[0] * shape[1]:
                    raise ValueError('姿态标注长度与 kpt_shape 不一致。')
                for offset in range(5, len(values), shape[1]):
                    if any(not 0 <= coordinate <= 1 for coordinate in values[offset:offset + 2]) or shape[1] == 3 and values[offset + 2] not in (0, 1, 2):
                        raise ValueError('姿态坐标或可见性无效。')
            objects += 1
    if not objects:
        raise ValueError('YOLO 测试集没有可评分目标，不能生成零指标占位。')
    output = root / 'evaluation-data.yaml'
    normalized = {'path': str(root), 'names': names, 'nc': len(names),
        'train': str(selected), 'val': str(selected), 'test': str(selected)}
    if params.get('task') == 'pose':
        shape = data.get('kpt_shape')
        if not isinstance(shape, list) or len(shape) != 2 or any(isinstance(value, bool) or not isinstance(value, int) for value in shape) or not 1 <= shape[0] <= 1000 or shape[1] not in (2, 3):
            raise ValueError('姿态数据缺少有效的 kpt_shape。')
        normalized['kpt_shape'] = shape
        if data.get('flip_idx') is not None:
            if not isinstance(data['flip_idx'], list) or sorted(data['flip_idx']) != list(range(shape[0])):
                raise ValueError('姿态 flip_idx 无效。')
            normalized['flip_idx'] = data['flip_idx']
    output.write_text(yaml.safe_dump(normalized), encoding='utf-8')
    return output, len(images)


def evaluate_yolo(model_path, dataset, params, classes):
    from ultralytics import YOLO
    model_path = Path(model_path)
    if model_path.suffix.lower() not in ('.torchscript', '.onnx', '.safetensors', '.pt', '.pth'):
        raise ValueError('YOLO 需要真实 TorchScript/ONNX 导出或安全 tensor 权重。')
    if model_path.suffix.lower() in ('.pt', '.pth', '.safetensors'):
        checkpoint = _checkpoint(model_path)
        state = checkpoint.get('model_state_dict', checkpoint.get('state_dict'))
        if not isinstance(state, dict):
            raise ValueError('YOLO .pt 含可执行模型对象，不能安全加载；请导出 TorchScript/ONNX 或 tensor state_dict。')
        version = str(params.get('yolo_version', '11')).lower().removeprefix('yolo').removeprefix('v')
        variant = params.get('model_variant', 'n')
        if version not in ('8', '9', '10', '11', '12', '26') or variant not in ('n', 's', 'm', 'l', 'x'):
            raise ValueError('YOLO 架构标识无效。')
        prefix = 'yolov' if int(version) < 11 else 'yolo'
        suffix = {'classify': '-cls', 'segment': '-seg', 'pose': '-pose', 'obb': '-obb'}.get(params.get('task'), '')
        model = YOLO(f'{prefix}{version}{variant}{suffix}.yaml', task=params.get('task', 'detect'))
        architecture = {**model.model.yaml, 'nc': len(classes)}
        model.model = type(model.model)(cfg=architecture, nc=len(classes), verbose=False)
        model.model.load_state_dict(state, strict=True)
    else:
        model = YOLO(str(model_path), task=params.get('task', 'detect'))
    if params.get('task') == 'classify':
        samples = image_samples(dataset, classes, params.get('split', 'test'))
        results = model.predict(source=[str(path) for path, _ in samples], device='cpu', batch=1,
            imgsz=params.get('image_size', 224), verbose=False, save=False)
        if len(results) != len(samples) or any(result.probs is None for result in results):
            raise ValueError('YOLO 分类器没有返回真实类别概率。')
        probabilities = [result.probs.data.cpu().tolist() for result in results]
        if any(len(row) != len(classes) or any(not math.isfinite(value) for value in row) for row in probabilities):
            raise ValueError('YOLO 分类概率或类别数量无效。')
        metrics = classification_metrics([label for _, label in samples],
            [max(range(len(row)), key=row.__getitem__) for row in probabilities], probabilities, classes)
        metrics['task'] = 'classify'
        return metrics
    data, count = _yolo_data(dataset, params, classes)
    metrics = model.val(data=str(data), split=params.get('split', 'test'), device='cpu', workers=0, batch=1,
        imgsz=params.get('image_size', 224), plots=False, save=False, verbose=False,
        project=str(Path(dataset) / 'validation-output'), exist_ok=True)
    values = metrics.results_dict
    result = {'sample_count': count, 'task': params.get('task', 'detect')}
    suffix = {'segment': 'M', 'pose': 'P', 'obb': 'OBB'}.get(params.get('task'), 'B')
    for key, source in (('precision', f'metrics/precision({suffix})'), ('recall', f'metrics/recall({suffix})'),
        ('mAP50', f'metrics/mAP50({suffix})'), ('mAP50_95', f'metrics/mAP50-95({suffix})')):
        value = values.get(source)
        if value is None or not math.isfinite(float(value)):
            raise ValueError('YOLO 评测未返回所需的真实指标。')
        result[key] = float(value)
    return result
