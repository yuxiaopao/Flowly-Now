# 05 - 管理端 UI 统一验收清单

> 全阶段完成后使用；也可分 Phase 部分勾选。
> 最后更新：2026-06-18（第二轮复验）

---

## 一、使用说明

- 每项测试通过后勾选 `[x]`
- 失败项记录到 [`PROGRESS.md`](PROGRESS.md) 更新日志
- 浏览器自动化测试 **必须** 使用 `chrome-devtools` MCP；**禁止** `cursor-ide-browser`（见 [`AGENTS.md`](../../AGENTS.md)）

---

## 二、信息架构（Phase A）

- [x] **A-01** 侧栏无与 Tab 同 URL 的 custom_links
- [x] **A-02** 「功能开关」Tab 与配置中心 features 模块有明确文案区分 + 交叉链接
- [x] **A-03** 欢迎页 Bento 不含 Tab 已覆盖的 7 模块重复入口
- [x] **A-04** 新用户 30 秒内能找到：改站点名、开关功能、看系统状态

---

## 三、视觉统一（Phase B）

- [x] **B-01** 主色 `#1d4ed8` 在 Panel、Jazzmin 列表、表单、按钮上一致
- [x] **B-02** 无紫色主色、无 gradient text 统计数字
- [x] **B-03** 工作流 changelist 与控制台 Panel 圆角/间距同级
- [x] **B-04** 工作流 changeform 保存栏与 `f-btn-primary` 视觉一致，`input[name="_save"]` 主色为 `#1d4ed8`
- [x] **B-05** 登录页到欢迎页无品牌断层
- [x] **B-06** `flowly_tokens.css` 单点改色全局生效（Panel 外置 + Jazzmin `custom_admin.css` 内联）

---

## 四、交互体验（Phase C）

- [x] **C-01** Tab 点击有 loading 条，页面加载后消失
- [x] **C-02** 控制台 API 失败可点重试，统计/图表/活动均有重试按钮
- [x] **C-03** 配置中心未保存切换模块有提示
- [x] **C-04** 配置中心 URL 含 `?module=` 且可分享
- [x] **C-05** 各 Panel 列表/图表有空态；功能开关 seed 后 41 项正常加载
- [x] **C-06** 保存操作有 toast
- [x] **C-07** 危险操作有 confirm

---

## 五、架构与配置（Phase D）

- [x] **D-01** 生产环境无模板硬编码 `localhost:5200`（默认 env 开发可接受）
- [x] **D-02** `FRONTEND_URL` 环境变量控制用户端链接
- [x] **D-03** 静态资源无未使用的 duplicate 文件
- [x] **D-04** 站点名在登录页、欢迎页可配置一致
- [x] **D-05** Panel 页 `body.flowly-panel-page` 生效

---

## 六、无障碍与响应式

- [x] **A11Y-01** Tab 可键盘聚焦，方向键切换焦点
- [x] **A11Y-02** 交互元素 `:focus-visible` 可见
- [x] **A11Y-03** 跳过链接可跳到 `#flowly-main`
- [x] **A11Y-04** Tab 最小触控高度 >= 44px
- [x] **RESP-01** 375px 宽度 Tab 可横向滚动
- [x] **RESP-02** 配置中心 900px 以下侧栏换行

---

## 七、端到端用户路径（必测）

1. [x] **E2E-01** 登录 -> 欢迎
2. [x] **E2E-02** Tab「控制台」-> 数据加载
3. [x] **E2E-03** Tab「配置中心」-> module URL + 模块表单
4. [x] **E2E-04** Tab「功能开关」-> toggle -> seed -> toggle + toast「功能已开启」
5. [x] **E2E-05** 侧栏工作流 -> 编辑 changeform
6. [x] **E2E-06** Tab「系统」-> 健康检查
7. [x] **E2E-07** Tab「用户端」-> `FRONTEND_URL`

---

## 八、业务与规范

- [x] **GOV-01** 配置变更写入审计；toggle 后 `FeatureAuditLog` 有记录
- [x] **GOV-02** 无 dead code / orphan 引用
- [x] **GOV-03** 硬编码 URL/色值已抽离
- [x] **GOV-04** API 500 不白屏（代码层具备反馈）

---

## 九、验收结论

| 字段 | 内容 |
|------|------|
| 验收日期 | 2026-06-18 |
| 验收人 | Agent（chrome-devtools MCP） |
| 通过项 / 总项 | **35 / 35**（100%） |
| 遗留 P0 | **无** |
| 遗留 P2 | **无** |
| 是否发布 | **通过** |
| 详细报告 | [`tests/artifacts/acceptance/ADMIN_UI_ACCEPTANCE_REPORT.md`](../../tests/artifacts/acceptance/ADMIN_UI_ACCEPTANCE_REPORT.md) |

### 2026-06-18 第二轮关键修复

| 修复 | 文件 |
|------|------|
| DEBUG 静态文件走 finders | `config/urls.py` |
| AdminLTE 4 选择器 | `admin_static/admin/css/custom_admin.css` |
| API 响应解包 | `templates/admin/flowly_base.html` |

---

## 十、快速 smoke 命令（开发环境）

```powershell
# 后端需已运行 :8000（改 urls/模板/settings 后须重启 Daphne）
cd Backend
python manage.py check
python ..\tests\acceptance\admin_ui_accept_smoke.py

# 功能开关 E2E 前置（可选）
python manage.py seed_features
```

浏览器：Chrome 独立 Profile + `--remote-debugging-port=9222`，见 [`AGENTS.md`](../../AGENTS.md) 第十节。
