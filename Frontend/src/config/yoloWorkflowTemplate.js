/**
 * Standard YOLO detection project workflow template.
 * Used when creating from /training redirect or marketplace seed.
 */
export const YOLO_WORKFLOW_TEMPLATE = {
  name: 'YOLO 识别项目',
  description: '数据集 → YOLO 训练 → 场景分析 → 建站向导 → 环境 → QA → 预览 → Agent',
  nodes: [
    {
      id: 'dataset_upload_1',
      type: 'dataset_upload',
      position: { x: 80, y: 200 },
      data: {
        label: '上传标注数据集',
        config: {
          format: 'yolo',
          sourceType: 'upload'
        }
      }
    },
    {
      id: 'yolo_training_1',
      type: 'yolo_training',
      position: { x: 280, y: 200 },
      data: {
        label: 'YOLO 训练',
        config: {
          trainingMode: 'local',
          yoloVersion: 'v8',
          modelVariant: 'n',
          epochs: 50,
          batchSize: 16,
          imageSize: 640,
          dataSourceType: 'upstream'
        }
      }
    },
    {
      id: 'project_profiler_1',
      type: 'project_profiler',
      position: { x: 480, y: 200 },
      data: {
        label: '场景分析',
        config: {
          websiteType: 'detection',
          useLlmEnrich: false
        }
      }
    },
    {
      id: 'website_generator_1',
      type: 'website_generator',
      position: { x: 680, y: 200 },
      data: {
        label: '生成识别网站',
        config: {
          websiteType: 'detection',
          projectType: 'detection',
          framework: 'ultralytics',
          frontendFramework: 'vue',
          backendFramework: 'flask',
          qaProfile: 'default',
          wizard: {
            siteName: 'YOLO 识别系统',
            usageDescription: '上传现场图片，查看目标检测框与置信度',
            primaryColor: '#f59e0b',
            qaProfile: 'default',
            websiteType: 'detection',
            wizardCompleted: true
          }
        }
      }
    },
    {
      id: 'environment_provision_1',
      type: 'environment_provision',
      position: { x: 880, y: 200 },
      data: {
        label: '环境配置',
        config: { runtimeMode: 'desktop' }
      }
    },
    {
      id: 'site_qa_1',
      type: 'site_qa',
      position: { x: 1080, y: 200 },
      data: {
        label: '站点自查',
        config: {
          websiteType: 'detection',
          qaProfile: 'default',
          skipPlaywright: false
        }
      }
    },
    {
      id: 'site_preview_1',
      type: 'site_preview',
      position: { x: 1280, y: 200 },
      data: {
        label: '站点预览',
        config: { qaProfile: 'default' }
      }
    },
    {
      id: 'project_agent_1',
      type: 'project_agent',
      position: { x: 1480, y: 200 },
      data: {
        label: '项目 Agent',
        config: {
          qaProfile: 'default',
          autoQaAfterEdit: true,
          message: ''
        }
      }
    }
  ],
  edges: [
    { id: 'e1', source: 'dataset_upload_1', target: 'yolo_training_1' },
    { id: 'e2', source: 'yolo_training_1', target: 'project_profiler_1' },
    { id: 'e3', source: 'project_profiler_1', target: 'website_generator_1' },
    { id: 'e4', source: 'website_generator_1', target: 'environment_provision_1' },
    { id: 'e5', source: 'environment_provision_1', target: 'site_qa_1' },
    { id: 'e6', source: 'site_qa_1', target: 'site_preview_1' },
    { id: 'e7', source: 'site_preview_1', target: 'project_agent_1' }
  ]
}
