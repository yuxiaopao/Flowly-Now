# 最终交付产物验证（2026-10-31）

本记录对应当前工作区已冻结源码的本地构建。下列结果均已等待命令实际退出；未执行远端发布、SSH、镜像推送或生产数据库操作。

## 最终镜像

以下为 `docker image inspect --format '{{.Id}}'` 的实际结果，不能以较早的中间镜像替代。

| 本地标签 | 最终 image ID |
| --- | --- |
| `flowly-reliability-backend:local` | `sha256:38de83c60271aa84e2834165c58ef4be5e6bd7fd364c234da1cfafe25eeb81a3` |
| `flowly-delivery-final:local` | `sha256:fd890acc1721dc0147952aeb9da3e084ef7d62832c77c25f59fb56b4f5d3889d` |

构建命令均从项目根目录运行：

```powershell
docker build --progress=plain --target dependencies -f docker/Dockerfile.backend -t flowly-backend-dependencies:validation .
docker build --progress=plain -f docker/Dockerfile.backend -t flowly-reliability-backend:local .
docker build --progress=plain -f docker/Dockerfile.frontend -t flowly-delivery-final:local .
```

后端依赖阶段完整安装共同 profile 和安全约束，并通过 `pip check`。系统依赖及官方 CPU PyTorch 层复用构建缓存；共同依赖使用 BuildKit pip 下载缓存，仍执行完整安装和一致性检查。最终 runtime 复制当前全部后端源码。前端最终 Docker 编译已包含首页百分比/布局及应用页 CSS 作用域修复，avatar 类型检查与构建通过（2.43 秒），主 Vite 构建通过（54.62 秒）。

日志：`.cache/backend-final-dependencies-build.log`、`.cache/backend-final-runtime-build.log`、`.cache/frontend-final-build.log`。

## 最终 Linux 后端镜像

在带独立 UUID 标签、2 GiB 内存限制的临时容器中验证；容器使用 `--network none`，未挂载业务目录、数据库或 GPU。生产模式必需配置使用本次临时 QA 密钥及明确的本机 hosts/CORS，未复制宿主 `.env` 或修改业务设置。

- `pip check`：无损坏的依赖关系。实际安装清单保存在 `.cache/backend-final-installed-packages.txt`。
- 实际导入：PyTorch `2.13.0+cpu`、TorchVision `0.28.0+cpu`、NumPy `2.5.4`、OpenCV `5.0.0`、Ultralytics `8.4.194`；CUDA 不可用，符合 CPU 镜像声明。
- 实际算子：BGR 小矩阵缩放和 RGB 转换、CPU autograd 梯度、TorchVision CPU NMS 均断言通过，无模型下载或训练任务。
- Django `check`：0 问题；`makemigrations --check --dry-run`：`No changes detected`。
- 使用 `config.workflow_test_settings` 的全新 SQLite 内存数据库完整执行全部迁移成功，包含 applications `0001–0004`、core 新迁移和 website_generator `0008`。
- 使用独立内存测试环境执行 **86 项全部通过**（16.11 秒）：应用真实 HTTP/ORM 发布与调用、递归工作流冻结/子执行、执行器与任务可靠性、datasets 初始表接管及网站历史字段迁移边界。
- 上述 86 项包含 `training/test_analytics.py::YoloAnalyticsTests::test_symlinked_report_cannot_escape_run_directory`，该项在 Linux **实际通过**，补齐 Windows 权限限制导致的唯一 skip。

运行脚本：`.cache/validate-final-backend-image.py`；完整日志：`.cache/backend-final-image-validation.log`。临时测试容器在退出路径核对精确 ID/UUID 标签后清理。

## 前端 Nginx 和真实生产包

最终前端镜像通过 `nginx -t`。在自建临时 Docker 网络和本机假上游中验证：根页面、SPA 深层路由、入口 JS、WASM MIME、静态资源、媒体资源均返回 200；`/api/file.png` 仍正确代理到 API。SSE 首帧到达 **0.000 秒**，后续事件 **2.000 秒**到达，确认没有等待流结束才转发。

随后在仅绑定随机本机端口的临时入口 `http://127.0.0.1:59674`，通过 `backend:host-gateway` 接入本次隔离 QA 后端。使用真正的 Chrome DevTools MCP 验证最终压缩生产包，命令退出 0，结果如下：

```json
{"productionBundle":true,"ok":true,"loginObserved":true,"sameOrigin":true,"apiRequests":8,"proxyStatus":200,"applicationGrid":true,"homeFlow":true}
```

这覆盖真实登录和同源 API 往返、应用测试区布局，以及从应用详情返回首页后的整行垂直布局，验证最终 CSS 作用域在压缩产物中生效。

日志：`.cache/frontend-final-nginx-validation.log`、`.cache/production-entry-chrome-final.log`。假上游、前端测试容器和临时网络均已清理；真实 QA 入口在浏览器验证结束后核对 ID/标签清理，`.cache/final-production-entry.json` 已记录 `cleaned: true`。

## Windows 桌面最终产物

最新前端源码执行 `npm run build:renderer` 成功，主渲染器构建 39.20 秒；两个源码声明文件的构建前后 SHA-256 一致。完成 canonical 训练/CLIP 脚本和独立运行 helper 同步。

- `npm run test:unit`：**42/42** 通过，无跳过。
- `npm run test:smoke`：安装的原生 Electron **45.2.1** 在全新 QA profile 成功载入渲染器，配置中无云 API token。
- Windows x64 unpacked 打包命令实际退出 0：

```powershell
$env:CSC_IDENTITY_AUTO_DISCOVERY='false'
npm exec -- electron-builder --dir --win --x64 --publish never --config.electronDist=./node_modules/electron/dist --config.win.signAndEditExecutable=false --config.directories.output=../.cache/desktop-package-qa
```

上述命令在 `E:\Flowly-now\Desktop` 运行，产物是**未签名的 Windows 测试目录包**。ASAR 核对确认 main/preload、QA profile、renderer trust、训练进程控制和 Vue 入口均存在；外置训练资源包含四个独立 helper。

对实际打包的 `Flowly.exe`，通过真正的 Chrome DevTools MCP、独立调试端口 **9223** 和全新 QA profile 验证成功，命令退出 0：

```json
{"packaged":true,"electron":"45.2.1","rendererMounted":true,"isolatedProfile":true,"ipcBridge":true,"contextIsolation":true,"noCloudCredential":true,"networkBlocked":true}
```

这确认实际 Vue UI 挂载、真实 preload IPC 可用、未暴露原生 require，且 QA 网络阻断生效。测试未读取原有用户 profile、云凭证或触发训练。结束后自有 Electron 进程树停止、临时 QA profile 删除，9223 已确认无监听，未发现本次遗留的 Electron/MCP 进程。另一个独立 Chrome profile 因自动审批拒绝清理而保留，本步骤未尝试替代删除，详情见 [浏览器验证记录](browser-verification-20261031.md)。

| 产物 | SHA-256 |
| --- | --- |
| `E:\Flowly-now\.cache\desktop-package-qa\win-unpacked\Flowly.exe`（249,789,440 字节） | `6d55496f3073c70e96264411770dc33b8e699cdd7d085a49ef05b37c067fb0c3` |
| `E:\Flowly-now\.cache\desktop-package-qa\win-unpacked\resources\app.asar` | `fa13cbc6e45b104d6acc3fda7f8264c6d104c39966712c72a46c431ac4ad83d0` |

日志：`.cache/desktop-final-renderer-build.log`、`.cache/desktop-final-unit.log`、`.cache/desktop-final-native-smoke.log`、`.cache/desktop-final-package-build.log`、`.cache/desktop-final-package-resources.log`、`.cache/desktop-final-packaged-mcp.log`。

## 持续交付门禁和边界

CI 现从 Dockerfile 的两个 CPU ARG 严格提取 `x.y.z+cpu`，仅对对应精确公共版本进行独立审计，避免 PyPI 不识别 `+cpu` 后缀而漏报。实际 `torch==2.13.0` / `torchvision==0.28.0` 审计退出 0，**无已知漏洞**；格式错误如 `latest` 会拒绝。共同 profile 的完整依赖解析审计门禁保留。YAML、版本提取/拒绝错误格式、main/develop 发布分支及审计依赖关系静态校验通过；部署/健康检查 **28/28** 复测通过。

日志：`.cache/cpu-pinned-audit-config-check.log`、`.cache/cpu-pinned-audit-final.log`、`.cache/deployment-final-cpu-audit-regressions.log`。

本记录不宣称操作系统包、宿主可选 GPU/模型环境或整套镜像供应链已经全部审计清零。未替换宿主 CUDA/PyTorch 模型栈；Python profile 仍保留经过约束的兼容范围，本次实际产物由上述镜像 ID 和安装清单标识。未验证签名安装器、macOS/Linux 桌面发行包或外部云部署。应用镜像回滚也不等于数据库迁移自动回滚。
