# YOLO 实施落地计划

> 文档目的：基于当前 Flowly 代码现状，把前面 4 份训练专题文档收敛成一份 **可执行的实施路线图**。  
> 这份文档不再新增业务概念，而是回答三个问题：  
> 1. 先改什么，后改什么。  
> 2. 每一阶段具体落在哪些文件、哪些模块、哪些接口。  
> 3. 什么叫做这一阶段真正完成，而不是“写了一半”。

---

## 一、先说结论：这件事不能一口气大改，必须四段推进

你现在已经有：
- 训练模型总蓝图
- YOLO 训练到建站的专项闭环
- 节点/API/WebSocket 契约
- 前端实时看板规范

接下来如果直接“全面开干”，很容易翻车。原因很简单：
- 当前 `training` app 还是通用训练设计
- 当前前端训练页还是通用训练页
- 当前网站生成器虽然能用，但没接 `training_run_id`
- 当前项目资源模型还没有真正建立

所以正确打法不是“重构所有模块”，而是：

> **先把 YOLO 训练这条主链跑通，再把建站、项目化、CodeGraph 挂上去。**

我建议拆成 4 个阶段：

### Phase 1：YOLO 训练后端打底
目标：真正能创建 YOLO 训练运行、推送训练进度、下载权重。

### Phase 2：YOLO 实时训练前端打底
目标：真正能看到实时训练看板、图表、ETA、断线重连。

### Phase 3：训练完成后的网站生成与项目化
目标：真正把 `best.pt` 用起来，生成识别网站并挂到左导航。

### Phase 4：CodeGraph 和全链路收尾
目标：让生成项目具备代码解析、质量报告、回归验收。

---

## 二、当前代码现状与真实阻塞点

这里必须直说，不然实施顺序会失真。

### 2.1 当前 `training` 路由和 serializer 都是通用型
当前：
- `Backend/training/urls.py`
- `Backend/training/serializers.py`
- `Backend/training/views.py`

都只围绕：
- `training-jobs`
- 通用 `TrainingJob`
- 通用 `config`

这意味着：
- 没有 `yolo-runs` 资源
- 没有 YOLO 专属 serializer
- 没有 YOLO 的 metrics/history 结构

### 2.2 当前 WebSocket 已有，但消息体不够细
当前：
- `Backend/training/routing.py`
- `Backend/training/consumers.py`

已经支持：
- `training_started`
- `epoch_start`
- `epoch_complete`
- `training_progress`
- `training_complete`
- `training_error`

但问题是：
- 字段没完全对齐 YOLO 专项契约
- 还没有强制包含 ETA / GPU / preview_samples / learning_rate

### 2.3 当前前端训练页是“列表页 + 简单详情”，不是训练控制台
当前：
- `Frontend/src/views/training/TrainingProgress.vue`

只能算一个基础页面，明显不够。

### 2.4 当前网站生成已经能生成 detection 网站
当前：
- `Backend/website_generator/views.py`
- `Backend/website_generator/models.py`
- `Backend/website_generator/generators/detection.py`

这是好消息，说明建站层不是从零开始。

### 2.5 当前没有真正的项目资源来挂左导航
也就是说：
- `GeneratedSite` 不是“业务项目”
- 左导航项目入口缺统一资源模型

### 结论
真正先要改的是 **训练主链**，而不是先去做项目页或 CodeGraph 集成。

---

## 三、Phase 1：YOLO 训练后端打底

这是整个项目的 P0，不先做这个，别的都没有意义。

---

## 3.1 目标

在不破坏当前通用训练功能的前提下，新增一条 YOLO 专项训练主链，满足：

- 可以创建 YOLO 训练运行
- 可以保存 YOLO 配置快照
- 可以通过 WebSocket 实时推送训练进度
- 可以落盘 `best.pt / last.pt / export` 产物
- 可以下载权重文件

---

## 3.2 建议新增/修改模块

### 后端主要涉及
- `Backend/training/models.py`
- `Backend/training/serializers.py`
- `Backend/training/views.py`
- `Backend/training/urls.py`
- `Backend/training/tasks.py`
- `Backend/training/consumers.py`
- `Backend/training/routing.py`
- `Backend/workflows/services/langchain_service.py`

---

## 3.3 具体实施步骤

### Step 1：保留 `TrainingJob`，先做 YOLO 语义扩展，不先大改模型名

不要一上来就把 `TrainingJob` 重命名成 `TrainingRun`，那会连带一堆迁移和兼容问题。

#### 正确做法
先在 `TrainingJob` 上补字段，支持 YOLO：
- `training_kind`：`generic` / `yolo`
- `yolo_version`
- `model_variant`
- `dataset_source_mode`
- `loss_box_history`
- `loss_cls_history`
- `loss_dfl_history`
- `precision_history`
- `recall_history`
- `map50_history`
- `map50_95_history`
- `gpu_runtime_stats`
- `estimated_duration_seconds`
- `best_weight_path`
- `last_weight_path`
- `exported_artifacts`

#### 为什么这样做
因为这是最稳的增量演进，先让功能跑起来，再决定是否抽象出新模型。

---

### Step 2：新增 YOLO 专项 serializer

在 `Backend/training/serializers.py` 中新增：

- `YoloTrainingRunCreateSerializer`
- `YoloTrainingRunDetailSerializer`
- `YoloTrainingMetricsHistorySerializer`
- `YoloTrainingRetrySerializer`

#### 原则
不要把 YOLO 字段硬塞到现有 `TrainingJobCreateSerializer` 里继续污染通用训练入口。

---

### Step 3：新增 YOLO 专项 API 入口

在 `Backend/training/views.py` 中新增一个 YOLO 专项 ViewSet，建议命名：

- `YoloTrainingRunViewSet`

配套路由：
- `POST /api/v1/training/yolo-runs/`
- `GET /api/v1/training/yolo-runs/{id}/`
- `GET /api/v1/training/yolo-runs/{id}/metrics-history/`
- `POST /api/v1/training/yolo-runs/{id}/cancel/`
- `POST /api/v1/training/yolo-runs/{id}/retry/`
- `GET /api/v1/training/yolo-runs/{id}/download/`

#### 注意
不要删除现有 `training-jobs` 路由。先并存，避免通用训练回归。

---

### Step 4：在 `tasks.py` 中实现 YOLO 执行路径

当前 `run_training_task` 是通用子进程训练入口。

#### 建议策略
先不要推翻它，而是在内部按 `training_kind == 'yolo'` 分支：

- 通用训练继续走原逻辑
- YOLO 训练走新的 ultralytics / YOLO runner 逻辑

#### 最关键要补齐的能力
- 训练前 preflight（数据集、GPU、环境）
- 每 epoch 回写 YOLO 专项 metrics
- ETA 估算
- checkpoint 保存
- export 产物落盘
- WebSocket 推送标准化消息

---

### Step 5：扩展 `TrainingConsumer` 消息体

当前 `TrainingConsumer` 可以保留。

#### 需要补什么
让 `training_progress` 消息强制带：
- `loss.box / cls / dfl`
- `metrics.precision / recall / mAP50 / mAP50_95 / fitness`
- `learning_rate`
- `gpu.memory_used_mb / total_mb / utilization_percent`
- `timing.elapsed_seconds / eta_seconds / eta_formatted / estimated_completion_at`
- `preview_samples`

#### 不要做什么
不要新增第二套 YOLO 专用 consumer。复用当前 consumer 更稳。

---

### Step 6：在 workflow 执行器中注册 `yolo_training` 节点

在 `Backend/workflows/services/langchain_service.py` 里：
- 为节点映射新增 `yolo_training`
- 专门实现 `run_yolo_training_node()`

#### 为什么不继续复用 `run_model_training_node()`
因为 YOLO 配置、指标、产物、前端展示协议都已经偏专门化。

硬塞进去，后面只会更乱。

---

## 3.4 Phase 1 完成标准

满足以下全部条件，才算 Phase 1 完成：

- 可以通过 `POST /training/yolo-runs/` 创建训练
- 训练记录能正确落库
- WebSocket 能推送 YOLO 完整指标
- 前端可以拿到 `best.pt` 下载链接
- 当前通用训练功能不回归

---

## 四、Phase 2：YOLO 实时训练前端打底

Phase 1 完成后，马上接前端，不要拖。

---

## 4.1 目标

做出一个真正可用的 YOLO 训练控制台，而不是把现有 `TrainingProgress.vue` 再塞更多条件分支。

---

## 4.2 建议新增/修改模块

### 前端主要涉及
- `Frontend/src/api/training.js`
- `Frontend/src/router/routes.js`
- `Frontend/src/views/training/TrainingProgress.vue`
- `Frontend/src/stores/`（新增 `yoloTraining.js`）
- 新增 `Frontend/src/views/training/yolo/` 目录
- 新增 `Frontend/src/components/training/yolo/` 目录

---

## 4.3 具体实施步骤

### Step 1：扩展 `Frontend/src/api/training.js`

新增 YOLO 专项方法：
- `listYoloRuns()`
- `getYoloRun(id)`
- `createYoloRun(data)`
- `getYoloMetricsHistory(id)`
- `cancelYoloRun(id)`
- `retryYoloRun(id, payload)`
- `downloadYoloArtifact(id, artifact)`
- `getYoloWebSocketUrl(id)`

#### 原则
不要让前端自己拼字符串路由，统一放 API 层。

---

### Step 2：新增 `yoloTraining` store

建议文件：
- `Frontend/src/stores/yoloTraining.js`

负责：
- 当前训练详情
- WebSocket 生命周期
- 自动重连
- 图表点缓存
- 日志与时间线
- 页面状态机

#### 这里直接复用 `codeGraph.js` 的 WebSocket 管理经验
但不要直接 copy，要抽成更稳定的状态逻辑。

---

### Step 3：新增 YOLO 专项详情页

建议新增路由：

- `/training/yolo`
- `/training/yolo/:trainingRunId`

建议新增页面：
- `YoloTrainingListPage.vue`
- `YoloTrainingDashboardPage.vue`

#### 原则
不要把现有 `TrainingProgress.vue` 直接魔改成 YOLO 控制台。

它可以保留为通用训练页，但 YOLO 必须单独做。

---

### Step 4：按组件拆页面

建议组件：
- `YoloTrainingHeroPanel.vue`
- `YoloTrainingProgressRing.vue`
- `YoloTrainingStatusCards.vue`
- `YoloTrainingLossChart.vue`
- `YoloTrainingMetricsChart.vue`
- `YoloTrainingGpuCard.vue`
- `YoloTrainingPreviewGrid.vue`
- `YoloTrainingEventTimeline.vue`
- `YoloTrainingLogPanel.vue`
- `YoloTrainingActionBar.vue`

#### 原则
不允许做成一个 1500 行的 dashboard 单文件组件。

---

### Step 5：先做 MVP，不要第一版就做满配

#### MVP 先做
- 顶部状态区
- 环形进度
- 核心指标卡
- Loss / Metrics 两张图
- ETA 区
- 日志区
- cancel / retry / download 操作

#### 第二波再补
- GPU 趋势图
- 验证样例预览
- 时间线
- 节点侧边面板

---

## 4.4 Phase 2 完成标准

- 页面能通过 REST + WebSocket 组合展示实时训练
- WebSocket 断线能自动重连
- 图表可持续追加数据点
- ETA 正常展示
- 训练完成后可以下载权重
- 不影响现有通用训练页

---

## 五、Phase 3：训练完成后的网站生成与项目化

这是把训练结果真正用起来的一段。

---

## 5.1 目标

让 YOLO 训练完成后，用户可以：
- 一键生成识别网站
- 一键创建平台项目
- 在左导航看到项目入口

---

## 5.2 建议新增/修改模块

### 后端
- `Backend/website_generator/views.py`
- `Backend/website_generator/serializers.py`
- `Backend/website_generator/models.py`
- 新增 `Backend/projects/` 或现有适合的项目域模块

### 前端
- `Frontend/src/api/websiteGenerator.js`（若已有则扩展）
- `Frontend/src/api/projects.js`（新建）
- `Frontend/src/views/projects/`
- 左导航菜单配置模块

---

## 5.3 具体实施步骤

### Step 1：扩展网站生成入口

在 `Backend/website_generator/views.py` 中新增：
- `yolo_generate` action

#### 行为
输入：
- `training_run_id`

内部自动：
- 找到 `best_weight_path`
- 读取 `class_names`
- 调用 detection generator
- 返回 `generated_site_id`

#### 原则
不要让前端自己先查训练详情，再手拼 `model_path` + `labels` 调现有 generate。

这个逻辑应该由后端封装。

---

### Step 2：建立项目资源模型

建议新增独立资源，例如：
- `GeneratedProject`

字段至少包括：
- `name`
- `project_type`
- `source_training_run_id`
- `generated_site_id`
- `site_url`
- `model_artifact`
- `class_names`
- `status`
- `tenant`
- `created_by`

#### 为什么必须新建
`GeneratedSite` 是代码生成产物，不是平台长期业务项目。

---

### Step 3：左导航挂项目入口

前端新增项目导航源：
- `GET /api/v1/projects/nav/`

#### 行为
- 登录后拉导航项目列表
- 把 YOLO 识别系统项目展示到左导航
- 点击进入项目详情页

---

### Step 4：训练完成页接入后续动作

在 `YoloTrainingActionBar.vue` 中新增按钮：
- `生成识别网站`
- `创建项目并加入左导航`

#### 交互顺序建议
1. 先生成网站
2. 网站成功后创建项目
3. 创建成功后提示“前往项目”

---

## 5.4 Phase 3 完成标准

- 训练完成后可一键发起网站生成
- 网站生成成功后可创建项目
- 左导航能展示新项目
- 项目详情页能打开推理网站入口

---

## 六、Phase 4：CodeGraph 与全链路收尾

这是收尾阶段，不是前置阶段。

---

## 6.1 目标

让生成的网站项目具备：
- 代码结构解析
- 调用链/依赖图
- 质量报告
- 全链路回归可验收

---

## 6.2 建议新增/修改模块

### 后端
- `Backend/codegraph/` 相关 views / routing / consumer
- 项目域与 codegraph 的关联字段

### 前端
- `Frontend/src/stores/codeGraph.js`（复用/扩展）
- 项目详情页中的 CodeGraph 标签页

---

## 6.3 具体实施步骤

### Step 1：项目详情页挂 CodeGraph 入口

项目详情页增加 Tab：
- `概览`
- `推理网站`
- `代码解析`

### Step 2：实现异步分析触发

用户点击：
- `开始代码解析`

后端：
- 对生成网站目录做分析
- 保存报告
- 用 WebSocket / 轮询回传状态

### Step 3：展示结果

至少展示：
- 前端文件数
- 后端文件数
- API 路由数
- 组件数
- 问题数
- route graph / component graph / call graph

---

## 6.4 回归验收清单

到 Phase 4 必须跑完整链回归：

1. 上传或选择标注项目
2. 发起 YOLO 训练
3. WebSocket 实时看板正常
4. 训练完成并生成权重
5. 下载权重成功
6. 生成检测网站成功
7. 创建平台项目成功
8. 左导航展示成功
9. CodeGraph 解析成功
10. 现有通用训练、现有 website generator 不回归

---

## 七、开发顺序建议（按周/按批次）

如果按较稳的节奏推进，我建议：

### 批次 1：后端训练主链
- `models.py`
- `serializers.py`
- `views.py`
- `urls.py`
- `tasks.py`
- `consumers.py`
- `langchain_service.py`

### 批次 2：前端训练控制台
- `api/training.js`
- `stores/yoloTraining.js`
- `views/training/yolo/*`
- `components/training/yolo/*`

### 批次 3：建站与项目化
- `website_generator` 扩展
- 项目资源模型
- 项目详情页与左导航

### 批次 4：CodeGraph 与回归
- codegraph 集成
- 联调
- 回归
- 文档收尾

---

## 八、风险清单

### 风险 1：直接大改 `TrainingJob` 命名与结构
风险：通用训练回归、数据库迁移复杂。

#### 规避
先做增量字段扩展，不先改名。

---

### 风险 2：把 YOLO 继续塞进通用训练接口
风险：协议越来越脏，前端越来越难维护。

#### 规避
单独做 `yolo-runs` 资源。

---

### 风险 3：前端继续在 `TrainingProgress.vue` 上无限加条件
风险：技术债爆炸。

#### 规避
单独做 YOLO 页面与组件。

---

### 风险 4：网站生成仍然让前端直接拼 `model_path`
风险：后续不可治理。

#### 规避
新增 `yolo_generate` 后端封装入口。

---

### 风险 5：左导航直接挂 `GeneratedSite`
风险：概念错位，后续统计、权限、项目详情都会乱。

#### 规避
新建项目资源层。

---

## 九、每阶段的验收口径

### Phase 1 验收
- YOLO 训练能从接口创建
- WebSocket 有完整指标
- 可以下载权重

### Phase 2 验收
- 实时看板可稳定显示
- 断线可自动恢复
- 图表和 ETA 正常

### Phase 3 验收
- 权重可一键生成网站
- 网站可创建平台项目
- 左导航可见

### Phase 4 验收
- CodeGraph 可解析生成项目
- 整链路回归通过

---

## 十、最终建议

如果你问我最应该马上开始实现的是哪一段，我的结论不变：

> **先做 Phase 1：YOLO 训练后端打底。**

原因很直接：
- 没有训练主链，就没有实时看板
- 没有权重产物，就没有建站
- 没有稳定指标推送，就没有前端实时图表

所以开发顺序不要乱。

### 正确顺序是
1. 训练主链后端
2. 实时训练前端
3. 建站与项目化
4. CodeGraph 收尾

### 不正确顺序是
- 先做花哨前端
- 先做左导航项目页
- 先做 CodeGraph 集成
- 训练主链最后补

那样会白做一堆壳子。

结论一句话：

> **这套 YOLO 方案真正的起点，不是页面，也不是项目管理，而是“先让 YOLO 训练运行、实时指标、权重产物这三件事稳稳落地”。**
