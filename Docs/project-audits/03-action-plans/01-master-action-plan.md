# 99 - 总行动方案与功能完善路线图

> 本文档不是问题复述，而是把当前代码现状转成可执行的推进方案。  
> 目标：告诉后续开发应该 **先做什么、为什么做、做到什么算完成**。

---

## 一、总原则

## 原则 1：P0 先封堵，再谈扩展
任何继续新增功能的前提，都是先封堵以下风险：
- 跨租户越权
- 模板真相源混乱
- workflow 执行链字段漂移
- 凭证读取与计费口径不一致
- 前端管理员守卫与发布态协议问题

## 原则 2：先统一业务域，再拆技术实现
不要上来就大规模微调代码结构。先把业务域定义清楚：
- workflow domain
- template domain
- execution domain
- tenant/access domain
- resource/credential domain
- knowledge/agent domain

## 原则 3：所有后续功能必须挂靠到闭环里
任何新增功能都必须回答：
- 它属于哪个业务域？
- 它补的是哪条业务闭环？
- 它依赖哪个统一真相源？
- 它遵守哪条 tenant / permission 规则？

否则就不要做。

---

## 二、建议的执行顺序

---

## Phase 1：止血封堵（最高优先级）

## 目标
让系统从“继续变乱”变成“可以稳定重构”。

## 任务 1：统一租户访问边界

### 要做什么
1. 在后端抽出统一 tenant access mixin / helper / permission policy
2. 清理所有 `owner=self.request.user` 但应受 tenant 限制的 queryset
3. 禁止子资源通过裸 `workflow_id` / `agent_id` / `tenant_id` 绕过父资源归属检查
4. 修正所有 `user.tenants.values_list(...)` 这类不稳定关系引用，统一到 membership

### 涉及模块
- `Backend/workflows`
- `Backend/datasets`
- `Backend/rag`
- `Backend/agents`
- `Backend/billing`
- `Backend/augmentation`
- `Backend/annotations`

### 完成标准
- 任意资源 list/retrieve/update/delete 都能明确走 tenant policy
- 不再出现“这个模块按 owner，那边按 tenant，另一边按 public”的混合授权语义
- 至少补一组跨租户访问回归测试

---

## 任务 2：workflow 执行链止血

### 要做什么
1. 修掉 `duplicate()` / `create_from_template()` 与真实模型字段不一致的问题
2. 统一 execution detail / logs / traceback / error_stack 字段口径
3. 拆掉重复 action 名称
4. 统一模板转 workflow 的字段映射入口
5. 所有凭证读取只允许通过统一解密方法

### 涉及模块
- `Backend/workflows/views.py`
- `Backend/workflows/models.py`
- `Backend/workflows/serializers.py`
- `Backend/workflows/services/*`

### 完成标准
- workflow 复制、模板创建、执行详情查询不再依赖历史字段名
- 执行日志接口单一且清晰
- 凭证消费路径不再绕过加密入口

---

## 任务 3：前端权限与协议止血

### 要做什么
1. 路由守卫补齐 `requiresAdmin`
2. 统一 workflow 发布态字段，去掉历史兼容语义
3. 停止在核心业务流里继续扩散模板兼容字段
4. 把最膨胀的 `tenant` store 拆出子域

### 涉及模块
- `Frontend/src/router`
- `Frontend/src/stores`
- `Frontend/src/api`
- `Frontend/src/types`

### 完成标准
- 非管理员无法进入管理员路由
- 前后端对 workflow 发布态使用同一语义
- 前端状态域开始按业务边界收敛

---

## Phase 2：业务域收敛（核心建设期）

## 目标
把重复系统收成稳定的业务底座。

---

## 任务 4：把模板系统收敛为唯一模板域

### 要做什么
1. 选定唯一模板真相源
2. 统一模板分类、模板详情、模板列表、安装/使用、评分/收藏、模板来源、发布状态
3. 统一前端模板 store、API adapter、DTO
4. 把旧模板 app 和 marketplace app 降级为适配层或迁移目标

### 为什么必须先做
从当前代码看，模板业务是最容易继续膨胀的区域，而且已经影响前后端协议稳定性。

### 建议落地方向
- 模板不再只是“列表页资源”，而是工作流资产
- 模板生命周期明确化：草稿、待审核、已发布、已下线、已归档
- 模板来源明确化：官方、团队、个人、社区

### 完成标准
- 模板只有一条主 API 资源线
- 前端 marketplace 不再混用两套模板来源
- 模板字段命名、统计口径、ID 类型、状态语义统一

---

## 任务 5：建立统一资源中心

### 要做什么
1. 统一 provider/service 常量
2. 统一凭证模型与前端凭证入口
3. 明确 gateway / workflows / tools 的职责边界
4. 设计统一资源依赖检测：模板/工作流执行前能检查缺失资源

### 为什么必须做
如果不统一资源层，后面任何模型、工具、第三方集成都还会继续复制。

### 推荐资源模型
- Credential
- Provider
- Model
- Tool Integration
- Knowledge Resource
- Dataset Resource

### 完成标准
- 用户只在一个主入口管理凭证
- workflow/template 执行前可以明确知道缺哪些依赖
- provider / service 不再多处各自维护

---

## 任务 6：建立执行观测域

### 要做什么
1. 统一 execution、node execution、execution log、cost、metrics 的职责
2. 设计执行时间线与节点输入输出快照
3. 设计错误重试、断点续跑、失败节点恢复能力
4. 统一 UI 查询口径

### 为什么必须做
工作流平台最终价值不在编辑器，而在“跑得稳、看得懂、能排障”。

### 完成标准
- UI 能基于统一 execution 结构展示执行详情
- 节点执行、错误、成本、缓存命中信息可以串起来
- 后续再做 SLA/告警/预算才有基础

---

## Phase 3：产品增长（建立真正业务价值）

## 目标
在收敛后的底座上，做真正能带来业务增长的能力。

---

## 任务 7：模板资产运营化

### 重点功能
- 推荐算法
- 精选模板位
- 分类专题
- 模板审核流
- 模板健康分
- 模板成功率/转化率统计
- 相似模板推荐

### 业务价值
让模板不只是内容，而是平台资产和增长入口。

---

## 任务 8：团队协作与治理能力

### 重点功能
- 团队共享模板
- 团队共享知识库
- 团队共享凭证
- 角色权限分级
- 操作审计
- 审批流
- 预算与额度控制

### 业务价值
把 Flowly 从单用户工具推向组织级平台。

---

## 任务 9：智能辅助能力

### 重点功能
- 自然语言生成 workflow
- 基于执行历史的优化建议
- 基于模板热度和成功率推荐配置
- 自动发现依赖缺失
- 执行失败原因归类

### 业务价值
强化平台差异化，而不是只做普通流程编排器。

---

## 三、按业务域给出的功能完善建议

---

## 1. Workflow Domain

### 当前问题
- 定义态与执行态混在一起
- 模板化逻辑散在 view 中
- 执行器职责过载

### 功能完善建议
- 增加 workflow version 概念
- 增加 preflight 校验
- 增加 failure recovery / rerun from node
- 增加 execution timeline
- 增加 workflow health / success-rate dashboard

### 业务逻辑目标
Workflow 不只是“可编辑 JSON”，而是“可发布、可回放、可治理的执行单元”。

---

## 2. Template Domain

### 当前问题
- 三套模型/接口/前端入口并存
- 模板生命周期不清晰
- 安装/使用/评分口径不统一

### 功能完善建议
- 统一模板生命周期
- 增加模板依赖声明（所需凭证、知识库、模型）
- 增加模板质量分
- 增加模板安装引导与首次运行引导
- 增加模板版本记录与变更说明

### 业务逻辑目标
模板是平台资产，不是 workflow 的附件。

---

## 3. Tenant / Access Domain

### 当前问题
- 规则散落
- 授权语义混用
- 前后端都可能伪造 tenant 上下文

### 功能完善建议
- 统一角色模型：owner/admin/member/viewer
- 统一资源可见性：private/team/public/system
- 统一资源操作权限矩阵
- 增加团队审计与共享资源日志

### 业务逻辑目标
所有资源都必须回答：谁创建、归谁、谁可见、谁能执行、谁能付费。

---

## 4. Resource / Credential Domain

### 当前问题
- 凭证双模型
- provider 常量分裂
- 调用边界不清

### 功能完善建议
- 统一凭证与 provider 模型
- 区分个人凭证、团队凭证、系统凭证
- 增加凭证健康状态与最后验证时间
- 增加凭证轮换、失效预警、使用审计

### 业务逻辑目标
资源中心是 workflow 平台的能源系统。

---

## 5. Knowledge / Agent / Dataset Domain

### 当前问题
- 多个智能模块可能继续走向平行系统
- 租户边界与资源绑定未统一

### 功能完善建议
- 把知识库、数据集、prompt、agent 都视为 workflow 可引用资源
- 建立统一依赖引用模型
- 允许模板声明“所需知识资源 / 所需 agent 能力”

### 业务逻辑目标
这些能力必须服务于 workflow 生态，而不是再造多个孤岛。

---

## 四、建议继续输出的设计文档

当前 audit 文档已经够用了。继续推进时，不要再重复写问题单，应该改写目标设计文档。

建议新增：

### 06-template-domain-target-architecture.md
内容应包含：
- 模板唯一真相源
- 模板生命周期
- 模板来源与可见性
- 模板 DTO
- 安装与使用闭环
- 前后端迁移路径

### 07-tenant-access-policy.md
内容应包含：
- owner / tenant / visibility / role / action 定义
- 权限矩阵
- queryset 规范
- action 权限规范
- 客户端 tenant 传值规则

### 08-execution-observability-design.md
内容应包含：
- execution / node execution / log / metric / cost 的统一结构
- UI 查询模型
- 重试与恢复机制
- 执行时间线

### 09-resource-center-design.md
内容应包含：
- credential/provider/model/tool/knowledge 统一资源模型
- 依赖声明机制
- 执行前校验机制
- 成本统计与审计

### 10-product-roadmap.md
内容应包含：
- 止血期
- 收敛期
- 增长期
- 每阶段验收标准

---

## 五、每周推进建议

如果你准备继续以“文档驱动 + 分阶段实现”的方式推进，建议按下面节奏。

## 第 1 周
- 锁定模板真相源
- 锁定 tenant access policy
- 锁定 workflow status / execution 字段口径
- 输出 06 / 07 / 08 三份目标设计文档

## 第 2 周
- 开始 tenant/queryset 统一整改
- 开始 workflow 执行链止血
- 开始前端管理员守卫和协议收敛

## 第 3-4 周
- 开始模板域 API 与前端 store 收敛
- 开始统一凭证入口与 provider 常量
- 开始 execution observability UI 收敛

## 第 5-8 周
- 完成模板资产闭环
- 完成资源中心基础能力
- 开始模板运营与团队共享功能

---

## 六、验收标准

最终不是看你改了多少文件，而是看是否达成这些结果：

### 架构层
- 是否只剩一个模板真相源
- 是否只剩一套 tenant access rule
- 是否只剩一条凭证主入口
- 是否只剩一条 execution 主观测线

### 产品层
- 模板是否形成完整生命周期
- 工作流是否形成完整执行闭环
- 团队资源是否可安全共享
- 成本与日志是否可追踪

### 开发层
- 新增功能是否能明确挂靠业务域
- 新增接口是否遵守统一 DTO 和权限规则
- 前端新增页面是否不再依赖兼容字段拼凑

---

## 七、最后的建议

这个项目最危险的方向，是继续“哪里痛修哪里、哪里缺补哪里”。

正确方向是：

1. **先统一规则**  
2. **再统一真相源**  
3. **再统一业务闭环**  
4. **最后才做增长功能**

如果按这个路线推进，Flowly 是可以从当前的多模块半成品，走到真正的平台底座的。

如果不按这个路线，而是继续横向加页面、加接口、加兼容字段，系统复杂度会继续上升，但业务价值不会同步提升。

这不是编码问题，这是发展方向问题。

---

## 八、执行状态（2026-06-06）

以下为本文档中列出的各 Phase/Task 的处理状态。

### Phase 1 止血封堵

| Task | 内容 | 状态 |
|---|---|---|
| 任务 1 | 统一租户访问边界 | ✅ 完成 — `tenants/access.py` + `TenantPermission` 委托；`user.tenant` 空操作模式全线修复（branding/training/datasets/website_generator/annotations）；agents 子资源 (Conversation/Tool/Execution)、annotations AnnotationItem queryset 加了 tenant 边界 |
| 任务 2 | workflow 执行链止血 | ✅ 完成 — 统一时间线 `/timeline/`、`/analytics/`、`ExecutionLogViewSet` tenant 边界 |
| 任务 3 | 前端权限与协议止血 | ✅ 完成 — marketplace API 层统一到 canonical endpoint |

### Phase 2 业务域收敛

| Task | 内容 | 状态 |
|---|---|---|
| 任务 4 | 模板系统收敛为唯一真相源 | ✅ 主体完成 — `WorkflowTemplate` canonical，install/rate/report 均已使用真实记录模型 |
| 任务 5 | 统一资源中心 | 🔶 进行中 — `APICredential` 凭证模型已统一 |
| 任务 6 | 执行观测域 | ✅ 完成 — Layer 3 analytics、时间线端点、访问边界全部修复 |

### 已新增基础设施

| 新增项 | 说明 |
|---|---|
| `TemplateInstall` 模型 | canonical 安装记录表，取代 session 统计 |
| `TemplateRatingRecord` 模型 | canonical 评分记录表，取代 session 评分 |
| `TemplateReport` 模型 | canonical 举报记录表，取代计数器 |
| `WorkflowTemplate.is_public` | 公开可见性控制字段 |
| `WorkflowTemplate.report_count` | 举报计数字段 |
| `/executions/{id}/timeline/` | 统一时间线端点 |
| `/executions/analytics/` | Layer 3 指标聚合端点 |

### 未解决（诚实列出）

| 问题 | 优先级 | 说明 |
|---|---|---|
| 三套模板系统长期合并 | 高 | 字段不兼容、数据隔离，需要架构决策 |
| `execution_logs` JSONField 废弃 | 中 | 需要 DB 迁移，统一写入 `ExecutionLog` 表 |
| `source_execution_id` 重试链路 | 中 | 需要 migration 新增字段 |
| 任务 1 跨 app 清理 | ✅ 已解决 | agents/annotations 子资源边界已修复；`user.tenant` 空操作全线修复 |
| 任务 5 凭证模型 | 中 | `Provider` 常量分裂、gateway 层凭证路径待统一 |
| 任务 7 模板资产运营化 | 低 | 推荐算法、精选模板位、审核流等 |
| 任务 8 团队协作治理 | 低 | 审批流、预算额度控制 |
| 任务 9 智能辅助能力 | 低 | NL 生成 workflow、基于历史的优化建议 |

