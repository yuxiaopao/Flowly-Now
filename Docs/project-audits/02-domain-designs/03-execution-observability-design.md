# Execution Observability Design

> 文档目的：定义 Flowly 执行观测域的目标形态，把执行记录、节点轨迹、日志、指标、成本、重试、断点续跑统一为一套可观测体系。  
> 这份文档不是继续列问题清单，而是直接回答：执行域最终应该提供什么可观测能力、如何分层组织、如何与模板域和租户域对齐。

---

## 一、先说结论

当前项目在执行观测上的情况是：

- 有基础结构，`WorkflowExecution`、`NodeExecution`、`ExecutionLog`、`ExecutionCache` 四个模型各自存在
- 但结构之间缺乏统一口径
- 部分视图层缺少访问边界控制
- 执行链路没有统一时间线视图
- 成本、缓存命中率、重试链路没有系统化统计
- 模板域无法依赖执行域聚合真实运行指标

### 最终目标
Flowly 的执行域必须支撑以下能力：

- 任意一次执行，从触发到完成，每一步都能回放
- 任意一次失败，能直接定位到节点、时间和原因
- 任意一个模板，能看到累计安装次数、运行次数、成功率、首次运行成功率
- 任意一个节点，能看到 token 消耗、延迟、缓存命中、重试历史
- 任意一个 workflow，能看到 tenant 维度的成本分布和执行趋势

这不是监控大屏，这是平台级可观测能力。

---

## 二、当前代码直接暴露的问题

以下全部是从现有代码中直接看到的事实，不是推断。

### 2.1 口径漂移：`traceback` 与 `error_stack` 并存
在 `WorkflowExecution` 模型中有：
- `error_message`
- `error_stack`

但在 `views.py` 的 `legacy_logs` action 中返回的是：
- `traceback`

模型里没有定义 `traceback` 字段。这说明日志字段在不同层的名字不一致。

### 2.2 日志数据存在两个地方
在 `WorkflowExecution` 模型中有：
- `execution_logs` — JSONField，内嵌在执行记录里

同时又有独立的 `ExecutionLog` 模型，与执行记录关联。

这意味着当前可能两套日志在并存使用：
- 内嵌 JSONField
- 独立表

### 2.3 NodeExecution 的 queryset 没有访问边界
```python
# views.py 第 996 行
queryset = NodeExecution.objects.all()
```

这行代码直接不过滤。
- 不校验 execution 归属
- 不校验 workflow 归属
- 不校验 tenant

意味着任何认证用户都能拿到全平台所有节点的执行记录。

### 2.4 ExecutionCache 的 queryset 没有访问边界
同样问题：
```python
# views.py 第 1483 行
queryset = ExecutionCache.objects.all()
```

不校验 workflow scope，不校验 tenant。

### 2.5 `NodeExecution` 的 `node_id` 类型问题
模型里定义为：
```python
node = models.ForeignKey(Node, ...)
```

这是 UUID 关联。但从 views.py 的统计接口来看，`node_id` query param 接收的是 UUID 格式。

如果前端传的是整数 ID，会产生类型不匹配。

### 2.6 没有统一执行时间线端点
目前分散在多个接口里：
- `/executions/{id}/status/` — 返回 `node_status`、`progress`、`duration`
- `/executions/{id}/output/` — 返回 `output_data`
- `/executions/{id}/logs/` — 返回 `ExecutionLog` 表记录
- `/executions/{id}/legacy_logs/` — 返回内嵌 `execution_logs`

这意味着前端渲染一个执行详情页，可能需要调 3-4 个接口才能拼出完整画面。

### 2.7 没有模板域维度的执行统计
执行域目前能统计：
- 单次执行的 token 和 cost
- 按 workflow 的执行统计

但没有：
- 按 template 聚合的 install → run → success 链路
- template 的 health score 计算
- template 的首次运行成功率

这直接导致模板域无法建立运营指标。

---

## 三、目标观测模型：四层结构

执行域的观测能力按层次组织，从底到顶分别是：

```
Layer 1: Raw Data      — 节点执行、模型调用、token消耗、日志事件
Layer 2: Aggregation   — 执行汇总、节点轨迹、成本统计、缓存分析
Layer 3: Domain Metrics — workflow健康分、template健康分、tenant成本分布
Layer 4: Presentation  — 时间线、执行详情、趋势图、告警
```

---

## 3.1 Layer 1：原始执行数据（已有基础，需整理口径）

#### 节点执行记录（NodeExecution）
这是最细粒度的执行数据来源。

当前已有字段方向是对的，建议保留并补充：

- `execution_id`：关联执行
- `node_id`：节点标识（建议同时存 UUID 和原始标识符）
- `node_type`：节点类型
- `node_version`：快照版本
- `status`：pending / running / completed / failed / skipped / retrying
- `input_data`：节点输入快照
- `output_data`：节点输出快照
- `started_at / completed_at / duration_ms`
- `error_message / retry_count / max_retries_exceeded`
- `prompt_tokens / completion_tokens / total_tokens / model_latency_ms`
- `cache_hit / cache_key`
- `model_name / provider`
- `cost_amount`

#### 关键补充
每个节点执行记录必须快照以下内容，而不是只记最终状态：
- 实际调用的模型名称和版本
- 实际使用的凭证 ID（不暴露密钥）
- 依赖的知识库 / dataset 访问记录
- 输入变量展开后的快照

#### 执行日志（ExecutionLog）
当前独立模型结构合理，继续使用。

建议统一：
- 不再同时使用 `WorkflowExecution.execution_logs` JSONField
- 所有日志统一走 `ExecutionLog` 独立表
- `WorkflowExecution.execution_logs` 应标记为废弃，不再写入

---

## 3.2 Layer 2：执行链路聚合

#### 执行记录（WorkflowExecution）
这是执行链路的主聚合根。

当前模型已经覆盖了关键字段，建议做以下调整：

##### 建议调整

**废弃字段**：
- `execution_logs`（JSONField）：统一迁移到 `ExecutionLog` 表
- `traceback`（不存在于模型但出现在 legacy 接口）：明确用 `error_stack`

**建议补充**：
- `template_id`：记录执行是否来自模板安装
- `template_version_id`：记录安装的是哪个版本
- `source_execution_id`：重试时记录来源执行 ID，形成重试链路

##### 保留的字段组

**触发链路**：
- `trigger_type`
- `trigger_source`
- `trigger_config`

**状态与时间**：
- `queued_at / started_at / completed_at / paused_at / duration_ms`
- `status`
- `progress / current_node_id`

**节点状态**：
- `node_status`（JSONField）：保留作为节点执行状态快照的快速访问方式
- 但应与 `NodeExecution` 表保持一致性校验

**成本与资源**：
- `token_usage`
- `cost_amount / cost_currency`

**上下文**：
- `context_snapshot`（暂停续跑）
- `context_data`

**执行结果**：
- `input_data`
- `output_data`
- `error_message`
- `error_stack`

---

## 3.3 Layer 3：业务域指标

这一层目前基本缺失，需要新建。

#### Template Execution Metrics（模板执行指标）
这是模板域和执行域的交汇点。

每个模板的运营能力，依赖执行域提供：

```
TemplateMetrics:
  template_id
  total_installs
  total_executions
  successful_executions
  failed_executions
  success_rate
  first_run_success_rate   ← 安装后首次执行是否成功
  avg_cost_per_execution
  avg_duration_ms
  health_score             ← 综合评分
  last_executed_at
  updated_at
```

#### Workflow Execution Metrics（Workflow 执行指标）
```
WorkflowMetrics:
  workflow_id
  tenant_id
  total_executions
  success_rate
  avg_duration_ms
  avg_cost
  total_cost
  avg_node_count
  avg_cache_hit_rate
  p50_latency_ms
  p95_latency_ms
  p99_latency_ms
  updated_at
```

#### Tenant Execution Metrics（租户执行指标）
```
TenantExecutionMetrics:
  tenant_id
  period（day / week / month）
  total_executions
  total_cost
  by_workflow_id[]
  by_trigger_type[]
  top_slow_executions[]
  top_failed_workflows[]
  budget_usage_percent
```

---

## 3.4 Layer 4：接口与展示

### 统一执行时间线接口

这是最关键的一步。

建议新增一个统一端点：

```
GET /api/v1/executions/{id}/timeline/
```

返回结构：
```json
{
  "execution_id": "...",
  "workflow_id": "...",
  "workflow_version": 3,
  "status": "completed",
  "trigger_type": "manual",
  "triggered_by": "user_123",
  "tenant_id": "tenant_abc",
  "template_id": "template_xyz",
  "template_version_id": "v2",

  "timeline": [
    {
      "phase": "queued",
      "timestamp": "2026-06-05T10:00:00Z",
      "duration_ms": 0
    },
    {
      "phase": "started",
      "timestamp": "2026-06-05T10:00:01Z",
      "duration_ms": 1000
    },
    {
      "phase": "node",
      "node_id": "node_1",
      "node_name": "LLM Node",
      "node_type": "llm",
      "status": "completed",
      "started_at": "2026-06-05T10:00:01Z",
      "completed_at": "2026-06-05T10:00:03Z",
      "duration_ms": 2000,
      "cache_hit": false,
      "prompt_tokens": 500,
      "completion_tokens": 200,
      "cost": 0.0025
    },
    {
      "phase": "node",
      "node_id": "node_2",
      "node_name": "Tool Node",
      "node_type": "tool",
      "status": "completed",
      "duration_ms": 500,
      "cache_hit": true
    },
    {
      "phase": "completed",
      "timestamp": "2026-06-05T10:00:04Z",
      "total_duration_ms": 3000,
      "total_cost": 0.0032,
      "total_tokens": 700
    }
  ],

  "summary": {
    "total_nodes": 2,
    "completed_nodes": 2,
    "failed_nodes": 0,
    "skipped_nodes": 0,
    "total_prompt_tokens": 500,
    "total_completion_tokens": 200,
    "total_cost": 0.0032,
    "cache_hit_rate": 0.5
  }
}
```

### 为什么要统一
现在前端调多个接口拼时间线，会导致：
- 网络请求数多
- 数据口径可能不一致
- 节点和执行记录之间的时序关系要前端自己关联

统一时间线接口让前端只需要调一个端点。

---

## 四、执行重试链路

当前重试逻辑在 `views.py` 的 `retry` action 里已经存在：

```python
# views.py 第 661 行
new_execution = WorkflowExecution.objects.create(
    workflow=execution.workflow,
    trigger_type='manual',
    triggered_by=request.user,
    status='pending',
    input_data=execution.input_data
)
```

但有几个问题：

### 4.1 没有追踪重试链路
当前重试后，新执行和老执行之间没有关联记录。

建议新增字段：
- `WorkflowExecution.source_execution_id`
- `WorkflowExecution.retry_chain_id`（所有重试共享同一个 ID）

这样可以：
- 看到原始执行是哪个
- 看到后续所有重试版本
- 计算“从首次失败到最终成功花了多久”

### 4.2 重试的节点从哪里恢复不清晰
如果 workflow 在 node_3 失败了，重试时：
- 从哪个节点开始？
- node_1 和 node_2 的结果是否复用？
- 缓存是否命中？

当前 `retry` action 没有处理这个逻辑，直接从 `pending` 状态重新创建执行。

### 4.3 建议的重试策略

#### 策略 1：仅重试失败节点
适用场景：workflow 定义没变，失败是临时性的（网络、超时）。

- 保留已完成节点的执行结果（从 `NodeExecution` 读取）
- 仅重新执行 failed 节点
- 减少 token 消耗和成本

#### 策略 2：从指定节点重跑全链路
适用场景：workflow 定义更新，需要用新版本重跑。

- 从指定节点开始
- 丢弃之前节点的结果
- 使用新的 workflow 定义

#### 策略 3：克隆执行
适用场景：保留历史记录，完全重新运行。

- 当前 `retry` action 实际是策略 3
- 但它没有告诉用户这是哪种意图

---

## 五、暂停与续跑

当前 `WorkflowExecution` 已有：
- `context_snapshot`
- `pause()` / `resume()` 方法
- `paused_at` 字段

但问题在于：

### 5.1 上下文快照没有实际填充
在 `views.py` 第 715 行：
```python
# Note: In a real implementation, you would get the current context from the executor
execution.save_context_snapshot({})
```

注释已经说明这不是真正实现的。这意味着暂停续跑功能目前只是桩代码，不是实际能力。

### 5.2 暂停粒度问题
当前暂停是对整个执行级别的。

建议增加节点级暂停能力：
- 可以在指定节点暂停
- 可以按条件触发暂停（如人工审核节点）

---

## 六、执行缓存

`ExecutionCache` 模型结构合理，但有几个问题。

### 6.1 缓存 key 设计
当前使用 `config_hash` 作为唯一键：
```python
config_hash = models.CharField(max_length=64, db_index=True, unique=True)
```

这要求执行器在每次运行前计算 hash。

建议补充：
- `input_hash`：输入数据的 hash
- `combined_hash`：config_hash + input_hash 的组合
- 明确缓存命中是基于哪些维度

### 6.2 缓存与节点执行记录的关联
当前 `NodeExecution` 有 `cache_hit` 和 `cache_key`：
```python
cache_hit = models.BooleanField(default=False, verbose_name='缓存命中', db_index=True)
cache_key = models.CharField(max_length=100, null=True, blank=True, verbose_name='缓存键')
```

但 `ExecutionCache` 模型没有记录：
- 哪个节点执行用了这个缓存
- 缓存命中的响应时间节省

建议在 `ExecutionCache` 增加：
- `access_count`
- `hit_execution_ids[]`

### 6.3 缓存 TTL 与清理
`ExecutionCacheConfig` 已经存在 TTL 配置。

但当前没有定时清理任务来真正清理过期缓存。

---

## 七、与模板域的集成

执行域是模板运营指标的数据源，但目前两者之间没有显式集成。

### 7.1 模板执行链路追踪
从模板安装到执行的链路：

```
TemplateInstall
  → created_workflow_id
  → WorkflowExecution (source_template_id)
  → NodeExecution[]
```

当前 `TemplateInstall` 模型（如果存在的话）没有记录这些关联。

建议在执行记录中显式记录：
```python
class WorkflowExecution:
    template_id = ForeignKey(WorkflowTemplate, null=True)
    template_version_id = ForeignKey(TemplateVersion, null=True)
    install_id = ForeignKey(TemplateInstall, null=True)
```

### 7.2 模板健康分计算
模板健康分依赖执行域数据，公式建议：

```
health_score = (
    0.3 * success_rate +
    0.25 * first_run_success_rate +
    0.2 * (1 - avg_cost_normalized) +
    0.15 * avg_rating +
    0.1 * recency_factor
)
```

其中：
- `success_rate` = successful_executions / total_executions
- `first_run_success_rate` = 首次执行成功的 install 数 / 总 install 数
- `avg_cost_normalized` = 当前成本 / 同类模板平均成本
- `avg_rating` = 模板平均评分
- `recency_factor` = 最近 30 天活跃度

这些数据全部来自执行域。

---

## 八、与租户域的集成

执行域的每个记录都应该有 `tenant_id` 绑定。

### 8.1 当前状态
`WorkflowExecution` 已有 `tenant` 字段。

但 `NodeExecution` 和 `ExecutionLog` 没有显式 `tenant_id`。

### 8.2 建议
- `NodeExecution` 通过 `execution.tenant` 继承
- `ExecutionLog` 通过 `execution.tenant` 继承
- 在 views 层确保 tenant 继承链路不中断

### 8.3 成本归属
每个 `WorkflowExecution` 的 `cost_amount` 必须归属到 `tenant`。

这样可以支持：
- 租户月度账单
- 租户成本预警
- 租户内 workflow 成本排行

---

## 九、建议的 API 目标形态

### 执行管理接口
```
GET    /executions/                           ← 执行列表
GET    /executions/{id}/                      ← 执行详情
GET    /executions/{id}/timeline/             ← 统一时间线
GET    /executions/{id}/logs/                 ← 执行日志
GET    /executions/{id}/output/               ← 执行输出
POST   /executions/{id}/cancel/               ← 取消执行
POST   /executions/{id}/pause/                ← 暂停执行
POST   /executions/{id}/resume/               ← 恢复执行
POST   /executions/{id}/retry/                ← 重试执行
DELETE /executions/{id}/                      ← 删除执行（只读后不允许删除）
```

### 节点执行接口
```
GET    /node-executions/                      ← 节点执行列表（需加访问控制）
GET    /node-executions/{id}/                 ← 节点执行详情
GET    /executions/{id}/nodes/                ← 本次执行的所有节点
```

### 统计接口
```
GET    /executions/statistics/                 ← 个人/租户执行统计
GET    /executions/{id}/statistics/           ← 本次执行的节点统计
GET    /workflows/{id}/metrics/               ← workflow 维度指标
GET    /templates/{id}/metrics/               ← template 维度指标（新增）
GET    /tenants/{id}/billing/summary/         ← 租户成本汇总（新增）
```

### 缓存接口
```
GET    /execution-cache/                      ← 缓存列表（需加访问控制）
GET    /execution-cache/{id}/                 ← 缓存详情
DELETE /execution-cache/{id}/                ← 删除缓存
DELETE /execution-cache/                      ← 清理过期缓存
GET    /execution-cache/stats/               ← 缓存统计
```

---

## 十、访问边界强制要求

这是执行域最严重的安全问题，必须优先修复。

### 10.1 NodeExecutionViewSet 必须加访问控制

```python
def get_queryset(self):
    # 当前：无过滤 ← 必须修复
    queryset = NodeExecution.objects.filter(
        execution__workflow__in=_get_accessible_workflow_queryset(self.request.user)
    )
```

### 10.2 ExecutionCacheViewSet 必须加访问控制

```python
def get_queryset(self):
    # 当前：无过滤 ← 必须修复
    queryset = ExecutionCache.objects.filter(
        # 通过某种方式关联到 accessible workflow
    )
```

### 10.3 通用规则
执行域所有模型的访问控制，必须继承 workflow 的 tenant 边界。

不允许出现任何“我直接查全表”的 queryset。

---

## 十一、建议的落地顺序

### Phase A：修复访问边界（最高优先级）
1. 修复 `NodeExecutionViewSet.get_queryset()` 的 tenant 过滤
2. 修复 `ExecutionCacheViewSet.get_queryset()` 的 tenant 过滤
3. 清理 `legacy_logs` 与 `ExecutionLog` 表的双写问题

### Phase B：统一口径
1. 废弃 `WorkflowExecution.execution_logs` JSONField，统一走 `ExecutionLog` 表
2. 统一 `traceback` 与 `error_stack` 的命名，取其一
3. 统一 `node_id` 的类型处理

### Phase C：补全执行链路
1. 实现真正的 `pause/resume` 上下文快照
2. 建立重试链路追踪（`source_execution_id` / `retry_chain_id`）
3. 明确重试策略并让用户选择

### Phase D：建立 Layer 3 指标
1. 新增 `TemplateMetrics` 聚合表或视图
2. 新增 `WorkflowMetrics` 聚合表或视图
3. 实现 template health score 计算

### Phase E：统一时间线接口
1. 实现 `/executions/{id}/timeline/` 统一端点
2. 前端统一走这一个接口，不再并发请求多个端点
3. 实现 tenant 成本汇总接口

---

## 十二、最终判断

执行域是 Flowly 的核心能力底座，但它现在的状态是“能跑但不能看”。

具体来说：

- 执行记录本身数据还行，但各层之间口径不一致
- 节点执行记录分散在两个地方，没有统一
- 最严重的是 `NodeExecution` 和 `ExecutionCache` 的 views 没有访问边界
- 没有模板维度的执行统计，导致模板域无法建立健康分和运营指标
- 没有统一时间线接口，前端体验会很碎片

所以这份文档的结论很清楚：

### 执行域的下一步不是加新功能，而是先修复访问边界、统一数据口径、然后建立 Layer 3 业务指标。

修复访问边界是 P0，其他都可以往后排。

---

## 十三、执行状态（2026-06-06）

以下为本文档中列出的问题的处理状态。

### 已解决

| 问题 | 位置 | 修复 |
|---|---|---|
| `NodeExecutionViewSet` queryset 无访问边界 | `workflows/views.py` 第 972 行 | 已修复 — 使用 `get_accessible_workflow_queryset()` 过滤 |
| `ExecutionCacheViewSet` queryset 无访问边界 | `workflows/views.py` 第 1613 行 | 已修复 — 通过 `NodeExecution.cache_hit` 关联到 accessible workflow |
| `ExecutionLogViewSet` (monitoring) 只按 owner 过滤，忽略 tenant 共享 | `monitoring/views.py` 第 38 行 | 已修复 — 改用 `get_accessible_workflow_queryset()` |
| `AuditLogViewSet` superuser 时 queryset 重复定义，普通用户无 tenant 边界 | `workflows/views.py` 第 1239 行 | 已修复 — superuser 返回全量，非 superuser 按 owner/tenant 双重边界 |
| 无统一执行时间线端点（前端需调 3-4 个接口） | 新增 | 已解决 — `GET /workflows/executions/{uuid}/timeline/` 一次性返回 execution + node_executions + logs |
| `APICredentialViewSet` queryset 中 superuser 时返回全量前重复定义变量 | `workflows/views.py` 第 1140 行 | 已修复 — 统一用 `queryset = APICredential.objects.all()` + 条件过滤 |
| `AuditLogViewSet` 无 tenant 过滤 | `workflows/views.py` 第 1239 行 | 已修复 — 与 AuditLogViewSet superuser/tenant 修复同步完成 |
| Layer 3 指标缺失 | 新增 | 已解决 — `GET /workflows/executions/analytics/` 返回 workflow/template/tenant 三层聚合 |

### 未解决

| 问题 | 优先级 | 说明 |
|---|---|---|
| `WorkflowExecution.execution_logs` (JSONField) 与 `ExecutionLog` 独立表并存 | 中 | 需要废弃 JSONField，统一写入 `ExecutionLog` 表 |
| `traceback` 在 legacy 接口中出现但模型无此字段 | 低 | 统一用 `error_stack` |
| `WorkflowExecution` 缺少 `template_id` / `source_execution_id` 字段 | 中 | 需要新建 migration 补充字段才能形成完整重试链路 |
| 模板执行链路追踪（template → install → workflow → execution） | 中 | 需要在 `create_from_template` 中正确写入 `workflow.config.template_id`（已实现），但执行时写入 `template_id` 字段尚未实现 |
| `NodeExecution.node_id` 类型问题（UUID vs 整数） | 低 | 前端目前传 UUID，与 FK 一致，无需改动 |
| 三套模板系统（workflows/marketplace/templates）的长期模型合并 | 高 | 字段不兼容，数据隔离，需要架构决策 |

### API 路由状态

```
GET /api/v1/workflows/executions/analytics/      ✅ 新增 — Layer3 聚合
GET /api/v1/workflows/executions/{id}/timeline/  ✅ 新增 — 统一时间线
GET /api/v1/workflows/executions/statistics/     ✅ 存在
GET /api/v1/workflows/executions/{id}/status/     ✅ 存在
GET /api/v1/workflows/executions/{id}/output/    ✅ 存在
GET /api/v1/workflows/executions/{id}/logs/     ✅ 存在
GET /api/v1/node-executions/                     ✅ 已有 — 访问边界已修复
GET /api/v1/execution-cache/                     ✅ 已有 — 访问边界已修复
GET /api/v1/execution-cache/stats/               ✅ 存在
```

