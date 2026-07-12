# execution_logs JSONField 废弃计划

> 状态：已分析，待执行（DB migration 需停机窗口）
> 生成时间：2026-06-06
> 关联：`03-action-plans/01-master-action-plan.md` 未解决清单

---

## 一、现状分析

### 1.1 字段位置

`WorkflowExecution` 模型（第 432 行）：

```python
# Backend/workflows/models.py
execution_logs = models.JSONField(
    default=list,
    verbose_name='执行日志'
)
```

### 1.2 写入路径（现状）

`WorkflowExecution.add_execution_log()` 方法（第 583 行）向 JSONField 写入：

```python
def add_execution_log(self, log_entry: dict):
    if self.execution_logs is None:
        self.execution_logs = []
    self.execution_logs.append(log_entry)
    self.save(update_fields=['execution_logs'])
```

**调用位置：** 需全局搜索确认有多少地方调用此方法。

### 1.3 读取路径（已废弃）

| 路径 | 现状 |
|---|---|
| `logs` action (`GET /executions/{id}/logs/`) | ✅ 已改为从 `ExecutionLog` 表读取 |
| `timeline` action (`GET /executions/{id}/timeline/`) | ✅ 已改为从 `ExecutionLog` 表读取 |
| Serializer `execution_logs` 字段 | ✅ serializer 无此字段 |
| `WorkflowExecution.execution_logs` 直接访问 | ⚠️ 仅 `add_execution_log()` 内部 |

### 1.4 结论

JSONField **不再参与任何读取路径**，写入也只有 `add_execution_log()` 一个方法。
废弃迁移成本：**低**。

---

## 二、废弃方案

### 2.1 阶段一：统一写入（向前兼容）

修改 `add_execution_log()`，同时写入 `ExecutionLog` 表：

```python
def add_execution_log(self, log_entry: dict):
    # 写入独立表（主路径）
    ExecutionLog.objects.create(
        execution=self,
        node_execution_id=log_entry.get('node_execution_id'),
        level=log_entry.get('level', 'info'),
        message=log_entry.get('message', ''),
        metadata=log_entry.get('metadata', {}),
    )
    # JSONField 保持写入（向后兼容，前端可能仍有直接访问）
    if self.execution_logs is None:
        self.execution_logs = []
    self.execution_logs.append(log_entry)
    self.save(update_fields=['execution_logs'])
```

### 2.2 阶段二：停止 JSONField 写入（平滑过渡）

在所有调用方确认只读 `ExecutionLog` 表后，去掉 `add_execution_log()` 中的 JSONField 写入分支：

```python
def add_execution_log(self, log_entry: dict):
    ExecutionLog.objects.create(
        execution=self,
        node_execution_id=log_entry.get('node_execution_id'),
        level=log_entry.get('level', 'info'),
        message=log_entry.get('message', ''),
        metadata=log_entry.get('metadata', {}),
    )
```

### 2.3 阶段三：数据库迁移（停机操作）

新增 migration 删除字段：

```python
# migrations/0013_remove_execution_logs.py
from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [
        ('workflows', '0012_template_installs_and_ratings'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='workflowexecution',
            name='execution_logs',
        ),
    ]
```

---

## 三、前置条件检查清单

在执行阶段三之前，必须确认：

- [ ] `add_execution_log()` 的所有调用方已审查（确认写入了 `ExecutionLog` 表）
- [ ] 前端无直接读取 `WorkflowExecution.execution_logs` 字段的代码
- [ ] 后端无其他视图/serializer 直接访问 `execution.execution_logs`
- [ ] 无第三方服务依赖 `WorkflowExecution.execution_logs` JSONField

---

## 四、风险评估

| 风险 | 等级 | 缓解 |
|---|---|---|
| 停机迁移 | 中 | 选择低峰窗口，migration 执行时间 < 1 分钟 |
| 历史数据丢失 | 低 | 阶段一先做双写，数据已在 `ExecutionLog` 表 |
| 前端缓存残留 | 低 | JSONField 删除后前端读取返回 404，自然触发切换 |

---

## 五、执行顺序

```
1. 全局搜索 add_execution_log() 调用 → 确认写入路径
2. 修改 add_execution_log() → 双写 ExecutionLog + JSONField
3. 前端回归测试 → /logs/ 和 /timeline/ 端点
4. 停止 JSONField 写入（去掉 append 分支）
5. DB migration 删除字段
```
