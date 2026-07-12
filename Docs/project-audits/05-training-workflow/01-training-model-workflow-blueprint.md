# Training Model Workflow Blueprint

> 文档目的：基于 Flowly 当前代码现状，设计一套完整的训练模型业务闭环。  
> 重点不是只讲“怎么发起训练”，而是把 **数据准备 → 训练配置 → 异步执行 → 评估验收 → 模型版本化 → 发布部署 → 工作流消费 → 观测治理** 全部串起来。  
> 这份文档的目标是让你后续可以直接按它拆需求、拆模型、拆页面、拆接口、拆任务执行链路。

---

## 一、先说结论

如果你真想把“训练模型”做成完整业务，而不是一个 demo 级按钮，你要的不是单个 `TrainingJob`，而是一整套 **训练资产闭环**。

当前代码里已经有一些基础：

- `Backend/training/models.py` 里已经有 `TrainingJob`
- `Backend/evaluation/models.py` 里已经有 `EvaluationJob`
- `Backend/workflows/services/langchain_service.py` 里已经有 `model_training` 与 `model_evaluation` 节点
- `Backend/datasets` 已经有通用数据集域
- `Backend/workflows` 已经有异步执行、执行观测、checkpoint 基础能力

但这些能力现在还是散的，没有形成完整业务链。

### 最终你真正需要的主线

> **数据集准备 → 数据质检/切分 → 训练任务创建 → 训练执行 → 指标回传 → 模型版本产出 → 评估验收 → 发布为可用模型 → 工作流/Agent/RAG 消费 → 线上观测与迭代重训**

如果没有这条闭环，训练功能只会停留在：
- 能提交一个任务
- 跑完吐一个文件路径
- 但不知道这个模型算不算可上线资产

这不够。

---

## 二、先看当前代码的真实基础与真实缺口

这部分必须客观，不然方案会脱离代码现状。

### 2.1 已有基础

#### 训练任务基础已经存在
`Backend/training/models.py` 中已有：
- `TrainingJob`
- 训练状态、框架、模型类型
- 训练进度、epoch、loss、metric、metrics_history
- `workflow` / `node` / `execution` 关联
- `tenant` / `created_by` 关联
- `dataset_path` / `model_path`

这说明项目已经具备“把训练作为 workflow 节点异步执行任务”的基础骨架。

#### 评估任务基础已经存在
`Backend/evaluation/models.py` 中已有：
- `EvaluationJob`
- `model_path`
- `test_dataset_path`
- `metrics`
- `metrics_history`

这说明训练后接评估，不是从零开始。

#### workflow 执行器已预埋训练节点
在 `Backend/workflows/services/langchain_service.py` 里已经有：
- `run_model_training_node()`
- `run_model_evaluation_node()`

而且 `run_model_training_node()` 已经尝试：
- 读训练配置
- 生成 config 文件
- 创建 `TrainingJob`
- 异步分发 Celery 训练任务

这说明你的系统方向本来就是：

> **训练不是独立工具页，而是工作流平台中的一个 MLOps 节点能力。**

这点是对的，应该保留。

---

### 2.2 当前真实缺口

#### 缺口 1：训练数据集域重复建设
当前有两套 Dataset：

- `Backend/datasets/models.py` 的通用 `Dataset`
- `Backend/training/models.py` 的训练专用 `Dataset`

这是重复建设。

后果很直接：
- 数据集元数据不统一
- tenant 边界会分裂
- 前端会有两套上传入口
- 训练链路和数据治理链路永远打不通

#### 缺口 2：训练产物还不是“模型资产”
现在 `TrainingJob` 最终只落一个：
- `model_path`

这只是文件路径，不是正式资产。缺少：
- 模型注册
- 模型版本
- 模型状态
- 模型来源
- 可部署性状态
- 可消费协议

#### 缺口 3：评估没有绑定模型版本
当前 `EvaluationJob` 主要绑定：
- `model_path`
- `test_dataset_path`

这意味着评估还是文件级，不是资产级。

后果：
- 无法明确评估的是哪个版本
- 无法沉淀模型版本历史
- 无法形成“发布前门禁”

#### 缺口 4：训练与资源中心未打通
训练本身依赖：
- 基础模型
- GPU / runtime
- 凭证
- 数据集
- 向量库 / embedding（部分场景）
- 存储路径

但当前系统里这些依赖散在：
- `gateway`
- `training`
- `datasets`
- `rag`
- `workflows`

还没有统一 preflight 检测。

#### 缺口 5：训练观测不完整
虽然 `TrainingJob` 有进度和 metrics_history，`WorkflowExecution` 也有执行观测基础，但还缺：
- 训练阶段时间线
- checkpoint 记录
- GPU/显存使用记录
- dataset version 对应关系
- 失败原因归类
- 成本累计

#### 缺口 6：租户/团队权限还不稳
训练往往比普通 workflow 更敏感，因为它会消耗：
- GPU
- 存储
- 预算
- 团队数据
- 团队模型资产

如果继续使用松散 owner-only 权限，这块一定失控。

---

## 三、先定义你到底要做的“训练模型工作流”是什么

这里必须先定业务范围，否则方案会漂。

我建议你把训练能力先收敛成下面四类场景。

---

## 3.1 场景 A：监督微调 / 文本分类训练
最适合当前系统先落地。

### 输入
- 标注好的数据集
- 任务类型（分类、回归、生成）
- 基础模型
- 超参数

### 输出
- 训练后的模型版本
- 评估指标
- 训练报告

### 为什么优先做这个
因为它最符合你当前已有能力：
- dataset
- annotation / augmentation
- training job
- evaluation job

这是最自然的一条闭环。

---

## 3.2 场景 B：提示词/轻量参数优化
适合做低成本训练变体。

### 输入
- prompts
- few-shot examples
- evaluation set

### 输出
- 优化后的 prompt version / adapter version
- 离线评估结果

### 价值
这能把“训练”扩展到更轻量的 AI 优化场景，不只局限于传统 ML。

---

## 3.3 场景 C：RAG 知识增强型训练
适用于需要把文档、知识库、向量检索结合起来的场景。

### 输入
- 文档集合 / dataset
- embedding 方案
- 检索配置
- rerank 配置
- 评估集

### 输出
- 检索配置版本
- 知识增强报告
- 召回/准确率/答案质量结果

### 结论
这个场景不是纯训练，但业务上属于“模型优化工作流”，应该纳入训练专题边界。

---

## 3.4 场景 D：工作流内嵌训练节点
这是 Flowly 最有差异化的地方。

### 形态
训练不是独立后台，而是工作流里的一个节点：
- 数据准备节点
- 训练节点
- 评估节点
- 发布节点

### 价值
这意味着用户可以把训练流程本身自动化：
- 定时拉数据
- 自动增广
- 自动训练
- 自动评估
- 满足阈值后自动发布

这个能力如果打通，会非常强。

---

## 四、完整业务闭环设计

下面是你真正需要的一条完整链路。

---

## 4.1 Step 1：训练项目创建

训练不应该直接从 `TrainingJob` 开始，而应该先有一个更高层对象：

### 建议新增领域对象：`TrainingProject`

```text
TrainingProject
- id
- tenant_id
- owner_id
- name
- description
- task_type              # classification / regression / generation / rag-optimization
- base_model_id          # 来源模型
- status                 # draft / ready / training / evaluating / approved / published / archived
- latest_dataset_version_id
- latest_model_version_id
- latest_evaluation_id
- visibility
- created_at
- updated_at
```

### 为什么必须有这个对象
因为 `TrainingJob` 只是一次运行记录，不应该承担这些职责：
- 管理项目目标
- 管理长期配置
- 管理模型谱系
- 管理多个训练版本
- 管理审批发布

没有 `TrainingProject`，你后面所有版本历史都会乱。

---

## 4.2 Step 2：数据集准备

训练链路的第二步不是点训练，而是把数据准备成可训练资产。

### 建议统一为一个数据资产域
不要保留 `training.Dataset` 和 `datasets.Dataset` 两套体系。

### 正确方向
- 统一主数据集域到 `Backend/datasets`
- 训练域不再维护独立 Dataset 主模型
- 训练项目只引用数据集版本

### 建议新增：`DatasetVersion`

```text
DatasetVersion
- id
- dataset_id
- version_number
- source_snapshot
- schema_snapshot
- row_count
- label_distribution
- split_strategy
- train_ratio
- val_ratio
- test_ratio
- quality_report
- created_by
- created_at
```

### 训练前数据准备动作
你要把这些做成明确步骤：

1. 上传或导入数据集
2. 自动识别 schema
3. 校验标签字段、特征字段、空值、脏数据
4. 可选接标注与增强流程
5. 生成 train/val/test split
6. 固化为 `DatasetVersion`
7. 锁定用于训练的版本

### 为什么必须版本化
否则：
- 你无法复现训练结果
- 你不知道评估是不是用同一套数据
- 训练失败后无法定位是不是数据变了

---

## 4.3 Step 3：训练配置确认

训练任务的创建，不应该直接传一堆 JSON，而应通过结构化配置对象。

### 建议新增：`TrainingRunConfig`

```text
TrainingRunConfig
- id
- training_project_id
- dataset_version_id
- base_model_id
- framework
- runtime_profile_id
- hyperparameters
- resource_requirements
- early_stopping_config
- checkpoint_config
- output_artifact_config
- evaluation_plan
- preflight_result
- created_by
- created_at
```

### 核心配置项

#### 模型相关
- base model
- tokenizer
- model family
- parameter-efficient tuning / full fine-tune

#### 数据相关
- dataset version
- label mapping
- field mapping
- split strategy

#### 训练相关
- epochs
- batch size
- learning rate
- optimizer
- scheduler
- warmup
- weight decay
- gradient accumulation
- max sequence length

#### 资源相关
- cpu / memory / gpu profile
- runtime image
- storage quota
- output dir

#### checkpoint 相关
- save every N epoch
- best metric monitor
- auto resume

#### 评估相关
- evaluation dataset version
- metrics list
- threshold gate

### 强制要求：训练前必须做 preflight
不能让任务直接进队列。

preflight 至少检查：
- dataset 是否 ready
- split 是否齐全
- base model 是否存在
- credential 是否可用
- runtime profile 是否可用
- tenant quota 是否足够
- output 存储是否可写
- evaluation 配置是否完整

---

## 4.4 Step 4：发起训练运行

这里才轮到 `TrainingJob`。

### 正确认知
`TrainingJob` 应该改名理解成：

> **TrainingRun：一次实际训练执行实例**

如果你不想立即改名，至少业务语义上要这么认知。

### 建议的运行对象模型

```text
TrainingRun
- id
- training_project_id
- training_run_config_id
- workflow_execution_id
- source_node_execution_id
- status
- queue_info
- runtime_info
- progress
- current_epoch
- current_step
- current_loss
- current_metric
- gpu_usage
- memory_usage
- metrics_history
- error_message
- started_at
- completed_at
```

### 为什么要关联 workflow execution
因为你的平台主线不是独立 MLOps 面板，而是工作流平台。训练运行必须能回到：
- 哪个 workflow 触发的
- 哪个节点触发的
- 哪次 execution 触发的

这点你当前 `TrainingJob` 已经部分具备，是对的，要强化而不是删掉。

---

## 4.5 Step 5：训练执行过程

训练执行不是黑盒跑完就算数，应该被拆成明确阶段。

### 建议训练运行状态机

```text
draft
→ queued
→ provisioning
→ preparing_data
→ training
→ validating
→ packaging
→ completed

异常分支：
- failed
- cancelled
- timeout
- blocked
```

### 当前问题
现在 `TrainingJob.STATUS_CHOICES` 只有：
- queued
- running
- completed
- failed
- cancelled

这太粗了，无法表达训练阶段。

### 为什么要拆阶段
因为训练出问题不只是“失败”，而是会失败在：
- 资源申请
- 数据读取
- checkpoint 恢复
- epoch 训练
- validation
- artifact 打包

你需要明确知道失败点。

---

## 4.6 Step 6：训练产物落库

训练结束后，不能只留下一个 `model_path`，必须产出正式模型资产。

### 建议新增：`ModelRegistry`

```text
ModelRegistry
- id
- tenant_id
- owner_id
- name
- description
- model_family
- task_type
- source_type           # official / imported / trained / external
- visibility
- current_published_version_id
- created_at
- updated_at
```

### 建议新增：`ModelVersion`

```text
ModelVersion
- id
- registry_id
- version_number
- training_project_id
- training_run_id
- base_model_id
- dataset_version_id
- artifact_path
- config_snapshot
- metrics_snapshot
- evaluation_summary
- status                # draft / evaluated / approved / published / deprecated / archived
- checksum
- model_size
- created_by
- created_at
```

### 训练成功后的标准输出
1. 生成 artifact 文件
2. 生成 config snapshot
3. 生成 metrics snapshot
4. 创建 `ModelVersion`
5. 绑定回 `TrainingProject.latest_model_version_id`

### 这样做的意义
你得到的不是一个“文件路径”，而是一个真正可管理的模型资产版本。

---

## 4.7 Step 7：评估验收

评估不应该只是顺手跑一下，而应该是训练闭环里的正式门禁。

### 当前已有基础
`EvaluationJob` 已存在，但太轻。

### 建议升级语义
`EvaluationJob` 应明确绑定：
- `model_version_id`
- `dataset_version_id`
- `evaluation_suite_id`

### 建议新增：`EvaluationSuite`

```text
EvaluationSuite
- id
- name
- task_type
- metrics
- thresholds
- sample_strategy
- report_template
```

### 评估阶段至少输出
- accuracy / precision / recall / f1 / auc（分类场景）
- rouge / bleu / bertscore（生成场景）
- latency
- inference cost
- robustness report
- failure cases
- confusion matrix / sample predictions

### 评估门禁规则
定义上线门槛，例如：
- `val_f1 >= 0.86`
- `latency_p95 <= 1200ms`
- `first_pass_rate >= 90%`

不满足则：
- 允许存档版本
- 不允许发布上线

---

## 4.8 Step 8：审批与发布

这是很多系统缺失的一环，但如果你有 tenant 和团队协作，这步必须有。

### 建议模型版本状态机

```text
draft
→ evaluated
→ pending_approval
→ approved
→ published
→ deprecated
→ archived
```

### 为什么需要审批
因为团队场景下，训练结果不是谁训练完谁就能直接上线。

尤其涉及：
- 团队共享模型
- 高成本模型
- 对外服务模型
- 有合规要求的数据场景

### 审批主体
- owner：可以发起申请
- tenant admin / mlops admin：可以审批
- superuser：可强制发布 / 回滚

---

## 4.9 Step 9：部署与消费

训练出来的模型最终要被谁用，这是闭环的关键。

### 消费入口至少三种

#### 入口 A：workflow 节点消费
工作流里的 LLM / model 节点可以选择：
- 官方模型
- 外部 provider 模型
- 本租户训练模型版本

#### 入口 B：Agent 消费
Agent 的 `model` 字段不能只写字符串，应能引用：
- external model key
- model registry version id

#### 入口 C：API / 推理服务消费
如果后续有推理 API，应该支持：
- 通过 `model_version_id` 调用
- 自动路由到已发布版本

### 关键要求
训练模型不能停留在“下载文件”。

它必须成为平台资源中心里一个标准可消费对象。

---

## 五、完整页面与交互流程

如果你要落地，这里是前端应该具备的页面闭环。

---

## 5.1 训练项目列表页

### 目标
让用户看到所有训练项目，而不是直接看原始 job。

### 关键字段
- 项目名
- 任务类型
- 基础模型
- 最新数据版本
- 最新模型版本
- 最近训练状态
- 最近评估结果
- 所属 tenant
- 最近更新时间

### 关键操作
- 新建训练项目
- 查看详情
- 复制配置
- 发起训练
- 查看版本历史
- 查看评估记录

---

## 5.2 数据准备页

### 功能
- 上传/导入数据集
- schema 检查
- 标签映射
- train/val/test split
- 脏数据提示
- 样本预览
- 数据版本生成

### 必须有的反馈
- 行数/字段数
- 标签分布
- 缺失值
- 类别不平衡告警
- 重复样本提示
- 建议 batch size / epoch 初始值

---

## 5.3 训练配置页

### 功能
- 选择 base model
- 选择数据集版本
- 配置超参数
- 配置运行资源
- 配置 checkpoint
- 配置评估方案
- 运行 preflight

### 必须有的体验
- 参数模板（初学者 / 标准 / 高精度 / 低成本）
- 资源成本预估
- 预计训练时长
- quota 预警

---

## 5.4 训练运行详情页

### 功能
- 查看运行时间线
- 实时进度
- epoch / step 曲线
- loss / metric 曲线
- GPU/内存使用
- 日志输出
- checkpoint 列表
- 取消 / 重试 / 从 checkpoint 恢复

### 注意
这页应当与前面设计的 execution observability 对齐，而不是另起一套日志系统。

---

## 5.5 模型版本详情页

### 功能
- 版本信息
- 来源项目
- 来源数据集版本
- 训练配置快照
- 评估报告
- 发布状态
- 使用量与成功率
- 回滚到旧版本

---

## 5.6 发布审批页

### 功能
- 待审批版本列表
- 指标达标情况
- 风险项提示
- 审批意见
- 发布/驳回

---

## 六、接口设计建议

下面给你一套更完整的 API 形态，不是最终代码，但能直接指导后端拆分。

---

## 6.1 训练项目域

```text
GET    /api/v1/training/projects/
POST   /api/v1/training/projects/
GET    /api/v1/training/projects/{id}/
PATCH  /api/v1/training/projects/{id}/
GET    /api/v1/training/projects/{id}/versions/
POST   /api/v1/training/projects/{id}/clone/
```

---

## 6.2 数据准备域

```text
GET    /api/v1/datasets/
POST   /api/v1/datasets/
GET    /api/v1/datasets/{id}/preview/
POST   /api/v1/datasets/{id}/validate/
POST   /api/v1/datasets/{id}/split/
POST   /api/v1/datasets/{id}/versions/
GET    /api/v1/dataset-versions/{id}/
```

---

## 6.3 训练运行域

```text
GET    /api/v1/training/runs/
POST   /api/v1/training/runs/
GET    /api/v1/training/runs/{id}/
POST   /api/v1/training/runs/{id}/cancel/
POST   /api/v1/training/runs/{id}/retry/
POST   /api/v1/training/runs/{id}/resume-from-checkpoint/
GET    /api/v1/training/runs/{id}/timeline/
GET    /api/v1/training/runs/{id}/metrics-history/
GET    /api/v1/training/runs/{id}/logs/
```

---

## 6.4 模型注册域

```text
GET    /api/v1/model-registries/
POST   /api/v1/model-registries/
GET    /api/v1/model-registries/{id}/
GET    /api/v1/model-registries/{id}/versions/
GET    /api/v1/model-versions/{id}/
POST   /api/v1/model-versions/{id}/publish/
POST   /api/v1/model-versions/{id}/deprecate/
POST   /api/v1/model-registries/{id}/rollback/
```

---

## 6.5 评估域

```text
GET    /api/v1/evaluations/
POST   /api/v1/evaluations/
GET    /api/v1/evaluations/{id}/
GET    /api/v1/evaluations/{id}/report/
POST   /api/v1/evaluations/{id}/approve/
POST   /api/v1/evaluations/{id}/reject/
```

---

## 七、数据模型建议总表

这里直接给你一个建议模型清单，便于后面拆库表。

### 已有但应升级
- `TrainingJob` → 语义升级为 `TrainingRun`
- `EvaluationJob` → 绑定模型版本与数据集版本
- `datasets.Dataset` → 成为统一数据资产主模型

### 建议新增
- `TrainingProject`
- `DatasetVersion`
- `TrainingRunConfig`
- `ModelRegistry`
- `ModelVersion`
- `EvaluationSuite`
- `TrainingCheckpoint`
- `TrainingArtifact`
- `DeploymentTarget`（如果要做部署）
- `TrainingApprovalRecord`

---

## 八、状态机设计

### 8.1 TrainingProject 状态
```text
draft
→ ready
→ training
→ evaluating
→ approved
→ published
→ archived
```

### 8.2 TrainingRun 状态
```text
queued
→ provisioning
→ preparing_data
→ training
→ validating
→ packaging
→ completed

异常：
failed / cancelled / timeout / blocked
```

### 8.3 ModelVersion 状态
```text
draft
→ evaluated
→ pending_approval
→ approved
→ published
→ deprecated
→ archived
```

### 8.4 EvaluationJob 状态
```text
pending
→ running
→ completed
→ failed
```

---

## 九、和现有业务域怎么打通

这部分最关键，因为你明确说了：**依旧以目前代码情况来看**。

所以我不讲空中楼阁，直接说怎么和现有系统对齐。

---

## 9.1 和 workflow domain 打通

### 当前基础
`TrainingJob` 已有关联：
- `workflow`
- `node`
- `execution`

### 正确方向
保留这个设计，但加强：
- `TrainingRun` 是 `WorkflowExecution` 的子链路
- `NodeExecution` 里应能看到 training_run_id
- execution timeline 里应嵌入训练阶段事件

### 结果
这样用户在执行详情页里，可以看到：
- 训练节点启动
- 训练任务入队
- 训练中 epoch 进度
- checkpoint 保存
- 评估节点执行
- 发布节点执行

---

## 9.2 和 datasets domain 打通

### 当前问题
`training.models.Dataset` 与 `datasets.models.Dataset` 平行存在。

### 结论
这两套不能长期并存。

### 正确方向
- `datasets.Dataset` 做唯一主数据集资源
- `training` 域通过 `DatasetVersion` 或 dataset snapshot 引用
- 原 `training.Dataset` 逐步降级为兼容层或迁移对象

---

## 9.3 和 resource / credential domain 打通

训练依赖：
- 基础模型来源
- 第三方 provider key
- 存储 bucket
- 计算 runtime

这些不应在训练域自己乱管。

### 正确方向
训练域只引用统一资源中心里的：
- base model
- credential
- runtime profile
- storage target

---

## 9.4 和 execution observability 打通

训练不是独立观测岛。

### 你应复用前面那套 execution observability 思路
- training run timeline
- logs
- metrics_history
- cost tracking
- retry chain
- checkpoint record

不要再单做一套观测协议。

---

## 9.5 和 tenant/access 打通

### 关键原则
- `TrainingProject` 属于 tenant
- `DatasetVersion` 属于 tenant
- `ModelRegistry` 属于 tenant
- `ModelVersion` 属于 tenant

### owner 只负责归责，不负责边界
否则团队训练模型永远做不稳。

### 角色权限建议
- owner/admin：可创建项目、发起训练、审批发布
- member：可创建训练 run、查看项目、提交评估
- viewer：只读查看，不可发起高成本训练

---

## 十、训练工作流的标准业务流程图（文字版）

```text
1. 创建 TrainingProject
2. 选择/创建 Dataset
3. 运行数据校验
4. 生成 DatasetVersion
5. 选择 BaseModel + RuntimeProfile
6. 配置 Hyperparameters + Checkpoint + EvaluationPlan
7. 执行 Preflight
8. 创建 TrainingRun
9. Celery / Worker 异步执行训练
10. 周期性回写 progress / epoch / loss / metrics_history
11. 输出 artifact + config snapshot
12. 创建 ModelVersion
13. 自动或手动创建 EvaluationJob
14. 评估通过 → 状态变为 evaluated / pending_approval
15. 审批通过 → published
16. Workflow / Agent / API 开始消费该模型版本
17. 线上观测结果回流，触发下一轮重训
```

---

## 十一、用户真正关心的细节：你必须补齐的业务点

你说要“完整思路和细节”，那这些细节不能省。

### 11.1 数据质量门禁
训练前必须自动提示：
- 标签缺失率
- 类别不平衡
- 数据泄漏风险
- 文本长度分布
- 重复样本率
- train/test 污染风险

### 11.2 成本预估
训练前必须给：
- 预计 GPU 时长
- 预计 token / compute cost
- 租户预算占比

### 11.3 失败恢复
训练失败后必须支持：
- 从头重跑
- 从 checkpoint 恢复
- 只重跑评估
- 复制旧配置再跑

### 11.4 版本可回滚
模型发布后必须支持：
- 切回旧版本
- 标记 bad version
- 回滚原因记录

### 11.5 线上反馈闭环
模型上线后必须持续收集：
- 调用量
- 成功率
- 响应时间
- 用户反馈
- bad case 样本

这些数据最终应反哺下一轮训练。

---

## 十二、按当前代码情况，最合理的落地顺序

不要一次性全做。现在的代码基础不允许你一口吃成胖子。

### Phase 1：先把训练跑通并接入主链路
1. 停止新增训练域重复数据模型
2. 统一训练输入改为引用 `datasets` 域
3. 保留 `TrainingJob`，但明确它是 `TrainingRun`
4. 补 workflow execution ↔ training job 时间线关联
5. 补训练详情页与 metrics_history 展示

### Phase 2：再建立模型资产层
1. 新增 `TrainingProject`
2. 新增 `ModelRegistry` / `ModelVersion`
3. 训练完成自动注册模型版本
4. 评估绑定模型版本

### Phase 3：再做审批与发布
1. 模型版本状态机
2. 审批流
3. 发布与回滚
4. tenant 权限与预算控制

### Phase 4：最后再做自动化重训闭环
1. 定时训练 workflow
2. 新数据触发重训
3. 指标回退自动告警
4. 模型健康分

---

## 十三、最终判断

你要的“完整训练模型工作流”，本质上不是一个页面，也不是一个 Celery 任务，而是一个 **模型资产生产系统**。

如果只停留在当前 `TrainingJob + model_path` 这层，你最多只能说：
- 系统能提交训练任务

但还不能说：
- 系统具备完整训练模型业务闭环

### 真正完整的闭环必须满足这五件事
1. **数据可版本化**：知道用哪份数据训练
2. **训练可复现**：知道用哪套配置、哪次运行产出了模型
3. **模型可注册**：训练结果不是文件，而是正式资产版本
4. **评估可门禁**：知道模型是否达标、是否允许上线
5. **上线可消费可回流**：workflow、agent、API 能用，线上指标能反哺下一轮训练

这五件事缺任何一个，你的训练链路都不完整。

所以最直接的建议是：

> **先把训练域从“任务执行”升级为“模型资产闭环”，再考虑做更复杂的 MLOps 花活。**

不然你后面做得越多，返工越大。
