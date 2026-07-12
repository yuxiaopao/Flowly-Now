# 管理端 UI — 关键代码文件速查

> 改 UI 前先查此表，避免改错文件。  
> 最后更新：2026-06-12

---

## 一、路由与上下文

| 文件 | 职责 |
|------|------|
| [`Backend/config/admin_site.py`](../../Backend/config/admin_site.py) | `FlowlyAdminSite`：Panel 路由、`each_context`、Tab 高亮 `_resolve_flowly_active_tab`、JSON API |
| [`Backend/admin/constants.py`](../../Backend/admin/constants.py) | `FLOWLY_ADMIN_TABS`、`SETTING_MODULE_KEYS`、默认值 |
| [`Backend/config/settings.py`](../../Backend/config/settings.py) | `JAZZMIN_SETTINGS`、`JAZZMIN_UI_TWEAKS`、`STATICFILES_DIRS` |

### Panel 路由映射

| 方法 | URL name | 模板 |
|------|----------|------|
| `index` / `flowly_welcome` | `/admin/` | `flowly_welcome.html` |
| `flowly_dashboard` | `flowly/` | `flowly_dashboard.html` |
| `settings_hub` | `flowly/settings/` | `flowly_settings_hub.html` |
| `features_panel` | `flowly/features/` | `features_panel.html` |
| `ai_models_panel` | `flowly/ai-models/` | `ai_models_panel.html` |
| `audit_panel` | `flowly/audit/` | `audit_panel.html` |
| `system_panel` | `flowly/system/` | `system_panel.html` |

### JSON API（Panel 数据）

| 路径 | 方法 |
|------|------|
| `/admin/flowly/dashboard-data/` | GET |
| `/admin/flowly/system-data/` | GET |
| `/admin/flowly/ai-models-data/` | GET |
| `/admin/flowly/api/toggle-feature/` | POST |
| `/admin/flowly/api/update-config/` | POST |
| `/api/v1/admin/settings/modules/` | REST（配置中心） |

---

## 二、模板

| 文件 | 职责 |
|------|------|
| [`templates/admin/flowly_base.html`](../../Backend/templates/admin/flowly_base.html) | Panel 基类：设计系统 CSS、toast/loading/apiCall JS |
| [`templates/admin/includes/flowly_tab_bar.html`](../../Backend/templates/admin/includes/flowly_tab_bar.html) | Tab 栏 + 外链工具 |
| [`templates/admin/login.html`](../../Backend/templates/admin/login.html) | 登录页覆盖 |
| [`templates/admin/flowly_welcome.html`](../../Backend/templates/admin/flowly_welcome.html) | 欢迎页 |
| [`templates/admin/flowly_dashboard.html`](../../Backend/templates/admin/flowly_dashboard.html) | 控制台 |
| [`templates/admin/flowly_settings_hub.html`](../../Backend/templates/admin/flowly_settings_hub.html) | 配置中心壳 |
| [`templates/admin/features_panel.html`](../../Backend/templates/admin/features_panel.html) | 功能开关 |
| [`templates/admin/ai_models_panel.html`](../../Backend/templates/admin/ai_models_panel.html) | AI 模型 |
| [`templates/admin/audit_panel.html`](../../Backend/templates/admin/audit_panel.html) | 审计 |
| [`templates/admin/system_panel.html`](../../Backend/templates/admin/system_panel.html) | 系统状态 |

**Phase D3 目标路径**：`templates/admin/panels/*.html`

---

## 三、静态资源

| 文件 | 加载方式 | 职责 |
|------|----------|------|
| [`admin_static/admin/css/custom_admin.css`](../../Backend/admin_static/admin/css/custom_admin.css) | Jazzmin `custom_css` | 全局 Jazzmin 主题、侧栏、表格、登录 |
| [`admin_static/admin/css/flowly_shell.css`](../../Backend/admin_static/admin/css/flowly_shell.css) | `flowly_base` link | Tab 栏、页头、a11y、隐藏 content-header |
| [`admin_static/admin/js/custom_admin.js`](../../Backend/admin_static/admin/js/custom_admin.js) | Jazzmin `custom_js` | 快捷键、Django messages→toast、表单 submit |
| [`admin_static/admin/js/settings_modules.js`](../../Backend/admin_static/admin/js/settings_modules.js) | settings hub | 九模块表单 + CRUD |
| [`admin_static/admin/img/logo.png`](../../Backend/admin_static/admin/img/logo.png) | Jazzmin logo | 品牌 Logo |

### 疑似重复（Phase D2 处理）

| 路径 | 说明 |
|------|------|
| `admin_static/css/custom_admin.css` | 与 `admin/css/` 可能重复 |
| `admin_static/js/custom_admin.js` | 与 `admin/js/` 可能重复 |
| `admin_static/img/logo.svg` | SVG 副本 |

---

## 四、后端业务（配置中心）

| 文件 | 职责 |
|------|------|
| [`Backend/admin/models.py`](../../Backend/admin/models.py) | SystemSetting、LegalDocument、BackupRecord 等 |
| [`Backend/admin/services/config_service.py`](../../Backend/admin/services/config_service.py) | 模块校验、公开配置缓存 |
| [`Backend/admin/module_views.py`](../../Backend/admin/module_views.py) | REST API views |
| [`Backend/admin/urls.py`](../../Backend/admin/urls.py) | `/api/v1/admin/...` 路由 |
| [`Backend/admin/admin.py`](../../Backend/admin/admin.py) | ModelAdmin 注册 |

---

## 五、按优化 Phase 改哪些文件

| Phase | 主要文件 |
|-------|----------|
| A | `settings.py`（custom_links）、`features_panel.html`、`settings_modules.js` |
| B | `flowly_tokens.css`（新建）、`flowly_components.css`（新建）、`flowly_base.html`、`custom_admin.css`、`login.html` |
| C | 各 `*_panel.html`、`settings_modules.js`、`flowly_base.html` |
| D | `settings.py`、context processor（新建）、`admin_site.py`、模板路径、`admin_static/**` |

---

## 六、Frontend 用户端（非本优化范围，但有关联）

| 文件 | 关联 |
|------|------|
| [`Frontend/src/stores/siteConfig.js`](../../Frontend/src/stores/siteConfig.js) | 读公开配置 |
| [`Frontend/src/api/public.js`](../../Frontend/src/api/public.js) | `GET /api/v1/public/site-config/` |
| [`Frontend/src/assets/logos/logo.png`](../../Frontend/src/assets/logos/logo.png) | Logo 源（已复制到 admin_static） |

---

## 七、文档索引

| 文档 | 链接 |
|------|------|
| 总 README | [`../README.md`](../README.md) |
| 进度 | [`../PROGRESS.md`](../PROGRESS.md) |
| 现状 | [`../00-current-state.md`](../00-current-state.md) |
| 验收 | [`../05-acceptance-checklist.md`](../05-acceptance-checklist.md) |
