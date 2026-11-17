export const MODEL_EVALUATION = Object.freeze({
  pageSize: 20,
  imageSize: { min: 8, max: 1024, step: 8 },
  defaults: { metrics: ['accuracy', 'precision', 'recall', 'f1'], features: [], split: 'test', imageSize: 224 },
  metrics: [
    { value: 'accuracy', label: '准确率' },
    { value: 'precision', label: '精确率' },
    { value: 'recall', label: '召回率' },
    { value: 'f1', label: 'F1' },
    { value: 'auc', label: 'AUC' },
    { value: 'mAP50', label: 'mAP@50（目标检测）' },
    { value: 'mAP50_95', label: 'mAP@50:95（目标检测）' },
  ],
  resources: {
    model: { endpoint: '/training/training-jobs/', label: '训练记录', params: { status: 'completed' } },
    training: { endpoint: '/training/datasets/', label: '训练数据集', params: {} },
    generic: { endpoint: '/datasets/', label: '通用数据集', params: {} },
  },
})

export function evaluationConfig(value = {}) {
  const metrics = Array.isArray(value.metrics) ? value.metrics : typeof value.metrics === 'string'
    ? value.metrics.split(',').map(item => item.trim()).filter(Boolean) : MODEL_EVALUATION.defaults.metrics
  return {
    ...value, label: value.label ?? '', description: value.description ?? '',
    trainingJobId: value.trainingJobId || value.trainingRunId || '', modelPath: value.modelPath ?? '',
    trainingDatasetId: value.trainingDatasetId ?? '', datasetId: value.datasetId ?? '', testDataset: value.testDataset ?? '',
    metrics: [...metrics], features: Array.isArray(value.features) ? [...value.features] : [], labelColumn: value.labelColumn ?? '',
    split: value.split ?? MODEL_EVALUATION.defaults.split,
    imageSize: value.imageSize ?? MODEL_EVALUATION.defaults.imageSize,
  }
}

export function evaluationMetricRows(output) {
  const values = output?.metrics ?? output ?? {}
  return MODEL_EVALUATION.metrics.filter(metric => Object.hasOwn(values, metric.value)).map(metric => ({
    ...metric, display: typeof values[metric.value] === 'number' && Number.isFinite(values[metric.value])
      ? `${(values[metric.value] * 100).toFixed(1)}%` : '无法计算',
  }))
}
