"""CPU inference over real samples; never deserialize executable Python objects."""
import csv
import json
import math
from pathlib import Path
import zipfile
from .constants import MAX_FEATURES, MAX_MODEL_PARAMETERS, MAX_SAMPLES


def _number(value):
    if isinstance(value, bool):
        raise ValueError('特征必须是有限数值。')
    number = float(value)
    if not math.isfinite(number):
        raise ValueError('特征包含 NaN 或无穷大。')
    return number


def read_tabular_data(path, label_column=None, features=None):
    path = Path(path)
    if path.suffix.lower() == '.csv':
        with path.open(encoding='utf-8-sig', newline='') as source:
            reader = csv.DictReader(source)
            columns = reader.fieldnames or []
            if len(set(columns)) != len(columns) or len(columns) < 2:
                raise ValueError('CSV 必须有唯一表头、至少一个特征和标签列。')
            label_column = label_column or ('label' if 'label' in columns else columns[-1])
            features = features or [name for name in columns if name != label_column]
            if label_column not in columns or not features or any(name not in columns or name == label_column for name in features):
                raise ValueError('指定的标签列或特征列不存在。')
            values, labels = [], []
            for row in reader:
                if len(values) >= MAX_SAMPLES:
                    raise ValueError('测试样本数超过限制。')
                if None in row or any(row.get(name) is None or not str(row[name]).strip() for name in [*features, label_column]):
                    raise ValueError('测试数据包含缺列或空值，未丢弃样本。')
                values.append([_number(row[name]) for name in features])
                labels.append(row[label_column])
    elif path.suffix.lower() == '.json':
        data = json.loads(path.read_text(encoding='utf-8-sig'))
        values, labels = data.get('features'), data.get('labels')
        if not isinstance(values, list) or not isinstance(labels, list):
            raise ValueError('JSON 必须包含 features 二维数组和 labels 数组。')
        values = [[_number(value) for value in row] for row in values]
        names = data.get('feature_names')
        if names is not None:
            if not isinstance(names, list) or len(set(names)) != len(names) or any(not isinstance(name, str) for name in names):
                raise ValueError('JSON feature_names 必须是唯一的列名数组。')
            if any(len(row) != len(names) for row in values):
                raise ValueError('JSON 特征列名数量与样本维度不一致。')
            if features:
                if any(name not in names for name in features):
                    raise ValueError('JSON 缺少模型要求的特征列。')
                values = [[row[names.index(name)] for name in features] for row in values]
    else:
        raise ValueError('通用分类评测需要已登记的 CSV 或 JSON 标注数据。')
    if not values or len(values) != len(labels) or len(values) > MAX_SAMPLES:
        raise ValueError('测试样本不能为空，特征与标签数量必须一致且不超过限制。')
    width = len(values[0])
    if not 0 < width <= MAX_FEATURES or any(len(row) != width for row in values):
        raise ValueError('样本特征维度为空、不一致或超过限制。')
    return values, labels


def _checkpoint(path):
    import torch
    if Path(path).suffix.lower() == '.safetensors':
        from safetensors.torch import load_file
        return {'model_state_dict': load_file(str(path), device='cpu')}
    if not zipfile.is_zipfile(path):
        raise ValueError('仅接受 ZIP tensor checkpoint；旧任意 pickle 模型请导出安全权重。')
    with zipfile.ZipFile(path) as archive:
        if any(name.endswith('/constants.pkl') for name in archive.namelist()):
            raise ValueError('TorchScript 不能伪装成普通 checkpoint，请使用登记的 .torchscript 导出。')
    result = torch.load(str(path), map_location='cpu', weights_only=True)
    if not isinstance(result, dict):
        raise ValueError('模型必须是已知结构的 tensor checkpoint。')
    return result


def _mlp(checkpoint, configuration):
    import torch
    state = checkpoint.get('model_state_dict')
    if state is None:
        state = checkpoint.get('state_dict')
    if not isinstance(state, dict) or not state or any(not isinstance(value, torch.Tensor) for value in state.values()):
        raise ValueError('模型不含通用分类器所需的真实 state_dict。')
    config = {**configuration, **(checkpoint.get('config') if isinstance(checkpoint.get('config'), dict) else {})}
    dimensions = [config.get('input_dim', 784), *(config.get('hidden_dims', [256, 128])), config.get('output_dim', 10)]
    if any(isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= MAX_FEATURES for value in dimensions):
        raise ValueError('模型维度配置无效或超过限制。')
    if sum((left + 1) * right for left, right in zip(dimensions, dimensions[1:])) > MAX_MODEL_PARAMETERS:
        raise ValueError('模型参数量超过评测限制。')
    dropout = float(config.get('dropout', .2))
    if not math.isfinite(dropout) or not 0 <= dropout < 1:
        raise ValueError('模型 dropout 配置无效。')
    layers = []
    for index, (left, right) in enumerate(zip(dimensions, dimensions[1:])):
        layers.append(torch.nn.Linear(left, right))
        if index < len(dimensions) - 2:
            layers.append(torch.nn.ReLU())
            if dropout:
                layers.append(torch.nn.Dropout(dropout))
    model = torch.nn.Sequential(*layers)
    model.load_state_dict(state, strict=True)
    return model.eval(), dimensions[0], dimensions[-1]


def classification_metrics(expected, predicted, probabilities, labels):
    if not expected or len(expected) != len(predicted):
        raise ValueError('没有实际可评分样本，不能生成零分占位指标。')
    count = len(expected)
    matrix = [[0 for _ in labels] for _ in labels]
    for truth, guess in zip(expected, predicted):
        if not 0 <= truth < len(labels) or not 0 <= guess < len(labels):
            raise ValueError('真实或预测类别超出模型类别范围。')
        matrix[truth][guess] += 1
    precision = recall = f1 = 0.0
    for index, row in enumerate(matrix):
        support, true_positive = sum(row), row[index]
        predicted_count = sum(line[index] for line in matrix)
        precision += support * (true_positive / predicted_count if predicted_count else 0.0)
        recall += support * (true_positive / support if support else 0.0)
        f1 += support * (2 * true_positive / (support + predicted_count) if support + predicted_count else 0.0)
    result = {'sample_count': count, 'accuracy': sum(matrix[index][index] for index in range(len(labels))) / count,
        'precision': precision / count, 'recall': recall / count, 'f1': f1 / count,
        'classes': labels, 'confusion_matrix': matrix}
    class_aucs = [_binary_auc([int(value == index) for value in expected], [row[index] for row in probabilities])
                  for index in ([1] if len(labels) == 2 else range(len(labels)))]
    result['auc'] = sum(class_aucs) / len(class_aucs) if class_aucs and all(value is not None for value in class_aucs) else None
    return result


def _binary_auc(expected, scores):
    positives = sum(expected)
    negatives = len(expected) - positives
    if not positives or not negatives:
        return None
    ordered = sorted(zip(scores, expected))
    positive_rank_sum = 0.0
    index = 0
    while index < len(ordered):
        end = index + 1
        while end < len(ordered) and ordered[end][0] == ordered[index][0]:
            end += 1
        average_rank = (index + 1 + end) / 2
        positive_rank_sum += average_rank * sum(label for _, label in ordered[index:end])
        index = end
    return (positive_rank_sum - positives * (positives + 1) / 2) / (positives * negatives)


def _label_indices(values, classes):
    result = []
    for value in values:
        if str(value) in classes:
            result.append(classes.index(str(value)))
        else:
            try:
                number = float(value)
            except (ValueError, TypeError):
                raise ValueError('测试标签不属于模型的已登记类别。') from None
            if not math.isfinite(number) or not number.is_integer() or not 0 <= number < len(classes):
                raise ValueError('测试标签索引超出真实模型类别。')
            index = int(number)
            result.append(index)
    return result


def evaluate_pytorch_classifier(model_path, test_data, labels, configuration=None, training_data=None):
    """Preserve the callable interface, requiring real samples and safe weights."""
    if not test_data:
        raise ValueError('测试样本不能为空。')
    values = [[_number(value) for value in sample['features']] for sample in test_data]
    return _tabular_inference(model_path, values, [sample['label'] for sample in test_data], labels, configuration or {}, training_data)


def _tabular_inference(model_path, values, targets, labels, configuration, training_data=None, checkpoint=None):
    import torch
    if Path(model_path).suffix.lower() == '.torchscript':
        model = torch.jit.load(str(model_path), map_location='cpu').eval()
        input_dim, output_dim = len(values[0]), len(labels)
        config = {}
    else:
        checkpoint = checkpoint if checkpoint is not None else _checkpoint(model_path)
        model, input_dim, output_dim = _mlp(checkpoint, configuration)
        config = {**configuration, **(checkpoint.get('config') if isinstance(checkpoint.get('config'), dict) else {})}
    if not values or any(len(row) != input_dim for row in values):
        raise ValueError('测试特征列与模型输入维度不一致。')
    labels = [str(value) for value in labels] if labels else [str(index) for index in range(output_dim)]
    if len(labels) != output_dim or len(set(labels)) != len(labels):
        raise ValueError('真实类别数与模型输出维度不一致。')
    inputs = torch.tensor(values, dtype=torch.float32)
    preprocessing = 'raw_features'
    metadata = checkpoint.get('preprocessing', {}) if isinstance(checkpoint, dict) else {}
    if metadata:
        from training.tabular_artifacts import SCHEMA_VERSION
        if metadata.get('schema') != SCHEMA_VERSION or metadata.get('kind') not in ('none', 'standardize'):
            raise ValueError('模型的标准化元数据版本或类型不受支持。')
        if metadata['kind'] == 'standardize':
            if not isinstance(metadata.get('mean'), list) or not isinstance(metadata.get('std'), list):
                raise ValueError('模型缺少完整的标准化统计量。')
            config['input_mean'], config['input_std'] = metadata.get('mean'), metadata.get('std')
    if config.get('input_mean') is not None or config.get('input_std') is not None:
        means = [_number(value) for value in config.get('input_mean', [])]
        scales = [_number(value) for value in config.get('input_std', [])]
        if len(means) != input_dim or len(scales) != input_dim or any(scale < 0 for scale in scales):
            raise ValueError('模型记录的标准化参数无效或维度不匹配。')
        inputs = (inputs - torch.tensor(means)) / (torch.tensor(scales) + 1e-8)
        preprocessing = 'recorded_standardization'
    elif not metadata and config.get('dataset_path'):
        if not training_data:
            raise ValueError('旧模型训练使用标准化，但未记录scaler；请关联已登记的原训练数据，不能使用测试集重算。')
        label = None
        if Path(training_data).suffix.lower() == '.csv':
            with open(training_data, encoding='utf-8-sig', newline='') as stream:
                header = next(csv.reader(stream), [])
            label = header[-1] if header else None
        original, _ = read_tabular_data(training_data, label)
        if any(len(row) != input_dim for row in original):
            raise ValueError('原训练数据特征维度与模型不一致。')
        tensor = torch.tensor(original, dtype=torch.float32)
        inputs = (inputs - tensor.mean(dim=0)) / (tensor.std(dim=0, unbiased=False) + 1e-8)
        preprocessing = 'training_dataset_standardization'
    with torch.inference_mode():
        logits = model(inputs)
        if not isinstance(logits, torch.Tensor) or tuple(logits.shape) != (len(values), output_dim) or not torch.isfinite(logits).all():
            raise ValueError('模型没有返回有效的分类 logits。')
        probabilities = logits.softmax(dim=1).tolist()
        predicted = logits.argmax(dim=1).tolist()
    result = classification_metrics(_label_indices(targets, labels), predicted, probabilities, labels)
    result['preprocessing'] = preprocessing
    return result


def evaluate_csv_classification(model_path, csv_path, label_col=None, features=None, labels=None, configuration=None, training_data=None):
    configuration = configuration or {}
    checkpoint = None if Path(model_path).suffix.lower() == '.torchscript' else _checkpoint(model_path)
    config = {**configuration, **(checkpoint.get('config', {}) if checkpoint else {})}
    metadata = checkpoint.get('preprocessing', {}) if checkpoint else {}
    stored_features = metadata.get('feature_names') or config.get('feature_names') or []
    stored_label = metadata.get('label_column') or config.get('label_column')
    if not stored_features and not metadata and config.get('dataset_path') and training_data and Path(training_data).suffix.lower() == '.csv':
        with open(training_data, encoding='utf-8-sig', newline='') as source:
            original_header = next(csv.reader(source), [])
        stored_features, stored_label = original_header[:-1], original_header[-1] if original_header else None
    if stored_features:
        if not isinstance(stored_features, list) or any(not isinstance(name, str) for name in stored_features) or len(set(stored_features)) != len(stored_features):
            raise ValueError('模型的训练特征列描述无效。')
        if features and set(features) != set(stored_features):
            raise ValueError('所选特征列与模型训练Schema不一致。')
        features = stored_features
    values, targets = read_tabular_data(csv_path, label_col or stored_label, features)
    result = _tabular_inference(model_path, values, targets, labels or [], configuration, training_data, checkpoint)
    result['feature_columns'] = features or []
    return result


def evaluate_request(request):
    model, dataset, params = request['model'], request['dataset'], request['parameters']
    kind = request['training_kind']
    if kind == 'yolo':
        from .image_evaluators import evaluate_yolo
        return evaluate_yolo(model, dataset, params, request['class_names'])
    if kind == 'clip_cls':
        from .image_evaluators import evaluate_clip
        return evaluate_clip(model, dataset, params, request['class_names'])
    if kind != 'generic':
        raise ValueError('该模型类型尚无已验证适配器；请使用通用分类、CLIP分类或YOLO产物。')
    return evaluate_csv_classification(model, dataset, params.get('label_column'), params.get('features'),
        request['class_names'], request['model_configuration'], request.get('training_dataset'))
