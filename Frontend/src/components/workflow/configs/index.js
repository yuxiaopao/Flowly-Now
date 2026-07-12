// Domain node config form components
// These components provide configuration UIs for different AI/LLM domain nodes

export { default as ImageGenerationConfig } from './ImageGenerationConfig.vue'
export { default as VideoGenerationConfig } from './VideoGenerationConfig.vue'
export { default as AudioGenerationConfig } from './AudioGenerationConfig.vue'
export { default as SubtitleGenerationConfig } from './SubtitleGenerationConfig.vue'
export { default as VideoTranslationConfig } from './VideoTranslationConfig.vue'
export { default as VideoUploadConfig } from './VideoUploadConfig.vue'
export { default as SubtitleTranslateConfig } from './SubtitleTranslateConfig.vue'
export { default as SegmentDubbingConfig } from './SegmentDubbingConfig.vue'
export { default as LipSyncConfig } from './LipSyncConfig.vue'
export { default as SubtitleBurnConfig } from './SubtitleBurnConfig.vue'
export { default as ImageEditingConfig } from './ImageEditingConfig.vue'

export { default as DatasetUploadConfig } from './DatasetUploadConfig.vue'
export { default as DataAnnotationConfig } from './DataAnnotationConfig.vue'
export { default as DataAugmentationConfig } from './DataAugmentationConfig.vue'

export { default as ModelTrainingConfig } from './ModelTrainingConfig.vue'
export { default as ModelEvaluationConfig } from './ModelEvaluationConfig.vue'
export { default as ModelDeploymentConfig } from './ModelDeploymentConfig.vue'

export { default as DocumentLoaderConfig } from './DocumentLoaderConfig.vue'
export { default as EmbeddingConfig } from './EmbeddingConfig.vue'
export { default as VectorStoreConfig } from './VectorStoreConfig.vue'
export { default as RetrieverConfig } from './RetrieverConfig.vue'
export { default as RerankerConfig } from './RerankerConfig.vue'

export { default as AgentConfig } from './AgentConfig.vue'
export { default as PlannerConfig } from './PlannerConfig.vue'
export { default as ExecutorConfig } from './ExecutorConfig.vue'
export { default as MemoryConfig } from './MemoryConfig.vue'

export { default as FileReaderConfig } from './FileReaderConfig.vue'
export { default as FileWriterConfig } from './FileWriterConfig.vue'
export { default as WebScraperConfig } from './WebScraperConfig.vue'

export { default as CsvTransformConfig } from './CsvTransformConfig.vue'
export { default as JsonTransformConfig } from './JsonTransformConfig.vue'

export { default as WebsiteGeneratorConfig } from './WebsiteGeneratorConfig.vue'
export { default as YoloTrainingConfig } from './YoloTrainingConfig.vue'
export { default as ClipClassificationConfig } from './ClipClassificationConfig.vue'
export { default as ClipRetrievalConfig } from './ClipRetrievalConfig.vue'
export { default as ProjectProfilerConfig } from './ProjectProfilerConfig.vue'
export { default as SiteFactoryNodeConfig } from './SiteFactoryNodeConfig.vue'
export { default as TrainingStrategyWizard } from './TrainingStrategyWizard.vue'

// Config component mapping by node type
export const configComponentMap = {
  'image_generation': 'ImageGenerationConfig',
  'video_generation': 'VideoGenerationConfig',
  'audio_generation': 'AudioGenerationConfig',
  'subtitle_generation': 'SubtitleGenerationConfig',
  'video_upload': 'VideoUploadConfig',
  'subtitle_translate': 'SubtitleTranslateConfig',
  'segment_dubbing': 'SegmentDubbingConfig',
  'lip_sync': 'LipSyncConfig',
  'subtitle_burn': 'SubtitleBurnConfig',
  'video_translation': 'VideoTranslationConfig',
  'image_editing': 'ImageEditingConfig',
  
  'dataset_upload': 'DatasetUploadConfig',
  'data_annotation': 'DataAnnotationConfig',
  'data_augmentation': 'DataAugmentationConfig',
  
  'model_training': 'ModelTrainingConfig',
  'model_evaluation': 'ModelEvaluationConfig',
  'model_deployment': 'ModelDeploymentConfig',
  
  'document_loader': 'DocumentLoaderConfig',
  'embedding': 'EmbeddingConfig',
  'vector_store': 'VectorStoreConfig',
  'retriever': 'RetrieverConfig',
  'reranker': 'RerankerConfig',
  
  'agent': 'AgentConfig',
  'planner': 'PlannerConfig',
  'executor': 'ExecutorConfig',
  'memory': 'MemoryConfig',
  
  'file_reader': 'FileReaderConfig',
  'file_writer': 'FileWriterConfig',
  'web_scraper': 'WebScraperConfig',
  
  'csv_transform': 'CsvTransformConfig',
  'json_transform': 'JsonTransformConfig',
  'website_generator': 'WebsiteGeneratorConfig',

  'yolo_training': 'YoloTrainingConfig',
  'clip_classification': 'ClipClassificationConfig',
  'clip_retrieval': 'ClipRetrievalConfig',
  'project_profiler': 'ProjectProfilerConfig',
  'environment_provision': 'SiteFactoryNodeConfig',
  'site_preview': 'SiteFactoryNodeConfig',
  'site_qa': 'SiteFactoryNodeConfig',
  'project_agent': 'SiteFactoryNodeConfig',
  'backend_setup': 'SiteFactoryNodeConfig',
  'frontend_setup': 'SiteFactoryNodeConfig',
  'ui_beautify': 'SiteFactoryNodeConfig',
  'site_code_review': 'SiteFactoryNodeConfig',
}
