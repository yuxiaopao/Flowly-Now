# 06 - Template Domain 目标架构设计

> 文档目的：定义 Flowly 模板领域的唯一目标形态。  
> 这份文档不是继续列问题，而是直接回答：**模板系统最终应该长成什么样、为什么要这样设计、如何分阶段落地**。

---

## 一、先给结论

当前项目里的模板能力分散在三套系统中：

- `Backend/templates`
- `Backend/marketplace`
- `Backend/workflows` 内嵌模板

前端也存在并行消费：

- `Frontend/src/api/marketplace.js`
- `Frontend/src/api/workflow.js` 中模板相关接口
- `Frontend/src/stores/marketplace.js`
- `Frontend/src/views/marketplace/Index.vue`
- `Frontend/src/views/marketplace/Marketplace.vue`

这不是“模块多样化”，而是 **同一业务域被重复实现**。

## 最终目标
Flowly 只应该有一个模板领域：

### Template Domain = Workflow Asset Domain
模板不是单独的展示内容，也不是 marketplace 的附属表，更不是 workflow app 里的一个便捷功能。

模板应该被定义为：

> **经过标准化、可分发、可复用、可安装、可统计、可治理的工作流资产。**

所以模板域的最终定位是：

- 它的源头来自 workflow
- 它的用途是复用与分发
- 它的管理依赖 tenant / permission / resource policy
- 它的价值依赖 install / run / success / rating / cost 等运营数据

也就是说，模板系统不是“页面”，而是平台资产层。

---

## 二、模板域的核心设计原则

## 原则 1：模板必须只有一个真相源
不能再允许：
- marketplace 一套模板模型
- templates 一套模板模型
- workflows 一套模板模型

### 最终要求
后端只保留一个主模板聚合根（aggregate root）。

其他模块如果还需要模板能力：
- 只能引用这一套模板域
- 不能再各自维护自己的模板主表

---

## 原则 2：模板本质上是 workflow 的“资产化快照”
模板不等于 workflow 本体。

### 正确认知
- workflow 是可持续编辑、可版本演进的定义态实体
- template 是某个 workflow 在某个时点被标准化后产出的可复用资产

这意味着模板必须具备：
- 明确的来源 workflow / source
- 明确的版本信息
- 明确的依赖声明
- 明确的发布状态
- 明确的安装/运行统计

否则模板只是 workflow JSON 的复制品，不是资产。

---

## 原则 3：模板是带生命周期的业务对象
现在很多实现还停留在：
- `is_public`
- `is_published`
- `is_active`

这不够。

### 模板生命周期必须显式化
建议统一为：
- `draft`：草稿，作者自己编辑中
- `pending_review`：待审核，准备发布
- `published`：已发布，对目标可见范围开放
- `suspended`：已下线，暂时不可安装
- `archived`：已归档，不再参与推荐和运营

### 为什么必须这样做
因为后续功能都依赖状态驱动：
- 审核流程
- 推荐排序
- 模板修改权限
- 团队共享策略
- 历史版本保留
- 用户安装可见性

---

## 原则 4：模板必须有明确“来源”和“可见性”
模板不只是“谁创建的”，还要区分“它属于谁、给谁看、谁能装”。

### 建议拆成四个维度

#### 1. owner
创建者 / 维护者。

#### 2. tenant
资源边界归属。

#### 3. source_type
模板来源类型：
- `official`
- `team`
- `personal`
- `community`

#### 4. visibility
模板可见性：
- `private`
- `tenant`
- `public`
- `system`

### 为什么这么拆
因为：
- official 模板不应该和普通用户模板走完全同一运营逻辑
- 团队模板与社区模板的权限边界不同
- owner 只能表示“谁建的”，不能表示“谁能访问”

---

## 原则 5：模板必须声明依赖，而不是盲装
现在很多模板安装逻辑只做“创建副本”或“安装记录”，这不够。

真实模板要可用，往往依赖：
- 模型 provider
- API credential
- 工具配置
- 知识库/collection
- dataset
- variables

### 所以模板域必须内置依赖声明
至少支持：
- 所需 credentials
- 所需 providers/models
- 所需 tool integrations
- 所需 knowledge resources
- 所需 runtime variables

### 这样做的价值
模板安装前就能判断：
- 能不能安装
- 能不能直接运行
- 缺什么资源
- 要不要引导用户先补配置

这一步决定模板能不能真正闭环。

---

## 三、目标业务闭环

模板域最终应该支撑这条主链：

```text
Workflow 定义
→ 选择版本/快照
→ 生成 Template Draft
→ 完善元数据与依赖声明
→ 提交审核/发布
→ 对目标范围可见
→ 用户安装/创建副本
→ 依赖检查与首次运行引导
→ 收集使用/成功/评分/成本数据
→ 参与推荐、精选、运营排序
→ 持续版本演进或归档
```

这条闭环里每个环节都要有清晰模型支撑。

---

## 四、推荐的目标领域模型

这里不讨论 ORM 细节，先定义业务模型。

---

## 4.1 Template

### 它是什么
模板域的主聚合根，表示一个可分发的工作流资产。

### 建议字段

#### 标识与归属
- `id`
- `slug`
- `owner_id`
- `tenant_id`
- `source_type`
- `visibility`

#### 基本元数据
- `name`
- `summary`
- `description`
- `category_id`
- `tags`
- `thumbnail_url`
- `gallery_images`

#### 资产内容
- `workflow_snapshot`
- `variables_schema`
- `input_schema`
- `output_schema`
- `dependency_manifest`

#### 生命周期
- `status`
- `published_at`
- `suspended_at`
- `archived_at`
- `review_status`
- `review_notes`

#### 运营与质量
- `install_count`
- `run_count`
- `success_run_count`
- `rating_avg`
- `rating_count`
- `favorite_count`
- `view_count`
- `health_score`

#### 来源追踪
- `source_workflow_id`
- `source_workflow_version_id`
- `current_template_version_id`

#### 审计
- `created_at`
- `updated_at`
- `created_by`
- `updated_by`

### 关键说明
这里故意不建议继续使用当前各处混乱的字段组，如：
- `is_public`
- `is_published`
- `is_active`
- `access`

原因很简单：这些字段表达力不够，而且已经在不同模块里变成不同语义了。

---

## 4.2 TemplateVersion

### 它是什么
模板内容版本，表示模板资产在某次发布时的稳定快照。

### 为什么必须有
因为 workflow 本身会演进，模板也会演进，如果没有显式版本：
- 用户安装的是哪个内容说不清
- 模板更新后历史安装无法回溯
- 运营统计与版本质量无法关联

### 建议字段
- `id`
- `template_id`
- `version`
- `workflow_snapshot`
- `variables_schema`
- `dependency_manifest`
- `changelog`
- `created_at`
- `created_by`

### 关键规则
- 模板发布时必须绑定明确版本
- 用户安装行为必须记录安装的是哪个 `template_version`
- 运行统计后续要能追溯到版本质量

---

## 4.3 TemplateCategory

### 它是什么
模板分类，不只是展示标签，而是运营入口。

### 建议字段
- `id`
- `slug`
- `name`
- `description`
- `icon`
- `color`
- `parent_id`
- `sort_order`
- `is_active`
- `visibility_scope`

### 说明
目前 `templates`、`marketplace`、`workflows` 三套分类模型字段都不一致。

目标状态必须统一为：
- 支持排序
- 支持层级
- 支持主题色/icon
- 支持启用/停用

这样后续分类页、专题页、推荐位才有基础。

---

## 4.4 TemplateInstall

### 它是什么
用户安装模板、从模板生成 workflow 副本的记录。

### 建议字段
- `id`
- `template_id`
- `template_version_id`
- `installed_by`
- `tenant_id`
- `created_workflow_id`
- `dependency_check_result`
- `first_run_status`
- `installed_at`

### 为什么不能只是“装了就记一条”
模板安装真正关心的不是安装动作本身，而是：
- 安装后创建了什么 workflow
- 是否通过依赖检查
- 首次运行是否成功
- 用户是不是装了但跑不起来

这些直接决定模板质量评估。

---

## 4.5 TemplateReview / TemplateRating / TemplateFavorite

### 建议原则
不要把“评分”“评论”“收藏”继续做成彼此割裂的临时功能。

建议统一为：
- `TemplateRating`：评分
- `TemplateReview`：带文本评价的内容
- `TemplateFavorite`：收藏

### 这些数据的价值
不是为了页面热闹，而是为模板运营提供信号：
- 用户满意度
- 推荐排序
- 精选判断
- 低质量模板识别

---

## 4.6 TemplateDependencyManifest

这个可以是独立表，也可以先落在 JSON 结构里，但业务上必须被视为一等公民。

### 建议声明内容
- required credentials
- required provider/models
- required tools
- required knowledge bases
- required datasets
- required variables
- optional integrations

### 作用
它是“模板可用性”的前提，不是附属说明。

---

## 五、推荐的 API 目标形态

目标不是简单“把所有接口放一起”，而是把模板域做成稳定资源线。

---

## 5.1 资源入口建议
统一保留一个主入口：

- `/api/template-domain/templates/` 或继续沿用 `/api/v1/templates/`

关键不是路径名，而是：
- 只有一套模板资源
- 只有一套模板详情结构
- 只有一套模板安装行为

---

## 5.2 建议的模板 API 列表

### 查询类
- `GET /templates/`
- `GET /templates/{id}/`
- `GET /templates/featured/`
- `GET /templates/recommended/`
- `GET /templates/categories/`
- `GET /templates/{id}/stats/`

### 管理类
- `POST /templates/`
- `PATCH /templates/{id}/`
- `POST /templates/{id}/submit-review/`
- `POST /templates/{id}/publish/`
- `POST /templates/{id}/suspend/`
- `POST /templates/{id}/archive/`

### 使用类
- `POST /templates/{id}/preflight/`
- `POST /templates/{id}/install/`
- `POST /templates/{id}/create-workflow/`
- `POST /templates/{id}/favorite/`
- `POST /templates/{id}/rate/`
- `POST /templates/{id}/review/`

### 版本类
- `GET /templates/{id}/versions/`
- `POST /templates/{id}/versions/`
- `GET /templates/{id}/versions/{version_id}/`

### 运营类
- `GET /templates/analytics/`
- `POST /templates/{id}/feature/`
- `POST /templates/{id}/unfeature/`

---

## 5.3 安装前预检 API 必须单独存在
这是模板域很关键的一步。

### `POST /templates/{id}/preflight/`
返回：
- 是否缺 credential
- 是否缺 provider
- 是否缺 knowledge resource
- 是否变量不完整
- 是否当前 tenant 无权限使用某资源

### 为什么要独立出来
因为“安装”和“可运行”不是一回事。

模板市场如果只有 install 没有 preflight，用户体验会很差：
- 装得上
- 跑不动
- 不知道缺什么

这不是小问题，是模板域是否专业的问题。

---

## 六、推荐的前端目标结构

前端模板域当前问题很明显：
- store 混用两套来源
- 页面重复
- normalize 兼容逻辑过多
- UI 可能漂亮，但数据层并不干净

所以前端必须按模板域重建，而不是继续页面层补丁。

---

## 6.1 建议的前端模板域目录

```text
Frontend/src/domains/template/
  api/
    templateApi.js
  stores/
    templateStore.js
  types/
    template.ts
  composables/
    useTemplateInstall.ts
    useTemplatePreflight.ts
  components/
    TemplateCard.vue
    TemplateDetailDrawer.vue
    TemplateStats.vue
    TemplateInstallWizard.vue
    TemplateDependencyChecklist.vue
    TemplateReviewList.vue
  views/
    TemplateMarketplacePage.vue
    TemplateDetailPage.vue
    MyTemplatesPage.vue
    TemplateAdminPage.vue
```

### 目标
- 前端只保留一套模板 store
- 前端只保留一套模板 DTO
- marketplace 页面与“我的模板”页面共享同一套 domain 层

---

## 6.2 前端模板 DTO 建议

前端不要继续通过 `normalizeTemplate()` 去兼容多套历史字段。

### 目标 DTO 应该显式固定
例如：
- `id`
- `name`
- `summary`
- `description`
- `category`
- `tags`
- `thumbnailUrl`
- `sourceType`
- `visibility`
- `status`
- `installCount`
- `ratingAvg`
- `ratingCount`
- `favoriteCount`
- `isInstalled`
- `dependencyStatus`
- `author`
- `publishedAt`

### 核心原则
前端不再承担“猜这个模板到底来自 marketplace 还是 workflow”的责任。

这必须由后端模板域统一解决。

---

## 6.3 模板安装交互应该升级为向导
不要再停留在：
- 点击“安装”
- 成功/失败 toast

### 正确交互链路
1. 打开模板详情
2. 查看依赖清单
3. 做 preflight
4. 补凭证/补知识库/补变量
5. 选择目标 tenant/workspace
6. 创建 workflow 副本
7. 安装完成
8. 首次运行引导

这条链路会直接提高模板使用成功率。

---

## 七、模板域与其他业务域的边界

模板域不是孤岛，但也不能吞并所有东西。

---

## 7.1 与 Workflow Domain 的边界

### Workflow Domain 负责
- workflow 原始定义
- workflow 编辑与版本
- workflow 执行

### Template Domain 负责
- workflow 的资产化快照
- 模板发布、分发、安装、运营

### 边界规则
模板不直接替代 workflow；模板安装后应生成新的 workflow 实体。

---

## 7.2 与 Tenant / Access Domain 的边界

### Tenant / Access Domain 负责
- 谁能看模板
- 谁能管理模板
- 谁能安装模板
- 是否能访问模板依赖资源

### Template Domain 负责
- 描述模板对可见性和来源的业务语义

---

## 7.3 与 Resource Domain 的边界

### Resource Domain 负责
- 凭证
- 模型
- 工具
- 知识库
- 数据集

### Template Domain 负责
- 声明模板依赖哪些资源
- 在安装与预检时调用资源检查

### 关键原则
模板不能自己发明一套凭证模型。

---

## 7.4 与 Execution Domain 的边界

### Execution Domain 负责
- 实际运行结果
- 成功率
- cost
- logs
- node execution

### Template Domain 负责
- 聚合模板维度的运营指标
- 如 install_count、run_count、success_rate、health_score

这意味着模板域的大部分统计，其实来自执行域的汇总，而不是模板自己独立产生。

---

## 八、推荐的落地路径

这里给的是现实路径，不是理想化一步到位。

---

## 阶段 1：冻结继续扩散

### 目标
先阻止模板域继续裂。

### 需要做的事
1. 明确只允许新增一个模板主方向，不再新增第四套模板实现
2. 前端禁止继续混入新的模板字段兼容逻辑
3. 新接口不再新增 marketplace / workflow 双写行为
4. 把 `06-marketplace-field-migration-summary.md` 中的兼容层治理收完

### 完成标准
- 没有新的模板平行实现继续长出来
- 已有 marketplace 迁移继续在受控范围内推进

---

## 阶段 2：选定唯一模板真相源

这是最关键的决策点。

### 我的判断
**更适合作为未来真相源的是 `workflows` 方向，而不是 `marketplace` 方向。**

### 原因
1. `Backend/workflows/models.py` 中的模板结构更接近 workflow 资产，而不是纯展示内容
2. `workflows` 天然更靠近 workflow source
3. 后续模板依赖声明、版本、运行联动、执行统计接入，都更适合挂在 workflow 生态上
4. `marketplace` 当前更像一个“市场投影视图层”，不是好的主领域模型

### 但注意
这不表示 `workflows` 当前实现已经合格。
它只是比 `marketplace` 更接近未来方向。

### 所以正确动作不是“直接保留现状”，而是：
- 以 `workflows` 方向为基础
- 吸收 `templates` 与 `marketplace` 里已有但合理的能力
- 重建统一模板域

---

## 阶段 3：统一 DTO 与 API

### 目标
让前后端都只认识一套模板契约。

### 需要做的事
1. 定义统一 `TemplateDTO`
2. 定义统一 `TemplateDetailDTO`
3. 定义统一 `TemplateInstallDTO`
4. 定义统一 `TemplatePreflightDTO`
5. 前端模板 store 全量切到这套 DTO

### 完成标准
- 不再需要 marketplace normalize 兼容层去猜字段
- 页面不再关心模板来自哪套后端表

---

## 阶段 4：迁移安装与运营链路

### 目标
把 install/rate/review/favorite/analytics 统一到主模板域。

### 需要做的事
1. 迁移 install 记录
2. 迁移评分与收藏
3. 接 execution 聚合指标
4. 增加 template health / success rate 指标

---

## 阶段 5：下线旧实现

### 目标
删除多余模板系统。

### 需要做的事
1. 旧 app 改为只读兼容层或完全删除
2. 旧前端 API 删除
3. 旧页面合并
4. 清理兼容字段与 property alias

### 完成标准
- 系统里只有一个模板域
- 前后端都只走一条模板主线

---

## 九、关于 `06-marketplace-field-migration-summary.md` 的定位判断

这份文档很有价值，但要看清楚它的边界。

### 它解决了什么
- 收口 `Backend/marketplace` 内部字段命名兼容问题
- 让后续 marketplace 真字段 rename 具备准备条件
- 降低 marketplace 模块继续恶化的速度

### 它没有解决什么
- 没有解决“三套模板系统并存”这个根问题
- 没有决定最终模板真相源
- 没有统一前后端模板域
- 没有建立模板资产闭环

### 所以客观判断
这份文档对应的是：

> **局部迁移准备工作**，不是模板域架构的终局。

方向没错，但层级还不够高。

---

## 十、最终判断

模板域是你这个项目最值得继续投入的业务线之一，但前提是你要停止把它当成“市场页面功能”。

正确的战略方向应该是：

### 模板 = 工作流资产中心
它承接：
- workflow 复用
- 团队沉淀
- 资源依赖声明
- 首次运行成功率
- 质量评估
- 推荐运营
- 多租户共享

如果按这个方向做，模板域会成为整个 Flowly 平台最重要的增长引擎之一。

如果不按这个方向做，而是继续：
- marketplace 修一点
- workflow template 再加一点
- templates app 再补一点

那最后只会继续积累平行系统和兼容垃圾。

结论就一句：

**模板域下一步不是继续补页面，而是确立唯一资产模型，并围绕“发布—安装—运行—统计—推荐”这条闭环来重建。**
