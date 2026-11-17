# Flowly Desktop

> 与 Web 端功能一致的 Flowly 桌面客户端，内置 GPU 训练 Agent（YOLO / ultralytics）

## 架构

```
Desktop (Electron)
├── main.js              主进程：窗口、训练子进程、WebSocket Agent
├── preload.js           暴露 window.flowlyDesktop + window.agentAPI
├── renderer/            打包后的 Frontend SPA（与网站相同 UI）
└── training-scripts/    同步自 Backend/scripts/train_model.py
```

桌面端加载 **完整 Frontend**（仪表盘、工作流、Agent、市场、设置等），并通过 `agentAPI` 提供本地 GPU 训练能力。

## 环境要求

- Node.js 24（与 CI 和 Docker 构建环境一致）
- Python 3.9+（训练任务，需 `pip install ultralytics`）
- NVIDIA GPU + CUDA（可选，无 GPU 时可 CPU 训练）

## 开发（推荐）

**一条命令启动 Frontend 开发服务器 + Electron：**

```bash
cd Desktop
npm install
npm run dev:full
```

前提：后端 ASGI 已运行（WebSocket 必须）：

```powershell
cd Backend
..\.venv\Scripts\daphne.exe -b 127.0.0.1 -p 8000 config.asgi:application
```

### 分步开发

```bash
# 终端 1 — Frontend
cd Frontend && npm run dev

# 终端 2 — Electron（连接 http://127.0.0.1:5200）
cd Desktop && npm run dev
```

## 本地生产模式（不依赖 Vite 开发服务器）

```bash
cd Desktop
npm run build:renderer   # 构建 Frontend 并复制到 renderer/
npm start                # 加载 renderer/index.html
```

## 打包安装包

```bash
cd Desktop
npm run build:win    # Windows NSIS
npm run build:mac    # macOS DMG
npm run build:linux  # Linux AppImage
```

## 测试

```bash
npm run sync-training
npm run test:smoke          # 构建 renderer + 启动 Electron
npm run test:integration    # REST + WebSocket（仅独立 QA 后端，需下述认证配置）
```

集成测试要求 `FLOWLY_ISOLATED_QA=1`、`FLOWLY_CLOUD_URL` 指向本机隔离服务，且该服务的 `/api/v1/__isolated-qa__/` 明确返回 `isolated: true`。提供仅用于该测试库的 `FLOWLY_API_TOKEN`，或 `FLOWLY_E2E_USERNAME` / `FLOWLY_E2E_PASSWORD`。REST 与 WebSocket 均携带认证；匿名注册必须失败。脚本创建无 GPU 的测试设备，验证所属账号列表和可训练设备过滤后删除该设备，不触发训练，也不输出凭据。不得对业务后端运行。

## 配置

| 变量 | 默认 | 说明 |
|------|------|------|
| `FLOWLY_CLOUD_URL` | `http://127.0.0.1:8000` | Agent REST/WS 云端地址 |
| `FLOWLY_DEV_SERVER_URL` | `http://127.0.0.1:5200` | 开发模式 Frontend 地址 |
| `FLOWLY_PYTHON` | 自动检测 | Python 可执行文件 |
| `FLOWLY_AGENT_ID` | 自动生成 | Agent 唯一 ID |

Frontend Electron 构建使用 `Frontend/.env.electron`（API/WS 指向 `127.0.0.1:8000`，hash 路由）。

## 桌面端 Agent 行为

1. 用户登录后，`App.vue` 自动调用 `agentAPI.connect`（携带 JWT）
2. 设置 → **桌面端 Agent** 可查看本机 GPU 状态、手动连接/断开
3. 其他用户（或同一账号在 Web 端）可在设置页 **下发训练任务** 到本机

## IPC / 前端桥接

| API | 说明 |
|-----|------|
| `window.flowlyDesktop.isDesktop` | 是否运行在 Electron |
| `window.agentAPI.connect()` | 连接云端 Agent |
| `window.agentAPI.getStatus()` | 连接 / GPU / 训练状态 |
| `window.agentAPI.startTraining()` | 本地启动训练（调试） |

Web 端通过 `@/utils/electron.js` 与 `@/composables/useDesktopAgentBridge.js` 调用上述能力。
## YOLO 工作流节点的训练详情

登录现有 Flowly 账号，打开对应工作流，点击 **YOLO 训练节点 → 查看训练详情**。详情以工作流内弹窗呈现，颜色随应用的深色、浅色、纯黑白和高对比主题切换。原有工作流向导继续保留。

通过桌面快捷方式或 `npm start` 正常启动 Flowly：有有效登录状态时进入工作台，未登录时先登录，成功后进入工作台，再从工作流列表选择要查看的工作流。启动时不自动打开指定工作流或训练详情。前端路由、主进程 IPC 和后端训练任务均校验身份。主进程从当前账号可访问的训练任务获取项目目录，并校验工作流、节点、训练任务三者的绑定。

弹窗每 2 秒同步实际训练记录，GPU 每 5 秒采样，展示轮次与批次、损失和准确率、网络模块及参数、类别含义与样本数量、硬件占用、日志，以及最终权重、ONNX 和评估报告。尚未生成的产物显示等待状态。关闭弹窗停止订阅；独立训练进程继续运行。

默认的“图表分析与模型对比”视图展示可缩放的损失、任务指标、学习率及每轮耗时。分类使用 Top-1/Top-5，检测、分割、姿态和旋转框任务读取实际 CSV 中对应的框、掩膜、关键点指标。混淆矩阵支持验证集/独立测试集切换、样本数/按真实类别归一化，并提供误分类列表、逐类 Precision/Recall/F1。原生图表和批次预览按文件更新时间刷新，可下载原图；交互图表可下载 PNG。

模型对比最多选择四条当前账号可访问的真实训练记录，指标和曲线随记录同步。不同任务不能直接比较；缺少同一数据划分证据时提示参考限制。没有其他模型的训练结果时不生成示例曲线。图表分析也可在已登录的 Web 工作流中查看；本机硬件、日志、文件定位和快照导出仍通过桌面端“实时记录、网络与导出”访问。

已完成的本地训练可使用 `Scripts/import_local_yolo_training.py` 导入现有账号。脚本校验训练完成标记、评估与模型摘要，幂等创建工作流和训练记录；相同账号与训练目录重复导入不会创建重复任务。参数通过 `--help` 查看。导入的训练节点默认复用已完成产物，避免重新训练。

`training-monitor/reader.js` 负责文件读取与路径限制，`auth.js` 负责会话和任务绑定验证，`service.js` 提供主页面 IPC 订阅与导出。节点组件为 `Frontend/src/components/workflow/nodes/YoloTrainingNode.vue`，弹窗内容为 `Frontend/src/components/workflow/yolo/LocalYoloRunMonitor.vue` 与 `Frontend/src/components/training/live/`。

验证命令：`npm run test:monitor`；界面改动后运行 `npm run build:renderer`。真实界面验证使用官方 Chrome DevTools MCP，脚本为 `Scripts/training_monitor_chrome_mcp.mjs`，可配置 `CHROME_MCP_BROWSER_URL` 和 `CHROME_MCP_ENTRY` 连接桌面端的调试端口。

图表分析回归脚本为 `Scripts/yolo_analytics_chrome_mcp.mjs`，覆盖真实曲线、矩阵与评估集合、38 类指标、原生图片、模型对比边界、四种主题和窄屏。后端只读数据接口为 `/api/v1/training/yolo-runs/<id>/analytics/`，继承训练任务的账号/租户访问校验。

`Scripts/training_auth_dialog_chrome_mcp.mjs` 验证现有账号登录、退出权限回收和节点数据绑定；凭据从 `FLOWLY_E2E_USERNAME`、`FLOWLY_E2E_PASSWORD` 读取。配置故障弹窗的验证应在本地测试服务实际断开时执行，恢复服务后检查重试；Electron 的离线模拟不能作为请求已被阻断的依据。

