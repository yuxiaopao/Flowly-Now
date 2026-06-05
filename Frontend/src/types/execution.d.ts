/**
 * 工作流执行相关类型定义
 */

// ==================== 执行状态 ====================

export type ExecutionStatus = 
  | 'pending' 
  | 'running' 
  | 'paused' 
  | 'completed' 
  | 'failed' 
  | 'cancelled'

export type NodeExecutionStatus = 
  | 'pending' 
  | 'running' 
  | 'completed' 
  | 'failed' 
  | 'skipped'
  | 'retrying'

// ==================== 执行事件 ====================

export type ExecutionEventType = 
  | 'execution_start' 
  | 'execution_complete' 
  | 'execution_error'
  | 'execution_paused' 
  | 'execution_resume' 
  | 'execution_timeout'
  | 'execution_cancelled' 
  | 'node_start' 
  | 'node_complete' 
  | 'node_error'
  | 'stream'

export interface ExecutionEvent {
  type: ExecutionEventType
  execution_id: number
  data: Record<string, unknown>
  timestamp?: string
}

export interface StreamEvent extends ExecutionEvent {
  content?: string
  delta?: string
  done?: boolean
}

export interface NodeEvent extends ExecutionEvent {
  nodeId: string
  nodeName?: string
  status: NodeExecutionStatus
}

// ==================== 节点状态摘要 ====================

export interface NodeStatusSummary {
  total: number
  pending: number
  running: number
  completed: number
  failed: number
  skipped: number
}

// ==================== 执行日志条目 ====================

export interface ExecutionLogEntry {
  nodeId: string | number
  nodeName?: string
  status: NodeExecutionStatus
  startedAt?: string
  completedAt?: string
  duration?: number
  inputData?: Record<string, unknown>
  outputData?: Record<string, unknown>
  errorMessage?: string
  retryCount?: number
  usedFallback?: boolean
  logs?: string[]
}

// ==================== 工作流执行记录 ====================

export interface WorkflowExecution {
  id: number
  workflow: number
  workflowName: string
  version: number
  status: ExecutionStatus
  inputData: Record<string, unknown>
  outputData: Record<string, unknown>
  errorMessage?: string
  traceback?: string
  nodeStatus: Record<string, NodeExecutionStatus>
  nodeStatusSummary?: NodeStatusSummary
  executionLogs: ExecutionLogEntry[]
  startedAt?: string
  completedAt?: string
  duration?: number
  triggeredBy?: {
    id: number
    username: string
    email: string
    avatar?: string
  }
  triggerType: string
  triggerSource?: Record<string, unknown>
  taskId?: string
  progress: number
  currentNodeId?: number
}

// ==================== 执行请求与响应 ====================

export interface ExecutionRequest {
  inputData?: Record<string, unknown>
  triggerType?: string
  isAsync?: boolean
}

export interface ExecutionResponse {
  executionId: number
  taskId?: string
  status: ExecutionStatus
  message?: string
  streamUrl?: string
  outputData?: Record<string, unknown>
  errorMessage?: string
}

// ==================== Diff 相关类型 ====================

export type DiffStatus = 'added' | 'removed' | 'modified' | 'unchanged'

export interface DiffNodeChange {
  id: string
  type: string
  name?: string
  status: DiffStatus
  changes?: Record<string, { old: unknown; new: unknown }>
}

export interface DiffEdgeChange {
  id: string
  source: string
  target: string
  label?: string
  status: DiffStatus
}

export interface DiffSummary {
  nodesAdded: number
  nodesRemoved: number
  nodesModified: number
  edgesAdded: number
  edgesRemoved: number
  unchanged: number
}

export interface DiffResult {
  summary: DiffSummary
  nodes: DiffNodeChange[]
  edges: DiffEdgeChange[]
  rawDiff: Record<string, unknown>
}

// ==================== 执行统计 ====================

export interface ExecutionStatistics {
  total: number
  completed: number
  failed: number
  running: number
  averageDuration: number
  successRate: number
  executionsByDay: Array<{
    date: string
    count: number
    success: number
    failed: number
  }>
  topFailingNodes: Array<{
    nodeId: string
    nodeName: string
    failureCount: number
  }>
}

// ==================== 执行结果 ====================

export interface ExecutionResult {
  executionId: number
  workflowId: number
  workflowName: string
  status: ExecutionStatus
  inputData: Record<string, unknown>
  outputData: Record<string, unknown>
  errorMessage?: string
  duration?: number
  startedAt: string
  completedAt?: string
  nodeResults?: Array<{
    nodeId: string
    nodeName: string
    status: NodeExecutionStatus
    input: unknown
    output: unknown
    duration?: number
    error?: string
  }>
}

// ==================== Execution Log (API model) ====================

export interface APIExecutionLog {
  id: string
  execution: number
  node_execution: string | null
  node_name?: string
  level: 'DEBUG' | 'INFO' | 'WARNING' | 'ERROR'
  message: string
  details: Record<string, unknown>
  timestamp: string
}
