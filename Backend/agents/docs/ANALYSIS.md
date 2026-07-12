# Backend/agents/ 模块完整问题分析报告

> 生成时间: 2026-06-06
> 分析范围: models.py, models_desktop.py, views.py, views_desktop.py, serializers.py, serializers_desktop.py, urls.py, engine.py, debugger.py, multi_agent.py, consumers.py, routing.py, signals.py, admin.py, apps.py

---

## 一、架构概览

```
Backend/agents/
├── models.py              # Agent / AgentTool / AgentConversation / AgentExecution
├── models_desktop.py      # DesktopAgent（桌面端训练 Agent 注册）
├── views.py               # AgentViewSet / AgentConversationViewSet /
│                           #   AgentToolViewSet / AgentExecutionViewSet
├── views_desktop.py       # DesktopAgentViewSet
├── serializers.py         # 主模块序列化器
├── serializers_desktop.py # 桌面端序列化器
├── urls.py               # URL 路由（DRF DefaultRouter 嵌套）
├── engine.py             # AgentEngine + 7 个内置工具（ReAct 框架）
├── debugger.py           # AgentDebugger（步进调试服务）
├── multi_agent.py        # MultiAgentOrchestrator（多 Agent 编排）
├── consumers.py          # DesktopAgentConsumer（WebSocket 消费者）
├── routing.py            # WebSocket URL 路由
├── signals.py            # Django 信号（对话更新广播）
├── admin.py              # Django Admin 注册
├── apps.py              # App 配置
└── docs/                # 本文档目录
```

### 数据流图

```
用户请求
    │
    ▼
AgentViewSet (views.py)
    │
    ├─ chat() ───────────► create_agent_engine() ──► AgentEngine.chat()
    │                                               │
    ├─ stream_chat() ─────► AgentEngine.stream_chat() ◄── SSE Response
    │
    ├─ debug() ──────────► AgentExecution (记录)
    │
    └─ tools() ───────────► AgentEngine.TOOLS_REGISTRY

DesktopAgentViewSet (views_desktop.py)
    │
    ├─ register ──────────► DesktopAgent.objects.update_or_create()
    ├─ dispatch_training ─► channel_layer.group_send() ──► DesktopAgentConsumer
    └─ heartbeat ─────────► status / last_seen 更新

DesktopAgentConsumer (consumers.py)
    │
    ├─ receive: agent_registered / training_progress / training_complete / ...
    └─ send: training_command / get_status / pong
```

---

## 二、问题清单（按严重程度分级）

> 以下标记 ✓ = 已修复，— = 待处理。

### P0 - 阻断性问题（4个）

- [x] ~~P0-1: `stream_chat` 中 `message_count` 未更新~~ ✓
- [x] ~~P0-2: `stream_chat` 流异常时用户消息已追加但不完整~~ ✓（补偿回滚机制）
- [x] ~~P0-3: `views_desktop.py` 缺少 `models` 导入~~ ✓
- [x] ~~P0-4: `config/constants.py` 可能不存在~~ ✓（已验证存在）



**文件**: `views.py`
**位置**: 第 148 行、第 165 行

**问题**: 用户消息追加到 `conversation.messages` 但未增加 `message_count`。助手消息追加后也未增加计数。导致 `message_count` 与实际消息数严重不符。

```python
# views.py:144-148 —— 用户消息追加后 message_count 未更新
conversation.messages.append({
    'role': 'user',
    'content': message
})
conversation.save()  # message_count 未 += 1

# views.py:162-166 —— 助手消息追加后 message_count 也未更新
conversation.messages.append({
    'role': 'assistant',
    'content': full_response
})
conversation.save()  # message_count 未 += 1
```

**对比 `chat()` 方法**（第 99-116 行）：正常更新了 `message_count`。

**修复方案**: 在 `stream_chat` 的 `generate()` 中，追加用户消息后 `conversation.message_count += 1`；追加助手消息后 `conversation.message_count += 1`。

---

#### P0-2: `chat` 和 `stream_chat` 消息保存逻辑不一致

**文件**: `views.py`
**位置**: 第 99-116 行 vs 第 152-166 行

| 行为 | `chat()` | `stream_chat()` |
|------|----------|-----------------|
| 用户消息追加 | 立即 `.save()` | 立即 `.save()` |
| 助手消息追加 | 立即 `.save()` | 流结束时 `.save()` |
| 中途异常 | 无回滚 | 用户消息已追加但不完整 |
| `message_count` | 每次 +1（共 +2） | 两者都未 +1 |

**修复方案**: 统一为 `stream_chat` 中在追加用户消息后立即 `message_count += 1`，追加助手消息后立即 `message_count += 1`，并加 try-except 回滚。

---

#### P0-3: `views_desktop.py` 缺少 `models` 导入

**文件**: `views_desktop.py`
**位置**: 第 103 行、第 178 行

```python
# 第 103 行使用 models.Q，但导入在第 178 行
.filter(
    models.Q(owner=request.user) | models.Q(owner__isnull=True)
)

# 第 178 行 —— 导入放在文件末尾
from django.db import models
```

**影响**: `available()` 方法运行时 `models` 未定义，`NameError`。

**修复方案**: 将 `from django.db import models` 移到文件顶部。

---

#### P0-4: `config/constants.py` 可能不存在

**文件**: `models.py`
**位置**: 第 14-19 行

```python
from config.constants import (
    DEFAULT_LLM_MODEL,
    DEFAULT_TEMPERATURE,
    DEFAULT_MAX_TOKENS,
    DEFAULT_CONTEXT_WINDOW,
)
```

如果 `config/constants.py` 不存在或这些常量未定义，`models.py` 无法导入，整个 `agents` app 无法加载。

**修复方案**: 确认 `config/constants.py` 存在且包含所有需要的常量，或在 `models.py` 中用硬编码默认值兜底。

---

### P1 - 严重问题（8个）

> 以下标记 ✓ = 已修复，— = 待处理。

- [x] ~~P1-1: `engine.py` 重复定义常量~~ ✓
- [x] ~~P1-2: `stream_chat` 缺少记忆累积~~ ✓
- [x] ~~P1-3: `chat` 未传入历史消息~~ ✓（`create_agent_engine` 预加载对话历史）
- [x] ~~P1-4: `create_agent_engine` API key 读取错误~~ ✓
- [x] ~~P1-5: `DesktopAgentViewSet` 权限混用~~ ✓
- [x] ~~P1-6: `token_count` 恒为 0~~ ✓（chars/4 估算）
- [x] ~~P1-7: `engine.py` 缺少 `import ast`~~ ✓
- [x] ~~P1-7b: `engine.py` `chat()` 未绑定 tools~~ ✓（实现了 `_react_chat` ReAct 工具循环，支持多轮 tool_call，支持 Ollama 降级）



**文件**: `engine.py`
**位置**: 第 28-34 行

```python
DEFAULT_NUM_RESULTS = 5
DEFAULT_MAX_LENGTH = 2000
MAX_TOOL_ITERATIONS = 5

DEFAULT_MAX_LENGTH = 2000    # 重复
DEFAULT_NUM_RESULTS = 5       # 重复
MAX_TOOL_ITERATIONS = 5      # 重复
```

**修复方案**: 删除重复定义（第 32-34 行）。

> ✓ 已修复：删除了第 32-34 行的重复定义。

---

#### P1-2: `stream_chat` 缺少记忆累积

**文件**: `engine.py`
**位置**: 第 729-751 行

`stream_chat` 生成器在完成后没有把对话追加到 `_history`，导致上下文丢失。

```python
# 当前代码 —— 没有更新 self._history
def stream_chat(self, message: str):
    for chunk in self.llm.stream(messages):
        yield {"type": "content", "content": chunk.content}
    yield {"type": "done"}  # 没有追加到 _history
```

**修复方案**: 在生成器结束时，收集 `full_response`，追加到 `self._history`。

> ✓ 已修复：生成器完成后追加 user/assistant 消息到 `_history`，异常时追加部分响应。

---

#### P1-3: Agent 模块完全未实现 ReAct 工具调用循环

**文件**: `engine.py`
**位置**: 第 683-727 行

`chat()` 方法直接调用 `llm.invoke(messages)` 不带 tools，`tool_calls` 永远返回 `None`。`AgentEngine` 初始化时虽然注册了 7 个工具，但从未在 LLM 调用中实际使用。

**现状**:
```python
# engine.py:705 —— 没有绑定 tools 参数
response = self.llm.invoke(messages)
```

**修复方案**: 使用 LangChain 的 tool calling API 实现 ReAct 循环（参考 LangChain AgentExecutor）。

---

#### P1-4: `create_agent_engine` 访问不存在的 User 属性

**文件**: `engine.py`
**位置**: 第 764-765 行

```python
api_key = None
if agent_model.owner:
    api_key = getattr(agent_model.owner, 'openai_api_key', None)
```

User 模型没有 `openai_api_key` 字段，会返回默认值 `None`。应从 `settings` 或其他配置源读取。

**修复方案**: 从 `settings.OPENAI_API_KEY` 或 `agent_model.settings` 中读取 API key，移除对 `owner.openai_api_key` 的依赖。

---

#### P1-5: `DesktopAgentViewSet` 权限混用

**文件**: `views_desktop.py`
**位置**: 第 27 行、第 35-37 行

```python
permission_classes = [AllowAny]  # 允许任何人访问

def get_queryset(self):
    if self.request.user.is_authenticated:
        return DesktopAgent.objects.filter(owner=self.request.user)
    return DesktopAgent.objects.filter(owner__isnull=True)  # 未登录也能看到无主 agents
```

未登录用户能访问所有 `owner__isnull=True` 的 DesktopAgent 信息。

**修复方案**: 将 `permission_classes` 改为 `[IsAuthenticated]`，对 `register` 和 `heartbeat` 用 `@permission_classes([AllowAny])` 单独覆盖。

---

#### P1-6: `token_count` 永远为 0

**文件**: `models.py`
**位置**: 第 147 行

`AgentConversation` 的 `token_count` 字段在创建和更新时从未被赋值。`message_count` 在 `chat()` 中更新了但 `token_count` 没有。

**修复方案**: 接入 `tiktoken` 或类似库，在追加消息时计算 token 数。

---

#### P1-7: `engine.py` 缺少 `import ast`

**文件**: `engine.py`
**位置**: 第 98-99 行

`CalculatorTool.run()` 使用了 `ast.parse()` 但文件顶部没有 `import ast`。

**修复方案**: 在 `engine.py` 顶部添加 `import ast`。

---

#### P1-8: `available()` 方法重复构造查询

**文件**: `views_desktop.py`
**位置**: 第 88-108 行

```python
# 第 93-96 行先过滤了
agents = DesktopAgent.objects.filter(
    gpu_available=True, status__in=['online', 'training']
)

# 第 99-106 行 if 分支完全重新构造了查询，上面的结果被丢弃
if request.user.is_authenticated:
    agents = DesktopAgent.objects.filter(gpu_available=True).filter(
        models.Q(owner=request.user) | models.Q(owner__isnull=True)
    ).filter(status__in=['online'])
```

**修复方案**: 删除第 93-96 行的查询，只保留 if 分支内的逻辑。

---

### P2 - 功能缺陷（10个）

> 以下标记 ✓ = 已修复，— = 待处理。

- [x] ~~P2-1: `AgentConversation.updated_at` 无索引~~ ✓
- [x] ~~P2-2: `AgentConversation` 无复合唯一索引~~ ✓
- [x] ~~P2-3: `debugger.py` 全局单例内存泄漏~~ ✓（已添加 LRU 容量限制 + TTL 过期清理）
- [x] ~~P2-4: `AgentDebugger` key 类型不一致~~ ✓
- [x] ~~P2-5: `AgentTool` 模型与引擎脱节~~ — 设计选择：引擎读 `Agent.tools`（JSON列表）作为工具来源，`AgentTool` 模型仅用于 Admin UI 元数据管理，非运行时绑定
- [x] ~~P2-6: `BaseAgent` 三个核心方法未实现~~ ✓（`MultiAgentWrapper.think()` 为各角色实现了 LLM 驱动的 `_build_*_prompt` 方法；`act()` 改为 async-safe；添加 `ThreadPoolExecutor` 解决 GIL 问题）
- [x] ~~P2-7: `BaseAgent` 没有 `model`/`temperature` 参数传递~~ ✓
- [x] ~~P2-8: `started_at` 手动赋值冗余~~ ✓
- [x] ~~P2-9: `exchange_count` 计算逻辑错误~~ ✓
- [x] ~~P2-10: `running` 状态从未使用~~ ✓（`debug()` 现在使用三态）

### P3 - 代码规范问题（10个）

> 以下标记 ✓ = 已修复，— = 待处理。

- [x] ~~P3-1: `engine.py` 重命名 `AgentTool` → `BaseTool`~~ ✓
- [x] ~~P3-2: `views_desktop.py` import 位置错误~~ ✓
- [x] ~~P3-3: `multi_agent.py` 函数内重复导入~~ ✓
- [x] ~~P3-4: `consumers.py` 导入了未使用的 `json`~~ ✓
- [x] ~~P3-5: `debugger.py` `datetime` 导入~~ ✓
- [x] ~~P3-6: `models.py` 从 `config.constants` 导入~~ ✓
- [x] ~~P3-7: `AgentListSerializer` 缺少字段~~ ✓
- [x] ~~P3-8: `tools_remove` 类型安全~~ ✓
- [x] ~~P3-9: debugger 用 `__dict__`~~ ✓
- [x] ~~P3-10: `get_status` agents 返回值~~ ✓

### P4 - 边界情况（8个）

> 以下标记 ✓ = 已修复，— = 待处理。

- [x] ~~P4-1: `stream_chat` 流异常时用户消息已追加但不完整~~ ✓
- [x] ~~P4-2: `available()` 查询未过滤 `supports_yolo_training`~~ ✓
- [x] ~~P4-3: `stream_chat` SSE Chrome 兼容性~~ ✓（每 10 chunks 发送 ping comment 防止超时）
- [x] ~~P4-4: `cloud_url` 字段无人读取~~ ✓
- [x] ~~P4-5: `AgentConversation` ordering 缺索引~~ ✓（已在 `Meta.indexes` 中添加）
- [x] ~~P4-6: `plan.get("steps", [])` 假设 plan 是 dict~~ ✓
- [x] ~~P4-7: `conversation_id` 返回值类型问题~~ ✓
- [x] ~~P4-8: `is_active` 字段没有任何代码检查~~ ✓

**文件**: `models.py`
**位置**: 第 157 行

`ordering = ['-updated_at']` 依赖的字段没有索引，高并发下查询会慢。

**修复方案**: 添加 `models.Index(fields=['-updated_at'])` 到 Meta.indexes。

---

#### P2-2: `AgentConversation` 无复合唯一索引

**文件**: `models.py`
**位置**: 第 123-161 行

一个用户和一个 Agent 的对话应该只有一条记录，但模型没有唯一约束。可能产生重复对话记录。

**修复方案**: 在 `Meta` 中添加 `unique_together = [['agent', 'user']]`。

---

#### P2-3: `debugger.py` 全局单例内存泄漏

**文件**: `debugger.py`
**位置**: 第 429-442 行

```python
_debuggers: Dict[int, AgentDebugger] = {}  # 永不清理
```

**修复方案**: 实现 LRU 缓存或定期清理策略，或将调试状态持久化到 DB。

---

#### P2-4: `AgentDebugger` 接受 UUID 但字典 key 类型不匹配

**文件**: `debugger.py`
**位置**: 第 176 行

`views.py` 传入的是 UUID 对象，而 `_debuggers` 字典的 key 类型可能是 UUID 或整数，不一致。

**修复方案**: 统一使用 UUID 字符串作为 key。

---

#### P2-5: `AgentTool` 模型和 `AgentEngine.TOOLS_REGISTRY` 完全脱节

**文件**: `models.py` vs `engine.py`

- `AgentTool` 模型可以存储工具配置（`config` JSONField）
- `AgentEngine` 只读 `Agent.tools` JSON 列表，完全不读 `AgentTool` 模型
- `AgentToolViewSet` 能 CRUD 工具配置，但这些配置永远不会被引擎使用

**修复方案**: 让 `AgentEngine` 从 `AgentTool` 模型读取工具配置，或废弃 `AgentTool` 模型。

---

#### P2-6: `BaseAgent` 三个核心方法未实现

**文件**: `multi_agent.py`
**位置**: 第 66-76 行

```python
async def think(self, context: Dict[str, Any]) -> str:
    raise NotImplementedError  # 未实现

async def act(self, thought: str) -> TaskResult:
    raise NotImplementedError  # 未实现

async def reflect(self, result: TaskResult) -> str:
    raise NotImplementedError  # 未实现
```

**影响**: `MultiAgentOrchestrator` 无法真正运行，`multi_agent.py` 的所有编排逻辑都是空壳。

---

#### P2-7: `multi_agent.py` 的 `BaseAgent` 没有 `model`/`temperature` 参数传递

**文件**: `multi_agent.py`
**位置**: 第 46-65 行

`BaseAgent.__init__` 接收了 `model` 和 `temperature` 但存为实例变量，而 `MultiAgentWrapper` 的 `think()` 只是透传 task，没有用这些参数调用 LLM。

---

#### P2-8: `AgentExecution.started_at` 使用 `auto_now_add` 又手动赋值

**文件**: `models.py:202` vs `views.py:208`

```python
# models.py —— auto_now_add=True
started_at = models.DateTimeField(auto_now_add=True, verbose_name='开始时间')

# views.py —— 手动赋值（多余）
started_at=timezone.now(),
```

`auto_now_add=True` 在首次保存时自动设为当前时间，手动赋值是多余的。

---

#### P2-9: `AgentExecution.exchange_count` 计算逻辑错误

**文件**: `serializers.py`
**位置**: 第 72-83 行

```python
def get_exchange_count(self, obj):
    count = 0
    if obj.input_data and isinstance(obj.input_data, dict) and 'message' in obj.input_data:
        count += 1
    if obj.output_data and isinstance(obj.output_data, dict) and 'response' in obj.output_data:
        count += 1
    return count
```

这个方法把 `input` 有数据算一次、`output` 有数据算一次，得出 0/1/2 的值。Exchange count 的语义是用户-助手对话轮次，这个计算方式完全不对。

---

#### P2-10: `AgentExecution` 的 `running` 状态从未被使用

**文件**: `models.py:191` vs `views.py:202`

`debug()` 直接创建 `completed` 或 `failed`，没有中间 `running` 态。如果需要长时间运行的 Agent 执行，无法追踪进度。

---

### P3 - 代码规范问题（10个）

> 以下标记 ✓ = 已修复，— = 待处理。

- [x] ~~P3-1: `engine.py` 重命名 `AgentTool` → `BaseTool`~~ ✓
- [x] ~~P3-2: `views_desktop.py` import 位置错误~~ ✓（已在P0-3修复）
- [x] ~~P3-3: `multi_agent.py` 函数内重复导入~~ ✓（已在第一批修复）
- [x] ~~P3-4: `consumers.py` 导入了未使用的 `json`~~ ✓
- [x] ~~P3-5: `debugger.py` `datetime` 导入~~ ✓（移至顶部）
- [x] ~~P3-6: `models.py` 从 `config.constants` 导入~~ ✓（已验证存在）
- [x] ~~P3-7: `AgentListSerializer` 缺少字段~~ ✓（已在第一批修复）
- [x] ~~P3-8: `tools_remove` 类型安全~~ ✓
- [x] ~~P3-9: debugger 用 `__dict__`~~ ✓（已在第一批修复）
- [x] ~~P3-10: `get_status` agents 返回值~~ ✓（已在第一批修复）

**文件**: `engine.py`
**位置**: 第 37 行

```python
class AgentTool:  # 遮蔽了同名的 models.AgentTool 模型
```

`AgentTool` 类名和 `models.AgentTool` 模型类同名，可能导致导入混淆。

---

#### P3-2: `views_desktop.py` 第 178 行 import 位置错误

导入放在文件末尾，导致方法中 `models.Q` 找不到。

---

#### P3-3: `multi_agent.py` 函数内重复导入

**文件**: `multi_agent.py`
**位置**: 第 408 行

`create_multi_agent_chain()` 函数内部导入 `AgentEngine`，但顶部没有导入。

---

#### P3-4: `consumers.py` 导入了未使用的 `json`

**文件**: `consumers.py`
**位置**: 第 12 行

---

#### P3-5: `debugger.py` `complete_execution` 方法内导入

**文件**: `debugger.py`
**位置**: 第 388 行

`from datetime import datetime` 在函数内部导入，而文件顶部已经 `import datetime`。

---

#### P3-6: `models.py` 从 `config.constants` 导入

**文件**: `models.py`
**位置**: 第 14-19 行

需要确认 `config/constants.py` 存在，否则无法加载。

---

#### P3-7: `AgentListSerializer` 缺少 `tenant` 和 `owner` 字段

**文件**: `serializers.py`
**位置**: 第 34-44 行

列表页需要展示归属信息，但序列化器缺失。

---

#### P3-8: `tools_remove` 不验证 tool 类型

**文件**: `views.py`
**位置**: 第 276-278 行

```python
if tool_name in agent.tools:
    agent.tools.remove(tool_name)
```

如果 `agent.tools` 不是列表类型会抛异常。

---

#### P3-9: `debugger.py` `to_dict` 中 `breakpoints` 用 `__dict__`

**文件**: `debugger.py`
**位置**: 第 167 行

`bp.__dict__` 对 dataclass 不够稳定，应用 `dataclasses.asdict(bp)`。

---

#### P3-10: `multi_agent.py` `MultiAgentOrchestrator.get_status` 返回 `agents` 值错误

**文件**: `multi_agent.py`
**位置**: 第 283 行

```python
"agents": [a.name for a in self.agents.values()]
```

`self.agents` 是 `Dict[str, BaseAgent]`，应该 `self.agents.keys()` 或直接 `list(self.agents.keys())`。

---

### P4 - 业务逻辑问题（8个）

#### P4-1: `Agent.agent_type` 没有任何业务分支

**文件**: `models.py:56-61`, `engine.py`, `views.py`

`conversational`、`task`、`research`、`coding` 四种类型在引擎和视图中没有任何区分处理。类型字段纯展示用途。

---

#### P4-2: `Agent.skills` 字段没有任何代码读取

**文件**: `models.py:71`

> ✓ 已部分处理：`chat`/`stream_chat`/`debug` 添加了 `is_active` 检查，但 `skills` 字段本身仍未使用。需后续打通。

`skills` JSON 字段可以存任意数据，但没有任何视图或引擎读取/使用这个字段。

---

#### P4-3: `DesktopAgent.supports_yolo_training` 从未被业务逻辑检查

**文件**: `models_desktop.py:56`

> ✓ 已修复：`dispatch_training` 现在检查 `supports_yolo_training`。

---

#### P4-4: `Agent.context_window` 语义不一致

**文件**: `models.py:73` vs `engine.py:673`

> ✓ 已修复：引擎中添加了注释说明 `context_window` 实际为消息对数限制，非 token 数。字段名暂保留以避免迁移。

---

#### P4-5: `DesktopAgent.cloud_url` 从未被使用

**文件**: `models_desktop.py:68`

> ✓ 已修复：`dispatch_training` 响应中返回 `cloud_url`。#### P4-6: `multi_agent.py` `plan.get("steps", [])` 假设 plan 是 dict

**文件**: `multi_agent.py:184`

如果 `coordinator.think()` 返回非 dict（如字符串），静默返回空列表并跳过执行。

---

#### P4-7: `AgentExecution.conversation_id` 返回值类型问题

**文件**: `views.py:340`

```python
'conversation_id': execution.conversation_id  # 外键字段返回的是关联对象
```

Django 外键字段直接访问返回关联对象（不是 UUID 字符串）。前端收到的是嵌套对象而非字符串。

---

#### P4-8: `Agent` 的 `is_active` 字段没有任何代码检查

**文件**: `models.py:76`

`is_active` 字段可以设为 False，但所有视图（`chat`、`stream_chat`、`debug` 等）都没有检查这个字段。

---

## 三、可实现的功能扩展

| 功能 | 现状 | 优先级 | 预估工时 |
|------|------|--------|----------|
| ReAct 工具调用循环 | 使用 `bind(tools)` 实现多轮工具循环 | P1 | ✓已实现，支持 Ollama 降级 |
| Token 计数与计费 | 使用 chars/4 估算 | P1 | 0.5天（✓已修复，精确计费需 tiktoken） |
| 修复 `stream_chat` 记忆累积 | 上下文丢失 | P1 | 0.5天（✓已修复） |
| `AgentTool` 模型与引擎打通 | 引擎读 `Agent.tools` JSON；模型仅 Admin 元数据 | P2 | — 设计选择 |
| 多 Agent 协作编排 | 为各角色实现 LLM 驱动的 `_build_*_prompt` | P2 | ✓已实现 |
| Agent 对话摘要压缩 | summary 字段空置 | P2 | 1-2天 |
| `available()` 查询优化 | 重复查询逻辑 | P2 | 0.5天（✓已修复） |
| Agent 版本快照 | 无 | P3 | 1天 |
| Agent 模板导入/导出 | 无 | P3 | 0.5天 |
| 修复 `is_active` 检查 | 字段未使用 | P3 | 0.5天（✓已修复） |
| Desktop Agent 训练资格检查 | supports_yolo_training 未用 | P3 | 0.5天（✓已修复） |
| `context_window` 语义修正 | 概念混淆 | P3 | 1天（✓已修复） |
| Debugger 持久化（DB） | 全局内存单例 | P3 | 1-2天 |

---

## 四、快速修复清单（按依赖排序）

> 以下清单标记 ✓ = 已完成，— = 待处理。

### 第一批（独立，可立即修复）

- [x] ~~1. `engine.py` — 添加 `import ast`~~ ✓
- [x] ~~2. `engine.py` — 删除重复常量定义（第 32-34 行）~~ ✓
- [x] ~~3. `views_desktop.py` — 将 `from django.db import models` 移到文件顶部~~ ✓
- [x] ~~4. `views_desktop.py` — 删除 `available()` 中第 93-96 行的冗余查询~~ ✓
- [x] ~~5. `serializers.py` — `AgentListSerializer` 添加 `tenant` 和 `owner` 字段~~ ✓
- [x] ~~6. `serializers.py` — 修正 `exchange_count` 语义（单轮对话返回1）~~ ✓
- [x] ~~7. `multi_agent.py` — `get_status` 修正 `agents` 列表推导式~~ ✓
- [x] ~~8. `multi_agent.py` — 移除 `create_multi_agent_chain` 内重复导入~~ ✓
- [x] ~~9. `debugger.py` — 用 `dataclasses.asdict()` 替代 `__dict__`~~ ✓

### 第二批（需要逻辑修改）

- [x] ~~10. `views.py:stream_chat` — 修复 `message_count` 更新~~ ✓
- [x] ~~11. `views.py:stream_chat` — 添加异常回滚~~ ✓
- [x] ~~12. `engine.py:stream_chat` — 追加消息到 `_history`~~ ✓
- [ ] 13. `engine.py:chat` — 实现 ReAct 工具调用循环（待架构设计）
- [x] ~~14. `models.py` — 添加 `AgentConversation` 复合唯一索引~~ ✓
- [x] ~~15. `models.py` — 添加 `AgentConversation.updated_at` 索引~~ ✓
- [x] ~~16. `views_desktop.py` — 修复 `permission_classes`~~ ✓
- [x] ~~17. `engine.py:create_agent_engine` — 修复 API key 读取逻辑~~ ✓
- [x] ~~18. `models.py` — 确认 `config/constants.py` 存在~~ ✓

### 第三批（需要架构设计）

- [ ] 19. `multi_agent.py` — 实现 `BaseAgent` 三个核心方法
- [ ] 20. `debugger.py` — 将调试状态持久化到 DB（替换全局内存单例）
- [ ] 21. Token 计数接入 `tiktoken`
- [ ] 22. `Agent.skills` 字段的实际使用逻辑
- [ ] 23. Desktop Agent 训练资格检查
- [ ] 24. `AgentExecution.running` 状态的实际使用逻辑

### 第四批（代码规范补充）

- [x] ~~`debugger.py` — 移除未使用的 `asyncio` / `Callable` 导入~~ ✓
- [x] ~~`debugger.py` — `datetime` 导入提到顶部~~ ✓
- [x] ~~`consumers.py` — 移除未使用的 `json` 导入~~ ✓
- [x] ~~`engine.py` — 重命名 `AgentTool` → `BaseTool`~~ ✓
- [x] ~~`engine.py` — 移除未使用的 `Callable` / `Union` 导入~~ ✓
- [x] ~~`engine.py` — 添加 `context_window` 语义注释~~ ✓
- [x] ~~`multi_agent.py` — `plan` 非 dict 容错处理~~ ✓
- [x] ~~`multi_agent.py` — `MultiAgentWrapper` 传递 `model`/`temperature`~~ ✓
- [x] ~~`views.py:chat/stream_chat/debug` — 添加 `is_active` 检查~~ ✓
- [x] ~~`views.py:debug` — `execution_id` 返回字符串~~ ✓
- [x] ~~`views.py:debug` — 使用 `running` 状态并设置 `completed_at`~~ ✓
- [x] ~~`views.py:debug` — 添加异常处理分支~~ ✓
- [x] ~~`views.py:debug_session_detail` — `id`/`conversation_id` 返回字符串~~ ✓
- [x] ~~`views.py:tools_remove` — 添加 `isinstance(list)` 类型安全~~ ✓
- [x] ~~`views.py:stream_chat` — 异常补偿（回滚不完整的用户消息）~~ ✓
- [x] ~~`views_desktop.py:available` — 过滤 `supports_yolo_training`~~ ✓
- [x] ~~`views_desktop.py:dispatch_training` — 检查 `supports_yolo_training`~~ ✓
- [x] ~~`views_desktop.py:dispatch_training` — 返回 `cloud_url`~~ ✓
- [x] ~~`signals.py:conversation_updated` — `conversation_id` 返回字符串，`message_count` 用字段值~~ ✓
- [x] ~~`signals.py:execution_completed` — 移除错误的 `updated_at=started_at` 更新~~ ✓
- [x] ~~`engine.py:create_agent_engine` — 新增 `conversation` 参数，预加载对话历史~~ ✓
- [x] ~~`views.py` — 所有 `chat`/`stream_chat` 方法传入 conversation~~ ✓
- [x] ~~`views.py` — 所有消息保存时同步更新 `token_count`~~ ✓
- [x] ~~`views.py:stream_chat` — 每 10 chunks 发送 SSE ping 防止 Chrome 超时~~ ✓
- [x] ~~`debugger.py` — 添加 LRU 容量限制 + TTL 过期清理~~ ✓
- [x] ~~`debugger.py` — `_evict_stale()` 移除未使用的 `timedelta` 导入~~ ✓
- [x] ~~`views.py:add_message` — 添加 `message_count` 和 `token_count` 更新~~ ✓
- [x] ~~`multi_agent.py:_run_with_coordinator` — 早期返回改为 `TaskResult`~~ ✓
- [x] ~~`multi_agent.py:_run_with_coordinator` — `reflect` 结果类型安全处理~~ ✓
- [x] ~~`multi_agent.py` — 添加 `ThreadPoolExecutor` 解决 async GIL 问题~~ ✓
- [x] ~~`multi_agent.py:MultiAgentWrapper` — 为各角色实现 `_build_*_prompt` 方法~~ ✓
- [x] ~~`multi_agent.py:MultiAgentWrapper.act` — 改为 async-safe 使用 `run_in_executor`~~ ✓
- [x] ~~`views.py:debug()` — 移除未定义的 `conversation` 引用~~ ✓（重构为不带 conversation）
- [x] ~~`views.py:debug()` — `engine` 未定义~~ ✓（在使用前调用 `create_agent_engine`）
- [x] ~~`views.py:debug()` — `engine.chat()` 抛异常时不创建 execution 记录~~ ✓（用 try/except 包裹，提前返回 failed 记录）
- [x] ~~`engine.py` — 添加 `Callable` 到 typing 导入~~ ✓
- [x] ~~`engine.py` — `get_tool` 返回类型改为 `BaseTool`~~ ✓
- [x] ~~`engine.py` — 实现 `_react_chat` ReAct 工具循环 + Ollama 降级~~ ✓
- [x] ~~`engine.py` — 重构 `chat()` 分发到 `_react_chat`/`_simple_chat`~~ ✓
- [x] ~~`engine.py` — `stream_chat` 支持 tools 配置~~ ✓
