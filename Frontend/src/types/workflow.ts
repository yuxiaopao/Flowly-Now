/**
 * 工作流相关类型 - 独立于 nodes/execution 的类型
 * 所有通用类型请从 '@/types' 导入
 */

export interface Workflow {
  id: number
  name: string
  description?: string
  status: 'draft' | 'active' | 'paused' | 'archived'
  isPublished: boolean
  isPublic: boolean
  version: number
  tags: string[]
  settings: Record<string, unknown>
  owner?: User
  nodes: unknown[]
  edges: unknown[]
  createdAt: string
  updatedAt: string
}

export interface WorkflowListItem {
  id: number
  name: string
  description?: string
  status: 'draft' | 'active' | 'paused' | 'archived'
  owner: User
  nodeCount: number
  executionCount: number
  tags: string[]
  createdAt: string
  updatedAt: string
}

export interface User {
  id: number
  username: string
  email: string
  avatar?: string
}

export interface ValidationResult {
  valid: boolean
  errors: string[]
  warnings: string[]
}

// ==================== 节点数据结构 ====================

export interface WorkflowNode {
  id: string | number
  type: string
  position: { x: number; y: number }
  data: {
    label: string
    description?: string
    config: Record<string, unknown>
    errorHandling?: string
    maxRetries?: number
    retryDelay?: number
    fallbackValue?: unknown
  }
  style?: Record<string, unknown>
  class?: string
  sourcePosition?: 'left' | 'right' | 'top' | 'bottom'
  targetPosition?: 'left' | 'right' | 'top' | 'bottom'
}

// ==================== 连线数据结构 ====================

export interface WorkflowEdge {
  id: string
  source: string | number
  target: string | number
  sourceHandle?: string
  targetHandle?: string
  type?: string
  label?: string
  animated?: boolean
  style?: Record<string, unknown>
  data?: {
    condition?: Record<string, unknown>
  }
}
