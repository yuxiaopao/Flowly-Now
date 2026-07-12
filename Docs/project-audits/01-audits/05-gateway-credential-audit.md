# Gateway / 凭证 / 计费 / 工具耦合审查

## 审查范围
- `Backend/gateway`
- `Backend/workflows` 中 `Tool` / `APICredential` / 成本与日志相关实现
- 前端 `settings`、`gateway` 相关 API/store/页面

## 问题分级

### P0-1 凭证模型重复，职责冲突
- `gateway.UserAPIKey`
- `workflows.APICredential`

两套模型都在承载第三方凭证存储，字段语义高度重叠，但服务商枚举、使用入口、前端管理入口都不一致。

#### 影响
- 用户需要在两个入口重复配置凭证
- 调用侧无法形成统一真相源
- 后续权限、审计、轮换、加密逻辑会重复建设

#### 建议
- 统一凭证真相源，优先保留加密能力更完整的 `APICredential`
- `gateway` 改为消费统一凭证服务，而不是维护自己的 API key 模型

### P0-2 计费逻辑分散，费用口径不一致
- `gateway` 内部硬编码价格
- `gateway.AIModel` 自带价格字段
- `WorkflowExecution.cost_amount`
- `NodeExecution.token_usage`
- `APICallLog.cost`

存在多处费用与 token 统计字段，缺少单一计费入口。

#### 影响
- 成本统计可能不一致
- 账单、执行记录、节点记录、网关日志难以对账

#### 建议
- 统一计费服务，价格只从 `AIModel` 或一个统一配置源读取
- 工作流层只保留聚合值，网关层保留明细值

### P1-1 Provider / Service 枚举不一致
- `gateway` 使用较小 provider 枚举
- `workflows` 使用更大的 service_type 枚举

#### 影响
- 前后端配置体验割裂
- 新增 provider 时容易漏改

#### 建议
- 提取共用 provider/service 常量
- 统一前端下拉数据源

### P1-2 前端凭证入口割裂
- `/settings/api-keys`
- `/settings/credentials`

#### 影响
- 用户心智混乱
- API 层重复

#### 建议
- 合并为单一凭证管理界面
- 区分“模型凭证”“工具凭证”“集成凭证”视图，而不是拆成两套资源

### P2-1 工具调用与网关调用边界不清
`ToolExecutor`、`ProviderRegistry`、`langchain_service`、gateway 调用路径存在重叠。

#### 建议
- 明确：
  - `gateway` 负责模型调用抽象、定价、日志
  - `workflows` 负责编排与执行
  - `tools` 负责工具定义与调用协议

## 推荐整改顺序
1. 统一 provider/service 常量
2. 统一前端凭证管理入口
3. 让 `gateway` 读取统一凭证源
4. 统一计费服务与 token 统计口径
5. 逐步废弃重复模型与旧 API
