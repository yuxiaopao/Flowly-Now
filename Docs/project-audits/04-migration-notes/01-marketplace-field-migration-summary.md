# Marketplace 字段统一与迁移准备总结

## 文档目的
本文件总结本轮对 `Backend/marketplace` 的字段统一、兼容层收口、运行时风险修复、迁移阻塞判断与后续执行建议。

这不是泛泛而谈的复盘，而是给后续继续接手的人一个清晰结论：
- 已经做了什么
- 为什么这样做
- 当前到底卡在哪里
- 下一步应该怎么做

---

## 一、背景与核心问题

`marketplace.WorkflowTemplate` 当前存在两套命名体系并行：

### 数据库真实字段名
- `install_count`
- `avg_rating`
- `preview_image`
- `is_published`

### 对外契约/业务语义字段名
- `use_count`
- `rating`
- `thumbnail`
- `is_public`

这会带来几个直接问题：

1. 同一语义在不同层名字不一致
2. 前端、序列化、admin、signal、task、ORM 查询都容易各写各的
3. 后续真实 rename 数据库字段时，爆炸半径很大
4. 项目里 `Backend/workflows` 还有另一套模板系统已经在使用 `use_count` / `rating` 等命名，进一步提高误改风险

这个问题在 `Docs/project-audits/03-template-market-audit.md` 已被指出，但之前没有落到足够细的迁移准备层。

---

## 二、本轮已完成的改动

### 2.1 模型中集中收口旧字段名
已在 `Backend/marketplace/models.py` 的 `WorkflowTemplate` 中新增常量：

- `DB_FIELD_USE_COUNT = 'install_count'`
- `DB_FIELD_RATING = 'avg_rating'`
- `DB_FIELD_THUMBNAIL = 'preview_image'`
- `DB_FIELD_IS_PUBLIC = 'is_published'`
- `DB_ORDER_BY_POPULAR = f'-{DB_FIELD_USE_COUNT}'`
- `DB_ORDER_BY_RATING = f'-{DB_FIELD_RATING}'`

### 价值
不是为了好看，而是为了把散落在各处的旧字段字符串收敛到模型层，降低真实 rename 前的修改面。

---

### 2.2 ORM 调用点已开始走模型常量
已收口的文件包括：

- `Backend/marketplace/views.py`
- `Backend/marketplace/tasks.py`
- `Backend/marketplace/signals.py`
- `Backend/marketplace/serializers.py`
- `Backend/marketplace/admin.py`

收口内容包括但不限于：

- `filter(is_published=True/False)` → `filter(**{WorkflowTemplate.DB_FIELD_IS_PUBLIC: ...})`
- `order_by('-install_count')` → `order_by(WorkflowTemplate.DB_ORDER_BY_POPULAR)`
- `order_by('-avg_rating')` → `order_by(WorkflowTemplate.DB_ORDER_BY_RATING)`
- `save(update_fields=['install_count', 'avg_rating', ...])` → 通过模型常量传入真实 DB 字段名
- `update(install_count=...)` / `update(avg_rating=...)` → 通过模型常量构造 `**kwargs`

### 价值
这一步没有改 schema，但已经把“旧字段名硬编码遍地开花”的状态明显收缩。

---

### 2.3 Serializer 写入桥接层已收口
`Backend/marketplace/serializers.py` 中的 `TemplateCreateSerializer` 仍保留必要桥接，但已经不再裸写旧字段字符串：

- `thumbnail` 写入通过 `source=WorkflowTemplate.DB_FIELD_THUMBNAIL`
- `is_public` 写入通过 `source=WorkflowTemplate.DB_FIELD_IS_PUBLIC`

### 结论
当前桥接仍然必要，因为数据库真实字段还没改。现在删掉桥接不会更先进，只会直接破坏写入链路。

---

### 2.4 Compatibility alias 层已明确化
`Backend/marketplace/models.py` 中保留了四个 property 兼容层：

- `use_count` → `install_count`
- `rating` → `avg_rating`
- `thumbnail` → `preview_image`
- `is_public` → `is_published`

这些 property 已补充注释，明确它们是“兼容别名”，不是最终字段结构。

同时新增：

- `compatibility_alias_fields()`
- `supports_schema_field_rename()`

当前 `supports_schema_field_rename()` 会基于兼容别名是否已清空来判断是否安全进入真实 schema rename。

### 价值
这一步把迁移状态显式化了，避免后续误判“已经可以 rename”。

---

### 2.5 修复了一个真实运行时风险：signal 中 tracker 访问不安全
`Backend/marketplace/signals.py` 原先直接使用：

- `instance.tracker.has_changed(...)`

但当前代码中并没有明确看到 `FieldTracker` 的可靠定义来源。这意味着运行时如果 `tracker` 不存在，signal 可能直接报错。

已新增安全函数：

- `_template_tracker_changed(instance, field_name)`

该函数会在以下情况下直接返回 `False`：
- `instance` 没有 `tracker`
- `tracker.has_changed` 不可调用

然后 publish 状态检测统一改为使用该安全函数。

### 价值
这不是“风格优化”，而是降低运行时不确定性，避免在未来迁移期间叠加额外故障。

---

## 三、当前仍存在的核心阻塞

### 3.1 真实数据库字段 rename 还不能安全执行
原因不是单点未完成，而是整个运行时依赖链还没有彻底脱离兼容层。

#### 直接阻塞点
1. `WorkflowTemplateSerializer` 仍直接暴露：
   - `use_count`
   - `rating`
   - `thumbnail`
   - `is_public`

2. `WorkflowTemplateAdmin` 仍直接依赖：
   - `list_display` 中的 `is_public`, `use_count`, `rating`
   - `readonly_fields` 中的 `use_count`, `rating`
   - `fieldsets` 中的 `thumbnail`, `use_count`, `rating`, `is_public`

3. 视图和任务层仍有实例属性写法依赖 compatibility alias，例如：
   - `template.use_count = ...`
   - `template.rating = ...`
   - `template.is_public = True/False`

### 结论
只要这些依赖还在，直接删除 property 并 rename 真实字段，就会同时破坏：
- DRF serializer
- Django admin
- 视图层实例写入
- 任务层统计写回

所以真实字段迁移现在不是“下一步顺手做”，而是一个必须成组落地的破坏性重构。

---

### 3.2 代码库存在另一套模板系统，不能粗暴全局替换
`Backend/workflows` 中还有另一套模板相关模型/serializer/view，且已经在使用：

- `use_count`
- `rating`
- `thumbnail_url`
- `is_public`

这意味着：
- 全局搜索替换极易误伤 `workflows`
- “名字一样”不等于“同一模型语义”
- marketplace 的 rename 必须严格限定作用域

### 结论
后续任何真实迁移都必须按 `Backend/marketplace` 的边界精细处理，不能搞全项目粗替换。

---

## 四、当前状态的客观判断

### 已经完成的阶段
目前可以明确认为已经完成：

1. **DTO / API 外观层统一的基础准备**
2. **marketplace 内部旧字段字符串收口**
3. **serializer 写入桥接集中化**
4. **compatibility alias 层角色明确化**
5. **signal tracker 风险兜底**

### 还没有完成的阶段
以下工作仍未进入真正执行：

1. **拆除 compatibility alias 依赖链**
2. **把 serializer/admin 从 property 依赖改成显式受控映射**
3. **真实数据库字段 rename**
4. **migration 生成与应用验证**
5. **跨 app 模板系统治理**

---

## 五、为什么这次没有直接生成 migration

因为那样不负责任。

当前如果直接对 `WorkflowTemplate` 做真实字段 rename，例如：
- `install_count` → `use_count`
- `avg_rating` → `rating`
- `preview_image` → `thumbnail`
- `is_published` → `is_public`

会立刻遇到以下冲突：

1. 模型内已有同名 property，类定义冲突
2. serializer/admin 当前把这些名字当现成属性在用，但依赖方式还不够显式
3. ORM/任务/视图仍有实例写法依赖 alias 层
4. signal 与状态追踪逻辑仍需重新确认

所以现在直接生成 migration，不是推进，而是提前引爆。

---

## 六、建议的后续执行路径

### 阶段 A：拆除 compatibility alias 依赖链
先做运行时脱敏，不碰数据库。

#### 需要做的事
1. 改 `WorkflowTemplateSerializer`
   - 不再隐式依赖 property 名称存在
   - 改成显式字段/方法映射

2. 改 `WorkflowTemplateAdmin`
   - 列表、只读字段、fieldsets 不再直接依赖 compatibility alias
   - 必要时改为显式方法或真实字段展示

3. 改视图与任务层实例赋值
   - 逐步减少 `template.use_count = ...`
   - 逐步减少 `template.rating = ...`
   - 逐步减少 `template.is_public = ...`

4. 清点剩余 alias 依赖点
   - 直到 `compatibility_alias_fields()` 可以真实返回空集

### 阶段 B：执行真实字段 rename
在阶段 A 完成后再做。

#### 目标 rename
- `install_count` → `use_count`
- `avg_rating` → `rating`
- `preview_image` → `thumbnail`
- `is_published` → `is_public`

#### 执行内容
1. 删除 compatibility property
2. 修改模型真实字段名
3. 生成 migration
4. 校验 admin / serializer / views / tasks / signals
5. 跑 Django check、定向接口验证、管理后台验证

### 阶段 C：跨模板系统统一治理
这是更大的架构问题，不属于本轮字段迁移，但不能忽视。

建议：
1. 选定唯一模板真相源
2. 统一模板 DTO / endpoint
3. 前端模板 store 统一收口
4. 逐步下线重复模板系统或降级为适配层

---

## 七、本轮产出清单

### 实际修改文件
- `Backend/marketplace/models.py`
- `Backend/marketplace/views.py`
- `Backend/marketplace/serializers.py`
- `Backend/marketplace/tasks.py`
- `Backend/marketplace/signals.py`
- `Backend/marketplace/admin.py`

### 主要新增/调整点
- marketplace 旧 DB 字段常量集中化
- ORM 查询/排序/更新字段常量化
- serializer 写入桥接常量化
- compatibility alias 迁移状态检查方法
- signal tracker 安全访问函数

---

## 八、最终结论

这轮工作真正完成的，不是“字段迁移”，而是**字段迁移前的硬清障**。

现在的状态可以概括为：

- 对外契约已经朝统一命名收口
- 内部旧字段硬编码已经明显减少
- 兼容层角色已经被显式标记
- 运行时一个潜在 signal 风险已被补上
- 但真实 schema rename 还不能直接做

最重要的判断是：

> 当前下一步不应该是直接生成 migration，
> 而应该先拆除 `WorkflowTemplate` 的 compatibility alias 依赖链，
> 让 serializer、admin、views、tasks 先脱离对 property 的隐式依赖。

这一步做完，才适合进入真正的数据库字段 rename。
