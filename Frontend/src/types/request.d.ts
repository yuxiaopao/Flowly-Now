/**
 * TypeScript type definitions for the request utility and API layer.
 */

import type { AxiosRequestConfig, AxiosResponse } from 'axios'

/** Unified API response wrapper used by the backend */
export interface ApiResponse<T = unknown> {
  code?: number
  message?: string
  data: T
}

/** Paginated list response */
export interface PaginatedResponse<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

/** Standard request parameters for list endpoints */
export interface ListParams {
  page?: number
  page_size?: number
  search?: string
  ordering?: string
}

/** HTTP error response from backend */
export interface ApiError {
  detail?: string
  message?: string
  error?: string
  error_message?: string
  errors?: Record<string, string[]>
}

/** Request utility configuration options */
export interface RequestConfig extends AxiosRequestConfig {
  /** Skip automatic error toast notification */
  silent?: boolean
  /** Custom error message override */
  errorMessage?: string
}

/** Stream event data from SSE endpoints */
export interface StreamEvent {
  event: string
  data: string | number | object
}

/** Token stats from execution responses */
export interface TokenStats {
  prompt: number
  completion: number
  total: number
}
