<template>
  <section
    ref="workspace"
    class="avatar-workspace"
    :aria-busy="isApplying"
  >
    <PageHeader
      compact
      :title="studio.title"
      :subtitle="studio.subtitle"
    >
      <template #actions>
        <AppButton
          variant="secondary"
          :disabled="!isReady"
          @click="toggleFullscreen"
        >
          <Maximize2 aria-hidden="true" />{{ isFullscreen ? studio.exitFullscreen : studio.fullscreen }}
        </AppButton>
        <AppButton
          :loading="isApplying"
          :disabled="!isReady"
          @click="applyAvatar"
        >
          <Check aria-hidden="true" />{{ studio.apply }}
        </AppButton>
      </template>
    </PageHeader>
    <p
      v-if="error"
      class="studio-error"
      role="alert"
    >
      {{ error }}
    </p>
    <div
      class="studio-status"
      role="status"
    >
      <span>{{ isApplying ? studio.applying : status || studio.hint }}</span>
      <AppButton
        v-if="loadFailed"
        variant="secondary"
        size="small"
        @click="reloadStudio"
      >
        {{ studio.retry }}
      </AppButton>
    </div>
    <div class="studio-frame-container">
      <div
        v-if="!isReady"
        class="studio-loading"
        role="status"
      >
        {{ loadFailed ? studio.unavailable : studio.loading }}
      </div>
      <iframe
        v-if="authStore.user?.id"
        :key="frameKey"
        ref="frame"
        class="studio-frame"
        :src="frameUrl"
        :title="studio.frameTitle"
        allow="clipboard-write; fullscreen"
        @load="pingStudio"
        @error="onLoadError"
      />
    </div>
    <footer class="studio-footer">
      <span>{{ studio.capabilities }}</span>
      <a
        :href="studio.source"
        target="_blank"
        rel="noopener noreferrer"
      >{{ studio.attribution }}<ExternalLink aria-hidden="true" /></a>
    </footer>
  </section>
</template>

<script setup>
import { computed, onMounted, onBeforeUnmount, ref, watch } from 'vue'
import { onBeforeRouteLeave } from 'vue-router'
import { Check, ExternalLink, Maximize2 } from 'lucide-vue-next'
import PageHeader from '@/components/layout/PageHeader.vue'
import AppButton from '@/components/common/AppButton.vue'
import { useAuthStore } from '@/stores/auth'
import { useAppStore } from '@/stores/app'
import { AVATAR_STUDIO as studio } from '@/config/avatarStudio'
import { getAvatarStudioUrl, isAvatarStudioMessage, makeAvatarStudioMessage } from '@/utils/avatarStudio'
import { normalizeAccountAvatar } from '@/utils/accountAvatar'
import { getSettingsError } from '@/utils/personalCenter'

const authStore = useAuthStore()
const appStore = useAppStore()
const workspace = ref(null)
const frame = ref(null)
const frameKey = ref(0)
const frameUrl = computed(() => getAvatarStudioUrl(authStore.user?.id))
const isReady = ref(false)
const isApplying = ref(false)
const isFullscreen = ref(false)
const loadFailed = ref(false)
const error = ref('')
const status = ref('')
let readyTimer
let pendingCapture
const targetOrigin = location.origin === 'null' ? '*' : location.origin

function startReadyTimer() {
  clearTimeout(readyTimer)
  readyTimer = setTimeout(onLoadError, studio.readyTimeoutMs)
}
function onLoadError() { if (!isReady.value) loadFailed.value = true }
function pingStudio() { frame.value?.contentWindow?.postMessage(makeAvatarStudioMessage(studio.ping), targetOrigin) }
function reloadStudio() {
  isReady.value = false
  loadFailed.value = false
  error.value = ''
  frameKey.value++
  startReadyTimer()
}
function receiveMessage(event) {
  if (!isAvatarStudioMessage(event, frame.value?.contentWindow, location.origin)) return
  const message = event.data
  if (message.type === studio.ready) {
    isReady.value = true
    loadFailed.value = false
    clearTimeout(readyTimer)
  } else if (message.type === studio.response && pendingCapture?.id === message.requestId) {
    clearTimeout(pendingCapture.timer)
    const capture = pendingCapture
    pendingCapture = null
    if (message.error) capture.reject(new Error(studio.captureError))
    else capture.resolve(message.preferences)
  }
}
async function applyAvatar() {
  if (!isReady.value || isApplying.value) return
  isApplying.value = true
  error.value = ''
  status.value = ''
  const accountId = authStore.user?.id
  try {
    const result = await new Promise((resolve, reject) => {
      const id = crypto.randomUUID()
      const timer = setTimeout(() => {
        pendingCapture = null
        reject(new Error(studio.captureError))
      }, studio.requestTimeoutMs)
      pendingCapture = { id, timer, resolve, reject }
      frame.value.contentWindow.postMessage(makeAvatarStudioMessage(studio.request, id), targetOrigin)
    })
    if (!result?.shape || !result?.color || !result?.expression) throw new Error(studio.captureError)
    const preferences = normalizeAccountAvatar({ ...result, mode: 'robot' })
    if (!accountId || accountId !== authStore.user?.id) throw new Error(studio.saveError)
    const saved = await authStore.updateProfile({ avatarPreferences: preferences })
    status.value = saved.avatarPreferencesSynced ? studio.applied : saved.avatarPreferencesPersisted ? studio.appliedLocal : studio.appliedSession
    appStore.success(status.value)
  } catch (cause) {
    error.value = getSettingsError(cause, studio.saveError)
  } finally {
    isApplying.value = false
  }
}
async function toggleFullscreen() {
  try {
    if (document.fullscreenElement === workspace.value) await document.exitFullscreen()
    else await workspace.value.requestFullscreen()
  } catch { error.value = studio.fullscreenError }
}
function syncFullscreen() { isFullscreen.value = document.fullscreenElement === workspace.value }
watch(() => authStore.user?.id, reloadStudio)
onBeforeRouteLeave(() => !isApplying.value)
onMounted(() => {
  window.addEventListener('message', receiveMessage)
  document.addEventListener('fullscreenchange', syncFullscreen)
  startReadyTimer()
})
onBeforeUnmount(() => {
  clearTimeout(readyTimer)
  if (pendingCapture) {
    clearTimeout(pendingCapture.timer)
    pendingCapture.reject(new Error(studio.captureError))
  }
  window.removeEventListener('message', receiveMessage)
  document.removeEventListener('fullscreenchange', syncFullscreen)
})
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;
.avatar-workspace { min-width: 0; }
.avatar-workspace :deep(.page-header__actions svg) { width: $spacing-4; height: $spacing-4; }
.studio-status { display: flex; align-items: center; justify-content: space-between; gap: $spacing-3; margin-block: $spacing-3; color: var(--text-secondary); font-size: $font-size-sm; line-height: $line-height-normal; }
.studio-error { color: var(--color-error); font-size: $font-size-sm; }
.studio-frame-container { position: relative; overflow: hidden; border: 1px solid var(--border-primary); border-radius: $radius-xl; }
.studio-frame { display: block; width: 100%; height: max(720px, calc(100dvh - 330px)); border: 0; background: var(--bg-secondary); }
.studio-loading { position: absolute; inset: 0; z-index: 1; display: grid; place-items: center; background: var(--bg-secondary); color: var(--text-secondary); font-size: $font-size-sm; pointer-events: none; }
.studio-footer { display: flex; justify-content: space-between; flex-wrap: wrap; gap: $spacing-2; margin-top: $spacing-3; color: var(--text-tertiary); font-size: $font-size-xs; line-height: $line-height-normal; }
.studio-footer a { display: inline-flex; align-items: center; gap: $spacing-1; color: var(--text-secondary); text-underline-offset: $spacing-1; }
.studio-footer svg { width: $spacing-3; height: $spacing-3; }
.avatar-workspace:fullscreen { padding: $spacing-5; overflow: auto; background: var(--bg-primary); }
.avatar-workspace:fullscreen .studio-frame { height: calc(100dvh - 160px); }
@media (max-width: $breakpoint-sm) { .studio-frame { height: 840px; } .avatar-workspace:fullscreen { padding: $spacing-3; } }
</style>
