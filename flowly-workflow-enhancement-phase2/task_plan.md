# 工作流增强 Phase 2：从表层到深度实现

## 目标

将 Phase 1 搭建的 25 个领域节点从"可渲染但不可执行"的表层状态，升级为**真正可运行、数据流打通、错误可恢复**的生产就绪状态。

---

## 问题分级

### P0 — 阻断性问题（必须先修，否则整个链路不通）

| # | 问题 | 根因 | 涉及文件 |
|---|------|------|---------|
| P0-1 | node type 命名不一致：constants 用 `web_scraper_node`，models 用 `web_scraper`，seed 模板用 `webScraper` | 三处各写各的 | `constants.py`, `models.py`, `seed_domain_templates.py`, `langchain_service.py` |
| P0-2 | 种子模板 type 字段用 camelCase，前端/后端全部用 snake_case | 模板导入后端会 404 | `seed_domain_templates.py`, `Editor.vue` |
| P0-3 | 前端表单字段 > 后端 handler 字段，大量字段有定义无执行 | 表单设计过度超前 | 25 个 `*Config.vue` vs `langchain_service.py` |

### P1 — 功能就绪问题（核心功能可用）

| # | 问题 | 影响 |
|---|------|------|
| P1-1 | 凭证管理缺失（`self._get_credential()` 方法体不明） | 所有外部 API 调用会失败 |
| P1-2 | 视频/音频生成返回 `prediction_id` 后无轮询 | 用户看到"处理中"然后卡死 |
| P1-3 | WebSocket 实时执行反馈缺失 | 用户不知道节点在跑什么 |
| P1-4 | ChromaDB/Pinecone 连接配置缺失 | RAG 管道无法真实工作 |

### P2 — 生产就绪问题（工程质量）

| # | 问题 |
|---|------|
| P2-1 | Model training 节点是假数据（字符串拼接 + 打印），无真实训练 |
| P2-2 | 每个 handler 的 except 块只有 `return {'success': False, 'error': str(e)}` |
| P2-3 | 无节点执行日志（输入/输出/耗时/token 消耗） |
| P2-4 | 无重试机制（`max_retries` 配置存在但未使用） |

---

## 执行计划

### Phase 1: 修复 P0 阻断性问题

- [ ] **P0-1**: 统一 node type 命名 → 全部 snake_case，去掉 `_node` 后缀
- [ ] **P0-2**: 修复种子模板 type 字段 → camelCase → snake_case
- [ ] **P0-3**: 对齐前端表单与后端 handler 字段 → 裁剪多余字段，补缺失字段

### Phase 2: P1 功能就绪

- [ ] **P1-1**: 实现 `APICredential` 凭证管理（模型 + API + handler 读取）
- [ ] **P1-2**: 添加异步任务轮询（Replicate 视频/音频 polling）
- [ ] **P1-3**: WebSocket 实时执行反馈
- [ ] **P1-4**: ChromaDB 持久化配置 + Pinecone v3 API 更新

### Phase 3: P2 工程质量

- [ ] **P2-1**: 真实模型训练节点（实际调用 PyTorch/Trainer）
- [ ] **P2-2**: 每个 handler 补全重试逻辑
- [ ] **P2-3**: 节点执行日志（`NodeExecution` 记录真实输入输出）
- [ ] **P2-4**: 执行缓存（基于 node config hash 避免重复执行）

### Phase 4: P3 体验优化

- [ ] **P3-1**: 模板缩略图生成
- [ ] **P3-2**: 模板评分/评论系统
- [ ] **P3-3**: Agent 节点真实工具调用（不只是 prompt 拼接）

---

## 命名规范（约定）

所有 node type 必须统一为 **snake_case**，禁止后缀：

```
✅ image_generation    ✅ web_scraper    ✅ csv_transform
❌ imageGeneration     ❌ web_scraper_node    ❌ csvTransform
```

---

## 错误记录

| 日期 | 错误 | 尝试 | 结果 |
|------|------|------|------|
| 2026-05-18 | views.py 两个同名 WorkflowTemplateViewSet | 重命名为 PublicWorkflowTemplateViewSet | ✅ 已修复 |
| 2026-05-18 | models.py NODE_TYPE_CHOICES 缺少 25 个新类型 | 补全全部 40 个类型 | ✅ 已修复 |
