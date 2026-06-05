<template>
  <div class="workspace-manager">
    <!-- Header -->
    <div class="manager-header">
      <h2>团队工作空间</h2>
      <el-button
        type="primary"
        @click="showCreateDialog = true"
      >
        <Plus class="btn-icon" />
        创建工作空间
      </el-button>
    </div>

    <!-- Workspace List -->
    <div class="workspace-grid">
      <div
        v-for="workspace in workspaces"
        :key="workspace.id"
        class="workspace-card"
        :class="{ active: currentWorkspace?.id === workspace.id }"
        @click="selectWorkspace(workspace)"
      >
        <div class="card-header">
          <div
            class="workspace-avatar"
            :style="{ backgroundColor: workspace.color || '#3b82f6' }"
          >
            {{ workspace.name.charAt(0).toUpperCase() }}
          </div>
          <el-dropdown
            trigger="click"
            @command="(cmd) => handleCommand(cmd, workspace)"
          >
            <el-button
              size="small"
              text
              @click.stop
            >
              <MoreVertical class="menu-icon" />
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="settings">
                  设置
                </el-dropdown-item>
                <el-dropdown-item command="invite">
                  邀请成员
                </el-dropdown-item>
                <el-dropdown-item command="duplicate">
                  复制
                </el-dropdown-item>
                <el-dropdown-item
                  command="delete"
                  divided
                >
                  删除
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>

        <div class="card-body">
          <h3>{{ workspace.name }}</h3>
          <p v-if="workspace.description">
            {{ workspace.description }}
          </p>
          <div class="workspace-stats">
            <span class="stat">
              <Users class="stat-icon" />
              {{ workspace.member_count || 1 }} 成员
            </span>
            <span class="stat">
              <Layers class="stat-icon" />
              {{ workspace.workflow_count || 0 }} 工作流
            </span>
          </div>
        </div>

        <div class="card-footer">
          <el-tag
            :type="getPlanType(workspace.plan)"
            size="small"
          >
            {{ getPlanLabel(workspace.plan) }}
          </el-tag>
          <span
            v-if="workspace.my_role"
            class="role-badge"
          >
            {{ getRoleLabel(workspace.my_role) }}
          </span>
        </div>
      </div>

      <!-- Create Workspace Card -->
      <div
        class="workspace-card create-card"
        @click="showCreateDialog = true"
      >
        <Plus class="create-icon" />
        <span>创建新工作空间</span>
      </div>
    </div>

    <!-- Workspace Detail -->
    <div
      v-if="currentWorkspace"
      class="workspace-detail"
    >
      <el-tabs v-model="activeTab">
        <!-- Members Tab -->
        <el-tab-pane
          label="成员"
          name="members"
        >
          <div class="tab-header">
            <h3>成员管理</h3>
            <el-button
              type="primary"
              size="small"
              @click="showInviteDialog = true"
            >
              <UserPlus class="btn-icon" />
              邀请成员
            </el-button>
          </div>

          <el-table
            :data="members"
            class="members-table"
          >
            <el-table-column
              label="成员"
              min-width="200"
            >
              <template #default="{ row }">
                <div class="member-cell">
                  <el-avatar
                    :size="36"
                    :src="row.user.avatar"
                  >
                    {{ row.user.username.charAt(0) }}
                  </el-avatar>
                  <div class="member-info">
                    <span class="name">{{ row.user.username }}</span>
                    <span class="email">{{ row.user.email }}</span>
                  </div>
                </div>
              </template>
            </el-table-column>
            <el-table-column
              label="角色"
              width="150"
            >
              <template #default="{ row }">
                <el-select
                  v-model="row.role"
                  size="small"
                  :disabled="row.is_owner || !canManageMembers"
                  @change="updateMemberRole(row)"
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
                    label="编辑"
                    value="editor"
                  />
                  <el-option
                    label="查看"
                    value="viewer"
                  />
                </el-select>
              </template>
            </el-table-column>
            <el-table-column
              label="状态"
              width="100"
            >
              <template #default="{ row }">
                <el-tag
                  :type="getStatusType(row.status)"
                  size="small"
                >
                  {{ getStatusLabel(row.status) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column
              v-if="canManageMembers"
              label="操作"
              width="100"
            >
              <template #default="{ row }">
                <el-button
                  v-if="row.role !== 'owner' && row.status === 'active'"
                  type="danger"
                  size="small"
                  text
                  @click="removeMember(row)"
                >
                  移除
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <!-- Folders Tab -->
        <el-tab-pane
          label="文件夹"
          name="folders"
        >
          <div class="tab-header">
            <h3>文件夹</h3>
            <el-button
              type="primary"
              size="small"
              @click="showFolderDialog = true"
            >
              <FolderPlus class="btn-icon" />
              新建文件夹
            </el-button>
          </div>

          <div class="folder-tree">
            <div
              v-for="folder in folders"
              :key="folder.id"
              class="folder-item"
              :style="{ paddingLeft: `${folder.level * 20 + 12}px` }"
            >
              <Folder
                class="folder-icon"
                :style="{ color: folder.color }"
              />
              <span class="folder-name">{{ folder.name }}</span>
              <span class="folder-count">{{ folder.workflow_count }} 个工作流</span>
              <el-dropdown
                v-if="canEdit"
                trigger="click"
              >
                <el-button
                  size="small"
                  text
                >
                  <MoreVertical class="menu-icon" />
                </el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item @click="editFolder(folder)">
                      编辑
                    </el-dropdown-item>
                    <el-dropdown-item @click="moveFolder(folder)">
                      移动
                    </el-dropdown-item>
                    <el-dropdown-item command="delete">
                      删除
                    </el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>
            <div
              v-if="folders.length === 0"
              class="empty-folders"
            >
              <FolderOpen class="empty-icon" />
              <p>暂无文件夹</p>
            </div>
          </div>
        </el-tab-pane>

        <!-- Activity Tab -->
        <el-tab-pane
          label="活动"
          name="activity"
        >
          <div class="activity-list">
            <div
              v-for="activity in activities"
              :key="activity.id"
              class="activity-item"
            >
              <el-avatar
                :size="32"
                :src="activity.user.avatar"
              >
                {{ activity.user.username?.charAt(0) }}
              </el-avatar>
              <div class="activity-content">
                <p>
                  <strong>{{ activity.user.username }}</strong>
                  {{ activity.action_description }}
                </p>
                <span class="activity-time">{{ formatTime(activity.created_at) }}</span>
              </div>
            </div>
            <div
              v-if="activities.length === 0"
              class="empty-activity"
            >
              <Activity class="empty-icon" />
              <p>暂无活动记录</p>
            </div>
          </div>
        </el-tab-pane>

        <!-- Settings Tab -->
        <el-tab-pane
          v-if="canManage"
          label="设置"
          name="settings"
        >
          <div class="settings-form">
            <div class="form-section">
              <h4>基本信息</h4>
              <el-form label-width="120px">
                <el-form-item label="名称">
                  <el-input v-model="currentWorkspace.name" />
                </el-form-item>
                <el-form-item label="描述">
                  <el-input
                    v-model="currentWorkspace.description"
                    type="textarea"
                  />
                </el-form-item>
                <el-form-item label="颜色">
                  <el-color-picker v-model="currentWorkspace.color" />
                </el-form-item>
              </el-form>
            </div>

            <el-divider />

            <div class="form-section">
              <h4>成员设置</h4>
              <el-form label-width="120px">
                <el-form-item label="最大成员数">
                  <el-input-number
                    v-model="currentWorkspace.max_members"
                    :min="1"
                    :max="100"
                  />
                </el-form-item>
                <el-form-item label="允许访客访问">
                  <el-switch v-model="currentWorkspace.allow_guest_access" />
                </el-form-item>
              </el-form>
            </div>

            <el-divider />

            <div class="form-section danger-zone">
              <h4>危险区域</h4>
              <el-button
                type="danger"
                @click="deleteWorkspace"
              >
                删除工作空间
              </el-button>
              <p>删除后，所有数据将无法恢复。</p>
            </div>
          </div>
        </el-tab-pane>
      </el-tabs>
    </div>

    <!-- Create Workspace Dialog -->
    <el-dialog
      v-model="showCreateDialog"
      title="创建工作空间"
      width="500px"
    >
      <el-form label-width="100px">
        <el-form-item
          label="名称"
          required
        >
          <el-input
            v-model="newWorkspace.name"
            placeholder="工作空间名称"
          />
        </el-form-item>
        <el-form-item label="描述">
          <el-input
            v-model="newWorkspace.description"
            type="textarea"
            placeholder="描述（可选）"
          />
        </el-form-item>
        <el-form-item label="类型">
          <el-select v-model="newWorkspace.workspace_type">
            <el-option
              label="团队"
              value="team"
            />
            <el-option
              label="组织"
              value="organization"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="套餐">
          <el-select v-model="newWorkspace.plan">
            <el-option
              label="免费"
              value="free"
            />
            <el-option
              label="专业版"
              value="pro"
            />
            <el-option
              label="企业版"
              value="enterprise"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">
          取消
        </el-button>
        <el-button
          type="primary"
          @click="createWorkspace"
        >
          创建
        </el-button>
      </template>
    </el-dialog>

    <!-- Invite Dialog -->
    <el-dialog
      v-model="showInviteDialog"
      title="邀请成员"
      width="500px"
    >
      <el-form label-width="100px">
        <el-form-item
          label="邮箱"
          required
        >
          <el-input
            v-model="inviteEmail"
            placeholder="member@example.com"
          />
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="inviteRole">
            <el-option
              label="管理员"
              value="admin"
            />
            <el-option
              label="编辑"
              value="editor"
            />
            <el-option
              label="查看"
              value="viewer"
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
          @click="sendInvite"
        >
          发送邀请
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import {
  Plus, MoreVertical, Users, Layers, UserPlus, FolderPlus,
  Folder, FolderOpen, Activity
} from 'lucide-vue-next'

const workspaces = ref([])
const currentWorkspace = ref(null)
const members = ref([])
const folders = ref([])
const activities = ref([])
const activeTab = ref('members')

const showCreateDialog = ref(false)
const showInviteDialog = ref(false)
const showFolderDialog = ref(false)

const newWorkspace = ref({
  name: '',
  description: '',
  workspace_type: 'team',
  plan: 'free'
})

const inviteEmail = ref('')
const inviteRole = ref('editor')

const canManage = computed(() => {
  return currentWorkspace.value?.my_role === 'owner' || currentWorkspace.value?.my_role === 'admin'
})

const canManageMembers = computed(() => canManage.value)
const canEdit = computed(() => {
  return currentWorkspace.value?.my_role !== 'viewer'
})

const getPlanType = (plan) => {
  const types = { free: 'info', pro: 'success', enterprise: 'warning' }
  return types[plan] || 'info'
}

const getPlanLabel = (plan) => {
  const labels = { free: '免费', pro: '专业版', enterprise: '企业版' }
  return labels[plan] || plan
}

const getRoleLabel = (role) => {
  const labels = { owner: '所有者', admin: '管理员', editor: '编辑', viewer: '查看' }
  return labels[role] || role
}

const getStatusType = (status) => {
  const types = { active: 'success', invited: 'warning', pending: 'info', removed: 'danger' }
  return types[status] || 'info'
}

const getStatusLabel = (status) => {
  const labels = { active: '活跃', invited: '已邀请', pending: '待确认', removed: '已移除' }
  return labels[status] || status
}

const formatTime = (timestamp) => {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  const now = new Date()
  const diff = now - date

  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return `${Math.floor(diff / 60000)} 分钟前`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)} 小时前`
  if (diff < 604800000) return `${Math.floor(diff / 86400000)} 天前`

  return date.toLocaleDateString('zh-CN')
}

const selectWorkspace = (workspace) => {
  currentWorkspace.value = workspace
  fetchMembers(workspace.id)
  fetchFolders(workspace.id)
  fetchActivities(workspace.id)
}

const fetchMembers = async (workspaceId) => {
  members.value = [
    {
      id: 1,
      user: { username: 'Admin', email: 'admin@example.com', avatar: '' },
      role: 'owner',
      status: 'active',
      is_owner: true
    },
    {
      id: 2,
      user: { username: 'Editor User', email: 'editor@example.com', avatar: '' },
      role: 'editor',
      status: 'active',
      is_owner: false
    }
  ]
}

const fetchFolders = async (workspaceId) => {
  folders.value = [
    { id: 1, name: '生产环境', color: '#10b981', level: 0, workflow_count: 5 },
    { id: 2, name: '开发测试', color: '#f59e0b', level: 0, workflow_count: 3 },
    { id: 3, name: '数据处理', color: '#3b82f6', level: 1, workflow_count: 2 }
  ]
}

const fetchActivities = async (workspaceId) => {
  activities.value = [
    {
      id: 1,
      user: { username: 'Admin', avatar: '' },
      action_description: '创建了工作空间',
      created_at: new Date(Date.now() - 86400000).toISOString()
    },
    {
      id: 2,
      user: { username: 'Editor User', avatar: '' },
      action_description: '编辑了工作流「数据同步」',
      created_at: new Date(Date.now() - 3600000).toISOString()
    }
  ]
}

const createWorkspace = async () => {
  if (!newWorkspace.value.name) return
  // Mock creation
  workspaces.value.push({
    id: Date.now(),
    ...newWorkspace.value,
    member_count: 1,
    workflow_count: 0,
    my_role: 'owner'
  })
  showCreateDialog.value = false
  newWorkspace.value = { name: '', description: '', workspace_type: 'team', plan: 'free' }
}

const sendInvite = async () => {
  if (!inviteEmail.value) return
  // Mock invite
  members.value.push({
    id: Date.now(),
    user: { username: inviteEmail.value, email: inviteEmail.value, avatar: '' },
    role: inviteRole.value,
    status: 'invited',
    is_owner: false
  })
  showInviteDialog.value = false
  inviteEmail.value = ''
}

const updateMemberRole = async (member) => {
  // TODO: implement role update via API
}

const removeMember = async (member) => {
  members.value = members.value.filter(m => m.id !== member.id)
}

const handleCommand = (command, workspace) => {
  switch (command) {
    case 'settings':
      currentWorkspace.value = workspace
      activeTab.value = 'settings'
      break
    case 'invite':
      selectWorkspace(workspace)
      showInviteDialog.value = true
      break
    case 'delete':
      workspaces.value = workspaces.value.filter(w => w.id !== workspace.id)
      if (currentWorkspace.value?.id === workspace.id) {
        currentWorkspace.value = null
      }
      break
  }
}

const deleteWorkspace = () => {
  workspaces.value = workspaces.value.filter(w => w.id !== currentWorkspace.value?.id)
  currentWorkspace.value = null
}

onMounted(() => {
  // Mock initial data
  workspaces.value = [
    {
      id: 1,
      name: '我的团队',
      description: '团队协作工作空间',
      workspace_type: 'team',
      plan: 'pro',
      member_count: 3,
      workflow_count: 12,
      my_role: 'owner',
      color: '#3b82f6'
    }
  ]
})
</script>

<style lang="scss" scoped>
.workspace-manager {
  padding: 24px;
}

.manager-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;

  h2 {
    margin: 0;
    font-size: 24px;
    font-weight: 600;
  }
}

.workspace-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 20px;
  margin-bottom: 32px;
}

.workspace-card {
  background: var(--el-bg-color);
  border: 1px solid var(--el-border-color);
  border-radius: 12px;
  padding: 20px;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    border-color: var(--el-color-primary);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  }

  &.active {
    border-color: var(--el-color-primary);
    background: var(--el-color-primary-light-9);
  }

  &.create-card {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    min-height: 180px;
    border-style: dashed;
    color: var(--el-text-color-secondary);

    &:hover {
      color: var(--el-color-primary);
      border-color: var(--el-color-primary);
    }

    .create-icon {
      width: 32px;
      height: 32px;
      margin-bottom: 8px;
    }
  }

  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 16px;

    .workspace-avatar {
      width: 48px;
      height: 48px;
      border-radius: 12px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 20px;
      font-weight: 700;
      color: white;
    }

    .menu-icon {
      width: 16px;
      height: 16px;
    }
  }

  .card-body {
    margin-bottom: 16px;

    h3 {
      margin: 0 0 4px;
      font-size: 16px;
      font-weight: 600;
    }

    p {
      margin: 0 0 12px;
      font-size: 14px;
      color: var(--el-text-color-secondary);
    }

    .workspace-stats {
      display: flex;
      gap: 16px;

      .stat {
        display: flex;
        align-items: center;
        gap: 4px;
        font-size: 13px;
        color: var(--el-text-color-secondary);

        .stat-icon {
          width: 14px;
          height: 14px;
        }
      }
    }
  }

  .card-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;

    .role-badge {
      font-size: 12px;
      color: var(--el-text-color-secondary);
    }
  }
}

.workspace-detail {
  background: var(--el-bg-color);
  border: 1px solid var(--el-border-color);
  border-radius: 12px;
  padding: 24px;
}

.tab-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;

  h3 {
    margin: 0;
    font-size: 18px;
    font-weight: 600;
  }
}

.btn-icon {
  width: 16px;
  height: 16px;
}

.members-table {
  .member-cell {
    display: flex;
    align-items: center;
    gap: 12px;

    .member-info {
      display: flex;
      flex-direction: column;

      .name {
        font-weight: 500;
      }

      .email {
        font-size: 12px;
        color: var(--el-text-color-secondary);
      }
    }
  }
}

.folder-tree {
  .folder-item {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 12px;
    border-radius: 8px;
    cursor: pointer;

    &:hover {
      background: var(--el-fill-color-light);
    }

    .folder-icon {
      width: 20px;
      height: 20px;
    }

    .folder-name {
      flex: 1;
      font-weight: 500;
    }

    .folder-count {
      font-size: 13px;
      color: var(--el-text-color-secondary);
    }

    .menu-icon {
      width: 16px;
      height: 16px;
      opacity: 0;
      transition: opacity 0.2s;
    }

    &:hover .menu-icon {
      opacity: 1;
    }
  }

  .empty-folders,
  .empty-activity {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 40px;
    color: var(--el-text-color-secondary);

    .empty-icon {
      width: 48px;
      height: 48px;
      margin-bottom: 12px;
      opacity: 0.5;
    }
  }
}

.activity-list {
  .activity-item {
    display: flex;
    gap: 12px;
    padding: 12px 0;
    border-bottom: 1px solid var(--el-border-color-lighter);

    &:last-child {
      border-bottom: none;
    }

    .activity-content {
      flex: 1;

      p {
        margin: 0 0 4px;

        strong {
          margin-right: 4px;
        }
      }

      .activity-time {
        font-size: 12px;
        color: var(--el-text-color-secondary);
      }
    }
  }
}

.settings-form {
  .form-section {
    margin-bottom: 24px;

    h4 {
      margin: 0 0 16px;
      font-size: 16px;
      font-weight: 600;
    }
  }

  .danger-zone {
    padding: 16px;
    background: var(--el-color-danger-light-9);
    border-radius: 8px;

    h4 {
      color: var(--el-color-danger);
    }

    p {
      margin: 12px 0 0;
      font-size: 13px;
      color: var(--el-text-color-secondary);
    }
  }
}
</style>
