# Phase A — 信息架构与导航收敛

> 状态：未开始  
> 预估：0.5–1 天 | 优先级：**P0**  
> 最后更新：2026-06-12

---

## 一、目标（做完什么算成功）

管理员能在 **30 秒内** 理解「Tab 管运营 Panel、侧栏管数据 CRUD」，且不存在两个入口做同一件事的困惑。

---

## 二、背景与问题

当前存在 **三套导航**：

1. 顶部 Flowly Tab（7 模块）
2. Jazzmin 侧栏 `custom_links`（欢迎页、控制台、AI 面板）
3. 欢迎页 Bento（已精简，但仍需与 Tab 对齐审查）

此外 **「功能开关」Tab** 与 **配置中心 features 模块** 职责重叠，用户不知道改哪里。

---

## 三、任务清单

### A1 — 明确 Tab vs 侧栏分工

- [ ] **A1.1** 文档化分工规则（写入本文件第七节）
- [ ] **A1.2** 删除侧栏中与 Tab 重复的 `custom_links`
  - 涉及文件：[`Backend/config/settings.py`](../../Backend/config/settings.py) → `JAZZMIN_SETTINGS.custom_links`
  - 删除项：`Flowly 欢迎页`、`Flowly 控制台`、`AI 模型面板`（均可由 Tab 到达）
- [ ] **A1.3** 侧栏保留：各 App Model 入口 + 必要的「配置中心快捷链」（可选一条指向 `/admin/flowly/settings/`）

**完成标准**：

- 侧栏不再出现与 Tab 完全同 URL 的 custom link
- 从侧栏进入任意页，Tab 栏仍可见且高亮正确（Flowly 页）

---

### A2 — 功能开关双入口决策与落地

- [ ] **A2.1** 确认决策（见下方「默认决策」）
- [ ] **A2.2** 配置中心 features 模块 UI 标题改为 **「功能可见性规则」**（若尚未改名）
  - 涉及：[`settings_modules.js`](../../Backend/admin_static/admin/js/settings_modules.js) 模块标题 / `MODULE_ICONS`
- [ ] **A2.3** 在「功能开关」Panel 页头增加链接：**高级规则 → 配置中心**
  - URL：`/admin/flowly/settings/?module=features`
  - 涉及：[`features_panel.html`](../../Backend/templates/admin/features_panel.html)
- [ ] **A2.4** 在配置中心 features 模块顶部增加说明：**运行时开关请前往「功能开关」Tab**

**完成标准**：

- 两个入口职责在 UI 文案上区分清晰
- 互相可一键跳转

**默认决策（可修改，修改后更新 PROGRESS 备注）**：

| 入口 | 职责 |
|------|------|
| Tab「功能开关」 | 运行时 toggle（Feature Service 即时生效） |
| 配置中心 features | CRUD「功能可见性规则」（按角色/范围） |

---

### A3 — 欢迎页入口与 Tab 对齐审查

- [ ] **A3.1** 确认欢迎页 Bento 仅含：工作流管理、用户管理、新建工作流、API 文档
- [ ] **A3.2** Hero CTA 保留：控制台、配置中心、用户端（不与 Bento 重复 Tab 可达模块列表）
- [ ] **A3.3** 底部提示文案与 Tab 操作一致（已部分完成，复核即可）

**完成标准**：

- 欢迎页无「控制台 / 配置 / 功能 / AI / 审计 / 系统」重复卡片

---

### A4 — 侧栏分组/排序优化

- [ ] **A4.1** 审查 `order_with_respect_to`，将高频 Model 置顶（Workflow、WorkflowExecution）
- [ ] **A4.2** 确认 `icons` 映射完整，无默认问号图标
- [ ] **A4.3**（可选）在 Jazzmin 文档允许范围内调整 App 显示顺序，形成 mental model：
  - 业务：workflows / agents / datasets
  - 平台：admin / gateway / features
  - 系统：auth / users / tenants

**完成标准**：

- 侧栏前 5 项覆盖 80% 日常 CRUD 路径

---

## 四、涉及文件清单

| 文件 | 改动类型 |
|------|----------|
| `Backend/config/settings.py` | 修改 `custom_links`、`order_with_respect_to` |
| `Backend/templates/admin/features_panel.html` | 增加交叉链接 |
| `Backend/admin_static/admin/js/settings_modules.js` | 模块标题/说明文案 |
| `Backend/templates/admin/flowly_welcome.html` | 审查（可能无需改） |

---

## 五、依赖与阻塞

| 依赖 | 说明 |
|------|------|
| 无 | Phase A 可独立实施 |
| 阻塞 B/C | 无；建议 A 先于 B 完成，避免 Jazzmin 改完又删链接 |

---

## 六、验收标准

- [ ] 新用户测试：「改功能开关」→ 只想到 Tab；「改某角色可见性」→ 想到配置中心
- [ ] 侧栏 custom_links 无 Tab 重复 URL
- [ ] 欢迎页 → Tab → 侧栏 CRUD 路径无循环跳转

---

## 七、备注 / 决策记录

### Tab vs 侧栏分工（定稿后勾选）

| 区域 | 职责 |
|------|------|
| **Flowly Tab** | 欢迎、控制台、配置中心、功能开关、AI 模型、审计、系统 |
| **Jazzmin 侧栏** | Django Model CRUD（工作流、用户、Agent、备份记录等） |
| **Jazzmin topmenu** | 仅外链：API 文档、用户端 |
| **欢迎页** | 品牌 + 统计 + 非 Tab 入口（工作流/用户/API） |

### 决策变更记录

| 日期 | 决策 | 决策人 |
|------|------|--------|
| 2026-06-12 | 默认保留 Tab「功能开关」，配置中心 features 改名 | 文档初稿 |
| | | |
