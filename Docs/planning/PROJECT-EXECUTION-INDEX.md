# Flowly-now 项目完善计划 — 执行索引

> 主计划：`PROJECT-IMPROVEMENT-PLAN.md`
> 创建时间：2026-06-03
> 任务追踪：`flowly-improvement/task.json`

---

## 任务总览

| 任务 ID | 阶段 | 类型 | 名称 | 依赖 | 状态 |
|---------|------|------|------|------|------|
| `plan-security` | Phase 0 | 规划 | 安全加固方案文档 | — | 进行中 |
| `plan-testing` | Phase 1 | 规划 | 测试覆盖方案文档 | — | 进行中 |
| `plan-hardcode` | Phase 2 | 规划 | 硬编码+质量方案文档 | — | 进行中 |
| `plan-frontend` | Phase 3 | 规划 | 前端架构方案文档 | — | 进行中 |
| `plan-devops` | Phase 5 | 规划 | DevOps+文档方案文档 | — | 进行中 |
| `exec-secret-key` | Phase 0 | 实施 | SECRET_KEY 修复 | `plan-security` | 待执行 |
| `exec-cors-perms` | Phase 0 | 实施 | CORS+权限审查 | `plan-security` | 待执行 |
| `exec-input-validation` | Phase 0 | 实施 | 输入验证增强 | `plan-security` | 待执行 |
| `exec-backend-tests` | Phase 1 | 实施 | Backend 模块测试 | `plan-testing` | 待执行 |
| `exec-workflow-serializer-tests` | Phase 1 | 实施 | Serializer 测试 | `plan-testing` | 待执行 |
| `exec-e2e-tests` | Phase 1 | 实施 | Playwright E2E | `plan-testing` | 待执行 |
| `exec-constants` | Phase 2 | 实施 | 常量枚举体系 | `plan-hardcode` | 待执行 |
| `exec-module-consistency` | Phase 2 | 实施 | 模块补全 | `plan-hardcode` | 待执行 |
| `exec-exception-handling` | Phase 2 | 实施 | 异常处理规范化 | `plan-hardcode` | 待执行 |
| `exec-naming-standards` | Phase 2 | 实施 | 命名规范统一 | `plan-hardcode` | 待执行 |
| `exec-ts-migration` | Phase 3 | 实施 | TS 迁移 | `plan-frontend` | 待执行 |
| `exec-component-lib` | Phase 3 | 实施 | 组件库抽取 | `plan-frontend` | 待执行 |
| `exec-cicd` | Phase 5 | 实施 | CI/CD 完善 | `plan-devops` | 待执行 |
| `exec-dependencies` | Phase 5 | 实施 | 依赖管理统一 | `plan-devops` | 待执行 |
| `exec-docs-restructuring` | — | 实施 | 文档重构 | — | 待执行 |

---

## 阶段详细文档索引

| 文档 | 内容 |
|------|------|
| `Docs/phases/PHASE-0-SECURITY-HARDENING.md` | 安全加固详细方案 |
| `Docs/phases/PHASE-1-TEST-COVERAGE.md` | 测试覆盖详细方案 |
| `Docs/phases/PHASE-2-HARDCODE-QUALITY.md` | 硬编码+代码质量详细方案 |
| `Docs/phases/PHASE-3-FRONTEND-ARCH.md` | 前端架构优化详细方案 |
| `Docs/phases/PHASE-5-DEVOPS-DOCS.md` | DevOps+文档详细方案 |

---

## 执行依赖图（DAG）

```
plan-security ──┬── exec-secret-key
                ├── exec-cors-perms
                └── exec-input-validation

plan-testing ───┼── exec-backend-tests
                ├── exec-workflow-serializer-tests
                └── exec-e2e-tests

plan-hardcode ──┼── exec-constants
                ├── exec-module-consistency
                ├── exec-exception-handling
                └── exec-naming-standards

plan-frontend ──┼── exec-ts-migration
                └── exec-component-lib

plan-devops ────┼── exec-cicd
                └── exec-dependencies

exec-docs-restructuring (无依赖，可随时执行)
```

---

## 当前进度

- [x] 初始化任务追踪系统 (`flowly-improvement/task.json`)
- [x] 创建总体执行索引文档
- [ ] Phase 0-5 详细方案文档（5 个子智能体并行创建中）
- [ ] 执行阶段开始（等待方案文档完成后启动）

---

*本文件由 AI Agent 自动生成*
