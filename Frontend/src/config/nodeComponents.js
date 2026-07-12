/**
 * Vue Flow 节点组件映射
 */
import { defineComponent, h, markRaw } from 'vue'
import WorkflowNodeHost from '@/components/workflow/WorkflowNodeHost.vue'
import StartNode from '@/components/workflow/nodes/StartNode.vue'
import EndNode from '@/components/workflow/nodes/EndNode.vue'
import LLMNode from '@/components/workflow/nodes/LLMNode.vue'
import PromptNode from '@/components/workflow/nodes/PromptNode.vue'
import ConditionNode from '@/components/workflow/nodes/ConditionNode.vue'
import LoopNode from '@/components/workflow/nodes/LoopNode.vue'
import InputNode from '@/components/workflow/nodes/InputNode.vue'
import OutputNode from '@/components/workflow/nodes/OutputNode.vue'
import CodeNode from '@/components/workflow/nodes/CodeNode.vue'
import VariableNode from '@/components/workflow/nodes/VariableNode.vue'
import ToolNode from '@/components/workflow/nodes/ToolNode.vue'
import HttpNode from '@/components/workflow/nodes/HttpNode.vue'
import SwitchNode from '@/components/workflow/nodes/SwitchNode.vue'
import DelayNode from '@/components/workflow/nodes/DelayNode.vue'
import TransformNode from '@/components/workflow/nodes/TransformNode.vue'
import EmailNode from '@/components/workflow/nodes/EmailNode.vue'
import SubworkflowNode from '@/components/workflow/nodes/SubworkflowNode.vue'
import ManualTriggerNode from '@/components/workflow/nodes/ManualTriggerNode.vue'
import ScheduleTriggerNode from '@/components/workflow/nodes/ScheduleTriggerNode.vue'
import WebhookTriggerNode from '@/components/workflow/nodes/WebhookTriggerNode.vue'
import FormTriggerNode from '@/components/workflow/nodes/FormTriggerNode.vue'
import MergeNode from '@/components/workflow/nodes/MergeNode.vue'
import SplitBatchesNode from '@/components/workflow/nodes/SplitBatchesNode.vue'
import FilterNode from '@/components/workflow/nodes/FilterNode.vue'
import SetNode from '@/components/workflow/nodes/SetNode.vue'
import DateTimeNode from '@/components/workflow/nodes/DateTimeNode.vue'
import IntegrationNode from '@/components/workflow/nodes/IntegrationNode.vue'
import ImageGenerationNode from '@/components/workflow/nodes/ImageGenerationNode.vue'
import VideoGenerationNode from '@/components/workflow/nodes/VideoGenerationNode.vue'
import AudioGenerationNode from '@/components/workflow/nodes/AudioGenerationNode.vue'
import SubtitleGenerationNode from '@/components/workflow/nodes/SubtitleGenerationNode.vue'
import VideoTranslationNode from '@/components/workflow/nodes/VideoTranslationNode.vue'
import VideoUploadNode from '@/components/workflow/nodes/VideoUploadNode.vue'
import SubtitleTranslateNode from '@/components/workflow/nodes/SubtitleTranslateNode.vue'
import SegmentDubbingNode from '@/components/workflow/nodes/SegmentDubbingNode.vue'
import LipSyncNode from '@/components/workflow/nodes/LipSyncNode.vue'
import SubtitleBurnNode from '@/components/workflow/nodes/SubtitleBurnNode.vue'
import ImageEditingNode from '@/components/workflow/nodes/ImageEditingNode.vue'
import DatasetUploadNode from '@/components/workflow/nodes/DatasetUploadNode.vue'
import DataAnnotationNode from '@/components/workflow/nodes/DataAnnotationNode.vue'
import DataAugmentationNode from '@/components/workflow/nodes/DataAugmentationNode.vue'
import ModelTrainingNode from '@/components/workflow/nodes/ModelTrainingNode.vue'
import YoloTrainingNode from '@/components/workflow/nodes/YoloTrainingNode.vue'
import ClipClassificationNode from '@/components/workflow/nodes/ClipClassificationNode.vue'
import ClipRetrievalNode from '@/components/workflow/nodes/ClipRetrievalNode.vue'
import ProjectProfilerNode from '@/components/workflow/nodes/ProjectProfilerNode.vue'
import ModelEvaluationNode from '@/components/workflow/nodes/ModelEvaluationNode.vue'
import ModelDeploymentNode from '@/components/workflow/nodes/ModelDeploymentNode.vue'
import WebsiteGeneratorNode from '@/components/workflow/nodes/WebsiteGeneratorNode.vue'
import EnvironmentProvisionNode from '@/components/workflow/nodes/EnvironmentProvisionNode.vue'
import SiteQaNode from '@/components/workflow/nodes/SiteQaNode.vue'
import SitePreviewNode from '@/components/workflow/nodes/SitePreviewNode.vue'
import ProjectAgentNode from '@/components/workflow/nodes/ProjectAgentNode.vue'
import BackendSetupNode from '@/components/workflow/nodes/BackendSetupNode.vue'
import FrontendSetupNode from '@/components/workflow/nodes/FrontendSetupNode.vue'
import UiBeautifyNode from '@/components/workflow/nodes/UiBeautifyNode.vue'
import SiteCodeReviewNode from '@/components/workflow/nodes/SiteCodeReviewNode.vue'
import DocumentLoaderNode from '@/components/workflow/nodes/DocumentLoaderNode.vue'
import EmbeddingNode from '@/components/workflow/nodes/EmbeddingNode.vue'
import VectorStoreNode from '@/components/workflow/nodes/VectorStoreNode.vue'
import RetrieverNode from '@/components/workflow/nodes/RetrieverNode.vue'
import RerankerNode from '@/components/workflow/nodes/RerankerNode.vue'
import AgentNode from '@/components/workflow/nodes/AgentNode.vue'
import PlannerNode from '@/components/workflow/nodes/PlannerNode.vue'
import ExecutorNode from '@/components/workflow/nodes/ExecutorNode.vue'
import MemoryNode from '@/components/workflow/nodes/MemoryNode.vue'
import FileReaderNode from '@/components/workflow/nodes/FileReaderNode.vue'
import FileWriterNode from '@/components/workflow/nodes/FileWriterNode.vue'
import WebScraperNode from '@/components/workflow/nodes/WebScraperNode.vue'
import CsvTransformNode from '@/components/workflow/nodes/CsvTransformNode.vue'
import JsonTransformNode from '@/components/workflow/nodes/JsonTransformNode.vue'
import JsonParserNode from '@/components/workflow/nodes/JsonParserNode.vue'
import TextTemplateNode from '@/components/workflow/nodes/TextTemplateNode.vue'
import RssFeedNode from '@/components/workflow/nodes/RssFeedNode.vue'
import { INTEGRATION_TYPES } from '@/config/integrations'

const CORE_NODE_COMPONENTS = {
  start: StartNode,
  end: EndNode,
  llm: LLMNode,
  prompt: PromptNode,
  condition: ConditionNode,
  loop: LoopNode,
  input: InputNode,
  output: OutputNode,
  code: CodeNode,
  variable: VariableNode,
  tool: ToolNode,
  http: HttpNode,
  switch: SwitchNode,
  delay: DelayNode,
  transform: TransformNode,
  email: EmailNode,
  subworkflow: SubworkflowNode,
  manual: ManualTriggerNode,
  schedule: ScheduleTriggerNode,
  webhook: WebhookTriggerNode,
  form: FormTriggerNode,
  merge: MergeNode,
  split: SplitBatchesNode,
  filter: FilterNode,
  set: SetNode,
  datetime: DateTimeNode,
  image_generation: ImageGenerationNode,
  video_generation: VideoGenerationNode,
  audio_generation: AudioGenerationNode,
  subtitle_generation: SubtitleGenerationNode,
  video_upload: VideoUploadNode,
  subtitle_translate: SubtitleTranslateNode,
  segment_dubbing: SegmentDubbingNode,
  lip_sync: LipSyncNode,
  subtitle_burn: SubtitleBurnNode,
  video_translation: VideoTranslationNode,
  image_editing: ImageEditingNode,
  dataset_upload: DatasetUploadNode,
  data_annotation: DataAnnotationNode,
  data_augmentation: DataAugmentationNode,
  model_training: ModelTrainingNode,
  yolo_training: YoloTrainingNode,
  clip_classification: ClipClassificationNode,
  clip_retrieval: ClipRetrievalNode,
  project_profiler: ProjectProfilerNode,
  model_evaluation: ModelEvaluationNode,
  model_deployment: ModelDeploymentNode,
  website_generator: WebsiteGeneratorNode,
  backend_setup: BackendSetupNode,
  frontend_setup: FrontendSetupNode,
  ui_beautify: UiBeautifyNode,
  site_code_review: SiteCodeReviewNode,
  environment_provision: EnvironmentProvisionNode,
  site_qa: SiteQaNode,
  site_preview: SitePreviewNode,
  project_agent: ProjectAgentNode,
  document_loader: DocumentLoaderNode,
  embedding: EmbeddingNode,
  vector_store: VectorStoreNode,
  retriever: RetrieverNode,
  reranker: RerankerNode,
  agent: AgentNode,
  planner: PlannerNode,
  executor: ExecutorNode,
  memory: MemoryNode,
  file_reader: FileReaderNode,
  file_writer: FileWriterNode,
  web_scraper: WebScraperNode,
  csv_transform: CsvTransformNode,
  json_transform: JsonTransformNode,
  json_parser: JsonParserNode,
  text_template: TextTemplateNode,
  rss_feed: RssFeedNode,
  openai_api: IntegrationNode,
  huggingface: IntegrationNode,
}

function wrapNodeComponent(Component) {
  const componentName = Component.name || Component.__name || 'WorkflowNode'
  return defineComponent({
    name: `Selectable_${componentName}`,
    inheritAttrs: false,
    props: {
      id: { type: String, required: true },
      data: { type: Object, default: () => ({}) },
      selected: { type: Boolean, default: false },
    },
    setup(props, { attrs }) {
      return () =>
        h(WorkflowNodeHost, {
          nodeComponent: Component,
          id: props.id,
          data: props.data,
          selected: props.selected,
          extraProps: attrs,
        })
    },
  })
}

/** 构建 Vue Flow nodeTypes 对象（经 WorkflowNodeHost 转发 select，修复 ISSUE-003） */
export function buildNodeTypesMap() {
  const map = {}
  for (const [type, Component] of Object.entries(CORE_NODE_COMPONENTS)) {
    map[type] = markRaw(wrapNodeComponent(Component))
  }
  INTEGRATION_TYPES.forEach((type) => {
    if (!map[type]) {
      map[type] = markRaw(wrapNodeComponent(IntegrationNode))
    }
  })
  return markRaw(map)
}

export function getNodeComponent(type) {
  return CORE_NODE_COMPONENTS[type] || IntegrationNode
}
