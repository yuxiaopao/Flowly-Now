/**
 * 工作流触发器相关类型定义
 */

// ==================== 触发器类型 ====================

export type TriggerType = 'manual' | 'schedule' | 'cron' | 'webhook' | 'event'
export type ScheduleType = 'once' | 'recurring' | 'cron'
export type TriggerStatus = 'active' | 'paused' | 'disabled'

// ==================== 工作流触发器 ====================

export interface WorkflowTrigger {
  id?: number
  name: string
  description?: string
  workflowId?: number
  workflow?: number
  triggerType: TriggerType
  scheduleType?: ScheduleType
  scheduledAt?: string
  intervalSeconds?: number
  cronExpression?: string
  webhookPath?: string
  webhookSecret?: string
  webhookMethod?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'
  eventType?: string
  eventSource?: string
  eventFilter?: Record<string, unknown>
  inputMapping?: Record<string, string>
  status?: TriggerStatus
  isEnabled?: boolean
  maxExecutions?: number
  executionCount?: number
  lastTriggeredAt?: string
  nextExecutionAt?: string
  createdAt?: string
  updatedAt?: string
  createdBy?: number
}

// ==================== 触发器执行记录 ====================

export interface TriggerExecution {
  id?: number
  triggerId?: number
  trigger?: WorkflowTrigger
  executionId?: number
  workflowExecutionId?: string
  triggerSource?: string
  eventData?: Record<string, unknown>
  status?: 'pending' | 'running' | 'success' | 'failed' | 'skipped'
  errorMessage?: string
  queuedAt?: string
  startedAt?: string
  completedAt?: string
  duration?: number
  inputData?: Record<string, unknown>
  outputData?: Record<string, unknown>
}

// ==================== 事件触发器配置 ====================

export interface EventTriggerConfig {
  source?: string
  eventTypes?: string[]
  filter?: Record<string, unknown>
  transformation?: string
}

// ==================== Webhook 触发器配置 ====================

export interface WebhookTriggerConfig {
  path: string
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'
  secret?: string
  authType?: 'none' | 'signature' | 'token'
  signatureHeader?: string
  signatureSecret?: string
}

// ==================== 定时触发器配置 ====================

export interface ScheduleTriggerConfig {
  scheduleType: ScheduleType
  scheduledAt?: string
  timezone?: string
  intervalSeconds?: number
  cronExpression?: string
  startDate?: string
  endDate?: string
  maxExecutions?: number
}

// ==================== 触发器统计 ====================

export interface TriggerStatistics {
  totalTriggers: number
  activeTriggers: number
  pausedTriggers: number
  totalExecutions: number
  successfulExecutions: number
  failedExecutions: number
  averageResponseTime: number
  triggersByType: Record<TriggerType, number>
  recentExecutions: TriggerExecution[]
}
