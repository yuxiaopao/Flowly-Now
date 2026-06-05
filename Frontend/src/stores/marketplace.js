import { defineStore } from 'pinia'
import { marketplaceApi } from '@/api/marketplace'
import {
  createFromTemplate,
} from '@/api/workflow'
import {
  getTemplateAuthor,
  getTemplateCategory,
  getTemplateFeatures,
  getTemplateNodeCount,
  getTemplateNodes,
  getTemplateRating,
  getTemplateTags,
  getTemplateUseCount,
  isTemplatePublic,
} from '@/utils/workflowTransform'

function normalizeTemplate(template) {
  if (!template) {
    return template
  }

  const displayCategory = getTemplateCategory(template)
  const displayNodeCount = getTemplateNodeCount(template)
  const displayUseCount = getTemplateUseCount(template)
  const displayRating = getTemplateRating(template)
  const displayAuthor = getTemplateAuthor(template)
  const displayNodes = getTemplateNodes(template)
  const displayFeatures = getTemplateFeatures(template)
  const displayTags = getTemplateTags(template)
  const isPublic = isTemplatePublic(template)

  return {
    ...template,
    use_count: displayUseCount,
    rating: displayRating,
    thumbnail: template?.thumbnail ?? template?.preview_image ?? '',
    is_public: isPublic,
    displayCategory,
    displayNodeCount,
    displayUseCount,
    displayRating,
    displayAuthor,
    displayNodes,
    displayFeatures,
    displayTags,
  }
}

function normalizeTemplateList(templates) {
  return (templates || []).map(normalizeTemplate)
}

function mapTemplateListById(list, templateId, updater) {
  return (list || []).map(template => template?.id === templateId ? updater(template) : template)
}

export const useMarketplaceStore = defineStore('marketplace', {
  state: () => ({
    templates: [],
    currentTemplate: null,
    categories: [],
    myTemplates: [],
    installedTemplates: [],
    featuredTemplates: [],
    categoryTemplates: [],
    isLoading: false,
    isSaving: false,
    error: null,
    filters: {
      category: null,
      tags: [],
      search: '',
      sort: 'popular',
      difficulty: '',
      tag: '',
      page: 1,
      page_size: 20,
    },
    pagination: {
      total: 0,
      page: 1,
      pageSize: 20,
    },
  }),

  getters: {
    hasMore: (state) => state.templates.length < state.pagination.total,
    featuredTemplatesGetter: (state) => state.templates.filter(t => t.is_featured),
    popularTemplates: (state) => [...state.templates].sort((a, b) => getTemplateUseCount(b) - getTemplateUseCount(a)).slice(0, 12),
    templatesByCategory: (state) => {
      const map = {}
      for (const group of state.categoryTemplates) {
        map[group.category?.slug || group.category?.id] = group.templates
      }
      return map
    },
  },

  actions: {
    patchTemplateEverywhere(templateId, updater) {
      const normalizeUpdatedTemplate = (template) => normalizeTemplate(updater(template))

      this.templates = mapTemplateListById(this.templates, templateId, normalizeUpdatedTemplate)
      this.featuredTemplates = mapTemplateListById(this.featuredTemplates, templateId, normalizeUpdatedTemplate)
      this.myTemplates = mapTemplateListById(this.myTemplates, templateId, normalizeUpdatedTemplate)
      this.installedTemplates = mapTemplateListById(this.installedTemplates, templateId, normalizeUpdatedTemplate)
      this.categoryTemplates = (this.categoryTemplates || []).map(group => ({
        ...group,
        templates: mapTemplateListById(group.templates, templateId, normalizeUpdatedTemplate),
      }))

      if (this.currentTemplate?.id === templateId) {
        this.currentTemplate = normalizeUpdatedTemplate(this.currentTemplate)
      }
    },

    replaceTemplateEverywhere(templateId, nextTemplate) {
      this.patchTemplateEverywhere(templateId, () => nextTemplate)
    },

    // ========== 使用新版 workflow.js API ==========

    async fetchCategories(params = {}) {
      try {
        const res = await marketplaceApi.getCategories(params)
        this.categories = res
        return res
      } catch (error) {
        this.error = error.message || '获取分类失败'
        throw error
      }
    },

    async fetchTemplates(params = {}) {
      this.isLoading = true
      this.error = null
      try {
        const queryParams = { ...this.filters, ...params }
        const res = await marketplaceApi.getTemplates(queryParams)
        const normalizedResults = normalizeTemplateList(res.results)
        this.templates = normalizedResults
        this.pagination.total = res.count
        this.pagination.page = Number(queryParams.page || 1)
        return {
          ...res,
          results: normalizedResults,
        }
      } catch (error) {
        this.error = error.message || '获取模板列表失败'
        console.error('fetchTemplates error:', error)
      } finally {
        this.isLoading = false
      }
    },

    async loadMoreTemplates() {
      if (this.templates.length >= this.pagination.total || this.isLoading) return
      this.pagination.page += 1
      try {
        const res = await marketplaceApi.getTemplates({
          ...this.filters,
          page: this.pagination.page,
        })
        const newTemplates = normalizeTemplateList(res.results)
        this.templates.push(...newTemplates)
        this.pagination.total = res.count
        return {
          ...res,
          results: newTemplates,
        }
      } catch (error) {
        this.error = error.message || '加载更多失败'
        this.pagination.page -= 1
      }
    },

    async fetchFeatured(params = {}) {
      try {
        const res = await marketplaceApi.getFeaturedTemplates(params)
        this.featuredTemplates = normalizeTemplateList(res.results)
        return {
          ...res,
          results: this.featuredTemplates,
        }
      } catch (error) {
        this.error = error.message || '获取精选模板失败'
        console.error('fetchFeatured error:', error)
        throw error
      }
    },

    async fetchByCategory() {
      this.isLoading = true
      this.error = null
      try {
        const res = await marketplaceApi.getTemplatesByCategory()
        this.categoryTemplates = (res || []).map(group => ({
          ...group,
          templates: normalizeTemplateList(group.templates),
        }))
        return this.categoryTemplates
      } catch (error) {
        this.error = error.message || '获取分类模板失败'
        console.error('fetchByCategory error:', error)
        throw error
      } finally {
        this.isLoading = false
      }
    },

    async fetchTemplate(id) {
      this.isLoading = true
      this.error = null
      try {
        const res = await marketplaceApi.getTemplate(id)
        this.currentTemplate = normalizeTemplate(res)
        return this.currentTemplate
      } catch (error) {
        this.error = error.message || '获取模板详情失败'
        console.error('fetchTemplate error:', error)
        throw error
      } finally {
        this.isLoading = false
      }
    },

    async applyTemplate(templateId, data = {}) {
      this.isLoading = true
      this.error = null
      try {
        return await createFromTemplate(templateId, data)
      } catch (error) {
        this.error = error.message || '创建工作流失败'
        throw error
      } finally {
        this.isLoading = false
      }
    },

    // ========== 使用 marketplaceApi ==========

    async fetchCategoryTemplates(categoryId, params = {}) {
      try {
        const res = await marketplaceApi.getCategoryTemplates(categoryId, params)
        return {
          ...res,
          results: normalizeTemplateList(res.results),
        }
      } catch (error) {
        this.error = error.message
        throw error
      }
    },

    async installTemplate(id) {
      this.isSaving = true
      try {
        const res = await marketplaceApi.installTemplate(id)
        this.patchTemplateEverywhere(id, (template) => {
          const nextUseCount = getTemplateUseCount(template) + 1
          return {
            ...template,
            is_installed: true,
            use_count: nextUseCount,
          }
        })
        return res
      } catch (error) {
        this.error = error.message
        throw error
      } finally {
        this.isSaving = false
      }
    },

    async rateTemplate(id, rating) {
      try {
        const res = await marketplaceApi.rateTemplate(id, rating)
        const ratingData = res

        this.patchTemplateEverywhere(id, (template) => ({
          ...template,
          rating: ratingData?.rating ?? ratingData?.avg_rating ?? template.rating,
          avg_rating: ratingData?.avg_rating ?? ratingData?.rating ?? template.avg_rating,
          rating_count: ratingData?.rating_count ?? template.rating_count,
        }))

        return res
      } catch (error) {
        this.error = error.message
        throw error
      }
    },

    async createTemplate(data) {
      this.isSaving = true
      try {
        const res = await marketplaceApi.createTemplate(data)
        const normalized = normalizeTemplate(res)
        this.myTemplates.unshift(normalized)
        return normalized
      } catch (error) {
        this.error = error.message
        throw error
      } finally {
        this.isSaving = false
      }
    },

    async updateTemplate(id, data) {
      this.isSaving = true
      try {
        const res = await marketplaceApi.updateTemplate(id, data)
        const normalized = normalizeTemplate(res)
        this.replaceTemplateEverywhere(id, normalized)
        return normalized
      } catch (error) {
        this.error = error.message
        throw error
      } finally {
        this.isSaving = false
      }
    },

    async publishTemplate(id) {
      try {
        const res = await marketplaceApi.publishTemplate(id)
        const normalized = normalizeTemplate(res)
        this.replaceTemplateEverywhere(id, normalized)
        return normalized
      } catch (error) {
        this.error = error.message
        throw error
      }
    },

    async unpublishTemplate(id) {
      try {
        const res = await marketplaceApi.unpublishTemplate(id)
        const normalized = normalizeTemplate(res)
        this.replaceTemplateEverywhere(id, normalized)
        return normalized
      } catch (error) {
        this.error = error.message
        throw error
      }
    },

    async fetchMyTemplates(params = {}) {
      this.isLoading = true
      try {
        const res = await marketplaceApi.getMyTemplates(params)
        this.myTemplates = normalizeTemplateList(res.results)
        return res
      } catch (error) {
        this.error = error.message
        throw error
      } finally {
        this.isLoading = false
      }
    },

    async fetchInstalledTemplates(params = {}) {
      try {
        const res = await marketplaceApi.getInstalledTemplates(params)
        this.installedTemplates = normalizeTemplateList(res.results)
        return res
      } catch (error) {
        this.error = error.message
        throw error
      }
    },

    // ========== 筛选与重置 ==========

    setFilters(filters) {
      this.filters = { ...this.filters, ...filters }
      this.pagination.page = 1
    },

    clearFilters() {
      this.filters = {
        category: null,
        tags: [],
        search: '',
        sort: 'popular',
        difficulty: '',
        tag: '',
        page: 1,
        page_size: 20,
      }
      this.pagination.page = 1
    },

    reset() {
      this.templates = []
      this.currentTemplate = null
      this.categories = []
      this.featuredTemplates = []
      this.categoryTemplates = []
      this.myTemplates = []
      this.installedTemplates = []
      this.isLoading = false
      this.isSaving = false
      this.error = null
      this.pagination = { total: 0, page: 1, pageSize: 20 }
    },
  },
})
