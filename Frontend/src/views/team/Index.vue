<template>
  <PageShell
    width="wide"
    class="team-page"
  >
    <PageHeader
      title="团队管理"
      subtitle="管理团队成员、技能分工与任务协作"
    >
      <template #actions>
        <el-button
          type="primary"
          @click="openCreateDialog"
        >
          <Plus class="btn-icon" />
          创建团队
        </el-button>
      </template>
    </PageHeader>

    <!-- Pending Invitations Banner -->
    <div
      v-if="pendingInvitations.length > 0"
      class="invitations-banner"
    >
      <div class="banner-content">
        <Bell class="banner-icon" />
        <span>您有 {{ pendingInvitations.length }} 个待处理邀请</span>
      </div>
      <el-button
        size="small"
        @click="showInvitationsDialog = true"
      >
        查看
      </el-button>
    </div>

    <!-- Tenants Grid -->
    <div class="tenants-section">
      <div
        v-if="tenants.length === 0 && !isLoading"
        class="empty-state"
      >
        <Users class="empty-icon" />
        <h3>暂无团队</h3>
        <p>创建您的第一个团队，邀请成员协作</p>
        <el-button
          type="primary"
          @click="openCreateDialog"
        >
          创建团队
        </el-button>
      </div>

      <div
        v-else
        class="tenants-grid"
      >
        <div
          v-for="tenant in tenants"
          :key="tenant.id"
          class="tenant-card"
          :class="{ active: selectedTenant?.id === tenant.id }"
          @click="selectTenant(tenant)"
        >
          <div class="card-header">
            <div class="tenant-avatar">
              {{ tenant.name?.charAt(0)?.toUpperCase() ?? '?' }}
            </div>
            <div class="tenant-info">
              <h3 class="tenant-name">
                {{ tenant.name }}
              </h3>
              <el-tag
                size="small"
                :type="getPlanType(tenant.plan)"
              >
                {{ getPlanLabel(tenant.plan) }}
              </el-tag>
            </div>
            <el-dropdown trigger="click">
              <el-button
                text
                size="small"
              
                :aria-label="`${tenant.name}的更多操作`"
              >
                <MoreVertical />
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item @click.stop="editTenant(tenant)">
                    <Edit class="menu-icon" />编辑
                  </el-dropdown-item>
                  <el-dropdown-item
                    v-if="isOwner(tenant)"
                    divided
                    class="danger-item"
                    @click.stop="handleDeleteTenant(tenant)"
                  >
                    <Trash2 class="menu-icon" />删除
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
          <p class="tenant-desc">
            {{ tenant.description || '暂无描述' }}
          </p>
          <div class="tenant-stats">
            <div class="stat">
              <Users class="stat-icon" /><span>{{ tenant.member_count || 0 }} 成员</span>
            </div>
            <div class="stat">
              <GitBranch class="stat-icon" /><span>{{ tenant.max_workflows }} 工作流</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ==================== Tenant Detail Drawer ==================== -->
    <el-drawer
      v-model="showDetailPanel"
      :title="selectedTenant?.name"
      size="900px"
      class="team-detail-drawer"
    >
      <div
        v-if="selectedTenant"
        class="tenant-detail"
      >
        <!-- Tabs -->
        <el-tabs
          v-model="detailTab"
          class="detail-tabs"
        >
          <!-- ---- Members Tab ---- -->
          <el-tab-pane
            label="成员"
            name="members"
          >
            <div class="section-header">
              <h4>成员列表</h4>
              <el-button
                v-if="isAdmin()"
                size="small"
                type="primary"
                @click="showInviteDialog = true"
              >
                <Plus class="btn-icon-sm" />邀请
              </el-button>
            </div>

            <div
              v-if="isLoadingMembers"
              class="loading"
            >
              <el-skeleton
                :rows="3"
                animated
              />
            </div>
            <div
              v-else
              class="members-list"
            >
              <div
                v-for="member in members"
                :key="member.id"
                class="member-item"
              >
                <div class="member-avatar">
                  {{ member.user?.username?.charAt(0)?.toUpperCase() ?? '?' }}
                </div>
                <div class="member-info">
                  <span class="member-name">{{ member.user?.username }}</span>
                  <span class="member-email">{{ member.user?.email }}</span>
                </div>
                <el-select
                  v-model="member.role"
                  size="small"
                  style="width: 100px"
                  :disabled="member.role === 'owner' || !isAdmin()"
                  @change="handleRoleChange(member)"
                >
                  <el-option
                    label="所有者"
                    value="owner"
                  />
                  <el-option
                    label="管理员"
                    value="admin"
                  />
                  <el-option
                    label="成员"
                    value="member"
                  />
                  <el-option
                    label="查看者"
                    value="viewer"
                  />
                </el-select>
                <el-button
                  v-if="canRemoveMember(member)"
                  text
                  size="small"
                  type="danger"
                  @click="handleRemoveMember(member)"
                >
                  <Trash2 class="remove-icon" />
                </el-button>
              </div>
            </div>
          </el-tab-pane>

          <!-- ---- Team Knowledge Base Tab ---- -->
          <el-tab-pane
            label="团队知识库"
            name="knowledge"
          >
            <div class="section-header">
              <h4>团队共享知识库</h4>
              <el-button
                size="small"
                @click="goToKnowledge"
              >
                前往知识库管理
                <ArrowRight class="btn-icon-sm" />
              </el-button>
            </div>
            <div
              v-if="isLoadingKnowledge"
              class="loading"
            >
              <el-skeleton
                :rows="3"
                animated
              />
            </div>
            <div
              v-else-if="teamCollections.length === 0"
              class="empty-tab"
            >
              <p>该团队暂无共享知识库，前往「知识库」页面创建时选择所属团队即可共享</p>
            </div>
            <div
              v-else
              class="resource-grid"
            >
              <div
                v-for="col in teamCollections"
                :key="col.id"
                class="resource-card"
              >
                <div class="resource-icon kb-icon">
                  <BookOpen class="resource-icon-inner" />
                </div>
                <div class="resource-info">
                  <h5>{{ col.name }}</h5>
                  <p class="resource-desc">
                    {{ col.description || '暂无描述' }}
                  </p>
                  <div class="resource-meta">
                    <span>{{ col.document_count ?? 0 }} 篇文档 · {{ col.chunk_count ?? 0 }} 分块</span>
                    <span>{{ col.embedding_model }}</span>
                  </div>
                </div>
              </div>
            </div>
          </el-tab-pane>

          <!-- ---- Team Agents Tab ---- -->
          <el-tab-pane
            label="团队 Agent"
            name="agents"
          >
            <div class="section-header">
              <h4>团队共享 Agent</h4>
              <el-button
                size="small"
                @click="router.push('/agents')"
              >
                前往 Agent 管理
                <ArrowRight class="btn-icon-sm" />
              </el-button>
            </div>
            <div
              v-if="isLoadingTeamAgents"
              class="loading"
            >
              <el-skeleton
                :rows="3"
                animated
              />
            </div>
            <div
              v-else-if="teamAgents.length === 0"
              class="empty-tab"
            >
              <p>该团队暂无共享 Agent，创建/编辑 Agent 时选择所属团队即可共享</p>
            </div>
            <div
              v-else
              class="resource-grid"
            >
              <div
                v-for="agent in teamAgents"
                :key="agent.id"
                class="resource-card clickable"
                @click="goToAgent(agent)"
              >
                <div class="resource-icon agent-icon">
                  <Bot class="resource-icon-inner" />
                </div>
                <div class="resource-info">
                  <h5>{{ agent.name }}</h5>
                  <p class="resource-desc">
                    {{ agent.description || '暂无描述' }}
                  </p>
                  <div class="resource-meta">
                    <span>{{ agent.model }}</span>
                    <span v-if="agent.knowledge_collections?.length">
                      关联 {{ agent.knowledge_collections.length }} 个知识库
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </el-tab-pane>

          <!-- ---- AI Collaboration Records Tab ---- -->
          <el-tab-pane
            label="AI协作记录"
            name="collaborations"
          >
            <div class="section-header">
              <h4>多智能体协作记录</h4>
              <el-button
                size="small"
                type="primary"
                @click="goToCollaborate"
              >
                <Plus class="btn-icon-sm" />发起协作
              </el-button>
            </div>
            <div
              v-if="isLoadingCollaborations"
              class="loading"
            >
              <el-skeleton
                :rows="3"
                animated
              />
            </div>
            <div
              v-else-if="teamCollaborations.length === 0"
              class="empty-tab"
            >
              <p>该团队暂无协作记录，点击「发起协作」创建一次多智能体协作任务</p>
            </div>
            <div
              v-else
              class="collaborations-list"
            >
              <div
                v-for="run in teamCollaborations"
                :key="run.id"
                class="collaboration-item"
              >
                <div class="collab-icon">
                  <Workflow class="collab-icon-inner" />
                </div>
                <div class="collab-content">
                  <p class="collab-task">
                    {{ run.task }}
                  </p>
                  <div class="collab-meta">
                    <span>{{ run.created_by_username }}</span>
                    <span>{{ formatDateTime(run.started_at) }}</span>
                  </div>
                </div>
                <el-tag
                  size="small"
                  :type="getCollaborationStatusType(run.status)"
                >
                  {{ getCollaborationStatusLabel(run.status) }}
                </el-tag>
              </div>
            </div>
          </el-tab-pane>

          <!-- ---- Skills Tab ---- -->
          <el-tab-pane
            label="技能分工"
            name="skills"
          >
            <div class="section-header">
              <h4>团队技能</h4>
              <el-button
                v-if="isAdmin()"
                size="small"
                type="primary"
                @click="openSkillCreateDialog"
              >
                <Plus class="btn-icon-sm" />添加技能
              </el-button>
            </div>

            <!-- Skills Filter -->
            <div class="skills-filter">
              <el-select
                v-model="skillCategoryFilter"
                size="small"
                clearable
                placeholder="分类筛选"
                style="width: 140px"
              >
                <el-option
                  label="工作流"
                  value="workflow"
                />
                <el-option
                  label="Agent"
                  value="agent"
                />
                <el-option
                  label="数据处理"
                  value="data"
                />
                <el-option
                  label="集成"
                  value="integration"
                />
                <el-option
                  label="监控"
                  value="monitoring"
                />
                <el-option
                  label="提示词"
                  value="prompt"
                />
                <el-option
                  label="测试"
                  value="testing"
                />
                <el-option
                  label="部署"
                  value="deployment"
                />
                <el-option
                  label="文档"
                  value="documentation"
                />
                <el-option
                  label="其他"
                  value="other"
                />
              </el-select>
            </div>

            <div
              v-if="isLoadingSkills"
              class="loading"
            >
              <el-skeleton
                :rows="3"
                animated
              />
            </div>
            <div
              v-else-if="filteredSkills.length === 0"
              class="empty-tab"
            >
              <p>暂无技能，点击「添加技能」创建第一个团队技能</p>
            </div>
            <div
              v-else
              class="skills-grid"
            >
              <div
                v-for="skill in filteredSkills"
                :key="skill.id"
                class="skill-card"
              >
                <div class="skill-header">
                  <div
                    class="skill-icon"
                    :style="{ background: getCategoryColor(skill.category) }"
                  >
                    <Cpu class="skill-icon-inner" />
                  </div>
                  <div class="skill-info">
                    <h5>{{ skill.name }}</h5>
                    <el-tag
                      size="small"
                      type="info"
                    >
                      {{ getCategoryLabel(skill.category) }}
                    </el-tag>
                  </div>
                  <el-dropdown
                    v-if="isAdmin()"
                    trigger="click"
                  >
                    <el-button
                      text
                      size="small"
                    
                      :aria-label="`${skill.name}的更多操作`"
                    >
                      <MoreVertical />
                    </el-button>
                    <template #dropdown>
                      <el-dropdown-menu>
                        <el-dropdown-item @click="openSkillAssignDialog(skill)">
                          <UserPlus class="menu-icon" />分配成员
                        </el-dropdown-item>
                        <el-dropdown-item @click="openSkillEditDialog(skill)">
                          <Edit class="menu-icon" />编辑
                        </el-dropdown-item>
                        <el-dropdown-item
                          divided
                          class="danger-item"
                          @click="handleDeleteSkill(skill)"
                        >
                          <Trash2 class="menu-icon" />删除
                        </el-dropdown-item>
                      </el-dropdown-menu>
                    </template>
                  </el-dropdown>
                </div>
                <p class="skill-desc">
                  {{ skill.description || '暂无描述' }}
                </p>
                <div class="skill-meta">
                  <span class="meta-item">
                    <Star class="meta-icon" />
                    熟练度 {{ skill.mastery_level }}/5
                  </span>
                  <span class="meta-item">
                    <Users class="meta-icon" />
                    {{ skill.assignee_count }} 人
                  </span>
                </div>
                <div
                  v-if="skill.keywords?.length"
                  class="skill-keywords"
                >
                  <el-tag
                    v-for="kw in skill.keywords.slice(0, 4)"
                    :key="kw"
                    size="small"
                  >
                    {{ kw }}
                  </el-tag>
                </div>
              </div>
            </div>
          </el-tab-pane>

          <!-- ---- Tasks Tab ---- -->
          <el-tab-pane
            label="任务协作"
            name="tasks"
          >
            <div class="section-header">
              <h4>团队任务</h4>
              <el-button
                v-if="isAdmin()"
                size="small"
                type="primary"
                @click="openTaskCreateDialog"
              >
                <Plus class="btn-icon-sm" />创建任务
              </el-button>
            </div>

            <!-- Task Filters -->
            <div class="tasks-filter">
              <el-select
                v-model="taskStatusFilter"
                size="small"
                clearable
                placeholder="状态筛选"
                style="width: 120px"
              >
                <el-option
                  label="待处理"
                  value="todo"
                />
                <el-option
                  label="进行中"
                  value="in_progress"
                />
                <el-option
                  label="审核中"
                  value="review"
                />
                <el-option
                  label="已完成"
                  value="done"
                />
                <el-option
                  label="已阻塞"
                  value="blocked"
                />
                <el-option
                  label="已取消"
                  value="cancelled"
                />
              </el-select>
              <el-select
                v-model="taskPriorityFilter"
                size="small"
                clearable
                placeholder="优先级"
                style="width: 100px"
              >
                <el-option
                  label="紧急"
                  value="urgent"
                />
                <el-option
                  label="高"
                  value="high"
                />
                <el-option
                  label="中"
                  value="medium"
                />
                <el-option
                  label="低"
                  value="low"
                />
              </el-select>
            </div>

            <div
              v-if="isLoadingTasks"
              class="loading"
            >
              <el-skeleton
                :rows="3"
                animated
              />
            </div>
            <div
              v-else-if="filteredTasks.length === 0"
              class="empty-tab"
            >
              <p>暂无任务，点击「创建任务」分配团队工作</p>
            </div>
            <div
              v-else
              class="tasks-list"
            >
              <div
                v-for="task in filteredTasks"
                :key="task.id"
                class="task-item"
                :class="`task-${task.status}`"
              >
                <div
                  class="task-priority-indicator"
                  :class="`priority-${task.priority}`"
                />
                <div class="task-content">
                  <div class="task-header">
                    <span
                      class="task-title"
                      :class="{ 'task-overdue': task.is_overdue }"
                    >{{ task.title }}</span>
                    <div class="task-tags">
                      <el-tag
                        size="small"
                        :type="getTaskStatusType(task.status)"
                      >
                        {{ getTaskStatusLabel(task.status) }}
                      </el-tag>
                      <el-tag
                        size="small"
                        :type="getPriorityType(task.priority)"
                        effect="plain"
                      >
                        {{ getPriorityLabel(task.priority) }}
                      </el-tag>
                    </div>
                  </div>
                  <div class="task-meta">
                    <span v-if="task.owner_name"><User class="meta-icon-sm" /> {{ task.owner_name }}</span>
                    <span v-if="task.due_date"><Calendar class="meta-icon-sm" /> {{ formatDate(task.due_date) }}</span>
                    <span
                      v-if="task.is_overdue"
                      class="overdue-label"
                    ><AlertTriangle class="meta-icon-sm" /> 已逾期</span>
                    <span><Users class="meta-icon-sm" /> {{ task.assignee_count }} 人</span>
                  </div>
                </div>
                <div class="task-actions">
                  <el-select
                    v-model="task.status"
                    size="small"
                    style="width: 110px"
                    @change="handleTaskStatusChange(task)"
                  >
                    <el-option
                      label="待处理"
                      value="todo"
                    />
                    <el-option
                      label="进行中"
                      value="in_progress"
                    />
                    <el-option
                      label="审核中"
                      value="review"
                    />
                    <el-option
                      label="已完成"
                      value="done"
                    />
                    <el-option
                      label="已阻塞"
                      value="blocked"
                    />
                    <el-option
                      label="已取消"
                      value="cancelled"
                    />
                  </el-select>
                  <el-dropdown
                    v-if="isAdmin()"
                    trigger="click"
                  >
                    <el-button
                      text
                      size="small"
                    
                      :aria-label="`${task.title || task.name}的更多操作`"
                    >
                      <MoreVertical />
                    </el-button>
                    <template #dropdown>
                      <el-dropdown-menu>
                        <el-dropdown-item @click="openTaskAssignDialog(task)">
                          <UserPlus class="menu-icon" />分配成员
                        </el-dropdown-item>
                        <el-dropdown-item @click="openTaskEditDialog(task)">
                          <Edit class="menu-icon" />编辑
                        </el-dropdown-item>
                        <el-dropdown-item
                          divided
                          class="danger-item"
                          @click="handleDeleteTask(task)"
                        >
                          <Trash2 class="menu-icon" />删除
                        </el-dropdown-item>
                      </el-dropdown-menu>
                    </template>
                  </el-dropdown>
                </div>
              </div>
            </div>
          </el-tab-pane>

          <!-- ---- Usage Tab ---- -->
          <el-tab-pane
            label="使用统计"
            name="usage"
          >
            <div class="usage-grid">
              <div class="usage-item">
                <span class="usage-label">成员数</span>
                <el-progress
                  :percentage="getUsagePercentage(usage?.current_month_users, selectedTenant.max_users)"
                  :status="getProgressStatus(getUsagePercentage(usage?.current_month_users, selectedTenant.max_users))"
                />
                <span class="usage-value">{{ usage?.current_month_users || 0 }} / {{ selectedTenant.max_users }}</span>
              </div>
              <div class="usage-item">
                <span class="usage-label">工作流数</span>
                <el-progress
                  :percentage="getUsagePercentage(usage?.current_month_workflows, selectedTenant.max_workflows)"
                  :status="getProgressStatus(getUsagePercentage(usage?.current_month_workflows, selectedTenant.max_workflows))"
                />
                <span class="usage-value">{{ usage?.current_month_workflows || 0 }} / {{ selectedTenant.max_workflows }}</span>
              </div>
              <div class="usage-item">
                <span class="usage-label">本月执行</span>
                <el-progress
                  :percentage="getUsagePercentage(usage?.current_month_executions, selectedTenant.max_executions_per_month)"
                  :status="getProgressStatus(getUsagePercentage(usage?.current_month_executions, selectedTenant.max_executions_per_month))"
                />
                <span class="usage-value">{{ usage?.current_month_executions || 0 }} / {{ selectedTenant.max_executions_per_month }}</span>
              </div>
            </div>
          </el-tab-pane>

          <!-- ---- Activity Tab ---- -->
          <el-tab-pane
            label="活动日志"
            name="activity"
          >
            <div
              v-if="isLoadingActivities"
              class="loading"
            >
              <el-skeleton
                :rows="5"
                animated
              />
            </div>
            <div
              v-else-if="activities.length === 0"
              class="empty-tab"
            >
              <p>暂无活动记录</p>
            </div>
            <div
              v-else
              class="activity-list"
            >
              <div
                v-for="act in activities"
                :key="act.id"
                class="activity-item"
              >
                <div
                  class="activity-dot"
                  :class="`activity-${act.action}`"
                />
                <div class="activity-content">
                  <p class="activity-desc">
                    {{ act.description }}
                  </p>
                  <span class="activity-time">{{ formatDateTime(act.created_at) }}</span>
                </div>
              </div>
            </div>
          </el-tab-pane>
        </el-tabs>
      </div>
    </el-drawer>

    <!-- ==================== Dialogs ==================== -->

    <!-- Create / Edit Tenant Dialog -->
    <el-dialog
      v-model="showCreateDialog"
      :title="editingTenant ? '编辑团队' : '创建团队'"
      width="500px"
    >
      <el-form
        ref="formRef"
        :model="formData"
        :rules="formRules"
        label-position="top"
      >
        <el-form-item
          label="团队名称"
          prop="name"
        >
          <el-input
            v-model="formData.name"
            placeholder="输入团队名称"
          />
        </el-form-item>
        <el-form-item
          v-if="!editingTenant"
          label="团队标识"
          prop="slug"
        >
          <el-input
            v-model="formData.slug"
            placeholder="英文标识（唯一）"
          >
            <template #prefix>
              flowly.app/
            </template>
          </el-input>
        </el-form-item>
        <el-form-item label="描述">
          <el-input
            v-model="formData.description"
            type="textarea"
            :rows="3"
            placeholder="团队描述（可选）"
          />
        </el-form-item>
        <el-form-item
          label="账单邮箱"
          prop="billing_email"
        >
          <el-input
            v-model="formData.billing_email"
            type="email"
            placeholder="账单接收邮箱"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">
          取消
        </el-button>
        <el-button
          type="primary"
          :loading="isSaving"
          @click="handleCreate"
        >
          {{ editingTenant ? '保存' : '创建' }}
        </el-button>
      </template>
    </el-dialog>

    <!-- Invite Dialog -->
    <el-dialog
      v-model="showInviteDialog"
      title="邀请成员"
      width="400px"
    >
      <el-form
        ref="inviteFormRef"
        :model="inviteForm"
        label-position="top"
      >
        <el-form-item
          label="邮箱"
          prop="email"
        >
          <el-input
            v-model="inviteForm.email"
            type="email"
            placeholder="输入成员邮箱"
          />
        </el-form-item>
        <el-form-item
          label="角色"
          prop="role"
        >
          <el-select
            v-model="inviteForm.role"
            style="width: 100%"
          >
            <el-option
              label="成员"
              value="member"
            />
            <el-option
              label="管理员"
              value="admin"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showInviteDialog = false">
          取消
        </el-button>
        <el-button
          type="primary"
          :loading="isSaving"
          @click="handleInvite"
        >
          发送邀请
        </el-button>
      </template>
    </el-dialog>

    <!-- Pending Invitations Dialog -->
    <el-dialog
      v-model="showInvitationsDialog"
      title="待处理邀请"
      width="500px"
    >
      <div
        v-if="pendingInvitations.length === 0"
        class="empty-tab"
      >
        <p>暂无待处理的邀请</p>
      </div>
      <div
        v-else
        class="invitations-list"
      >
        <div
          v-for="inv in pendingInvitations"
          :key="inv.id"
          class="invitation-item"
        >
          <div class="inv-info">
            <span class="inv-tenant">{{ inv.tenant_name }}</span>
            <span class="inv-role">{{ getRoleLabel(inv.role) }}</span>
          </div>
          <div class="inv-actions">
            <el-button
              size="small"
              type="primary"
              @click="handleAccept(inv)"
            >
              接受
            </el-button>
            <el-button
              size="small"
              @click="handleDecline(inv)"
            >
              拒绝
            </el-button>
          </div>
        </div>
      </div>
    </el-dialog>

    <!-- Create / Edit Skill Dialog -->
    <el-dialog
      v-model="showSkillDialog"
      :title="editingSkill ? '编辑技能' : '创建技能'"
      width="550px"
    >
      <el-form
        ref="skillFormRef"
        :model="skillForm"
        label-position="top"
      >
        <el-form-item
          label="技能名称"
          prop="name"
        >
          <el-input
            v-model="skillForm.name"
            placeholder="例如：工作流设计、API集成"
          />
        </el-form-item>
        <el-form-item label="技能描述">
          <el-input
            v-model="skillForm.description"
            type="textarea"
            :rows="2"
            placeholder="简要描述此技能的用途"
          />
        </el-form-item>
        <div class="form-row">
          <el-form-item
            label="分类"
            prop="category"
            style="flex: 1"
          >
            <el-select
              v-model="skillForm.category"
              style="width: 100%"
            >
              <el-option
                label="工作流"
                value="workflow"
              />
              <el-option
                label="Agent"
                value="agent"
              />
              <el-option
                label="数据处理"
                value="data"
              />
              <el-option
                label="集成"
                value="integration"
              />
              <el-option
                label="监控"
                value="monitoring"
              />
              <el-option
                label="提示词"
                value="prompt"
              />
              <el-option
                label="测试"
                value="testing"
              />
              <el-option
                label="部署"
                value="deployment"
              />
              <el-option
                label="文档"
                value="documentation"
              />
              <el-option
                label="其他"
                value="other"
              />
            </el-select>
          </el-form-item>
          <el-form-item
            label="所需熟练度"
            prop="mastery_level"
            style="flex: 1"
          >
            <el-rate
              v-model="skillForm.mastery_level"
              :max="5"
              show-text
              :texts="['入门', '初级', '中级', '高级', '专家']"
            />
          </el-form-item>
        </div>
        <el-form-item label="关键词（逗号分隔）">
          <el-input
            v-model="skillKeywordsInput"
            placeholder="例如：LLM, API, Python"
          />
        </el-form-item>
        <el-form-item label="技能说明">
          <el-input
            v-model="skillForm.instructions"
            type="textarea"
            :rows="3"
            placeholder="详细的技能使用说明和规范"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showSkillDialog = false">
          取消
        </el-button>
        <el-button
          type="primary"
          :loading="isSaving"
          @click="handleSaveSkill"
        >
          {{ editingSkill ? '保存' : '创建' }}
        </el-button>
      </template>
    </el-dialog>

    <!-- Assign Skill Dialog -->
    <el-dialog
      v-model="showSkillAssignDialog"
      title="分配技能"
      width="450px"
    >
      <el-form label-position="top">
        <el-form-item label="选择成员">
          <el-select
            v-model="skillAssignUserId"
            placeholder="选择成员"
            style="width: 100%"
          >
            <el-option
              v-for="member in members"
              :key="member.id"
              :label="`${member.user?.username} (${getRoleLabel(member.role)})`"
              :value="member.user?.id"
            />
          </el-select>
        </el-form-item>
        <div class="form-row">
          <el-form-item
            label="角色"
            style="flex: 1"
          >
            <el-select
              v-model="skillAssignRole"
              style="width: 100%"
            >
              <el-option
                label="负责人"
                value="owner"
              />
              <el-option
                label="贡献者"
                value="contributor"
              />
              <el-option
                label="审核者"
                value="reviewer"
              />
              <el-option
                label="观察者"
                value="viewer"
              />
            </el-select>
          </el-form-item>
          <el-form-item
            label="熟练度"
            style="flex: 1"
          >
            <el-rate
              v-model="skillAssignProficiency"
              :max="5"
            />
          </el-form-item>
        </div>
      </el-form>
      <div
        v-if="currentSkillAssign?.assignments?.length"
        class="current-assignees"
      >
        <p class="assignees-title">
          当前分配：
        </p>
        <div
          v-for="a in currentSkillAssign.assignments"
          :key="a.id"
          class="assignee-item"
        >
          <span>{{ a.user?.username }}</span>
          <el-tag size="small">
            {{ a.role }}
          </el-tag>
          <el-button
            text
            size="small"
            type="danger"
            @click="handleSkillUnassign(a)"
          >
            <Trash2 class="remove-icon" />
          </el-button>
        </div>
      </div>
      <template #footer>
        <el-button @click="showSkillAssignDialog = false">
          关闭
        </el-button>
        <el-button
          type="primary"
          :loading="isSaving"
          :disabled="!skillAssignUserId"
          @click="handleSkillAssign"
        >
          确认分配
        </el-button>
      </template>
    </el-dialog>

    <!-- Create / Edit Task Dialog -->
    <el-dialog
      v-model="showTaskDialog"
      :title="editingTask ? '编辑任务' : '创建任务'"
      width="550px"
    >
      <el-form
        ref="taskFormRef"
        :model="taskForm"
        label-position="top"
      >
        <el-form-item
          label="任务标题"
          prop="title"
        >
          <el-input
            v-model="taskForm.title"
            placeholder="例如：设计用户认证工作流"
          />
        </el-form-item>
        <el-form-item label="任务描述">
          <el-input
            v-model="taskForm.description"
            type="textarea"
            :rows="3"
            placeholder="详细描述任务内容和目标"
          />
        </el-form-item>
        <div class="form-row">
          <el-form-item
            label="优先级"
            prop="priority"
            style="flex: 1"
          >
            <el-select
              v-model="taskForm.priority"
              style="width: 100%"
            >
              <el-option
                label="紧急"
                value="urgent"
              />
              <el-option
                label="高"
                value="high"
              />
              <el-option
                label="中"
                value="medium"
              />
              <el-option
                label="低"
                value="low"
              />
            </el-select>
          </el-form-item>
          <el-form-item
            label="截止日期"
            style="flex: 1"
          >
            <el-date-picker
              v-model="taskForm.due_date"
              type="datetime"
              placeholder="选择截止时间"
              style="width: 100%"
            />
          </el-form-item>
        </div>
        <div class="form-row">
          <el-form-item
            label="负责人"
            style="flex: 1"
          >
            <el-select
              v-model="taskForm.owner_id"
              placeholder="选择负责人"
              clearable
              style="width: 100%"
            >
              <el-option
                v-for="member in members"
                :key="member.id"
                :label="member.user?.username"
                :value="member.user?.id"
              />
            </el-select>
          </el-form-item>
          <el-form-item
            label="关联技能"
            style="flex: 1"
          >
            <el-select
              v-model="taskForm.linked_skill"
              placeholder="选择技能"
              clearable
              style="width: 100%"
            >
              <el-option
                v-for="skill in skills"
                :key="skill.id"
                :label="skill.name"
                :value="skill.id"
              />
            </el-select>
          </el-form-item>
        </div>
        <el-form-item label="分配成员（可多选）">
          <el-select
            v-model="taskForm.assignee_ids"
            multiple
            placeholder="选择成员"
            style="width: 100%"
          >
            <el-option
              v-for="member in members"
              :key="member.id"
              :label="member.user?.username"
              :value="member.user?.id"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showTaskDialog = false">
          取消
        </el-button>
        <el-button
          type="primary"
          :loading="isSaving"
          @click="handleSaveTask"
        >
          {{ editingTask ? '保存' : '创建' }}
        </el-button>
      </template>
    </el-dialog>

    <!-- Assign Task Dialog -->
    <el-dialog
      v-model="showTaskAssignDialog"
      title="分配任务"
      width="400px"
    >
      <el-form label-position="top">
        <el-form-item label="选择成员">
          <el-select
            v-model="taskAssignUserId"
            placeholder="选择成员"
            style="width: 100%"
          >
            <el-option
              v-for="member in members"
              :key="member.id"
              :label="member.user?.username"
              :value="member.user?.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="角色">
          <el-select
            v-model="taskAssignRole"
            style="width: 100%"
          >
            <el-option
              label="负责人"
              value="owner"
            />
            <el-option
              label="贡献者"
              value="contributor"
            />
            <el-option
              label="审核者"
              value="reviewer"
            />
            <el-option
              label="观察者"
              value="viewer"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showTaskAssignDialog = false">
          关闭
        </el-button>
        <el-button
          type="primary"
          :loading="isSaving"
          :disabled="!taskAssignUserId"
          @click="handleTaskAssignUser"
        >
          确认分配
        </el-button>
      </template>
    </el-dialog>
  </PageShell>
</template>

<script setup>
import PageHeader from '@/components/layout/PageHeader.vue'
import PageShell from '@/components/layout/PageShell.vue'
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useTenantStore } from '@/stores/tenant'
import { useAuthStore } from '@/stores/auth'
import { useAppStore } from '@/stores/app'
import { ragApi } from '@/api/rag'
import { agentApi } from '@/api/agent'
import {
  Plus, Users, Bell, GitBranch, MoreVertical, Edit, Trash2,
  Cpu, Star, UserPlus, User, Calendar, AlertTriangle,
  BookOpen, Bot, Workflow, ArrowRight
} from 'lucide-vue-next'

const router = useRouter()

const tenantStore = useTenantStore()
const authStore = useAuthStore()
const appStore = useAppStore()

// ---- State ----
const showCreateDialog = ref(false)
const showDetailPanel = ref(false)
const showInviteDialog = ref(false)
const showInvitationsDialog = ref(false)
const showSkillDialog = ref(false)
const showSkillAssignDialog = ref(false)
const showTaskDialog = ref(false)
const showTaskAssignDialog = ref(false)

const selectedTenant = ref(null)
const editingTenant = ref(null)
const editingSkill = ref(null)
const editingTask = ref(null)
const currentTaskAssign = ref(null)

const usage = ref(null)
const isLoadingMembers = ref(false)
const isLoadingSkills = ref(false)
const isLoadingTasks = ref(false)
const isLoadingActivities = ref(false)
const isLoadingKnowledge = ref(false)
const isLoadingTeamAgents = ref(false)
const isLoadingCollaborations = ref(false)

const teamCollections = ref([])
const teamAgents = ref([])
const teamCollaborations = ref([])

const formRef = ref(null)
const inviteFormRef = ref(null)
const skillFormRef = ref(null)
const taskFormRef = ref(null)

const detailTab = ref('members')
const skillCategoryFilter = ref('')
const taskStatusFilter = ref('')
const taskPriorityFilter = ref('')

// Forms
const formData = reactive({ name: '', slug: '', description: '', billing_email: '' })
const inviteForm = reactive({ email: '', role: 'member' })

const skillForm = reactive({
  name: '', description: '', category: 'other', mastery_level: 1, instructions: ''
})
const skillKeywordsInput = ref('')
const skillAssignUserId = ref(null)
const skillAssignRole = ref('contributor')
const skillAssignProficiency = ref(3)
const currentSkillAssign = ref(null)

const taskForm = reactive({
  title: '', description: '', priority: 'medium', due_date: null,
  owner_id: null, linked_skill: null, assignee_ids: []
})
const taskAssignUserId = ref(null)
const taskAssignRole = ref('contributor')

const formRules = {
  name: [{ required: true, message: '请输入团队名称', trigger: 'blur' }],
  slug: [
    { required: true, message: '请输入团队标识', trigger: 'blur' },
    { pattern: /^[a-z0-9-]+$/, message: '只能包含小写字母、数字和连字符', trigger: 'blur' }
  ],
  billing_email: [
    { required: true, message: '请输入账单邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入有效的邮箱地址', trigger: 'blur' }
  ]
}

// ---- Computed ----
const tenants = computed(() => tenantStore.tenants)
const members = computed(() => tenantStore.members)
const pendingInvitations = computed(() => tenantStore.pendingInvitations)
const isLoading = computed(() => tenantStore.isLoading)
const isSaving = computed(() => tenantStore.isSaving)
const skills = computed(() => tenantStore.skills)
const tasks = computed(() => tenantStore.tasks)
const activities = computed(() => tenantStore.activities)

// Current user's membership in the selected tenant (for permission checks)
const currentUserMembership = computed(() => {
  if (!selectedTenant.value || !authStore.user) return null
  return members.value.find(m => m.user?.id === authStore.user?.id) || null
})

const filteredSkills = computed(() => {
  if (!skillCategoryFilter.value) return skills.value
  return skills.value.filter(s => s.category === skillCategoryFilter.value)
})

const filteredTasks = computed(() => {
  let result = tasks.value
  if (taskStatusFilter.value) result = result.filter(t => t.status === taskStatusFilter.value)
  if (taskPriorityFilter.value) result = result.filter(t => t.priority === taskPriorityFilter.value)
  return result
})

// ---- Helper Functions ----
function getPlanType(plan) {
  return { free: 'info', starter: '', professional: 'success', enterprise: 'warning' }[plan] || 'info'
}
function getPlanLabel(plan) {
  return { free: '免费版', starter: '入门版', professional: '专业版', enterprise: '企业版' }[plan] || plan
}
function getRoleLabel(role) {
  return { owner: '所有者', admin: '管理员', member: '成员', viewer: '查看者' }[role] || role
}
function getUsagePercentage(current, max) {
  if (!current || !max) return 0
  return Math.min(Math.round((current / max) * 100), 100)
}
function getProgressStatus(percentage) {
  if (percentage >= 90) return 'exception'
  if (percentage >= 70) return 'warning'
  return 'success'
}
function isOwner(tenant) { return tenant.owner?.id === authStore.user?.id }
function isAdmin() {
  if (!currentUserMembership.value) return false
  return ['owner', 'admin'].includes(currentUserMembership.value.role)
}
function canRemoveMember(member) {
  if (member.role === 'owner') return false
  if (!isAdmin()) return false
  return true
}
function getCategoryColor(cat) {
  const colors = {
    workflow: '#3b82f6', agent: '#8b5cf6', data: '#10b981',
    integration: '#f59e0b', monitoring: '#ec4899', prompt: '#06b6d4',
    testing: '#84cc16', deployment: '#f97316', documentation: '#64748b', other: '#6b7280'
  }
  return colors[cat] || colors.other
}
function getCategoryLabel(cat) {
  return {
    workflow: '工作流', agent: 'Agent', data: '数据处理', integration: '集成',
    monitoring: '监控', prompt: '提示词', testing: '测试', deployment: '部署',
    documentation: '文档', other: '其他'
  }[cat] || cat
}
function getTaskStatusType(s) {
  return { todo: 'info', in_progress: 'warning', review: '', done: 'success', blocked: 'danger', cancelled: 'info' }[s] || 'info'
}
function getTaskStatusLabel(s) {
  return { todo: '待处理', in_progress: '进行中', review: '审核中', done: '已完成', blocked: '已阻塞', cancelled: '已取消' }[s] || s
}
function getPriorityType(p) {
  return { urgent: 'danger', high: 'warning', medium: '', low: 'info' }[p] || 'info'
}
function getPriorityLabel(p) {
  return { urgent: '紧急', high: '高', medium: '中', low: '低' }[p] || p
}
function formatDate(d) {
  if (!d) return '-'
  return new Date(d).toLocaleDateString('zh-CN')
}
function formatDateTime(d) {
  if (!d) return '-'
  return new Date(d).toLocaleString('zh-CN')
}

// ---- Tenant Actions ----
function openCreateDialog() {
  editingTenant.value = null
  Object.assign(formData, { name: '', slug: '', description: '', billing_email: '' })
  showCreateDialog.value = true
}

function editTenant(tenant) {
  editingTenant.value = tenant
  Object.assign(formData, {
    name: tenant.name, slug: tenant.slug,
    description: tenant.description, billing_email: tenant.billing_email
  })
  showCreateDialog.value = true
}

async function handleCreate() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  try {
    if (editingTenant.value) {
      const ok = await appStore.prompt('team.edit', { name: editingTenant.value.name })
      if (!ok) return
      await tenantStore.updateTenant(editingTenant.value.id, formData)
      appStore.success('团队已更新')
    } else {
      await tenantStore.createTenant(formData)
      appStore.success('团队已创建')
    }
    showCreateDialog.value = false
    resetForm()
    await tenantStore.fetchTenants()
  } catch (err) {
    appStore.error('操作失败')
  }
}

async function handleDeleteTenant(tenant) {
  const ok = await appStore.prompt('team.delete', { name: tenant.name })
  if (!ok) return
  try {
    await tenantStore.deleteTenant(tenant.id)
    appStore.success('团队已删除')
    if (selectedTenant.value?.id === tenant.id) {
      selectedTenant.value = null
      showDetailPanel.value = false
    }
  } catch (err) {
    appStore.error('删除失败')
  }
}

function resetForm() {
  Object.assign(formData, { name: '', slug: '', description: '', billing_email: '' })
  editingTenant.value = null
}

async function selectTenant(tenant) {
  selectedTenant.value = tenant
  showDetailPanel.value = true
  detailTab.value = 'members'
  isLoadingMembers.value = true
  isLoadingSkills.value = true
  isLoadingTasks.value = true
  isLoadingActivities.value = true
  isLoadingKnowledge.value = true
  isLoadingTeamAgents.value = true
  isLoadingCollaborations.value = true

  try {
    const [usageData] = await Promise.all([
      tenantStore.fetchTenantUsage(tenant.id),
      tenantStore.fetchMembers(tenant.id),
      tenantStore.fetchSkills(tenant.id),
      tenantStore.fetchTasks(tenant.id),
      tenantStore.fetchActivities(tenant.id)
    ])
    usage.value = usageData
  } catch (err) {
    appStore.error('加载失败')
  } finally {
    isLoadingMembers.value = false
    isLoadingSkills.value = false
    isLoadingTasks.value = false
    isLoadingActivities.value = false
  }

  loadTeamKnowledge(tenant.id)
  loadTeamAgents(tenant.id)
  loadTeamCollaborations(tenant.id)
}

// ---- Team Knowledge / Agent / Collaboration (read-only visibility) ----
async function loadTeamKnowledge(tenantId) {
  isLoadingKnowledge.value = true
  try {
    const res = await ragApi.getCollections({ tenant: tenantId })
    teamCollections.value = res?.results || res || []
  } catch (err) {
    appStore.error('加载团队知识库失败')
  } finally {
    isLoadingKnowledge.value = false
  }
}

async function loadTeamAgents(tenantId) {
  isLoadingTeamAgents.value = true
  try {
    const res = await agentApi.getList({ tenant: tenantId })
    teamAgents.value = res?.results || res || []
  } catch (err) {
    appStore.error('加载团队 Agent 失败')
  } finally {
    isLoadingTeamAgents.value = false
  }
}

async function loadTeamCollaborations(tenantId) {
  isLoadingCollaborations.value = true
  try {
    const res = await agentApi.getCollaborationList({ tenant: tenantId })
    teamCollaborations.value = res?.results || res || []
  } catch (err) {
    appStore.error('加载团队协作记录失败')
  } finally {
    isLoadingCollaborations.value = false
  }
}

function goToKnowledge() {
  router.push('/knowledge')
}
function goToAgent(agent) {
  router.push(`/agents/${agent.id}/debug`)
}
function goToCollaborate() {
  router.push('/agents/collaborate')
}

function getCollaborationStatusType(s) {
  return { pending: 'info', running: 'warning', completed: 'success', failed: 'danger' }[s] || 'info'
}
function getCollaborationStatusLabel(s) {
  return { pending: '待处理', running: '进行中', completed: '已完成', failed: '失败' }[s] || s
}

// ---- Member Actions ----
async function handleRoleChange(member) {
  if (member.role === 'owner') return
  try {
    await tenantStore.updateMemberRole(member.id, member.role)
    appStore.success('角色变更已保存')
  } catch (err) {
    appStore.error('变更失败')
  }
}

async function handleInvite() {
  if (!selectedTenant.value) return
  const valid = await inviteFormRef.value?.validate().catch(() => false)
  if (!valid) return

  try {
    await tenantStore.inviteMember(selectedTenant.value.id, inviteForm)
    appStore.success('邀请已发送')
    showInviteDialog.value = false
    resetInviteForm()
  } catch (err) {
    appStore.error('邀请失败：' + (err.message || '未知错误'))
  }
}

async function handleRemoveMember(member) {
  const ok = await appStore.prompt('member.remove', { username: member.user?.username })
  if (!ok) return
  try {
    await tenantStore.removeMember(selectedTenant.value.id, member.id)
    appStore.success('成员已移除')
    members.value = members.value.filter(m => m.id !== member.id)
  } catch (err) {
    appStore.error('移除失败')
  }
}

function resetInviteForm() {
  Object.assign(inviteForm, { email: '', role: 'member' })
}

async function handleAccept(inv) {
  try {
    await tenantStore.acceptInvitation(inv.id)
    appStore.success('已加入团队')
    await tenantStore.fetchTenants()
  } catch (err) {
    appStore.error('操作失败')
  }
}

async function handleDecline(inv) {
  try {
    await tenantStore.declineInvitation(inv.id)
    appStore.success('已拒绝邀请')
  } catch (err) {
    appStore.error('操作失败')
  }
}

// ---- Skill Actions ----
function openSkillCreateDialog() {
  editingSkill.value = null
  Object.assign(skillForm, { name: '', description: '', category: 'other', mastery_level: 1, instructions: '' })
  skillKeywordsInput.value = ''
  showSkillDialog.value = true
}

function openSkillEditDialog(skill) {
  editingSkill.value = skill
  Object.assign(skillForm, {
    name: skill.name, description: skill.description,
    category: skill.category, mastery_level: skill.mastery_level,
    instructions: skill.instructions || ''
  })
  skillKeywordsInput.value = (skill.keywords || []).join(', ')
  showSkillDialog.value = true
}

async function handleSaveSkill() {
  if (!selectedTenant.value || !skillForm.name) return
  try {
    const keywords = skillKeywordsInput.value.split(',').map(k => k.trim()).filter(Boolean)
    const data = { ...skillForm, keywords }

    if (editingSkill.value) {
      await tenantStore.updateSkill(editingSkill.value.id, data)
      appStore.success('技能已更新')
    } else {
      await tenantStore.createSkill(selectedTenant.value.id, data)
      appStore.success('技能已创建')
    }
    showSkillDialog.value = false
    editingSkill.value = null
    await tenantStore.fetchSkills(selectedTenant.value.id)
  } catch (err) {
    appStore.error('操作失败')
  }
}

async function handleDeleteSkill(skill) {
  const ok = await appStore.prompt('skill.delete', { name: skill.name })
  if (!ok) return
  try {
    await tenantStore.deleteSkill(skill.id)
    appStore.success('技能已删除')
  } catch (err) {
    appStore.error('删除失败')
  }
}

function openSkillAssignDialog(skill) {
  currentSkillAssign.value = skill
  skillAssignUserId.value = null
  skillAssignRole.value = 'contributor'
  skillAssignProficiency.value = 3
  showSkillAssignDialog.value = true
}

async function handleSkillAssign() {
  if (!currentSkillAssign.value || !skillAssignUserId.value) return
  try {
    await tenantStore.assignSkill(currentSkillAssign.value.id, {
      user_id: skillAssignUserId.value,
      role: skillAssignRole.value,
      proficiency_level: skillAssignProficiency.value
    })
    appStore.success('技能已分配')
    skillAssignUserId.value = null
    await tenantStore.fetchSkills(selectedTenant.value.id)
    await tenantStore.fetchActivities(selectedTenant.value.id)
  } catch (err) {
    appStore.error('分配失败')
  }
}

async function handleSkillUnassign(assignment) {
  if (!currentSkillAssign.value) return
  try {
    await tenantStore.unassignSkill(currentSkillAssign.value.id, { user_id: assignment.user?.id })
    appStore.success('已移除分配')
    await tenantStore.fetchSkills(selectedTenant.value.id)
    await tenantStore.fetchActivities(selectedTenant.value.id)
  } catch (err) {
    appStore.error('移除失败')
  }
}

// ---- Task Actions ----
function openTaskCreateDialog() {
  editingTask.value = null
  Object.assign(taskForm, {
    title: '', description: '', priority: 'medium',
    due_date: null, owner_id: null, linked_skill: null, assignee_ids: []
  })
  showTaskDialog.value = true
}

function openTaskEditDialog(task) {
  editingTask.value = task
  Object.assign(taskForm, {
    title: task.title, description: task.description,
    priority: task.priority, due_date: task.due_date,
    owner_id: task.owner?.id, linked_skill: task.linked_skill?.id,
    assignee_ids: (task.task_assignees || []).map(a => a.user?.id).filter(Boolean)
  })
  showTaskDialog.value = true
}

async function handleSaveTask() {
  if (!selectedTenant.value || !taskForm.title) return
  try {
    const data = { ...taskForm }
    if (data.due_date) data.due_date = new Date(data.due_date).toISOString()

    if (editingTask.value) {
      await tenantStore.updateTask(editingTask.value.id, data)
      appStore.success('任务已更新')
    } else {
      await tenantStore.createTask(selectedTenant.value.id, data)
      appStore.success('任务已创建')
    }
    showTaskDialog.value = false
    editingTask.value = null
    await tenantStore.fetchTasks(selectedTenant.value.id)
    await tenantStore.fetchActivities(selectedTenant.value.id)
  } catch (err) {
    appStore.error('操作失败')
  }
}

async function handleDeleteTask(task) {
  const ok = await appStore.prompt('task.delete', { title: task.title })
  if (!ok) return
  try {
    await tenantStore.deleteTask(task.id)
    appStore.success('任务已删除')
  } catch (err) {
    appStore.error('删除失败')
  }
}

async function handleTaskStatusChange(task) {
  const oldStatus = task.status
  try {
    await tenantStore.changeTaskStatus(task.id, task.status)
    if (task.status === 'done') appStore.success('任务已完成')
    await tenantStore.fetchActivities(selectedTenant.value.id)
  } catch (err) {
    task.status = oldStatus
    appStore.error('状态变更失败')
  }
}

function openTaskAssignDialog(task) {
  currentTaskAssign.value = task
  taskAssignUserId.value = null
  taskAssignRole.value = 'contributor'
  showTaskAssignDialog.value = true
}

async function handleTaskAssignUser() {
  if (!currentTaskAssign.value || !taskAssignUserId.value) return
  try {
    await tenantStore.assignTaskUser(currentTaskAssign.value.id, {
      user_id: taskAssignUserId.value, role: taskAssignRole.value
    })
    appStore.success('任务已分配')
    taskAssignUserId.value = null
    await tenantStore.fetchTasks(selectedTenant.value.id)
    await tenantStore.fetchActivities(selectedTenant.value.id)
  } catch (err) {
    appStore.error('分配失败')
  }
}

// ---- Init ----
onMounted(async () => {
  await tenantStore.fetchTenants()
  await tenantStore.fetchPendingInvitations()
})
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.btn-icon { width: 16px; height: 16px; }
.btn-icon-sm { width: 14px; height: 14px; }

.invitations-banner {
  display: flex; justify-content: space-between; align-items: center;
  padding: $spacing-4; background: rgba($color-warning, 0.1);
  border: 1px solid rgba($color-warning, 0.3); border-radius: $radius-lg;
  margin-bottom: var(--page-section-gap);
  .banner-content { display: flex; align-items: center; gap: $spacing-3; color: $color-warning; }
  .banner-icon { width: 20px; height: 20px; }
}

.tenants-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(min(100%, var(--content-card-min-width)), 1fr)); gap: $spacing-4;
}
.tenant-card {
  background: var(--bg-secondary); border: 1px solid var(--border-primary);
  border-radius: var(--content-card-radius); padding: var(--content-card-padding); cursor: pointer;
  transition: all $transition-fast;
  &:hover { border-color: $color-primary; }
  &.active { border-color: $color-primary; box-shadow: 0 0 0 2px rgba($color-primary, 0.2); }
}
.card-header { display: flex; align-items: center; gap: $spacing-3; margin-bottom: $spacing-3; }
.tenant-avatar {
  width: 48px; height: 48px; border-radius: $radius-lg;
  background: linear-gradient(135deg, $color-primary, $color-secondary);
  color: $color-white; display: flex; align-items: center;
  justify-content: center; font-size: $font-size-xl; font-weight: $font-weight-bold;
}
.tenant-info { flex: 1; .tenant-name { font-size: $font-size-base; font-weight: $font-weight-semibold; margin: 0 0 $spacing-1; } }
.tenant-desc { font-size: $font-size-sm; color: var(--text-secondary); margin: 0 0 $spacing-3; }
.tenant-stats { display: flex; gap: $spacing-4; font-size: $font-size-sm; color: var(--text-tertiary);
  .stat { display: flex; align-items: center; gap: $spacing-1; } .stat-icon { width: 14px; height: 14px; }
}

.empty-state {
  text-align: center; padding: $spacing-12;
  .empty-icon { width: 64px; height: 64px; color: var(--text-tertiary); margin-bottom: $spacing-4; }
  h3 { margin: 0 0 $spacing-2; } p { color: var(--text-secondary); margin: 0 0 $spacing-4; }
}

.tenant-detail { height: 100%; }

.detail-tabs { height: 100%; }
:deep(.el-tabs__content) { overflow-y: auto; max-height: calc(100vh - 220px); padding-right: $spacing-2; }

.section-header {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: $spacing-4;
  h4 { font-size: $font-size-sm; font-weight: $font-weight-semibold; margin: 0; color: var(--text-secondary); }
}

.loading { padding: $spacing-4 0; }
.empty-tab { text-align: center; padding: $spacing-8; color: var(--text-secondary); font-size: $font-size-sm; }

// Members
.members-list { display: flex; flex-direction: column; gap: $spacing-2; }
.member-item {
  display: flex; align-items: center; gap: $spacing-3;
  padding: $spacing-3; background: var(--bg-tertiary); border-radius: $radius-md;
}
.member-avatar {
  width: 36px; height: 36px; border-radius: 50%; background: $color-primary;
  color: $color-white; display: flex; align-items: center; justify-content: center;
  font-size: $font-size-sm; font-weight: $font-weight-semibold; flex-shrink: 0;
}
.member-info { flex: 1; min-width: 0;
  .member-name { display: block; font-size: $font-size-sm; font-weight: $font-weight-medium; }
  .member-email { font-size: $font-size-xs; color: var(--text-tertiary); }
}
.remove-icon { width: 14px; height: 14px; }

// Team Knowledge / Agents (shared resource cards)
.resource-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(min(100%, var(--content-card-min-width)), 1fr)); gap: $spacing-4; }
.resource-card {
  display: flex; gap: $spacing-3; background: var(--bg-tertiary);
  border: 1px solid var(--border-primary); border-radius: $radius-lg; padding: $spacing-4;
  transition: all $transition-fast;
  &.clickable { cursor: pointer; &:hover { border-color: $color-primary; } }
}
.resource-icon {
  width: 40px; height: 40px; border-radius: $radius-md; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  &.kb-icon { background: linear-gradient(135deg, #06b6d4, #3b82f6); }
  &.agent-icon { background: linear-gradient(135deg, #8b5cf6, #ec4899); }
  .resource-icon-inner { width: 20px; height: 20px; color: white; }
}
.resource-info { flex: 1; min-width: 0;
  h5 { margin: 0 0 $spacing-1; font-size: $font-size-sm; font-weight: $font-weight-semibold; }
}
.resource-desc {
  font-size: $font-size-xs; color: var(--text-secondary); margin: 0 0 $spacing-2;
  overflow: hidden; text-overflow: ellipsis; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;
}
.resource-meta { display: flex; gap: $spacing-3; font-size: $font-size-xs; color: var(--text-tertiary); flex-wrap: wrap; }

// AI Collaboration Records
.collaborations-list { display: flex; flex-direction: column; gap: $spacing-2; }
.collaboration-item {
  display: flex; align-items: center; gap: $spacing-3; padding: $spacing-3;
  background: var(--bg-tertiary); border: 1px solid var(--border-primary); border-radius: $radius-lg;
}
.collab-icon {
  width: 36px; height: 36px; border-radius: $radius-md; flex-shrink: 0;
  background: linear-gradient(135deg, #f59e0b, #ef4444);
  display: flex; align-items: center; justify-content: center;
  .collab-icon-inner { width: 18px; height: 18px; color: white; }
}
.collab-content { flex: 1; min-width: 0;
  .collab-task {
    margin: 0 0 $spacing-1; font-size: $font-size-sm; color: var(--text-primary);
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  }
}
.collab-meta { display: flex; gap: $spacing-3; font-size: $font-size-xs; color: var(--text-tertiary); }

// Skills
.skills-filter { margin-bottom: $spacing-4; }
.skills-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(min(100%, var(--content-card-min-width)), 1fr)); gap: $spacing-4; }
.skill-card {
  background: var(--bg-tertiary); border: 1px solid var(--border-primary);
  border-radius: $radius-lg; padding: $spacing-4; transition: all $transition-fast;
  &:hover { border-color: $color-primary; }
}
.skill-header { display: flex; align-items: center; gap: $spacing-3; margin-bottom: $spacing-2; }
.skill-icon {
  width: 40px; height: 40px; border-radius: $radius-md;
  display: flex; align-items: center; justify-content: center; flex-shrink: 0;
  .skill-icon-inner { width: 20px; height: 20px; color: white; }
}
.skill-info { flex: 1; h5 { margin: 0 0 $spacing-1; font-size: $font-size-sm; font-weight: $font-weight-semibold; } }
.skill-desc { font-size: $font-size-xs; color: var(--text-secondary); margin: 0 0 $spacing-3; line-height: $line-height-relaxed; }
.skill-meta { display: flex; gap: $spacing-3; margin-bottom: $spacing-2; }
.meta-item { display: flex; align-items: center; gap: 4px; font-size: $font-size-xs; color: var(--text-secondary); }
.meta-icon { width: 12px; height: 12px; }
.skill-keywords { display: flex; flex-wrap: wrap; gap: $spacing-1; }

// Tasks
.tasks-filter { display: flex; gap: $spacing-3; margin-bottom: $spacing-4; }
.tasks-list { display: flex; flex-direction: column; gap: $spacing-2; }
.task-item {
  display: flex; align-items: stretch; gap: $spacing-3;
  background: var(--bg-tertiary); border: 1px solid var(--border-primary);
  border-radius: $radius-lg; overflow: hidden; transition: all $transition-fast;
  &:hover { border-color: $color-primary; }
  &.task-done { opacity: 0.7; }
}
.task-priority-indicator { width: 4px; flex-shrink: 0;
  &.priority-urgent { background: var(--error); }
  &.priority-high { background: var(--warning); }
  &.priority-medium { background: var(--primary); }
  &.priority-low { background: var(--text-tertiary); }
}
.task-content { flex: 1; padding: $spacing-3 $spacing-3 $spacing-3 0; min-width: 0; }
.task-header { display: flex; align-items: center; justify-content: space-between; gap: $spacing-2; margin-bottom: $spacing-1; }
.task-title { font-size: $font-size-sm; font-weight: $font-weight-medium; &.task-overdue { color: var(--error); } }
.task-tags { display: flex; gap: $spacing-1; flex-shrink: 0; }
.task-meta { display: flex; align-items: center; gap: $spacing-3; font-size: $font-size-xs; color: var(--text-secondary); }
.meta-icon-sm { width: 12px; height: 12px; }
.overdue-label { color: var(--error); display: flex; align-items: center; gap: 2px; }
.task-actions { display: flex; align-items: center; gap: $spacing-2; padding: $spacing-3; flex-shrink: 0; }

// Usage
.usage-grid { display: flex; flex-direction: column; gap: var(--content-gap); }
.usage-item {
  .usage-label { font-size: $font-size-sm; color: var(--text-secondary); margin-bottom: $spacing-2; display: block; }
  .usage-value { font-size: $font-size-xs; color: var(--text-tertiary); margin-top: $spacing-1; display: block; }
}

// Activity
.activity-list { display: flex; flex-direction: column; gap: 0; }
.activity-item { display: flex; gap: $spacing-3; padding: $spacing-3 0; position: relative;
  &:not(:last-child)::after { content: ''; position: absolute; left: 5px; top: 24px; bottom: 0; width: 1px; background: var(--border-primary); }
}
.activity-dot { width: 10px; height: 10px; border-radius: 50%; background: var(--primary); flex-shrink: 0; margin-top: 4px;
  &.activity-skill_created { background: var(--success); }
  &.activity-skill_assigned { background: var(--primary); }
  &.activity-task_created { background: var(--warning); }
  &.activity-task_completed { background: var(--success); }
  &.activity-member_joined { background: var(--info); }
}
.activity-content { flex: 1; }
.activity-desc { margin: 0 0 $spacing-1; font-size: $font-size-sm; color: var(--text-primary); }
.activity-time { font-size: $font-size-xs; color: var(--text-tertiary); }

// Shared
.menu-icon { width: 14px; height: 14px; margin-right: $spacing-2; }
.danger-item { color: var(--error) !important; }
.form-row { display: flex; gap: $spacing-4; }

// Skill assign dialog
.current-assignees { margin-top: $spacing-4; padding-top: $spacing-4; border-top: 1px solid var(--border-primary); }
.assignees-title { font-size: $font-size-xs; color: var(--text-secondary); margin: 0 0 $spacing-2; }
.assignee-item { display: flex; align-items: center; gap: $spacing-2; margin-bottom: $spacing-2; font-size: $font-size-sm; }

// Invitations
.invitations-list { display: flex; flex-direction: column; gap: $spacing-3; }
.invitation-item { display: flex; justify-content: space-between; align-items: center; padding: $spacing-3; background: var(--bg-tertiary); border-radius: $radius-md;
  .inv-info { .inv-tenant { display: block; font-weight: $font-weight-medium; }
    .inv-role { font-size: $font-size-xs; color: var(--text-tertiary); }
  }
  .inv-actions { display: flex; gap: $spacing-2; }
}
</style>
