# Phase 2: 硬编码整改 + 代码质量详细方案

> 基于源代码全面审查生成
> 制定时间：2026-06-03

---

## 一、硬编码问题清单

### 1.1 Magic Number 分散问题

**发现：`DEFAULT_MAX_TOKENS` 在多处定义且值不一致**

| 定义位置 | 当前值 | 问题 |
|---------|--------|------|
| `Backend/config/constants.py:25` | `2000` | 已集中定义 |
| `Backend/nl_to_workflow/constants.py:13` | `4096` | **重复定义，值不同** |
| `Backend/nl_to_workflow/views.py:31` | `4096` | **重复定义** |
| `Backend/workflows/services/langchain_service.py` | 依赖导入 | 引用 `constants.DEFAULT_MAX_TOKENS` ✅ |
| `Backend/agents/engine.py` | 依赖导入 | 引用 `constants.DEFAULT_MAX_TOKENS` ✅ |
| `Backend/agents/models.py` | 依赖导入 | 引用 `constants.DEFAULT_MAX_TOKENS` ✅ |

**整改方案：**
- [ ] 统一 `DEFAULT_MAX_TOKENS = 4096`（更大上下文适合工作流场景）
- [ ] 删除 `Backend/nl_to_workflow/constants.py` 中重复的 `DEFAULT_MAX_TOKENS`
- [ ] 删除 `Backend/nl_to_workflow/views.py:31` 中重复的 `DEFAULT_MAX_TOKENS = 4096`
- [ ] 删除 `Backend/nl_to_workflow/services.py` 中所有散落的 `max_tokens=4096`（行 385, 1478）
- [ ] 在 `config/constants.py` 中添加注释说明这是唯一来源

**验收标准：** `grep -r "DEFAULT_MAX_TOKENS" Backend/` 只在 `config/constants.py` 和引用它的文件中出现

### 1.2 分页常量重复定义

**发现：`PAGE_SIZE_DEFAULT` 在 `config/constants.py` 已定义，但多处仍硬编码**

| 位置 | 硬编码值 | 应替换为 |
|------|---------|---------|
| `Backend/workflows/views.py` | `page_size=20` | `constants.PAGE_SIZE_DEFAULT` |
| `Backend/agents/views.py` | `page_size=20` | `constants.PAGE_SIZE_DEFAULT` |
| `Backend/rag/views.py` | `page_size=20` | `constants.PAGE_SIZE_DEFAULT` |
| `Backend/gateway/views.py` | `page_size=20` | `constants.PAGE_SIZE_DEFAULT` |

**整改方案：**
- [ ] 统计所有 `page_size=\d+` 硬编码位置
- [ ] 统一替换为 `constants.PAGE_SIZE_DEFAULT`
- [ ] 对需要不同 page_size 的接口显式传入 `page_size` 参数

### 1.3 超时常量分散

**发现：`config/constants.py` 已定义超时常量，但 `workflows/services/monitoring.py` 仍存在内联超时计算**

| 位置 | 问题 | 建议 |
|------|------|------|
| `Backend/config/constants.py:53-59` | 超时常量已集中 | ✅ 无需改动 |
| `Backend/workflows/services/monitoring.py:785-787` | `> 1000` 是 Magic Number | 改为 `MAX_PROFILE_RECORDS = 1000` |

**整改方案：**
- [ ] 在 `config/constants.py` 添加 `MAX_EXECUTION_PROFILES = 1000`
- [ ] 替换 `workflows/services/monitoring.py:785-787`

### 1.4 前端 API 超时硬编码

**发现：`Frontend/src/api/index.js` 中存在多个硬编码超时值**

| 位置 | 当前值 | 建议常量 |
|------|--------|---------|
| `api/index.js` | `timeout: 30000` | `VITE_API_TIMEOUT_MS` (环境变量) |
| `api/index.js` | 重试 `3` 次 | `VITE_API_MAX_RETRIES` |

**整改方案：**
- [ ] 在 `Frontend/src/config/index.js` 中添加 API 超时配置
- [ ] 在 `.env.example` 中添加对应字段
- [ ] `api/index.js` 改为读取配置而非硬编码

---

## 二、模块一致性整改

### 2.1 模块完整性审查结果

| 模块 | views.py | serializers.py | urls.py | admin.py | 状态 |
|------|----------|----------------|---------|----------|------|
| `integrations` | ✅ 存在 | ✅ 存在 | ✅ 存在 | ✅ 存在 | **完整** |
| `branding` | ✅ 存在 | ✅ 存在 | ✅ 存在 | ✅ 存在 | **完整** |
| `templates` | ✅ 存在 | ✅ 存在 | ✅ 存在 | ✅ 存在 | **完整** |
| `core` | ❌ 子目录 views/ | ❌ 子目录 serializers/ | ❌ 缺失 | ❌ 缺失 | **需重构** |

> 注：初次审查误判了 `integrations`、`branding`、`templates`，它们实际上文件都已存在。真正需要整改的是 **`core` 模块结构与其他模块不一致**。

### 2.2 `core` 模块结构重构

**问题：** `core` 模块使用 `views/` 子目录结构，而其他 25 个模块均使用扁平的 `views.py` 文件。

**当前结构：**
```
core/
├── views/
│   ├── notification_views.py
│   ├── audit_views.py
│   └── health_views.py
├── serializers/
│   ├── notification_serializers.py
│   └── audit_serializers.py
├── models/
│   ├── notification.py
│   └── audit.py
├── apps.py
└── __init__.py
```

**目标结构（与其他模块统一）：**
```
core/
├── models.py           (合并 notification.py + audit.py)
├── views.py           (合并所有 *_views.py)
├── serializers.py     (合并所有 *_serializers.py)
├── urls.py            (新建，注册所有 URL)
├── admin.py           (新建，注册 admin)
├── apps.py
└── __init__.py
```

**执行步骤：**
1. [ ] 创建 `core/models.py`，合并 `models/notification.py` + `models/audit.py`
2. [ ] 创建 `core/views.py`，合并 `views/notification_views.py` + `views/audit_views.py` + `views/health_views.py`
3. [ ] 创建 `core/serializers.py`，合并两个子文件
4. [ ] 创建 `core/urls.py`，注册所有 URL（参考其他模块如 `workflows/urls.py`）
5. [ ] 创建 `core/admin.py`，注册 admin（参考 `core/admin_site.py` 的 Jazzmin 配置）
6. [ ] 删除 `core/views/`、`core/serializers/`、`core/models/` 子目录
7. [ ] 更新 `Backend/config/urls.py` 中的 `include('core.urls')`
8. [ ] 运行 `python manage.py check` 验证

**验收标准：** `python manage.py check` 无错误，curl 测试 `/api/v1/health/` 等 endpoint 正常响应

### 2.3 缺失 admin.py 的模块

| 模块 | 已有 admin.py | 需补齐 |
|------|-------------|--------|
| `prompts` | ❌ 无 | admin.py |
| `marketplace` | ❌ 无 | admin.py |
| `evaluation` | ❌ 无 | admin.py |
| `datasets` | ✅ 有 | — |

**执行步骤：**
- [ ] 为 `prompts`、`marketplace`、`evaluation` 三个模块创建 `admin.py`
- [ ] 参考已有 admin.py 格式（如 `workflows/admin.py`）
- [ ] 注册主要模型到 Django Admin

---

## 三、异常处理规范化

### 3.1 过于宽泛的异常捕获

**发现：全 Backend 有 20+ 处 `except Exception as e:`**

| 模块 | 出现次数 | 风险级别 |
|------|---------|---------|
| `nl_to_workflow/vector_store.py` | 9 | 高 |
| `workflows/services/monitoring.py` | 7 | 中 |
| `workflows/services/sandbox_service.py` | 5+ | 中 |
| `nl_to_workflow/output_parser.py` | 2 | 中 |
| `scripts/index_templates.py` | 1 | 低（脚本文件） |

**3.1.1 `vector_store.py` 异常处理分析（最严重）**

该文件 9 处 `except Exception as e:` 均捕获了多种不同类型的异常。建议分类：

```python
# 当前（有问题）：
except Exception as e:
    logger.error(f"Error: {e}")

# 建议改为：
try:
    ...
except ChromaConnectionError as e:
    raise VectorStoreConnectionError(f"ChromaDB 连接失败: {e}") from e
except ImportError as e:
    raise VectorStoreImportError(f"依赖缺失: {e}") from e
except ValueError as e:
    raise VectorStoreConfigError(f"配置错误: {e}") from e
```

**整改方案：**
- [ ] 创建 `Backend/core/exceptions.py`（统一异常基类）
- [ ] 为 `vector_store.py` 每种异常建立具体异常类
- [ ] 逐步改造其他模块

**3.1.2 统一异常类设计**

```python
# Backend/core/exceptions.py

class BaseAPIException(Exception):
    """所有业务异常的基类"""
    status_code = 500
    error_code = "INTERNAL_ERROR"
    default_message = "服务器内部错误"

    def __init__(self, message=None, details=None):
        self.message = message or self.default_message
        self.details = details or {}
        super().__init__(self.message)

class WorkflowNotFoundError(BaseAPIException):
    status_code = 404
    error_code = "WORKFLOW_NOT_FOUND"
    default_message = "工作流不存在"

class WorkflowExecutionError(BaseAPIException):
    status_code = 500
    error_code = "WORKFLOW_EXECUTION_ERROR"
    default_message = "工作流执行失败"

class AgentNotFoundError(BaseAPIException):
    status_code = 404
    error_code = "AGENT_NOT_FOUND"
    default_message = "Agent 不存在"

class TokenLimitExceededError(BaseAPIException):
    status_code = 400
    error_code = "TOKEN_LIMIT_EXCEEDED"
    default_message = "Token 数量超限"

class VectorStoreConnectionError(BaseAPIException):
    status_code = 503
    error_code = "VECTOR_STORE_UNAVAILABLE"
    default_message = "向量数据库连接失败"

class RateLimitExceededError(BaseAPIException):
    status_code = 429
    error_code = "RATE_LIMIT_EXCEEDED"
    default_message = "请求频率超限"
```

**验收标准：** 所有 `except Exception as e:` 替换为具体异常类型

---

## 四、命名规范统一

### 4.1 前端 Store Action 命名现状

**分析了 3 个 Store，发现命名存在以下问题：**

| Store | Action 示例 | 问题 |
|-------|------------|------|
| `workflow.js` | `fetchWorkflows`, `fetchWorkflowById` | ✅ `fetch` 前缀一致 |
| `workflow.js` | `saveWorkflow`, `createWorkflow`, `deleteWorkflow` | ✅ `save`/`create`/`delete` 动词清晰 |
| `workflow.js` | `executeWorkflow` | ✅ 动词+名词 |
| `agent.js` | `fetchAgents`, `fetchAgentById` | ✅ `fetch` 前缀一致 |
| `agent.js` | `deleteAgent`, `updateAgent` | ✅ 动词清晰 |

**命名规范文档（草案）：**

| 动作类型 | 前缀/模式 | 示例 | 说明 |
|---------|----------|------|------|
| 从 API 获取列表 | `fetch` + 复数名词 | `fetchWorkflows`, `fetchAgents` | 必须包含加载状态 |
| 从 API 获取单个 | `fetch` + 单数名词 + `ById` | `fetchWorkflowById` | — |
| 创建（POST） | `create` + 单数名词 | `createWorkflow` | 调用 API POST |
| 更新（PUT/PATCH） | `update` + 单数名词 | `updateWorkflow` | 调用 API PATCH |
| 删除（DELETE） | `delete` + 单数名词 | `deleteWorkflow` | 调用 API DELETE |
| 本地状态加载 | `load` + 名词 | `loadCanvasState` | 不调用 API |
| 本地状态保存 | `save` + 名词 | `saveCanvasState` | 不调用 API（只是内存） |
| 异步执行 | `execute` + 名词 | `executeWorkflow` | 触发后台任务 |
| 重置状态 | `reset` + 名词 | `resetForm` | 清空表单状态 |

**执行步骤：**
- [ ] 审计全部 17 个 Store 的 action 命名
- [ ] 统一不符合规范的 action 名称
- [ ] 创建 `Frontend/src/stores/README.md` 记录命名规范

### 4.2 前端 Route Name 命名

**当前状态：** 混合使用 PascalCase 和 camelCase

| 当前 Route Name | 建议 | 原因 |
|----------------|------|------|
| `WorkflowList` | ✅ PascalCase | 页面组件命名 |
| `AgentList` | ✅ PascalCase | 页面组件命名 |
| `NLCreator` | ✅ PascalCase | 页面组件命名 |
| `WorkflowDetail` | ✅ PascalCase | 页面组件命名 |

**结论：** Route name 均使用 PascalCase，符合 Vue Router 惯例，无需修改。

### 4.3 前端 API 模块命名

| 文件 | 命名 | 建议 |
|------|------|------|
| `nlWorkflow.js` | camelCase | ✅ |
| `datasetRecommend.js` | camelCase | ✅ |
| `websiteGenerator.js` | camelCase | ✅ |
| `nlWorkflow.js` (imports) | PascalCase | `import nlWorkflowApi` → 建议 `import nlWorkflowApi` |

**结论：** API 模块命名已统一使用 camelCase，无需修改。

---

## 五、执行检查清单

### Phase 2.1 硬编码整改
- [ ] 统一 `DEFAULT_MAX_TOKENS = 4096`（删除 `nl_to_workflow/constants.py` 和 `views.py` 中的重复定义）
- [ ] 替换所有 `page_size=\d+` 硬编码为 `constants.PAGE_SIZE_DEFAULT`
- [ ] 添加 `MAX_EXECUTION_PROFILES = 1000`
- [ ] 前端 API 超时配置化（`VITE_API_TIMEOUT_MS`）

### Phase 2.2 模块一致性
- [ ] `core` 模块从子目录结构重构为扁平结构（models.py / views.py / serializers.py / urls.py / admin.py）
- [ ] 为 `prompts`、`marketplace`、`evaluation` 补齐 `admin.py`

### Phase 2.3 异常处理
- [ ] 创建 `Backend/core/exceptions.py`（统一异常类体系）
- [ ] 增强 `Backend/config/exception_handlers.py`（统一 JSON 错误响应格式）
- [ ] 重构 `vector_store.py` 的 9 处 `except Exception` 为具体异常
- [ ] 重构 `monitoring.py`、`sandbox_service.py` 的宽泛异常捕获

### Phase 2.4 命名规范
- [ ] 审计全部 17 个 Store 的 action 命名，不符合规范的统一修正
- [ ] 创建 `Frontend/src/stores/README.md` 命名规范文档

---

## 六、代码变更示例

### 示例 1：`nl_to_workflow/views.py` 删除重复常量

```python
# 删除 (line 31)
- DEFAULT_MAX_TOKENS = 4096

# 保留 import
from config.constants import DEFAULT_MAX_TOKENS
```

### 示例 2：`core` 模块统一结构

```python
# core/models.py
from .notification import Notification
from .audit import AuditLog

__all__ = ['Notification', 'AuditLog']

# core/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('health/', views.health_check, name='health'),
    path('notifications/', views.notification_list, name='notification-list'),
    path('audit/', views.audit_log_list, name='audit-log-list'),
]
```

### 示例 3：`core/exceptions.py` 统一异常体系

```python
# core/exceptions.py
class BaseAPIException(Exception):
    status_code = 500
    error_code = "INTERNAL_ERROR"

    def to_response(self):
        return {
            "error": {
                "code": self.error_code,
                "message": self.message,
                "details": self.details
            }
        }
```

---

*本方案基于 `grep` + `read` 全量代码审查生成*
