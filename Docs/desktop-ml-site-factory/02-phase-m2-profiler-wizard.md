# M2 — Project Profiler + 建站向导

> **优先级**：P1（M1 完成后）  
> **目标**：建站前自动分析类别/场景；用户分步填写资料；AI 只填固定 scaffold 槽位。  
> **状态**：✅ 核心已实现（2026-06-18）

---

## 一、范围

- 新节点 `project_profiler`
- `WebsiteGeneratorConfig` / `WebsiteGeneratorNode` **分步 Wizard**
- `website_generator` runner 输入改为 **profiler JSON + wizard 表单**
- 检测站 / 分类站 template 分支（检索站 M4 接同一 wizard 壳）

---

## 二、任务清单

### 2.1 `project_profiler`

- [x] **M2.1** 节点注册 + `run_project_profiler_node()`
- [x] **M2.2** 输入：`class_names`, `model_path`, `website_type`, `sample_images[]?`（可选）
- [x] **M2.3** 输出 `profile.json`：`domain`, `scenario`, `ui_tone`, `copy_hints[]`, `risk_notes[]`, `recommended_template`
- [x] **M2.4** 实现：规则（类名关键词）+ 可选 LLM 补全文案（不生成代码）
- [x] **M2.5** 前端 `ProjectProfilerNode.vue`：展示分析卡片

### 2.2 建站 Wizard

- [x] **M2.6** 共用组件 `TrainingSiteWizard.vue`（步骤条）
- [x] **M2.7** Step1 场景确认（读 profiler，可编辑）
- [x] **M2.8** Step2 品牌：站点名、Logo URL、主色、联系方式
- [x] **M2.9** Step3 合规/说明：免责声明、隐私、使用场景描述
- [x] **M2.10** Step4 输出：outputDir、port、qaProfile
- [x] **M2.11** 上游自动填充：YOLO/CLIP 节点 `best_weight_path`, `class_names`

### 2.3 生成器改造

- [x] **M2.12** `get_generator()` 增加 `profile` + `wizard` context
- [x] **M2.13** Vue 页：标题/副标题/类名展示从 profile 注入（detection 模板）
- [x] **M2.14** 禁止 generator 新建任意表 — 仅 SQLite 固定 schema

### 2.4 模板与工作流

- [x] **M2.15** 更新 `yolo-detection-project`：`train → profiler → website_generator → M1 链`
- [x] **M2.16** 文档更新 `node-io-contracts.md` profiler 节

---

## 三、Profiler 输出契约（摘要）

```json
{
  "domain": "工业安全",
  "scenario": "安全帽佩戴检测",
  "ui_tone": "industrial_warning",
  "copy_hints": ["上传现场照片", "红框标注未佩戴区域"],
  "risk_notes": ["低照度场景误检率可能升高"],
  "recommended_template": "detection",
  "class_display_names": { "helmet": "安全帽", "no_helmet": "未佩戴" }
}
```

---

## 四、完成标准

1. 安全帽类 `class_names` 输入 → profiler 输出工业场景文案 ✅  
2. Wizard 四步可走通，缺少必填项不能执行建站 ✅（`wizardCompleted` + 后端校验）  
3. 生成站首页标题/说明与 wizard 一致 ✅  

**验证**：`python Backend/scripts/m2_profiler_smoke_test.py`

---

## 五、依赖

- M1 SQLite scaffold 与 QA 链已通  

---

## 六、后续优化（非阻断）

- [x] classification 生成器同步 profile/wizard 注入（2026-06-18）
- Wizard 与 PropertyPanel 分离「高级选项」折叠
- LLM 润色默认关闭，租户级开关
