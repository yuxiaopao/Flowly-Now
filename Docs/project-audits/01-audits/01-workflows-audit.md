# Workflows 结构债与不一致审查

## 审查范围
- `Backend/workflows/models.py`
- `Backend/workflows/views.py`
- `Backend/workflows/serializers.py`
- `Backend/workflows/tasks.py`
- `Backend/workflows/services/*`

## 问题分级

### P0-1 Edge 复制逻辑使用不存在字段
复制工作流时，`views.py` 中使用了与当前 `Edge` 模型不一致的字段，例如 `type`、`condition`，而模型实际字段是 `condition_expression`、`condition_priority`、`style` 等。

#### 影响
- 复制工作流时边数据可能丢失
- 运行时可能直接报错

#### 建议
- 统一 `duplicate()`、模板创建逻辑与 `Edge` 模型字段
- 先做字段映射核对，再补测试

### P0-2 模板创建逻辑存在字段漂移
模板转工作流逻辑存在访问不存在字段的风险，例如访问模板上的历史字段或未同步字段。

#### 影响
- 从模板创建工作流可能直接失败
- 模板能力不稳定

#### 建议
- 统一模板 schema
- 把 workflow-template 到 workflow 的转换逻辑集中封装，不要散落在多个 view 中

### P0-3 执行详情接口字段口径不一致
执行详情相关接口中存在使用模型不存在字段或历史字段别名的问题，如错误堆栈字段命名不统一。

#### 影响
- 前端展示执行错误详情不稳定
- 调试与排障成本升高

#### 建议
- 统一 `WorkflowExecution` 的错误字段命名
- 清理 view/serializer 中的历史字段引用

### P0-4 凭证读取路径存在安全实现问题
工具执行链中存在直接读取凭证存储字段的风险，未严格通过统一解密入口读取。

#### 影响
- 凭证加密策略可能形同虚设
- 安全实现与调用实现脱节

#### 建议
- 所有凭证消费只允许走统一解密方法
- 增加凭证读取审计与测试

### P0-5 执行日志 action 定义冲突
`WorkflowExecutionViewSet` 中存在同名 action 重复定义迹象，后定义覆盖前定义。

#### 影响
- 部分接口实现实际不可达
- 返回口径可能与预期文档不一致

#### 建议
- 重命名并拆分执行明细与日志查询接口
- 为每个 action 建最小 API 回归测试

---

### P1-1 Serializer 字段设计冗余
`EdgeSerializer` 等存在语义重复字段，增加前后端理解成本。

#### 建议
- 保留单一主字段命名
- 列表与详情输出按场景分开

### P1-2 条件边表达式能力未真正打通
模型有 `condition_expression`，但执行器分支逻辑仍偏向使用 label/简化判断。

#### 影响
- 模型能力与执行能力脱节
- 条件边语义不完整

#### 建议
- 建立条件边统一求值入口
- 不再允许分支逻辑依赖 label 充当业务语义

### P1-3 执行器职责过载
`WorkflowExecutor` 同时负责：图构建、节点执行、并行调度、错误策略、上下文写入、广播、NodeExecution 持久化。

#### 影响
- 可测试性差
- 新节点类型接入成本不断升高

#### 建议
- 拆为图调度层、节点运行层、状态同步层、广播层

### P1-4 租户过滤不统一
部分查询集缺少严格 tenant/owner 约束，依赖 owner/public 的方式不够硬。

#### 影响
- 多租户边界存在泄漏风险

#### 建议
- 为 workflows 域建立统一 queryset mixin
- 先补高风险资源：workflow、variable、tool、template、execution

### P1-5 运行时与定义态边界不清
`WorkflowExecution`、`NodeExecution`、JSON 日志、结构化日志并存，口径分裂。

#### 建议
- 明确：
  - 执行聚合状态放哪里
  - 节点明细放哪里
  - 可观测日志放哪里
  - 面向 UI 的查询接口从哪里读

---

### P2-1 duplicate 逻辑未覆盖新增节点字段
复制节点时未同步全部节点字段，如 schema、timeout、条件等。

### P2-2 UUID / 类型标注不一致
执行器内部对节点 ID 的类型标注与真实模型主键类型存在偏差。

### P2-3 并行执行路径与 start/end 节点语义混杂
并行执行时对起止节点的处理较脆弱。

### P2-4 import 结构散乱
`views.py` 中 import 分散、文件过长，维护信号很差。

### P2-5 ErrorHandlerRegistry 设计偏临时
更像工厂/注册表混合实现，边界不稳。

---

### P3-1 WebSocket 广播逻辑重复
广播逻辑分散在 views/tasks/signals 多处。

### P3-2 NodeType 扩展方式过硬编码
节点类型全靠模型枚举，未来扩张成本高。

### P3-3 Serializer 存在覆盖式实现痕迹
部分 `to_representation` 设计存在重复/覆盖历史痕迹。

## 结论
`workflows` 已经不是普通业务 app，而是“定义态 + 运行时 + 模板层 + 凭证/工具接入 + 缓存/广播”的混合中台。当前最需要先做的不是继续加功能，而是：

1. 修掉 P0 字段漂移和接口冲突
2. 给执行链、模板链、凭证链补一致性测试
3. 拆清执行器职责
4. 统一多租户与日志口径

## 推荐行动顺序
1. 修正 `duplicate()` / template create 字段映射
2. 统一 execution detail / logs 接口
3. 修正凭证读取实现
4. 补 workflows 高风险回归测试
5. 规划 `workflows` 域内拆层
