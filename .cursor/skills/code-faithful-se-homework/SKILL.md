---
name: code-faithful-se-homework
description: Generate software-engineering homework (可行性研究, 数据流图, 设计文档) from the live Backend/Frontend/Desktop code, not stale README or Docs. Use when the user asks for 软工作业, GB/T 8567 可行性研究, 数据流图/DFD, 系统设计说明书, or any course artifact about Flowly or the current repo.
---

# 按当前代码写软工作业

README、`Docs/`、旧图都可能落后于代码。作业内容以 **正在运行的源码** 为准。

## 工作顺序

1. 读代码，不读宣传稿。至少核对：`INSTALLED_APPS`、关键 models、执行器、网关/RAG、前端入口、桌面端。
2. 列出真实模块边界和数据对象，再动笔。
3. 文档里写「系统现在做什么」，不写「计划做但代码里没有」的能力。
4. 封面学号/姓名留填空，不要编造。

## 代码优先核对清单

| 要写的内容 | 去哪核对 |
|-----------|---------|
| 有哪些子系统 | `INSTALLED_APPS`、前端路由、Desktop 主进程 |
| 用户/会话/工作流 | `NLSession`、Workflow 模型、执行记录 |
| 怎么跑起来 | Django + Vue 端口、Celery/Redis、Electron |
| 外部系统 | ProviderRegistry、向量库、Webhook/SMTP、桌面训练 |
| 节点种类 | `node_types` 声明，不要按 README 猜个数 |
| 垂直业务（短剧/苗绣/CUMCM/YOLO） | 是语创 enrichment / 节点模板，不是 0 层加工 |

## 可行性研究（GB/T 8567 风格）

用 `python-docx` 写 `.docx`。本机 Word COM 可能 `TYPE_E_CANTLOADLIBRARY`，不要把 COM 当默认路径。

报告要有：现状与目标、技术/经济/操作可行性、候选方案比较、风险、结论。表格用代码里的真实组件名。

## 数据流图分层（作业口径）

- **顶层**：系统 = 加工 0，只连外部实体。
- **0 层**：1.0 认证、2.0 语创、3.0 工作流维护、4.0 执行、5.0 智能服务。
- **1 层**：拆 2.0 和 4.0。用户在语创 1 层只与 2.1 对话；确认经会话进 2.6。
- 短剧 / 苗绣 / CUMCM / YOLO 模板挂在 **2.3**，不要升成 0 层加工。

画图用本地 Visio 时，读并遵循 [visio-dfd](../visio-dfd/SKILL.md)。

## 禁止

- 把过期 README 当架构真相。
- 为了图好看而合并/删掉代码里真实存在的存储或外部实体。
- 未导出、未目视检查就宣称图已完成。
