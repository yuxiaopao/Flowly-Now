/**
 * Standard YOLO detection project workflow template (Site Factory v2).
 * Full AI role-agent chain: train → profile → generate → backend/frontend/UI → env → QA(autofix) → review → preview → agent
 */
export const YOLO_WORKFLOW_TEMPLATE = {
  name: 'YOLO 识别项目',
  description:
    '数据集 → YOLO 训练 → 场景分析 → 建站(Flask+Vue+MySQL) → 后端/前端/UI 分工 → 环境授权 → QA自修 → 预览 → 项目 Agent',
  nodes: [
    {
      id: 'dataset_upload_1',
      type: 'dataset_upload',
      position: { x: 40, y: 220 },
      data: {
        label: '上传标注数据集',
        config: {
          format: 'yolo',
          sourceType: 'upload',
        },
      },
    },
    {
      id: 'yolo_training_1',
      type: 'yolo_training',
      position: { x: 240, y: 220 },
      data: {
        label: 'YOLO 训练',
        config: {
          trainingMode: 'local',
          yoloVersion: 'v8',
          modelVariant: 'n',
          epochs: 50,
          batchSize: 16,
          imageSize: 640,
          dataSourceType: 'upstream',
        },
      },
    },
    {
      id: 'project_profiler_1',
      type: 'project_profiler',
      position: { x: 440, y: 220 },
      data: {
        label: '场景分析',
        config: {
          websiteType: 'detection',
          useLlmEnrich: true,
        },
      },
    },
    {
      id: 'website_generator_1',
      type: 'website_generator',
      position: { x: 640, y: 220 },
      data: {
        label: '生成识别网站',
        config: {
          websiteType: 'detection',
          projectType: 'detection',
          framework: 'ultralytics',
          frontendFramework: 'vue',
          backendFramework: 'flask',
          dbEngine: 'mysql',
          qaProfile: 'default',
          wizard: {
            siteName: 'YOLO 识别系统',
            usageDescription: '上传现场图片，查看目标检测框与置信度',
            primaryColor: '#f59e0b',
            qaProfile: 'default',
            websiteType: 'detection',
            wizardCompleted: true,
          },
          environmentConfig: {
            dbEngine: 'mysql',
          },
        },
      },
    },
    {
      id: 'backend_setup_1',
      type: 'backend_setup',
      position: { x: 840, y: 120 },
      data: {
        label: '后端搭建',
        config: {
          agentMode: 'auto',
          allowCoreEdit: true,
          autoQaAfterEdit: false,
        },
      },
    },
    {
      id: 'frontend_setup_1',
      type: 'frontend_setup',
      position: { x: 1040, y: 120 },
      data: {
        label: '前端搭建',
        config: {
          agentMode: 'auto',
          autoQaAfterEdit: false,
        },
      },
    },
    {
      id: 'ui_beautify_1',
      type: 'ui_beautify',
      position: { x: 1240, y: 120 },
      data: {
        label: 'UI 美化',
        config: {
          agentMode: 'auto',
          autoQaAfterEdit: false,
        },
      },
    },
    {
      id: 'environment_provision_1',
      type: 'environment_provision',
      position: { x: 1040, y: 320 },
      data: {
        label: '环境配置',
        config: {
          runtimeMode: 'desktop',
          dbEngine: 'mysql',
          requirePathGrant: true,
          customPaths: [],
        },
      },
    },
    {
      id: 'site_qa_1',
      type: 'site_qa',
      position: { x: 1240, y: 320 },
      data: {
        label: '站点自查',
        config: {
          websiteType: 'detection',
          qaProfile: 'default',
          skipPlaywright: false,
          autoFix: true,
          maxFixRounds: 2,
        },
      },
    },
    {
      id: 'site_code_review_1',
      type: 'site_code_review',
      position: { x: 1440, y: 220 },
      data: {
        label: '代码复查',
        config: {
          agentMode: 'auto',
          maxRounds: 2,
          autoQaAfterEdit: true,
        },
      },
    },
    {
      id: 'site_preview_1',
      type: 'site_preview',
      position: { x: 1640, y: 220 },
      data: {
        label: '站点预览',
        config: { qaProfile: 'default' },
      },
    },
    {
      id: 'project_agent_1',
      type: 'project_agent',
      position: { x: 1840, y: 220 },
      data: {
        label: '项目 Agent',
        config: {
          qaProfile: 'default',
          autoQaAfterEdit: true,
          syncSystemAgent: true,
          agentMemoryEnabled: true,
          message: '',
        },
      },
    },
  ],
  edges: [
    { id: 'e1', source: 'dataset_upload_1', target: 'yolo_training_1' },
    { id: 'e2', source: 'yolo_training_1', target: 'project_profiler_1' },
    { id: 'e3', source: 'project_profiler_1', target: 'website_generator_1' },
    { id: 'e4', source: 'website_generator_1', target: 'backend_setup_1' },
    { id: 'e5', source: 'backend_setup_1', target: 'frontend_setup_1' },
    { id: 'e6', source: 'frontend_setup_1', target: 'ui_beautify_1' },
    { id: 'e7', source: 'ui_beautify_1', target: 'environment_provision_1' },
    { id: 'e8', source: 'environment_provision_1', target: 'site_qa_1' },
    { id: 'e9', source: 'site_qa_1', target: 'site_code_review_1' },
    { id: 'e10', source: 'site_code_review_1', target: 'site_preview_1' },
    { id: 'e11', source: 'site_preview_1', target: 'project_agent_1' },
  ],
}
