/**
 * 数据增强 API 服务
 * @description 提供数据增强任务的管理和状态查询
 */

import { request } from './index'

// =============================================================================
// 类型定义
// =============================================================================

/**
 * @typedef {Object} AugmentationRunParams
 * @property {string} dataset_id - 数据集ID
 * @property {string} [strategy='all'] - 增强策略 (geometric, color, noise, mixup, all)
 * @property {number} [ratio=2.0] - 增强倍数
 * @property {string[]} [transformations=[]] - 具体变换配置
 * @property {string} [output_mode='create_new'] - 输出模式 (create_new, overwrite)
 * @property {string} [output_name=''] - 输出数据集名称
 */

/**
 * @typedef {Object} AugmentationJob
 * @property {string} id - 任务ID
 * @property {string} input_dataset - 输入数据集ID
 * @property {string} input_dataset_name - 输入数据集名称
 * @property {string} [output_dataset] - 输出数据集ID
 * @property {string} [output_dataset_name] - 输出数据集名称
 * @property {string} strategy - 增强策略
 * @property {string} strategy_display - 策略显示名称
 * @property {number} ratio - 增强倍数
 * @property {string[]} transformations - 变换配置
 * @property {number} augmented_count - 增强后样本数
 * @property {number} original_count - 原始样本数
 * @property {string} status - 状态 (pending, running, completed, failed)
 * @property {string} status_display - 状态显示名称
 * @property {number} progress - 进度百分比
 * @property {string} output_mode - 输出模式
 * @property {string} output_dir - 输出目录
 * @property {string} output_name - 输出数据集名称
 * @property {string} error_message - 错误信息
 * @property {string} created_by - 创建者ID
 * @property {string} creator_name - 创建者名称
 * @property {string} created_at - 创建时间
 * @property {string} [started_at] - 开始时间
 * @property {string} [completed_at] - 完成时间
 * @property {number} [duration_seconds] - 持续时间(秒)
 * @property {boolean} is_complete - 是否完成
 */

/**
 * @typedef {Object} AugmentationStatus
 * @property {string} id - 任务ID
 * @property {string} status - 状态
 * @property {string} status_display - 状态显示名称
 * @property {number} progress - 进度百分比
 * @property {number} augmented_count - 增强后样本数
 * @property {number} original_count - 原始样本数
 * @property {string} error_message - 错误信息
 * @property {string} started_at - 开始时间
 * @property {string} completed_at - 完成时间
 * @property {number} duration_seconds - 持续时间(秒)
 */

/**
 * @typedef {Object} AugmentationPreset
 * @property {string} id - 预设ID
 * @property {string} name - 预设名称
 * @property {string} description - 预设描述
 * @property {string} strategy - 增强策略
 * @property {number} ratio - 增强倍数
 * @property {string[]} transformations - 变换配置
 * @property {string} recommended_for - 推荐用于
 */

// =============================================================================
// API 函数
// =============================================================================

/**
 * 运行数据增强任务
 * @param {AugmentationRunParams} data - 增强参数
 * @returns {Promise<AugmentationJob>} 创建的增强任务
 * @throws {RequestError}
 * @example
 * const job = await runAugmentation({
 *   dataset_id: 'uuid-string',
 *   strategy: 'all',
 *   ratio: 2.0,
 *   output_name: 'my_augmented_dataset'
 * })
 */
export async function runAugmentation(data) {
  return request.post('/augmentations/run/', data)
}

/**
 * 获取增强任务详情
 * @param {string} id - 任务ID
 * @returns {Promise<AugmentationJob>} 任务详情
 * @throws {RequestError}
 * @example
 * const job = await getAugmentationJob('job-uuid')
 */
export async function getAugmentationJob(id) {
  return request.get(`/augmentations/${id}/`)
}

/**
 * 获取增强任务列表
 * @param {Object} [params] - 查询参数
 * @param {string} [params.status] - 状态筛选
 * @param {string} [params.strategy] - 策略筛选
 * @param {string} [params.dataset] - 数据集ID筛选
 * @param {string} [params.search] - 搜索关键词
 * @param {number} [params.page] - 页码
 * @param {number} [params.page_size] - 每页数量
 * @returns {Promise<{count: number, results: AugmentationJob[]}>}
 * @throws {RequestError}
 * @example
 * const { results } = await listAugmentationJobs({ status: 'completed' })
 */
export async function listAugmentationJobs(params = {}) {
  return request.get('/augmentations/', params)
}

/**
 * 获取增强任务状态
 * @param {string} id - 任务ID
 * @returns {Promise<AugmentationStatus>} 任务状态
 * @throws {RequestError}
 * @example
 * const status = await getAugmentationStatus('job-uuid')
 * console.log(status.progress, status.status)
 */
export async function getAugmentationStatus(id) {
  return request.get(`/augmentations/${id}/status/`)
}

/**
 * 取消增强任务
 * @param {string} id - 任务ID
 * @returns {Promise<{message: string}>}
 * @throws {RequestError}
 * @example
 * await cancelAugmentationJob('job-uuid')
 */
export async function cancelAugmentationJob(id) {
  return request.post(`/augmentations/${id}/cancel/`)
}

/**
 * 重试增强任务
 * @param {string} id - 任务ID
 * @returns {Promise<AugmentationJob>}
 * @throws {RequestError}
 * @example
 * const job = await retryAugmentationJob('job-uuid')
 */
export async function retryAugmentationJob(id) {
  return request.post(`/augmentations/${id}/retry/`)
}

/**
 * 获取增强任务统计
 * @returns {Promise<Object>} 统计数据
 * @property {number} total_jobs - 总任务数
 * @property {number} completed_jobs - 已完成任务数
 * @property {number} failed_jobs - 失败任务数
 * @property {number} running_jobs - 运行中任务数
 * @property {number} total_augmented_samples - 总增强样本数
 * @property {number} total_original_samples - 总原始样本数
 * @throws {RequestError}
 * @example
 * const stats = await getAugmentationStatistics()
 */
export async function getAugmentationStatistics() {
  return request.get('/augmentations/statistics/')
}

/**
 * 获取增强预设配置
 * @returns {Promise<AugmentationPreset[]>}
 * @throws {RequestError}
 * @example
 * const presets = await getAugmentationPresets()
 * console.log(presets[0].transformations)
 */
export async function getAugmentationPresets() {
  return request.get('/augmentations/presets/')
}

/**
 * 删除增强任务
 * @param {string} id - 任务ID
 * @returns {Promise<void>}
 * @throws {RequestError}
 * @example
 * await deleteAugmentationJob('job-uuid')
 */
export async function deleteAugmentationJob(id) {
  return request.delete(`/augmentations/${id}/`)
}

// =============================================================================
// 导出 API 对象
// =============================================================================

export const augmentationApi = {
  // 核心操作
  run: runAugmentation,
  get: getAugmentationJob,
  list: listAugmentationJobs,
  status: getAugmentationStatus,
  cancel: cancelAugmentationJob,
  retry: retryAugmentationJob,
  delete: deleteAugmentationJob,

  // 辅助功能
  getStatistics: getAugmentationStatistics,
  getPresets: getAugmentationPresets,
}

export default augmentationApi
