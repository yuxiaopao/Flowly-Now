import { computed, onBeforeUnmount, ref } from 'vue'
import { APPLICATIONS } from '@/config/applications'

export function useApplicationCollection(loader) {
  const rows = ref([])
  const page = ref(1)
  const count = ref(0)
  const loading = ref(false)
  const error = ref('')
  const pageCount = computed(() => Math.max(1, Math.ceil(count.value / APPLICATIONS.pageSize)))
  let revision = 0
  async function load(nextPage = 1) {
    const current = ++revision
    loading.value = true
    error.value = ''
    page.value = nextPage
    try {
      const result = await loader({ page: nextPage, page_size: APPLICATIONS.pageSize })
      if (current !== revision) return
      rows.value = result.results || result || []
      count.value = result.count ?? rows.value.length
    } catch (failure) { if (current === revision) error.value = failure.message || '数据加载失败，请重试。' }
    finally { if (current === revision) loading.value = false }
  }
  function reset() { revision++; rows.value = []; count.value = 0; page.value = 1; error.value = '' }
  onBeforeUnmount(() => { revision++ })
  return { rows, page, count, loading, error, pageCount, load, reset }
}

