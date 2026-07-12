# 00 — 管理端 UI 现状诊断

> 状态：基线已记录  
> 最后更新：2026-06-12

---

## 一、目标

记录 **2026-06-12 代码库真实状态**，区分「已完成」与「待优化」，避免重复劳动或遗漏。

---

## 二、管理端技术栈

| 组件 | 版本/说明 |
|------|-----------|
| Django Admin | 项目默认 Admin Site 替换为 `FlowlyAdminSite` |
| Jazzmin | 主题与侧栏，配置于 `JAZZMIN_SETTINGS` |
| 自定义 Panel | 7 个 Flowly 页面 + 欢迎页 |
| 静态资源 | `Backend/admin_static/` → `STATICFILES_DIRS` |
| 设计系统 | `f-*` CSS 类 + `flowly_shell.css` |

**访问入口**：`http://127.0.0.1:8000/admin/`（非 `:5200` Vue 前端）

---

## 三、已完成项

| # | 项 | 说明 | 代码位置 |
|---|-----|------|----------|
| 1 | 浏览器式 Tab 栏 | 7 模块 + 右侧 API/用户端工具 | [`flowly_tab_bar.html`](../../Backend/templates/admin/includes/flowly_tab_bar.html)、[`flowly_shell.css`](../../Backend/admin_static/admin/css/flowly_shell.css) |
| 2 | Tab 路由与高亮 | `FLOWLY_ADMIN_TABS` + `_resolve_flowly_active_tab()` | [`constants.py`](../../Backend/admin/constants.py)、[`admin_site.py`](../../Backend/config/admin_site.py) |
| 3 | 整页跳转 + Loading | Tab 点击 `showLoading()`，页面 load 后隐藏 | [`flowly_base.html`](../../Backend/templates/admin/flowly_base.html) |
| 4 | 紧凑页头 | 大 Hero 改为 `f-page-header` | 各 `*_panel.html`、`flowly_dashboard.html` |
| 5 | 深蓝白主题 + Design Tokens | `flowly_tokens.css` 单源；Jazzmin `@import` | [`flowly_tokens.css`](../../Backend/admin_static/admin/css/flowly_tokens.css)、[`custom_admin.css`](../../Backend/admin_static/admin/css/custom_admin.css) |
| 6 | 组件样式外置 | `flowly_components.css`，`flowly_base` 无内联大段 CSS | [`flowly_components.css`](../../Backend/admin_static/admin/css/flowly_components.css) |
| 7 | 九模块配置中心 | REST API + dirty 提示 + URL `?module=` | [`flowly_settings_hub.html`](../../Backend/templates/admin/flowly_settings_hub.html)、[`settings_modules.js`](../../Backend/admin_static/admin/js/settings_modules.js) |
| 8 | 用户端配置同步 | `FRONTEND_URL` + context processor | [`context_processors.py`](../../Backend/admin/context_processors.py)、[`settings.py`](../../Backend/config/settings.py) |
| 9 | 欢迎页精简 | Bento 4 项 + Hero CTA | [`flowly_welcome.html`](../../Backend/templates/admin/flowly_welcome.html) |
| 10 | 无障碍 + Shell 降级 | skip link、Tab 键盘、`body.flowly-panel-page` 降级 | [`flowly_shell.css`](../../Backend/admin_static/admin/css/flowly_shell.css) |
| 11 | 侧栏 IA 清理 | Tab 与 `custom_links` 分工；features 交叉链接 | [`settings.py`](../../Backend/config/settings.py) `JAZZMIN_SETTINGS` |
| 12 | 登录页品牌 | 深蓝渐变 + 动态 `site_name` | [`login.html`](../../Backend/templates/admin/login.html) |
| 13 | Panel 交互增强 | 控制台重试、审计 presets、健康详情、AI 配置状态 | 各 `*_panel.html` |

---

## 四、遗留问题（2026-06-12 更新后）

### 仍待处理

| 问题 | 现象 | 建议 |
|------|------|------|
| Jazzmin Model 页细节 | changelist/changeform 与 f-* 仍有细微差异 | B 验收微调 |
| 功能开关导入预览 | 导入 JSON 前无 diff 预览 | C3 补全 |
| 控制台空态 | 无数据时缺专用 empty 组件 | C1 补全 |
| Tab 增强 | 快捷键 / 徽章 / 记忆 | C7 可选 |
| 模板目录 | Panel 模板仍平铺在 `templates/admin/` | D3 可选 |

### 已解决（原 P0/P1）

- Tab vs 侧栏重复入口 → Phase A
- 内联 CSS / tokens 重复 → Phase B（`flowly_tokens.css` + `flowly_components.css`）
- 硬编码 `localhost:5200` → Phase D1 + context processor
- 静态资源重复副本 → Phase D2 已删除
- 配置 dirty / URL 同步、Panel 重试、审计 presets、健康详情 → Phase C
- `:has()` 降级 → `body.flowly-panel-page`

---

## 五、当前 Tab 定义（代码快照）

```python
# Backend/admin/constants.py — FLOWLY_ADMIN_TABS
welcome      → /admin/
dashboard    → /admin/flowly/
settings     → /admin/flowly/settings/
features     → /admin/flowly/features/
ai_models    → /admin/flowly/ai-models/
audit        → /admin/flowly/audit/
system       → /admin/flowly/system/
```

---

## 六、侧栏 custom_links（已 A1 清理）

当前 `JAZZMIN_SETTINGS.custom_links` 仅保留 admin 应用下「平台配置中心」快捷链；Tab 覆盖的欢迎页/控制台/AI 面板等入口已移除。

---

## 七、前端 URL（已 D1）

`FRONTEND_URL` 环境变量 + `flowly_admin` context processor 注入 `frontend_url`；Tab 栏与欢迎页 CTA 均使用模板变量。

---

## 八、静态资源（已 D2）

历史副本 `admin_static/css/`、`admin_static/js/`、`admin_static/img/` 已删除；Jazzmin 引用路径为 `admin_static/admin/`。

---

## 九、备注

- Vue Frontend 若存在 `/admin` 路由，与本 Django Admin **不是同一入口**，优化范围以 `:8000/admin/` 为准。
- 基线 + Phase A/B/D 主体已完成；剩余见 [`PROGRESS.md`](PROGRESS.md) 与 [`05-acceptance-checklist.md`](05-acceptance-checklist.md)。
