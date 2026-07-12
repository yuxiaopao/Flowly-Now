# 训练模型完整业务闭环专题

> 目标：围绕当前 Flowly 代码现状，设计一套真正可落地的“训练模型工作流”业务闭环。  
> 这个专题不是单点接口说明，而是从数据、资源、训练、评估、发布、执行、租户治理、成本观测一直打到端到端流程。

## 文件清单
- `01-training-model-workflow-blueprint.md`：训练模型完整业务逻辑总方案、角色、流程、数据模型、状态机、页面、接口、风险与落地顺序
- `02-yolo-training-to-deploy-blueprint.md`：YOLO 训练 + 权重保存 + 网站生成 + 左导航项目入口 + CodeGraph 解析的专项闭环方案
- `03-yolo-node-config-and-api-contract.md`：YOLO 训练节点、网站生成节点、项目创建节点、CodeGraph 节点的配置结构、REST API、WebSocket 消息与上下文契约规范
- `04-yolo-frontend-realtime-dashboard.md`：YOLO 训练实时看板、图表区、动画区、状态机、断线重连、异常交互与后续动作区的前端设计规范
- `05-yolo-implementation-rollout-plan.md`：YOLO 训练后端、前端、网站生成、项目化、CodeGraph 的分阶段实施顺序、修改模块、验收标准与风险清单

## 实施进度（2026-06-12 起）

**新一轮 Desktop 站点工厂（QA / Preview / CLIP / Project Agent）请以独立目录为准：**

→ [`Docs/desktop-ml-site-factory/README.md`](../../desktop-ml-site-factory/README.md)  
→ 进度看板：[`PROGRESS.md`](../../desktop-ml-site-factory/PROGRESS.md)

本目录历史蓝图仍作参考；YOLO 去重整合已完成部分见 `desktop-ml-site-factory/00-current-state.md`。

## 适用范围
这套方案主要覆盖：
- 监督微调 / 分类训练 / 轻量模型训练
- 基于当前 `training`、`evaluation`、`datasets`、`workflows`、`rag`、`gateway`、`tenants` 代码的可演进落地方向
- 团队/租户场景下的训练任务治理

## 当前代码基础结论
从现有代码看，项目并不是完全没有训练能力，而是：

- 已有 `training` app，存在 `TrainingJob` 与训练数据集模型
- `workflows` 执行器里已经有 `model_training`、`model_evaluation` 节点
- `evaluation` app 已有 `EvaluationJob`
- `datasets`、`rag`、`gateway`、`execution` 已分别具备部分底层能力

但问题同样明显：

- 训练域和通用数据集域是两套平行数据模型
- 训练产物还没有升级成正式“模型资产”
- 训练 → 评估 → 发布 → 部署 → 推理 还没有闭环
- tenant / permission / cost / observability 还没真正打通到训练链路

所以这个专题的重点，不是再造一个“训练按钮”，而是把训练模型变成平台级闭环能力。
