/**
 * CodeGraph API 封装
 */

import api from './index'
import { getWebSocketUrl as buildWebSocketUrl } from '@/config'

/**
 * 获取项目列表
 */
export function getProjects() {
  return api.get('/codegraph/projects/')
}

/**
 * 获取项目详情
 * @param {number} projectId
 */
export function getProject(projectId) {
  return api.get(`/codegraph/projects/${projectId}/`)
}

/**
 * 获取项目代码结构
 * @param {number} projectId
 */
export function getProjectStructure(projectId) {
  return api.get(`/codegraph/projects/${projectId}/structure/`)
}

/**
 * 获取依赖图数据
 * @param {number} projectId
 * @param {boolean} forceRefresh
 */
export function getGraphData(projectId, forceRefresh = false, config = {}) {
  return api.get(`/codegraph/projects/${projectId}/graph/`, {
    ...config,
    params: { force_refresh: forceRefresh }
  })
}

/**
 * 获取图统计信息
 * @param {number} projectId
 */
export function getGraphStats(projectId) {
  return api.get(`/codegraph/projects/${projectId}/stats/`)
}

/**
 * 触发项目重新分析
 * @param {number} projectId
 * @param {object} options
 */
export function analyzeProject(projectId, options = {}) {
  return api.post(`/codegraph/projects/${projectId}/analyze/`, options)
}

/**
 * 获取模块列表
 * @param {number} projectId
 */
export function getModules(projectId) {
  return api.get(`/codegraph/projects/${projectId}/modules/`)
}

/**
 * 获取模块依赖关系
 * @param {number} projectId
 */
export function getModuleDependencies(projectId) {
  return api.get(`/codegraph/projects/${projectId}/modules/dependencies/`)
}

/**
 * 获取文件内容
 * @param {number} projectId
 * @param {string} filePath
 */
export function getFileContent(projectId, filePath, config = {}) {
  return api.get(`/codegraph/projects/${projectId}/file/`, {
    ...config,
    params: { path: filePath }
  })
}

/**
 * AI 解读文件用途
 * @param {number} projectId
 * @param {object} payload - { path, module, type, indegree, outdegree, centrality }
 */
export function explainFile(projectId, payload, config = {}) {
  return api.post(`/codegraph/projects/${projectId}/file/explain/`, payload, config)
}

/**
 * CodeGraph 分析助手问答
 * @param {number} projectId
 * @param {object} payload - { message, history?, selected_path?, selected_node_id? }
 */
export function askAssistant(projectId, payload, config = {}) {
  return api.post(`/codegraph/projects/${projectId}/assistant/ask/`, payload, config)
}

/**
 * 搜索文件或模块
 * @param {number} projectId
 * @param {string} query
 * @param {object} options
 */
export function searchFiles(projectId, query, options = {}, config = {}) {
  return api.get(`/codegraph/projects/${projectId}/search/`, {
    ...config,
    params: {
      q: query,
      ...options
    }
  })
}

/**
 * 失效项目缓存
 * @param {number} projectId
 */
export function invalidateCache(projectId) {
  return api.post(`/codegraph/projects/${projectId}/cache/`)
}

/**
 * 获取 WebSocket 连接 URL
 * @param {number} projectId
 */
export function getWebSocketUrl(projectId) {
  return buildWebSocketUrl(`/ws/${projectId}/`)
}

/**
 * 获取文件监视 WebSocket 连接 URL
 * @param {number} projectId
 */
export function getFileWatchWebSocketUrl(projectId) {
  return buildWebSocketUrl(`/ws/${projectId}/files/`)
}

export default {
  getProjects,
  getProject,
  getProjectStructure,
  getGraphData,
  getGraphStats,
  analyzeProject,
  getModules,
  getModuleDependencies,
  getFileContent,
  explainFile,
  askAssistant,
  searchFiles,
  invalidateCache,
  getWebSocketUrl,
  getFileWatchWebSocketUrl,
}
