# 07 - Tenant Access Policy 统一设计

> 文档目的：把 Flowly 当前散落的 owner / tenant / public / membership / role 判定，收敛成一套平台级访问规则。  
> 这份文档不是代码修复清单，而是后续所有多租户整改、权限实现、资源共享、审计设计的母规则。

---

## 一、先说结论

当前项目的多租户问题，不是“有几个 queryset 写得不够严谨”，而是：

### 现在系统里没有一套真正统一的访问语义
同一个项目里同时存在这些做法：

- `owner=self.request.user`
- `Q(owner=self.request.user) | Q(is_public=True)`
- `tenant_id__in=_get_accessible_tenant_ids(...)`
- `user.tenants.values_list(...)`
- `Q(owner=self.request.user) | Q(owner__isnull=True)`
- 某些接口在 `action()` 里临时做权限判断

这不是风格不统一，而是平台规则缺失。

## 最终目标
Flowly 必须建立一套统一的访问控制模型，满足下面这句话：

> **任意资源在任意动作下，系统都能明确回答：谁拥有它、它属于哪个 tenant、谁能看、谁能改、谁能执行、谁能共享。**

如果做不到这一点，后续这些能力都会持续产生漏洞：
- 团队模板
- 团队知识库
- 团队凭证
- Agent 协作
- 成本归属
- 审计追责
- 管理后台

---

## 二、当前代码反映出的真实问题

这不是抽象判断，是从现有实现直接能看到的问题。

### 1. membership 获取方式不统一
在 `Backend/workflows/views.py` 中，已经开始使用：
- `TenantMembership.objects.filter(user=user, is_active=True).values_list('tenant_id', flat=True)`

这是正确方向。

但在 `Backend/datasets/views.py` 里仍然存在：
- `user.tenants.values_list('tenant', flat=True)`

这说明不同模块对“用户属于哪些 tenant”没有统一来源。

### 2. owner-only 过滤仍然大量存在
例如：
- `Backend/agents/views.py` 的 `AgentViewSet.get_queryset()` 直接 `filter(owner=self.request.user)`
- `Backend/rag/views.py` 中 `VectorStore` / `DocumentCollection` 仍然主要按 owner 过滤
- `Backend/gateway/views.py` 中凭证读取仍然按 owner 为主

这意味着：
- tenant 字段即使存在，也不一定真正进入访问边界
- 后续团队共享与协作能力会继续失真

### 3. public 语义与 tenant 语义混杂
例如在 `Backend/workflows/views.py` 里可见：
- `Q(owner=user) | Q(tenant_id__in=tenant_ids) | Q(is_public=True, tenant__isnull=True)`

这本身不一定错，但系统里没有统一定义：
- `public` 到底是不是“全站可见”
- tenant 内部共享与 public 的优先级是什么
- tenant 资源能不能同时 public

### 4. 权限检查位置分散
当前项目里有些权限在：
- queryset
- permission class
- action 内部
- serializer save 阶段

这会导致一个严重问题：

> **你无法只看一层代码就判断资源是否安全。**

这对长期维护非常糟糕。

---

## 三、统一访问模型：五要素

后续所有资源访问都应基于这五个核心概念。

---

## 3.1 Principal
表示“谁在发起动作”。

### 可能主体
- 匿名用户
- 登录用户
- tenant 成员
- tenant 管理员
- tenant owner
- system admin / superuser
- 后台系统任务（未来可能）

### 结论
权限判断不能只看 `request.user` 是否登录，而必须进一步判断：
- 属于哪些 tenant
- 在 tenant 里的角色是什么
- 是否系统管理员

---

## 3.2 Resource Ownership
表示“资源归谁拥有”。

建议统一拆成两个维度：

### owner
表示创建者 / 责任人。

### tenant
表示资源边界归属。

### 核心规则
- `owner` 不是边界，只是归责与默认控制人
- `tenant` 才是多租户平台中的主边界

### 为什么必须这样定
因为很多资源未来会发生：
- 团队共享
- owner 离职 / 转移
- 团队接管
- 模板运营归属
- 成本归集

如果把 owner 当边界，平台能力永远做不稳。

---

## 3.3 Visibility
表示“谁能看见资源”。

建议统一为：
- `private`
- `tenant`
- `public`
- `system`

### 语义定义

#### `private`
仅 owner 和被显式授权者可见。

#### `tenant`
当前 tenant 内满足 membership 的用户可见。

#### `public`
所有登录用户或所有用户可见，必须按资源类型明确。

#### `system`
平台内建资源，通常由系统维护，可能对所有 tenant 可见但不可修改。

### 注意
不要继续用：
- 某处 `is_public`
- 某处 `access`
- 某处 `is_active`
- 某处 `owner__isnull=True`

去隐式表达 visibility。这种写法会越来越乱。

---

## 3.4 Role
表示用户在某个 tenant 中的身份。

结合 `Backend/tenants/models.py`，当前已有：
- `owner`
- `admin`
- `member`
- `viewer`

这个方向是对的，后续应把它作为统一角色基线。

### 建议能力语义

#### owner
- 管理 tenant
- 管理成员
- 管理账单
- 管理所有 tenant 资源
- 管理共享与删除

#### admin
- 管理大多数 tenant 资源
- 管理成员（受限）
- 发布模板 / 管理共享配置

#### member
- 创建与编辑自己有权限的资源
- 使用 tenant 共享资源
- 执行工作流

#### viewer
- 只读访问 tenant 授权范围内资源
- 不允许修改、执行高风险动作、管理共享

---

## 3.5 Action
表示“对资源做什么”。

后续权限规则不能只区分“读/写”，建议至少统一为：
- `list`
- `retrieve`
- `create`
- `update`
- `delete`
- `execute`
- `share`
- `manage`
- `administer`

### 为什么必须有 `execute`
在 Flowly 里，执行本身就是高价值动作：
- 会消耗资源
- 会使用凭证
- 会产生成本
- 可能访问数据和知识库

所以 `execute` 不能被默认等同于 `update` 或 `read`。

---

## 四、统一授权判断顺序

后续所有资源访问都应遵循同一判断顺序。

### Step 1：先识别 principal
- 是否匿名
- 是否登录
- 是否 superuser
- 属于哪些 tenant
- 在目标 tenant 中是什么角色

### Step 2：再识别资源边界
- resource.owner 是谁
- resource.tenant 是谁
- resource.visibility 是什么
- resource 是否 system resource

### Step 3：最后判断 action
- 当前主体对该资源执行该动作是否被允许

### 绝对禁止的顺序
不要再出现：
- 先按 query param tenant_id 过滤
- 再想办法补权限判断
- 或 action 里临时兜底判断

那会持续产生绕过点。

---

## 五、统一资源分类规则

不是所有资源都一样，后续应按资源类型定义默认授权模型。

---

## 5.1 Personal Resource
示例：
- 个人 draft workflow
- 个人 prompt 草稿
- 个人偏好设置

### 默认规则
- `tenant` 可为空
- 默认 `visibility=private`
- owner 是主控制人
- 非 owner 不可见，除非显式共享

---

## 5.2 Tenant Resource
示例：
- 团队 workflow
- 团队模板
- 团队知识库
- 团队凭证
- 团队 agent

### 默认规则
- `tenant` 必填
- `visibility=tenant`
- owner 只是创建者，不是唯一边界
- 访问必须基于 membership + role

---

## 5.3 Public Resource
示例：
- 官方模板
- 公开模板
- 公共文档型资源

### 默认规则
- 允许公开读取
- 不允许公开修改
- 如果带 tenant，必须明确规则，不允许隐式“既属于 tenant 又全站公开”而没有定义

---

## 5.4 System Resource
示例：
- 系统内置模板
- 平台默认 provider 配置
- 平台级通知规则

### 默认规则
- 平台统一维护
- tenant 侧通常只读
- 修改权限只属于 system admin

---

## 六、推荐的统一权限矩阵

以下矩阵不是最终代码，而是平台规则基线。

---

## 6.1 资源读取

### `list` / `retrieve`
- superuser：全部可见
- owner：自己的资源可见
- tenant admin/member/viewer：可见当前 tenant 授权资源
- 匿名用户：仅 public/system 中允许匿名读取的资源

---

## 6.2 资源创建

### `create`
- owner 只能在自己允许的 tenant 范围内创建资源
- 不允许伪造 `tenant_id`
- tenant 应由：
  - 当前上下文决定，或
  - 显式传入但必须经过 membership 验证

### 原则
客户端提交的 tenant 只是“申请使用哪个上下文”，不是最终真相。

---

## 6.3 资源更新与删除

### `update` / `delete`
- personal resource：通常 owner 可改删
- tenant resource：需按 tenant role 判断
- public/system resource：只有更高权限管理者可改删

### 强规则
`owner == request.user` 不能自动推导“可以删除 tenant 共享资源”。

否则团队共享资源会被个人随意破坏。

---

## 6.4 执行动作

### `execute`
建议规则：
- owner：自己的可执行资源可执行
- tenant member 及以上：可执行 tenant 授权资源
- viewer：默认不能执行
- 执行前必须再校验依赖资源权限

### 关键点
执行权限不是资源本身权限的简单子集，还要叠加：
- credential access
- knowledge access
- dataset access
- billing / quota policy

---

## 6.5 共享与管理动作

### `share`
- personal → tenant 的共享需要明确能力
- 通常 owner / tenant admin 以上可做

### `manage`
- 包括成员管理、可见性切换、审核、运营配置等
- 通常 tenant admin / owner 可做

### `administer`
- 平台级资源操作
- 仅 superuser / system admin

---

## 七、后端实现原则

这部分是后续代码落地必须遵守的约束。

---

## 7.1 membership 只能有一个标准来源
统一来源：
- `TenantMembership`
- `related_name='tenant_memberships'`

### 禁止继续出现
- `user.tenants.values_list(...)`
- 猜测式关联名
- 各 app 自己发明 membership helper

### 建议统一 helper
例如后续应有：
- `get_accessible_tenant_ids(user)`
- `get_tenant_role(user, tenant_id)`
- `is_tenant_admin(user, tenant_id)`

所有模块复用，不允许复制。

---

## 7.2 queryset 是第一道边界
所有资源访问必须优先在 queryset 层收紧。

### 原则
- `get_queryset()` 决定“默认你根本看不到什么”
- `permission class` 决定“你即使拿到了对象，也能不能做这个动作”
- `action()` 内部只做业务校验，不承担主授权责任

### 为什么
如果主授权散在 action 里，list/retrieve 就很容易漏掉。

---

## 7.3 子资源访问必须先校验父资源归属
例如：
- node 属于 workflow
- edge 属于 workflow
- execution 属于 workflow
- conversation 属于 agent
- document 属于 collection

### 强规则
任何基于父资源访问的子资源接口，都必须先通过父资源的 tenant access policy。

不要只看子资源自己的 owner 或 id。

---

## 7.4 create 时 tenant 绑定必须受控
很多漏洞都出在 create。

### 规则
- 后端不能盲信前端传入的 `tenant_id`
- 必须验证当前用户是否属于该 tenant
- 对 team resource，tenant 缺失应报错，而不是默认塞空
- 对 personal resource，tenant 是否允许为空必须显式规定

---

## 7.5 owner-only 规则只能用于 personal resource
### 禁止误用
像下面这种逻辑不能默认到处复用：
- `filter(owner=self.request.user)`

因为它只适用于真正的个人资源。

一旦资源是 tenant resource，这种写法就会直接砍掉团队语义，或者埋下共享漏洞。

---

## 八、前端配合规则

权限问题不只是后端问题，前端也不能继续放大风险。

---

## 8.1 tenant 上下文要显式，但不能当真相源
前端可以维护“当前 tenant 上下文”，但它只是 UX 状态，不是授权真相。

### 含义
- 前端可切换当前工作空间/tenant
- 但后端必须重新验证该上下文是否有效

---

## 8.2 页面路由和按钮可见性要基于统一权限能力
前端不应散落写：
- 某页面自己猜是不是 admin
- 某按钮自己猜是不是 owner

### 正确方式
后续前端应围绕统一能力判断，如：
- `canViewTemplate`
- `canEditWorkflow`
- `canExecuteWorkflow`
- `canManageTenantCredentials`

这些能力最终应来源于后端规则映射，而不是页面拍脑袋。

---

## 8.3 前端不得默认展示不属于当前 tenant 的敏感资源
例如：
- 凭证
- 知识库
- dataset
- tenant workflow
- agent conversation

这不是单纯 UX 问题，而是安全边界问题。

---

## 九、推荐的领域级默认策略

这部分直接给后续各业务域使用。

---

## 9.1 Workflow Domain
### 默认归类
- draft workflow：personal / tenant 混合，需要显式状态区分
- published team workflow：tenant resource

### 规则
- 读取走 tenant queryset
- 执行走 tenant + dependency access
- 节点、边、execution 继承 workflow 边界

---

## 9.2 Template Domain
### 默认归类
- 个人模板：personal
- 团队模板：tenant resource
- 官方模板：system/public
- 社区模板：public

### 规则
- 安装权限不等于查看权限
- 发布权限不等于编辑权限
- 运营权限单独定义

---

## 9.3 Resource / Credential Domain
### 默认归类
- 个人凭证：personal
- 团队共享凭证：tenant resource
- 系统 provider：system resource

### 规则
- 查看密钥、使用密钥、管理密钥必须分开权限
- 执行时对凭证的使用必须再校验一次

---

## 9.4 Knowledge / Dataset / RAG Domain
### 默认归类
- collection、dataset、vector store 原则上都应支持 tenant 边界

### 规则
- 不允许继续以 owner-only 为主要语义
- 被 workflow / template 引用时，必须验证跨资源权限一致性

---

## 9.5 Agent Domain
### 默认归类
- agent：personal 或 tenant resource
- conversation / execution / tool：继承 agent 边界

### 规则
- conversation 不能只按 `agent__owner=self.request.user` 过滤
- 如果 agent 属于 tenant，conversation / execution 也必须按 tenant policy 收口

---

## 十、建议的落地顺序

---

## Phase A：统一语义
### 要做什么
1. 确认 owner / tenant / visibility / role / action 定义
2. 确认哪些资源是 personal、tenant、public、system
3. 建统一 helper / policy 命名

### 完成标准
- 团队内部对访问语义没有歧义
- 新代码不再随手发明一套权限说法

---

## Phase B：先修 membership 与 queryset 基线
### 要做什么
1. 全域统一 membership 读取方式
2. 替换 `user.tenants.values_list(...)`
3. 把高风险资源先切到统一 tenant queryset

### 高优先级模块
- `workflows`
- `datasets`
- `agents`
- `rag`
- `gateway`

---

## Phase C：再收 action 权限
### 要做什么
1. 把 create/update/delete/execute/share/manage 拆开定义
2. 权限类统一化
3. 减少 action 内部临时授权逻辑

---

## Phase D：补跨资源一致性校验
### 要做什么
1. workflow 执行时校验 credential / dataset / knowledge 权限
2. template 安装时校验依赖资源权限
3. agent 执行时校验上下文资源权限

---

## Phase E：补回归测试
### 至少要有
- 跨 tenant list 不可见
- 跨 tenant retrieve 404/403
- viewer 不可执行
- member 不可管理 tenant settings
- 无 membership 时伪造 tenant_id 失败

---

## 十一、最终判断

Flowly 后续能不能真正变成团队级平台，不是取决于你做多少页面，而是取决于你有没有一套稳定的 tenant access policy。

如果这套规则不建立：
- 模板域做不稳
- 资源中心做不稳
- 成本归属做不稳
- 团队共享做不稳
- 审计追责做不稳

所以这份文档的结论很直接：

### tenant / access 不是辅助模块，而是平台根基

后续所有业务域都必须围绕下面这条规则实现：

> **owner 负责归责，tenant 负责边界，visibility 负责可见性，role 负责能力级别，action 决定最终授权。**

谁不遵守这套规则，谁就在继续制造未来的漏洞和重构成本。
