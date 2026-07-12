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
export function getGraphData(projectId, forceRefresh = false) {
  return api.get(`/codegraph/projects/${projectId}/graph/`, {
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
export function getFileContent(projectId, filePath) {
  return api.get(`/codegraph/projects/${projectId}/file/`, {
    params: { path: filePath }
  })
}

/**
 * 搜索文件或模块
 * @param {number} projectId
 * @param {string} query
 * @param {object} options
 */
export function searchFiles(projectId, query, options = {}) {
  return api.get(`/codegraph/projects/${projectId}/search/`, {
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
  searchFiles,
  invalidateCache,
  getWebSocketUrl,
  getFileWatchWebSocketUrl,
}
