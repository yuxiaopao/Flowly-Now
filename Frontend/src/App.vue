<template>
  <div :data-theme="appStore.theme">
    <component :is="layoutComponent">
      <router-view v-slot="{ Component }">
        <KeepAlive :include="['WorkflowEditor']">
          <component
            :is="Component"
            v-if="Component"
          />
        </KeepAlive>
      </router-view>
    </component>

    <!-- Global components -->
    <CommandPalette ref="commandPaletteRef" />
    <ToastContainer />
    <GlobalModal />
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import AppLayout from '@/layouts/AppLayout.vue'
import PublicLayout from '@/layouts/PublicLayout.vue'
import EditorLayout from '@/layouts/EditorLayout.vue'
import CommandPalette from '@/components/common/CommandPalette.vue'
import ToastContainer from '@/components/common/ToastContainer.vue'
import GlobalModal from '@/components/common/GlobalModal.vue'
import { useAppStore } from '@/stores/app'
import { useAuthStore } from '@/stores/auth'
import { useSiteConfigStore } from '@/stores/siteConfig'
import { useThemeFavicon } from '@/composables/useThemeFavicon'
import { useDesktopAgentBridge } from '@/composables/useDesktopAgentBridge'

const route = useRoute()
const appStore = useAppStore()
const authStore = useAuthStore()
const siteConfigStore = useSiteConfigStore()
const commandPaletteRef = ref(null)

// Initialize theme favicon
useThemeFavicon()

// Electron: auto-connect GPU agent when user is authenticated
useDesktopAgentBridge(authStore)

const layoutComponent = computed(() => {
  const layout = route.meta.layout
  switch (layout) {
    case 'blank':
      return 'div'
    case 'editor':
      return EditorLayout
    case 'public':
      return PublicLayout
    case 'default':
    default:
      return AppLayout
  }
})

onMounted(async () => {
  appStore.init()
  siteConfigStore.fetchPublicConfig()

  if (authStore.token && !authStore.user) {
    try {
      await authStore.fetchUserInfo()
    } catch {
      // Silent failure on init - user can proceed without auth
    }
  }
})

// Provide command palette access via app store for global keyboard shortcut
appStore.openCommandPalette = () => {
  commandPaletteRef.value?.open()
}
</script>

<style lang="scss">
@use '@/assets/styles/css-variables.scss';
@use '@/assets/styles/global.scss';
</style>
