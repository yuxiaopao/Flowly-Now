/**
 * Flowly API TypeScript Type Definitions
 * Version: 1.0.0
 * 
 * This file contains shared type definitions for the Flowly API.
 * Import these types in both frontend and backend code to ensure type consistency.
 */

// =============================================================================
// Common Types
// =============================================================================

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface ErrorResponse {
  error: string;
  detail?: string;
  code?: string;
}

// =============================================================================
// User & Authentication
// =============================================================================

export interface UserSimple {
  id: number;
  username: string;
  email: string;
  avatar: string | null;
}

export interface User extends UserSimple {
  first_name?: string;
  last_name?: string;
  role?: 'admin' | 'developer' | 'user';
  phone?: string;
  bio?: string;
  default_model?: string;
  total_executions?: number;
  monthly_executions?: number;
  execution_limit?: number;
  created_at?: string;
  last_login_at?: string;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  access: string;
  refresh: string;
  user: UserSimple;
}

export interface RegisterRequest {
  username: string;
  email: string;
  password: string;
  password_confirm: string;
  first_name?: string;
  last_name?: string;
  phone?: string;
}

export interface RegisterResponse {
  id: number;
  username: string;
  email: string;
  access: string;
  refresh: string;
}

export interface ChangePasswordRequest {
  old_password: string;
  new_password: string;
  new_password_confirm: string;
}

// =============================================================================
// Workflows
// =============================================================================

export interface WorkflowList {
  id: number;
  name: string;
  description: string;
  owner: UserSimple;
  status: 'draft' | 'active' | 'paused' | 'archived';
  status_display?: string;
  is_published: boolean;
  is_public: boolean;
  version: number;
  tags: string[];
  node_count: number;
  execution_count: number;
  created_at: string;
  updated_at: string;
}

export interface WorkflowDetail extends WorkflowList {
  settings: Record<string, unknown>;
  parent: number | null;
  nodes: Node[];
  edges: Edge[];
}

export interface WorkflowCreate {
  name: string;
  description?: string;
  status?: 'draft' | 'active' | 'paused';
  is_published?: boolean;
  is_public?: boolean;
  tags?: string[];
  settings?: Record<string, unknown>;
  nodes?: NodeCreate[];
  edges?: EdgeCreate[];
}

export interface WorkflowUpdate {
  name?: string;
  description?: string;
  status?: 'draft' | 'active' | 'paused' | 'archived';
  is_published?: boolean;
  is_public?: boolean;
  tags?: string[];
  settings?: Record<string, unknown>;
}

export interface WorkflowExecuteRequest {
  input_data?: Record<string, unknown>;
  trigger_type?: 'manual' | 'webhook' | 'scheduled' | 'api';
  is_async?: boolean;
}

export interface WorkflowValidateResponse {
  valid: boolean;
  errors: string[];
  warnings: string[];
}

// =============================================================================
// Nodes
// =============================================================================

export interface Node {
  id: number;
  workflow: number;
  node_type: string;
  node_type_display?: string;
  name: string;
  description?: string;
  position_x: number;
  position_y: number;
  config: Record<string, unknown>;
  style: Record<string, unknown>;
  created_at?: string;
  updated_at?: string;
}

export interface NodeCreate {
  node_type: string;
  name: string;
  description?: string;
  position_x?: number;
  position_y?: number;
  config?: Record<string, unknown>;
  style?: Record<string, unknown>;
}

export interface NodePosition {
  id: number;
  position: {
    x: number;
    y: number;
  };
}

export interface AvailableNodeType {
  type: string;
  label: string;
  category: string;
  description: string;
}

// =============================================================================
// Edges
// =============================================================================

export interface Edge {
  id: number;
  workflow: number;
  source_node: number;
  source_node_name?: string;
  target_node: number;
  target_node_name?: string;
  label?: string;
  type: string;
  animated: boolean;
  condition?: Record<string, unknown>;
}

export interface EdgeCreate {
  source_node: number;
  target_node: number;
  label?: string;
  type?: string;
  animated?: boolean;
  condition?: Record<string, unknown>;
}

// =============================================================================
// Executions
// =============================================================================

export interface Execution {
  id: number;
  workflow: number;
  workflow_name?: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  status_display?: string;
  trigger_type: string;
  started_at: string;
  completed_at: string | null;
  duration?: number;
}

export interface ExecutionDetail extends Execution {
  input_data: Record<string, unknown>;
  output_data: Record<string, unknown>;
  error_message?: string;
  node_status?: Record<string, unknown>;
}

export interface ExecutionLogs {
  node_status: Record<string, unknown>;
  error_message: string | null;
  traceback: string | null;
}

// =============================================================================
// Agents
// =============================================================================

export interface AgentList {
  id: number;
  name: string;
  description: string;
  agent_type: 'conversational' | 'task' | 'research' | 'coding';
  model: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface AgentDetail extends AgentList {
  system_prompt?: string;
  temperature: number;
  max_tokens: number;
  tools: string[];
  skills: string[];
  memory_enabled: boolean;
  context_window: number;
  settings: Record<string, unknown>;
  tools_detail?: AgentTool[];
}

export interface AgentCreate {
  name: string;
  description?: string;
  agent_type?: 'conversational' | 'task' | 'research' | 'coding';
  system_prompt?: string;
  model?: string;
  temperature?: number;
  max_tokens?: number;
  tools?: string[];
  skills?: string[];
  memory_enabled?: boolean;
  context_window?: number;
  is_active?: boolean;
}

export interface AgentUpdate extends Partial<AgentCreate> {}

export interface AgentTool {
  id: number;
  name: string;
  tool_type: string;
  config: Record<string, unknown>;
  is_enabled: boolean;
}

export interface AgentChatRequest {
  message: string;
  conversation_id?: number;
}

export interface AgentChatResponse {
  conversation_id: number;
  response: string;
  tool_calls?: unknown[];
}

export interface AgentDebugRequest {
  message: string;
}

export interface AgentDebugResponse {
  response: string;
  tool_calls?: unknown[];
}

export interface AgentToolsResponse {
  available_tools: string[];
  agent_tools: string[];
}

export interface AgentSkillsResponse {
  skills: string[];
}

export interface AgentConversationsResponse {
  available_tools: string[];
  agent_tools: string[];
  skills: string[];
}

export interface AgentConversation {
  id: number;
  agent: number;
  messages: ChatMessage[];
  summary?: string;
  message_count: number;
  token_count: number;
  created_at: string;
  updated_at: string;
}

export interface ChatMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
}

export interface AgentExecution {
  id: number;
  agent: number;
  agent_name?: string;
  conversation: number | null;
  status: 'pending' | 'running' | 'completed' | 'failed';
  input_data?: Record<string, unknown>;
  output_data?: Record<string, unknown>;
  error_message?: string;
  started_at: string;
  completed_at: string | null;
}

export interface DebugSessionDetail {
  id: number;
  conversation_id: number | null;
  messages: ChatMessage[];
  status: string;
  started_at: string;
}

// =============================================================================
// Conversations
// =============================================================================

export interface ConversationMessagesResponse {
  messages: ChatMessage[];
  message_count: number;
  token_count: number;
}

export interface AddMessageRequest {
  role: 'user' | 'assistant' | 'system';
  content: string;
}

// =============================================================================
// Prompts
// =============================================================================

export interface PromptCategory {
  id: number;
  name: string;
  slug: string;
  description?: string;
  icon?: string;
  color?: string;
  prompt_count?: number;
}

export interface PromptVariable {
  name: string;
  description?: string;
  required?: boolean;
}

export interface PromptDetail {
  id: number;
  name: string;
  description: string;
  prompt_type: 'system' | 'user' | 'assistant' | 'task';
  template: string;
  variables: PromptVariable[];
  category?: PromptCategory;
  tags: string[];
  use_count: number;
  avg_rating: number;
  rating_count: number;
  is_featured: boolean;
  creator_name?: string;
  created_at: string;
}

export interface PromptCreate {
  name: string;
  description?: string;
  prompt_type?: 'system' | 'user' | 'assistant' | 'task';
  template: string;
  variables?: PromptVariable[];
  category_id?: number;
  tags?: string[];
  temperature?: number;
  max_tokens?: number;
}

export interface PromptRatingRequest {
  rating: number;
  comment?: string;
}

// =============================================================================
// NL to Workflow
// =============================================================================

export interface NLSession {
  id: number;
  name: string;
  description: string;
  workflow_id: number | null;
  status: 'active' | 'completed' | 'failed';
  generated_workflow?: WorkflowDetail;
  error_message?: string;
  created_at: string;
  updated_at: string;
}

export interface NLSessionCreate {
  name?: string;
  description: string;
}

export interface NLSessionMessage {
  message: string;
}

export interface NLSessionResponse {
  session: NLSession;
  message: string;
  suggestions?: string[];
}

// =============================================================================
// Gateway - AI Model Gateway
// =============================================================================

export interface ModelProvider {
  id: number;
  name: string;
  provider_type: string;
  is_active: boolean;
  is_default: boolean;
  config: Record<string, unknown>;
  models_count?: number;
  created_at: string;
}

export interface AIModel {
  id: number;
  provider: number;
  provider_name?: string;
  name: string;
  model_id: string;
  display_name?: string;
  description?: string;
  is_active: boolean;
  is_default: boolean;
  config: Record<string, unknown>;
  max_tokens?: number;
  supports_streaming?: boolean;
  total_calls?: number;
  total_tokens?: number;
  created_at: string;
}

export interface AIModelCreate {
  provider: number;
  name: string;
  model_id: string;
  display_name?: string;
  description?: string;
  is_active?: boolean;
  is_default?: boolean;
  config?: Record<string, unknown>;
}

export interface UserAPIKey {
  id: number;
  name: string;
  provider: string;
  endpoint?: string;
  is_verified: boolean;
  last_used_at?: string;
  created_at: string;
}

export interface UserAPIKeyCreate {
  name: string;
  provider: string;
  endpoint?: string;
  api_key: string;
}

export interface APICallLog {
  id: number;
  endpoint: string;
  method: string;
  provider: string;
  model: string;
  tokens_used: number;
  cost: number;
  latency_ms: number;
  status_code: number;
  created_at: string;
}

export interface GatewayChatRequest {
  model: string;
  messages: ChatMessage[];
  temperature?: number;
  max_tokens?: number;
  stream?: boolean;
}

export interface GatewayEmbeddingsRequest {
  model?: string;
  input: string | string[];
}

export interface NLSessionCreateRequest {
  description: string;
  name?: string;
}

export interface NLSessionCreateResponse {
  session_id: number;
  workflow?: WorkflowDetail;
  message: string;
}

export interface NLSessionMessageRequest {
  message: string;
}

export interface NLSessionMessageResponse {
  message: string;
  suggestions?: string[];
}

export interface NLPreviewRequest {
  description: string;
}

export interface NLPreviewResponse {
  preview: {
    name: string;
    description: string;
    nodes: Node[];
    edges: Edge[];
    node_count: number;
    edge_count: number;
  };
  message: string;
}

// =============================================================================
// Monitoring
// =============================================================================

export interface Alert {
  id: number;
  rule: number;
  severity: 'low' | 'medium' | 'high' | 'critical';
  severity_display?: string;
  title: string;
  message: string;
  status: 'active' | 'acknowledged' | 'resolved' | 'muted';
  status_display?: string;
  created_at: string;
}

export interface AlertRule {
  id: number;
  name: string;
  description?: string;
  condition: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  threshold: number;
  time_window_minutes: number;
  notify_email: boolean;
  notify_webhook: boolean;
  webhook_url?: string;
  is_active: boolean;
  created_at: string;
}

export interface AlertRuleCreate {
  name: string;
  description?: string;
  condition: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  threshold: number;
  time_window_minutes?: number;
  notify_email?: boolean;
  notify_webhook?: boolean;
  webhook_url?: string;
  is_active?: boolean;
}

export interface AlertAcknowledgeRequest {
  note?: string;
}

export interface DashboardMetrics {
  total_executions: number;
  executions_this_month: number;
  successful_executions: number;
  success_rate: number;
  active_alerts: number;
  workflow_count: number;
}

export interface Metric {
  id: number;
  metric_type: string;
  value: number;
  unit: string;
  tags?: Record<string, string>;
  timestamp: string;
}

export interface NotificationChannel {
  id: number;
  name: string;
  channel_type: 'email' | 'webhook' | 'slack';
  channel_type_display?: string;
  config: Record<string, unknown>;
  is_active: boolean;
  created_at: string;
}

export interface NotificationChannelCreate {
  name: string;
  channel_type: 'email' | 'webhook' | 'slack';
  config: Record<string, unknown>;
  is_active?: boolean;
}

// =============================================================================
// RAG
// =============================================================================

export interface DocumentCollection {
  id: number;
  name: string;
  description?: string;
  vector_store: number;
  vector_store_name?: string;
  embedding_model: string;
  chunk_size: number;
  chunk_overlap: number;
  document_count?: number;
  chunk_count?: number;
  created_at: string;
}

export interface DocumentCollectionCreate {
  name: string;
  description?: string;
  vector_store?: number;
  embedding_model?: string;
  chunk_size?: number;
  chunk_overlap?: number;
}

export interface Document {
  id: number;
  title: string;
  status: string;
  status_display?: string;
  chunk_count: number;
  token_count: number;
  created_at: string;
  processed_at?: string;
}

export interface DocumentUpload {
  collection_id: number;
  title: string;
  content: string;
  metadata?: Record<string, unknown>;
}

export interface RAGQueryRequest {
  query: string;
  top_k?: number;
  min_similarity?: number;
}

export interface RAGQueryResponse {
  response: string;
  sources: unknown[];
}

// =============================================================================
// RAG - Vector Stores
// =============================================================================

export interface VectorStore {
  id: number;
  name: string;
  store_type: 'qdrant' | 'milvus' | 'chroma' | 'pinecone' | 'weaviate';
  store_type_display?: string;
  host: string;
  port?: number;
  collection_name?: string;
  api_key?: string;
  is_connected: boolean;
  collection_count?: number;
  total_vectors?: number;
  created_at: string;
  updated_at: string;
}

export interface VectorStoreCreate {
  name: string;
  store_type: 'qdrant' | 'milvus' | 'chroma' | 'pinecone' | 'weaviate';
  host: string;
  port?: number;
  collection_name?: string;
  api_key?: string;
}

export interface VectorStoreTest {
  success: boolean;
  message: string;
  collection_count?: number;
}

// =============================================================================
// RAG - Pipelines
// =============================================================================

export interface RAGPipeline {
  id: number;
  name: string;
  description?: string;
  collection?: number;
  collection_name?: string;
  retriever_config: Record<string, unknown>;
  generator_config?: Record<string, unknown>;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface RAGPipelineCreate {
  name: string;
  description?: string;
  collection: number;
  retriever_config?: Record<string, unknown>;
  generator_config?: Record<string, unknown>;
}

export interface RAGRetrieveRequest {
  query: string;
  top_k?: number;
  min_similarity?: number;
}

export interface RAGRetrieveResponse {
  chunks: RAGChunk[];
  total: number;
}

export interface RAGChunk {
  id: number;
  content: string;
  metadata: Record<string, unknown>;
  score?: number;
}

// =============================================================================
// RAG - Documents
// =============================================================================

export interface DocumentCreate {
  collection_id: number;
  title: string;
  content: string;
  metadata?: Record<string, unknown>;
}

export interface DocumentAddUrl {
  url: string;
  title?: string;
  metadata?: Record<string, unknown>;
}

// =============================================================================
// Billing
// =============================================================================

export interface PricePlan {
  id: number;
  plan_type: 'free' | 'starter' | 'professional' | 'enterprise';
  plan_type_display?: string;
  billing_cycle: 'monthly' | 'yearly';
  price: number;
  currency: string;
  max_workflows: number;
  max_executions_per_month: number;
  max_team_members: number;
  max_storage_gb: number;
  max_api_calls_per_month: number;
  enable_advanced_nodes: boolean;
  enable_version_history: boolean;
  enable_custom_domain: boolean;
}

export interface Subscription {
  id: number;
  plan_type: 'free' | 'starter' | 'professional' | 'enterprise';
  plan_type_display?: string;
  billing_cycle: 'monthly' | 'yearly';
  status: string;
  status_display?: string;
  is_trial: boolean;
  trial_ends_at?: string;
  current_period_start: string;
  current_period_end: string;
  cancel_at_period_end: boolean;
}

export interface SubscriptionCreate {
  plan_type: 'free' | 'starter' | 'professional' | 'enterprise';
  billing_cycle: 'monthly' | 'yearly';
}

export interface UsageRecord {
  period_start: string;
  period_end: string;
  workflow_count: number;
  execution_count: number;
  api_call_count: number;
  storage_used_mb: number;
  input_tokens: number;
  output_tokens: number;
  total_cost: number;
}

export interface UsageSummary {
  current_usage: UsageRecord;
  limits: Record<string, number>;
  usage_percentages: Record<string, number>;
  remaining: Record<string, number>;
}

export interface Invoice {
  id: number;
  invoice_number: string;
  status: string;
  status_display?: string;
  subtotal: number;
  tax: number;
  discount: number;
  total: number;
  currency: string;
  period_start: string;
  period_end: string;
  paid_at?: string;
  created_at: string;
}

export interface CouponValidation {
  valid: boolean;
  discount?: {
    type: 'percentage' | 'fixed';
    value: number;
  };
}

// =============================================================================
// Billing - Additional Types
// =============================================================================

export interface Payment {
  id: number;
  amount: number;
  currency: string;
  status: 'pending' | 'completed' | 'failed' | 'refunded';
  payment_method: string;
  payment_provider?: string;
  transaction_id?: string;
  paid_at?: string;
  created_at: string;
}

export interface Coupon {
  id: number;
  code: string;
  discount_type: 'percentage' | 'fixed';
  discount_value: number;
  min_purchase?: number;
  max_uses?: number;
  current_uses: number;
  valid_from: string;
  valid_until: string;
  is_active: boolean;
  created_at: string;
}

export interface UsageHistory {
  period_start: string;
  period_end: string;
  executions: number;
  tokens: number;
  api_calls: number;
  storage_mb: number;
  cost: number;
}

// =============================================================================
// Integrations
// =============================================================================

export interface Webhook {
  id: number;
  name: string;
  url: string;
  events: string[];
  headers?: Record<string, string>;
  is_active: boolean;
  is_verified: boolean;
  retry_count: number;
  timeout_seconds: number;
  total_deliveries: number;
  successful_deliveries: number;
  failed_deliveries: number;
  created_at: string;
}

export interface WebhookCreate {
  name: string;
  url: string;
  events: string[];
  secret?: string;
  headers?: Record<string, string>;
  retry_count?: number;
  timeout_seconds?: number;
}

export interface WebhookTestRequest {
  payload?: Record<string, unknown>;
}

export interface Integration {
  id: number;
  name: string;
  integration_type: string;
  is_active: boolean;
  is_connected: boolean;
  last_sync_at?: string;
}

export interface AvailableIntegration {
  id: number;
  name: string;
  integration_type: string;
  category: string;
  description: string;
  icon: string;
  color: string;
  usage_count: number;
  is_featured: boolean;
}

// =============================================================================
// Integrations - Webhook Deliveries
// =============================================================================

export interface WebhookDelivery {
  id: number;
  webhook: number;
  webhook_name?: string;
  event: string;
  payload: string;
  status: 'pending' | 'success' | 'failed' | 'retrying';
  status_code?: number;
  attempts: number;
  response_body?: string;
  error_message?: string;
  created_at: string;
  completed_at?: string;
}

export interface WebhookStats {
  total_deliveries: number;
  successful_deliveries: number;
  failed_deliveries: number;
  success_rate: number;
  avg_response_time_ms?: number;
  last_delivery_at?: string;
}

// =============================================================================
// Integrations - Templates
// =============================================================================

export interface IntegrationTemplate {
  id: number;
  name: string;
  description?: string;
  integration_type: string;
  category: string;
  config_schema: Record<string, unknown>;
  is_featured: boolean;
  usage_count: number;
  created_at: string;
}

// =============================================================================
// Marketplace
// =============================================================================

export interface TemplateDetail {
  id: number;
  name: string;
  slug: string;
  description: string;
  category: {
    id: number;
    name: string;
    slug: string;
  };
  tags: string[];
  nodes: Node[];
  edges: Edge[];
  install_count: number;
  view_count: number;
  avg_rating: number;
  rating_count: number;
  is_verified: boolean;
  is_featured: boolean;
  author_name: string;
  author_avatar?: string;
  is_installed: boolean;
  created_at: string;
}

// =============================================================================
// Marketplace - Additional Types
// =============================================================================

export interface TemplateCategory {
  id: number;
  name: string;
  slug: string;
  description?: string;
  icon?: string;
  color?: string;
  template_count?: number;
  is_active: boolean;
}

export interface TemplateInstall {
  id: number;
  template: number;
  template_name?: string;
  installed_by: number;
  installed_by_name?: string;
  installed_at: string;
  workflow_id?: number;
}

export interface TemplateRating {
  id: number;
  template: number;
  rating: number;
  title?: string;
  content?: string;
  user: number;
  user_name?: string;
  created_at: string;
}

export interface TemplateReport {
  reason: string;
  details?: string;
}

export interface TemplateInstallRequest {
  name?: string;
}

export interface TemplateRateRequest {
  rating: number;
  title?: string;
  content?: string;
}

// =============================================================================
// Tenants
// =============================================================================

export interface TenantDetail {
  id: number;
  name: string;
  slug: string;
  description?: string;
  status: 'active' | 'suspended' | 'trial' | 'cancelled';
  plan: 'free' | 'starter' | 'professional' | 'enterprise';
  owner: UserSimple;
  settings?: Record<string, unknown>;
  custom_domain?: string;
  max_users: number;
  max_workflows: number;
  max_executions_per_month: number;
  billing_email: string;
  subscription_id?: string;
  subscription_end?: string;
  created_at: string;
  updated_at: string;
}

export interface TenantCreate {
  name: string;
  slug: string;
  description?: string;
  billing_email: string;
}

export interface TenantMembership {
  id: number;
  user: UserSimple;
  role: 'owner' | 'admin' | 'member' | 'viewer';
  permissions: string[];
  is_active: boolean;
  joined_at: string;
}

export interface TenantInvitation {
  id: number;
  tenant: number;
  tenant_name?: string;
  email: string;
  role: 'owner' | 'admin' | 'member' | 'viewer';
  status: 'pending' | 'accepted' | 'expired' | 'declined';
  created_at: string;
  expires_at: string;
}

export interface TenantInviteRequest {
  email: string;
  role: 'admin' | 'member' | 'viewer';
}

export interface TenantUsage {
  current_month_workflows: number;
  current_month_executions: number;
  current_month_users: number;
  total_workflows_created: number;
  total_executions: number;
  total_api_calls: number;
  total_tokens_used: number;
}

// =============================================================================
// API Request/Response Helpers
// =============================================================================

export type PaginationParams = {
  page?: number;
  page_size?: number;
};

export type Ordering = '-created_at' | 'created_at' | '-updated_at' | 'updated_at' | 'name' | '-name';

export interface ListParams extends PaginationParams {
  search?: string;
  ordering?: Ordering;
}

export interface WorkflowListParams extends ListParams {
  status?: 'draft' | 'active' | 'paused' | 'archived';
}

export interface AgentListParams extends ListParams {
  is_active?: boolean;
}
