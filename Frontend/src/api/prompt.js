import { request } from './index'

export const promptApi = {
  /**
   * 获取模板列表
   */
  getTemplates(params = {}) {
    return request.get('/prompts/templates/', params)
  },

  /**
   * 获取模板详情
   */
  getTemplate(id) {
    return request.get(`/prompts/templates/${id}/`)
  },

  /**
   * 创建模板
   */
  createTemplate(data) {
    return request.post('/prompts/templates/', data)
  },

  /**
   * 更新模板
   */
  updateTemplate(id, data) {
    return request.patch(`/prompts/templates/${id}/`, data)
  },

  /**
   * 删除模板
   */
  deleteTemplate(id) {
    return request.delete(`/prompts/templates/${id}/`)
  },

  /**
   * 渲染模板
   */
  renderTemplate(id, context) {
    return request.post(`/prompts/templates/${id}/render/`, { context })
  },

  /**
   * 获取热门模板
   */
  getPopular(limit = 10) {
    return request.get('/prompts/templates/popular/', { limit })
  },

  /**
   * 获取推荐模板
   */
  getFeatured() {
    return request.get('/prompts/templates/featured/')
  },

  /**
   * 获取分类列表
   */
  getCategories() {
    return request.get('/prompts/categories/')
  },

  /**
   * 复制模板
   */
  duplicateTemplate(id) {
    return request.post(`/prompts/templates/${id}/duplicate/`)
  },

  /**
   * 分享模板
   */
  shareTemplate(id) {
    return request.post(`/prompts/templates/${id}/share/`)
  },

  /**
   * 取消分享模板
   */
  unshareTemplate(id) {
    return request.post(`/prompts/templates/${id}/unshare/`)
  },

  /**
   * 获取变量类型列表
   */
  getVariableTypes() {
    return request.get('/prompts/variables/types/')
  }
}

export default promptApi
