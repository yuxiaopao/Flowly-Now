import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { promptApi } from '@/api/prompt'

export const usePromptStore = defineStore('prompt', () => {
  // State
  const templates = ref([])
  const currentTemplate = ref(null)
  const isLoading = ref(false)
  const isSaving = ref(false)
  const error = ref(null)

  // Categories
  const categories = ref([
    { value: 'general', label: '通用' },
    { value: 'writing', label: '写作' },
    { value: 'coding', label: '编程' },
    { value: 'analysis', label: '分析' },
    { value: 'creative', label: '创意' },
    { value: 'business', label: '商业' }
  ])

  // Variable types
  const variableTypes = ref([
    { value: 'string', label: '文本' },
    { value: 'number', label: '数字' },
    { value: 'boolean', label: '布尔' },
    { value: 'select', label: '选择' },
    { value: 'textarea', label: '多行文本' }
  ])

  // Rendered result
  const renderedContent = ref('')

  // Getters
  const featuredTemplates = computed(() =>
    templates.value.filter(t => t.is_featured)
  )

  const popularTemplates = computed(() =>
    [...templates.value].sort((a, b) => b.usage_count - a.usage_count).slice(0, 10)
  )

  const templatesByCategory = computed(() => {
    const grouped = {}
    categories.value.forEach(cat => {
      grouped[cat.value] = templates.value.filter(t => t.category === cat.value)
    })
    return grouped
  })

  // Actions
  async function fetchTemplates(params = {}) {
    isLoading.value = true
    error.value = null
    try {
      const response = await promptApi.getTemplates(params)
      templates.value = response.results || response
      return response
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function fetchTemplate(id) {
    isLoading.value = true
    error.value = null
    try {
      const response = await promptApi.getTemplate(id)
      currentTemplate.value = response
      return response
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function createTemplate(data) {
    isSaving.value = true
    error.value = null
    try {
      const response = await promptApi.createTemplate(data)
      templates.value.unshift(response)
      return response
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      isSaving.value = false
    }
  }

  async function updateTemplate(id, data) {
    isSaving.value = true
    error.value = null
    try {
      const response = await promptApi.updateTemplate(id, data)
      const index = templates.value.findIndex(t => t.id === id)
      if (index !== -1) {
        templates.value[index] = { ...templates.value[index], ...response }
      }
      if (currentTemplate.value?.id === id) {
        currentTemplate.value = { ...currentTemplate.value, ...response }
      }
      return response
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      isSaving.value = false
    }
  }

  async function deleteTemplate(id) {
    isLoading.value = true
    error.value = null
    try {
      await promptApi.deleteTemplate(id)
      templates.value = templates.value.filter(t => t.id !== id)
      if (currentTemplate.value?.id === id) {
        currentTemplate.value = null
      }
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function renderTemplate(id, context) {
    try {
      const response = await promptApi.renderTemplate(id, context)
      renderedContent.value = response.rendered
      return response
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function duplicateTemplate(id) {
    try {
      const response = await promptApi.duplicateTemplate(id)
      templates.value.unshift(response)
      return response
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function shareTemplate(id) {
    try {
      await promptApi.shareTemplate(id)
      const template = templates.value.find(t => t.id === id)
      if (template) {
        template.is_public = true
      }
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function unshareTemplate(id) {
    try {
      await promptApi.unshareTemplate(id)
      const template = templates.value.find(t => t.id === id)
      if (template) {
        template.is_public = false
      }
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  function clearRendered() {
    renderedContent.value = ''
  }

  function clearStore() {
    templates.value = []
    currentTemplate.value = null
    error.value = null
    renderedContent.value = ''
  }

  return {
    // State
    templates,
    currentTemplate,
    isLoading,
    isSaving,
    error,
    categories,
    variableTypes,
    renderedContent,

    // Getters
    featuredTemplates,
    popularTemplates,
    templatesByCategory,

    // Actions
    fetchTemplates,
    fetchTemplate,
    createTemplate,
    updateTemplate,
    deleteTemplate,
    renderTemplate,
    duplicateTemplate,
    shareTemplate,
    unshareTemplate,
    clearRendered,
    clearStore
  }
})
