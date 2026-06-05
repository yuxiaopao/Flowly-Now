/**
 * Agent 相关类型定义
 */

// ==================== LLM 提供商 ====================

export type LLMProvider = 'openai' | 'anthropic' | 'ollama' | 'azure' | 'gemini' | 'local'

// ==================== Agent 类型 ====================

export type AgentType = 'chat' | 'reasoning' | 'tool_calling' | 'custom' | 'agentic'

// ==================== Agent 接口 ====================

export interface Agent {
  id: string
  name: string
  description?: string
  agentType?: AgentType
  model?: string
  provider?: LLMProvider
  systemPrompt?: string
  tools?: AgentTool[]
  memoryConfig?: AgentMemoryConfig
  createdAt?: string
  updatedAt?: string
  owner?: number
  isPublic?: boolean
  settings?: AgentSettings
}

export interface AgentMemoryConfig {
  enabled?: boolean
  maxMessages?: number
  windowType?: 'sliding' | 'summary'
  summaryType?: 'last' | 'first' | 'condensed'
  includeSystemPrompt?: boolean
}

export interface AgentSettings {
  temperature?: number
  maxTokens?: number
  topP?: number
  frequencyPenalty?: number
  presencePenalty?: number
  stopSequences?: string[]
  streaming?: boolean
}

// ==================== Agent Tool 工具接口 ====================

export type ToolType = 'builtin' | 'api' | 'script' | 'custom' | 'workflow'

export interface ToolDefinition {
  endpoint?: string
  method?: string
  parameters?: Record<string, ToolParameterSchema>
  parametersArray?: ToolParameter[]
  script?: string
  handler?: string
  inputSchema?: Record<string, unknown>
  outputSchema?: Record<string, unknown>
}

export interface ToolParameterSchema {
  type: 'string' | 'number' | 'boolean' | 'object' | 'array'
  description?: string
  required?: boolean
  default?: unknown
  enum?: string[]
  minimum?: number
  maximum?: number
}

export interface ToolParameter {
  name: string
  value: string
  type?: 'static' | 'variable' | 'expression'
}

export interface ToolRetryPolicy {
  maxRetries?: number
  retryDelay?: number
  exponentialBackoff?: boolean
}

export interface AgentTool {
  id?: string
  name: string
  description?: string
  type?: ToolType
  definition?: ToolDefinition
  credential?: string
  retryPolicy?: ToolRetryPolicy
  cacheEnabled?: boolean
  cacheTtlSeconds?: number
  enabled?: boolean
  category?: string
  icon?: string
  metadata?: Record<string, unknown>
}

// ==================== Agent 执行 ====================

export interface AgentExecution {
  id: string
  agentId: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  input: Record<string, unknown>
  output?: Record<string, unknown>
  error?: string
  messages?: AgentMessage[]
  toolsUsed?: string[]
  createdAt?: string
  completedAt?: string
  duration?: number
}

export interface AgentMessage {
  id?: string
  role: 'user' | 'assistant' | 'system' | 'tool'
  content: string
  toolCalls?: Array<{
    id: string
    name: string
    arguments: Record<string, unknown>
  }>
  toolResults?: Array<{
    toolCallId: string
    result: unknown
    error?: string
  }>
  createdAt?: string
}

// ==================== Agent 模板 ====================

export interface AgentTemplate {
  id: string
  name: string
  description: string
  icon: string
  category: string
  defaultConfig: Partial<Agent>
  variables?: Array<{
    name: string
    label: string
    type: string
    required: boolean
    default?: unknown
  }>
}
