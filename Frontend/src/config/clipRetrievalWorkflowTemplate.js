/**
 * CLIP retrieval project workflow template (M4).
 */
export const CLIP_RETRIEVAL_WORKFLOW_TEMPLATE = {
  name: 'CLIP 检索项目',
  description: '图文数据集 → CLIP 索引 → 场景分析 → 检索站 → 环境 → QA → 预览 → Agent',
  nodes: [
    {
      id: 'dataset_upload_1',
      type: 'dataset_upload',
      position: { x: 80, y: 200 },
      data: {
        label: '上传图文数据集',
        config: {
          format: 'image_text_pairs',
          sourceType: 'upload',
          source: 'upload',
        },
      },
    },
    {
      id: 'clip_retrieval_1',
      type: 'clip_retrieval',
      position: { x: 280, y: 200 },
      data: {
        label: 'CLIP 检索索引',
        config: {
          indexType: 'flat',
          baseModel: 'simple-bow',
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
          websiteType: 'clip_retrieval',
          useLlmEnrich: false,
        },
      },
    },
    {
      id: 'website_generator_1',
      type: 'website_generator',
      position: { x: 680, y: 200 },
      data: {
        label: '生成检索网站',
        config: {
          websiteType: 'clip_retrieval',
          frontendFramework: 'vue',
          backendFramework: 'flask',
          qaProfile: 'default',
          wizard: {
            siteName: 'CLIP 图文检索',
            usageDescription: '输入文字描述，搜索相似图片',
            primaryColor: '#06b6d4',
            qaProfile: 'default',
            websiteType: 'clip_retrieval',
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
        config: {
          websiteType: 'clip_retrieval',
          qaProfile: 'default',
          skipPlaywright: true,
        },
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
        config: { qaProfile: 'default', autoQaAfterEdit: true },
      },
    },
  ],
  edges: [
    { id: 'e1', source: 'dataset_upload_1', target: 'clip_retrieval_1' },
    { id: 'e2', source: 'clip_retrieval_1', target: 'project_profiler_1' },
    { id: 'e3', source: 'project_profiler_1', target: 'website_generator_1' },
    { id: 'e4', source: 'website_generator_1', target: 'environment_provision_1' },
    { id: 'e5', source: 'environment_provision_1', target: 'site_qa_1' },
    { id: 'e6', source: 'site_qa_1', target: 'site_preview_1' },
    { id: 'e7', source: 'site_preview_1', target: 'project_agent_1' },
  ],
}
