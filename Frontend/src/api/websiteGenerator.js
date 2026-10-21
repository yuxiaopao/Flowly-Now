import api from './index'

export const websiteGeneratorApi = {
  list: (params) => api.get('/website-generator/', { params }),
  generate: (data) => api.post('/website-generator/generate/', normalizeGeneratePayload(data)),
  get: (id) => api.get(`/website-generator/${id}/`),
  update: (id, data) => api.put(`/website-generator/${id}/`, data),
  delete: (id) => api.delete(`/website-generator/${id}/`),
  download: (id) => api.get(`/website-generator/${id}/download/`, { responseType: 'blob' }),
  deploy: (id) => api.post(`/website-generator/${id}/deploy/`),
  agentMessage: (id, data) => api.post(`/website-generator/${id}/agent/message/`, data),
  generateFromTraining: (trainingRunId, name) => api.post('/website-generator/generate/', normalizeGeneratePayload({
    training_run_id: trainingRunId,
    name: name || `YOLO Detection - ${new Date().toLocaleDateString('zh-CN')}`,
    website_type: 'detection',
  })),
}

function normalizeGeneratePayload(data = {}) {
  return {
    ...data,
    training_job_id: data.trainingJobId || data.training_job_id || data.trainingRunId || data.training_run_id || '',
    training_run_id: data.trainingRunId || data.training_run_id || data.trainingJobId || data.training_job_id || '',
    model_artifact_manifest: data.modelArtifactManifest || data.model_artifact_manifest || {},
    site_brief: data.siteBrief || data.site_brief || {},
    required_features: data.requiredFeatures || data.required_features || ['imageRecognition', 'videoRecognition', 'factRecognition', 'historyRecords'],
    theme_profile: data.themeProfile || data.theme_profile || {},
    environment_config: { ...(data.environmentConfig || data.environment_config || {}), dbEngine: 'mysql' },
    agent_memory_enabled: data.agentMemoryEnabled ?? data.agent_memory_enabled ?? true,
    frontend_framework: 'vue',
    backend_framework: 'flask',
    website_type: data.websiteType || data.website_type || 'detection',
    model_path: data.modelPath || data.model_path || '',
    output_dir: data.outputDir || data.output_dir || '',
  }
}
