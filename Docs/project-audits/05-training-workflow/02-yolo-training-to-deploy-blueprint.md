# YOLO 训练 + 网站部署完整业务流程

> 文档目的：基于 Flowly 当前代码现状，针对 YOLO 模型训练 + 权重保存 + 网站自动生成 + 左导航栏项目管理 + CodeGraph 解析这条具体链路，给出完整的业务流程、节点设计、页面交互、实时反馈机制。  
> 这不是通用训练方案，而是你刚才描述的具体场景的专项方案。

---

## 一、先明确你描述的完整链路

你描述的链路拆解下来是这样的：

```text
上传已标注数据集
    → 选择 YOLO 版本
    → 配置训练参数与所需环境
    → 发起 YOLO 训练
    → 前端实时展示训练动画、数据曲线、时间估算
    → 训练完成，权重文件保存到客户本地
    → 通过大模型自动搭建权重识别网站
    → 网站在左导航栏产生独立项目入口
    → 网站支持 CodeGraph 全量解析
    → 用户可访问该网站进行识别推理
```

这条链路目前没有任何一个系统完整具备。你需要的是：

- 端到端完整跑通
- 每一步都有用户可见的实时反馈
- 最终产物是可直接使用的推理网站

下面按这个链路一步步拆解。

---

## 二、先看你当前代码的实际基础

这部分不是废话，你必须知道从哪起步。

### 2.1 训练节点现状

`Backend/workflows/services/langchain_service.py` 第 3929 行已有 `run_model_training_node()`：

- 接收 `framework` 参数，可选 pytorch / transformers
- 接收 `hyperparameters`
- 接收 `datasetId` / `datasetPath`
- 接收 `annotationProjectId`，可从标注项目导出已标数据
- 自动探测 GPU
- 创建 `TrainingJob` 记录
- 分发 Celery 异步任务

但目前训练节点是**通用训练**，没有 YOLO 专属路径。

### 2.2 标注数据现状

`Backend/annotations` app 已有 `AnnotationProject`，支持导出 JSON 格式标注数据。

这意味着你不需要用户手动整理数据集，而可以直接从标注项目导出。

### 2.3 网站生成现状

`Backend/website_generator` app 已有完整代码生成器：

- `DetectionGenerator`（目标检测网站生成）
- 生成了 Vue3 前端 + Flask 后端 + Dockerfile + docker-compose
- 支持上传图片 + bounding box 显示 + 置信度列表
- 后端已内置 YOLO 预处理/推理/后处理逻辑

这说明"大模型自动生成网站"这个节点**已经存在**，但目前需要手动传入 `model_path` 和 `labels`。

### 2.4 CodeGraph 现状

`Backend/codegraph` app 存在，应已具备代码解析能力。需要确认它是否能对生成的网站项目做全量解析。

### 2.5 结论

你当前的代码基础比很多同类系统强得多，但缺少的关键环节是：

1. YOLO 专属训练路径
2. 训练过程实时回传 WebSocket
3. 时间估算算法
4. 权重保存到用户本地
5. 从训练节点到网站生成节点的自动串联
6. 左导航栏项目管理入口
7. CodeGraph 集成到生成网站

---

## 三、完整业务流程拆解（节点级）

### 节点 1：数据准备节点（DatasetPrepare）

#### 功能
接收用户上传的已标注数据集，转化为 YOLO 格式的训练数据。

#### 输入
- 已标注数据集文件（支持 COCO JSON / VOC XML / 自定义格式）
- 或者直接传入 `annotation_project_id`，从标注系统导出

#### 输出
- 标准化 YOLO 格式数据集目录：
  ```
  /datasets/{project_id}/
    images/
      train/
      val/
    labels/
      train/
      val/
  dataset.yaml   ← YOLO 训练配置文件
  ```

#### 内部逻辑
1. 解析用户上传的标注文件格式
2. 转换为 YOLO txt 格式（class_id x_center y_center width height）
3. 按比例切分 train / val
4. 生成 `dataset.yaml`
5. 计算数据集统计：图片数、类别数、标注总数、平均每图目标数
6. 生成数据质量报告（类别分布、尺寸分布）

#### 前端交互
- 上传压缩包或选择已有标注项目
- 自动显示类别列表
- 显示数据切分预览
- 数据质量预警（如某类别样本极少）

#### 关键反馈
- 数据转换进度条
- 转换完成后显示：图片总数、train/val 数量、各类别数量分布

---

### 节点 2：YOLO 版本选择 + 环境配置节点（YOLOConfig）

#### 功能
让用户选择 YOLO 版本并配置运行时环境。

#### YOLO 版本选项
- YOLOv5
- YOLOv6
- YOLOv7
- YOLOv8（推荐）
- YOLOv9
- YOLOv10
- YOLO11（最新）

#### 环境配置项
用户需要配置的关键参数：

##### 基础配置
- `model_variant`：n / s / m / l / x（从预训练模型开始）
- `data_yaml`：指向上一步生成的 `dataset.yaml`
- `epochs`：训练轮次
- `batch_size`：批大小（根据 GPU 显存自动建议）
- `imgsz`：输入图片尺寸（默认 640）

##### 进阶配置
- `optimizer`：SGD / Adam / AdamW
- `learning_rate`：初始学习率
- `weight_decay`：权重衰减
- `warmup_epochs`：预热轮次
- `patience`：早停耐心值
- `cos_lr`：余弦学习率调度

##### 增强配置
- `hsv_h / hsv_s / hsv_v`：色相/饱和度/明度增强
- `degrees / translate / scale / shear`：几何增强
- `fliplr / mosaic / mixup`：数据增强开关

##### 环境检测与建议
这是你要求的一个重点：**访问客户配置和所需环境**。

系统应自动：
1. 检测 GPU 可用性（`torch.cuda.is_available()`）
2. 检测 GPU 型号与显存（`torch.cuda.get_device_properties()`）
3. 建议最优 `batch_size`：
   - < 8GB 显存：建议 batch_size = 8 或 16
   - 8-16GB：建议 batch_size = 16 或 32
   - > 16GB：建议 batch_size = 32 或 64
4. 估算训练时间（见 3.1 节）

#### 前端交互
- 版本选择下拉框 + 版本说明弹窗
- GPU 自动检测 + 显示显存大小
- batch_size 滑块（根据显存自动推荐）
- epochs 输入（默认 100）
- 高级配置折叠面板
- 配置预览 YAML 展示

---

### 节点 3：YOLO 训练节点（YOLOTraining）

这是整个链路的核心节点，也是实时反馈要求最高的节点。

#### 实时数据回传机制（重点）

当前 `run_model_training_node()` 已经通过 Celery 异步执行训练，但**没有 WebSocket 实时回传机制**。

你的需求明确要求：**前端实时展现训练动画和数据曲线**。

这意味着必须实现以下 WebSocket 推送：

```python
# 训练 Celery 任务中，定期推送进度
{
    "event": "training_progress",
    "data": {
        "job_id": "...",
        "epoch": 45,
        "total_epochs": 100,
        "progress_percent": 45.0,
        "current_loss": 0.234,
        "best_fitness": 0.876,
        "metrics": {
            "precision": 0.912,
            "recall": 0.887,
            "mAP50": 0.901,
            "mAP50-95": 0.678
        },
        "lr": 0.000123,
        "gpu_memory_used_mb": 6144,
        "gpu_memory_total_mb": 16384,
        "epoch_time_seconds": 187,
        "eta_seconds": 10285,
        "timestamp": "2026-06-05T23:45:00Z"
    }
}
```

#### 推送频率
- 每完成 1 个 epoch 推送一次完整指标
- 或者每 30 秒推送一次（即使 epoch 未完成）

#### 训练动画（前端实现）

前端需要实现的动画/可视化：

1. **进度环 / 进度条**：显示 epoch 进度 + 百分比
2. **Loss 曲线**：实时绘制当前 epoch 的 loss 变化趋势（折线图）
3. **mAP 曲线**：mAP50 / mAP50-95 随 epoch 变化的曲线
4. **Precision / Recall 曲线**
5. **GPU 显存使用图**：显存占用随训练进程的变化（柱状图或面积图）
6. **当前预测结果预览**：每隔 N 个 epoch 对验证集跑一次推理，展示预测样例
7. **训练状态卡**：GPU 型号、已用时间、预计剩余时间、当前学习率

#### 时间估算算法（重点实现）

你明确要求：**加入时间估算算法，让客户有时间准备**。

##### 估算公式

基于前 N 个 epoch 的实测数据做滚动估算：

```
avg_epoch_time = sum(last_N_epoch_times) / N
remaining_epochs = total_epochs - current_epoch
estimated_remaining_seconds = avg_epoch_time * remaining_epochs
estimated_total_seconds = elapsed_seconds + estimated_remaining_seconds
```

##### 首次估算（前 3 个 epoch 不显示 ETA）
因为前几个 epoch 时间波动大，不具备估算价值。

##### GPU 类型对估算的影响
- NVIDIA GPU（CUDA）：按实测时间估算
- CPU 训练：按比例放大（CPU 训练通常是 GPU 的 5-20 倍）

##### 显示格式
```
已用时间：15 分 32 秒
预计剩余：约 42 分钟
预计完成：今日 00:28
```

#### 训练过程中的用户操作
- **暂停**：保存 checkpoint，暂停训练
- **取消**：终止训练，保留已有的 checkpoint
- **查看日志**：实时滚动训练输出日志（loss、metrics 输出流）
- **查看当前权重**：每隔 N 个 epoch 可下载当前 best.pt

#### 训练完成后的输出

```python
{
    "success": True,
    "output": {
        "model_path": "/path/to/runs/train/exp/weights/best.pt",
        "last_epoch": 100,
        "best_fitness": 0.891,
        "final_metrics": {
            "precision": 0.923,
            "recall": 0.908,
            "mAP50": 0.934,
            "mAP50-95": 0.712
        },
        "export_formats": ["onnx", "torchscript"],
        "exported_paths": {
            "best.pt": "/path/to/best.pt",
            "last.pt": "/path/to/last.pt",
            "best.onnx": "/path/to/best.onnx"
        },
        "training_time_seconds": 3847,
        "dataset_stats": {...}
    }
}
```

---

### 节点 4：权重保存节点（ModelSave）

你要求：**训练出来的权重文件保存在客户的本地**。

这里的"本地"有两种理解：
1. 用户自己的服务器/电脑（self-hosted 场景）
2. 平台服务器上，但用户可下载到本地

#### 实现方案

##### 方案 A：下载到本地
- 训练完成后，前端触发 `/api/training/runs/{id}/download/` 接口
- 后端返回文件流
- 浏览器自动下载 `.pt` 文件
- 同时支持导出 ONNX、TorchScript 等格式

##### 方案 B：平台存储 + 可下载
- 权重文件保存在平台存储（如 `MEDIA_ROOT/training_outputs/{job_id}/weights/`）
- 用户在"我的模型"页面可查看、下载、删除

##### 方案 C：存储到对象存储（推荐生产环境）
- 对接 S3 / MinIO / 阿里云 OSS
- 用户可配置自己的 bucket
- 权重自动上传到对象存储
- 生成永久下载链接

#### 前端交互
- 训练完成后弹窗提示："训练完成，是否保存权重？"
- 显示可用格式列表（best.pt / last.pt / best.onnx / best.torchscript）
- 一键下载按钮
- 同时自动触发下一个节点（网站生成）

---

### 节点 5：网站生成节点（SiteGenerator）

你描述的核心能力：**通过大模型直接搭建权重文件识别类别的网站**。

#### 当前代码基础

`Backend/website_generator/generators/detection.py` 的 `DetectionGenerator` **已经能生成完整的目标检测网站**：

- Vue3 前端（图片上传 + bounding box + 置信度展示）
- Flask 后端（YOLO 推理 + 预处理/后处理）
- Dockerfile + docker-compose
- `.env` 配置

#### 当前缺失的环节

1. **自动识别 labels**：目前需要手动传入 `labels`，应该自动从训练产物的 dataset.yaml 或权重文件中读取类别
2. **自动注入 model_path**：权重文件路径应自动注入到生成的后端代码里
3. **与训练节点的串联**：训练完成后应自动触发网站生成，而不是手动再点一次

#### 自动获取类别（关键）

训练完成后，从以下位置获取类别列表：

```python
# 从 dataset.yaml 获取
with open(os.path.join(dataset_path, 'dataset.yaml')) as f:
    content = f.read()
    for line in content.split('\n'):
        if line.strip().startswith('names:'):
            # 解析 names: {0: class1, 1: class2} 或 names: [class1, class2]
            ...

# 或从训练输出目录获取
best_pt_path = '/path/to/best.pt'
# ultralytics 的模型文件里包含类别信息
from ultralytics import YOLO
model = YOLO(best_pt_path)
class_names = model.names  # dict {0: 'person', 1: 'car', ...}
```

#### 网站配置参数

网站生成节点应接收：

```python
{
    "model_path": "/path/to/best.pt",
    "labels": ["helmet", "no_helmet", "person"],  # 自动获取
    "framework": "ultralytics",
    "model_type": "yolov8",
    "port": 5000,
    "project_name": "安全帽检测系统",
    "output_dir": "/path/to/generated_site/"
}
```

#### 生成的文件结构

```
{project_name}/
├── frontend/
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   └── src/
│       └── App.vue
├── backend/
│   ├── app.py          ← 包含 YOLO 推理逻辑
│   ├── requirements.txt
│   ├── config.json
│   └── model/          ← 放置 best.pt
│       └── best.pt
├── Dockerfile
├── docker-compose.yml
├── .env.example
└── README.md
```

#### 前端交互
- 输入项目名称（如"安全帽检测系统"）
- 选择推理端口（默认 5000）
- 选择前端框架（Vue3 / React / 纯 HTML）
- 预览生成进度（每个文件生成状态）
- 生成完成后显示：
  - 本地启动命令
  - Docker 启动命令
  - 访问地址
  - 在线演示地址（如果有托管）

---

### 节点 6：项目创建节点（ProjectCreate）

你要求：**在左导航栏产生该项目入口**。

这意味着网站生成完成后，需要在平台里创建一个"项目"记录，并将该项目添加到当前用户的左侧导航栏。

#### 生成的平台项目记录

```python
{
    "id": "project_uuid",
    "name": "安全帽检测系统",
    "description": "基于 YOLOv8 的安全帽检测推理网站",
    "project_type": "yolo_detection",
    "site_id": "generated_site_uuid",    # 关联 GeneratedSite
    "model_path": "/path/to/best.pt",
    "labels": ["helmet", "no_helmet"],
    "site_url": "http://localhost:5000",
    "source_training_run_id": "training_run_uuid",
    "source_workflow_id": "workflow_uuid",
    "source_workflow_execution_id": "execution_uuid",
    "status": "deployed",   # generating / deployed / stopped
    "deployed_at": "2026-06-05T23:50:00Z",
    "created_by": "user_id",
    "tenant_id": "tenant_id"
}
```

#### 左导航栏入口

在用户侧边栏生成一个独立入口：

```
左导航栏
├── 工作流
├── 执行记录
├── 数据集
├── 标注
├── 我的项目        ← 新增
│   ├── 安全帽检测系统    ← 生成后自动添加
│   ├── 车牌识别系统
│   └── 垃圾分类系统
├── 模型管理
└── 设置
```

点击进入后应展示：
- 项目基本信息
- 推理网站访问地址
- 部署状态
- 使用统计（访问量、识别次数）
- 重新部署按钮
- 代码下载
- 删除项目

---

### 节点 7：CodeGraph 解析节点（CodeGraphAnalyze）

你要求：**允许进行 CodeGraph 的全面解析**。

#### 当前理解

CodeGraph 应能对生成的网站代码做全量分析，生成：

- 代码结构图（前端组件树、后端路由）
- 函数调用关系
- 数据流分析
- 依赖关系图
- 代码质量报告

#### 实现方式

生成的网站代码在平台存储后，触发 CodeGraph 解析：

```python
# 伪代码
from codegraph.analyzers import analyze_python, analyze_vue

# 分析后端
backend_result = analyze_python(
    code_dir='/path/to/generated_site/backend/',
    entry_file='app.py'
)

# 分析前端
frontend_result = analyze_vue(
    code_dir='/path/to/generated_site/frontend/'
)

# 生成综合报告
report = {
    "backend": backend_result,
    "frontend": frontend_result,
    "combined_graph": merge_graphs(backend_result, frontend_result)
}
```

#### 前端交互

在项目详情页中提供"代码解析"入口：

- 查看代码结构树
- 查看组件依赖关系图
- 查看 API 调用关系
- 查看数据流路径
- 生成代码质量报告

---

## 四、完整工作流模板设计

把以上所有节点串联成一条完整工作流模板：

```text
[数据准备] DatasetPrepare
    输入：annotation_project_id 或上传数据集
    输出：YOLO 格式数据集路径、dataset.yaml、统计信息
        ↓
[环境配置] YOLOConfig
    输入：YOLO 版本、训练参数、GPU 配置
    输出：完整训练配置 JSON
        ↓
[YOLO 训练] YOLOTraining
    输入：dataset.yaml、model_variant、epochs、batch_size 等
    输出：best.pt、last.pt、训练指标、时间统计
        ↓
[权重保存] ModelSave
    输入：训练产出权重路径
    输出：用户下载链接或上传到对象存储
        ↓
[网站生成] SiteGenerator
    输入：best.pt、labels（自动获取）、项目名称
    输出：完整网站代码目录
        ↓
[项目创建] ProjectCreate
    输入：项目名称、网站路径、模型路径
    输出：平台项目记录、左导航栏入口
        ↓
[代码解析] CodeGraphAnalyze
    输入：网站代码目录
    输出：代码结构图、质量报告
```

---

## 五、前端实时训练动画详细设计

这是你强调的重点功能，必须详细设计。

### 5.1 训练监控面板布局

```
┌──────────────────────────────────────────────────────────────┐
│  安全帽检测 - YOLOv8 训练中                                   │
│  状态：第 67 / 100 epoch   进度：67%                          │
│                                                              │
│  ┌────────────────────────────────────────────────────┐     │
│  │                    训练进度动画                       │     │
│  │          （动态进度环 + 粒子/渐变效果）               │     │
│  │                                                    │     │
│  │              ████████████░░░░░░░░░░               │     │
│  │                   67%  ·  67/100                  │     │
│  └────────────────────────────────────────────────────┘     │
│                                                              │
│  ┌──────────────────┐  ┌──────────────────┐  ┌────────────┐  │
│  │  mAP50          │  │  mAP50-95       │  │  最佳Fitness│  │
│  │  0.934          │  │  0.712          │  │  0.891     │  │
│  │  ▲ +0.003      │  │  ▲ +0.012      │  │  ▲ +0.005  │  │
│  └──────────────────┘  └──────────────────┘  └────────────┘  │
│                                                              │
│  ┌─────────────────────────────┐  ┌───────────────────────┐  │
│  │  Loss 曲线                   │  │  验证集预测样例        │  │
│  │  ~~~~~~~~~~~~~~~~~~~~~~~~   │  │  ┌─────┐ ┌─────┐    │  │
│  │  loss_box  │ loss_cls     │  │  │ img │ │ img │    │  │
│  │  当前: 0.23│  当前: 0.067  │  │  │ 预测 │ │ 预测 │    │  │
│  └─────────────────────────────┘  └───────────────────────┘  │
│                                                              │
│  ┌──────────────────┐  ┌────────────────────────────────┐   │
│  │  GPU: RTX 4090  │  │  已用: 15:32  │  预计剩余: ~42分钟 │  │
│  │  显存: 6.1G/24G │  │  预计完成: 00:28                │  │
│  └──────────────────┘  └────────────────────────────────┘   │
│                                                              │
│  [ 暂停训练 ]  [ 查看日志 ]  [ 下载当前权重 ]  [ 取消训练 ]   │
└──────────────────────────────────────────────────────────────┘
```

### 5.2 训练动画效果

进度环动画：
- 环形进度条，随 epoch 推进逐渐填满
- 中心数字显示当前 epoch / 总 epoch
- 环形颜色渐变（蓝色 → 黄色 → 绿色，随指标提升）
- 环形周围有旋转粒子效果（可选）

Loss 曲线动画：
- 实时追加新数据点
- 平滑滚动，保留最近 50 个 epoch 的曲线
- 两条曲线：loss_box（定位 loss）和 loss_cls（分类 loss）
- 悬停显示具体数值

### 5.3 时间估算 UX

```
预计剩余时间计算逻辑：

第 1-3 epoch：显示 "正在分析训练速度..."
第 4 epoch 开始：显示 "~{N}分钟"（基于前3个epoch平均值）
第 10 epoch 开始：显示 "~{H}小时{M}分钟"（基于最近7个epoch）
训练后期：显示精确到分钟

颜色语义：
绿色：按预期进度
黄色：比预期慢 > 20%
红色：比预期慢 > 50%（可能有问题）
```

---

## 六、接口设计

### 训练发起接口

```
POST /api/v1/training/yolo-runs/
```

Request:
```json
{
    "name": "安全帽检测训练",
    "annotation_project_id": "uuid-of-annotation-project",
    "yolo_version": "v8",
    "model_variant": "n",
    "epochs": 100,
    "batch_size": 16,
    "imgsz": 640,
    "optimizer": "SGD",
    "learning_rate": 0.01,
    "weight_decay": 0.0005,
    "patience": 50,
    "augmentation": {
        "hsv_h": 0.015,
        "hsv_s": 0.7,
        "hsv_v": 0.4,
        "degrees": 0.0,
        "translate": 0.1,
        "scale": 0.5,
        "fliplr": 0.5,
        "mosaic": 1.0,
        "mixup": 0.0
    },
    "checkpoint_save_interval": 10,
    "notify_on_complete": true
}
```

Response:
```json
{
    "run_id": "uuid",
    "status": "queued",
    "estimated_duration_seconds": 3847,
    "websocket_url": "ws://host/ws/training/uuid/",
    "dataset_stats": {
        "train_images": 1200,
        "val_images": 300,
        "classes": 3
    },
    "message": "训练任务已创建，将在 GPU 可用时开始"
}
```

### WebSocket 训练进度推送

```
ws://host/ws/training/{run_id}/
```

推送消息格式：

```json
{
    "event": "training_progress",
    "data": {
        "run_id": "...",
        "epoch": 67,
        "total_epochs": 100,
        "progress_percent": 67.0,
        "loss": {
            "box": 0.234,
            "cls": 0.067,
            "dfl": 0.089
        },
        "metrics": {
            "precision": 0.912,
            "recall": 0.887,
            "mAP50": 0.901,
            "mAP50-95": 0.678,
            "fitness": 0.891
        },
        "lr": 0.000123,
        "gpu": {
            "name": "NVIDIA RTX 4090",
            "memory_used_mb": 6144,
            "memory_total_mb": 24576,
            "utilization_percent": 87
        },
        "timing": {
            "epoch_time_seconds": 187,
            "elapsed_seconds": 12529,
            "eta_seconds": 6171,
            "eta_formatted": "约 1 小时 42 分钟"
        },
        "best_epoch": 62,
        "best_fitness": 0.891,
        "timestamp": "2026-06-05T23:45:00Z"
    }
}
```

### 网站生成接口

```
POST /api/v1/website/yolo-generate/
```

Request:
```json
{
    "training_run_id": "uuid-of-training-run",
    "project_name": "安全帽检测系统",
    "description": "基于 YOLOv8n 的安全帽检测推理网站",
    "port": 5000,
    "frontend_framework": "vue3",
    "backend_framework": "flask",
    "deploy_option": "local",    // local / docker / cloud
    "generate_codegraph_report": true
}
```

### 项目管理接口

```
GET    /api/v1/projects/                          # 项目列表
POST   /api/v1/projects/                          # 创建项目
GET    /api/v1/projects/{id}/                    # 项目详情
DELETE /api/v1/projects/{id}/                    # 删除项目
POST   /api/v1/projects/{id}/deploy/             # 部署网站
POST   /api/v1/projects/{id}/stop/               # 停止网站
GET    /api/v1/projects/{id}/codegraph/          # 获取代码解析结果
GET    /api/v1/projects/{id}/usage-stats/       # 使用统计
```

---

## 七、数据模型建议

### 新增 / 升级的模型

#### YOLOTrainingRun（升级自 TrainingJob）
```python
class YOLOTrainingRun(models.Model):
    # 关联
    annotation_project = ForeignKey(AnnotationProject, ...)
    yolo_version = CharField()      # v5 / v6 / v7 / v8 / v9 / v10 / 11
    model_variant = CharField()     # n / s / m / l / x
    dataset_path = CharField()
    dataset_yaml = TextField()

    # 配置快照
    config_snapshot = JSONField()    # 完整训练配置

    # YOLO 专有指标
    loss_box_history = JSONField()
    loss_cls_history = JSONField()
    loss_dfl_history = JSONField()
    map50_history = JSONField()
    map50_95_history = JSONField()
    precision_history = JSONField()
    recall_history = JSONField()

    # 实时进度（WebSocket 推送用）
    current_epoch = IntegerField()
    best_epoch = IntegerField()
    best_fitness = FloatField()
    gpu_info = JSONField()

    # 产出
    best_weight_path = CharField()
    last_weight_path = CharField()
    exported_formats = JSONField()    # {onnx: path, torchscript: path, ...}

    # 估算
    estimated_duration_seconds = IntegerField()
    actual_duration_seconds = IntegerField()
```

#### GeneratedProject（新增）
```python
class GeneratedProject(models.Model):
    name = CharField(max_length=200)
    description = TextField()
    project_type = CharField()        # yolo_detection / classification / ...
    tenant = ForeignKey(Tenant)
    created_by = ForeignKey(User)

    # 关联训练
    source_training_run = OneToOneField(YOLOTrainingRun)

    # 关联网站
    generated_site = ForeignKey(GeneratedSite)

    # 网站配置
    site_url = URLField()
    port = IntegerField()
    deployment_status = CharField()    # generating / deployed / stopped / error

    # 代码解析
    codegraph_report = JSONField()
    codegraph_analyzed_at = DateTimeField()

    # 统计
    visit_count = IntegerField(default=0)
    inference_count = IntegerField(default=0)
    last_accessed_at = DateTimeField()

    status = CharField()              # active / archived
    created_at = DateTimeField()
    updated_at = DateTimeField()
```

---

## 八、时间估算算法（代码级实现）

```python
class YOLOTrainingTimeEstimator:
    """
    基于滚动平均的 YOLO 训练时间估算器。
    使用最近 N 个 epoch 的实测时间来预测剩余时间。
    """

    def __init__(self, total_epochs: int, warmup_epochs: int = 3):
        self.total_epochs = total_epochs
        self.warmup_epochs = warmup_epochs
        self.epoch_times = []  # 最近每个 epoch 的耗时（秒）
        self.rolling_window = 7  # 滚动窗口大小

    def add_epoch_time(self, epoch: int, time_seconds: float):
        """记录一个 epoch 的耗时。"""
        self.epoch_times.append(time_seconds)

    def get_eta_seconds(self, current_epoch: int) -> Optional[float]:
        """
        获取预估剩余时间（秒）。
        如果 epoch 数 <= warmup_epochs，返回 None（估算不可靠）。
        """
        if current_epoch <= self.warmup_epochs:
            return None

        # 取最近 N 个 epoch 的时间（排除 warmup）
        recent_times = self.epoch_times[-(self.rolling_window):]
        if not recent_times:
            return None

        avg_epoch_time = sum(recent_times) / len(recent_times)
        remaining_epochs = self.total_epochs - current_epoch

        # 加 10% buffer（防止最后阶段过慢）
        return avg_epoch_time * remaining_epochs * 1.1

    def get_total_estimated_seconds(self, current_epoch: int, elapsed_seconds: float) -> Optional[float]:
        """
        获取预估总训练时间（秒）。
        """
        eta = self.get_eta_seconds(current_epoch)
        if eta is None:
            return None
        return elapsed_seconds + eta

    def get_eta_formatted(self, current_epoch: int, elapsed_seconds: float) -> str:
        """
        获取格式化的预估剩余时间。
        """
        eta = self.get_eta_seconds(current_epoch)
        if eta is None:
            return "正在分析训练速度..."

        hours = int(eta // 3600)
        minutes = int((eta % 3600) // 60)
        seconds = int(eta % 60)

        if hours > 0:
            return f"约 {hours} 小时 {minutes} 分钟"
        elif minutes > 0:
            return f"约 {minutes} 分钟 {seconds} 秒"
        else:
            return f"约 {seconds} 秒"

    def get_total_formatted(self, current_epoch: int, elapsed_seconds: float) -> str:
        """
        获取格式化的预估总时间。
        """
        total = self.get_total_estimated_seconds(current_epoch, elapsed_seconds)
        if total is None:
            return "估算中..."

        hours = int(total // 3600)
        minutes = int((total % 3600) // 60)

        if hours > 0:
            return f"{hours} 小时 {minutes} 分钟"
        else:
            return f"{minutes} 分钟"

    def get_completion_time(self, current_epoch: int, elapsed_seconds: float) -> Optional[datetime]:
        """
        预估完成时间点。
        """
        eta = self.get_eta_seconds(current_epoch)
        if eta is None:
            return None
        return timezone.now() + timedelta(seconds=eta)
```

---

## 九、与现有系统的打通

### 和 Annotation 打通
- 直接选择已完成的标注项目作为训练数据源
- 不需要用户再导出/上传
- 标注项目 → 数据集转换 → 训练，全自动串联

### 和 Workflow Executor 打通
- 整个链路是一个完整工作流
- 每个节点状态实时写入 `WorkflowExecution` + `NodeExecution`
- 可以在执行详情页看到完整训练时间线

### 和 Gateway / Credential 打通
- GPU 调用可能需要特定凭证（如果是远程 GPU 集群）
- 通过统一 credential 体系读取

### 和 Tenant 打通
- 所有训练任务、网站生成、项目记录都属于当前 tenant
- 团队成员共享项目
- 支持团队级别的模型管理和部署

### 和 Storage 打通
- 权重文件、生成的网站代码，全部存入统一存储
- 支持本地存储 / MinIO / S3

---

## 十、落地优先级建议

按当前代码现状，分阶段落地：

### Phase 1（最高优先级）：让 YOLO 训练真正跑起来
1. 新增 YOLO 专属训练节点（ultralytics 路径）
2. 实现 WebSocket 实时进度推送
3. 实现前端训练动画和曲线
4. 实现时间估算算法

### Phase 2：打通训练到网站生成
1. 自动从训练产出获取 labels
2. 自动串联到网站生成节点
3. 生成网站可自动注入 model_path

### Phase 3：项目化管理
1. 生成网站后自动创建 GeneratedProject
2. 左导航栏自动出现项目入口
3. 项目详情页展示部署状态和访问统计

### Phase 4：CodeGraph 集成
1. 网站生成完成后自动触发 CodeGraph 解析
2. 项目详情页展示代码结构
3. 支持重新解析

---

## 十一、最终判断

你描述的这条链路本身是成立的，而且你当前代码已经有非常好的基础：

- `DetectionGenerator` 已经能生成完整网站
- `AnnotationProject` 已经支持标注数据导出
- `TrainingJob` 已经有异步训练框架
- `workflows` 已经有完整的节点执行体系

你真正缺少的不是从头做，而是**把现有的东西串起来 + 补实时反馈 + 补 YOLO 专属路径**。

最优先要做的一件事：

> **先让 YOLO 训练节点能真正跑起来（Phase 1），同时把 WebSocket 实时推送和前端动画做进去。**  
> 这是你描述的所有功能里，用户感知最强、价值最高的一环。  
> 其他节点可以后补，但这环如果跑不通，后面所有东西都等于零。
