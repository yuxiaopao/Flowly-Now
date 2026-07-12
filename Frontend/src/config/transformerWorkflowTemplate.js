/**
 * Transformer fine-tuning project workflow template.
 */
export const TRANSFORMER_WORKFLOW_TEMPLATE = {
  name: 'Transformer 微调项目',
  description: '数据集 → Transformer 微调 → 场景分析 → 分类站 → 环境 → QA → 预览 → Agent',
  nodes: [
    {
      id: 'dataset_upload_1',
      type: 'dataset_upload',
      position: { x: 80, y: 200 },
      data: {
        label: '上传数据集',
        config: {
          format: 'image_folder',
          sourceType: 'upload',
        },
      },
    },
    {
      id: 'model_training_1',
      type: 'model_training',
      position: { x: 280, y: 200 },
      data: {
        label: 'Transformer 微调',
        config: {
          framework: 'transformers',
          modelType: 'classification',
          trainingKind: 'transformer',
          baseWeightUri: 'bert-base-uncased',
          epochs: 10,
          batchSize: 8,
          learningRate: 0.00005,
          dataSourceType: 'upstream',
        },
      },
    },
    {
      id: 'project_profiler_1',
      type: 'project_profiler',
      position: { x: 480, y: 200 },
      data: {
        label: '场景分析',
        config: {
          websiteType: 'classification',
          useLlmEnrich: true,
        },
      },
    },
    {
      id: 'website_generator_1',
      type: 'website_generator',
      position: { x: 680, y: 200 },
      data: {
        label: '生成分类网站',
        config: {
          websiteType: 'classification',
          projectType: 'classification',
          framework: 'transformers',
          frontendFramework: 'vue',
          backendFramework: 'flask',
          qaProfile: 'default',
          wizard: {
            siteName: 'Transformer 分类系统',
            usageDescription: '上传样本，查看分类结果与置信度',
            primaryColor: '#06b6d4',
            qaProfile: 'default',
            websiteType: 'classification',
            wizardCompleted: true,
          },
        },
      },
    },
    {
      id: 'environment_provision_1',
      type: 'environment_provision',
      position: { x: 880, y: 200 },
      data: {
        label: '环境配置',
        config: { runtimeMode: 'desktop' },
      },
    },
    {
      id: 'site_qa_1',
      type: 'site_qa',
      position: { x: 1080, y: 200 },
      data: {
        label: '站点自查',
        config: { websiteType: 'classification', qaProfile: 'default' },
      },
    },
    {
      id: 'site_preview_1',
      type: 'site_preview',
      position: { x: 1280, y: 200 },
      data: {
        label: '站点预览',
        config: { qaProfile: 'default' },
      },
    },
    {
      id: 'project_agent_1',
      type: 'project_agent',
      position: { x: 1480, y: 200 },
      data: {
        label: '项目 Agent',
        config: { autoQaAfterEdit: true, qaProfile: 'default', agentMode: 'auto' },
      },
    },
  ],
  edges: [
    { id: 'e1', source: 'dataset_upload_1', target: 'model_training_1' },
    { id: 'e2', source: 'model_training_1', target: 'project_profiler_1' },
    { id: 'e3', source: 'project_profiler_1', target: 'website_generator_1' },
    { id: 'e4', source: 'website_generator_1', target: 'environment_provision_1' },
    { id: 'e5', source: 'environment_provision_1', target: 'site_qa_1' },
    { id: 'e6', source: 'site_qa_1', target: 'site_preview_1' },
    { id: 'e7', source: 'site_preview_1', target: 'project_agent_1' },
  ],
}
