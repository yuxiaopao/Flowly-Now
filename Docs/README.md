# Flowly 文档中心

本文档中心只放项目知识资产，不放测试产物、临时截图和运行日志。根目录仅保留 `README.md`、`AGENTS.md`、依赖与环境配置文件，其余项目规划、参考资料和历史报告统一归入本目录。

## 目录规划

| 目录 | 用途 | 维护规则 |
| --- | --- | --- |
| `guides/` | 本地开发、部署、环境启动指南 | 面向实际操作，保持步骤可执行 |
| `api/` | API 规范、一致性指南、接口开发提示 | 接口变更时同步更新 |
| `planning/` | 项目改进计划、执行索引、任务追踪数据 | 只放仍有执行价值的计划 |
| `project-audits/` | 架构审计、领域设计、迁移记录、行动计划 | 按审计主题分组，不再堆到根目录 |
| `phases/` | 分阶段治理方案 | 保留阶段性基线，完成后写入执行状态 |
| `tasks/` | 团队任务拆分文档 | 任务归档前保持编号稳定 |
| `reference/` | 长篇参考资料、项目结构、搭建手册、提示词、答辩材料 | 不作为日常入口，避免污染主索引 |
| `maintenance/` | 文件盘点、清理建议、目录治理记录 | 每次大规模整理后更新 |
| `reports/` | 代码图谱、审计类静态报告 | 按报告来源分子目录 |
| `archive/` | 历史材料、学生作业、旧工具页面 | 只读归档，不再作为当前事实来源 |
| `admin-ui-optimization/` | Admin UI 专项优化文档 | 专项闭环，独立维护 |
| `desktop-ml-site-factory/` | 桌面端 ML Site Factory 专项文档 | 专项闭环，独立维护 |
| `superpowers/` | Agent 计划与验证记录 | 只保存可复用计划 |
| `软件著作权/` | 软著申请材料 | 申报材料独立归档 |

## 快速入口

| 场景 | 文档 |
| --- | --- |
| 本地开发 | [`guides/deployment/local-dev.md`](guides/deployment/local-dev.md) |
| Docker 部署 | [`guides/deployment/docker.md`](guides/deployment/docker.md) |
| API 开发 | [`api/API-DEVELOPMENT-PROMPT.md`](api/API-DEVELOPMENT-PROMPT.md) |
| 项目结构参考 | [`reference/PROJECT-STRUCTURE.md`](reference/PROJECT-STRUCTURE.md) |
| 数据库表名参考 | [`reference/database-tables.md`](reference/database-tables.md) |
| 项目搭建参考 | [`reference/setup-guide.md`](reference/setup-guide.md) |
| 总体改进计划 | [`planning/PROJECT-IMPROVEMENT-PLAN.md`](planning/PROJECT-IMPROVEMENT-PLAN.md) |
| 执行索引 | [`planning/PROJECT-EXECUTION-INDEX.md`](planning/PROJECT-EXECUTION-INDEX.md) |
| 文件清理记录 | [`maintenance/file-inventory-and-cleanup-plan.md`](maintenance/file-inventory-and-cleanup-plan.md) |
| 测试目录规范 | [`../tests/README.md`](../tests/README.md) |

## 命名与落位规则

- 新文档文件名使用小写英文和连字符，历史中文文件名保留在归档或参考目录中。
- 当前事实优先写入 `guides/`、`api/`、`planning/`、`project-audits/`，不要直接新增到 `Docs/` 根目录。
- 测试报告、截图、Playwright 结果统一写入 `tests/artifacts/`，不要放在 `Docs/` 或仓库根目录。
- 模块 README 可以保留在模块目录旁边，例如 `Backend/codegraph/README.md`、`Desktop/README.md`，但跨模块规划必须回到 `Docs/`。
