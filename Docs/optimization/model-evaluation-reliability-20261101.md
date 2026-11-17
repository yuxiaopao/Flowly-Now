# 模型评测可靠性与验证记录 · 2026-11-01

本文记录旧 `EvaluationJob` 域的本轮修复和真实验证边界。它评估已登记训练产物在标注数据上的分类 / 检测指标，与 [应用测试集和批量回归](application-regression-api-contract.md) 是两个领域。这里的通过不代表任意模型格式、云部署、模型质量或全平台所有功能均已完成。

## 已替换的假成功链路

旧评测在模型缺失、数据解析失败等情况下会退回随机 mock 指标，且列表缺少 owner 隔离。当前 `Backend/evaluation/evaluators.py` 已移除随机评测；HTTP 与 `LangChainService.run_model_evaluation_node` 都通过 `evaluation/services.py` 的同一真实 runner。模型、数据、适配器或指标不可用时持久化 `failed` 与错误代码，不生成假 accuracy，也不把空样本伪装成零分。

工作流接缝位于 `Backend/workflows/services/langchain_service.py::LangChainService.run_model_evaluation_node`，实际适配在 `Backend/evaluation/workflow.py`。节点 actor、workflow、node、execution 来自实际运行记录，优先读取引擎 `_execution.metadata` 并核验真实运行中的 `NodeExecution`；业务输入的 `metadata` 不能覆盖它。普通用户和团队场景均有真实数据库回归，不依赖超级用户绕过权限。

## 已登记资源与身份

模型先解析真实 `TrainingJob`，要求完成状态、当前管理权限和同一空间；选定文件必须匹配任务登记的 `model_path`、best / last 权重或允许的导出字段。默认受管产物目录为 `BASE_DIR/data/training_outputs`、`BASE_DIR/outputs`，可用 Django setting `EVALUATION_ARTIFACT_ROOTS` 明确配置。

标准任务目录必须属于该任务 UUID；自定义受管目录还须有真实已完成训练节点的输出证明。有关联执行的任务必须核对 workflow / node / execution、完成节点类型、`training_run_id`、actor 和 tenant。仅伪造一条 owner 相同记录，不能使任意主机文件成为可信产物。

数据可引用 `datasets.Dataset` 或 `training.Dataset`，必须是同一可管理空间的已登记本地数据；前者还要求 `ready`。默认根为 `MEDIA_ROOT/datasets`、`BASE_DIR/data/datasets`、`BASE_DIR/data/training_datasets`，配置接缝为 `EVALUATION_DATA_ROOTS`。拒绝受管根逃逸、符号链接 / Windows junction、缺失文件、超限数据及将他人文件或目录重新登记为自己的别名。旧 `model_path` / `test_dataset_path` 仅保留为已登记资源的兼容别名，不能作为任意文件读取入口。

权限分为读取和管理：个人评测仅 creator 可读写，超级用户可管理；活跃团队成员可读，owner / admin 可管理，普通 member 只能管理自己创建的评测和资源，viewer 不能创建 / 运行 / 编辑 / 删除。Worker 启动前、等待中及接受结果前重新检查账号、团队和资源权限；停用、撤销或来源变化会明确失败。历史无 owner 评测对普通用户隐藏，管理员可审计。

同时修复 `Backend/datasets/views.py::DatasetViewSet.get_queryset` 的个人数据泄露：个人数据限定 `created_by=actor AND tenant IS NULL`，团队数据限定可访问团队，保留超级用户管理规则。真实 HTTP 回归覆盖他人个人数据的 list / detail / preview / stats / download / edit / reprocess / delete 拒绝，且不会删除其原文件。

## 当前支持的真实产物

| 类型 | 支持条件 | 明确边界 |
| --- | --- | --- |
| 通用表格分类 | 已知 `TrainingRunner` MLP 结构，ZIP checkpoint 的 `model_state_dict` / `state_dict` 或 safetensors；架构参数匹配并严格加载；也接受已登记 `.torchscript` 分类导出 | CSV / JSON 必须有真实有限特征与标签；任意 Python 模型对象、未知网络结构不降级成 mock |
| CLIP 分类 | 真实 `.torchscript` 分类导出；完整 zero-shot tensor state 需可用 CLIP 适配器；finetune 分类头需匹配的真实基础编码器 | manifest / 说明清单没有权重时失败。基础编码器只使用摘要匹配的已准备缓存，不下载、不生成随机替代骨干 |
| YOLO | 已登记 `.torchscript` / `.onnx` 导出，或允许架构的纯 tensor state 重建；真实标注图像和本地 YAML / 目录 | 原始含可执行 Python 对象的 YOLO checkpoint 不使用不安全 pickle 回退；需要先导出受支持形式。分割 / 姿态 / 旋转框接缝存在，本轮真实 CPU 证据仅覆盖检测与分类，不能宣称其他任务已完成等价实测 |

普通 checkpoint 使用 `torch.load(..., weights_only=True)`，不使用 `weights_only=False` 或为未知对象增加安全白名单。TorchScript 必须使用已登记的明确导出类型，不能把它伪装成普通 `.pt`。这些准入措施不意味着任意来源 TorchScript / ONNX 或 tensor 文件本身构成安全沙箱，仍不能开放为不受信任文件执行服务。

图像分类读取真实类别目录及标注，拒绝未知类别、无样本和无效 logits。YOLO 读取真实图片和标注，校验本地路径、类别及样本，不允许运行 YAML 下载指令。分类指标为 `accuracy/precision/recall/f1/auc`，默认前四项；precision / recall / F1 按真实类别 support 加权，混淆矩阵和 `sample_count` 可追溯。AUC 使用真实概率，缺少必要正负样本时返回 `null`，不伪造 0。YOLO 非分类指标为 `precision/recall/mAP50/mAP50_95`；不适用指标明确拒绝。

## scaler、列顺序与训练闭环

原通用训练会标准化特征，但历史 checkpoint 没有完整记录 scaler，评测直接使用原始测试数值会产生错误结果。本轮精确调整通用 checkpoint 元数据，不改变训练算法：

- `Backend/training/tabular_artifacts.py` 定义 `flowly.tabular-preprocessing/v1`，记录标准化类型、mean、std、epsilon、feature_names 和 label_column。
- `Backend/training/training_runner.py` 与 canonical `Backend/scripts/train_model.py` 将这些字段写入 epoch、best、final 等通用产物；Desktop 同步脚本与生成副本已更新。本文没有声明 Desktop 最终打包结果。
- 评测优先使用训练记录的 scaler 和 feature 顺序。测试 CSV 列顺序改变时按训练列名映射；缺少训练列，即使列数相同也明确失败。显式 `features` 必须匹配记录的特征集合，含逗号的列名仍是一个数组元素。
- 旧产物确实训练过标准化但没有元数据时，只允许从同身份、已登记的原训练数据恢复统计量；原训练数据不可用则失败，**不能从测试集拟合 scaler**。无训练 schema 的旧模型按明确列配置或真实 CSV schema 推导，维度不匹配不能静默补齐。

CSV 的 label 选择顺序为显式 `label_column`、记录的训练 label、名为 `label` 的列、最后一列。`features` 省略或 `[]` 表示使用训练 schema 或推导所有非标签列；不是零特征输入。空值、NaN、无穷大、缺列、空样本均拒绝，不静默丢弃行。JSON 数据使用 `features` 二维数组和 `labels` 数组，可带 `feature_names` 供列映射。

真实闭环回归实际运行 `TrainingRunner` 的 CPU 训练：8 条带明显偏移的训练样本、25 个 epoch，保存 mean `[100, 0.5]` 与实际 std；用 4 条不同的 held-out 样本评测，并反转 CSV 特征列顺序。新元数据路径的 accuracy / F1 均为 1；去掉元数据后，从原训练集恢复 scaler 的旧产物路径仍为 1；替换为同宽但缺训练列的测试集则 HTTP 422、持久 `failed`、`metrics={}`。这证明训练与评测预处理接线正确，不是模型在通用数据上的质量保证。

## HTTP 与工作流契约

HTTP 基础路径为 `/api/v1/evaluations/`，详情查找值为服务端生成的 **`job_id`**，不是内部数据库 UUID。

| 方法 / 路径 | 行为 |
| --- | --- |
| GET / POST `/api/v1/evaluations/` | 按身份列出 / 创建评测 |
| GET / PUT / PATCH / DELETE `/api/v1/evaluations/{job_id}/` | 读取 / 更新 / 删除；运行中不能编辑或删除 |
| POST `/api/v1/evaluations/{job_id}/run/` | 使用已保存配置真实运行，正文为 `{}` |
| POST `/api/v1/evaluations/{job_id}/cancel/` | 取消 pending / running，清除 claim，不接受迟到结果 |

创建示例：

```json
{
  "name": "保留集分类评测",
  "training_job_id": "<TrainingJob UUID>",
  "dataset_id": "<datasets.Dataset UUID>",
  "parameters": {
    "label_column": "label",
    "features": ["x1", "x2"],
    "metrics": ["accuracy", "precision", "recall", "f1", "auc"]
  }
}
```

`dataset_id` 与 `training_dataset_id` 二选一，分别对应两个已存在的数据集域。参数另有 `split=test|val`、`image_size=8..1024`（默认 224）；未知参数拒绝。`created_by`、tenant、workflow 来源、状态、metrics、快照和 `job_id` 均由服务端维护。

工作流 UI 保持 camelCase：`trainingJobId`（兼容 `trainingRunId`）、`datasetId`、`trainingDatasetId`、`labelColumn`、`features`、`imageSize`、`split`、`metrics`。模型 ID 优先于上游 `training_run_id`；旧 `modelPath` 可匹配登记任务，所给路径仍须属于所选任务。显式数据集 ID 优先于旧 `testDataset` / 上游 `test_dataset` / `dataset_path`；没有选择时才尝试训练任务所登记的数据集。空白 UI `labelColumn` 被省略以启用自动选择；HTTP 显式非法参数仍会被校验。

创建不自动执行。`run/` 同步等待一个受限 CPU 子进程，持久状态依次为 `pending → running → completed|failed|cancelled`；没有把该旧域伪装成 Celery 批量系统。行锁与 claim token 防止并发重复运行；running / completed / cancelled 再直接 run 返回 409，失败可明确重试，已取消任务需编辑重置或新建。stale lease 被读取时恢复成 `failed/lease_expired`，不自动重放。

默认运行超时 300 秒、租约 330 秒；工作流总 deadline 可进一步缩短预算。相关配置为 `EVALUATION_TIMEOUT_SECONDS`、`EVALUATION_LEASE_SECONDS`，默认模型与数据上限各 512 MiB。取消、租约失效、权限撤销或父工作流停止后，以 `running + claim_token` 条件写入，迟到结果无法覆盖终态。

运行复制经授权文件到独立临时目录并计算摘要；`artifact_snapshot` 保留模型 / 数据哈希、资源 ID、actor / tenant / 执行来源，`metrics_history` 记录真实尝试。资源被合法删除后，历史审计仍保留；`verification_status=verified_source_removed` 明确说明当前关联已不存在。旧随机指标历史不被重新包装成可信证据，标记 `legacy_unverified`；新验证成功才标记 `verified`。

## 子进程与数据隐私边界

CPU 子进程不初始化 Django / 数据库，环境变量采用白名单，home / cache 指向自身临时目录，不继承云模型密钥、数据库连接和宿主模型缓存；仅复制受准入校验的模型、测试数据及必要的原训练数据 / 基础编码器。Python socket 网络入口被禁用，CUDA 可见设备为空，数值库线程设为 1；超时或取消会终止该子进程树。

这是受管来源准入、环境隔离、Python 层网络限制与生命周期控制，**不是操作系统容器或对任意恶意原生模型的完整安全沙箱**。不能据此向公网承诺“任意模型文件安全执行”。实际工作流 / HTTP 权限仍是第一层边界，整个宿主环境也没有因本轮测试而变成无漏洞环境。

## 迁移与真实验证

该旧域原本没有正式 migrations。新增 `evaluation/migrations/0001_initial.py` 的接管操作对已有 syncdb 表补齐历史基线，不删除原行；随后 `0002_evaluationjob_artifact_snapshot_and_more.py` 使用正式字段迁移添加 tenant、资源 / 执行关联、claim / lease、参数和快照。模型 / 数据 / 执行关联采用 `SET_NULL` 保留审计，tenant 采用 `PROTECT`。不要直接在业务库上试验迁移或用 fake 迁移掩盖结构不一致。

| 验证 | 结果与证据 |
| --- | --- |
| 评测、迁移、训练闭环、数据隐私、任务 / runtime paths 和旧执行器关联集 | **81 passed，49.53 秒，exit 0**；`.cache/evaluation-final-related.log` |
| 最后 fresh 团队权限、真实默认 queued dispatcher / 空 label、迁移与数据隐私增量 | **6 passed，12.04 秒，exit 0**；`.cache/evaluation-final-guard.log` |
| CLIP / YOLO 分类类型的真实 TorchScript CPU 推理 | **2 passed，16.22 秒，exit 0**；`.cache/evaluation-image-task-types.log`。使用受控小图像分类模型证明实际路由和评分，不代表完整预训练 CLIP 的质量验证 |
| YOLO 检测评分 | 真实微型 TorchScript 常量框模型、64px 图片及真实框标签，经 Ultralytics CPU val 得到 precision / recall / mAP 的实际结果；已包含在关联集。证明指标来自真推理和标注，不能外推真实业务模型精度 |
| 训练与 Desktop runtime helper | Node security / training-control **13 passed，exit 0**；`.cache/evaluation-desktop-helpers.log`；canonical 与生成脚本编译通过 |
| 真 fresh SQLite 迁移 | 私有临时 DB，`MIGRATION_MODULES={}`，实际 migrate、system check 与 evaluation / applications / training / datasets `makemigrations --check` 均通过；`.cache/evaluation-fresh-migrate.log` |
| RAG 发布证据关联一致性 | **109 passed，16.34 秒，exit 0**；`.cache/rag-content-final.log`。独立隔离 MySQL 集合 **16 passed，55.50 秒，exit 0**，其中包含 6 个 RAG 锁测试；`.cache/continuation-mysql-final-20261101.log` |
| 移除部署假成功及应用关联回归 | 新增 14 项先红后绿；部署、原工作流校验及 App 生命周期 / readiness / 批次关联集 **95 passed、4 subtests passed，29.98 秒，exit 0**；`.cache/deployment-unavailable-red.log`、`.cache/deployment-unavailable-final.log` |

恶意 pickle 未执行、受管根 / junction 拒绝、跨 owner / tenant 路径拒绝、真实失败持久化、取消与 stale 迟到结果、真实工作流 dispatcher 及原训练 schema 闭环，分别见 `tests/backend/test_evaluation_security.py`、`test_evaluation_training_roundtrip.py`、`test_evaluation_migrations.py`、`test_dataset_owner_isolation.py`。各集合重叠，不相加计作总数。最新完整后端和 Chrome / Docker 最终结果由本轮总交付记录另行汇总，本文不提前认定通过。

部署回归随后增加真实 `available_types` 能力列表断言，最后一次定向复跑为 **13 passed、1 failed**：失败发生在导入 `langchain_core.messages`，Windows 返回 `WinError 8` 内存不足，日志 `.cache/deployment-unavailable-capabilities.log`。没有因此删除断言或放宽检查；主代理将调配资源后统一执行包含该增量的完整后端回归，本文不把这次环境失败写成通过。

## 明确保留的未完成项

`Backend/workflows/services/langchain_service.py::LangChainService.run_model_deployment_node` 的四平台 **假成功已移除，真实部署适配器仍未实现**。local / SageMaker / LambdaGPU / Triton 的既有配置完整保留，直接调用统一返回 `success=false`、`error_type=deployment_not_configured`；未知或畸形平台返回 `unsupported_platform`。消息与平台常量集中在 `Backend/workflows/services/model_deployment.py`。不再生成伪 URL、hash 资源名或 `running` 状态，也不会因为安装了 SDK 就假定已经部署。

`Backend/workflows/services/workflow_validation.py::UNIMPLEMENTED_INTEGRATIONS` 已加入 `model_deployment`。真实工作流执行前检查、App readiness 与试跑会明确阻止此节点，失败试跑不能成为发布依据。`tests/backend/workflows/test_model_deployment_unavailable.py` 覆盖四平台直接方法、未知 / 畸形值、默认 local，以及四平台真实 HTTP validate / execute / readiness / test / publish 的拒绝链。评测成功与模型部署成功仍是不同事实。

真实 local serving 后续至少需要复用受授权 artifact / schema / scaler 解析，持久 deployment 状态和进程身份，配置监听地址与鉴权，实际 health 与预测通过后才置 ready，并实现停止、失败清理及重启恢复。云平台需真实 provider create / query / stop 及服务端返回的资源 ID；当前适配器未接入时已经明确失败。本轮没有发起云资源、支付或外部部署。

没有安装或替换 GPU 栈，也没有执行 GPU 长训练。宿主保留 torch `2.10.0+cu128`、torchvision `0.25.0+cu128`、transformers `5.8.1` 与 CUDA `12.8`；既有两个 Torch advisories 的限制仍需单独管理，不能将 CPU 定向测试或其他依赖修复表述为“整个宿主环境零漏洞”。
