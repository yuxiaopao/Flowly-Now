/**
 * 触发器相关 TypeScript 类型定义
 */

/**
 * 触发器类型枚举
 */
export type TriggerType = 'manual' | 'schedule' | 'cron' | 'webhook' | 'event'

/**
 * 定时执行类型
 */
export type ScheduleType = 'once' | 'recurring'

/**
 * Webhook 认证方式
 */
export type WebhookAuthType = 'none' | 'header' | 'signature'

/**
 * 输入映射项
 */
export interface InputMapping {
  external: string
  internal: string
}

/**
 * 触发器配置
 */
export interface TriggerConfig {
  /** Cron 表达式 */
  cronExpression?: string
  /** 定时执行时间 */
  scheduledAt?: string
  /** 执行间隔（秒） */
  intervalSeconds?: number
  /** 定时类型 */
  scheduleType?: ScheduleType
  /** Webhook 认证方式 */
  authType?: WebhookAuthType
  /** Webhook 密钥 */
  webhookSecret?: string
  /** 最大执行次数，0 表示无限制 */
  maxExecutions?: number
  /** 输入映射 */
  inputMappings?: InputMapping[]
}

/**
 * 工作流触发器
 */
export interface WorkflowTrigger {
  id: number
  workflowId: number
  name: string
  description?: string
  triggerType: TriggerType
  isEnabled: boolean
  config: TriggerConfig
  executionCount: number
  lastTriggeredAt?: string
  createdAt: string
  updatedAt: string
}

/**
 * 触发器执行状态
 */
export type TriggerExecutionStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'

/**
 * 触发器执行记录
 */
export interface TriggerExecution {
  id: number
  triggerId: number
  status: TriggerExecutionStatus
  inputData?: Record<string, unknown>
  outputData?: Record<string, unknown>
  errorMessage?: string
  durationMs?: number
  queuedAt: string
  startedAt?: string
  completedAt?: string
}

/**
 * 触发器列表查询参数
 */
export interface TriggerListParams {
  page?: number
  page_size?: number
  workflow_id?: number | string
}

/**
 * Cron 表达式预设
 */
export interface CronPreset {
  label: string
  expression: string
}

/**
 * 触发器类型选项
 */
export interface TriggerTypeOption {
  value: TriggerType
  label: string
}

/**
 * 预设的 Cron 表达式模板
 */
export const CRON_PRESETS: CronPreset[] = [
  { label: '每分钟', expression: '* * * * *' },
  { label: '每小时', expression: '0 * * * *' },
  { label: '每天午夜', expression: '0 0 * * *' },
  { label: '每周一', expression: '0 0 * * 1' },
  { label: '每月1号', expression: '0 0 1 * *' },
  { label: '每10分钟', expression: '*/10 * * * *' },
  { label: '每30分钟', expression: '*/30 * * * *' },
  { label: '工作日9点', expression: '0 9 * * 1-5' },
  { label: '每天9点', expression: '0 9 * * *' },
  { label: '每天18点', expression: '0 18 * * *' },
]

/**
 * 触发器类型选项列表
 */
export const TRIGGER_TYPE_OPTIONS: TriggerTypeOption[] = [
  { value: 'manual', label: '手动触发' },
  { value: 'schedule', label: '定时触发' },
  { value: 'cron', label: 'Cron 表达式' },
  { value: 'webhook', label: 'Webhook' },
]

/**
 * 获取触发器类型标签
 * @param type - 触发器类型
 * @returns 对应标签
 */
export function getTriggerTypeLabel(type: TriggerType): string {
  const option = TRIGGER_TYPE_OPTIONS.find(o => o.value === type)
  return option?.label ?? type
}

/**
 * 获取执行状态类型（用于 Element Plus Tag）
 * @param status - 执行状态
 * @returns Tag 类型
 */
export function getExecutionStatusType(status: TriggerExecutionStatus): string {
  const typeMap: Record<TriggerExecutionStatus, string> = {
    pending: 'info',
    running: 'primary',
    completed: 'success',
    failed: 'danger',
    cancelled: 'warning',
  }
  return typeMap[status] ?? 'info'
}

/**
 * 格式化日期时间
 * @param dateStr - ISO 日期字符串
 * @returns 格式化后的日期时间字符串
 */
export function formatTriggerDate(dateStr?: string): string {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}
