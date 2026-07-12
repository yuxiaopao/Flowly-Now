<template>
  <div class="integrations-page">
    <PageHeader
      compact
      title="集成"
      subtitle="连接您的常用工具和服务"
    />

    <!-- Categories -->
    <el-tabs
      v-model="activeCategory"
      class="category-tabs"
    >
      <el-tab-pane
        label="全部"
        name="all"
      />
      <el-tab-pane
        label="通信"
        name="communication"
      />
      <el-tab-pane
        label="数据"
        name="data"
      />
      <el-tab-pane
        label="自动化"
        name="automation"
      />
      <el-tab-pane
        label="存储"
        name="storage"
      />
      <el-tab-pane
        label="分析"
        name="analytics"
      />
    </el-tabs>

    <!-- Featured Integrations -->
    <div
      v-if="activeCategory === 'all'"
      class="section featured-section"
    >
      <h2>推荐集成</h2>
      <div class="featured-grid">
        <div
          v-for="integration in featuredIntegrations"
          :key="integration.id"
          class="featured-card"
          @click="openIntegration(integration)"
        >
          <div
            class="card-icon"
            :style="{ backgroundColor: integration.color }"
          >
            <span>{{ integration.name?.charAt(0) ?? '?' }}</span>
          </div>
          <div class="card-content">
            <h4>{{ integration.name }}</h4>
            <p>{{ integration.description }}</p>
          </div>
          <div class="card-status">
            <el-tag
              v-if="isConnected(integration)"
              type="success"
              size="small"
            >
              已连接
            </el-tag>
            <el-tag
              v-else
              size="small"
            >
              可用
            </el-tag>
          </div>
        </div>
      </div>
    </div>

    <!-- All Integrations -->
    <div class="section integrations-section">
      <h2>{{ getCategoryTitle() }}</h2>
      <div class="integrations-grid">
        <div
          v-for="integration in filteredIntegrations"
          :key="integration.id"
          class="integration-card"
          :class="{ connected: isConnected(integration) }"
          @click="openIntegration(integration)"
        >
          <div class="card-header">
            <div
              class="integration-icon"
              :style="{ backgroundColor: integration.color }"
            >
              <span>{{ integration.name?.charAt(0) ?? '?' }}</span>
            </div>
            <div class="integration-info">
              <h4>{{ integration.name }}</h4>
              <span class="category-tag">{{ integration.category }}</span>
            </div>
          </div>
          <p class="description">
            {{ integration.description }}
          </p>
          <div class="card-footer">
            <div
              v-if="isConnected(integration)"
              class="connection-info"
            >
              <span class="connected-dot" />
              <span>已连接</span>
            </div>
            <div
              v-else
              class="usage-count"
            >
              {{ integration.usageCount }} 人使用
            </div>
            <el-button
              size="small"
              :type="isConnected(integration) ? 'default' : 'primary'"
            >
              {{ isConnected(integration) ? '管理' : '连接' }}
            </el-button>
          </div>
        </div>
      </div>
    </div>

    <!-- My Integrations -->
    <div class="section my-integrations">
      <h2>我的集成</h2>
      <div
        v-if="myIntegrations.length === 0"
        class="empty-state"
      >
        <Plug class="empty-icon" />
        <p>暂无连接的集成</p>
        <el-button
          type="primary"
          @click="activeCategory = 'all'"
        >
          浏览集成
        </el-button>
      </div>
      <div
        v-else
        class="integrations-list"
      >
        <div
          v-for="item in myIntegrations"
          :key="item.id"
          class="integration-item"
        >
          <div
            class="item-icon"
            :style="{ backgroundColor: item.color }"
          >
            <span>{{ item.name?.charAt(0) ?? '?' }}</span>
          </div>
          <div class="item-info">
            <h4>{{ item.name }}</h4>
            <p>上次同步: {{ item.lastSync }}</p>
          </div>
          <div class="item-stats">
            <div class="stat">
              <span class="stat-value">{{ item.syncedItems }}</span>
              <span class="stat-label">同步项</span>
            </div>
            <div class="stat">
              <span class="stat-value">{{ item.failedSyncs }}</span>
              <span class="stat-label">失败</span>
            </div>
          </div>
          <div class="item-actions">
            <el-button
              size="small"
              @click="syncIntegration(item)"
            >
              同步
            </el-button>
            <el-button
              size="small"
              text
              type="danger"
              @click="disconnectIntegration(item)"
            >
              断开
            </el-button>
          </div>
        </div>
      </div>
    </div>

    <!-- Integration Detail Dialog -->
    <el-dialog
      v-model="showDetailDialog"
      :title="selectedIntegration?.name"
      width="600px"
    >
      <div
        v-if="selectedIntegration"
        class="integration-detail"
      >
        <div class="detail-header">
          <div
            class="detail-icon"
            :style="{ backgroundColor: selectedIntegration.color }"
          >
            <span>{{ selectedIntegration.name?.charAt(0) ?? '?' }}</span>
          </div>
          <div class="detail-info">
            <h3>{{ selectedIntegration.name }}</h3>
            <p>{{ selectedIntegration.description }}</p>
          </div>
        </div>

        <el-divider />

        <div class="detail-section">
          <h4>支持的事件</h4>
          <div class="events-list">
            <div
              v-for="event in selectedIntegration.events"
              :key="event"
              class="event-item"
            >
              <Zap class="event-icon" />
              <code>{{ event }}</code>
            </div>
          </div>
        </div>

        <div class="detail-section">
          <h4>配置说明</h4>
          <div class="config-guide">
            <p>{{ selectedIntegration.setupGuide }}</p>
          </div>
        </div>

        <div
          v-if="isConnected(selectedIntegration)"
          class="detail-section"
        >
          <h4>连接状态</h4>
          <div class="connection-status">
            <el-tag type="success">
              已连接
            </el-tag>
            <span>最后同步: {{ selectedIntegration.lastSync }}</span>
          </div>
        </div>
      </div>
      <template #footer>
        <el-button @click="showDetailDialog = false">
          关闭
        </el-button>
        <el-button
          v-if="!isConnected(selectedIntegration)"
          type="primary"
          @click="connectIntegration"
        >
          连接
        </el-button>
        <el-button
          v-else
          type="danger"
          @click="disconnectFromDialog"
        >
          断开连接
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { Plug, Zap } from 'lucide-vue-next'
import { useAppStore } from '@/stores/app'
import { useIntegrationsStore } from '@/stores/integrations'
import PageHeader from '@/components/layout/PageHeader.vue'

const integrationsStore = useIntegrationsStore()
const appStore = useAppStore()

const activeCategory = ref('all')
const showDetailDialog = ref(false)
const selectedIntegration = ref(null)

// Computed
const featuredIntegrations = computed(() => {
  return integrationsStore.templates
    .filter(t => t.isFeatured ?? t.is_featured)
    .slice(0, 6)
})

const allIntegrations = computed(() => {
  return integrationsStore.availableIntegrations
})

const filteredIntegrations = computed(() => {
  if (activeCategory.value === 'all') {
    return allIntegrations.value
  }
  return allIntegrations.value.filter(i => i.category === activeCategory.value)
})

const myIntegrations = computed(() => {
  return integrationsStore.connectedIntegrations
})

// Methods
const getCategoryTitle = () => {
  const titles = {
    all: '所有集成',
    communication: '通信工具',
    data: '数据工具',
    automation: '自动化平台',
    storage: '存储服务',
    analytics: '分析工具'
  }
  return titles[activeCategory.value] || '集成'
}

const isConnected = (integration) => {
  return integrationsStore.integrations.some(
    i => (i.integrationType ?? i.integration_type) === (integration.integrationType ?? integration.integration_type)
      && (i.isConnected ?? i.is_connected)
  )
}

const openIntegration = async (integration) => {
  selectedIntegration.value = integration
  showDetailDialog.value = true
}

const connectIntegration = async () => {
  if (!selectedIntegration.value) return
  try {
    await integrationsStore.connectIntegration(selectedIntegration.value.id)
    appStore.success('集成连接成功')
    showDetailDialog.value = false
  } catch (error) {
    appStore.error('连接失败，请稍后重试')
  }
}

const disconnectIntegration = async (item) => {
  try {
    await integrationsStore.disconnectIntegration(item.id)
    appStore.success('已断开连接')
  } catch (error) {
    appStore.error('操作失败，请稍后重试')
  }
}

const disconnectFromDialog = async () => {
  if (!selectedIntegration.value) return
  try {
    const connectedItem = integrationsStore.integrations.find(
      i => (i.integrationType ?? i.integration_type) === (selectedIntegration.value.integrationType ?? selectedIntegration.value.integration_type)
    )
    if (connectedItem) {
      await integrationsStore.disconnectIntegration(connectedItem.id)
      appStore.success('已断开连接')
    }
    showDetailDialog.value = false
  } catch (error) {
    appStore.error('操作失败，请稍后重试')
  }
}

const syncIntegration = async (item) => {
  try {
    await integrationsStore.syncIntegration(item.id)
    appStore.success('同步完成')
  } catch (error) {
    appStore.error('同步失败，请稍后重试')
  }
}

onMounted(async () => {
  await Promise.all([
    integrationsStore.fetchAvailableIntegrations(),
    integrationsStore.fetchIntegrationTemplates(),
    integrationsStore.fetchIntegrations()
  ])
})
</script>

<style lang="scss" scoped>
.integrations-page {
  padding: 24px;
}

.category-tabs {
  margin-bottom: 24px;
}

.section {
  margin-bottom: 32px;

  h2 {
    margin: 0 0 16px;
    font-size: 20px;
    font-weight: 600;
  }
}

.featured-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.featured-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
  background: var(--el-bg-color);
  border: 1px solid var(--el-border-color);
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    border-color: var(--el-color-primary);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  }

  .card-icon {
    width: 48px;
    height: 48px;
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;

    span {
      font-size: 20px;
      font-weight: 700;
      color: white;
    }
  }

  .card-content {
    flex: 1;

    h4 {
      margin: 0;
      font-size: 16px;
    }

    p {
      margin: 4px 0 0;
      font-size: 14px;
      color: var(--el-text-color-secondary);
    }
  }
}

.integrations-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;

  @media (max-width: 1200px) {
    grid-template-columns: repeat(3, 1fr);
  }

  @media (max-width: 768px) {
    grid-template-columns: repeat(2, 1fr);
  }
}

.integration-card {
  padding: 16px;
  background: var(--el-bg-color);
  border: 1px solid var(--el-border-color);
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    border-color: var(--el-color-primary);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  }

  &.connected {
    border-color: #10b981;
    background: rgba(16, 185, 129, 0.05);
  }

  .card-header {
    display: flex;
    align-items: flex-start;
    gap: 12px;
    margin-bottom: 12px;

    .integration-icon {
      width: 40px;
      height: 40px;
      border-radius: 10px;
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;

      span {
        font-size: 16px;
        font-weight: 700;
        color: white;
      }
    }

    .integration-info {
      h4 {
        margin: 0;
        font-size: 15px;
      }

      .category-tag {
        font-size: 12px;
        color: var(--el-text-color-secondary);
      }
    }
  }

  .description {
    margin: 0 0 12px;
    font-size: 13px;
    color: var(--el-text-color-secondary);
    line-height: 1.4;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }

  .card-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;

    .connection-info {
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 13px;
      color: #10b981;

      .connected-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: #10b981;
      }
    }

    .usage-count {
      font-size: 13px;
      color: var(--el-text-color-secondary);
    }
  }
}

.integrations-list {
  .integration-item {
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 16px;
    background: var(--el-bg-color);
    border: 1px solid var(--el-border-color);
    border-radius: 12px;
    margin-bottom: 12px;

    &:last-child {
      margin-bottom: 0;
    }

    .item-icon {
      width: 48px;
      height: 48px;
      border-radius: 12px;
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;

      span {
        font-size: 20px;
        font-weight: 700;
        color: white;
      }
    }

    .item-info {
      flex: 1;

      h4 {
        margin: 0;
        font-size: 16px;
      }

      p {
        margin: 4px 0 0;
        font-size: 14px;
        color: var(--el-text-color-secondary);
      }
    }

    .item-stats {
      display: flex;
      gap: 24px;

      .stat {
        text-align: center;

        .stat-value {
          display: block;
          font-size: 18px;
          font-weight: 600;
        }

        .stat-label {
          font-size: 12px;
          color: var(--el-text-color-secondary);
        }
      }
    }

    .item-actions {
      display: flex;
      gap: 8px;
    }
  }
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 48px;
  background: var(--el-fill-color-light);
  border-radius: 12px;

  .empty-icon {
    width: 48px;
    height: 48px;
    color: var(--el-text-color-secondary);
    opacity: 0.5;
    margin-bottom: 16px;
  }

  p {
    margin: 0 0 16px;
    color: var(--el-text-color-secondary);
  }
}

.integration-detail {
  .detail-header {
    display: flex;
    gap: 16px;

    .detail-icon {
      width: 64px;
      height: 64px;
      border-radius: 16px;
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;

      span {
        font-size: 28px;
        font-weight: 700;
        color: white;
      }
    }

    .detail-info {
      h3 {
        margin: 0;
      }

      p {
        margin: 8px 0 0;
        color: var(--el-text-color-secondary);
      }
    }
  }

  .detail-section {
    margin-top: 24px;

    h4 {
      margin: 0 0 12px;
      font-size: 14px;
    }
  }

  .events-list {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;

    .event-item {
      display: flex;
      align-items: center;
      gap: 6px;
      padding: 6px 12px;
      background: var(--el-fill-color-light);
      border-radius: 6px;

      .event-icon {
        width: 14px;
        height: 14px;
        color: var(--el-color-primary);
      }

      code {
        font-size: 12px;
        font-family: 'JetBrains Mono', monospace;
      }
    }
  }

  .config-guide {
    padding: 12px;
    background: var(--el-fill-color-light);
    border-radius: 8px;

    p {
      margin: 0;
      font-size: 14px;
      color: var(--el-text-color-secondary);
    }
  }

  .connection-status {
    display: flex;
    align-items: center;
    gap: 12px;

    span {
      font-size: 14px;
      color: var(--el-text-color-secondary);
    }
  }
}
</style>
