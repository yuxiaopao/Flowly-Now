# 工作流增强 Phase 2 — 发现与决策记录

## 命名不一致根因分析

### `web_scraper_node` 后缀问题

```
constants.py:              WEB_SCRAPER_NODE = "web_scraper_node"
langchain_service.py:       'web_scraper_node': self.run_web_scraper_node
Editor.vue nodeTypes:       type: 'web_scraper_node'
models.py NODE_TYPE_CHOICES: 'web_scraper'           ← 不一致！
seed_domain_templates.py:   "type": "webScraper"      ← camelCase！
```

**决策**: 统一为 `web_scraper`（去掉 `_node` 后缀），与 `file_reader`/`file_writer` 保持风格一致。

### 种子模板 camelCase 问题

`seed_domain_templates.py` 中的 node type:
- `"type": "imageGeneration"` → 改为 `"type": "image_generation"`
- `"type": "videoGeneration"` → 改为 `"type": "video_generation"`
- `"type": "webScraper"` → 改为 `"type": "web_scraper"`
- `"type": "documentLoader"` → 改为 `"type": "document_loader"`
- `"type": "csvTransform"` → 改为 `"type": "csv_transform"`

所有 6 个模板都需要修复。

### 表单字段与 Handler 对齐问题

前端 25 个 `*Config.vue` 表单字段普遍比后端 handler 读取的字段多。
原因：表单设计时参考了行业最佳实践字段，但 handler 实现时只做了最小化实现。

**决策**: 
- 后端补齐缺失字段（让 handler 真正读取配置）
- 前端表单字段保持不变（作为未来扩展预留）

## Handler 实现质量评估

| Handler | 质量评分 | 主要问题 |
|---------|---------|---------|
| `run_image_generation_node` | 7/10 | 有多 provider 分支，但缺少异步 polling |
| `run_video_generation_node` | 4/10 | 调用了 Replicate 但无轮询，返回 prediction_id 就结束 |
| `run_model_training_node` | 2/10 | 生成训练脚本字符串但不执行，直接 save 假数据 |
| `run_retriever_node` | 5/10 | Chroma 硬编码实例化，无持久化配置 |
| `run_agent_node` | 3/10 | 只调用了 llm，没有真正的工具调用循环 |
| `run_file_writer_node` | 6/10 | 相对完整，但无目录创建逻辑 |
| `run_web_scraper_node` | 5/10 | 有基础实现，缺登录/代理/Cookie 支持 |
| `run_csv_transform_node` | 8/10 | 相对完整（但 `localData` 字段与 `schema` 字段名冲突） |

## 前端 Node Type Registry 对齐情况

Editor.vue 中注册了 25 个领域节点，但部分节点的 type key 与 `constants.py` 不完全一致：

需要核实具体差异：
- `image_generation` ✅
- `video_generation` ✅  
- `web_scraper_node` ❌（应为 `web_scraper`）

## 凭证管理现状

`langchain_service.py` 中 `self._get_credential()` 方法体未知。需要确认：
1. 是否真的实现了？
2. 凭证存在哪个模型？（`APICredential` 已存在）
3. 读取逻辑是否安全？

## 决策记录

| 日期 | 决策 | 理由 |
|------|------|------|
| 2026-05-18 | Node type 统一用 snake_case | 后端一致、Python 惯例、前后端 JSON 标准 |
| 2026-05-18 | 前端表单字段保留，后端补齐 | 表单是用户输入契约，不应降级 |
| 2026-05-18 | ChromaDB 用文件持久化 | 避免内存实例在重启后丢失 |
| 2026-05-18 | Replicate 轮询 30s 间隔，最多 60 次 | 平衡 API 限制与用户体验 |
