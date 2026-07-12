# Phase D — 架构与可维护性

> 状态：未开始  
> 预估：1–2 天 | 优先级：**P1–P2**  
> 最后更新：2026-06-12

---

## 一、目标（做完什么算成功）

- 多环境部署无需改模板里的 URL
- 样式/模板结构清晰，新人 30 分钟能定位要改的文件
- 无冗余静态资源副本

---

## 二、背景与问题

| 问题 | 影响 |
|------|------|
| `localhost:5200` 硬编码 |  staging/production 链接错误 |
| CSS 分散三处 + 内联 | 改色/改组件需多处同步 |
| `admin_static/css/` 与 `admin_static/admin/css/` 重复 | 改错文件、collectstatic 混淆 |
| `:has(.flowly-shell)` | 旧 Safari 等可能不隐藏 content-header |
| Panel 模板平铺在 `templates/admin/` | 文件增多后难浏览 |

---

## 三、任务清单

### D1 — `FRONTEND_URL` 环境变量

- [ ] **D1.1** 在 [`Backend/config/settings.py`](../../Backend/config/settings.py) 增加：

```python
FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://localhost:5200')
```

- [ ] **D1.2** 替换硬编码位置：
  - `JAZZMIN_SETTINGS.topmenu_links` 用户端 URL
  - `flowly_tab_bar.html`
  - `flowly_welcome.html`
- [ ] **D1.3** 文档化 `.env` 示例（可写入 [`Docs/guides/deployment/local-dev.md`](../guides/deployment/local-dev.md) 一行）

**完成标准**：

- 设置 `FRONTEND_URL=https://app.example.com` 后，Tab 工具与用户端 CTA 全部指向新 URL
- grep 模板无裸 `localhost:5200`（CORS 等后端配置可保留或一并 env 化）

---

### D2 — 静态资源去重

- [ ] **D2.1** diff 对比：
  - `admin_static/css/custom_admin.css` vs `admin_static/admin/css/custom_admin.css`
  - `admin_static/js/custom_admin.js` vs `admin_static/admin/js/custom_admin.js`
- [ ] **D2.2** 确认 Jazzmin 引用路径为 `admin/css/...`（见 `JAZZMIN_SETTINGS.custom_css`）
- [ ] **D2.3** 删除未被引用的副本目录或文件
- [ ] **D2.4** 同样处理 `logo.svg` 双份（`admin/img/` vs `img/`）

**完成标准**：

- 每个逻辑资源仅一份 canonical 路径
- `python manage.py collectstatic --dry-run` 无意外 duplicate 警告（若适用）

---

### D3 — 模板目录重组

- [ ] **D3.1** 创建 `Backend/templates/admin/panels/`
- [ ] **D3.2** 移动（或复制后删旧）：
  - `flowly_dashboard.html` → `panels/dashboard.html`
  - `flowly_settings_hub.html` → `panels/settings_hub.html`
  - `features_panel.html` → `panels/features.html`
  - `ai_models_panel.html` → `panels/ai_models.html`
  - `audit_panel.html` → `panels/audit.html`
  - `system_panel.html` → `panels/system.html`
  - `flowly_welcome.html` → `panels/welcome.html`（或保留根目录）
- [ ] **D3.3** 更新 [`admin_site.py`](../../Backend/config/admin_site.py) 中 `TemplateResponse` 路径
- [ ] **D3.4** 更新 [`references/key-files-index.md`](references/key-files-index.md)

**完成标准**：

- 所有 Panel 路由正常 200
- `templates/admin/` 根目录仅保留 `flowly_base.html`、`login.html`、`includes/`

---

### D4 — Admin context processor

- [ ] **D4.1** 新建 `Backend/admin/context_processors.py`（或 `config/context_processors.py`）：

```python
def flowly_admin(request):
    return {
        'frontend_url': settings.FRONTEND_URL,
        'site_name': ...,  # 从 SystemSetting 或 default
    }
```

- [ ] **D4.2** 注册到 `TEMPLATES[0]['OPTIONS']['context_processors']`
- [ ] **D4.3** 模板改用 `{{ frontend_url }}`、`{{ site_name }}`
- [ ] **D4.4** 登录页显示动态站点名

**完成标准**：

- 修改 `SystemSetting.site_name` 后，登录页与欢迎页标题一致（允许缓存 TTL 说明）

---

### D5 — `:has()` 降级方案

- [ ] **D5.1** 在 `FlowlyAdminSite` 各 Panel view 的 context 增加 `body_class='flowly-panel-page'`
- [ ] **D5.2** Jazzmin base 模板 body 标签支持 `{{ body_class }}`（或通过 `extra_body_class` block）
- [ ] **D5.3** CSS 双写：

```css
body.flowly-panel-page .content-header { display: none; }
body:has(.flowly-shell) .content-header { display: none; }
```

**完成标准**：

- 在不支持 `:has` 的浏览器（或禁用）仍隐藏 Flowly 页重复 header

---

## 四、涉及文件清单

| 任务 | 主要文件 |
|------|----------|
| D1 | `settings.py`, `flowly_tab_bar.html`, `flowly_welcome.html` |
| D2 | `admin_static/**` |
| D3 | `templates/admin/**`, `admin_site.py` |
| D4 | `context_processors.py`, `settings.py`, `login.html`, `flowly_welcome.html` |
| D5 | `admin_site.py`, `flowly_shell.css`, Jazzmin base override（若需） |

---

## 五、依赖与阻塞

| 项 | 说明 |
|----|------|
| D1 与 B4 | 登录页站点名依赖 D4 更完整 |
| D3 | 纯重构，需全 Panel 冒烟 |
| D2 | 删除前必须 diff，避免删错 canonical 文件 |

---

## 六、验收标准

- [ ] `grep -r localhost:5200 Backend/templates/admin` 无结果
- [ ] 静态资源目录结构文档与磁盘一致
- [ ] Panel 模板路径变更后 CI/手动 smoke 通过
- [ ] context processor 在 login + flowly 页均可用

---

## 七、备注

- D3 为 **P2**，可在 A/B/C 完成后再做，避免大规模移动与功能开发冲突
- D1 可与 Phase B **并行**，投入小收益大

详见 [`references/key-files-index.md`](references/key-files-index.md)
