# NL 创建全面智能化设计

日期：2026-07-16  
状态：已批准（用户授权按经验落地）

## 目标

消除「死模板成图 / 关键词硬路由 / 规则编辑冒充智能」；NL 创建与编辑完善以 AI 为主路径，模板仅作离线兜底并显式标注。

## 决策

- 方案：Agent 闭环渐进（P0→P1→P2）
- 模板 fallback：默认关闭；仅无 LLM 或 `NL_WORKFLOW_USE_TEMPLATES=true` 时可用，并标记 `offline_template`
- 关键词意图：保留为弱兜底；对话/编辑主路径用 LLM 结构化意图与动作规划

## P0（本次必达）

1. 生成失败 → 带错误信息的修图重试，不套领域整图模板
2. `NL_WORKFLOW_TEMPLATE_FALLBACK` 默认 `false`
3. 服务层 `resolve_intent`：LLM 意图 + 关键词兜底
4. 生成 prompt 注入相似模板摘要（RAG/DB 检索，作参考非成图）
5. `wire_*` 仅补缺省，不覆盖已有 provider

## P1（本次一并落地核心）

1. `/optimize` + 「优化」：结构优化 + LLM 完善 pass
2. 编辑器动作：AI 规划 JSON → 调用工具（加语言链 / 设 URL / 配置检查 / 布局 / 修改）
3. 规则动作降级为 tool 实现，不再抢在 AI 之前硬匹配（AI 失败时才兜底）

## P2（已落地）

- 本地 ReAct 工具检索上下文注入生成 prompt（`agent_context.gather_generation_context`，默认开启 `NL_WORKFLOW_USE_AGENT_CONTEXT`）
- 生成后工具校验元数据（`_agent_validation`），硬错误参与重试
- Celery 异步生成：`POST /sessions/` 传 `async=true` 或 `NL_WORKFLOW_ASYNC_GENERATE=true` → `202` + `task_id`
- 轮询：`GET /sessions/<uuid>/task/`
- 长会话摘要：`conversation_summary` + `compress_messages_for_generation`（阈值 `NL_CHAT_SUMMARY_THRESHOLD`）
- ReAct AgentExecutor 默认使用本地 prompt，避免 `hub.pull` 网络依赖（`NL_WORKFLOW_USE_HUB_REACT_PROMPT` 可显式开启）

## P3（可选后续）

- 全量 ReAct AgentExecutor 作为主生成路径（当前以工具检索增强 LLM 生成为主）
- 前端默认开启 async 生成开关 UI

## 验收

- 同需求多次生成结构可不相同（LLM 路径）
- 无关键词也能识别修改/优化并改画布
- LLM 坏 JSON 会重试修图，不会静默变成固定 17 节点视频模板
- 离线模板响应含 `_intelligence_note` 说明非智能兜底
