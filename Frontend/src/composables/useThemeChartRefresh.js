import { watch, nextTick } from 'vue'
import { useAppStore } from '@/stores/app'

/**
 * Re-render charts when the global theme changes.
 * Waits for data-theme CSS variables to settle before calling refresh.
 */
export function useThemeChartRefresh(refreshCallback) {
  const appStore = useAppStore()

  watch(
    () => appStore.theme,
    async () => {
      await nextTick()
      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          refreshCallback?.()
        })
      })
    },
  )
}
