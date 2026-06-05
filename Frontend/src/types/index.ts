/**
 * 类型定义统一入口
 * 从这里导入所有类型，避免重复定义
 *
 * 使用方式：
 *   import type { Workflow, WorkflowNode, ExecutionStatus } from '@/types'
 *
 * 注意：
 *   - ToolParameter 同时存在于 agent.d.ts 和 nodes.d.ts，优先使用 agent.d.ts 版本
 *   - ExecutionStatus/NodeExecutionStatus 等同时存在于 workflow.ts 和 execution.d.ts，
 *     统一从 execution.d.ts 导出
 */

// API 层类型
export type { TokenStats } from './request'
export type { ListResponse, PaginationParams, SortParams } from './api'
export * from './gateway'
export * from './billing'
export * from './rag'

// Agent、Trigger、Variable、Workflow
export * from './agent'
export * from './trigger'
export * from './variable'
export * from './workflow'

// Re-export execution types (prefer execution.d.ts over workflow.ts duplicates)
export type {
  ExecutionStatus,
  NodeExecutionStatus,
  ExecutionEventType,
  ExecutionEvent,
  StreamEvent,
  NodeEvent,
  NodeStatusSummary,
  ExecutionLogEntry,
  WorkflowExecution,
  ExecutionRequest,
  ExecutionResponse,
  DiffStatus,
  DiffNodeChange,
  DiffEdgeChange,
  DiffSummary,
  DiffResult,
  ExecutionStatistics,
  ExecutionResult,
  APIExecutionLog,
} from './execution'

// Re-export node configuration types
export type {
  NodeType,
  NodePosition,
  NodeStyle,
  ErrorHandlingStrategy,
  BaseNodeConfig,
  LLMNodeConfig,
  PromptNodeConfig,
  ConditionBranch,
  ConditionNodeConfig,
  CodeNodeConfig,
  HTTPNodeConfig,
  LoopNodeConfig,
  ToolNodeConfig,
  VariableAssignment,
  VariableNodeConfig,
  InputNodeConfig,
  OutputNodeConfig,
  RAGNodeConfig,
  SwitchBranch,
  SwitchNodeConfig,
  TransformMapping,
  TransformType,
  TransformNodeConfig,
  EmailAttachment,
  SmtpConfig,
  EmailNodeConfig,
  DelayNodeConfig,
  WebhookNodeConfig,
  SubworkflowMapping,
  SubworkflowNodeConfig,
  TemplateNodeConfig,
  ImageGenerationConfig,
  VideoGenerationConfig,
  AudioGenerationConfig,
  SubtitleGenerationConfig,
  ImageEditingConfig,
  DatasetUploadConfig,
  DataAnnotationConfig,
  DataAugmentationConfig,
  ModelTrainingConfig,
  ModelEvaluationConfig,
  ModelDeploymentConfig,
  DocumentLoaderConfig,
  EmbeddingConfig,
  VectorStoreConfig,
  RetrieverConfig,
  RerankerConfig,
  AgentNodeConfig,
  PlannerConfig,
  ExecutorConfig,
  MemoryConfig,
  FileReaderConfig,
  FileWriterConfig,
  WebScraperConfig,
  CsvTransformConfig,
  JsonTransformConfig,
  NodeConfig,
  NodeTypeMetadata,
} from './nodes'
