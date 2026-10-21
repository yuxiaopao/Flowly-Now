<template>
  <Teleport to="body">
    <Transition name="palette-fade">
      <div
        v-if="isOpen"
        class="command-palette-overlay"
        @click="close"
      >
        <div
          class="command-palette"
          role="dialog"
          aria-modal="true"
          aria-label="快速跳转"
          @click.stop
        >
          <!-- Search Input -->
          <div class="search-container">
            <Search class="search-icon" />
            <input
              ref="searchInput"
              v-model="query"
              type="text"
              aria-label="搜索页面与命令"
              role="combobox"
              aria-autocomplete="list"
              aria-expanded="true"
              aria-controls="command-results"
              :aria-activedescendant="filteredResults[selectedIndex] ? 'command-' + selectedIndex : undefined"
              class="search-input"
              placeholder="输入命令或搜索..."
              @keydown="handleKeydown"
            >
            <kbd class="shortcut-hint">ESC</kbd>
          </div>

          <!-- Tabs -->
          <div class="tabs">
            <button
              v-for="tab in tabs"
              :key="tab.id"
              :class="['tab', { active: activeTab === tab.id }]"
              :aria-pressed="activeTab === tab.id"
              @click="activeTab = tab.id"
            >
              <component
                :is="tab.icon"
                class="tab-icon"
              />
              {{ tab.label }}
            </button>
          </div>

          <!-- Results -->
          <div
            id="command-results"
            ref="resultsContainer"
            role="listbox"
            aria-label="匹配的页面与命令"
            class="results"
          >
            <!-- Empty State -->
            <div
              v-if="filteredResults.length === 0 && query"
              class="empty-state"
            >
              <Command class="empty-icon" />
              <p>没有找到匹配的项</p>
            </div>

            <!-- Commands -->
            <div v-else>
              <div
                v-for="(group, groupName) in groupedResults"
                :key="groupName"
                class="result-group"
              >
                <div
                  v-if="groupName"
                  class="group-header"
                >
                  {{ groupName }}
                </div>
                <div
                  v-for="(item, index) in group"
                  :id="'command-' + getGlobalIndex(groupName, index)"
                  :key="item.id"
                  role="option"
                  :aria-selected="isSelected(item)"
                  :class="['result-item', { selected: isSelected(item) }]"
                  @click="executeItem(item)"
                  @mouseenter="selectedIndex = getGlobalIndex(groupName, index)"
                >
                  <div
                    v-if="item.icon"
                    class="item-icon"
                  >
                    <component
                      :is="item.icon"
                      class="icon"
                    />
                  </div>
                  <div
                    v-else-if="item.emoji"
                    class="item-emoji"
                  >
                    {{ item.emoji }}
                  </div>
                  <div class="item-content">
                    <div class="item-title">
                      {{ item.title }}
                    </div>
                    <div
                      v-if="item.description"
                      class="item-description"
                    >
                      {{ item.description }}
                    </div>
                  </div>
                  <div
                    v-if="item.shortcut"
                    class="item-shortcut"
                  >
                    <kbd
                      v-for="key in item.shortcut"
                      :key="key"
                    >{{ key }}</kbd>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Footer -->
          <div class="palette-footer">
            <div class="footer-hint">
              <kbd>↑↓</kbd> 导航
              <kbd>↵</kbd> 选择
              <kbd>ESC</kbd> 关闭
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { ref, computed, watch, nextTick, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAppStore } from '@/stores/app'
import { APP_NAV_ITEMS } from '@/config/appNavigation'
import {
  Search, Command, Bot, Workflow,
  Settings, Plus, Play, ChevronRight,
  Users, Bell, Key, Palette, Moon, Sun, Contrast, CircleDot
} from 'lucide-vue-next'

const router = useRouter()
const appStore = useAppStore()

const isOpen = ref(false)
const query = ref('')
const activeTab = ref('all')
const selectedIndex = ref(0)
const searchInput = ref(null)
const resultsContainer = ref(null)

const tabs = [
  { id: 'all', label: '全部', icon: Command },
  { id: 'navigation', label: '导航', icon: ChevronRight },
  { id: 'actions', label: '操作', icon: Play },
  { id: 'settings', label: '设置', icon: Settings }
]

const commands = computed(() => ([
  ...APP_NAV_ITEMS.map(item => ({
    id: item.path, title: item.label, description: '打开' + item.label,
    icon: item.icon, action: () => router.push(item.path), tab: 'navigation',
  })),
  { id: 'action-new-workflow', title: '新建工作流', description: '打开工作流编辑器', icon: Plus, action: () => router.push('/workflows/new'), tab: 'actions' },
  { id: 'action-new-agent', title: '新建智能体', description: '配置新的 Agent', icon: Bot, action: () => router.push('/agents/new'), tab: 'actions' },

  { id: 'settings-profile', title: '个人资料', description: '编辑个人资料', icon: Users, action: () => router.push('/settings/profile'), tab: 'settings' },
  { id: 'settings-api-keys', title: '模型与服务凭证', description: '管理 API 密钥', icon: Key, action: () => router.push('/settings/credentials'), tab: 'settings' },
  { id: 'settings-billing', title: '订阅管理', description: '管理订阅和账单', icon: Palette, action: () => router.push('/settings/billing'), tab: 'settings' },
  { id: 'settings-notifications', title: '通知设置', description: '配置通知偏好', icon: Bell, action: () => router.push('/settings/notifications'), tab: 'settings' },
  { id: 'settings-integrations', title: '集成', description: '管理第三方集成', icon: Workflow, action: () => router.push('/settings/integrations'), tab: 'settings' },

  { id: 'theme-dark', title: '切换到深色模式', description: '使用深色主题', icon: Moon, action: () => appStore.setTheme('dark'), tab: 'settings' },
  { id: 'theme-light', title: '切换到浅色模式', description: '使用浅色主题', icon: Sun, action: () => appStore.setTheme('light'), tab: 'settings' },
  { id: 'theme-pure-bw', title: '切换到纯黑白', description: '使用极简黑白主题', icon: Contrast, action: () => appStore.setTheme('pure-bw'), tab: 'settings' },
  { id: 'theme-high-contrast', title: '切换到高对比', description: '使用高对比主题', icon: CircleDot, action: () => appStore.setTheme('high-contrast'), tab: 'settings' }
]))

const groupedResults = computed(() => {
  const filtered = filteredResults.value
  const groups = {}

  filtered.forEach(item => {
    const group = item.group || '常用'
    if (!groups[group]) {
      groups[group] = []
    }
    groups[group].push(item)
  })

  return groups
})

const filteredResults = computed(() => {
  let items = commands.value

  if (activeTab.value !== 'all') {
    items = items.filter(item => item.tab === activeTab.value)
  }

  if (query.value) {
    const q = query.value.toLowerCase()
    items = items.filter(item =>
      item.title.toLowerCase().includes(q) ||
      item.description?.toLowerCase().includes(q)
    )
  }

  return items
})

const isSelected = (item) => {
  const index = filteredResults.value.findIndex(i => i.id === item.id)
  return index === selectedIndex.value
}

const getGlobalIndex = (groupName, indexInGroup) => {
  let count = 0
  for (const group of Object.values(groupedResults.value)) {
    if (group === groupedResults.value[groupName]) {
      return count + indexInGroup
    }
    count += group.length
  }
  return indexInGroup
}

const executeItem = (item) => {
  if (item.action) {
    item.action()
  }
  close()
}

const handleKeydown = (e) => {
  if (e.key === 'Escape') { e.preventDefault(); close(); return }
  const total = filteredResults.value.length
  if (!total) return

  switch (e.key) {
    case 'ArrowDown':
      e.preventDefault()
      selectedIndex.value = (selectedIndex.value + 1) % total
      scrollToSelected()
      break
    case 'ArrowUp':
      e.preventDefault()
      selectedIndex.value = (selectedIndex.value - 1 + total) % total
      scrollToSelected()
      break
    case 'Enter':
      e.preventDefault()
      if (filteredResults.value[selectedIndex.value]) {
        executeItem(filteredResults.value[selectedIndex.value])
      }
      break
    case 'Escape':
      close()
      break
  }
}

const scrollToSelected = () => {
  nextTick(() => {
    const container = resultsContainer.value
    const selected = container?.querySelector('.result-item.selected')
    if (selected) {
      selected.scrollIntoView({ block: 'nearest' })
    }
  })
}

let returnFocus

const open = () => {
  returnFocus = document.activeElement
  isOpen.value = true
  query.value = ''
  activeTab.value = 'all'
  selectedIndex.value = 0
  nextTick(() => {
    searchInput.value?.focus()
  })
}

const close = () => {
  isOpen.value = false
  nextTick(() => returnFocus?.focus())
}

const handleGlobalKeydown = (e) => {
  if (isOpen.value && e.key === 'Escape') { e.preventDefault(); close(); return }
  if (isOpen.value && e.key === 'Tab') {
    const controls = [...document.querySelectorAll('.command-palette input, .command-palette button')]
    const first = controls[0]
    const last = controls.at(-1)
    if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last?.focus() }
    else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first?.focus() }
  }
  if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
    e.preventDefault()
    if (isOpen.value) {
      close()
    } else {
      open()
    }
  }
}

watch(query, () => {
  selectedIndex.value = 0
})

watch(activeTab, () => {
  selectedIndex.value = 0
})

onMounted(() => {
  document.addEventListener('keydown', handleGlobalKeydown)
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleGlobalKeydown)
})

defineExpose({ open, close })
</script>

<style lang="scss" scoped>
.command-palette-overlay {
  position: fixed;
  inset: 0;
  z-index: 9999;
  background: var(--overlay-backdrop);
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding: 10vh 16px 16px;
}

.command-palette {
  width: 100%;
  max-width: 600px;
  background: var(--bg-elevated);
  border: 1px solid var(--border-primary);
  border-radius: 16px;
  box-shadow: var(--shadow-xl);
  overflow: hidden;
}

.search-container {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-primary);

  .search-icon {
    width: 20px;
    height: 20px;
    color: var(--text-secondary);
    flex-shrink: 0;
  }

  .search-input {
    flex: 1;
    border: none;
    background: transparent;
    font-size: 16px;
    outline: none;
    color: var(--text-primary);

    &::placeholder {
      color: var(--text-tertiary);
    }
  }

  .shortcut-hint {
    padding: 4px 8px;
    background: var(--surface-muted);
    border: 1px solid var(--border-primary);
    border-radius: 6px;
    font-size: 12px;
    font-family: inherit;
    color: var(--text-secondary);
  }
}

.tabs {
  display: flex;
  gap: 4px;
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-primary);

  .tab {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 8px 16px;
    background: transparent;
    border: none;
    border-radius: 8px;
    font-size: 14px;
    color: var(--text-secondary);
    cursor: pointer;
    transition: all 0.2s;

    &:hover {
      background: var(--surface-muted);
    }

    &.active {
      background: var(--accent-muted);
      color: var(--text-primary);
    }

    .tab-icon {
      width: 16px;
      height: 16px;
    }
  }
}

.results {
  max-height: min(400px, 50dvh);
  overflow-y: auto;
  padding: 8px;
}

.result-group {
  margin-bottom: 8px;

  .group-header {
    padding: 8px 12px 4px;
    font-size: 12px;
    font-weight: 600;
    color: var(--text-secondary);
    text-transform: uppercase;
  }
}

.result-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border-radius: 10px;
  cursor: pointer;
  transition: background 0.15s;

  &:hover,
  &.selected {
    background: var(--surface-muted);
  }

  .item-icon {
    width: 36px;
    height: 36px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--surface-strong);
    border-radius: 10px;
    flex-shrink: 0;

    .icon {
      width: 18px;
      height: 18px;
      color: var(--text-secondary);
    }
  }

  .item-emoji {
    width: 36px;
    height: 36px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 20px;
    flex-shrink: 0;
  }

  .item-content {
    flex: 1;
    min-width: 0;

    .item-title {
      font-weight: 500;
      color: var(--text-primary);
    }

    .item-description {
      font-size: 13px;
      color: var(--text-secondary);
      margin-top: 2px;
    }
  }

  .item-shortcut {
    display: flex;
    gap: 4px;
    flex-shrink: 0;

    kbd {
      padding: 4px 8px;
      background: var(--surface-muted);
      border: 1px solid var(--border-primary);
      border-radius: 6px;
      font-size: 12px;
      font-family: inherit;
      color: var(--text-secondary);
    }
  }
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 48px 20px;
  color: var(--text-secondary);

  .empty-icon {
    width: 48px;
    height: 48px;
    opacity: 0.5;
    margin-bottom: 12px;
  }
}

.palette-footer {
  padding: 12px 16px;
  border-top: 1px solid var(--border-primary);
  background: var(--surface-muted);

  .footer-hint {
    display: flex;
    align-items: center;
    gap: 16px;
    font-size: 12px;
    color: var(--text-secondary);

    kbd {
      padding: 2px 6px;
      background: var(--surface-strong);
      border: 1px solid var(--border-primary);
      border-radius: 6px;
      font-size: 11px;
      font-family: inherit;
    }
  }
}

.palette-fade-enter-active,
.palette-fade-leave-active {
  transition: opacity 0.15s ease;

  .command-palette {
    transition: transform 0.15s ease, opacity 0.15s ease;
  }
}

.palette-fade-enter-from,
.palette-fade-leave-to {
  opacity: 0;

  .command-palette {
    transform: scale(0.95) translateY(-10px);
    opacity: 0;
  }
}
@media (max-width: 600px) {
  .tabs .tab { min-height: 44px; padding: 8px 10px; }
  .item-shortcut { display: none; }
  .search-container .search-input { min-width: 0; }
}
</style>
