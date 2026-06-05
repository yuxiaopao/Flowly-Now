# 任务 1：完善工作流执行引擎

## 任务概述

| 属性 | 值 |
|------|-----|
| **任务名称** | 工作流执行引擎开发 |
| **优先级** | P0 - 核心功能 |
| **预估工时** | 3-5 天 |
| **前置依赖** | 工作流数据模型已完成 |

## 任务目标

实现工作流的完整执行引擎，支持：
- 节点按拓扑顺序执行
- 支持多种节点类型的执行逻辑
- 错误处理和重试机制
- 执行状态实时推送

## 详细需求

### 1.1 执行器核心实现

```python
# Backend/workflows/services/executor.py
# 创建执行器服务
```

**核心功能：**
- `WorkflowExecutor` 类 - 工作流执行器
- `execute()` 方法 - 执行整个工作流
- `_execute_node()` 方法 - 执行单个节点
- `_get_next_nodes()` 方法 - 根据连线获取下一个节点

### 1.2 支持的节点类型执行逻辑

| 节点类型 | 执行逻辑 | 关键代码 |
|---------|---------|---------|
| `start` | 初始化上下文，记录开始日志 | `execute_start_node()` |
| `end` | 返回最终输出 | `execute_end_node()` |
| `llm` | 调用 LLM API 获取响应 | `execute_llm_node()` |
| `prompt` | 渲染 Prompt 模板 | `execute_prompt_node()` |
| `condition` | 条件判断，选择分支 | `execute_condition_node()` |
| `tool` | 调用工具执行任务 | `execute_tool_node()` |
| `http` | 发送 HTTP 请求 | `execute_http_node()` |
| `code` | 执行代码片段 | `execute_code_node()` |
| `loop` | 循环执行节点组 | `execute_loop_node()` |

### 1.3 执行上下文管理

```python
class ExecutionContext:
    """执行上下文 - 管理工作流执行过程中的变量"""
    
    def __init__(self, input_data: dict):
        self.variables = {}
        self.input_data = input_data
        self.nodes_output = {}  # 节点ID -> 输出
        self.metadata = {}  # 元数据
    
    def set_var(self, name: str, value: any):
        """设置变量"""
        self.variables[name] = value
    
    def get_var(self, name: str, default=None) -> any:
        """获取变量"""
        return self.variables.get(name, default)
    
    def set_node_output(self, node_id: str, output: any):
        """设置节点输出"""
        self.nodes_output[node_id] = output
    
    def get_node_output(self, node_id: str) -> any:
        """获取节点输出"""
        return self.nodes_output.get(node_id)
```

### 1.4 错误处理机制

```python
class NodeErrorHandling:
    """节点错误处理策略"""
    
    STRATEGIES = {
        'stop': '停止执行，抛出异常',
        'skip': '跳过当前节点，继续执行下一个',
        'retry': '重试指定次数',
        'fallback': '使用备用值'
    }
```

**配置项：**
- `error_handling`: 错误处理策略
- `max_retries`: 最大重试次数
- `retry_delay`: 重试延迟（秒）
- `fallback_value`: 备用值

### 1.5 执行状态追踪

```python
class ExecutionTracker:
    """执行状态追踪"""
    
    def __init__(self, execution_id: str):
        self.execution_id = execution_id
        self.node_status = {}  # node_id -> status
        self.start_time = None
        self.end_time = None
    
    def mark_node_start(self, node_id: str):
        """标记节点开始"""
        self.node_status[node_id] = 'running'
        # 发送 WebSocket 消息
        self.broadcast('node_start', {'node_id': node_id})
    
    def mark_node_complete(self, node_id: str, output: any):
        """标记节点完成"""
        self.node_status[node_id] = 'completed'
        self.broadcast('node_complete', {
            'node_id': node_id,
            'output': output
        })
    
    def mark_node_failed(self, node_id: str, error: str):
        """标记节点失败"""
        self.node_status[node_id] = 'failed'
        self.broadcast('node_failed', {
            'node_id': node_id,
            'error': error
        })
```

## 技术实现要点

### 2.1 拓扑排序执行

```python
def topological_sort(nodes: list, edges: list) -> list:
    """拓扑排序 - 确保按依赖顺序执行"""
    # 构建邻接表
    graph = defaultdict(list)
    in_degree = defaultdict(int)
    
    # 初始化
    for node in nodes:
        in_degree[node.id] = 0
    
    # 构建图
    for edge in edges:
        graph[edge.source_node_id].append(edge.target_node_id)
        in_degree[edge.target_node_id] += 1
    
    # BFS 拓扑排序
    queue = deque([n for n in nodes if in_degree[n.id] == 0])
    result = []
    
    while queue:
        node = queue.popleft()
        result.append(node)
        
        for neighbor in graph[node.id]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)
    
    return result
```

### 2.2 变量插值

```python
def interpolate(text: str, context: dict) -> str:
    """变量插值 - 支持 {{variable}} 语法"""
    pattern = r'\{\{([^}]+)\}\}'
    
    def replacer(match):
        var_name = match.group(1).strip()
        return str(context.get(var_name, match.group(0)))
    
    return re.sub(pattern, replacer, text)
```

### 2.3 条件表达式求值

```python
def evaluate_condition(condition: dict, context: dict) -> bool:
    """评估条件表达式"""
    field = condition.get('field')
    operator = condition.get('operator')
    value = condition.get('value')
    
    actual_value = context.get(field)
    
    operators = {
        'eq': lambda a, b: a == b,
        'ne': lambda a, b: a != b,
        'gt': lambda a, b: a > b,
        'lt': lambda a, b: a < b,
        'gte': lambda a, b: a >= b,
        'lte': lambda a, b: a <= b,
        'contains': lambda a, b: b in a,
        'startswith': lambda a, b: str(a).startswith(str(b)),
        'endswith': lambda a, b: str(a).endswith(str(b)),
        'in': lambda a, b: a in b,
    }
    
    return operators[operator](actual_value, value)
```

## 验收标准

- [ ] 工作流可以按拓扑顺序正确执行
- [ ] 所有节点类型都能正确执行
- [ ] 错误处理策略生效
- [ ] WebSocket 实时推送执行状态
- [ ] 执行日志完整记录
- [ ] 单元测试覆盖率 > 80%

## 关键文件清单

| 文件路径 | 说明 |
|---------|------|
| `Backend/workflows/services/executor.py` | 执行器核心 |
| `Backend/workflows/services/context.py` | 执行上下文 |
| `Backend/workflows/services/tracker.py` | 状态追踪 |
| `Backend/workflows/nodes/` | 各类节点执行逻辑 |
| `Backend/workflows/consumers.py` | WebSocket 推送 |
| `Backend/workflows/tasks.py` | Celery 异步任务 |

## 测试用例

```python
# tests/test_executor.py

def test_simple_workflow_execution():
    """测试简单工作流执行"""
    # 创建 start -> llm -> end 工作流
    # 执行并验证结果

def test_condition_routing():
    """测试条件路由"""
    # 创建条件分支工作流
    # 验证根据条件选择正确分支

def test_error_handling_retry():
    """测试错误重试"""
    # 配置重试策略
    # 模拟失败后验证重试

def test_loop_execution():
    """测试循环执行"""
    # 创建循环工作流
    # 验证循环正确终止
```

---

## 备注

- 参考 Dify 的执行引擎设计
- 考虑支持并行执行优化
- 后续可添加执行回放功能
