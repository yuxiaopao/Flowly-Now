# 00 — 产品决策锁稿

> **状态**：已定稿（2026-06-12）  
> 变更须写入 [`PROGRESS.md`](PROGRESS.md) 决策变更日志。

---

## 决策 1：CLIP 检索站产品形态

**结论**：**交互演示站为主 + API/导出 Tab 为辅**（双层，同一站点）。

| 层级 | 内容 |
|------|------|
| 主路径 | Tab1 文本搜图、Tab2 以图搜图、Tab3 图库浏览 |
| 进阶 | Tab4 API 文档、cURL、下载 `index/` + `metadata.json` |
| 模板 | 独立 `clip_retrieval` scaffold，**不与** YOLO 检测站共用 Vue 页面 |
| 工作流 | `clip_retrieval` 训练/索引节点 → profiler → website_generator(template=clip_retrieval) → QA → Preview |

详细 UI/API：[`references/clip-retrieval-site-spec.md`](references/clip-retrieval-site-spec.md)

**已定稿** ✅

---

## 决策 2：生成站数据库

| 存储 | 用途 |
|------|------|
| **Flowly 平台 MySQL** | `GeneratedSite`、QA 报告、Agent 对话、执行记录、CodeGraph 绑定 |
| **生成站目录内 SQLite（默认）** | 推理历史、站点设置、用户反馈（固定 schema，AI 不随意改表） |
| **生成站 MySQL（可选，高级）** | 与 SQLite 同 schema；Wizard Step4 可选；密码经 Desktop 环境变量注入 |

理由：零安装 MySQL，Desktop/学者友好；平台仍用 MySQL 做项目治理；高级用户可切换 MySQL。

**已定稿** ✅（2026-06-30 扩展：MySQL 可选）

---

## 决策 3：QA 标准与阈值

**结论**：**全面 QA（L1–L4）** + **绿/黄/红** + **双 Profile**。

| 层级 | 内容 | 失败是否阻断 |
|------|------|--------------|
| L1 | 结构、依赖、权重、SQLite 可写、端口 | 阻断 |
| L2 | Flask `/health` + 任务 API 冒烟 | 阻断 |
| L3 | Playwright 主路径（上传/输入→结果展示） | 阻断 |
| L4 | 验证集指标（mAP/Acc/R@K） | 按档位 + Profile |

数值阈值：[`references/qa-threshold-matrix.md`](references/qa-threshold-matrix.md)

| Profile | 黄灯 | 红灯 | 发布/对外 |
|---------|------|------|-----------|
| `default`（小白默认） | 警告 | 阻断预览对外 | 仅绿灯 |
| `research`（学者模板） | 允许预览+导出报告 | 阻断一键部署 | 黄灯可预览 |

**已定稿** ✅

---

## 决策 4：预览与运行时

**结论**：**Flowly Desktop 本地起服务**（与本地权重一致）。

- 预览 URL：`http://127.0.0.1:{port}`，节点内 iframe  
- 权限：首次 `environment_provision` 一次性申请目录读写 + 子进程 + localhost  
- 云端 sandbox：**非 M1–M3 范围**  

**已定稿** ✅

---

## 决策 5：专属 Agent 边界

**结论**：**允许改前端 + 后端推理封装**；**禁止**删 scaffold 核心 infer 入口；**任意改码后强制重跑 site_qa（L2–L4）**。

| 允许 | 禁止/需确认 |
|------|-------------|
| Vue 文案、布局、主题 | 删除 `app.py` 权重加载器 |
| Flask 阈值、后处理、路由封装 | 未授权 shell / 任意外网 |
| SQLite 查询与展示逻辑 | 直接改 `.pt` 权重（应回训练节点） |

状态机：[`references/state-machines.md`](references/state-machines.md)

**已定稿** ✅

---

## 决策 6：训练 UI 形态

**结论**：**多节点 + 多模板 + 分步 Wizard**（非单一 mega 表单）。

- YOLO / CLIP / Transformers 各模板，共用 Wizard 壳组件  
- 步骤越细越好（数据 → 权重 → 超参 → 环境 → 输出）  

实现阶段：M2 统一 Wizard 壳；M4 CLIP 节点。

**已定稿** ✅

---

## 决策 7：CLIP 任务拆分

**结论**：**多节点**，数据集多素材类型。

| 节点 | 任务 |
|------|------|
| `clip_classification` | 图像分类 / 零样本分类 |
| `clip_retrieval` | 图文检索 / 以图搜图索引 |
| （可选后续）`clip_detection` | open-vocab 检测，与 YOLO 分 executor |

数据集共用 `dataset_upload`，`format` 区分：`yolo` | `image_folder` | `image_text_pairs` | …

**已定稿** ✅

---

## 变更流程

1. 提出变更 + 理由  
2. 更新本文对应节 + `references/` 受影响文件  
3. 写入 `PROGRESS.md` 决策变更日志  
4. 重新过文档验收清单（[`README.md`](README.md) 第七节）  
