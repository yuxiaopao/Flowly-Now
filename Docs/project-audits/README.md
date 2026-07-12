# Flowly 全项目审查与设计文档索引

> **最近更新：2026-06-06** — Phase 1 tenant 访问边界全线修复，`user.tenant` 空操作问题已解决
>
> - `03-action-plans/01-master-action-plan.md` → **Section 八**（执行状态）
> - `02-domain-designs/03-execution-observability-design.md` → **Section 十三**（执行状态）

---

本目录已按主题拆分为子文件夹，避免后续继续堆在根目录导致混乱。

生成时间：2026-06-05

## 目录结构

### `00-index/`
用于放总览类文档。
- `00-overview.md`：总览、产品方向、架构主线

### `01-audits/`
用于放问题审查、现状诊断、风险分级。
- `01-workflows-audit.md`
- `02-tenant-boundary-audit.md`
- `03-template-market-audit.md`
- `04-frontend-architecture-audit.md`
- `05-gateway-credential-audit.md`

### `02-domain-designs/`
用于放目标架构、领域设计、母规则文档。
- `01-template-domain-target-architecture.md`
- `02-tenant-access-policy.md`
- `03-execution-observability-design.md`

### `03-action-plans/`
用于放跨主题的总行动方案、阶段路线图。
- `01-master-action-plan.md`

### `04-migration-notes/`
用于放专项迁移记录、字段迁移说明、执行级备忘。
- `01-marketplace-field-migration-summary.md`

### `05-training-workflow/`
用于放训练模型专题、训练闭环方案、训练资产设计。
- `README.md`
- `01-training-model-workflow-blueprint.md`

### `06-team-module-analysis/`
用于放团队/租户模块的深度解析、问题诊断、功能机会与修复路线图。
- `01-team-module-architecture.md`：模型架构、API 设计、现存问题、功能机会全景分析

## 编号规则

现在改为 **子目录内独立编号**，不再强行维护一条跨目录的全局流水号。

这样做的原因很直接：
- 已经有子目录分类了，再用全局编号会让命名和查找都变得别扭
- 不同类型文档的新增频率不同，强绑一条编号链后续维护成本很高
- 目录本身已经承担了一层分类语义，编号只需要在当前目录内保证顺序即可

### 当前规则
- `00-index/`：保留 `00-*` 作为总览入口
- `01-audits/`：按审查主题顺序编号
- `02-domain-designs/`：按设计文档产出顺序编号
- `03-action-plans/`：按行动方案顺序编号
- `04-migration-notes/`：按迁移记录顺序编号
- `05-training-workflow/`：按训练专题文档顺序编号

## 建议阅读顺序
1. `00-index/00-overview.md`：先看全局方向
2. `01-audits/03-template-market-audit.md`：看模板系统重复建设问题
3. `04-migration-notes/01-marketplace-field-migration-summary.md`：看 marketplace 字段迁移现状与阻塞
4. `02-domain-designs/01-template-domain-target-architecture.md`：看模板域目标架构
5. `01-audits/02-tenant-boundary-audit.md`：看租户边界风险
6. `02-domain-designs/02-tenant-access-policy.md`：看统一访问母规则
7. `02-domain-designs/03-execution-observability-design.md`：看执行观测域设计、执行链路、数据口径与访问边界
8. `05-training-workflow/01-training-model-workflow-blueprint.md`：看训练模型完整业务闭环、数据版本化、模型资产化与发布链路
9. `05-team-module-analysis/01-team-module-architecture.md`：看团队/租户模块全景分析、3P0+7P1+4P2 问题清单、12 项功能机会、修复优先级建议
10. `01-audits/04-frontend-architecture-audit.md`：看前端契约与状态问题
11. `01-audits/05-gateway-credential-audit.md`：看凭证与网关治理问题
12. `03-action-plans/01-master-action-plan.md`：最后看总体推进顺序

## 后续归档规则
后面继续新增文档时，按下面规则放置：

- 总览/目录/导航类：放 `00-index/`
- 审查/巡检/风险诊断类：放 `01-audits/`
- 目标架构/领域规则/策略设计类：放 `02-domain-designs/`
- 路线图/阶段计划/总行动方案类：放 `03-action-plans/`
- 迁移总结/执行纪要/专项改造记录类：放 `04-migration-notes/`
- 训练模型专题/训练闭环/模型资产设计类：放 `05-training-workflow/`
- 团队/租户模块全景分析/问题诊断/功能路线图类：放 `05-team-module-analysis/`

### 新增命名规则
- 同一子目录内按 `01-`, `02-`, `03-` 递增
- 文件名主体使用英文短横线命名
- 文件名应直接表达主题，不写模糊标题
- 不再在不同子目录里复用“全局阶段号”来表达文档重要性

## 补充说明
- `04-migration-notes/01-marketplace-field-migration-summary.md` 是对 `marketplace.WorkflowTemplate` 字段统一与真实 schema rename 准备状态的专项总结。
- 它不是模板域的最终架构文档，模板域终局定义以 `02-domain-designs/01-template-domain-target-architecture.md` 为准。
