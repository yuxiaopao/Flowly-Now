<template>
  <div class="notification-center">
    <!-- Trigger Button -->
    <el-badge
      :value="unreadCount"
      :hidden="unreadCount === 0"
      :max="99"
    >
      <el-button
        circle
        :type="hasUnread ? 'primary' : 'default'"
        @click="togglePanel"
      >
        <Bell
          class="btn-icon"
          :class="{ 'has-unread': hasUnread }"
        />
      </el-button>
    </el-badge>

    <!-- Notification Panel -->
    <el-popover
      :visible="showPanel"
      placement="bottom-end"
      :width="400"
      trigger="click"
      @update:visible="showPanel = $event"
    >
      <template #reference>
        <span />
      </template>

      <div
        class="notification-panel"
        @click.stop
      >
        <!-- Header -->
        <div class="panel-header">
          <h3>通知中心</h3>
          <div class="header-actions">
            <el-button
              v-if="unreadCount > 0"
              size="small"
              text
              @click="markAllAsRead"
            >
              全部已读
            </el-button>
            <el-dropdown
              trigger="click"
              @command="handleMenuCommand"
            >
              <el-button
                size="small"
                text
              >
                <MoreVertical class="menu-icon" />
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="archive">
                    归档已读
                  </el-dropdown-item>
                  <el-dropdown-item command="clear">
                    清空通知
                  </el-dropdown-item>
                  <el-dropdown-item command="settings">
                    通知设置
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </div>

        <!-- Tabs -->
        <div class="panel-tabs">
          <el-radio-group
            v-model="activeTab"
            size="small"
          >
            <el-radio-button label="all">
              全部
            </el-radio-button>
            <el-radio-button label="unread">
              未读
            </el-radio-button>
            <el-radio-button label="workflows">
              工作流
            </el-radio-button>
            <el-radio-button label="agents">
              Agent
            </el-radio-button>
          </el-radio-group>
        </div>

        <!-- Notification List -->
        <div
          v-loading="loading"
          class="notification-list"
        >
          <!-- Empty State -->
          <div
            v-if="!loading && filteredNotifications.length === 0"
            class="empty-state"
          >
            <Inbox class="empty-icon" />
            <p>暂无通知</p>
          </div>

          <!-- Notification Items -->
          <div
            v-for="notification in filteredNotifications"
            :key="notification.id"
            class="notification-item"
            :class="{
              unread: !notification.is_read,
              [notification.notification_type]: true
            }"
            @click="handleNotificationClick(notification)"
          >
            <div
              class="item-icon"
              :style="getNotificationChipStyle(notification)"
            >
              <component
                :is="getIcon(notification.notification_type)"
                class="icon"
              />
            </div>
            <div class="item-content">
              <div class="item-header">
                <span class="item-title">{{ notification.title }}</span>
                <span class="item-time">{{ formatTime(notification.created_at) }}</span>
              </div>
              <p class="item-message">
                {{ notification.message }}
              </p>
            </div>
            <div class="item-actions">
              <el-button
                v-if="!notification.is_read"
                size="small"
                text
                title="标记已读"
                @click.stop="markAsRead(notification)"
              >
                <Check class="action-icon" />
              </el-button>
              <el-dropdown
                trigger="click"
                @command="(cmd) => handleItemCommand(cmd, notification)"
              >
                <el-button
                  size="small"
                  text
                  @click.stop
                >
                  <MoreHorizontal class="action-icon" />
                </el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="link">
                      查看详情
                    </el-dropdown-item>
                    <el-dropdown-item command="archive">
                      归档
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
          </div>
        </div>

        <!-- Footer -->
        <div
          v-if="totalCount > visibleCount"
          class="panel-footer"
        >
          <el-button
            size="small"
            text
            @click="loadMore"
          >
            加载更多 ({{ totalCount - visibleCount }} 条)
          </el-button>
        </div>
      </div>
    </el-popover>

    <!-- Settings Dialog -->
    <el-dialog
      v-model="showSettings"
      title="通知设置"
      width="500px"
    >
      <div class="settings-form">
        <div class="settings-section">
          <h4>通知类型</h4>
          <el-checkbox
            v-model="preferences.workflow_completed"
            @change="updatePreference('workflow_completed', $event)"
          >
            工作流完成
          </el-checkbox>
          <el-checkbox
            v-model="preferences.workflow_failed"
            @change="updatePreference('workflow_failed', $event)"
          >
            工作流失败
          </el-checkbox>
          <el-checkbox
            v-model="preferences.workflow_scheduled"
            @change="updatePreference('workflow_scheduled', $event)"
          >
            工作流调度
          </el-checkbox>
          <el-checkbox
            v-model="preferences.agent_completed"
            @change="updatePreference('agent_completed', $event)"
          >
            Agent 完成
          </el-checkbox>
          <el-checkbox
            v-model="preferences.agent_failed"
            @change="updatePreference('agent_failed', $event)"
          >
            Agent 失败
          </el-checkbox>
          <el-checkbox
            v-model="preferences.alert_triggered"
            @change="updatePreference('alert_triggered', $event)"
          >
            告警通知
          </el-checkbox>
        </div>

        <el-divider />

        <div class="settings-section">
          <h4>通知方式</h4>
          <el-checkbox
            v-model="preferences.in_app_enabled"
            @change="updatePreference('in_app_enabled', $event)"
          >
            应用内通知
          </el-checkbox>
          <el-checkbox
            v-model="preferences.push_enabled"
            @change="updatePreference('push_enabled', $event)"
          >
            推送通知
          </el-checkbox>
          <el-checkbox
            v-model="preferences.email_enabled"
            @change="updatePreference('email_enabled', $event)"
          >
            邮件通知
          </el-checkbox>
        </div>

        <el-divider />

        <div class="settings-section">
          <h4>免打扰</h4>
          <el-checkbox
            v-model="preferences.quiet_hours_enabled"
            @change="updatePreference('quiet_hours_enabled', $event)"
          >
            启用免打扰模式
          </el-checkbox>
          <div
            v-if="preferences.quiet_hours_enabled"
            class="quiet-hours"
          >
            <el-time-select
              v-model="preferences.quiet_hours_start"
              placeholder="开始时间"
              start="00:00"
              step="00:30"
              end="23:30"
              @change="updateQuietHours"
            />
            <span>至</span>
            <el-time-select
              v-model="preferences.quiet_hours_end"
              placeholder="结束时间"
              start="00:00"
              step="00:30"
              end="23:30"
              @change="updateQuietHours"
            />
          </div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, markRaw } from 'vue'
import { useRouter } from 'vue-router'
import {
  Bell, Inbox, Check, MoreVertical, MoreHorizontal,
  CheckCircle, XCircle, Clock, Bot, AlertTriangle, Zap,
  Info, UserPlus, MessageCircle, AtSign
} from 'lucide-vue-next'

const router = useRouter()

const loading = ref(false)
const showPanel = ref(false)
const showSettings = ref(false)
const activeTab = ref('all')
const notifications = ref([])
const unreadCount = ref(0)
const page = ref(1)
const pageSize = ref(20)
const totalCount = ref(0)

const preferences = ref({
  workflow_completed: true,
  workflow_failed: true,
  workflow_scheduled: true,
  agent_completed: true,
  agent_failed: true,
  alert_triggered: true,
  in_app_enabled: true,
  push_enabled: true,
  email_enabled: false,
  quiet_hours_enabled: false,
  quiet_hours_start: '22:00',
  quiet_hours_end: '08:00'
})

const visibleCount = computed(() => notifications.value.length)
const hasUnread = computed(() => unreadCount.value > 0)

const filteredNotifications = computed(() => {
  if (activeTab.value === 'all') {
    return notifications.value
  } else if (activeTab.value === 'unread') {
    return notifications.value.filter(n => !n.is_read)
  } else if (activeTab.value === 'workflows') {
    return notifications.value.filter(n =>
      n.notification_type.startsWith('workflow')
    )
  } else if (activeTab.value === 'agents') {
    return notifications.value.filter(n =>
      n.notification_type.startsWith('agent')
    )
  }
  return notifications.value
})

const iconComponents = {
  workflow_completed: markRaw(CheckCircle),
  workflow_failed: markRaw(XCircle),
  workflow_scheduled: markRaw(Clock),
  agent_completed: markRaw(Bot),
  agent_failed: markRaw(AlertTriangle),
  trigger_activated: markRaw(Zap),
  alert_triggered: markRaw(Bell),
  system_message: markRaw(Info),
  user_invitation: markRaw(UserPlus),
  comment: markRaw(MessageCircle),
  mention: markRaw(AtSign)
}

const notificationThemeMap = {
  workflow_completed: { chip: 'var(--success)', text: 'var(--notification-chip-text)' },
  workflow_failed: { chip: 'var(--error)', text: 'var(--notification-chip-text)' },
  workflow_scheduled: { chip: 'var(--warning)', text: 'var(--notification-chip-text)' },
  agent_completed: { chip: 'var(--success)', text: 'var(--notification-chip-text)' },
  agent_failed: { chip: 'var(--warning)', text: 'var(--notification-chip-text)' },
  trigger_activated: { chip: 'var(--info)', text: 'var(--notification-chip-text)' },
  alert_triggered: { chip: 'var(--warning)', text: 'var(--notification-chip-text)' },
  system_message: { chip: 'var(--accent-primary)', text: 'var(--text-inverse)' },
  user_invitation: { chip: 'var(--info)', text: 'var(--notification-chip-text)' },
  comment: { chip: 'var(--info)', text: 'var(--notification-chip-text)' },
  mention: { chip: 'var(--error)', text: 'var(--notification-chip-text)' }
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

const togglePanel = () => {
  showPanel.value = !showPanel.value
  if (showPanel.value && notifications.value.length === 0) {
    fetchNotifications()
  }
}

const fetchNotifications = async () => {
  loading.value = true
  try {
    // Mock data for demonstration
    notifications.value = [
      {
        id: 1,
        notification_type: 'workflow_completed',
        title: '工作流执行完成',
        message: '「数据处理流程」已成功执行完成，用时 2分30秒',
        created_at: new Date(Date.now() - 300000).toISOString(),
        is_read: false,
        color: 'var(--success)',
        link: '/workflows/1'
      },
      {
        id: 2,
        notification_type: 'workflow_failed',
        title: '工作流执行失败',
        message: '「API 数据同步」执行失败：连接超时',
        created_at: new Date(Date.now() - 3600000).toISOString(),
        is_read: false,
        color: 'var(--error)',
        link: '/workflows/2'
      },
      {
        id: 3,
        notification_type: 'alert_triggered',
        title: '告警通知',
        message: '您的 API Key 使用量已达到 80% 配额',
        created_at: new Date(Date.now() - 86400000).toISOString(),
        is_read: true,
        color: 'var(--warning)',
        link: '/models'
      },
      {
        id: 4,
        notification_type: 'system_message',
        title: '系统公告',
        message: 'Flowly 平台将于本周日凌晨进行例行维护',
        created_at: new Date(Date.now() - 172800000).toISOString(),
        is_read: true,
        color: 'var(--accent-primary)',
        link: '/announcements'
      }
    ]
    unreadCount.value = notifications.value.filter(n => !n.is_read).length
    totalCount.value = notifications.value.length
  } catch {
    // Silent failure - notifications can be empty
  } finally {
    loading.value = false
  }
}

const markAsRead = async (notification) => {
  notification.is_read = true
  unreadCount.value = Math.max(0, unreadCount.value - 1)
}

const markAllAsRead = async () => {
  notifications.value.forEach(n => {
    n.is_read = true
  })
  unreadCount.value = 0
}

const handleNotificationClick = (notification) => {
  if (!notification.is_read) {
    markAsRead(notification)
  }
  if (notification.link) {
    router.push(notification.link)
    showPanel.value = false
  }
}

const handleMenuCommand = (command) => {
  if (command === 'archive') {
    notifications.value = notifications.value.filter(n => n.is_read)
  } else if (command === 'clear') {
    notifications.value = []
    totalCount.value = 0
  } else if (command === 'settings') {
    showSettings.value = true
  }
}

const handleItemCommand = (command, notification) => {
  if (command === 'link') {
    handleNotificationClick(notification)
  } else if (command === 'archive') {
    notifications.value = notifications.value.filter(n => n.id !== notification.id)
  } else if (command === 'delete') {
    notifications.value = notifications.value.filter(n => n.id !== notification.id)
    if (!notification.is_read) {
      unreadCount.value = Math.max(0, unreadCount.value - 1)
    }
    totalCount.value = Math.max(0, totalCount.value - 1)
  }
}

const loadMore = () => {
  page.value++
  fetchNotifications()
}

const updatePreference = (key, value) => {
  preferences.value[key] = value
  // API call would go here
}

const updateQuietHours = () => {
  // API call would go here
}

// Poll for new notifications
let pollInterval = null

onMounted(() => {
  fetchNotifications()
  // Poll every 30 seconds
  pollInterval = setInterval(fetchNotifications, 30000)
})

onUnmounted(() => {
  if (pollInterval) {
    clearInterval(pollInterval)
  }
})
</script>

<style lang="scss" scoped>
.notification-center {
  display: inline-flex;
}

.btn-icon {
  width: 20px;
  height: 20px;

  &.has-unread {
    color: var(--accent-primary);
  }
}

.notification-panel {
  margin: -12px;
  display: flex;
  flex-direction: column;
  max-height: 500px;
  background: var(--bg-elevated);
  color: var(--text-primary);
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px;
  border-bottom: 1px solid var(--border-primary);

  h3 {
    margin: 0;
    font-size: 16px;
    font-weight: 600;
    color: var(--text-primary);
  }

  .header-actions {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .menu-icon {
    width: 16px;
    height: 16px;
  }
}

.panel-tabs {
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-primary);
}

.notification-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px 0;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  color: var(--text-secondary);

  .empty-icon {
    width: 48px;
    height: 48px;
    margin-bottom: 12px;
    opacity: 0.5;
  }

  p {
    margin: 0;
  }
}

.notification-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px 16px;
  cursor: pointer;
  transition: background-color 0.2s;

  &:hover {
    background-color: var(--surface-muted);
  }

  &.unread {
    background-color: var(--notification-unread);

    .item-title {
      font-weight: 600;
    }
  }

  .item-icon {
    width: 36px;
    height: 36px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    box-shadow: 0 0 0 1px var(--surface-accent) inset;

    .icon {
      width: 18px;
      height: 18px;
      color: currentColor;
    }
  }

  .item-content {
    flex: 1;
    min-width: 0;

    .item-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 4px;

      .item-title {
        font-size: 14px;
        color: var(--text-primary);
      }

      .item-time {
        font-size: 12px;
        color: var(--text-secondary);
        flex-shrink: 0;
      }
    }

    .item-message {
      margin: 0;
      font-size: 13px;
      color: var(--text-secondary);
      line-height: 1.4;
      display: -webkit-box;
      -webkit-line-clamp: 2;
      line-clamp: 2;
      -webkit-box-orient: vertical;
      overflow: hidden;
    }
  }

  .item-actions {
    display: flex;
    align-items: center;
    gap: 4px;
    flex-shrink: 0;
    opacity: 0;
    transition: opacity 0.2s;

    .action-icon {
      width: 16px;
      height: 16px;
    }
  }

  &:hover .item-actions {
    opacity: 1;
  }
}

.panel-footer {
  padding: 12px;
  text-align: center;
  border-top: 1px solid var(--border-primary);
}

.settings-form {
  .settings-section {
    h4 {
      margin: 0 0 12px;
      font-size: 14px;
      font-weight: 600;
      color: var(--text-primary);
    }

    :deep(.el-checkbox) {
      display: flex;
      margin-bottom: 12px;
    }
  }

  .quiet-hours {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-top: 12px;
    color: var(--text-secondary);

    :deep(.el-select) {
      width: 140px;
    }
  }
}
</style>
