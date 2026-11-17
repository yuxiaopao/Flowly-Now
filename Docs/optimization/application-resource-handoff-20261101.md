# 应用草稿与知识资源创建往返验证

日期：2026-11-01。范围为新建知识应用时，缺少知识库的实际创建往返；没有增加工作流创建返回的半成品入口。

## 用户流程

1. 在应用中心填写名称、用途说明、类型和空间。
2. 当前空间没有可绑定知识库时，点击“先创建知识库”，先保存当前应用草稿，再进入知识库创建。
3. 知识库创建固定在原空间。取消返回原应用草稿；创建失败保留知识库输入并允许重试；成功返回后，只有服务端仍列为可绑定的同空间资源才会自动选中。
4. 返回的应用保留原名称、说明、类型和空间，最终仍由真实应用 API 校验权限并持久化。

正常知识库入口沿用原行为。原应用离开确认保留，仅明确暂存成功后的单次内部跳转放行。

## 状态与权限

- 草稿放在浏览器当前 tab 的 sessionStorage。URL 仅携带随机 nonce，不放名称、说明、令牌或外部返回地址；返回路径限定为应用中心与知识库内部路径。
- 状态以用户 ID 和当前登录会话 SID 隔离。同会话刷新 token 保留草稿，退出登录、切换账号或产生新 SID 会清理旧状态。
- 应用草稿保留 2 小时，资源创建交接有效 15 分钟。交接过期不能继续自动创建/绑定，但有效期内的原应用草稿可恢复；草稿完全过期时移除私人表单内容，并给出明确提示。
- 空间权限失效不自动改为个人空间；服务端 403 不清空用户输入；返回资源还必须通过服务端可绑定资源列表核验。
- 创建资源已经成功但返回导航失败时保留已创建 ID，重试返回不会再次提交创建请求。
- 知识库表单提供取消和离开保护；无效上下文、跨身份、存储失败、过期与服务端拒绝均有明确反馈。

主要实现为 `Frontend/src/utils/applicationResourceHandoff.js`、应用 `Index.vue` / `ApplicationResourceField.vue` 和知识库 `Index.vue`。

## 自动化验证

定向测试使用真实 Vue Router、Pinia、Element Plus、全局离开确认和 Axios adapter；仅在 HTTP 边界提供响应，保留页面实际提交和状态流转。

- 新增往返回归 17 项，包含团队成功创建、取消、403 保留/重试、失效权限、TTL、跨身份、同 SID 刷新、导航失败不重复提交、正常知识库入口及最终应用 403。真实 API 数字团队 ID 的标签回显新增红绿回归：验证过的原始 ID 类型用于 Element Plus 选项匹配，交接与权限比较仍统一为字符串。
- 与既有应用工作区和 RAG adapter 关联测试共 **40/40 通过**，日志 `.cache/application-resource-handoff-final.log`。
- 涉及源码及测试的 ESLint **0 error / 0 warning**，`git diff --check` 通过。
- 真实浏览器脚本为 `Scripts/application_context_chrome_mcp.mjs`，强制检查隔离 QA marker 和初始为空的团队资源。所有创建动作经实际页面 DOM，随后读取真实 API 验证持久化归属。

真实 Chrome 已确认仅 nonce 的跳转 URL、锁定原团队、取消后名称/说明/团队不变且没有创建集合；另已实际提交知识库并返回自动选中。Desktop renderer 构建期间 public 资源变化触发 Vite 整页刷新后，sessionStorage 中的原草稿及 completed nonce 仍保留并恢复。

最终应用提交发现并修复了一个后端阻断：没有显式选择存储时，团队知识库被自动分配到个人默认 VectorStore，应用按同空间规则拒绝绑定并返回 `source_unavailable`。负责 RAG 的代理修复默认存储选择，并保留应用的同空间隔离规则。

修复加载后，在原私有 SQLite、原用户会话 SID 和原 completed nonce 页面继续验收，未重新登录或重建种子。对这次已经存在、没有文档的 QA 知识库，通过真实前端 `ragApi` 正式 POST 新建同团队 memory store、PATCH 绑定该知识库，再 GET 核对知识库和存储都属于原团队。没有暗改数据库，也没有迁移或删除已有文档。

随后通过原应用表单 DOM 提交，真实 API 持久化成功；GET 核验名称、说明、团队、collection ID 均与暂存草稿一致。实际 Chrome DevTools MCP **4/4 检查通过**，由前两项成功检查与修复后的后两项合并，最终进程 exit 0。此结论明确包含对既有空 QA 知识库的授权 API 修复，不宣称四项均在一次全新环境执行。默认存储修复本身由后端真实 HTTP 回归另行覆盖。

浏览器日志为 `.cache/application-context-chrome-final.log`（前两项及原始失败）和 `.cache/application-context-chrome-continuation.log`（同 nonce 继续、存储归属及最终落库通过）。MCP 子进程已退出，9222 已归还主代理；保留本次 Context 页面供后续独立 QA，没有操作用户原浏览器或业务资源。

## 独立 QA 运行器只读复核

复核对象为 `Scripts/continuation_qa_guard.py` 和 `Scripts/run_continuation_qa.py`，不将其作为生产启动器。当前实现采用私有 `.cache/continuation-runtime-<UUID>`、SQLite 和 filesystem Celery broker，真实 eager=False Worker 只消费唯一测试队列。

已逐处核对：

- 纯标准库 guard 在 Django/Celery 导入前检查 manifest、token、工作目录、三个 broker URL、memory result backend 和禁 dotenv 配置；子进程环境采用 allowlist，拒绝继承业务数据库、Redis 和模型密钥。
- 私有根目录、manifest/settings/fixture metadata、SQLite 主文件及 WAL/SHM 均验证 canonical path，包含 dangling symlink；media、backup、tmp、logs、消息和模型 fixture 目录也必须留在私有根目录。
- 本地 provider 仅接受带明确端口的 `http://127.0.0.1:<port>/v1`，不读取或请求用户已有模型服务。
- 停止前核对 PID、创建时间、解释器、完整命令、工作目录和实际进程环境中的本次 root/token；子进程归属同样检查，系统 conhost 在读取环境前排除。
- 初次浏览器运行发现私有 seed 创建团队却缺少成员记录，页面按正式权限规则只显示个人空间；未以客户端伪造空间或放宽业务权限绕过。

此复核不替代隔离 guard 单测，也不宣称生产 DB、模型、Worker 或外部服务已配置。此前生命周期 fixture 的首次意外 Redis 连接及修复事实保留在 `Docs/guides/deployment/local-services.md`，没有对该 Redis 进行诊断、补偿清理或再次访问。
