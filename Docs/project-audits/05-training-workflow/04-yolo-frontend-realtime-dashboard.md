# YOLO 前端实时训练看板设计规范

> 文档目的：定义 YOLO 训练节点在前端的**实时监控页 / 节点详情面板 / 图表区 / 动画区 / 异常反馈区 / 操作区**的完整展示规范。  
> 这份文档直接服务于实现，不再讨论后端协议本身，而是明确：**前端如何消费 WebSocket、如何组织 UI、如何渲染图表、如何处理断线、如何显示 ETA、如何承接训练完成后的后续动作。**

---

## 一、为什么这份文档现在必须补

现在已经有了：

- `01-training-model-workflow-blueprint.md`：训练域总闭环
- `02-yolo-training-to-deploy-blueprint.md`：YOLO 专项业务流程
- `03-yolo-node-config-and-api-contract.md`：节点配置、REST API、WebSocket 契约

但还缺最关键的一层：

> **前端到底怎么把这些数据变成一个客户真正能看、能等、能理解、能操作的训练界面。**

如果这层不定，后面会出现这些问题：
- 页面只会显示几个数字，没有过程感
- WebSocket 数据到了但图表没统一口径
- 训练中断时用户不知道发生了什么
- ETA 字段有了但 UX 很差
- 训练完成后，不知道下一步该做下载权重还是生成网站

所以，这份文档的目标就是把 YOLO 训练实时看板定义成一个**可直接实现的产品级页面规范**。

---

## 二、结合当前前端现状的客观判断

从现有代码抽样看：

### 2.1 已有训练页基础
`Frontend/src/views/training/TrainingProgress.vue` 已经有：
- 训练任务列表
- 卡片式状态展示
- 基础进度条
- metricsHistory 简单 canvas 曲线
- cancel / retry / download 操作

这说明训练页不是从零开始。

### 2.2 已有执行页基础
`Frontend/src/views/workflows/ExecutionList.vue` 已经有：
- 执行记录列表
- 状态卡片
- 节点进度条
- 详情弹窗入口

这说明你的系统已经有“执行可观测”的页面骨架。

### 2.3 已有 WebSocket 实战参考
`Frontend/src/stores/codeGraph.js` 已经实现了：
- WebSocket 建连
- 自动重连
- ping 心跳
- 消息分发

这可以直接复用到 YOLO 训练看板。

### 2.4 当前训练页明显不够
现有 `TrainingProgress.vue` 只能算“通用训练列表页”，离 YOLO 专项实时看板差得很远，主要问题：
- 只有基础 loss/metric，没有 YOLO 专有指标
- 没有 ETA 区域
- 没有 GPU 可视化
- 没有验证样例预览
- 没有阶段动画
- 没有“训练完成后直接去生成网站/创建项目”的引导

### 结论
现有前端基础可复用，但必须新增**YOLO 专项训练看板**，而不是在现有通用训练页上继续硬补。

---

## 三、页面形态建议

YOLO 前端展示不应该只有一个页面。

建议拆成三层：

### 3.1 训练列表页
路由建议：

```text
/training/yolo
```

用途：
- 看所有 YOLO 训练任务
- 做筛选、排序、状态管理
- 点击进入详情

### 3.2 训练详情页 / 实时看板页
路由建议：

```text
/training/yolo/:trainingRunId
```

用途：
- 训练开始后主监控页
- WebSocket 实时展示
- 图表、GPU、ETA、日志、预览图都在这里

### 3.3 工作流节点侧边面板
用途：
- 当用户在 workflow editor 里点开 `yolo_training` 节点时
- 弹出轻量实时面板
- 只展示当前任务摘要，而不是完整版详情

### 结论
不要把所有能力都堆到一个页里。页面必须分层。

---

## 四、训练详情页的标准布局

这是最关键的部分。

建议采用 **6 区块布局**。

---

## 4.1 顶部区：任务头部 + 状态总览

### 展示内容
- 训练任务名称
- 项目名 / 工作流名
- 状态 badge
- 当前 epoch / 总 epoch
- 训练版本（YOLOv8n / YOLO11s）
- 数据集来源
- 启动时间
- 触发者

### 右侧主操作
- `暂停训练`
- `取消训练`
- `查看日志`
- `下载当前权重`
- `复制训练配置`

### 状态 badge 颜色规范
- `queued`：灰蓝
- `provisioning`：淡蓝
- `preparing_data`：紫蓝
- `training`：亮蓝
- `validating`：黄色
- `packaging`：青绿
- `completed`：绿色
- `failed`：红色
- `cancelled`：灰色
- `timeout`：橙红

---

## 4.2 第一屏核心区：训练动画 + 进度 + ETA

这是客户第一眼看到的区域，必须强。

### 左侧：训练动画卡

#### 建议形态
- 环形进度动画
- 中间显示 `67%`
- 下方显示 `Epoch 67 / 100`
- 环外有微粒转动或呼吸光晕
- 随状态切换颜色

#### 状态动画逻辑
- `queued`：缓慢脉冲
- `provisioning`：外圈扫描动画
- `preparing_data`：网格粒子流动
- `training`：环形推进 + 轻微呼吸动画
- `validating`：环形暂停推进，边缘闪烁
- `completed`：绿色发光 + 勾号过渡
- `failed`：红色抖动后静止

#### 注意
不能为了花哨影响可读性，动画必须服务于“等待感”。

---

### 中间：ETA / GPU / 时间卡组

#### 卡片 1：已用时间
- 文案：`已训练 15 分 32 秒`
- 数据源：`timing.elapsed_seconds`

#### 卡片 2：预计剩余
- 文案：`预计剩余约 42 分钟`
- 数据源：`timing.eta_formatted`

#### 卡片 3：预计完成时间
- 文案：`预计今日 00:28 完成`
- 数据源：`timing.estimated_completion_at`

#### 卡片 4：GPU 状态
- `NVIDIA RTX 4090`
- `6.1G / 24G`
- `87% 利用率`

#### 颜色语义
- ETA 正常：蓝色/绿色
- ETA 不稳定：黄色提示 `正在动态校准中`
- ETA 失真或不可用：灰色 `估算中...`
- GPU 过高：橙色/红色告警

---

### 右侧：当前关键信标卡

建议显示 4 个核心指标：
- `mAP50`
- `mAP50-95`
- `Precision`
- `Recall`

每张卡显示：
- 当前值
- 相对上一 epoch 的变化箭头
- 小型 sparkline

例如：

```text
mAP50
0.934
▲ +0.003
```

如果指标不存在（训练早期），显示：
- `待验证`
- 灰色占位骨架

---

## 4.3 第二屏：图表区

YOLO 看板最重要的部分之一。

建议拆成 4 张图，不要混成一张超级大图。

---

### 图表 1：Loss 曲线图

#### 线条
- `loss.box`
- `loss.cls`
- `loss.dfl`

#### 展示要求
- 支持图例切换
- 鼠标 hover 显示 epoch + 三条数值
- Y 轴自动平滑范围
- 线条颜色固定：
  - box：橙
  - cls：紫
  - dfl：青

#### 空态
前几个 epoch 数据不足时显示骨架屏。

---

### 图表 2：核心指标曲线图

#### 线条
- `precision`
- `recall`
- `mAP50`
- `mAP50_95`

#### 展示要求
- 默认只重点高亮 `mAP50` 与 `mAP50_95`
- 可切换显示全部
- 支持标记 best epoch
- 在 best epoch 位置加小圆点和 tooltip

---

### 图表 3：学习率与训练节奏图

#### 线条
- `learning_rate`
- `epoch_time_seconds`

#### 目的
这张图主要给高级用户看：
- 学习率变化是否合理
- epoch 耗时是否稳定

#### UX 要求
默认折叠在“高级视图”里，初级用户不强展示。

---

### 图表 4：GPU 资源趋势图

#### 数据
- `gpu.memory_used_mb`
- `gpu.utilization_percent`

#### 形态
双轴图或堆叠卡片图。

#### 告警规则
- 显存持续 > 90%：橙色提示
- GPU utilization 长时间 < 30%：提示训练可能空转/IO 瓶颈

---

## 4.4 第三屏：验证样例预览区

这是最容易让客户产生信任感的区域。

### 展示形式
建议用 2x2 或 3x2 卡片栅格。

每张卡展示：
- 验证图片缩略图
- 预测框可视化
- 预测标签和置信度
- 对应 epoch

### 数据来源
- WebSocket 的 `preview_samples[]`
- 或详情接口单独补充拉取

### 交互
- 点击可放大查看
- 支持切换“最近一次验证”/“最佳 epoch 验证”

### 空态
如果训练未进入验证阶段：
- 显示 `验证样例将在首轮验证后出现`

---

## 4.5 第四屏：日志与事件时间线

### 上半区：训练日志流

应展示：
- 环境检查结果
- 数据准备阶段日志
- epoch 日志
- checkpoint 保存日志
- export 日志
- 错误日志

### 样式要求
- 使用 monospace
- 支持等级颜色
- 支持关键字高亮（epoch / mAP / error / checkpoint）
- 支持自动滚动
- 支持暂停自动滚动

### 下半区：事件时间线

建议事件：
- 已入队
- GPU 已分配
- 数据准备完成
- 训练启动
- 第一次验证
- 最佳权重刷新
- checkpoint 保存
- 导出 onnx
- 训练完成

### 时间线用途
日志是技术流，时间线是产品流。两者都要有。

---

## 4.6 第五屏：训练完成后的后续动作区

这块非常重要，不然训练完成后页面就“死”了。

### 当状态 = `completed`
页面底部必须变成行动面板：

#### 主按钮
- `下载 best.pt`
- `下载 best.onnx`
- `生成识别网站`
- `创建项目并加入左导航`

#### 次级按钮
- `查看完整训练报告`
- `复制训练配置`
- `基于该配置重新训练`

### 当状态 = `failed`
页面底部变成恢复面板：
- `查看错误原因`
- `从 checkpoint 恢复`
- `降低 batch size 后重试`
- `复制配置重新训练`

### 当状态 = `cancelled`
- `从最近 checkpoint 恢复`
- `从头重跑`

---

## 五、页面状态机

前端不能只靠 `if status === xxx` 零散判断，必须定义状态机。

### 5.1 页面主状态

```text
idle
→ loading
→ connecting_ws
→ live_running
→ reconnecting
→ completed
→ failed
→ cancelled
```

### 5.2 状态说明

#### `idle`
- 还没拉详情
- 显示骨架屏

#### `loading`
- 正在请求详情接口
- 顶部与图表区显示 skeleton

#### `connecting_ws`
- 首次建立 WebSocket
- 顶部显示 `正在连接训练流...`

#### `live_running`
- WebSocket 正常
- 实时刷新图表、指标、动画

#### `reconnecting`
- WebSocket 断开后自动重连中
- 页面不清空数据
- 顶部黄色条提示：`连接中断，正在尝试重连...`

#### `completed`
- 停止实时订阅
- 显示完成态动效
- 展示后续动作区

#### `failed`
- 停止实时订阅
- 保留失败前最后数据
- 展示错误恢复区

#### `cancelled`
- 保留历史数据
- 提示用户可恢复或重新开始

---

## 六、WebSocket 消费策略

这部分必须和 `03-yolo-node-config-and-api-contract.md` 对齐。

### 6.1 建连策略

#### 首次进入详情页
1. 先调用 `GET /training/yolo-runs/{id}/`
2. 渲染已有静态数据
3. 再建立 WebSocket

#### 这样做的原因
避免页面首次进入时空白等待 WebSocket。

---

### 6.2 消息处理规则

#### `training_started`
- 状态变为 `live_running`
- 初始化训练动画

#### `epoch_start`
- 更新顶部进度文本
- 时间线加一条事件

#### `training_progress`
- 更新所有主卡片数值
- 追加图表数据点
- 刷新 ETA
- 刷新 GPU 卡
- 更新预览样例

#### `epoch_complete`
- 若有 checkpoint，时间线新增 `checkpoint saved`

#### `training_complete`
- 页面状态切到 `completed`
- 触发庆祝动效（轻量）
- 解锁后续动作按钮

#### `training_error`
- 页面状态切到 `failed`
- 顶部红色错误条
- 展示建议恢复动作

#### `training_cancelled`
- 页面状态切到 `cancelled`
- 说明 checkpoint 是否已保留

---

### 6.3 重连策略

参考现有 `codeGraph` store 的做法，但要更稳。

#### 规则
- 首次断线：2 秒后重连
- 第二次：5 秒
- 第三次：10 秒
- 最多 5 次

#### 超过 5 次后
页面显示：
- `实时连接失败，请手动刷新或稍后重试`

#### 断线期间页面行为
- 保留最后一帧数据
- 不清空图表
- 顶部显示黄色状态条

---

### 6.4 心跳策略

建议每 20 秒发一次：

```json
{ "type": "ping" }
```

收到：

```json
{ "type": "pong" }
```

如果 2 个周期都没有 pong：
- 主动重连

---

## 七、图表实现建议

### 7.1 不建议继续用原始 canvas 手绘
当前 `TrainingProgress.vue` 里是简单 canvas 画线，这对 YOLO 看板明显不够。

### 7.2 建议图表技术栈
优先：
- `echarts`

原因：
- 折线图能力成熟
- tooltip / legend / dataZoom / markPoint 都好做
- 动态更新性能足够

### 7.3 图表更新策略
- WebSocket 每次消息到达时，只 append 新点
- 不要整张图 re-render
- 最近 100 个点保留实时视图
- 历史完整数据可以通过接口回补

### 7.4 视图切换
图表区建议支持：
- `实时视图`
- `全量历史`

---

## 八、节点侧边面板设计

这是 workflow editor 里的轻量版，不是完整版详情页。

### 8.1 使用场景
- 用户在画布中点击 `yolo_training` 节点
- 如果该节点当前有运行中的 training_run
- 右侧弹出监控侧边栏

### 8.2 展示内容（精简版）
- 状态
- epoch 进度
- mAP50
- GPU 占用
- ETA
- 最近一张验证样例
- `前往完整看板` 按钮

### 8.3 不展示内容
- 不展示全量日志
- 不展示全量图表矩阵
- 不展示复杂恢复操作

这块的目标是“画布内可感知”，不是替代详情页。

---

## 九、训练列表页设计

YOLO 训练列表页也要升级，不然用户只能从详情页感知训练价值。

### 9.1 列表卡片建议字段
- 任务名
- 状态
- YOLO 版本
- 数据集名
- 当前 epoch / 总 epoch
- 当前 mAP50
- ETA
- GPU 名称
- 是否已有 best.pt
- 是否已生成网站

### 9.2 快速操作
- 查看详情
- 取消
- 重试
- 下载权重
- 生成网站

### 9.3 排序推荐
默认按：
1. `running`
2. `queued`
3. `failed`
4. `completed`

因为用户最关心的是正在跑的。

---

## 十、错误与异常 UX 规范

这部分不能省，YOLO 训练最常见的就是异常。

### 10.1 GPU 不可用
页面提示：
- `当前机器未检测到可用 GPU`
- 按钮：`切换为 CPU 训练` / `检查环境配置`

### 10.2 CUDA OOM
页面提示：
- `显存不足，建议降低 batch size 到 8 或 image size 到 512`
- 按钮：`按建议参数重试`

### 10.3 数据集格式错误
页面提示：
- `dataset.yaml 缺失或 labels 不完整`
- 按钮：`回到数据准备`

### 10.4 WebSocket 断开
页面提示：
- 黄色提示条：`实时连接中断，正在重连...`
- 保留最后画面，不要整页变空

### 10.5 网站生成失败
训练完成后如果点“生成网站”失败：
- 不回滚训练结果
- 保留权重下载
- 单独展示网站生成错误

---

## 十一、视觉风格建议

YOLO 训练看板不应该做成普通后台表单页，应该更偏“控制台”。

### 11.1 风格关键词
- 深色科技感
- 高对比数字卡片
- 柔和发光
- 重点信息集中
- 图表优先

### 11.2 配色建议
- 主色：蓝绿 / 青色系（训练进行中）
- 成功：绿色
- 警告：橙黄
- 错误：红色
- 辅助：紫色（高级指标）

### 11.3 字体建议
- 数字与时间：monospace
- 标题：粗体无衬线

### 11.4 视觉禁忌
- 不要满屏都是边框
- 不要把日志区做得比图表更抢眼
- 不要把每个指标都做成 одинаковый视觉权重

主次必须明确：
1. 状态与 ETA
2. 训练进度
3. 核心指标
4. 图表
5. GPU
6. 日志

---

## 十二、前端组件拆分建议

不要做成一个 1000 行的大页面组件。

建议拆成：

- `YoloTrainingDashboardPage.vue`
- `YoloTrainingHeroPanel.vue`
- `YoloTrainingStatusCards.vue`
- `YoloTrainingProgressRing.vue`
- `YoloTrainingMetricsChart.vue`
- `YoloTrainingLossChart.vue`
- `YoloTrainingGpuCard.vue`
- `YoloTrainingPreviewGrid.vue`
- `YoloTrainingEventTimeline.vue`
- `YoloTrainingLogPanel.vue`
- `YoloTrainingActionBar.vue`
- `YoloTrainingNodeDrawer.vue`

状态管理建议独立：
- `src/stores/yoloTraining.js`

---

## 十三、状态管理建议

### store 职责
- 管训练详情
- 管 WebSocket 生命周期
- 管图表点数据
- 管断线重连
- 管当前页面状态机

### store 内部状态建议

```js
state: {
  currentRun: null,
  liveStatus: 'idle',
  wsConnected: false,
  wsReconnectCount: 0,
  charts: {
    loss: [],
    metrics: [],
    gpu: [],
    timing: []
  },
  timelineEvents: [],
  previewSamples: [],
  logs: [],
  ui: {
    autoScrollLogs: true,
    advancedMode: false,
    selectedSampleMode: 'latest'
  }
}
```

---

## 十四、页面与协议映射表

### 14.1 顶部状态区
来自：
- `GET /training/yolo-runs/{id}/`
- WebSocket `training_started` / `training_progress`

### 14.2 动画与进度环
来自：
- `data.progress_percent`
- `data.epoch`
- `data.total_epochs`
- `data.status`

### 14.3 指标卡片
来自：
- `data.metrics.*`

### 14.4 ETA 区域
来自：
- `data.timing.elapsed_seconds`
- `data.timing.eta_formatted`
- `data.timing.estimated_completion_at`

### 14.5 图表区
来自：
- `metrics-history` 接口初始化
- WebSocket `training_progress` 增量追加

### 14.6 验证样例
来自：
- `data.preview_samples`

### 14.7 行动区
来自：
- `training_complete.next_actions`
- 页面本地状态 `completed`

---

## 十五、实施顺序建议

### Phase 1：先做 MVP 可看板
- 顶部状态区
- 进度环
- 核心指标卡
- Loss / Metrics 两张图
- ETA
- 基础日志区

### Phase 2：补高级能力
- GPU 趋势图
- 验证样例预览
- 时间线
- 节点侧边面板

### Phase 3：补后续动作闭环
- 下载权重
- 生成网站
- 创建项目
- CodeGraph 入口

---

## 十六、最终判断

前端这一层如果做不好，YOLO 训练这条链就算后端全通，用户也感知不到价值。

因为客户最关心的从来不是：
- 你是不是用了 ultralytics
- 你是不是写了一个 Celery task

客户真正关心的是：
- 现在跑到哪了
- 还要等多久
- 指标好不好
- 机器有没有问题
- 结果出来后我下一步点哪里

所以这份文档的本质，就是把 YOLO 训练页从“技术详情页”升级成“客户可等待、可理解、可决策的训练控制台”。

### 结论很直接

> **下一步如果继续推进，就应该开始按这份文档和 `03-yolo-node-config-and-api-contract.md` 一起落前端页面与 store，不要再继续泛写业务说明。**
