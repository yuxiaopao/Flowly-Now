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

- Node.js 18+
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
npm run test:integration    # REST + WebSocket（需后端 :8000）
```

可选：`FLOWLY_API_TOKEN=<jwt>` 验证 `/available/` 列表。

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

`npm start -- --open-workflow=<工作流 UUID>` 可直接打开指定工作流；未登录时先进入正常登录流程。前端路由、主进程 IPC 和后端训练任务均校验身份。主进程从当前账号可访问的训练任务获取项目目录，并校验工作流、节点、训练任务三者的绑定。

弹窗每 2 秒同步实际训练记录，GPU 每 5 秒采样，展示轮次与批次、损失和准确率、网络模块及参数、类别含义与样本数量、硬件占用、日志，以及最终权重、ONNX 和评估报告。尚未生成的产物显示等待状态。关闭弹窗停止订阅；独立训练进程继续运行。

已完成的本地训练可使用 `Scripts/import_local_yolo_training.py` 导入现有账号。脚本校验训练完成标记、评估与模型摘要，幂等创建工作流和训练记录；相同账号与训练目录重复导入不会创建重复任务。参数通过 `--help` 查看。导入的训练节点默认复用已完成产物，避免重新训练。

`training-monitor/reader.js` 负责文件读取与路径限制，`auth.js` 负责会话和任务绑定验证，`service.js` 提供主页面 IPC 订阅与导出。节点组件为 `Frontend/src/components/workflow/nodes/YoloTrainingNode.vue`，弹窗内容为 `Frontend/src/components/workflow/yolo/LocalYoloRunMonitor.vue` 与 `Frontend/src/components/training/live/`。

验证命令：`npm run test:monitor`；界面改动后运行 `npm run build:renderer`。真实界面验证使用官方 Chrome DevTools MCP，脚本为 `Scripts/training_monitor_chrome_mcp.mjs`，可配置 `CHROME_MCP_BROWSER_URL` 和 `CHROME_MCP_ENTRY` 连接桌面端的调试端口。

`Scripts/training_auth_dialog_chrome_mcp.mjs` 验证现有账号登录、退出权限回收和节点数据绑定；凭据从 `FLOWLY_E2E_USERNAME`、`FLOWLY_E2E_PASSWORD` 读取。配置故障弹窗的验证应在本地测试服务实际断开时执行，恢复服务后检查重试；Electron 的离线模拟不能作为请求已被阻断的依据。

