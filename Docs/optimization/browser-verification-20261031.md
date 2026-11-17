# 应用交付浏览器验证

日期：2026-10-31。全部自动化通过真实 `chrome-devtools-mcp`，独立 Chrome Profile 与 `127.0.0.1:9222`；先确认调试端口、`navigate_page`、前端 5200 与隔离后端 `/admin` 可用。未使用 Playwright、cursor-ide-browser 或其他浏览器自动化通道。

## 隔离与证据边界

后端由 `Scripts/run_isolated_reliability_backend.py` 创建临时 SQLite 数据库、独立测试账号和样例资料，不连接业务数据库。产品变更脚本还要求 `FLOWLY_ISOLATED_QA=1`，并校验仅该隔离服务提供的 `__isolated-qa__` 标记后才写入、恢复或清理数据。实际模型密钥与跟踪服务在该进程中清空。

知识助手使用真实文档入库、索引、检索与来源记录，通过本机 HTTP 模型协议 fixture 返回确定性回答。它证明协议和产品链路可运行，不能证明真实模型质量。识别项目仅验证来源、权重配置和工作流重建；样例 `.pt` 文件明确不是可推理模型。

## 最终结果

| 脚本 | 结果 | 已验证的实际行为 |
| --- | --- | --- |
| `Scripts/landing_chrome_mcp.mjs` | 6/6 | 桌面和 390 手机边界；四步 tab 的角色、焦点、左右/Home/End/环绕；6 项 FAQ 的 Enter 开关；匿名 CTA 保留应用目标进入登录；减少动态时页面动画为零 |
| `Scripts/applications_chrome_mcp.mjs` | 7/7，退出 0 | 表单创建工作流应用、真实图测试、测试证据关联 v1、一次性专属密钥调用、管理接口拒绝应用密钥、源图修改不改变 v1、草稿重新测试发布 v2、回滚 v1、吊销密钥立即拒绝、请求详情可追溯 |
| `Scripts/product_features_chrome_mcp.mjs` | 13/13，退出 0 | 下列知识、配置、账单、数据与界面场景 |
| `Scripts/project_reliability_chrome_mcp.mjs` | 9/9，退出 0 | 工作流 A/B 切换、未失焦编辑的刷新/离开保护、取消/确认离开、真实同步执行与认证 WebSocket、缺失文档清旧图和重试、ECharts 实际画布、DOMPurify 阻止可执行输出 |

产品脚本的 13 项检查包含：

1. 没有检索证据时请求实际失败，不能发布。
2. 已索引资料通过 HTTP 协议调用返回回答及持久化来源，再发布知识应用。
3. 识别项目打开真实源工作流；旧项目经明确操作创建完整 4 节点、3 连线的私有配置副本。
4. 在真实 Editor 修改节点名称并保存，`foo_bar`、`fooBar`、`Customer_ID`、UUID 字面量、原节点引用、模型 manifest 和 wizard 配置均不被递归改名。
5. 点击账单下载返回实际 `QA-BILL-001`、12.00 金额与“非税务发票”说明的 HTML 凭证。
6. 导出为创建时快照；修改源工作流后下载仍为原值；取消恢复不创建任何副本。
7. 确认恢复实际新增私有工作流，原资源仍存在。本轮最终运行从 4 份变为 8 份。
8. 服务端备份策略可以保存并回读。该实例报告调度配置存在；没有运行真实跨周期计划，不把配置存在冒充 worker 已健康执行。
9. Analytics 未知用量和成本显示未知，不补假 0 或假币种。
10. 真实成功率比例格式正确；应用页到首页后，标题、概况、交付步骤、资源区保持垂直顺序和完整宽度；四种主题均无横向溢出，各指标文字均留在其单元格内。
11. 真实前端 `streamExecuteWorkflow` 发出带认证的 POST，执行 start→300ms delay→end。收到 6 帧，首末帧相隔 364ms，记录实际完成且大小写输入键原样入库。
12. 390 手机布局有界，侧栏可打开并由 Escape 关闭且关闭后 inert。另用明确的临时布局样例检验长数字/耗时换行，随后恢复真实内容；没有将样例数字作为后台统计。
13. 错误密码不能清理数据；重新预览并输入正确密码与确认文字后，实际删除 9 份个人工作流，账号、应用、账单、备份和已索引知识保留，知识应用仍可真实运行。

## 实测发现并修复的问题

- 首页曾把 0..1 的成功率直接拼接 `%`。现通过集中配置的 Intl percent 输出，例如 `0.92857 → 92.9%`；未知值继续显示 `—`。
- 固定六列加不换行数字曾在真实统计下挤出页面。指标现按可用宽度排列，完整保留长数字并允许自然换行；对应 8 项定向测试通过。
- 应用调试区和首页曾共用全局 `.delivery-workbench` 规则，访问应用后污染首页。应用的三处规则已限定 `.applications-page` 祖先；真实 CSS 注入、Detail→Home→Detail 级联回归先红后绿，相关 27 项通过，浏览器跨页布局与截图复核通过。
- 新交付界面减少动态设置显式关闭动画和过渡；Landing 范围实测运行动画为 0。

脚本调试中修正过按钮选择、弹窗过渡等待、备份新记录识别及手机/桌面切换后的测试上下文恢复；没有通过伪造接口结果、降低业务断言或删除失败场景使测试通过。

## 图片和日志

- [工作台首屏，展开导航](../verification/ai-team-20261031/delivery-workbench-viewport.png)
- [工作台完整页面](../verification/ai-team-20261031/delivery-workbench.png)
- [手机工作台](../verification/ai-team-20261031/delivery-mobile.png)
- [应用请求与执行详情](../verification/ai-team-20261031/application-requests.png)
- [备份与数据管理](../verification/ai-team-20261031/personal-backup.png)
- [Landing 桌面](../verification/ai-team-20261031/landing-desktop.png)

最终日志位于 `.cache/applications-chrome-final.log`、`.cache/product-features-chrome-final.log`、`.cache/project-reliability-chrome-final.log` 和 `Docs/verification/ai-team-20261031/landing-results.json`。实际截图已查看，新增工作台首屏也核对了 224px 展开侧栏及 1440px 视口无横向溢出。

本记录只涵盖上述本地浏览器范围。最终生产镜像同源入口与 Windows Desktop 打包由交付验证单独记录；没有将本地通过写成生产部署成功。

最终前端镜像 `sha256:fd890acc1721dc0147952aeb9da3e084ef7d62832c77c25f59fb56b4f5d3889d` 另经真实 Chrome 检查通过，退出 0：实际登录被观测到，8 个 API 请求均为同源，代理 health 为 200，应用测试区仍为 grid，返回 Home 后完整宽度与垂直顺序正确。记录为 `.cache/production-entry-chrome-final.log`。临时生产入口已按精确 container ID 与 label 清理。

测试服务 5200、8000 和独立 Chrome 9222 已停止，核对无监听；用户原有应用与业务端口未停止。自动审批审查拒绝删除本轮独立 Chrome 临时目录，返回 `blocked by policy`、未提供更具体原因，因此没有重试其他删除手段。保留目录为 `C:\Users\18984\AppData\Local\Temp\flowly-chrome-ce801ef59a7f468191d1f696232f15e9`，不是用户日常 Chrome Profile。
