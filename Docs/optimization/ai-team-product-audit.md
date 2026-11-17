# 面向 AI 应用开发小团队的产品与前端审计

日期：2026-10-31。目标人群已由用户明确为「AI 应用开发小团队：知识库、工作流和应用部署」。本报告按应用交付任务组织，不把页面数量等同于产品完整度。

本文路由数量和 F1–F7 记录的是本轮实施前的审计基线。后续源码已陆续修复，不能把基线表当作最新未完成清单；本代理负责的落地状态见文末，其他协作变更以最终验证报告为准。

## 结论与证据边界

项目已有相当多的真实资源管理、知识检索、编排、执行和训练能力。主要产品缺口是缺少统一的「应用」对象，用户不能把这些资源组织为一个可测试、可发布、可观测、可迭代的交付物。现有「我的网站」是识别项目的生成与本地部署入口，不能直接改名充当通用知识助手或工作流应用的发布中心。

本次审计只读检查前端路由、导航配置、路由页面的服务调用、模板事件绑定，以及问题对应的后端实现；未修改业务或 UI。使用 impeccable 的 product/audit 参考，结合现有 PRODUCT.md 和 DESIGN.md。浏览器截图与交互复验由主代理使用 Chrome DevTools MCP 单独完成。

下表状态严格区分：

- **已接实现**：前端入口、处理函数和 API/store 调用链存在；不代表本次已用真实外部服务复验。
- **部分实现**：基本任务有调用链，但当前目标闭环存在明确缺口。
- **已证实未实现**：存在可执行的空处理、固定假值，或后端明确返回未实现/不支持。
- **重定向/静态**：本来就不承诺独立业务能力，不按空壳处理。
- **待实测**：需要用户凭证、真实第三方、部署环境或浏览器行为验证，静态证据不足以判定成功。

不把表单 placeholder、合理的空数组初始状态、正常的轮询 setTimeout 当作空壳。未调用的旧 composable 也不能用来证明当前页面故障。

## 当前入口规模与路由矩阵

对 `Frontend/src/router/routes.js` 做 AST 枚举，得到 **62 个路由配置项，56 个组件路由，6 个重定向，54 个不同视图文件**。计数包括设置父/子路由及 404，不包括重定向返回对象里的 path。`/nl-create` 另有 `/compose`、`/flowspeak` 别名。

主导航有 **22 个固定入口**，四组为：

| 现分组 | 全部固定入口 |
| --- | --- |
| 工作空间 | 工作台、工作流、我的网站、团队 |
| 智能与创作 | 智能体、多智能体协作、语创、提示词、智能体市场 |
| 模型与数据 | 模型管理、我的权重、知识库、向量存储、数据集、数据集推荐 |
| 工具与资源 | 执行历史、数据分析、模板市场、我的模板、代码图谱、API 测试、工作流对比 |

另有顶部新建工作流、个人中心和动态识别项目入口。个人中心包含 11 项设置。来源：[appNavigation.js](E:/Flowly-now/Frontend/src/config/appNavigation.js:4)、[userNavigation.js](E:/Flowly-now/Frontend/src/config/userNavigation.js:1)。

| 用户任务 | 全部对应路由 | 当前状态与已接能力 |
| --- | --- | --- |
| 了解产品 | `/` | 静态营销页。文案需随新人群调整，不能在未实现发布闭环前承诺完整应用交付。 |
| 登录与找回账户 | `/login`、`/register`、`/forgot-password`、`/reset-password` | 已接 auth/public API；register 重定向登录注册标签。邮件实际送达待外部环境实测。 |
| 进入工作区 | `/home` | 已接工作流、执行统计、智能体列表；当前首要动作仍是新建工作流，没有应用列表/发布待办。 |
| 从描述生成原型 | `/nl-create`，别名 `/compose`、`/flowspeak` | 已接会话、流式生成、任务状态、重试、确认工作流。确认后交付对象是工作流，未形成通用应用草稿。 |
| 选择原型模板 | `/marketplace`、`/marketplace/:id`、`/my-templates` | 已接 marketplace store，浏览/安装/发布模板属于资源复用；不等于将应用部署给调用者。 |
| 管理流程 | `/workflows`、`/workflows/new`、`/workflows/:id/edit`、`/workflows/:id` | 已接创建/保存/校验/单次运行/复制/删除。编辑器生命周期、未保存保护及执行回退已有回归基线；子工作流执行能力仍缺失，见问题 F1。 |
| 兼容旧执行地址 | `/workflows/:id/execute` | 重定向到执行详情或工作流编辑器。 |
| 管理助手与工具 | `/agents`、`/agents/new`、`/agents/:id/edit` | 已接 CRUD、模型/工具类型/知识集合/团队选择；“发布”仅发布到智能体市场。 |
| 手动调试助手 | `/agents/:id/debug` | 已接普通/流式对话、历史、清空和记忆重置；Token 使用显示未接真实值，见 F2。 |
| 多智能体任务 | `/agents/collaborate` | 已接协作执行、角色配置、租户选择、历史详情与删除；实际模型调用待真实凭证实测。 |
| 复用公开助手 | `/agents/marketplace` | 已接公开列表、预览和 clone；clone 后进入助手编辑。 |
| 创建知识并验证检索 | `/knowledge`、`/knowledge/:id` | 已接集合/管线、上传文件/文本/URL、文档分块、重处理、重建索引、检索/管线查询。集合支持 query.collection 导航过滤，不能误报为跳转未接。 |
| 连接向量基础设施 | `/vector-stores`、`/vector-stores/:id` | 已接 CRUD、连接测试、集合列表。真实向量服务连接待环境实测。 |
| 配置模型与用量 | `/models` | 已接 provider/model/key、连接验证、请求日志和聚合。真实模型供应商待凭证实测。 |
| 管理提示词 | `/prompts` | 已接分类、CRUD、复制、分享、模板渲染。尚无以应用 release 为边界的提示词快照。 |
| 运行后追踪 | `/executions`、`/executions/:id` | 已接执行列表、统计、详情/时间线、重放与取消；主要维度是工作流 execution。 |
| 监控健康与告警 | `/monitoring` | 已接统计、活跃执行、趋势、资源和告警规则；主导航与命令面板缺少该页面入口，见 F3。 |
| 观察平台费用 | `/analytics` | 已接总览、执行趋势、模型/供应商/Token/成本图表；无应用/发布版本维度；失败时数字会落到默认 0，见 F4。 |
| 对比并合并流程 | `/workflows/diff` | 已接两份当前工作流载入、本地 diff 和把 B 图整体覆盖到 A；不是不可变历史版本对比或生产回滚。 |
| 团队管理协作 | `/team`、`/team/join` | 已接租户、成员/邀请、角色、技能、任务、活动。当前页面级租户选择不能替代全局应用归属/应用权限模型。 |
| API 调试 | `/api-explorer` | 有实际 fetch 请求、鉴权、参数/响应格式化；端点目录为手工列表，不是已发布应用生成的调用台。 |
| 数据探索与训练 | `/dataset-recommend`、`/datasets`、`/datasets/:id`、`/augmentations`、`/annotations/:id` | 已接推荐、数据上传/预览/统计/下载、增强任务和标注 API。保留为高级工具，不能因人群收敛而删除。 |
| 旧训练导航 | `/training`、`/training/yolo/:pathMatch(.*)*` | 训练入口引导到工作流节点；后者重定向前者，不按空壳处理。 |
| 从训练交付识别网站 | `/my-weights`、`/my-sites`、`/projects/:id` | 已接训练权重→网站生成、项目详情/ZIP/本地部署。属于专用 CV 工具链，项目回到源工作流有断点，见 F5。 |
| 分析代码依赖 | `/codegraph` | 已接 codeGraph store/项目与图谱；支持 query.project 定位。保留为高级工具。 |
| 进入个人中心 | `/settings`、`/settings/` | 设置容器；空子路由重定向个人资料。 |
| 账户与个人偏好 | `/settings/profile`、`/settings/avatar`、`/settings/notifications`、`/settings/preferences` | 已接 auth/preferences；头像编辑器嵌入本地独立应用。通知实际渠道发送待环境验证。 |
| 配置连接与集成 | `/settings/credentials`、`/settings/integrations`、`/settings/desktop-agent` | 已接凭证、集成投递记录、桌面桥/远端训练分发；平台安装包是否真实存在需分别验证。 |
| API 使用说明 | `/settings/api-doc` | 静态/示例文档；不包含新应用发布后的专属 endpoint/key/version 使用说明。 |
| 订阅与发票 | `/settings/billing` | 已接套餐/订阅/用量/发票列表；下载按钮和 PDF 后端均未实现，见 F6。真实支付结算不能以界面成功消息替代。 |
| 导出/备份/删除 | `/settings/data-export` | 导出创建和下载有 API；自动备份/恢复/删除全数据存在明确未实现，见 F7。 |
| 品牌与域名 | `/settings/branding` | 已接品牌、邮件模板、域名校验 API；域名所有权校验和实际路由/证书部署属于环境闭环，不能仅凭保存成功宣称完成。 |
| 兼容入口 | `/integrations`、`/settings/api-keys` | 分别重定向 settings/integrations 和 settings/credentials。 |
| 处理无效地址 | `/:pathMatch(.*)*` | 404 页面，可返回首页/工作流。 |

## 沿应用交付链路的闭环缺口

| 阶段 | 可以复用的已有能力 | 对小团队缺少的交付闭环 | 建议切片 |
| --- | --- | --- | --- |
| 原型 | 语创、工作流模板、助手、提示词 | 没有应用类型、负责人、资源归属和稳定应用 ID；进入首页就要先理解 22 个工具入口。 | 应用中心支持「知识助手」「自动化」两类，先创建真实草稿，再绑定已有资源；不复制所有编辑器。 |
| 知识/模型 | 集合上传/分块/检索、向量库、模型连接和凭证 | 原料准备与具体应用缺少上下文；用户不知道当前应用因哪个缺项不能测试。 | 构建页展示真实就绪条件，支持跳入资源页面并返回应用；无模型/索引未就绪显示具体阻塞原因。 |
| 编排 | 画布、输入/输出节点、校验、运行、变量/触发器 | 子工作流可配置但执行不支持；应用输入输出协议与调用边界未建立。 | 先让 workflow 应用显式绑定流程与输入协议，补执行能力；保留原画布/高级节点。 |
| 测试 | 编辑器单次运行、Agent 调试、知识检索、执行详情 | 没有统一应用测试结果、草稿指纹、版本关联和测试通过→发布的依据。未找到应用回归测试集/预期结果/批量评测入口。 | 第一切片实现两类应用的真实手动测试与 trace；将“草稿变更后测试过期”表达出来。批量评测作为后续明确功能，不装成已有。 |
| 发布 | 网站生成/本地部署、模板/助手市场发布 | 无通用应用运行端点、不可变发布版本、应用专属 key、停用/回滚。市场发布不等于运行时服务。 | 新应用发布域：测试成功的当前草稿→不可变 release→发布 API→key；CV 网站保留原路径。 |
| 观测/成本 | workflow execution、模型请求日志、平台 analytics/monitoring | 未按应用/发布版本聚合请求，调试 Token 有假 0；无法从线上错误定位回具体发布版本。 | 应用请求日志与请求详情先落地，关联 release/trace/执行 ID；usage 未知用“未提供”，不能补 0。后端数据充分后再做趋势/预算。 |
| 迭代 | 保存工作流、复制、两流程 diff、语创历史 | 修改原资源与当前线上行为没有明确隔离；diff 不是历史 release。 | 草稿与线上版本分开显示，修改后线上继续指向已发布版本；从发布记录执行真实回滚。 |

以上未实现判断限定为当前仓库查到的前端入口/代码链路；没有找到某类入口不意味着外部部署绝不存在。

## 已证实问题及处理边界

### F1：子工作流存在完整配置界面，但主执行链明确拒绝

前端节点在 [nodeRegistry.js](E:/Flowly-now/Frontend/src/config/nodeRegistry.js:117) 可选，属性面板在 [PropertyPanel.vue](E:/Flowly-now/Frontend/src/components/workflow/PropertyPanel.vue:985) 挂载配置表单。版本控件在 [SubworkflowConfig.vue](E:/Flowly-now/Frontend/src/components/workflow/SubworkflowConfig.vue:66)，候选版本在同文件 [363 行](E:/Flowly-now/Frontend/src/components/workflow/SubworkflowConfig.vue:363) 用 `Array.from(wf.version)` 生成，不来自真实版本记录。

后端交叉审查确认：[langchain_service.py](E:/Flowly-now/Backend/workflows/services/langchain_service.py:315) 的执行器注册不包含 subworkflow；[453 行](E:/Flowly-now/Backend/workflows/services/langchain_service.py:453) 未注册分支返回 unsupported_node；[workflow_executor.py](E:/Flowly-now/Backend/workflows/services/workflow_executor.py:240) 使用此分派；[workflow_validation.py](E:/Flowly-now/Backend/workflows/services/workflow_validation.py:100) 预先报缺执行器。后台审查代理直接只读调用得到 `success=False, error_type=unsupported_node`。

影响：小团队把复用流程接入主流程后无法运行；版本选择也会给出并不存在的稳定承诺。

建议：实现带权限检查、参数映射、输出映射、递归/深度限制、超时/取消和错误策略的真正执行器，再对接真实版本列表。若后端暂没有持久版本模型，不能继续生成数字版本选项冒充历史版本；需明确真实支持范围。此处是完整业务补齐，不能仅加一个成功返回。

### F2：Agent 调试器 Token 用量恒为 0

[Debugger.vue](E:/Flowly-now/Frontend/src/views/agent/Debugger.vue:432) 将 tokenUsage 初始化为 0，全文件没有后续赋值；[285 行](E:/Flowly-now/Frontend/src/views/agent/Debugger.vue:285) 却展示「Token 使用」与上限进度。普通/流式调用确实执行，但显示不反映真实计费量。

建议：接入同一次请求的真实 usage，并明确单轮/会话总量定义；供应商未提供时显示未知，不得显示假 0。保存历史后也要能复现对应值。

### F3：实时监控有页面，没有正常导航入口

监控路由在 [routes.js](E:/Flowly-now/Frontend/src/router/routes.js:266)；[appNavigation.js](E:/Flowly-now/Frontend/src/config/appNavigation.js:4) 的 22 个入口没有 monitoring。全 `src` 检索未找到通向 `/monitoring` 的 router-link/router.push；命令面板导航又来自 APP_NAV_ITEMS。

建议：将执行、请求、健康与告警收束在「运行与费用」任务入口，保留直接路由兼容。不能把一个已实现页面从导航漏掉后再称其不存在。

### F4：统计页把未知/加载失败映成 0，且无法定位具体应用版本

[analytics/Index.vue](E:/Flowly-now/Frontend/src/views/analytics/Index.vue:355) 对缺失 overview 各字段一律 `|| 0`；[stores/analytics.js](E:/Flowly-now/Frontend/src/stores/analytics.js:37) 捕获错误只写 store.error，页面没有对应失败状态面板。日期筛选在 [15 行](E:/Flowly-now/Frontend/src/views/analytics/Index.vue:15)，[433 行](E:/Flowly-now/Frontend/src/views/analytics/Index.vue:433) 仅构造日期参数，没有应用或 release 上下文。API usage 在 [451 行](E:/Flowly-now/Frontend/src/views/analytics/Index.vue:451) 再次独立获取，未传日期参数，不能保证与当前日期范围一致。

建议：每个数据块区分加载、真实 0、未知和失败，支持重试；同一过滤条件传给全部请求。新应用请求日志先按 release 真实记录，后续费用统计必须由这些事实聚合，不能凭前端图表构造成本。

### F5：网站项目“在工作流中编辑”实际新建固定模板

[GeneratedSiteDetail.vue](E:/Flowly-now/Frontend/src/views/projects/GeneratedSiteDetail.vue:85) 呈现「在工作流中编辑」，[256 行](E:/Flowly-now/Frontend/src/views/projects/GeneratedSiteDetail.vue:256) 固定跳 `/workflows/new?template=yolo-detection`，不带当前 site ID、生成配置、训练 run 或源 workflow ID。编辑器确实支持该模板，所以这不是死链接，而是返回了一个新模板。

建议：建立真实源流程关联并载入；历史没有源流程时，明确提供「基于此项目新建工作流」，完整带入可重建的配置和权重，不让用户误以为正在修改原项目。此专用项目留在高级工具，不作为通用应用中心的数据模型。

### F6：发票下载前后端均未实现，不能伪造财务文件

[Billing.vue](E:/Flowly-now/Frontend/src/views/settings/Billing.vue:180) 的已支付发票「下载」按钮没有事件或 href。前端已有 [billing.js](E:/Flowly-now/Frontend/src/api/billing.js:87) 下载 API 封装，但后端 [billing/views.py](E:/Flowly-now/Backend/billing/views.py:267) 只返回 `Invoice download not implemented` JSON，没有 PDF。

建议：先确认计费是真实外部收单、内部核算还是自部署配额管理。真实外部计费要接供应商发票/支付状态；内部单据也只能依据真实 Invoice 数据生成明确标注的合法文件。不能把占位 JSON 下载、改扩展名、随机账单或 toast 当作完成。套餐获取失败时 [Billing.vue](E:/Flowly-now/Frontend/src/views/settings/Billing.vue:325) 会展示写死价格/权益，宜显式区分示例套餐和真实可订购报价。

### F7：自动备份/恢复/删除全数据只形成操作外观

- 「启用自动备份」和频率/保留数控件存在；[DataExport.vue](E:/Flowly-now/Frontend/src/views/settings/DataExport.vue:378) 从 localStorage 读取，[389 行](E:/Flowly-now/Frontend/src/views/settings/DataExport.vue:389) watch 仅写 localStorage。仓库搜索只在此页使用该键，没有调度请求；「最近备份」在 [411 行](E:/Flowly-now/Frontend/src/views/settings/DataExport.vue:411) 实为 completed full export 的截取列表，不读取保留数。
- [517 行](E:/Flowly-now/Frontend/src/views/settings/DataExport.vue:517) 恢复备份只 warning「功能尚未开放」。
- [525 行](E:/Flowly-now/Frontend/src/views/settings/DataExport.vue:525) 删除全数据让用户输入确认并二次确认后，只 error「需要管理员权限」，没有实际权限判断或删除调用。

建议：在真实后台任务/恢复事务/删除服务落地前，界面如实显示能力状态和具体原因，不能让本地开关表示服务器已开始备份。后续完整实现需要任务状态、故障反馈、保留策略、恢复范围预览、权限检查、审计及事务边界；不能以直接批量删除或省略恢复验证替代。现有导出/下载功能保留。

## 应用中心信息结构建议（方案，尚未编写 UI）

此节依据主代理已确定的两类应用方向设计界面职责，不预定 API URL、字段或权限细节。精确接口以 `Docs/optimization/application-api-contract.md` 为准。

### 全局导航

将最常用任务提升为「应用中心、知识库、工作流、模型与连接、运行与费用、团队」。应用中心成为登录后的主要交付工作区。语创和模板可保留独立入口，并成为新建应用的可选起点。

现有智能体/协作、提示词、模板市场/我的模板、向量存储、数据集/推荐/增强/标注、权重/训练/识别网站、代码图谱、API 测试、工作流对比全部保留，以「资源」和「高级工具」分组可发现地收纳。个人设置维持单独入口。改变入口优先级不等于删除功能。

### 应用列表

页头一个主动作「创建应用」。首屏用可扫读列表，列为名称/用途、类型、状态、线上版本、最近请求、更新时间；统计只有接口真实支持时才增加。状态至少清楚区分只有草稿、已发布、草稿有新改动和已停用。

搜索与类型/状态筛选置于同一工具条；应用行直接进入详情。空状态提供「知识助手」「自动化」两个有具体说明的起点，完成最小创建后进入构建页，而不是再弹出多个不相干模块。失败状态应说明加载失败和重试，不误呈现“还没有应用”。

### 应用详情

固定页头包含应用名、用途/归属、应用类型和线上版本。草稿状态与线上状态独立，不让保存草稿看起来像已部署。主任务标签页：

| 标签页 | 知识助手 | 自动化 | 两类共享规则 |
| --- | --- | --- | --- |
| 构建 | 选择集合、提示词、模型及真实参数；提供进入知识/模型详情的返回链接。 | 绑定工作流，展示输入字段与输出约定；进入原画布编辑。 | 显示缺失配置、最近保存、草稿是否相对线上变更；提交失败保留输入。 |
| 测试 | 输入问题，显示回答/来源/耗时/真实 usage 和 trace。 | 按输入协议填表/JSON，显示节点状态、结果/异常和执行链接。 | 真实执行；防重复提交；区分运行中/失败/取消；结果绑定草稿指纹，变更后明确测试已过期。 |
| 发布 | 预览要冻结的知识/模型/提示词设置与调用协议。 | 预览要冻结的流程图/输入输出协议及依赖。 | 发布成不可变版本；展示线上端点、示例、历史、停用与真实回滚；权限不够时给出原因。 |
| 请求日志 | 显示当前应用的实际调用与错误。 | 关联工作流 execution/节点错误。 | 按时间/状态/版本筛选；详情能定位 release、trace、耗时、真实用量；默认脱敏。 |

密钥放在「发布」内可见的独立区块：创建、一次性展示、复制、撤销及最近使用；复制示例不自动混入现有秘密。应用调用使用应用密钥，不能让外部集成复制用户登录 JWT。请求日志不得显示原始密钥。

初版没有必要新增一页空的“大总览”。就绪条件可以放在构建顶部的紧凑清单，真实运行信息放请求日志。应用拥有足够真实数据后再加入摘要，避免四个装饰统计卡反复占首屏。

## 现代视觉方向（待主代理统一设计方案）

具体使用场景：中文小团队开发者在白天办公室的笔记本/外接显示器上，频繁切换配置、测试结果和请求日志，需要持续阅读与快速排错。由任务决定信息密度与主题，不能因 AI 产品类别自动采用霓虹深蓝。

建议延续既有四主题兼容与公共组件，调整层级和内容构成：

1. **交付工作台结构**：应用列表用清晰行、稳定列宽和可辨状态；详情用稳定页头与任务标签；画布和代码保留各自宽工作区。不再每个功能都做同尺寸图标卡片。
2. **减少无信息装饰**：主内容使用带轻微色温的中性表面与明确分隔，主要操作用单一强调色。类别不再同时在图标底色、卡片光晕、统计字、按钮重复争夺注意力；错误/警告仍保留语义色。
3. **可读的中文层级**：沿用可靠中文系统字体栈；标题、标签、正文、辅助信息明确区分；endpoint、版本号、用量使用等宽/等宽数字。表单标签与结果区形成固定阅读边界，不靠字号放大所有信息。
4. **把状态做成内容**：草稿比线上更新、测试已过期、文档索引中、密钥已撤销、请求失败等都有具体文案和下一步；成功反馈就地更新对象状态，toast 只是补充。
5. **适量的功能动效**：保存状态、测试进度、结果展开可短暂过渡；不为背景添加连续粒子/光场，不使用会挤动布局的动画。支持减少动画，键盘聚焦可见。
6. **专用结果组件**：知识回答采用回答+引用来源；自动化采用执行摘要+输入输出+节点错误；请求日志采用表格+详情。由内容类型产生差异，避免换个图标仍是相同卡片页面。

这些是信息结构和设计方向，不是已批准视觉稿。视觉定稿还需使用 Chrome DevTools 的真实页面截图检查主题、窄屏、键盘、加载/失败/空状态和长内容。

## 可实施切片与验收事实

| 顺序 | 范围 | 必须能证明的结果 |
| --- | --- | --- |
| 1 | 两类应用草稿/列表/详情构建 | 创建、重载、修改、权限失败和资源失效均真实；不影响原知识库/画布/训练工具。 |
| 2 | 应用测试 | 知识助手走真实检索+模型，自动化走真实 executor；失败保留原因和 trace；结果绑定当前草稿指纹。 |
| 3 | 不可变发布+调用端点+key | 只有满足条件的草稿能发布；发布快照不随原草稿变化；有效/错误/撤销 key、未发布、无权限均测到。 |
| 4 | 请求日志/停用/回滚 | 调用按真实 release 记录；日志脱敏；停用不再服务；回滚真正改变运行目标，历史不改写。 |
| 5 | 导航与视觉整体落地 | 主路径能从首页被找到，各高级工具仍可访问；四主题/窄屏/长文档/失败/空状态通过 Chrome DevTools 验证。 |
| 6 | 逐一补齐已证实旧缺口 | 子工作流、真实 usage、监控入口、统计状态与筛选、网站源流程、备份服务分别独立验收；billing 以真实账务条件为前提。 |

本次审计未新增/修改产品代码，未因文档变更重复执行整套测试。此前安全收尾基线为主 Vitest 334/334、头像 212/212、coverage 命令产出 lcov、ESLint 无错误、生产构建通过；该基线不代表本报告列出的旧缺口已经修复，也不代替新应用域和新 UI 的后续全面测试。

## 后续实施记录（应用前端与 F5，2026-10-31）

审计完成后，经主代理明确分工，本代理新增真实应用列表与详情工作区，复用正式 applications API。已接知识助手/自动化草稿、服务器分页筛选、资源绑定、JSON 测试、成功指纹发布、发布记录/测试证据回链、回滚/下线、一次性明文密钥/撤销、请求深链接与真实输入输出。请求/响应仅适配已知 metadata，draft/configuration/input/output 用户键保持原样。缺失用量显示「未提供」。网络结果不确定时复用同一 Idempotency-Key 恢复测试，running 记录按真实 trace 轮询；不提供伪取消，不宣称已部署公网主机。

应用界面采用共享四主题 delivery tokens、紧凑比较列表、明确任务标签与状态时间线。草稿未保存、一次性密钥未保存、正在执行请求均有离开保护；删除入口与后台 publisher 权限一致。已确认发布成功后若状态读取失败，界面保留真实发布结果并提示刷新，不把后续读取失败误报成发布失败。

F5 已改为真实源流程回链。工作流建站时通过当前用户、WorkflowExecution 和 NodeExecution 的数据库状态验证系统 context，记录 created_by/tenant/source_workflow/source_node/source_execution。客户端不能声明这些来源。源流程不可读时不暴露其 ID；源删除与历史从未记录分开表达。

历史项目使用空 body 的 `POST /website-generator/{site_id}/rebuild-workflow/`，由后台授权读取站点配置，在同一事务中创建真实同空间草稿与 4 节点/3 连线，前端收到真实 ID 后再打开既有 Editor。模型权重、用途、标签、公开界面配置可重建；数据库连接和凭据不复制，输出目录使用新的受控路径。调用者必须为项目所有者或团队管理员，普通可见不能借此复制模型配置。重复提交恢复同一幂等操作，失败事务不遗留半图。无需向 Editor 加入客户端模板信任通道。

定向验证：应用+项目前端 32/32，F5 后端与既有生成契约 14/14，新迁移前态实际 DDL 回归 1/1，涉及前端 ESLint 0 错误/0 警告，makemigrations 检查无遗漏。前一实现点主前端 370/370、头像 212/212、完整生产构建通过；最后追加代码后的全量构建由主代理按资源情况串行复核，浏览器也由主代理使用 Chrome DevTools MCP 验证。

迁移验证分阶段进行：新增 0008 已用隔离数据库的前态表真实应用并验证历史数据、nullable 来源字段和唯一约束。此前发现的历史 SQLite/MySQL 迁移兼容问题由主代理与交付代理继续独立修复、运行真实 fresh migrate；不使用假标迁移或关闭外键掩盖问题。

## 工作流自定义数据完整性补充（2026-10-31）

原有公共 API 拦截器会递归转换全部 JSON key，导致节点配置中的 `foo_bar` 与 `fooBar` 冲突、模型 manifest 字段被改写。现增加显式 `opaqueKeys` 选项，工作流模块统一声明配置、执行输入输出、schema、variables、style、Vue Flow data、模板内容等用户子树；子树键和值原样保留，外层接口 metadata 继续遵循 camelCase/snake_case 约定，其他资源默认行为保持一致。创建、读取、保存、节点增改与批量、模板、执行管理、JSON/FormData 导入、规范 JSON 导出均走该边界。

两处旧工作流流式封装统一为真实 Bearer 的 POST Fetch Response，正确请求 `stream_execute/`，保留 AbortSignal 与用户 input_data，不再向 URL 添加 token。JSON 导入按实际内容使用 JSON 或 FormData，multipart boundary 由浏览器设置。

定向验证使用真实 Axios 拦截器与 HTTP adapter，保留 API 模块、Editor、属性面板、Pinia 和路由行为。新增字段往返与 Editor 读取→修改标签→保存，连同既有导航保护共 38/38；原 Jest 工作流接口断言 32/32；相关 API ESLint 通过。验证覆盖大小写冲突键、嵌套数组、模型 manifest、UUID literal 与 node_outputs 引用均不改写。最终浏览器仍需由主代理使用 Chrome DevTools MCP 验证真实后端持久化与 POST SSE 逐帧行为。

实际 MySQL fresh migrate 另发现旧站点 0001 已定义导航字段、0002 重复添加。已将 0002 精确改为按历史模型列名检查缺失列，回滚时保留 initial 已有字段和数据。四种真实 SchemaEditor 前态（两字段均有、均无、分别缺一）先复现 3 失败，修复后 4/4 通过；MySQL 全链结果由交付代理单独记录。
