import { watch, onMounted } from 'vue'
import { useAppStore } from '@/stores/app'

export function useThemeFavicon() {
  const appStore = useAppStore()

  const darkThemes = ['dark', 'pure-bw', 'high-contrast']

  function updateFavicon() {
    const isDark = darkThemes.includes(appStore.theme)
    const faviconPath = isDark ? '/logow.png' : '/logo.png'
    
    let link = document.querySelector("link[rel='icon']")
    if (link) {
      link.href = faviconPath
    }
  }

  onMounted(() => {
    updateFavicon()
  })

  watch(() => appStore.theme, () => {
    updateFavicon()
  })
}
