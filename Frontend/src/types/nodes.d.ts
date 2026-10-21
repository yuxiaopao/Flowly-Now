/**
 * 扩展节点类型定义
 * 包含工作流中所有可用节点类型的配置接口
 */

// ==================== 节点类型 ====================

export type NodeType = 
  | 'start' 
  | 'end' 
  | 'llm' 
  | 'prompt' 
  | 'condition' 
  | 'tool' 
  | 'input' 
  | 'output' 
  | 'code' 
  | 'loop' 
  | 'variable' 
  | 'http'
  | 'email'
  | 'webhook'
  | 'template'
  | 'rag'
  | 'switch'
  | 'delay'
  | 'transform'
  | 'subworkflow'
  | 'image_generation'
  | 'video_generation'
  | 'audio_generation'
  | 'subtitle_generation'
  | 'video_translation'
  | 'video_upload'
  | 'subtitle_translate'
  | 'segment_dubbing'
  | 'lip_sync'
  | 'subtitle_burn'
  | 'image_editing'
  | 'dataset_upload'
  | 'data_annotation'
  | 'data_augmentation'
  | 'model_training'
  | 'model_evaluation'
  | 'model_deployment'
  | 'website_generator'
  | 'backend_setup'
  | 'frontend_setup'
  | 'ui_beautify'
  | 'site_code_review'
  | 'environment_provision'
  | 'site_qa'
  | 'site_preview'
  | 'project_profiler'
  | 'project_agent'
  | 'yolo_training'
  | 'clip_classification'
  | 'clip_retrieval'
  | 'document_loader'
  | 'embedding'
  | 'vector_store'
  | 'retriever'
  | 'reranker'
  | 'agent'
  | 'planner'
  | 'executor'
  | 'memory'
  | 'file_reader'
  | 'file_writer'
  | 'web_scraper_node'
  | 'csv_transform'
  | 'json_transform'

// ==================== 基础节点配置 ====================

export interface NodePosition {
  x: number
  y: number
}

export interface NodeStyle {
  backgroundColor?: string
  color?: string
  borderColor?: string
  borderRadius?: number
  width?: number
  height?: number
}

export type ErrorHandlingStrategy = 'stop' | 'skip' | 'retry' | 'fallback'

export interface BaseNodeConfig {
  label?: string
  description?: string
  errorHandling?: ErrorHandlingStrategy
  maxRetries?: number
  retryDelay?: number
  fallbackValue?: unknown
}

// ==================== LLM 节点配置 ====================

export interface LLMNodeConfig extends BaseNodeConfig {
  model?: string
  temperature?: number
  maxTokens?: number
  systemPrompt?: string
  userTemplate?: string
  inputVariable?: string
  provider?: 'openai' | 'anthropic' | 'ollama' | 'azure'
  streaming?: boolean
}

// ==================== Prompt 节点配置 ====================

export interface PromptNodeConfig extends BaseNodeConfig {
  template?: string
  variables?: Array<{ name: string; value: string }>
}

// ==================== Condition 条件节点配置 ====================

export interface ConditionBranch {
  id?: string
  type?: string
  field?: string
  operator?: string
  value?: string
  branch?: string
}

export interface ConditionNodeConfig extends BaseNodeConfig {
  conditions?: ConditionBranch[]
  defaultBranch?: string
  logicalOperator?: 'and' | 'or'
}

// ==================== Code 代码节点配置 ====================

export interface CodeNodeConfig extends BaseNodeConfig {
  code?: string
  inputVariable?: string
  language?: 'javascript' | 'python'
  timeout?: number
}

// ==================== HTTP 节点配置 ====================

export interface HTTPNodeConfig extends BaseNodeConfig {
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'
  url?: string
  headers?: Record<string, string>
  body?: string
  bodyType?: 'json' | 'form' | 'raw' | 'none'
  timeout?: number
  followRedirects?: boolean
  sslVerify?: boolean
}

// ==================== Loop 循环节点配置 ====================

export interface LoopNodeConfig extends BaseNodeConfig {
  itemsSource?: 'input' | 'static'
  items?: unknown[]
  maxIterations?: number
  loopVariable?: string
}

// ==================== Tool 工具节点配置 ====================

export interface ToolParameter {
  name: string
  value: string
  type?: 'static' | 'variable' | 'expression'
}

export interface ToolNodeConfig extends BaseNodeConfig {
  tool?: string
  toolName?: string
  parameters?: Record<string, unknown>
  parametersArray?: ToolParameter[]
  credential?: string
}

// ==================== Variable 变量节点配置 ====================

export interface VariableAssignment {
  name: string
  value: string
  source: 'static' | 'input' | 'expression'
}

export interface VariableNodeConfig extends BaseNodeConfig {
  assignments?: VariableAssignment[]
}

// ==================== Input 输入节点配置 ====================

export interface InputNodeConfig extends BaseNodeConfig {
  variableName?: string
  prompt?: string
  required?: boolean
  default?: unknown
  inputType?: 'text' | 'number' | 'boolean' | 'json' | 'file'
}

// ==================== Output 输出节点配置 ====================

export interface OutputNodeConfig extends BaseNodeConfig {
  template?: string
  outputVariable?: string
  format?: 'text' | 'json' | 'markdown' | 'xml'
}

// ==================== RAG 节点配置 ====================

export interface RAGNodeConfig extends BaseNodeConfig {
  collectionName?: string
  query?: string
  topK?: number
  similarityThreshold?: number
  searchType?: 'similarity' | 'mmr'
  rerankEnabled?: boolean
}

// ==================== Switch 分支节点配置 ====================

export interface SwitchBranch {
  id: string
  label: string
  conditionType?: 'expression' | 'comparison'
  expression?: string
  field?: string
  operator?: string
  value?: string
}

export interface SwitchNodeConfig extends BaseNodeConfig {
  expression?: string
  branches?: SwitchBranch[]
  defaultBranch?: string
  logicalOperator?: 'and' | 'or'
}

// ==================== Transform 数据转换节点配置 ====================

export interface TransformMapping {
  source: string
  target: string
}

export type TransformType = 'json_to_object' | 'object_to_json' | 'map' | 'filter' | 'sort' | 'merge' | 'split' | 'extract' | 'custom'

export interface TransformNodeConfig extends BaseNodeConfig {
  transformType?: TransformType
  mappings?: TransformMapping[]
  filterExpression?: string
  sortField?: string
  sortOrder?: 'asc' | 'desc'
  customScript?: string
  sourcePath?: string
  targetPath?: string
}

// ==================== Email 邮件节点配置 ====================

export interface EmailAttachment {
  name: string
  url: string
  type?: string
}

export interface SmtpConfig {
  server?: string
  port?: number
  username?: string
  password?: string
  useTls?: boolean
  useSsl?: boolean
}

export interface EmailNodeConfig extends BaseNodeConfig {
  to?: string
  cc?: string
  bcc?: string
  subject?: string
  body?: string
  fromEmail?: string
  isHtml?: boolean
  attachments?: EmailAttachment[]
  smtpConfig?: SmtpConfig
  templateId?: string
}

// ==================== Delay 延迟节点配置 ====================

export interface DelayNodeConfig extends BaseNodeConfig {
  delayType?: 'fixed' | 'random'
  duration?: number
  minDelay?: number
  maxDelay?: number
  unit?: 'seconds' | 'minutes' | 'hours'
}

// ==================== Webhook 节点配置 ====================

export interface WebhookNodeConfig extends BaseNodeConfig {
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'
  path?: string
  responseTemplate?: string
  responseStatusCode?: number
  headers?: Record<string, string>
  authType?: 'none' | 'bearer' | 'basic' | 'api_key'
  authToken?: string
}

// ==================== Subworkflow 子工作流节点配置 ====================

export interface SubworkflowMapping {
  parentVar: string
  childParam: string
  direction: 'parent_to_child' | 'child_to_parent'
}

export interface SubworkflowNodeConfig extends BaseNodeConfig {
  subworkflowId?: string | number
  subworkflowName?: string
  version?: string | 'latest'
  inputMapping?: SubworkflowMapping[]
  outputMapping?: SubworkflowMapping[]
  executionMode?: 'sync' | 'async'
  timeout?: number
  onError?: 'stop' | 'skip' | 'fallback'
  fallbackValue?: unknown
}

// ==================== Template 模板节点配置 ====================

export interface TemplateNodeConfig extends BaseNodeConfig {
  templateId?: string | number
  templateName?: string
  variables?: Record<string, unknown>
}

// ==================== 多模态生成节点配置 ====================

export interface ImageGenerationConfig extends BaseNodeConfig {
  provider: 'openai' | 'stability' | 'flux' | 'replicate'
  model: string
  prompt: string
  size: '1024x1024' | '512x512' | '1792x1024' | '1024x1792'
  quality: 'standard' | 'hd'
  style?: 'vivid' | 'natural'
  n?: number
}

export interface VideoGenerationConfig extends BaseNodeConfig {
  provider: 'runway' | 'pika' | 'replicate' | 'kling'
  model: string
  prompt: string
  duration?: number
  fps?: number
  resolution?: '720p' | '1080p' | '4k'
  inputImage?: string
}

export interface AudioGenerationConfig extends BaseNodeConfig {
  provider: 'openai' | 'elevenlabs' | 'azure'
  model: string
  text: string
  voice?: string
  speed?: number
  format?: 'mp3' | 'wav' | 'ogg'
}

export interface SubtitleGenerationConfig extends BaseNodeConfig {
  inputType: 'audio' | 'video'
  inputPath: string
  language: string
  format: 'srt' | 'vtt' | 'ass'
}

export interface VideoTranslationConfig extends BaseNodeConfig {
  provider?: 'dashscope'
  video_input?: string
  media_id?: string
  inputMode?: 'upload' | 'url' | 'upstream'
  source_language?: string
  target_languages?: string[]
  voice?: string
  subtitle_format?: 'srt' | 'vtt' | 'both'
  burn_subtitles?: boolean
  lip_sync?: boolean
  face_ref_image_url?: string
  video_extension?: boolean
}

export interface VideoUploadConfig extends BaseNodeConfig {
  inputMode?: 'upload' | 'url'
  video_input?: string
  media_id?: string
  public_url?: string
}

export interface SubtitleTranslateConfig extends BaseNodeConfig {
  source_language?: string
  target_language?: string
  subtitle_format?: 'srt' | 'vtt'
}

export interface SegmentDubbingConfig extends BaseNodeConfig {
  target_language?: string
  voice?: string
  provider?: string
}

export interface LipSyncConfig extends BaseNodeConfig {
  target_language?: string
  video_input?: string
  audio_input?: string
  lip_sync?: boolean
  face_ref_image_url?: string
  video_extension?: boolean
}

export interface SubtitleBurnConfig extends BaseNodeConfig {
  target_language?: string
  video_input?: string
  subtitle_format?: 'srt' | 'vtt'
}

export interface ImageEditingConfig extends BaseNodeConfig {
  provider: 'openai' | 'stability'
  model: string
  image: string
  instruction: string
  mask?: string
}

// ==================== 模型训练节点配置 ====================

export interface DatasetUploadConfig extends BaseNodeConfig {
  source: 'upload' | 'url' | 's3' | 'database'
  path: string
  format: 'image' | 'video' | 'text' | 'csv' | 'custom'
  validationRules?: Record<string, unknown>
}

export interface DataAnnotationConfig extends BaseNodeConfig {
  annotationType: 'classification' | 'detection' | 'segmentation' | 'ner'
  labels: string[]
  modelAssisted: boolean
}

export interface DataAugmentationConfig extends BaseNodeConfig {
  strategy: 'geometric' | 'color' | 'noise' | 'mixup' | 'custom'
  transformations: string[]
  ratio: number
}

export interface ModelTrainingConfig extends BaseNodeConfig {
  framework: 'pytorch' | 'tensorflow' | 'transformers' | 'yolo'
  modelType: string
  datasetId?: string
  hyperparameters: {
    epochs?: number
    batchSize?: number
    learningRate?: number
    optimizer?: string
    [key: string]: unknown
  }
  gpuEnabled: boolean
  checkpointing: boolean
}

export interface ModelEvaluationConfig extends BaseNodeConfig {
  modelPath: string
  testDataset: string
  metrics: string[]
  thresholds?: Record<string, number>
}

export interface ModelDeploymentConfig extends BaseNodeConfig {
  platform: 'sagemaker' | 'lambdagpu' | 'triton' | 'local'
  endpointType: 'realtime' | 'batch' | 'serverless'
  autoscaling: boolean
  minInstances?: number
  maxInstances?: number
}

export interface WebsiteGeneratorConfig extends BaseNodeConfig {
  websiteType?: string
  waitForCompletion?: boolean
  waitTimeoutSeconds?: number
  wizard?: Record<string, unknown>
}

export interface SiteFactoryRoleAgentConfig extends BaseNodeConfig {
  outputDir?: string
  websiteType?: string
  agentMode?: 'auto' | 'rules' | 'llm'
  useLlm?: boolean
  allowCoreEdit?: boolean
  autoQaAfterEdit?: boolean
  maxRounds?: number
  instruction?: string
  generatedSiteId?: string
}

export type BackendSetupConfig = SiteFactoryRoleAgentConfig
export type FrontendSetupConfig = SiteFactoryRoleAgentConfig
export type UiBeautifyConfig = SiteFactoryRoleAgentConfig
export type SiteCodeReviewConfig = SiteFactoryRoleAgentConfig

// ==================== RAG 检索节点配置 ====================

export interface DocumentLoaderConfig extends BaseNodeConfig {
  sourceType: 'file' | 'url' | 's3' | 'notion' | 'confluence' | 'web'
  path: string
  parser: 'pdf' | 'docx' | 'txt' | 'markdown' | 'html'
  chunkSize: number
  chunkOverlap: number
}

export interface EmbeddingConfig extends BaseNodeConfig {
  provider: 'openai' | 'huggingface' | 'cohere' | 'ollama'
  model: string
  batchSize?: number
}

export interface VectorStoreConfig extends BaseNodeConfig {
  provider: 'pinecone' | 'chroma' | 'qdrant' | 'weaviate' | 'milvus'
  indexName: string
  metric: 'cosine' | 'euclidean' | 'dotproduct'
  dimension?: number
}

export interface RetrieverConfig extends BaseNodeConfig {
  query: string
  topK: number
  filter?: Record<string, unknown>
  enableRerank: boolean
}

export interface RerankerConfig extends BaseNodeConfig {
  model: string
  topN: number
}

// ==================== Agent 节点配置 ====================

export interface AgentNodeConfig extends BaseNodeConfig {
  model: string
  tools: string[]
  maxIterations: number
  systemPrompt: string
  memoryEnabled: boolean
}

export interface PlannerConfig extends BaseNodeConfig {
  model: string
  decompositionStrategy: 'sequential' | 'parallel' | 'hierarchical'
  maxSubtasks?: number
}

export interface ExecutorConfig extends BaseNodeConfig {
  toolSelection: 'auto' | 'forced'
  contextWindow?: number
}

export interface MemoryConfig extends BaseNodeConfig {
  memoryType: 'buffer' | 'summary' | 'entity' | 'graph'
  maxItems: number
  ttl?: number
}

// ==================== 数据处理节点配置 ====================

export interface FileReaderConfig extends BaseNodeConfig {
  path: string
  format: 'csv' | 'json' | 'txt' | 'parquet' | 'excel'
  encoding?: string
}

export interface FileWriterConfig extends BaseNodeConfig {
  path: string
  format: 'csv' | 'json' | 'txt' | 'text' | 'docx' | 'md' | 'markdown' | 'parquet' | 'excel'
  overwrite: boolean
}

export interface WebScraperConfig extends BaseNodeConfig {
  url: string
  selectors: { name: string; selector: string }[]
  waitFor?: string
}

export interface CsvTransformConfig extends BaseNodeConfig {
  operation: 'filter' | 'aggregate' | 'join' | 'pivot' | 'melt'
  params: Record<string, unknown>
}

export interface JsonTransformConfig extends BaseNodeConfig {
  operation: 'map' | 'filter' | 'reduce' | 'flatten' | 'merge'
  schema: Record<string, unknown>
}

// ==================== 合并所有节点配置类型 ====================

export type NodeConfig = 
  | BaseNodeConfig
  | LLMNodeConfig
  | PromptNodeConfig
  | ConditionNodeConfig
  | CodeNodeConfig
  | HTTPNodeConfig
  | LoopNodeConfig
  | ToolNodeConfig
  | VariableNodeConfig
  | InputNodeConfig
  | OutputNodeConfig
  | RAGNodeConfig
  | SwitchNodeConfig
  | TransformNodeConfig
  | EmailNodeConfig
  | DelayNodeConfig
  | WebhookNodeConfig
  | SubworkflowNodeConfig
  | TemplateNodeConfig
  | ImageGenerationConfig
  | VideoGenerationConfig
  | AudioGenerationConfig
  | SubtitleGenerationConfig
  | VideoTranslationConfig
  | VideoUploadConfig
  | SubtitleTranslateConfig
  | SegmentDubbingConfig
  | LipSyncConfig
  | SubtitleBurnConfig
  | ImageEditingConfig
  | DatasetUploadConfig
  | DataAnnotationConfig
  | DataAugmentationConfig
  | ModelTrainingConfig
  | ModelEvaluationConfig
  | ModelDeploymentConfig
  | WebsiteGeneratorConfig
  | BackendSetupConfig
  | FrontendSetupConfig
  | UiBeautifyConfig
  | SiteCodeReviewConfig
  | DocumentLoaderConfig
  | EmbeddingConfig
  | VectorStoreConfig
  | RetrieverConfig
  | RerankerConfig
  | AgentNodeConfig
  | PlannerConfig
  | ExecutorConfig
  | MemoryConfig
  | FileReaderConfig
  | FileWriterConfig
  | WebScraperConfig
  | CsvTransformConfig
  | JsonTransformConfig

// ==================== 节点元数据 ====================

export interface NodeTypeMetadata {
  value: NodeType
  label: string
  icon?: string
  category?: string
  description?: string
  defaultConfig?: NodeConfig
  inputs?: string[]
  outputs?: string[]
}
