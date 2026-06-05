/**
 * 变量相关类型定义
 */

// ==================== 变量类型 ====================

export type VariableType = 'string' | 'number' | 'boolean' | 'json' | 'array' | 'object' | 'secret'
export type VariableSource = 'static' | 'input' | 'expression' | 'environment' | 'computed'
export type Environment = 'development' | 'production' | 'staging'

// ==================== 变量接口 ====================

export interface Variable {
  id?: string
  name: string
  value: unknown
  type?: VariableType
  source?: VariableSource
  environment?: Environment
  description?: string
  isSecret?: boolean
  isSystem?: boolean
  defaultValue?: unknown
  validationRules?: ValidationRule[]
  createdAt?: string
  updatedAt?: string
  createdBy?: number
}

export interface ValidationRule {
  type: 'required' | 'type' | 'range' | 'pattern' | 'custom'
  value?: unknown
  message?: string
  expression?: string
}

// ==================== 变量插值 ====================

export interface VariableInterpolation {
  raw: string
  resolved: unknown
  errors?: string[]
  warnings?: string[]
}

// ==================== 变量引用 ====================

export interface VariableReference {
  variableName: string
  nodeId?: string
  nodeName?: string
  field?: string
  usageType?: 'input' | 'output' | 'condition' | 'config'
}

// ==================== 变量作用域 ====================

export interface VariableScope {
  type: 'global' | 'workflow' | 'execution' | 'node'
  workflowId?: number
  executionId?: number
  nodeId?: string
}

// ==================== 变量变更历史 ====================

export interface VariableHistory {
  id?: string
  variableId: string
  variableName: string
  oldValue?: unknown
  newValue: unknown
  changedBy?: number
  changedByUsername?: string
  changedAt: string
  reason?: string
}

// ==================== 变量统计 ====================

export interface VariableStatistics {
  total: number
  byType: Record<VariableType, number>
  bySource: Record<VariableSource, number>
  secrets: number
  recentlyUsed: Array<{
    name: string
    lastUsedAt: string
    usageCount: number
  }>
}

// ==================== 变量组 ====================

export interface VariableGroup {
  id?: string
  name: string
  description?: string
  variables: Variable[]
  environment?: Environment
  isShared?: boolean
  createdAt?: string
  updatedAt?: string
}

// ==================== 环境变量 ====================

export interface EnvironmentVariable {
  key: string
  value: string
  isSecret?: boolean
  description?: string
  environment: Environment
}
