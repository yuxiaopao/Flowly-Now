# 多租户权限边界审查

## 审查范围
- `Backend/workflows`
- `Backend/tenants`
- `Backend/datasets`
- `Backend/rag`
- `Backend/agents`
- `Backend/billing`

## 结论
当前项目的多租户隔离不是“默认安全”，而是“局部手工过滤”。这会持续产生绕过点，属于架构级缺陷。

## 问题分级

### P0-1 workflows 多个 ViewSet 缺少硬性 tenant 边界
包括但不限于：
- `WorkflowViewSet`
- `NodeViewSet`
- `EdgeViewSet`
- `WorkflowExecutionViewSet`
- `ExecutionCacheViewSet`

#### 影响
- 通过 query param 或直接资源 ID，可能越权读取其他租户数据
- workflow、node、edge、execution、cache 这几类资源彼此关联，漏一个就会串穿全链路

#### 建议
- 建立统一 tenant queryset mixin
- 所有资源查询先做 tenant/member 约束，再做 owner/public 约束
- 对基于 `workflow_id` 的子资源查询，必须先校验父资源归属

### P0-2 datasets 查询关系写法错误，租户过滤不可信
数据集查询依赖的用户-租户关联写法存在错误或不稳，导致过滤可能失效或退化为只看公共数据。

#### 建议
- 统一使用明确的 membership 关系取 tenant_id 列表
- 不允许各模块自己猜用户与 tenant 的关系名

### P0-3 RAG / Agent / Billing 等域的 tenant 绑定不一致
一些模型仅按 owner 过滤，一些只按 user 过滤，一些存在 tenant 字段但未进入 queryset 主过滤条件。

#### 影响
- 同一系统里存在多种授权语义
- 后续接共享、委派、团队功能时必然继续泄漏

#### 建议
- 统一资源归属模型：owner 只是创建者，tenant 才是边界
- 对 conversation、subscription、collection、vector store 等高敏感资源补 tenant 绑定

### P1-1 Tenant 权限检查位置分散
部分接口把权限检查放在 action 内部，而不是 queryset / permission 层。

#### 风险
- 一个遗漏就是越权
- 对 list/retrieve/update/delete 的行为难以整体推理

#### 建议
- 把成员、管理员、所有者校验前移到 permission/mixin 层
- action 内部只保留业务校验，不承担主授权责任

### P1-2 客户端可传 tenant 语义过强
如果前端可通过 query/body/path 显式指定 tenant 资源，就会持续产生伪造上下文的风险。

#### 建议
- tenant 从认证上下文或当前会话上下文推导
- 对显式 tenant_id 参数统一做 membership 验证

## 推荐治理顺序
1. 先封堵 workflows 相关 queryset 漏洞
2. 统一 membership → tenant 获取方式
3. 抽出 tenant queryset / permission mixin
4. 全域清理 owner-only 过滤
5. 补跨租户访问回归测试
