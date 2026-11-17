# 应用测试集与批量回归 API 契约

记录日期：2026-11-01。本文对应 `Backend/applications/evaluation_*.py`、`services.py`、`readiness.py` 的当前实现。应用回归验证真实应用请求及其输出；训练模型的分类、检测指标属于独立的 [模型评测域](model-evaluation-reliability-20261101.md)。本文不代表全平台功能或生产部署已全部验收。

## 地址、身份与响应

所有下表路径均位于 `/api/v1/applications/{application_id}/` 下，并保留末尾 `/`。UUID 必须属于当前可见应用；跨应用套件、用例、批次和发布版本不能混用。

| 方法 | 相对路径 | 行为 |
| --- | --- | --- |
| GET / POST | `test-suites/` | 分页列出 / 创建测试集 |
| GET / PATCH / DELETE | `test-suites/{suite_id}/` | 读取 / 修改 / 软删除测试集 |
| GET / POST | `test-suites/{suite_id}/cases/` | 分页列出 / 创建用例 |
| PATCH / DELETE | `test-suites/{suite_id}/cases/{case_id}/` | 修改 / 删除用例 |
| GET | `test-suites/{suite_id}/export/` | 下载版本化测试集 JSON |
| POST | `test-suites-import/` | 事务性导入新测试集 |
| GET / POST | `evaluation-runs/` | 分页列出 / 发起持久批次；列表可用 `suite_id` 筛选 |
| GET | `evaluation-runs/{run_id}/` | 查询批次、计数及逐用例结果 |
| POST | `evaluation-runs/{run_id}/cancel/` | 取消，正文为 `{}` |
| GET | `evaluation-runs/{run_id}/compare/?baseline_id={run_id}` | 比较同应用、同测试集的两个已结束批次 |
| GET | `requests/{request_id}/execution/` | 读取同应用请求关联的主工作流执行摘要 |

这些管理接口使用已登录用户身份。应用 API Key 仅授权其应用的 `invoke/`，不能管理测试集或发起评测。普通 JSON API 经过项目统一响应包装，业务对象位于 `data`；分页对象包含 `results`。导出接口直接返回附件 JSON，并设置 `Cache-Control: private, no-store`。调用方同时检查 HTTP 状态和响应内容，不把成功接收任务视为测试通过。

| 空间 / 角色 | 读取套件、批次、比较 | 创建、修改、运行、取消 | 设置发布门禁、发布 |
| --- | --- | --- | --- |
| 个人应用所有者 | 可以 | 可以 | 可以 |
| 活跃团队 viewer | 可以 | 拒绝 | 拒绝 |
| 活跃团队 member | 可以 | 可以 | 仅其为应用所有者时可以 |
| 活跃团队 owner / admin | 可以 | 可以 | 可以 |

超级用户遵循应用域的管理权限；停用账号、失效团队及撤销成员资格仍受到准入检查。Worker 在用例之间及异步等待时重新读取身份和应用权限；权限失效后停止后续用例。外部系统已发生的操作不能撤回。

## 套件、用例与导入导出

创建套件正文为 `{"name":"核心问题","description":"发布前回归"}`。`name` 必填且不超过 160 字符，`description` 可选且不超过 4000 字符。套件有服务端维护的 `revision`；修改套件、创建 / 修改 / 删除用例都会推进修订号。

创建用例示例：

```json
{
  "name": "保留客户标识",
  "input_data": {"Customer_ID": "Ada", "foo_bar": 1, "fooBar": 2},
  "assertions": [
    {"type": "json_equals", "path": "/variables/text", "expected": "Hello Ada"},
    {"type": "latency_max", "expected": 5000}
  ],
  "enabled": true,
  "position": 0
}
```

`input_data` 必须是有限 JSON 对象，默认大小上限 100 KiB。业务键名、层级和字符串值保持原样；不会把 `foo_bar`、`fooBar`、`Customer_ID` 当作接口元数据重命名。也可用同应用的真实 `from_request_id` 复制请求输入，不能同时提供 `input_data`。创建用例必须有输入来源及至少一条断言。`name` 不超过 160 字符；`enabled` 默认 `true`；`position` 为 0 至 10000 的整数。PATCH 只修改明确传入的字段。

默认每应用最多 20 个未删除套件、每套件 100 条用例，每条用例 1 至 20 条断言。单条预期值上限 64 KiB，整套导入导出上限 2 MiB。套件 / 用例总量分别可由 Django settings 的 `APPLICATION_MAX_TEST_SUITES`、`APPLICATION_MAX_TEST_CASES` 调整，其余限制见 `Backend/applications/evaluation_constants.py`。

导出格式如下；导入同一格式会创建新套件及新用例 ID，保留输入、断言、启用状态和排序，不携带历史请求或批次证据：

```json
{
  "type": "flowly_application_test_suite",
  "schema_version": 1,
  "suite": {"name": "核心问题", "description": "发布前回归"},
  "cases": [
    {
      "name": "返回字段",
      "input_data": {},
      "assertions": [{"type": "json_exists", "path": "/variables/text", "expected": true}],
      "enabled": true,
      "position": 0
    }
  ]
}
```

未知字段、未知 schema 版本、空导入、非法断言或超限内容会拒绝，整个导入回滚；导入不能使用 `from_request_id`。删除套件不会删除历史批次；仍有在途批次或仍作为发布门禁的套件返回 409。

## 九种真实断言

断言只读取实际持久化 `ApplicationRequest` 的输出、耗时和错误代码，不执行表达式，不调用模型充当裁判。每条均必须提供 `expected`。只有前四种使用 JSON Pointer `path`，其他种类应省略 `path` 或传空字符串。

| `type` | 判定范围 | `expected` |
| --- | --- | --- |
| `json_equals` | 输出中所指值与预期递归相等；布尔与数字严格区分，数组顺序保留 | 任意有限 JSON 值 |
| `json_contains` | 字符串包含子串、数组含相等元素，或对象含全部预期键值 | 对应字符串、元素或对象 |
| `json_exists` | 指针所指字段是否存在；存在且为 `null` 仍算存在 | 布尔值 |
| `json_type` | 指针所指 JSON 类型 | `object` / `array` / `string` / `number` / `boolean` / `null` |
| `response_contains` | 知识回答输出的 `response` 字符串包含预期文本 | 非空字符串，最多 4000 字符 |
| `grounded` | 知识回答输出的 `grounded` 布尔值匹配 | 布尔值 |
| `sources_min` | 输出 `sources` 数组长度达到下限 | 0 至 50 的整数 |
| `latency_max` | 实际请求 `latency_ms` 不超过上限，单位毫秒 | 非负有限数值 |
| `error_code` | 实际请求为 `failed` / `rejected` 且错误代码完全匹配 | 非空字符串，最多 4000 字符 |

JSON Pointer 的空字符串表示整个输出；`/` 分隔路径，`~1` 表示 `/`，`~0` 表示 `~`，数组下标使用 `0`、`1` 等标准形式。缺失字段不会作为 `null` 通过相等断言。结果中的预期展示和实际值有长度限制，`expected_display`、`expected_truncated` 提示是否截断；真实判定使用完整值。

未成功的请求若没有声明 `error_code` 断言，该用例为 `error`。声明期望错误后，仍须所有断言均满足才为 `passed`，不会把任意失败当作成功。

## 固定目标、提交幂等与运行配置

发起当前草稿全量批次：

```http
POST /api/v1/applications/{application_id}/evaluation-runs/
Idempotency-Key: release-review-001
Content-Type: application/json

{"suite_id":"<suite UUID>","target":"draft"}
```

`target` 默认 `draft`。草稿批次在提交时固定配置、fingerprint、工作流及子工作流快照、manifest、测试集修订和每条用例的输入 / 断言副本。排队后再编辑来源或用例不会改变该批次实际执行目标。

指定发布版本使用 `{"suite_id":"<suite UUID>","target":"release","release_id":"<release UUID>"}`。版本必须属于同应用，实际执行该历史版本，不切换当前激活版本；草稿目标不能传 `release_id`。可选 `case_ids` 是非空、去重、最多 100 个 UUID 的数组，只能选择本套件的启用用例；省略时执行全部启用用例。空套件不能启动。

可选 `Idempotency-Key` 长度为 1 至 128 字符，不能全空白。它按应用和发起用户隔离：同键、相同规范化参数返回原批次；同键、不同参数返回 409 `idempotency_conflict`。原批次即使已结束或随后变旧，也不会因重发同键再执行。需要明确的新尝试时使用新键。这保证持久准入不重复，不承诺崩溃或人为新尝试下的外部副作用恰好一次。

默认采用 Celery task `applications.execute_evaluation`，事务提交后才投递，队列中只传批次 ID。需正确配置 `CELERY_BROKER_URL` 并启动能消费该 task 的 Worker。`CELERY_TASK_ALWAYS_EAGER=True` 时记录 `runner_mode=eager` 并同步执行真实任务，主要供隔离测试或明确的本地配置使用。正常异步投递失败返回 503 `queue_unavailable`，持久批次为 `failed`，不会偷偷在 Web 进程补跑。Broker 接收但没有 Worker 消费仍只是 `queued`；排队过期后在查询 / 后续准入恢复为 `failed/queue_expired`，不会宣称已运行。

首次创建后仍在途返回 202；已结束的新批次返回 201；重放已结束批次返回 200。默认每应用最多 1 个在途批次，排队租约 120 秒，总执行预算 900 秒，租约宽限 30 秒；批次总预算包含等待应用容量的时间。相关 settings 为 `APPLICATION_MAX_ACTIVE_EVALUATIONS`、`APPLICATION_EVALUATION_QUEUE_SECONDS`、`APPLICATION_EVALUATION_MAX_SECONDS`。单次请求继续遵守应用既有速率、并发和超时限制。异步子工作流必须实际完成并成功，才接受对应请求为成功；已完成的异步请求会先对账释放容量。

## 状态、取消与证据

批次主路径为 `queued → running → completed`，运行中取消为 `running → cancelling → cancelled`；排队取消直接 `cancelled`。超时、租约失联、权限撤销或 Worker 异常可结束为 `failed`。重复投递只接受尚未开始的 `queued` 身份，不自动重放失联任务。

用例状态为 `pending`、`running`、`passed`、`failed`、`error`、`skipped`、`cancelled`。批次 `completed` 表示已结束遍历，不代表全部通过；必须同时检查 `total/passed/failed/errors/skipped`。`pass_rate = passed / (passed + failed + errors)`，无已评分用例为 `null`，跳过和取消不进入分母。

运行中取消立即停止后续用例，并使已登记在途请求及工作流不再接受完成结果；`cancelling` 保留到 Worker 对在途调用返回或等待过程作出确认。外部 HTTP / 模型调用可能已产生作用，不能据此承诺撤回。在途租约过期会显式失败或完成取消确认，迟到结果不能覆盖终态。

批次详情包含逐用例 `request_id`、`case_hash`、断言结果、错误和耗时。真实输入 / 输出可通过同应用的 `requests/{request_id}/` 读取。测试集或草稿发生变化时 `is_stale=true`，保留原证据用于追溯。

## 应用范围的只读执行摘要

应用执行使用隐藏的工作流快照，原通用 `/workflows/executions/{id}/` 地址不会因此对外开放。查看应用请求的主执行应使用：

```http
GET /api/v1/applications/{application_id}/requests/{request_id}/execution/
```

后端先取得当前可见应用，再查该应用自己的 `ApplicationRequest`，只从其关联字段取得主 `WorkflowExecution`，不接受客户端指定其他 execution ID。正常响应在统一 `data` 包装内保持 raw snake_case：

```json
{
  "id": "<主 execution UUID>",
  "status": "running",
  "started_at": "2026-11-01T12:00:00Z",
  "completed_at": null,
  "nodes": [
    {
      "node_id": "<source node UUID 或实际 snapshot node UUID>",
      "node_name": "查询知识库",
      "node_type": "http_request",
      "status": "running",
      "started_at": null,
      "completed_at": null,
      "error_message": ""
    }
  ]
}
```

顶层仅有 `id/status/started_at/completed_at/nodes`；节点仅有示例中的七个字段。`id/status/node_id` 为字符串，`nodes` 为数组。节点 ID 优先用请求保存的 `workflow_manifest.node_aliases` 逆映射回源节点；缺少可用映射时返回真实快照节点 UUID，不伪造 ID。

状态和时间完全来自当前数据库记录。时间字段可以为 `null`：现有引擎的 `NodeExecution.started_at` 即使在 completed 记录中也可能未记录，接口不会用请求时间填充或制造耗时。`error_message` 为空时返回空字符串，否则只返回首行、最多 300 字符，并隐藏常见凭据模式和 URL；这不是日志或完整堆栈接口。

该摘要不返回 config、credentials、logs 或节点 input / output，也不递归开放子工作流调试能力。同应用的有效 viewer 可读；外部应用、不同应用的 request ID、未知 request 或没有关联执行均明确 404。应用 Key 仍被管理路由拒绝（401），其他写方法返回 405；没有增加取消、重试、恢复等控制权限。隐藏 Workflow / Node / 通用 Execution 的原 API 继续返回 404。

## 可选发布门禁和 live corpus

发布者可 PATCH `/api/v1/applications/{application_id}/`：

```json
{"required_evaluation_suite_id":"<本应用测试集 UUID>"}
```

传 `null` 明确解除门禁。启用时必须选择本应用至少有一条启用用例的未删除套件。发布除了既有真实单次测试成功的条件，还要求当前草稿 fingerprint、当前套件 revision、全部启用用例及当前知识内容都匹配的完整通过批次：`passed=total=启用数`，`failed/errors/skipped=0`。部分选择、旧配置、旧用例或知识内容漂移不能满足门禁，返回 409 `evaluation_required`。发布版本通过 `evaluation_run_id` 固定其证据，不会被以后新的评测替换。

知识应用固定检索配置和提示词，但文档 / 分块继续采用 **live 内容**，不会复制出完整不可变知识语料版本。批次记录开始和结束的 corpus signature；内容变化后，旧证据不能作为当前发布门禁通过依据。知识发布事务按 `Application → DocumentCollection → Suite` 获取锁；正式内容新增、处理提交 / 失败、编辑、删除及管理后台批量删除共用 Collection 锁，多个 Collection 按 UUID 排序，防止签名检查与发布提交间插入内容变更。

比较接口只接受同应用、同套件的两个非在途批次。用例变化标记 `added/removed/modified`；同一用例由通过变为非通过为 `regressed`，反之为 `improved`，其他稳定状态为 `unchanged`。两个批次的起止 corpus signature 必须一致；否则返回 `corpus_matches=false`、警告，并将相应用例比较标为 `inconclusive`。终止或失败批次也不能据此直接归因为版本质量变化。跨版本比较不等于冻结知识内容，外部模型本身的变化也没有被该 API 消除。

`GET .../readiness/` 提供配置、内容与索引准备情况，`connection_verified=false` 不会假冒真实连通性证明。空知识库、缺失配置或过时索引可能阻断准备状态；真实连接和结果仍需运行应用测试验证。

模型部署节点的四平台配置仍可保存，但真实部署适配器尚未接入，已列入 `UNIMPLEMENTED_INTEGRATIONS`。工作流 validate / execute、App readiness / test 明确拒绝 `model_deployment`；不再返回伪 endpoint 或假部署成功，也不能用该节点的旧假成功获取发布证据。后续真实服务接入不属于当前应用回归 API 的已完成能力。

## 已记录验证与范围

- `tests/backend/test_application_regressions.py`：真实 HTTP / ORM、实际工作流输出、固定目标、九类断言边界、幂等、投递失败、取消、权限、导入回滚、发布门禁及 corpus 比较。
- `tests/backend/test_application_readiness.py` 与 `tests/backend/test_rag_content_consistency.py`：准备状态、fresh 权限、真实内容编辑 / 删除与事务回滚；RAG + 应用批次 + readiness 关联集 **109 passed，16.34 秒，exit 0**，日志 `.cache/rag-content-final.log`。
- `tests/backend/test_application_execution_trace.py`：**7 项**真实 HTTP 增量回归，包含真实本机 HTTP 节点阻塞时 running → completed 的查询变化、原节点 ID 映射、真实 nullable 时间、team viewer / 撤权、foreign App / Request、App Key 拒绝、无执行 404、短错误及原隐藏 API 隔离。含该文件的应用 / 子工作流 / 部署拒绝关联集 **118 passed，25.42 秒，exit 0**，日志 `.cache/app-execution-trace-related.log`；7 项包含其中，不另加计数。
- 最新隔离 MySQL 集合 **18 passed，23.50 秒，exit 0**，日志 `.cache/continuation-mysql-release-20261101.log`；包含此前 App 批次并发 / 幂等、门禁修改与删除竞态、发布与内容提交互斥及 6 类 RAG bulk / admin / cascade 锁边界，另加同团队默认 Store 并发唯一选择和原 member 创建者撤权后的读取 / 删除拒绝。这 18 项包含其他数据库边界，不能全部算作应用回归 API 用例。

上述集合存在覆盖交集，不能相加当作总测试数。最新全后端回归、Chrome 和生产镜像的最终结果由本轮总交付记录单独汇总；本文不提前宣称通过。本接口提供确定性断言及持久批量执行，尚不包含 LLM judge、统计显著性分析、远端调度服务或所有业务模块的完整评测能力。
