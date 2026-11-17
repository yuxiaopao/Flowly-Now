# Desktop 续轮交付验证（2026-11-01）

本记录对应本轮最终冻结源码构建的 Windows x64 **未签名目录包**，包含应用回归界面、模型配置、模型部署能力边界提示、知识资源跳转的数字租户 ID 修复，以及应用请求内的只读工作流执行追踪。未创建签名安装器，未发布或部署。

## 产物与构建

- 最终产物：`E:\Flowly-now\.cache\desktop-package-continuation-final-qa\win-unpacked\Flowly.exe`。使用全新目录，未覆盖旧 `.cache/desktop-package-qa` 或 `.cache/desktop-package-continuation-qa`。前一包不包含后续执行追踪修复，不能替代本记录最终产物。
- `npm run build:renderer` 实际退出 0；avatar 类型检查与构建通过（1.88 秒），Electron 模式主 Vite 构建通过（25.23 秒）。原有大型可选模块 chunk 提示仍存在，未隐藏告警。
- 执行 `sync-training`、`sync-clip`、`sync-icons` 后，使用已安装的 Electron 45.2.1 构建；electron-builder 26.18.0 实际退出 0，未执行签名。
- 递归替换 renderer 前，已解析核对 `Desktop/renderer`、`Frontend/dist` 及其父路径、子树均在工作区内，且没有目录联接或符号链接；新包路径也已核对。

打包命令在 `E:\Flowly-now\Desktop` 执行：

```powershell
npm exec -- electron-builder --dir --win --x64 --publish never --config.electronDist=./node_modules/electron/dist --config.win.signAndEditExecutable=false --config.directories.output=../.cache/desktop-package-continuation-final-qa
```

| 产物 | 字节数 | SHA-256 |
| --- | ---: | --- |
| `win-unpacked/Flowly.exe` | 249789440 | `0a3b1659db97dc52130debaf67f22d349a3d553aad61b8a59336c1cd78b4430d` |
| `win-unpacked/resources/app.asar` | 33021262 | `44b37115bcbb3757f4a382feeac2d0ba91d3aa985bb101d46a57878ac72464da` |

## 共享训练资源

逐字节核对实际包内 `resources/training-scripts` 与 `resources/app.asar.unpacked/training-scripts`。两个训练入口及五个 helper 均等于 canonical 后端源码经过既有 `rewriteRuntimeImports` 映射后的内容：

- `scripts/train_model.py`、`scripts/build_clip_index.py`。
- `training/yolo_weights.py`、`training/clip_service.py`、`training/clip_trainer.py`、`training/tabular_artifacts.py`、`datasets/ml_format_validators.py`。

实际 `train_model.py` 已引用 `flowly_runtime.tabular_artifacts`，共享标准化元数据 helper 的打包 SHA-256 为 `dfb3f51656d31bba04ba6c00d0c649d7f6e47927a7dd10e2f566526a7c3d976f`。ASAR 内 main/preload、QA profile、renderer 信任校验、训练进程控制和 renderer 入口也逐字节匹配本次构建目录。额外确认实际包含 `application-workflow-trace-toggle` 的编译模块 `renderer/assets/Detail-Db_mRdpP.js` 存在于最终 ASAR，且与最新 renderer 字节一致。

## 测试结果

| 验证 | 结果与边界 |
| --- | --- |
| `npm run test:unit` | 最终同步后实际执行，42/42 通过，无失败或跳过。 |
| `npm run test:integration` | 原脚本因 REST/WS 缺少认证真实失败。修复脚本后，对隔离 QA 后端实际完成认证注册、心跳、WebSocket `connected` 与 `agent_registered_ack`、所属账号列表、无 GPU 设备过滤及测试设备删除，退出 0。匿名注册实际为 401。未触发训练。 |
| `npm run test:smoke` | 已安装原生 Electron 45.2.1 实际载入新 renderer，新 Profile 配置不含云 API token，退出 0。 |
| 实际目录包 Chrome DevTools MCP | 独立端口 9223 实际验证 `Flowly.exe`，退出 0；真实 Vue UI 已挂载，preload IPC 可调用，未暴露原生 `require`，无云凭据，QA 网络阻断生效。 |

实际包验证结果：

```json
{"packaged":true,"electron":"45.2.1","rendererMounted":true,"isolatedProfile":true,"ipcBridge":true,"contextIsolation":true,"noCloudCredential":true,"networkBlocked":true}
```

集成脚本现要求显式 `FLOWLY_ISOLATED_QA=1`、本机服务及服务端 `isolated: true` 标记，再使用仅该测试库的 token 或账号登录。REST 与 WS 均使用认证 header，不把 token 放入 URL 或日志。测试设备声明无 GPU，不能进入可训练设备列表。README 已同步该运行条件。

本次最终包的原生 smoke 与实际包 TEMP/TMP 都指向新建的工作区 `.cache/desktop-continuation-final-temp-*` 私有目录；未使用系统用户 Profile，未删除旧 Profile。最终包使用绝对 exe 路径启动，成功运行的新 Profile 由已有 helper 在退出时清理。结束后 9223 无监听，未发现本包遗留进程；未操作 9222。

两个声明文件的构建前后 SHA-256 保持不变：`components.d.ts` 为 `8C70D97C0AD4D5CA6AD542438A56B7D5D41E24E0EFDA5CD6FEB8CC25A2F86C23`，`auto-imports.d.ts` 为 `EF45E2CE4CEB50AE46781F2B67BDBAD5486144F21847B7A18015855C9213E08F`。

## 证据与限制

最终包完整日志位于 `.cache/desktop-continuation-final-{renderer-build,unit,native-smoke,integration,package-build,package-resources,packaged-mcp}.log`；本次产物哈希和资源清单位于 `.cache/desktop-continuation-final-package-proof.json`。核对深层 ASAR 资源时使用 Windows 规范化路径，不能将分隔符造成的提取错误误判为资源缺失。

本次验证覆盖本地 Windows 目录包和隔离协议链路，不代表签名安装器、macOS/Linux 包、真实云端设备部署、真实模型质量、GPU 长训练或生产环境已验收。实际包 QA 模式阻断网络，认证 REST/WS 协议使用独立集成脚本连接私有 QA 服务验证。
