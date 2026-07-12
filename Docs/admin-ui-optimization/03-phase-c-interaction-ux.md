# Phase C — 交互与体验打磨

> 状态：**已完成**  
> 预估：2–3 天 | 优先级：**P1**  
> 最后更新：2026-06-18

---

## 一、目标（做完什么算成功）

主要操作路径具备 **可预期的反馈**（loading / toast / 空态 / 错误重试），配置类操作有 **防误触**，整体交互延迟感 < 300ms（感知层面）。

---

## 二、背景与问题

基线已有 `showLoading()`、`showToast()`、`renderSkeleton()`（定义于 `flowly_base.html`），但各 Panel **使用不一致**：

- 部分 API 失败仅 console + toast
- 配置中心切换模块可能丢失未保存修改
- 列表首屏有时空白闪烁

---

## 三、全局交互规范（实施前对齐）

| 场景 | 规范 |
|------|------|
| 导航 Tab 点击 | `showLoading()` → 整页跳转 → `hideLoading()` |
| API GET 列表/图表 | 首屏 `renderSkeleton()`，失败显示重试按钮 |
| API POST 保存 | 按钮 disabled + spinner，成功 toast 3s，失败 toast + 保留表单 |
| 空数据 | 使用 `.f-empty` 结构（图标 + 标题 + 说明） |
| 危险操作 | confirm 或 modal 二次确认 |
| 动效 | 150–250ms，`cubic-bezier(0.16, 1, 0.3, 1)`，尊重 `prefers-reduced-motion` |
| 触控 | 可点击区域 ≥ 44×44px |

---

## 四、任务清单

### C1 — 控制台（`flowly_dashboard.html`）

- [ ] **C1.1** `dashboard-data` 失败：展示 `.f-empty` +「重试」按钮调用 `dashboard.load()`
- [ ] **C1.2** 图表无数据：Canvas 区域显示「暂无执行记录」文案
- [ ] **C1.3** 自动刷新开启时：页头 meta 或 Tab 标题旁小圆点脉冲（可选）
- [ ] **C1.4** `recent_activity` 为空：空态而非空白 `#activityFeed`

**涉及文件**：`flowly_dashboard.html`、内联 dashboard JS

**完成标准**：断网刷新控制台，可见错误态 + 可恢复

---

### C2 — 配置中心（`settings_modules.js` + hub 模板）

- [ ] **C2.1** 表单 dirty 标记：任意 input 变更后 `SettingsHub.isDirty = true`
- [ ] **C2.2** 切换模块 / 离开页面前：`beforeunload` 或 confirm「有未保存修改」
- [ ] **C2.3** 模块切换同步 URL：`history.pushState` 更新 `?module=xxx`
- [ ] **C2.4** 浏览器后退/前进：读取 `module` 参数并 `SettingsHub.loadModule()`
- [ ] **C2.5** 保存成功：toast + `isDirty = false`

**涉及文件**：`settings_modules.js`、`flowly_settings_hub.html`

**完成标准**：改字段 → 切模块 → 弹出提示；保存后 URL 与模块一致

---

### C3 — 功能开关（`features_panel.html`）

- [ ] **C3.1** 搜索框 `oninput` 改为 debounce 300ms
- [ ] **C3.2** 导入 JSON：modal 内预览条数 + 确认后再 POST
- [ ] **C3.3** toggle 失败：开关回滚到原状态

**涉及文件**：`features_panel.html` 内联 JS

---

### C4 — AI 模型（`ai_models_panel.html`）

- [ ] **C4.1** `testAll()` 改为 per-provider 状态（loading / ok / fail 图标）
- [ ] **C4.2** API Key 输入：`type=password` + 显示/隐藏切换
- [ ] **C4.3** 保存 Provider 后 toast + 列表刷新

**涉及文件**：`ai_models_panel.html`、相关 JS

---

### C5 — 审计（`audit_panel.html`）

- [ ] **C5.1** 日期筛选 presets：今天 / 7 天 / 30 天 快捷按钮
- [ ] **C5.2** 导出 CSV：`showLoading()` + 完成 toast
- [ ] **C5.3** 表格 loading 用 skeleton rows

**涉及文件**：`audit_panel.html`

---

### C6 — 系统（`system_panel.html`）

- [ ] **C6.1** health check `error/warning` 项可点击展开详情 message
- [ ] **C6.2** 自动刷新 10s 时在页头 meta 显示「下次刷新倒计时」（可选）
- [ ] **C6.3** psutil 不可用时友好文案，非「—」

**涉及文件**：`system_panel.html`

---

### C7 — Tab 栏增强（可选）

- [ ] **C7.1** `Alt+1` … `Alt+7` 跳转对应 Tab（需 preventDefault 不与浏览器冲突）
- [ ] **C7.2** 审计 Tab 徽章：今日操作数 > 0 时小圆点（需 API 或 data attribute）
- [ ] **C7.3** `localStorage` 记录上次 Tab，欢迎页 CTA 智能跳转（可选）

**涉及文件**：`flowly_base.html` 或 `custom_admin.js`、`flowly_tab_bar.html`

**完成标准**：快捷键在 README 或页脚提示中 documented

---

## 五、涉及文件清单

| Panel | 模板 | JS |
|-------|------|-----|
| 控制台 | `flowly_dashboard.html` | 模板内联 |
| 配置中心 | `flowly_settings_hub.html` | `settings_modules.js` |
| 功能开关 | `features_panel.html` | 模板内联 |
| AI 模型 | `ai_models_panel.html` | 模板内联 |
| 审计 | `audit_panel.html` | 模板内联 |
| 系统 | `system_panel.html` | 模板内联 |
| 全局 | `flowly_base.html` | 内联 + `custom_admin.js` |

---

## 六、依赖与阻塞

| 项 | 说明 |
|----|------|
| 建议 after B | 视觉稳定后再打磨交互，避免重复改模板 |
| C2 依赖 API | 配置模块 REST 已存在，无新后端需求 |
| C7 | 纯前端，可最后做 |

---

## 七、验收标准

- [ ] 每个 Panel 至少 1 个空态 + 1 个错误恢复路径可手动验证
- [ ] 配置中心未保存切换模块有拦截
- [ ] 全局 toast 不堆叠超过 3 条（可选 limit）
- [ ] 无 0ms 瞬时状态跳变（按钮至少 150ms 反馈）

---

## 八、备注 / 测试方法

1. Chrome DevTools → Network → Offline，逐 Panel 点刷新
2. 配置中心改站点名不保存，点侧栏模块 nav
3. 功能开关搜索快速输入，确认 debounce
4. 浏览器测试须用 **chrome-devtools MCP**（项目规范）
