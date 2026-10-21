# 管理端 UI 优化 - 进度看板

> 每完成一项任务，将 `- [ ]` 改为 `- [x]`，并更新下方总览表与更新日志。
> **最后更新**：2026-06-18

---

## 阶段总览

| Phase | 名称 | 进度 | 状态 | 文档 |
|-------|------|------|------|------|
| 基线 | 基线（Tab 壳层等） | 5/5 | 已完成 | [`00-current-state.md`](00-current-state.md) |
| A | 信息架构 | 4/4 | 已完成 | [`01-phase-a-information-architecture.md`](01-phase-a-information-architecture.md) |
| B | 视觉统一 | 5/5 | 已完成 | [`02-phase-b-visual-unification.md`](02-phase-b-visual-unification.md) |
| C | 交互体验 | 7/7 | 已完成 | [`03-phase-c-interaction-ux.md`](03-phase-c-interaction-ux.md) |
| D | 架构维护 | 5/5 | 已完成 | [`04-phase-d-architecture-maintainability.md`](04-phase-d-architecture-maintainability.md) |
| 验收 | 统一验收 | 35/35 | **已完成** | [`05-acceptance-checklist.md`](05-acceptance-checklist.md) |

---

## 基线已完成（代码已落地，勿重复做）

- [x] 浏览器式 Tab 栏（7 模块 + API/用户端工具按钮）
- [x] `flowly_shell.css` Shell 样式与 a11y 基础
- [x] 各 Panel 紧凑页头 `f-page-header`
- [x] 深蓝白主题（Jazzmin + Flowly）
- [x] 欢迎页 Bento 精简（非 Tab 入口）

---

## Phase A - 信息架构（4/4）

- [x] A1 明确 Tab vs 侧栏分工，清理重复 `custom_links`
- [x] A2 功能开关双入口决策与交叉链接
- [x] A3 欢迎页入口与 Tab 最终对齐审查
- [x] A4 侧栏分组/排序优化

---

## Phase B - 视觉统一（5/5）

- [x] B1 抽取 `flowly_tokens.css`
- [x] B2 抽离 `flowly_components.css`，精简 `flowly_base` 内联 CSS
- [x] B3 Jazzmin 列表/表单/详情与 f-* 对齐（`custom_admin.css` @import tokens）
- [x] B4 登录页纳入品牌体系（`site_name` 动态展示）
- [x] B5 原生页 `content-header` 样式统一

---

## Phase C - 交互体验（7/7）

- [x] C1 控制台：失败重试 + 图表/活动空态 + 自动刷新指示
- [x] C2 配置中心：未保存提示 + URL `?module=` 同步
- [x] C3 功能开关：搜索防抖 + 导入预览 + toggle 失败回滚
- [x] C4 AI 模型：Provider 配置状态 + 密钥掩码占位 + 测试反馈
- [x] C5 审计：日期 presets + 导出条数反馈
- [x] C6 系统：健康检查失败详情展开
- [x] C7 Tab 栏增强：Alt+1-7 快捷键 + title 提示

---

## Phase D - 架构维护（5/5）

- [x] D1 `FRONTEND_URL` 环境变量，去除硬编码
- [x] D2 静态资源去重（删除 `admin_static/css|js|img` 冗余副本）
- [ ] D3 模板目录重组（`panels/`）：可选，未阻塞验收
- [x] D4 Admin context processor（`frontend_url` / `site_name`）
- [x] D5 `:has()` 降级为 `body_class`
- [x] D6 DEBUG 中 `staticfiles_urlpatterns`（验收期修复 Jazzmin CSS 404）

---

## 更新日志

| 日期 | 完成项 | 负责人 | 备注 |
|------|--------|--------|------|
| 2026-06-12 | 建立文档体系；基线 5 项标记已完成 | Agent | 对应 Tab 壳层、Shell CSS、页头、主题、欢迎页 Bento |
| 2026-06-18 | 首轮验收 18/35；报告见 tests/artifacts/acceptance | Agent | P0：登录跳转、侧栏重复、用户端 URL、site_name |
| 2026-06-18 | **验收 35/35 全部通过**；GOV-01 + A11Y 复验 | Agent | smoke 含审计写入检测 |

---

## 下一步建议

管理端 UI 统一优化 **已全部完成**。可选后续：

1. D3（可选）：Panel 模板迁入 `templates/admin/panels/`
2. 生产部署：`collectstatic` + 反向代理静态资源
