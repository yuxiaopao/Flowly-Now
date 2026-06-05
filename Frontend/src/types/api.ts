/**
 * 响应格式类型定义
 */
export interface ApiResponse<T = unknown> {
  code: number
  data: T
  message: string
  errors?: Record<string, string[]>
}

export interface PaginatedResponse<T = unknown> {
  count: number
  total_pages: number
  current_page: number
  page_size: number
  next: string | null
  previous: string | null
  results: T[]
}

export interface ListResponse<T = unknown> {
  results: T[]
  count?: number
  next?: string | null
  previous?: string | null
}

/**
 * 错误响应类型
 */
export interface ApiError {
  code: number
  message: string
  errors?: Record<string, string[]>
}

/**
 * 请求配置类型
 */
export interface RequestConfig {
  loading?: boolean
  error?: boolean
  timeout?: number
  headers?: Record<string, string>
  [key: string]: unknown
}

/**
 * 分页参数
 */
export interface PaginationParams {
  page?: number
  page_size?: number
}

/**
 * 排序参数
 */
export interface SortParams {
  ordering?: string
}
