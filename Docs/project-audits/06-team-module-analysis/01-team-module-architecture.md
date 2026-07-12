# 团队模块深度解析报告

> 生成时间：2026-06-06
> 范围：Backend `tenants/` + Frontend `src/views/team/` + `src/stores/tenant.js` + `src/api/tenant.js`
> 性质：**诚实分析 — 问题不隐瞒，机会不夸大**

---

## 一、模块架构总览

### 1.1 模型层（9 个模型）

```
Tenant (租户)
├── TenantMembership (成员关系)         ← 核心
├── TenantInvitation (邀请)           ← 邮件 Token 邀请
├── TenantUsage (用量统计)
│
├── TeamSkill (团队技能)              ← AI 技能库
│   └── SkillAssignment (技能分配)
├── TeamTask (团队任务)               ← 任务协作
│   └── TaskAssignee (任务指派，through)
└── TeamActivity (活动日志)
```

### 1.2 API 层（7 个 ViewSet）

| ViewSet | 端点 | 操作 |
|---|---|---|
| `TenantViewSet` | `/tenants/` | CRUD + invite/remove_member/usage/members |
| `TenantMembershipViewSet` | `/memberships/` | 我的成员关系 |
| `TenantInvitationViewSet` | `/invitations/` | pending/join/accept/decline |
| `TenantUsageViewSet` | `/usage/` | 查询 + refresh |
| `TeamSkillViewSet` | `/skills/` | CRUD + assign/unassign |
| `TeamTaskViewSet` | `/tasks/` | CRUD + assign_user/unassign_user/change_status |
| `TeamActivityViewSet` | `/activities/` | 只读活动流 |

### 1.3 前端架构

```
Index.vue (1917行)
├── 团队卡片网格 (Tenants Grid)
├── 团队详情抽屉 (Detail Drawer, 6 tabs)
│   ├── 成员 (Members)
│   ├── 技能分工 (Skills)
│   ├── 任务协作 (Tasks)
│   ├── 使用统计 (Usage)
│   └── 活动日志 (Activity)
└── 7 个 Dialog (创建/邀请/技能/任务相关)
```

---

## 二、现存问题清单（诚实列举）

### 2.1 高危问题

#### P0-1：`isAdmin` 前端判断逻辑错误

**文件：** `Frontend/src/views/team/Index.vue` 第 1375 行

```javascript
function isAdmin(tenant) {
  return isOwner(tenant) || tenant.owner?.id === authStore.user?.id  // ← 逻辑重复！
}
```

`isOwner` 已经判断了 `tenant.owner?.id === authStore.user?.id`，`isAdmin` 又重复了一遍同样的逻辑。
真正的 admin 权限（`role === 'admin'`）从未被检查。

**后果：** 普通 admin 角色（role='admin'，非 owner）在 UI 上无法看到管理操作按钮，因为 `isAdmin` 总返回 `false`。

---

#### P0-2：角色变更后端未实际执行

**文件：** `Backend/tenants/views.py` 第 1504 行

```python
async def handleRoleChange(member):
  if member.role === 'owner':
    return
  appStore.info('角色变更已保存')  # ← 只有前端提示，没有 API 调用！
```

`handleRoleChange` 没有调用 `tenantStore` 的任何更新方法。后端也没有对应的 `PATCH /memberships/{id}/` 端点。角色变更只是前端乐观 UI 更新（没实际发请求）。

---

#### P0-3：`update_task_status` 乐观更新 Bug

**文件：** `Frontend/src/views/team/Index.vue` 第 1705 行

```javascript
async function handleTaskStatusChange(task) {
  await tenantStore.changeTaskStatus(task.id, task.status)
  // task.status 已经是新值，但若请求失败，UI 不会回滚
}
```

任务状态变更用 `el-select` 的 `v-model="task.status"` 双向绑定乐观更新，但没有错误回滚逻辑。API 失败时 UI 已变更但数据不一致。

---

#### P0-4：`TenantInvitation.invite` 要求对方是注册用户

**文件：** `Backend/tenants/serializers.py` 第 158 行

```python
def validate_email(self, value):
    User.objects.get(email=value)  # ← 不存在则抛 ValidationError
```

邀请新用户时，必须是已注册用户。这意味着邀请流程是"先注册再邀请"，而不是"发送邀请链接，对方点击后注册+加入"。

---

### 2.2 中危问题

#### P1-1：`TenantMembershipCreateSerializer` 只支持已注册用户邀请

与 P0-4 同源，但更深层的问题是：邀请接口没有区分"邀请已注册用户"和"邀请潜在用户"两种场景。

---

#### P1-2：权限判断分散，有两套实现

**文件：** `Backend/tenants/views.py`

```python
class TenantPermission:        # 第 30 行
    @staticmethod
    def is_member(user, tenant):
        return is_tenant_member(user, tenant.id)  # ← 委托到 tenants.access

class TeamSkillPermission:     # 第 431 行
    @staticmethod
    def is_admin(user, tenant):
        return TenantMembership.objects.filter(...)  # ← 自建查询，未委托 access.py
```

`TenantPermission` 委托到 `access.py`，但 `TeamSkillPermission` 重新实现了相同的逻辑。两条路径可能因为 `is_active=True` 等细节不一致而出现行为差异。

---

#### P1-3：usage refresh 统计口径错误

**文件：** `Backend/tenants/views.py` 第 410 行

```python
usage.current_month_workflows = Workflow.objects.filter(
    owner__in=tenant.memberships.values_list('user', flat=True)
).count()
```

`Workflow.owner` 是 User FK，但 tenant 成员的资源归属是通过 `Workflow.tenant` 而非 `Workflow.owner`。这个查询会漏掉所有通过 `tenant` 关联的工作流。

---

#### P1-4：活动日志硬上限

**文件：** `Backend/tenants/views.py` 第 712 行

```python
return qs[:100]  # 硬编码 100 条
```

没有分页，没有时间过滤，活动多了就截断。无法做历史追溯。

---

#### P1-5：删除成员后没有记录活动日志

**文件：** `Backend/tenants/views.py` 第 188 行

```python
def remove_member(self, request, pk=None):
    membership.delete()  # ← 直接删除，无 TeamActivity 记录
```

成员被移除是重要操作，应该写入 `TeamActivity`。

---

#### P1-6：`TaskAssignee` 和 `SkillAssignment` 角色系统不统一

| 维度 | TaskAssignee | SkillAssignment |
|---|---|---|
| 角色选项 | owner/contributor/reviewer/viewer | owner/contributor/reviewer/viewer |
| 角色字段 | `TaskAssignee.role` | `SkillAssignment.role` |
| `is_admin` 逻辑 | 用 `TeamSkillPermission.is_admin` | 用 `TeamSkillPermission.is_admin` |

两套 through model 有相同的角色枚举，但代码中混用：任务有"负责人"(owner) 概念，技能也有，但 owner 在两个场景中的权限含义完全不同。

---

#### P1-7：前端任务状态变更权限过宽

**文件：** `Frontend/src/views/team/Index.vue` 第 521 行

```html
<el-select v-model="task.status" @change="handleTaskStatusChange(task)">
```

任何成员都可以改变任务状态，没有检查权限。没有 `isAdmin` 检查，也没有检查是否是 assignee。

---

### 2.3 低危问题

#### P2-1：UI 交互缺少删除确认 API 调用

部分删除操作（成员移除、技能删除）前端弹窗确认，但未调用 `tenantStore` 的对应删除方法：`handleRemoveMember` 调用了 store，但 `handleDeleteSkill` 和 `handleDeleteTask` 同样调用了 store，经核实是正确的。实际只有角色变更没有 API 调用。

---

#### P2-2：`TenantInvitation` 邀请链接未发送邮件

邀请创建后没有实际发送邮件，只是返回了 token。邀请流程断了。

---

#### P2-3：usage 页面无刷新按钮

`/team` 页面只加载一次 usage，没有"刷新"按钮与 `/usage/refresh/` 端点联动。

---

#### P2-4：TeamTask 无批量操作

任务列表没有"批量标记完成"、"批量分配"等操作。大型团队无法高效管理。

---

#### P2-5：API URL 命名与 REST 规范不符

```
GET  /tenants/{id}/invite/        ← invite 是 POST，不是资源
DELETE /tenants/{id}/remove_member/  ← remove_member 是操作，非资源
POST  /tenants/{id}/invite/       ← 正确，但 GET /tenants/{id}/invite/ 无意义
POST  /tenants/{id}/remove_member/ ← 正确
```

---

#### P2-6：frontend `isAdmin` vs backend `is_admin` 命名不一致

前端用 `isAdmin()` 函数，后端用 `is_admin` role 字符串。没有统一。

---

## 三、可实现的功能机会

> 以下按投入产出比排序，每项标注最低实现成本

### 3.1 高价值（低成本，高产出）

| 功能 | 描述 | 最低实现成本 |
|---|---|---|
| **角色变更 API** | P0-2 的修复：添加 `PATCH /memberships/{id}/` 更新角色 | 1 个 action |
| **邮件邀请流程** | 邀请创建后发送邮件，邮件包含 `accept` 链接 | 集成邮件服务 |
| **成员加入/离开活动日志** | 补充 `member_joined` / `member_left` 记录 | 3 行代码 |
| **邀请待处理 Badge** | 顶栏/侧边栏显示未读邀请数 | 2 个 computed |
| **任务统计看板** | Usage tab 下增加任务完成率、逾期率等指标 | 3 个 aggregate query |

### 3.2 中价值（中等成本）

| 功能 | 描述 | 最低实现成本 |
|---|---|---|
| **工作流所有者感知** | 团队成员创建的工作流在 Workflow 模型中设置 `tenant`，使 usage 统计准确 | 1 个 signal |
| **技能推荐** | 根据成员技能分配 AI workflow 任务 | 新增 serializer + 2 个 view |
| **任务甘特图视图** | 切换到日历/Gantt 视图展示任务时间线 | 新增 Vue 组件 |
| **活动日志分页** | 替换硬编码 `[:100]` 为 DRF 分页 | 1 行改动 |
| **使用量告警** | usage 接近限额时自动通知 | Celery task |
| **成员在线状态** | WebSocket 推送成员活跃状态 | Django channels |

### 3.3 长期价值（高成本）

| 功能 | 描述 | 备注 |
|---|---|---|
| **权限矩阵系统** | 用 `TenantMembership.permissions` JSONField 实现细粒度 RBAC | 需要完整设计 |
| **团队模板市场** | 团队内部分享 workflow 模板，带权限控制 | 复用现有模板系统 |
| **任务依赖图** | 任务之间可设置依赖关系，形成 DAG | 数据模型扩展 |
| **AI 任务分配** | 基于成员技能熟练度自动推荐最优任务分配 | 需 ML 模型 |

---

## 四、跨模块依赖关系

```
tenants/TeamTask.tenant_id
  └── workflows/TrainingJob.tenant_id          ← 训练任务归属
  └── datasets/Dataset.tenant_id              ← 数据集归属
  └── augmentation/AugmentationJob.tenant_id  ← 数据增强归属
  └── website_generator/GeneratedSite.tenant_id← 网站生成归属
  └── workflows/Workflow.tenant_id           ← 工作流归属（!）

tenants/TenantInvitation.token
  └── 无邮件服务集成 ← 邀请流程断点

TenantUsage.current_month_*  ← 统计口径依赖各 app 的 tenant 字段填充率
```

**关键发现：** `Workflow` 模型有 `tenant` 字段，但 `WorkflowExecution` 没有。执行历史无法按 tenant 聚合。

---

## 五、修复优先级建议

```
P0（安全/数据损坏，必须立即修）:
  1. isAdmin 逻辑修复（前端）
  2. 角色变更 API 连接（后端+前端）
  3. usage 统计口径修正（后端）

P1（本版本应修，不修影响核心体验）:
  4. 邀请邮件流程
  5. 活动日志分页
  6. 成员操作写入日志
  7. 任务状态变更权限检查

P2（下版本规划）:
  8. 成员邀请开放给未注册用户
  9. 任务看板/甘特图视图
  10. 使用量告警通知
```

---

## 六、快速修复（当天可完成）

### 6.1 isAdmin 逻辑修复（1 行）

```javascript
// Frontend/src/views/team/Index.vue 第 1375 行
// 修改前：
function isAdmin(tenant) {
  return isOwner(tenant) || tenant.owner?.id === authStore.user?.id
}
// 修改后：需要从 members list 中查询当前用户的 membership role
// 需要新增 computed: currentUserMembership(tenant)
```

### 6.2 角色变更 API（后端 1 个 action）

```python
# Backend/tenants/views.py
@action(detail=True, methods=['patch'])
def update_role(self, request, pk=None):
    membership = self.get_object()
    new_role = request.data.get('role')
    if membership.role == 'owner':
        return Response({'error': '不能修改所有者角色'}, status=400)
    membership.role = new_role
    membership.save()
    return Response(TenantMembershipSerializer(membership).data)
```

### 6.3 成员操作日志（后端 3 行）

在 `remove_member` action 的 `membership.delete()` 前插入：

```python
TeamActivity.objects.create(
    tenant=tenant, user=request.user,
    action='member_left',
    description=f'移除成员: {membership.user.username}'
)
```

---

## 七、文档结构建议

后续工作建议按以下结构组织：

```
Docs/project-audits/05-team-module-analysis/
├── 01-team-module-architecture.md    ← 本文档（架构+问题）
├── 02-team-fixes-p0-p1.md            ← P0/P1 修复执行记录
├── 03-team-features-roadmap.md       ← 功能路线图
└── 04-team-permission-matrix.md     ← 权限矩阵设计（未来）
```
