export const MEDIA_EXECUTION_KIND = 'external_media'
export const MEDIA_EXECUTION_LABELS = {
  local_render: '本地成片',
  archive: '历史成片归档',
  image_generation: '效果图生成',
}

export function getMediaExecutionLabel(execution) {
  const source = execution?.triggerSource ?? execution?.trigger_source
  if (source?.kind !== MEDIA_EXECUTION_KIND) return ''
  return MEDIA_EXECUTION_LABELS[source.method] || MEDIA_EXECUTION_LABELS.local_render
}
