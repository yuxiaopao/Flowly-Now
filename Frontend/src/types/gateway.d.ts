/**
 * Gateway API Type Definitions
 * AI Model Gateway, API Keys, and API Call Logging types.
 */

/** Model provider from the gateway */
export interface ModelProvider {
  id: string
  name: string
  slug: string
  logo_url: string | null
  website: string | null
  description: string | null
  is_active: boolean
  created_at: string
  updated_at: string
}

/** AI Model configuration */
export interface AIModel {
  id: string
  provider: string
  provider_name?: string
  provider_slug?: string
  name: string
  model_id: string
  model_type: 'chat' | 'embedding' | 'image' | 'audio'
  max_tokens: number
  supports_streaming: boolean
  supports_function_calling: boolean
  supports_vision: boolean
  input_price: number
  output_price: number
  default_temperature: number
  default_top_p: number
  is_active: boolean
  is_default: boolean
  description: string | null
  context_window: number
  released_at: string | null
  created_at: string
  updated_at: string
}

/** Simplified AI model for list views */
export interface AIModelListItem {
  id: string
  name: string
  model_id: string
  model_type: AIModel['model_type']
  provider_name: string
  is_active: boolean
  is_default: boolean
}

/** User API Key */
export interface UserAPIKey {
  id: string
  provider: string
  provider_display?: string
  name: string
  masked_key: string
  endpoint: string | null
  api_version: string | null
  is_active: boolean
  last_used_at: string | null
  total_usage: number
  created_at: string
  updated_at: string
}

/** Data for creating a new API Key */
export interface CreateAPIKeyData {
  provider: string
  name: string
  api_key: string
  endpoint?: string
  api_version?: string
}

/** API Call Log entry */
export interface APICallLog {
  id: number
  user: number
  provider: string
  model: string
  endpoint: string
  input_tokens: number
  output_tokens: number
  total_tokens: number
  latency_ms: number
  status_code: number
  error_message: string | null
  cost: number
  timestamp: string
}

/** Aggregated API usage statistics */
export interface APICallAggregate {
  total_calls: number
  total_tokens: number
  total_cost: number
  avg_latency: number
  by_provider: Record<string, number>
  by_model: Record<string, number>
}

/** Gateway health status */
export type ProviderHealthStatus = 'ok' | 'error' | 'timeout' | 'degraded'

/** Individual provider health */
export interface ProviderHealth {
  status: ProviderHealthStatus
  latency_ms: number | null
  error: string | null
  models_count: number
}

/** Gateway overall health */
export interface GatewayHealth {
  status: 'ok' | 'degraded' | 'error'
  providers: Record<string, ProviderHealth>
}

/** Gateway chat message */
export interface ChatMessage {
  role: 'system' | 'user' | 'assistant'
  content: string
}

/** Gateway chat request */
export interface GatewayChatRequest {
  messages: ChatMessage[]
  model?: string
  temperature?: number
  max_tokens?: number
  stream?: boolean
}

/** Gateway chat response */
export interface GatewayChatResponse {
  message: string
  model: string
  usage?: TokenUsage
}

/** Token usage in a response */
export interface TokenUsage {
  prompt_tokens: number
  completion_tokens: number
  total_tokens: number
}

/** Gateway embeddings request */
export interface GatewayEmbeddingsRequest {
  texts: string[]
  model?: string
  encoding_format?: 'float' | 'base64'
}

/** Gateway embeddings response */
export interface GatewayEmbeddingsResponse {
  embeddings: number[][]
  model: string
  usage: TokenUsage
}
