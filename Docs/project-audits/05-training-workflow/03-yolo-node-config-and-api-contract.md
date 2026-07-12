# YOLO 节点配置与 API 协议规范

> 文档目的：把 YOLO 训练节点、网站生成节点、项目创建节点、CodeGraph 解析节点的 **输入输出字段、状态流、WebSocket 推送格式、前后端契约** 明确写死。  
> 这份文档的定位不是业务蓝图，而是协议层规范。写完之后，前端、后端、工作流节点、WebSocket 消费端都应该按同一套字段实现。

---

## 一、为什么必须先定协议，而不是继续写业务说明

你已经把业务逻辑说清楚了，现在最容易出问题的地方不是“不会做”，而是：

- 训练节点传什么字段，前后端各写一套
- WebSocket 推送什么，前端图表自己猜
- 网站生成节点到底是吃 `model_path`、`labels` 还是吃 `training_run_id`
- 左导航项目入口是读 `GeneratedSite` 还是读新项目模型
- CodeGraph 是异步触发还是同步触发

如果这些不先钉死，后面一定出现：
- 字段漂移
- 状态漂移
- 前端到处兼容
- 节点输出接不上后续节点

所以这份文档的目标很明确：

> **把 YOLO 专项链路的节点配置、REST API、WebSocket、状态机、节点上下文键名，统一成一套契约。**

---

## 二、总体协议原则

### 原则 1：工作流节点输出必须标准化
每个节点的输出都要写入统一 `context`，后续节点只能读标准 key，不能各自猜。

### 原则 2：REST 接口和工作流节点字段要同名
例如：
- 节点里叫 `training_run_id`
- REST 返回里也叫 `training_run_id`
- WebSocket 消息里也叫 `training_run_id`

不要一个地方叫 `job_id`，一个地方叫 `run_id`，另一个地方叫 `training_id`。

### 原则 3：状态枚举必须固定
不能今天 `completed`，明天 `success`，后天 `done`。

### 原则 4：网站生成优先吃训练产物引用，不优先吃裸路径
也就是：
- 优先使用 `training_run_id`
- 次选 `model_version_id`
- 最后才允许直接传 `model_path`

原因很简单：裸路径不可治理。

### 原则 5：WebSocket 消息必须有统一包结构
所有实时推送统一为：

```json
{
  "event": "training_progress",
  "version": "1.0",
  "timestamp": "2026-06-05T23:45:00Z",
  "data": {}
}
```

不要直接裸发业务字段。

---

## 三、统一上下文键名规范

工作流节点之间传递上下文，统一用下面这些 key。

### 3.1 数据准备输出 key

```json
{
  "dataset_id": "uuid",
  "dataset_version_id": "uuid",
  "dataset_path": "/data/datasets/project_123/",
  "dataset_yaml_path": "/data/datasets/project_123/dataset.yaml",
  "dataset_format": "yolo",
  "class_names": ["helmet", "no_helmet", "person"],
  "class_count": 3,
  "train_image_count": 1200,
  "val_image_count": 300,
  "annotation_project_id": "uuid"
}
```

### 3.2 YOLO 训练输出 key

```json
{
  "training_run_id": "uuid",
  "training_status": "completed",
  "yolo_version": "v8",
  "model_variant": "n",
  "best_weight_path": "/data/training_outputs/run_123/weights/best.pt",
  "last_weight_path": "/data/training_outputs/run_123/weights/last.pt",
  "exported_artifacts": {
    "pt": "/data/training_outputs/run_123/weights/best.pt",
    "onnx": "/data/training_outputs/run_123/export/best.onnx"
  },
  "class_names": ["helmet", "no_helmet", "person"],
  "final_metrics": {
    "precision": 0.923,
    "recall": 0.908,
    "mAP50": 0.934,
    "mAP50_95": 0.712,
    "fitness": 0.891
  },
  "training_duration_seconds": 3847,
  "estimated_duration_seconds": 4020,
  "best_epoch": 62,
  "project_suggestion_name": "安全帽检测系统"
}
```

### 3.3 网站生成输出 key

```json
{
  "generated_site_id": "uuid",
  "generated_site_status": "completed",
  "generated_site_output_dir": "/data/generated_sites/site_123/",
  "generated_site_url": "http://localhost:5000",
  "generated_site_port": 5000,
  "generated_site_download_url": "/api/v1/website-generator/{id}/download/",
  "project_name": "安全帽检测系统"
}
```

### 3.4 项目创建输出 key

```json
{
  "project_id": "uuid",
  "project_name": "安全帽检测系统",
  "project_type": "yolo_detection",
  "project_status": "active",
  "project_nav_slug": "helmet-detection-system"
}
```

### 3.5 CodeGraph 输出 key

```json
{
  "codegraph_analysis_id": "uuid",
  "codegraph_status": "completed",
  "codegraph_report_url": "/api/v1/projects/{id}/codegraph/",
  "codegraph_summary": {
    "backend_files": 8,
    "frontend_files": 12,
    "api_routes": 3,
    "components": 4,
    "issues": 2
  }
}
```

---

## 四、YOLO 训练节点配置协议

这里定义的是工作流里的 `yolo_training` 专项节点，不是泛用 `model_training`。

### 4.1 节点类型建议

建议新增节点类型：

```text
yolo_training
```

而不是继续把 YOLO 塞进通用 `model_training`。

原因：
- YOLO 配置非常专门
- 指标体系特殊（mAP50、mAP50-95、box/cls/dfl loss）
- 训练产物特殊（best.pt、last.pt、export）
- 前端看板也特殊

通用训练节点继续保留，但 YOLO 单独走专门节点。

---

### 4.2 节点配置 JSON 结构

```json
{
  "type": "yolo_training",
  "label": "YOLOv8 安全帽训练",
  "config": {
    "datasetSource": {
      "mode": "annotation_project",
      "annotationProjectId": "uuid",
      "datasetId": "",
      "datasetVersionId": ""
    },
    "model": {
      "yoloVersion": "v8",
      "modelVariant": "n",
      "pretrained": true,
      "weightsSource": "official",
      "baseWeightsPath": ""
    },
    "training": {
      "epochs": 100,
      "batchSize": 16,
      "imageSize": 640,
      "workers": 8,
      "device": "auto",
      "patience": 50,
      "cache": false,
      "resume": false,
      "seed": 42,
      "deterministic": false
    },
    "optimizer": {
      "name": "SGD",
      "learningRate": 0.01,
      "lrFinalFactor": 0.01,
      "momentum": 0.937,
      "weightDecay": 0.0005,
      "warmupEpochs": 3,
      "warmupMomentum": 0.8,
      "warmupBiasLr": 0.1,
      "cosLr": false
    },
    "augmentation": {
      "hsvH": 0.015,
      "hsvS": 0.7,
      "hsvV": 0.4,
      "degrees": 0.0,
      "translate": 0.1,
      "scale": 0.5,
      "shear": 0.0,
      "perspective": 0.0,
      "flipUd": 0.0,
      "flipLr": 0.5,
      "mosaic": 1.0,
      "mixup": 0.0,
      "copyPaste": 0.0
    },
    "checkpoint": {
      "enabled": true,
      "saveEveryNEpochs": 10,
      "saveBestOnly": false,
      "keepLast": true,
      "exportOnComplete": ["pt", "onnx"]
    },
    "runtime": {
      "environmentMode": "local_gpu",
      "pythonExecutable": "python",
      "workingDirectory": "",
      "storageTarget": "local",
      "storagePath": "",
      "credentialId": "",
      "allowAutoInstall": false
    },
    "ux": {
      "enableRealtimeMetrics": true,
      "enablePreviewSamples": true,
      "enableEta": true,
      "notifyOnComplete": true
    }
  }
}
```

---

### 4.3 字段说明

#### `datasetSource.mode`
可选值：
- `annotation_project`
- `dataset`
- `dataset_version`
- `filesystem`

#### `model.yoloVersion`
可选值：
- `v5`
- `v6`
- `v7`
- `v8`
- `v9`
- `v10`
- `11`

#### `model.modelVariant`
可选值：
- `n`
- `s`
- `m`
- `l`
- `x`

#### `runtime.environmentMode`
可选值：
- `local_gpu`
- `local_cpu`
- `remote_gpu`
- `docker`

#### `checkpoint.exportOnComplete`
可选值：
- `pt`
- `onnx`
- `torchscript`
- `engine`

---

### 4.4 节点输入依赖

#### 必选依赖
- `dataset_yaml_path` 或可转换出 `dataset_yaml_path` 的上游输出
- `class_names`

#### 可选依赖
- `baseWeightsPath`
- `credentialId`
- `storagePath`

#### 前置校验失败必须返回

```json
{
  "success": false,
  "error": {
    "code": "YOLO_PREFLIGHT_FAILED",
    "message": "GPU 环境不可用，且未允许 CPU fallback",
    "details": {
      "cuda_available": false,
      "environmentMode": "local_gpu"
    }
  }
}
```

---

## 五、YOLO 训练 REST API 协议

虽然工作流节点会触发训练，但平台也需要独立 API，供前端页面直接发起和管理训练。

---

### 5.1 创建 YOLO 训练运行

```text
POST /api/v1/training/yolo-runs/
```

#### Request

```json
{
  "name": "安全帽检测训练",
  "workflow_id": "uuid",
  "node_id": "uuid",
  "execution_id": "uuid",
  "dataset_source": {
    "mode": "annotation_project",
    "annotation_project_id": "uuid"
  },
  "model": {
    "yolo_version": "v8",
    "model_variant": "n",
    "pretrained": true
  },
  "training": {
    "epochs": 100,
    "batch_size": 16,
    "image_size": 640,
    "workers": 8,
    "device": "auto",
    "patience": 50
  },
  "optimizer": {
    "name": "SGD",
    "learning_rate": 0.01,
    "weight_decay": 0.0005,
    "warmup_epochs": 3,
    "cos_lr": false
  },
  "augmentation": {
    "mosaic": 1.0,
    "mixup": 0.0,
    "flip_lr": 0.5
  },
  "checkpoint": {
    "enabled": true,
    "save_every_n_epochs": 10,
    "export_on_complete": ["pt", "onnx"]
  },
  "runtime": {
    "environment_mode": "local_gpu",
    "storage_target": "local",
    "storage_path": "D:/CustomerModels/helmet-system/"
  }
}
```

#### Response 201

```json
{
  "training_run_id": "uuid",
  "status": "queued",
  "websocket_url": "/ws/training/uuid/",
  "estimated_duration_seconds": 4020,
  "estimated_completion_at": "2026-06-06T00:58:00Z",
  "dataset_summary": {
    "class_count": 3,
    "train_image_count": 1200,
    "val_image_count": 300
  },
  "gpu_summary": {
    "available": true,
    "name": "NVIDIA RTX 4090",
    "memory_total_mb": 24576,
    "recommended_batch_size": 16
  },
  "message": "YOLO 训练任务已入队"
}
```

#### 错误响应 400

```json
{
  "error": {
    "code": "INVALID_DATASET_SOURCE",
    "message": "annotation_project_id 不存在或不属于当前租户",
    "field": "dataset_source.annotation_project_id"
  }
}
```

---

### 5.2 获取 YOLO 训练详情

```text
GET /api/v1/training/yolo-runs/{training_run_id}/
```

#### Response 200

```json
{
  "training_run_id": "uuid",
  "name": "安全帽检测训练",
  "status": "running",
  "status_display": "训练中",
  "workflow_id": "uuid",
  "node_id": "uuid",
  "execution_id": "uuid",
  "dataset_source": {
    "mode": "annotation_project",
    "annotation_project_id": "uuid"
  },
  "model": {
    "yolo_version": "v8",
    "model_variant": "n",
    "pretrained": true
  },
  "progress": {
    "current_epoch": 67,
    "total_epochs": 100,
    "percent": 67.0,
    "best_epoch": 62,
    "best_fitness": 0.891
  },
  "timing": {
    "started_at": "2026-06-05T23:00:00Z",
    "elapsed_seconds": 12529,
    "estimated_duration_seconds": 4020,
    "eta_seconds": 6171,
    "estimated_completion_at": "2026-06-06T00:58:00Z"
  },
  "artifacts": {
    "best_weight_path": "",
    "last_weight_path": "",
    "exported_artifacts": {}
  },
  "final_metrics": null
}
```

---

### 5.3 获取训练历史曲线

```text
GET /api/v1/training/yolo-runs/{training_run_id}/metrics-history/
```

#### Response 200

```json
{
  "training_run_id": "uuid",
  "status": "running",
  "total_epochs": 100,
  "series": {
    "loss_box": [0.81, 0.74, 0.68],
    "loss_cls": [0.42, 0.39, 0.34],
    "loss_dfl": [0.91, 0.88, 0.83],
    "precision": [0.51, 0.62, 0.68],
    "recall": [0.43, 0.55, 0.61],
    "mAP50": [0.49, 0.58, 0.66],
    "mAP50_95": [0.21, 0.27, 0.34],
    "lr": [0.01, 0.0098, 0.0095],
    "epoch_time_seconds": [192, 185, 187]
  }
}
```

---

### 5.4 取消训练

```text
POST /api/v1/training/yolo-runs/{training_run_id}/cancel/
```

#### Response 200

```json
{
  "training_run_id": "uuid",
  "status": "cancelled",
  "message": "训练任务已取消，当前 checkpoint 已保留"
}
```

---

### 5.5 重试训练

```text
POST /api/v1/training/yolo-runs/{training_run_id}/retry/
```

#### Request

```json
{
  "mode": "from_scratch"
}
```

或

```json
{
  "mode": "from_checkpoint",
  "checkpoint_path": "/data/training_outputs/run_123/checkpoints/epoch_60.pt"
}
```

#### Response 200

```json
{
  "new_training_run_id": "uuid",
  "status": "queued",
  "message": "训练任务已重新加入队列"
}
```

---

### 5.6 下载权重

```text
GET /api/v1/training/yolo-runs/{training_run_id}/download/?artifact=pt
```

#### Query 参数
- `artifact=pt`
- `artifact=onnx`
- `artifact=torchscript`
- `artifact=last_pt`

#### Response
二进制文件流。

#### 错误响应

```json
{
  "error": {
    "code": "ARTIFACT_NOT_READY",
    "message": "请求的权重文件尚未生成"
  }
}
```

---

## 六、YOLO 训练 WebSocket 协议

当前系统已存在：
- `ws/training/<job_id>/`
- `TrainingConsumer`

这个基础是对的，但当前事件粒度还偏粗，需要针对 YOLO 扩充字段。

---

### 6.1 WebSocket 连接地址

```text
ws://host/ws/training/{training_run_id}/
```

### 6.2 连接确认消息

```json
{
  "event": "connected",
  "version": "1.0",
  "timestamp": "2026-06-05T23:45:00Z",
  "data": {
    "training_run_id": "uuid",
    "message": "Connected to YOLO training progress stream"
  }
}
```

---

### 6.3 训练启动消息

```json
{
  "event": "training_started",
  "version": "1.0",
  "timestamp": "2026-06-05T23:46:00Z",
  "data": {
    "training_run_id": "uuid",
    "status": "running",
    "gpu": {
      "name": "NVIDIA RTX 4090",
      "memory_total_mb": 24576
    },
    "config_summary": {
      "yolo_version": "v8",
      "model_variant": "n",
      "epochs": 100,
      "batch_size": 16,
      "image_size": 640
    }
  }
}
```

---

### 6.4 epoch 开始消息

```json
{
  "event": "epoch_start",
  "version": "1.0",
  "timestamp": "2026-06-05T23:47:00Z",
  "data": {
    "training_run_id": "uuid",
    "epoch": 12,
    "total_epochs": 100,
    "progress_percent": 12.0
  }
}
```

---

### 6.5 训练进度消息（主消息）

这个是前端动画、图表、ETA 的主数据源。

```json
{
  "event": "training_progress",
  "version": "1.0",
  "timestamp": "2026-06-05T23:48:00Z",
  "data": {
    "training_run_id": "uuid",
    "status": "running",
    "epoch": 12,
    "total_epochs": 100,
    "progress_percent": 12.0,
    "loss": {
      "box": 0.234,
      "cls": 0.067,
      "dfl": 0.089
    },
    "metrics": {
      "precision": 0.912,
      "recall": 0.887,
      "mAP50": 0.901,
      "mAP50_95": 0.678,
      "fitness": 0.891
    },
    "learning_rate": 0.000123,
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
      "eta_formatted": "约 1 小时 42 分钟",
      "estimated_completion_at": "2026-06-06T00:58:00Z"
    },
    "best": {
      "epoch": 11,
      "fitness": 0.891
    },
    "preview_samples": [
      {
        "image_url": "/media/training_previews/run_123/epoch_12_sample_1.jpg",
        "label": "helmet",
        "confidence": 0.97
      }
    ]
  }
}
```

---

### 6.6 epoch 完成消息

```json
{
  "event": "epoch_complete",
  "version": "1.0",
  "timestamp": "2026-06-05T23:49:00Z",
  "data": {
    "training_run_id": "uuid",
    "epoch": 12,
    "total_epochs": 100,
    "saved_checkpoint": true,
    "checkpoint_path": "/data/training_outputs/run_123/checkpoints/epoch_12.pt"
  }
}
```

---

### 6.7 训练完成消息

```json
{
  "event": "training_complete",
  "version": "1.0",
  "timestamp": "2026-06-06T00:58:00Z",
  "data": {
    "training_run_id": "uuid",
    "status": "completed",
    "artifacts": {
      "best_weight_path": "/data/training_outputs/run_123/weights/best.pt",
      "last_weight_path": "/data/training_outputs/run_123/weights/last.pt",
      "exported_artifacts": {
        "pt": "/data/training_outputs/run_123/weights/best.pt",
        "onnx": "/data/training_outputs/run_123/export/best.onnx"
      }
    },
    "final_metrics": {
      "precision": 0.923,
      "recall": 0.908,
      "mAP50": 0.934,
      "mAP50_95": 0.712,
      "fitness": 0.891
    },
    "duration_seconds": 3847,
    "next_actions": {
      "can_download": true,
      "can_generate_site": true,
      "recommended_project_name": "安全帽检测系统"
    }
  }
}
```

---

### 6.8 训练错误消息

```json
{
  "event": "training_error",
  "version": "1.0",
  "timestamp": "2026-06-05T23:52:00Z",
  "data": {
    "training_run_id": "uuid",
    "status": "failed",
    "error": {
      "code": "CUDA_OUT_OF_MEMORY",
      "message": "CUDA out of memory",
      "recoverable": true,
      "suggestion": "请降低 batch_size 到 8 或减小 image_size 到 512"
    }
  }
}
```

---

### 6.9 训练取消消息

```json
{
  "event": "training_cancelled",
  "version": "1.0",
  "timestamp": "2026-06-05T23:53:00Z",
  "data": {
    "training_run_id": "uuid",
    "status": "cancelled",
    "checkpoint_retained": true
  }
}
```

---

## 七、网站生成节点协议

当前系统已有 `GeneratedSite` 与 `website_generator.generate` action，但还不适合直接承接 YOLO 训练链路。

原因：
- 当前接口主吃 `model_path`
- 当前接口没有 `training_run_id`
- 当前接口没有“自动获取 labels”的强约束

所以需要一个 YOLO 专项入口，或者扩展现有生成接口。

---

### 7.1 工作流节点类型建议

```text
yolo_site_generator
```

---

### 7.2 节点配置 JSON

```json
{
  "type": "yolo_site_generator",
  "label": "生成安全帽检测网站",
  "config": {
    "source": {
      "mode": "training_run",
      "trainingRunId": "",
      "modelVersionId": "",
      "fallbackModelPath": ""
    },
    "site": {
      "projectName": "安全帽检测系统",
      "description": "基于 YOLOv8 的安全帽检测推理网站",
      "websiteType": "detection",
      "frontendFramework": "vue",
      "backendFramework": "flask",
      "port": 5000,
      "outputDir": ""
    },
    "deploy": {
      "deployOption": "local",
      "autoDeploy": false,
      "generateZip": true
    },
    "codegraph": {
      "autoAnalyze": true
    }
  }
}
```

---

### 7.3 节点输入解析优先级

节点应按以下优先级读取模型来源：

1. `config.source.trainingRunId`
2. 上游 `context.training_run_id`
3. `config.source.modelVersionId`
4. `config.source.fallbackModelPath`
5. 上游 `context.best_weight_path`

如果最终仍拿不到模型来源，必须失败。

---

### 7.4 节点成功输出

```json
{
  "success": true,
  "output": {
    "generated_site_id": "uuid",
    "generated_site_status": "generating",
    "generated_site_output_dir": "/data/generated_sites/site_123/",
    "generated_site_port": 5000,
    "generated_site_url": "http://localhost:5000",
    "project_name": "安全帽检测系统",
    "source_training_run_id": "uuid",
    "website_type": "detection",
    "frontend_framework": "vue",
    "backend_framework": "flask"
  }
}
```

---

## 八、网站生成 REST API 协议

建议新增 YOLO 专项便捷接口，而不是让前端去拼底层 `GeneratedSite` 字段。

### 8.1 从训练运行生成网站

```text
POST /api/v1/website-generator/yolo-generate/
```

#### Request

```json
{
  "training_run_id": "uuid",
  "project_name": "安全帽检测系统",
  "description": "基于 YOLOv8 的安全帽检测推理网站",
  "frontend_framework": "vue",
  "backend_framework": "flask",
  "port": 5000,
  "output_dir": "D:/GeneratedSites/helmet-system/",
  "auto_deploy": false,
  "generate_zip": true,
  "auto_create_project": true,
  "auto_codegraph": true
}
```

#### Response 201

```json
{
  "generated_site_id": "uuid",
  "status": "generating",
  "project_name": "安全帽检测系统",
  "website_type": "detection",
  "output_dir": "D:/GeneratedSites/helmet-system/",
  "message": "网站生成已开始"
}
```

---

### 8.2 获取生成网站详情

```text
GET /api/v1/website-generator/{generated_site_id}/
```

#### Response 200

```json
{
  "generated_site_id": "uuid",
  "name": "安全帽检测系统",
  "description": "基于 YOLOv8 的安全帽检测推理网站",
  "status": "completed",
  "website_type": "detection",
  "frontend_framework": "vue",
  "backend_framework": "flask",
  "output_dir": "D:/GeneratedSites/helmet-system/",
  "inference_endpoint": "http://localhost:5000/predict",
  "generated_files": [
    "frontend/index.html",
    "backend/app.py",
    "Dockerfile"
  ],
  "download_url": "/api/v1/website-generator/{id}/download/"
}
```

---

### 8.3 部署生成网站

```text
POST /api/v1/website-generator/{generated_site_id}/deploy/
```

#### Request

```json
{
  "mode": "local"
}
```

#### Response 200

```json
{
  "generated_site_id": "uuid",
  "status": "completed",
  "deployment": {
    "mode": "local",
    "site_url": "http://localhost:5000",
    "predict_endpoint": "http://localhost:5000/predict"
  }
}
```

---

## 九、项目创建协议

你要求左导航栏里出现生成的网站项目入口，所以必须有独立项目资源，而不能直接拿 `GeneratedSite` 硬顶。

原因：
- `GeneratedSite` 语义是“生成代码产物”
- 左导航项目语义是“平台中的长期业务对象”

这两者不是一个东西。

---

### 9.1 建议新增资源：`GeneratedProject`

### 9.2 创建项目接口

```text
POST /api/v1/projects/
```

#### Request

```json
{
  "name": "安全帽检测系统",
  "description": "基于 YOLOv8 的安全帽检测推理网站",
  "project_type": "yolo_detection",
  "source_training_run_id": "uuid",
  "generated_site_id": "uuid",
  "site_url": "http://localhost:5000",
  "model_artifact": {
    "artifact_type": "pt",
    "path": "D:/CustomerModels/helmet-system/best.pt"
  },
  "class_names": ["helmet", "no_helmet", "person"],
  "auto_add_to_nav": true
}
```

#### Response 201

```json
{
  "project_id": "uuid",
  "name": "安全帽检测系统",
  "project_type": "yolo_detection",
  "status": "active",
  "nav": {
    "slug": "helmet-detection-system",
    "label": "安全帽检测系统"
  },
  "site": {
    "url": "http://localhost:5000",
    "generated_site_id": "uuid"
  }
}
```

---

### 9.3 左导航接口建议

```text
GET /api/v1/projects/nav/
```

#### Response 200

```json
{
  "items": [
    {
      "project_id": "uuid",
      "label": "安全帽检测系统",
      "slug": "helmet-detection-system",
      "project_type": "yolo_detection",
      "status": "active"
    },
    {
      "project_id": "uuid2",
      "label": "车牌识别系统",
      "slug": "license-plate-recognition",
      "project_type": "yolo_detection",
      "status": "active"
    }
  ]
}
```

---

## 十、CodeGraph 解析协议

你要求“经允许进行 CodeGraph 的全面解析”，这里要明确成异步动作，不适合同步等待。

---

### 10.1 工作流节点类型建议

```text
codegraph_analyze
```

### 10.2 节点配置 JSON

```json
{
  "type": "codegraph_analyze",
  "label": "解析生成网站代码",
  "config": {
    "source": {
      "mode": "generated_site",
      "generatedSiteId": "",
      "projectId": "",
      "codeDir": ""
    },
    "analysis": {
      "includeFrontend": true,
      "includeBackend": true,
      "includeDependencies": true,
      "buildCallGraph": true,
      "buildRouteGraph": true,
      "buildComponentGraph": true
    }
  }
}
```

### 10.3 节点成功输出

```json
{
  "success": true,
  "output": {
    "codegraph_analysis_id": "uuid",
    "codegraph_status": "queued",
    "codegraph_report_url": "/api/v1/projects/project_uuid/codegraph/"
  }
}
```

---

### 10.4 REST 接口

```text
POST /api/v1/projects/{project_id}/codegraph/analyze/
GET  /api/v1/projects/{project_id}/codegraph/
```

#### `POST` Response 202

```json
{
  "analysis_id": "uuid",
  "status": "queued",
  "message": "CodeGraph 解析已开始"
}
```

#### `GET` Response 200

```json
{
  "analysis_id": "uuid",
  "status": "completed",
  "summary": {
    "backend_files": 8,
    "frontend_files": 12,
    "api_routes": 3,
    "components": 4,
    "issues": 2
  },
  "graphs": {
    "route_graph": {...},
    "component_graph": {...},
    "call_graph": {...}
  }
}
```

---

## 十一、前端契约：训练看板必须依赖哪些字段

前端训练面板不要自己发明字段，只能消费以下 WebSocket 字段。

### 11.1 顶部状态区
依赖：
- `data.status`
- `data.epoch`
- `data.total_epochs`
- `data.progress_percent`

### 11.2 指标卡片
依赖：
- `data.metrics.precision`
- `data.metrics.recall`
- `data.metrics.mAP50`
- `data.metrics.mAP50_95`
- `data.metrics.fitness`

### 11.3 Loss 曲线
依赖：
- `data.loss.box`
- `data.loss.cls`
- `data.loss.dfl`

### 11.4 GPU 卡片
依赖：
- `data.gpu.name`
- `data.gpu.memory_used_mb`
- `data.gpu.memory_total_mb`
- `data.gpu.utilization_percent`

### 11.5 ETA 区域
依赖：
- `data.timing.elapsed_seconds`
- `data.timing.eta_seconds`
- `data.timing.eta_formatted`
- `data.timing.estimated_completion_at`

### 11.6 验证样例区
依赖：
- `data.preview_samples[]`

---

## 十二、与当前代码直接冲突的地方

这里必须直接指出来，不然你会误以为现在的代码已经接近可用。

### 12.1 当前 `TrainingJob` 命名不够准确
它实际承担的是一次训练运行实例，更像 `TrainingRun`。

### 12.2 当前 WebSocket 路由参数叫 `job_id`
而训练主键、业务语义、前端心智更适合统一叫：
- `training_run_id`

建议未来兼容：
- 短期保留 `/ws/training/{job_id}/`
- 文档层统一写 `training_run_id`
- 后续逐步迁移

### 12.3 当前 `GeneratedSiteViewSet.get_queryset()` 直接全表
```python
return GeneratedSite.objects.all()
```

这是明显不够的。至少要加：
- tenant 过滤
- created_by / member 权限范围

### 12.4 当前网站生成接口主吃 `model_path`
这不利于治理。应升级为主吃 `training_run_id`。

---

## 十三、最终落地建议

这份协议文档定下来后，建议按下面顺序落地：

### 第一步：先做后端协议适配层
- 为 YOLO 训练新增专门 serializer / service
- 为网站生成新增 `yolo-generate` 接口
- 为项目创建新增 `GeneratedProject` 资源

### 第二步：补训练 WebSocket 字段
- 保留现有 `TrainingConsumer`
- 扩展 `training_progress` 消息体
- 把 ETA、GPU、loss、metrics 全补齐

### 第三步：前端严格按这份契约消费
- 不得在前端自行推断字段
- 不得混用 `job_id / run_id / training_id`

### 第四步：再做节点编排器适配
- `DatasetPrepare` → `yolo_training` → `yolo_site_generator` → `project_create` → `codegraph_analyze`

---

## 十四、最终判断

你选 A 是对的。因为现在继续谈业务已经没有增量了，真正会决定后续能不能落地的，是协议统一。

这份文档最重要的价值是三点：

1. **把节点配置写死**：以后不会再出现 YOLO 参数各写一套
2. **把 WebSocket 消息写死**：前端图表、动画、ETA 全有稳定输入
3. **把训练产物到网站生成的输入输出关系写死**：后续节点不会再靠硬编码路径瞎接

结论很直接：

> **下一步如果继续推进，就不该再写抽象文档，而应该开始按这份协议拆后端模型、serializer、service 和前端看板。**
