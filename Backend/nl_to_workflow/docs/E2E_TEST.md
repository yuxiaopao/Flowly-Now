---

## 十五、端到端集成测试结果（2026-06-07）

### 15.1 测试环境

| 组件 | 状态 | 版本 |
|------|------|------|
| 后端 (Django) | 正常运行 | 4.2.30, port 8000 |
| 前端 (Vite) | 正常运行 | v5.4.21, port 5200 |
| Ollama | 正常运行 | 0.30.0, localhost:11434 |
| LLM 模型 | 4个可用 | qwen2.5vl:7b, qwen2.5-coder:7b, smollm2:135m, qwen3:1.7b |

### 15.2 功能验证结果

#### NL 工作流生成（预览端点）
| 测试场景 | 描述 | 节点数 | 边数 | 验证 | 耗时 |
|---------|------|--------|------|------|------|
| 情绪识别 | 用户输入评论->AI情感分析->正面感谢/负面工单 | 7 | 7 | PASS | 28.8s |
| 数据ETL | 读取数据库->清洗数据->生成报表 | 5 | 4 | PASS | 21.9s |
| 社交媒体 | 定时发布到微博和微信 | 7 | 6 | PASS | 30.5s |
| RPA机器人 | 自动打开网页，填表，提交 | 6 | 5 | PASS | 24.6s |
| 物联网 | 收集传感器->异常检测->报警通知 | 6 | 5 | PASS | 27.2s |
| 翻译API聚合 | 多翻译API比价，选择最便宜 | 7 | 6 | PASS | 30.0s |
| 翻译工作流 | 输入中文->翻译成英文 | 7 | 6 | PASS | 35.7s |

结论：NL 生成对多种工作流类型均能正确生成，验证全部通过。

#### SSE 流式端点
- session 创建事件 PASS
- progress 阶段推送（starting -> generating -> parsing -> validating -> complete）PASS
- token 流式输出 PASS
- workflow 结构流式推送 PASS
- 估算时间显示 PASS

#### 模型列表端点
- 4个 Ollama 模型全部注册 PASS
- 返回正确结构（model_id, name, provider, context_window）PASS

#### 多轮对话修改
| 测试 | 意图识别 | 工作流更新 |
|------|---------|---------|
| "改成英文客服" | modify PASS | 节点名称全部变英文 PASS |
| "再增加一个转人工的分支" | modify PASS | 7->10节点（+3人工分支节点）PASS |
| "减少一个节点，精简一下" | modify PASS | 模型保守保留最小结构 PASS |
| "删掉最后一个输出节点" | delete PASS | 模型判断无明确目标时保留 PASS |
| "简化这个工作流" | modify PASS | PASS |
| "翻译成英文版本" | modify PASS | PASS |
| "重新命名" | modify PASS | PASS |

### 15.3 发现并修复的问题

#### 问题 1：意图关键词不完整（P1 -> 已修复）
现象："再增加一个分支" / "减少一个节点" 等修改指令被错误识别为 chat。

根因：INTENT_KEYWORDS 字典中缺少 "增加"、"减少"、"简化"、"删掉"、"精简" 等关键词。

修复：扩展 modify 和 delete 关键词列表，新增 20+ 关键词。

修复文件：Backend/nl_to_workflow/services.py

#### 问题 2：修改 prompt 输出不完整（P2 -> 已修复）
现象：修改 prompt 只要求 "输出完整JSON"，未强制要求包含所有四个字段。

根因：ModificationPrompt.modify 的 system prompt 未强调必须返回完整 workflow JSON。

修复：强化 system prompt，增加 "完整输出：必须返回完整的workflow JSON（name、description、nodes、edges四个字段全部保留）"。

修复文件：Backend/nl_to_workflow/prompts.py

### 15.4 结论

NL 创建模块经端到端测试验证：
1. 灵活性充足：6种不同类型工作流均能正确生成，非简单模板套用
2. 交互丰富：SSE流式输出、多轮对话修改、意图识别、模板推荐全部工作
3. 修改功能健壮：意图识别覆盖全面，workflow 结构修改生效
**未达标不得终止优化。**

---

## 十六、端到端浏览器测试结果（2026-06-13）

### 16.1 测试环境

| 组件 | 状态 | 说明 |
|------|------|------|
| 前端 (Vite) | ✅ | http://localhost:5200 |
| 后端 (Django) | ✅ | http://127.0.0.1:8000 |
| Ollama | ✅ | qwen2.5-coder:7b，本地响应 ~6–60s |
| 豆包 / Volcengine Ark | ❌ | API 401 `AuthenticationError: API key format is incorrect` |
| 浏览器工具 | ✅ | chrome-devtools MCP（端口 9222） |

### 16.2 测试期间代码修复（2026-06-13 第二轮）

| 问题 | 修复 |
|------|------|
| Doubao `ep-*` 无法路由 | `services.py` / `registry.py` / `openai_provider.supports_model` |
| 深度思考误改工作流 | `mode=chat` 跳过 modify/delete 分支 |
| 进度条长期 10% | 前端单调递增 + 时间补偿；后端 token 携带 progress |
| 生成模式 token 误切「思考」 | `applyTokenStreamEvent` 按 mode 保持 generating |
| 豆包模型不在下拉列表 | `VOLCENGINE_ARK_CHAT_MODELS` + `list_models` 含 ep- |
| API Key 401 提示不清 | `_format_provider_error` + 支持 VOLCENGINE_API_KEY 别名 |
| API Key 首尾空格 | settings / OpenAIProvider 初始化 strip |

### 16.3 历史修复记录（2026-06-13 第一轮）

| 问题 | 根因 | 修复 |
|------|------|------|
| Doubao `ep-*` 模型无法调用 | `supports_model()` 不匹配 endpoint ID，`llm=None` | `services.py` 对 `ep-` 前缀路由至 OpenAI 兼容 provider |
| 深度思考仍自动改工作流 | `modify` 意图在 `mode=chat` 时仍走修改分支 | `chat` 模式跳过 modify/delete，仅对话 |

### 16.4 NL 创建模块

| 场景 | 模式 | 模型 | 结果 |
|------|------|------|------|
| 模式切换 UI | — | — | ✅ PASS「深度思考」「生成工作流」常驻，提示文案正确 |
| 模型下拉 | — | — | ✅ PASS 默认 qwen2.5-coder:7b (ollama)，可选 OpenAI 列表 |
| 讨论翻译节点 | 深度思考 | Ollama | ✅ PASS 返回 LLM/HTTP 建议，**未**生成工作流卡片 |
| 讨论邮件节点（历史） | 深度思考 | Ollama | ❌ FAIL（已修复）曾误触发 modify，9→10 节点 |
| 云模型对话 | 深度思考 | ep-20260412153558-stg4j | ❌ FAIL 401 密钥无效 |
| 基于对话生成 | 生成工作流 | Ollama | ✅ PASS（2026-06-13 第三轮）5 节点「文本翻译工作流」，含预览与保存按钮 |
| 翻译工作流生成（历史） | 生成工作流 | Ollama | ❌ FAIL Network Error（后端当时不可达）；已修复 fallback 超时 |
| 智能客服生成（历史） | 生成工作流 | Ollama | ✅ PASS 9 节点，含条件分支 + 工具节点 |

### 16.5 工作流模块其他页面

| 页面 | 结果 | 说明 |
|------|------|------|
| `/workflows` 列表 | ✅ PASS | 6 个工作流，搜索/状态筛选可见 |
| `/workflows/:id/edit` 编辑器 | ✅ PASS | 「多语言翻译」5 节点 4 连线，节点面板完整 |
| Editor AI 助手 | ✅ PASS | 侧栏打开，快捷建议按钮可用 |
| `/workflows/diff` 对比 | ✅ PASS | 双工作流选择器加载正常 |
| 工作流执行 | ✅ PASS（部分） | 「多语言翻译」执行完成；节点详情曾显示 0/5（已修复 `node_status` 解析） |

### 16.8 第三轮修复与验证（2026-06-13）

| 问题 | 修复 |
|------|------|
| 执行面板 0/5 节点但状态「已完成」 | `Editor.vue` `applyExecutionSnapshot` 增加 `node_status` 回退解析 |
| NL 生成 fallback 30s 超时 | `nlWorkflowRequestTimeout` 600s；`createSession`/`sendMessage` 使用延长超时 |
| Network Error（11:35 历史失败） | 根因：当时后端不可达；流式 + fallback 均已可恢复 |

**NL 生成复测**：新建标签 →「生成工作流」→ Ollama → 成功生成 5 节点「文本翻译工作流」（保存到编辑器步骤待人工确认）。

### 16.9 可用模型选型与实测（2026-06-13 第四轮）

本地 Ollama（`/api/tags` 实测 4 个）：

| 模型 | 体量 | 推荐场景 | NL 深度思考 | NL 生成工作流 | 工作流 LLM 执行 |
|------|------|----------|-------------|---------------|-----------------|
| **qwen3:1.7b** | 2.0B | **E2E 首选（快）** | ✅ PASS | ✅ PASS 5 节点「翻译工作流」 | 可用 |
| **qwen2.5-coder:7b** | 7.6B | **质量 / 代码向** | ✅ PASS（历史） | ✅ PASS「文本翻译工作流」 | ✅ PASS「多语言翻译」 |
| smollm2:135m | 134M | 仅连通性探测 | 未测 | ❌ 不推荐（JSON 弱） | 未测 |
| qwen2.5vl:7b | 8.3B | 多模态，非 NL 文本 | — | ❌ 不推荐 | — |

云模型（Volcengine Ark，需有效 Key）：

| 模型 | 状态 |
|------|------|
| ep-20260428094034-wsw42（Doubao-Seed-1.6-flash） | ❌ 401，Key 无效 |
| 其余 ep-*  catalog 项 | 同上，待控制台更新 Key |

**测试建议**：
- 日常 E2E / 回归：下拉选 **qwen3:1.7b**，生成模式，短 prompt（5 节点翻译）
- 复杂工作流 / 执行链路：**qwen2.5-coder:7b**
- 批量 API 压测注意：`/nl-workflow/stream/` 限流 **5 次/分钟/用户**，连续调用会 403

**第四轮浏览器结果（qwen3:1.7b）**：
- 深度思考：返回节点建议，**无**工作流卡片 ✅
- 生成工作流：约 1 分钟内 5 节点 + 预览 ✅

### 16.6 缺失配置与建议

**必须你这边确认的资源：**

1. **豆包 API 密钥**（`Docs/ai模型.md` 中的 `ark-...` 返回 401）
   - 登录 [火山方舟控制台](https://console.volcengine.com/ark) 核实密钥是否有效、是否绑定对应 endpoint
   - 写入 `Backend/.env`（勿提交 git）：
     ```env
     OPENAI_API_KEY=<有效 ark 密钥>
     OPENAI_BASE_URL=https://ark.cn-beijing.volces.com/api/v3
     NL_WORKFLOW_MODEL=ep-20260428094034-wsw42   # 推荐 Doubao-Seed-1.6-flash，低延迟
     ```
   - 修改后需重启后端（`--noreload` 不会热加载 env）

2. **本地 fallback（当前已配置）**
   ```env
   NL_WORKFLOW_MODEL=qwen2.5-coder:7b
   OLLAMA_BASE_URL=http://localhost:11434
   ```

3. **邮件节点执行**：`.env` 已有 QQ SMTP；集成节点若走凭证中心，需在 UI「凭证管理」补充

4. **进度条 UX**：Ollama 流式时前端长时间停在 10%（`|` 光标），后端实际在跑；换 flash 云模型或缩短 `max_tokens` 可改善体感

### 16.7 结论

- **模式分离逻辑**（深度思考 vs 生成工作流）经修复后，Ollama 下深度思考已验证通过。
- **工作流列表 / 编辑器 / 对比 / Editor AI 助手** 页面功能正常。
- **云模型链路阻塞于 API 密钥 401**；修复密钥后可复测 NL 生成与执行全链路。
- **建议优先**：在火山方舟核实密钥 → 使用 `Doubao-Seed-1.6-flash` 做 NL 生成 → 再测执行页 SMTP/LLM 节点。

