# AI 应用交付 API

应用复用现有知识库、工作流引擎及执行记录。所有路径以 `/api/v1/applications/` 开头；响应沿用 `{code,message,data,errors}` 包装，以下描述 `data` 内容。字段使用 snake_case；`draft`、`input_data`、`output_data` 中用户定义的键不得递归改名。

## 权限与资源

个人应用仅 owner 可管理。团队应用仅活跃团队成员可读取，owner、团队 owner/admin/member 可编辑、测试和用登录身份调用；仅 owner、团队 owner/admin 可发布、回滚、下线、删除和管理调用密钥。viewer 只读。退出团队、停用账号、暂停/取消团队后立即失效；隐藏工作流快照不能通过普通工作流 API 查询或修改。绑定团队资源必须属于同一团队；个人应用仅绑定 owner 的个人资源，避免个人资源被团队成员间接读取。

`kind` 固定为 `knowledge` 或 `workflow`，创建后不可改变。`tenant_id` 创建后不可改变。知识库内容实时更新，release 固定 collection 绑定及检索/提示配置，并明确返回 `knowledge_content_policy: "live"`；源 collection 删除/权限失效时调用拒绝。工作流 release 使用真实、隐藏的数据库图快照；后续编辑或删除源工作流不会改变 release 的执行定义。

## 路径

| 方法与路径 | 内容 |
| --- | --- |
| GET / | 分页列表；支持 `search`、`kind`、`tenant_id`、`status=draft|published|unpublished`，筛选在分页前执行 |
| POST / | 创建 `{name,description?,kind,tenant_id?,draft}` |
| GET /overview/ | 当前可见应用的 `{application_count,published_count,draft_count,request_count,failed_count,success_rate,avg_latency_ms,total_tokens,total_cost,usage_complete,recent_applications,recent_requests}`；请求统计最近 7 天，最近应用 6 个、请求 8 条；无终态时成功率/延迟为 null，未知用量为 null |
| GET /resources/ | `?kind=knowledge|workflow&tenant_id=可选`，返回当前可绑定的 `{id,name}` 标准分页列表，团队源要求有效编辑权限 |
| GET /{id}/ | 应用详情 |
| PATCH/PUT /{id}/ | 更新 name、description、完整替换 draft；kind/tenant_id 不可变 |
| DELETE /{id}/ | 软删除并撤销调用能力，保留发布和请求审计记录 |
| POST /{id}/test/ | `{input_data:{...}}`，真实执行当前草稿并记录本次测试 fingerprint |
| POST /{id}/publish/ | `{}`；仅最新成功测试与当前草稿及真实源图 fingerprint 一致时创建 release 并激活，返回 release，HTTP 201；否则 409 |
| POST /{id}/rollback/ | `{release_id:"uuid"}`；仅激活本应用旧版本，返回应用详情 |
| POST /{id}/unpublish/ | `{}`；下线，返回应用详情 |
| GET /{id}/releases/ | 分页 release 列表，按 version 降序 |
| GET/POST /{id}/api-keys/ | 列表/创建 `{name,expires_at?}`；创建响应额外返回一次 `api_key`，以后仅 prefix，不可读回明文 |
| POST /{id}/api-keys/{key_id}/revoke/ | `{}`，立即撤销 |
| POST /{id}/invoke/ | `{input_data:{...}}`；已登录允许调用者或 `Authorization: Bearer flowly_app_...`；密钥仅允许该应用 invoke，不允许任何管理/日志 API |
| GET /{id}/requests/ | 分页请求记录；可过滤 `mode=test|invoke`、`status=completed|failed|running|rejected` |
| GET /{id}/requests/{request_id}/ | 仅返回此应用归属的单条真实请求；跨应用 id 一律 404 |

## 应用与发布对象

应用：`{id,name,description,kind,tenant_id,owner_id,draft,draft_fingerprint,tested_fingerprint,last_test_status,last_test_at,active_release,can_edit,can_publish,status,release_count,created_at,updated_at}`。`active_release` 为 release 摘要或 null。status 中 draft 表示从未发布，unpublished 表示有历史版本但已下线，published 表示有激活版本。

knowledge draft：`{collection_id:"uuid",system_prompt:"...",top_k:5,min_similarity:0.0}`。workflow draft：`{workflow_id:"uuid"}`。字段严格校验，拒绝未知配置；system_prompt 最长 16000 字，top_k 1..50，min_similarity 0..1。

release：`{id,application_id,version,fingerprint,configuration,knowledge_content_policy,created_by_id,created_at,is_active,test_request_id,tested_at}`。configuration 是当时的 draft；知识应用另保存 collection_settings，固定 collection 检索模式、embedding/chunk 参数与向量存储绑定/连接配置，实际文档/分块仍读取原 collection 的实时内容。存储凭据允许轮换，不复制到发布记录。工作流图另存不可变数据库快照与递归子图 manifest，不在列表中重复传输。版本号单调递增，回滚不覆写历史。

test_request_id 固定指向本版本 fingerprint 验证成功的真实测试请求，tested_at 为该次完成时间；后续测试不会改写旧版本证据。两个字段仅对升级前的旧历史允许 null，新发布必须找到同应用的实际成功测试，不能由客户端提交或替换证明。

调用密钥对象：`{id,name,prefix,expires_at,revoked_at,last_used_at,created_at,is_active}`。创建时额外返回一次 api_key；之后没有明文或 hash 字段。到期、撤销或创建者失去发布权限后，调用立即拒绝。

## 输入与请求记录

knowledge `input_data` 必须包含非空 `query`（最长 4000 字）；可含简单键值 `filters`，不接受其他键。workflow 的 input_data 原样交给现有图验证与执行器。input_data 必须是 JSON 对象，UTF-8 JSON 最多 100 KiB。

请求对象：`{id,application_id,release_id,mode,status,input_data,output_data,error_code,error_message,latency_ms,total_tokens,cost,currency,workflow_execution_id,created_at,completed_at,deadline_at}`。knowledge output_data 使用现有 RAG `{response,sources,grounded,answer_status}`；workflow output_data 使用现有执行上下文。模型没有返回可归因用量时 total_tokens/cost/currency 必须为 null；不得按字符串估算或伪造 0。

所有实际执行、执行失败和速率/并发拒绝都留记录。无知识证据返回 `no_evidence`，无可用模型返回 503 `upstream_unavailable`，两者均不能产生可发布的成功测试。运行错误返回 `{code,message,data:<请求对象>,errors:{reason:<error_code>}}`，保留 request id，禁止返回堆栈/凭据。未登录/错误密钥 401、越权资源 404/403、参数 400/422、无发布或测试失效 409、超输入/输出限制 413、速率/并发 429、运行/上游不可用 503、执行超时/租约失效 504。

速率默认每应用每分钟 60 次，最多并发 2 次，可由 `APPLICATION_RATE_PER_MINUTE`、`APPLICATION_MAX_CONCURRENT` 配置。运行准入使用数据库应用行锁串行检查，记录持久化，不依赖单个 Web 进程内存。调用密钥绑定创建者权限；创建者被停用或失去应用管理权限后 fail closed。请求和 release 只允许应用可见成员读取。

test/invoke 可携带 Idempotency-Key（非空、最多 128 字符）。同身份/模式/应用下重试同键与原输入，复用原记录；原请求运行中返回 202，相同键用于不同输入返回 409。新运行必须生成新键。应用密钥不能借此读取其他请求。

同步执行默认总预算 120 秒（APPLICATION_MAX_EXECUTION_SECONDS），客户端使用 180 秒超时。原生 HTTP/LLM 请求使用剩余预算，过期后不再启动新调用或接收迟到结果。第三方已发生的副作用无法撤回。持久租约在预算后额外保留 30 秒（APPLICATION_LEASE_GRACE_SECONDS）；进程失联时，下一次请求准入或日志轮询会将过期 running 明确结算为 failed/504，并协作停止关联执行。记录保留，不假造成功、不永久占用并发槽。

子工作流支持同步/异步、输入输出映射、stop/skip/fallback、共享 deadline、父取消与权限重验。异步模式立即返回 child_execution_id，完成后的映射值存入子执行 output_data.mapped_output，不改写已结束的父执行。应用草稿测试若仍有异步子任务未结束，会保持 running/202；轮询请求详情后按真实子结果结算，未通过前不能发布。当前可选版本仅 latest 或服务端真实当前版本号，不存在的历史版本拒绝；发布时递归固定所有实际子图并验证可信 manifest，后续修改源子图不影响 release。配置中的字面量、业务字段和用户代码原样保留，原节点 ID 通过可信执行别名继续引用。

## 复用边界

不创建第二个 RAG 检索器、工作流执行器或账单计量源。应用请求关联真实 WorkflowExecution；release 使用真实隐藏 Workflow/Node/Edge 图。既有 APICredential 是访问外部模型的凭据，不能当应用入口密钥使用。知识库发布固定配置但不复制文档；小团队首版不引入云部署、外部环境编排或支付结算。
