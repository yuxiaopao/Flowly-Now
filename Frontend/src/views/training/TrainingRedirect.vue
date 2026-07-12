<template>
  <div class="training-redirect">
    <PageHeader
      compact
      title="训练已迁移至工作流"
      subtitle="选择 YOLO / CLIP / Transformer 策略，一键创建完整 MLOps 项目工作流"
    />

    <el-card class="wizard-card">
      <template #header>
        <span>训练策略向导</span>
      </template>
      <TrainingStrategyWizard @finished="onStrategyFinished" />
    </el-card>

    <el-card class="redirect-card">
      <p>快速模板：</p>
      <div class="actions">
        <el-button type="primary" @click="createYoloWorkflow">
          YOLO 识别项目
        </el-button>
        <el-button type="primary" plain @click="createClipRetrievalWorkflow">
          CLIP 检索项目
        </el-button>
        <el-button type="primary" plain @click="createTransformerWorkflow">
          Transformer 微调项目
        </el-button>
        <el-button @click="router.push('/workflows')">
          查看我的工作流
        </el-button>
        <el-button @click="router.push('/datasets')">
          管理数据集
        </el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
import PageHeader from '@/components/layout/PageHeader.vue'
import TrainingStrategyWizard from '@/components/workflow/configs/TrainingStrategyWizard.vue'
import { YOLO_WORKFLOW_TEMPLATE } from '@/config/yoloWorkflowTemplate'
import { CLIP_RETRIEVAL_WORKFLOW_TEMPLATE } from '@/config/clipRetrievalWorkflowTemplate'
import { TRANSFORMER_WORKFLOW_TEMPLATE } from '@/config/transformerWorkflowTemplate'

const router = useRouter()

function applyTrainingConfig(template, config) {
  const cloned = JSON.parse(JSON.stringify(template))
  const nodeId = {
    yolo_training: 'yolo_training_1',
    clip_retrieval: 'clip_retrieval_1',
    clip_classification: 'clip_classification_1',
    model_training: 'model_training_1',
  }[config.targetNodeType]

  const node = cloned.nodes.find((n) => n.id === nodeId)
  if (!node) return cloned

  const cfg = node.data.config || {}
  if (config.targetNodeType === 'yolo_training') {
    Object.assign(cfg, {
      yoloVersion: config.yoloVersion,
      modelVariant: config.modelVariant,
      baseWeightUri: config.baseWeightUri,
      epochs: config.epochs,
      batchSize: config.batchSize,
      imageSize: config.imageSize,
      datasetYamlPath: config.datasetYamlPath,
      classNames: config.classNames,
      outputDir: config.outputDir,
    })
  } else if (config.targetNodeType === 'clip_retrieval') {
    Object.assign(cfg, {
      baseModel: config.baseModel,
      indexMode: config.indexMode,
      outputDir: config.outputDir,
    })
  } else if (config.targetNodeType === 'clip_classification') {
    Object.assign(cfg, {
      baseModel: config.baseModel,
      outputDir: config.outputDir,
    })
  } else {
    Object.assign(cfg, {
      framework: config.framework,
      modelType: config.modelType,
      trainingKind: 'transformer',
      baseWeightUri: config.baseWeightUri,
      epochs: config.epochs,
      learningRate: config.learningRate,
      outputDir: config.outputDir,
    })
  }
  node.data.config = cfg
  return cloned
}

function pickTemplate(config) {
  if (config.targetNodeType === 'clip_retrieval') return CLIP_RETRIEVAL_WORKFLOW_TEMPLATE
  if (config.targetNodeType === 'model_training') return TRANSFORMER_WORKFLOW_TEMPLATE
  if (config.targetNodeType === 'clip_classification') {
    const t = JSON.parse(JSON.stringify(YOLO_WORKFLOW_TEMPLATE))
    t.name = 'CLIP 分类项目'
    t.nodes = t.nodes.map((n) => {
      if (n.type === 'yolo_training') {
        return {
          id: 'clip_classification_1',
          type: 'clip_classification',
          position: n.position,
          data: { label: 'CLIP 分类', config: { baseModel: 'ViT-B-32/openai' } },
        }
      }
      return n
    })
    t.edges = t.edges.map((e) => ({
      ...e,
      source: e.source === 'yolo_training_1' ? 'clip_classification_1' : e.source,
      target: e.target === 'yolo_training_1' ? 'clip_classification_1' : e.target,
    }))
    return t
  }
  return YOLO_WORKFLOW_TEMPLATE
}

async function onStrategyFinished(config) {
  const base = pickTemplate(config)
  const template = applyTrainingConfig(base, config)
  const query = {
    yolo_training: 'yolo-detection',
    clip_retrieval: 'clip-retrieval',
    clip_classification: 'clip-classification',
    model_training: 'transformer-classification',
  }[config.targetNodeType] || 'custom'
  sessionStorage.setItem('flowly_pending_workflow_template', JSON.stringify(template))
  await router.push(`/workflows/new?template=${query}`)
}

async function createYoloWorkflow() {
  sessionStorage.setItem('flowly_pending_workflow_template', JSON.stringify(YOLO_WORKFLOW_TEMPLATE))
  await router.push('/workflows/new?template=yolo-detection')
}

async function createClipRetrievalWorkflow() {
  sessionStorage.setItem('flowly_pending_workflow_template', JSON.stringify(CLIP_RETRIEVAL_WORKFLOW_TEMPLATE))
  await router.push('/workflows/new?template=clip-retrieval')
}

async function createTransformerWorkflow() {
  sessionStorage.setItem('flowly_pending_workflow_template', JSON.stringify(TRANSFORMER_WORKFLOW_TEMPLATE))
  await router.push('/workflows/new?template=transformer-classification')
}
</script>

<style lang="scss" scoped>
.training-redirect {
  max-width: 720px;
  margin: 0 auto;
  padding: 24px;
}

.wizard-card {
  margin-top: 16px;
  margin-bottom: 16px;
}

.redirect-card {
  .actions {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
  }
}
</style>
