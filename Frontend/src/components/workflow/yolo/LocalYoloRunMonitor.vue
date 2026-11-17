<template>
  <div
    v-if="isDesktop"
    class="run-views"
    aria-label="训练详情视图"
  >
    <button
      type="button"
      :aria-pressed="activeView === 'charts'"
      @click="activeView = 'charts'"
    >
      图表分析与模型对比
    </button>
    <button
      type="button"
      :aria-pressed="activeView === 'details'"
      @click="activeView = 'details'"
    >
      实时记录、网络与导出
    </button>
  </div>
  <YoloRunAnalytics
    v-if="activeView === 'charts'"
    :job-id="binding.jobId"
  />
  <div
    v-if="isDesktop"
    v-show="activeView === 'details'"
    ref="monitorHost"
    class="training-live"
    data-testid="training-live"
    aria-label="实时训练"
  />
</template>

<script setup>
import { onMounted, onUnmounted, ref, watch } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useAppStore } from '@/stores/app'
import template from '@/components/training/live/template.html?raw'
import styles from '@/components/training/live/monitor.css?inline'
import { mountTrainingMonitor } from '@/components/training/live/renderer'
import YoloRunAnalytics from './YoloRunAnalytics.vue'

const monitorHost = ref(null)
const activeView = ref('charts')
const isDesktop = Boolean(window.flowlyDesktop?.training?.monitor)
const authStore = useAuthStore()
const appStore = useAppStore()
const props = defineProps({ binding: { type: Object, required: true } })
const emit = defineEmits(['snapshot'])
let dispose
let root

function mount() {
  dispose?.()
  if (!root) return
  // Keep charts and tables isolated from application-wide element styles.
  const style = document.createElement('style')
  style.textContent = styles
  root.innerHTML = template
  root.prepend(style)
  const api = window.flowlyDesktop?.training?.monitor
  let active = true
  let recovering = false
  root.host.dataset.theme = appStore.theme
  const start = () => api.start(authStore.token, props.binding)
  const unmount = mountTrainingMonitor(root, api && {
    ...api,
    start,
    refresh: start,
    onUpdate: callback => api.onUpdate(async payload => {
      if (!active) return
      callback(payload)
      if (payload.snapshot) emit('snapshot', payload.snapshot)
      if (!payload.authRequired || !authStore.token || recovering) return
      recovering = true
      try {
        // Reuse the application's refresh-token flow when an access token expires.
        await authStore.fetchUserInfo()
        if (active && authStore.token) callback(await start())
      } catch {
        // The auth store and interceptor handle invalid sessions and network errors.
      } finally {
        recovering = false
      }
    }),
  })
  dispose = () => { active = false; unmount() }
}

onMounted(() => {
  if (!monitorHost.value) return
  root = monitorHost.value.attachShadow({ mode: 'open' })
  mount()
})

watch(() => authStore.token, mount)
watch(() => props.binding, mount, { deep: true })
watch(() => appStore.theme, theme => { if (root) root.host.dataset.theme = theme })
onUnmounted(() => dispose?.())
</script>

<style scoped>
.training-live { width: 100%; min-width: 0; }
.run-views { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 16px; }
.run-views button { padding: 8px 12px; font: inherit; color: var(--text-secondary); background: var(--bg-secondary); border: 1px solid var(--border-color); border-radius: 6px; cursor: pointer; }
.run-views button[aria-pressed=true] { color: var(--primary-color); border-color: var(--primary-color); }
.run-views button:focus-visible { outline: 2px solid var(--primary-color); outline-offset: 3px; }
</style>
