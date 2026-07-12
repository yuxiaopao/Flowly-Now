/**
 * 从工作流对象解析列表卡片用的画布截图（保存时写入 config.canvas_preview）
 */
export function resolveWorkflowCanvasPreview(workflow) {
  if (!workflow) return ''
  const direct = workflow.canvasPreview || workflow.canvas_preview
  if (typeof direct === 'string' && direct.startsWith('data:image')) {
    return direct
  }
  const cfg = workflow.config
  if (cfg && typeof cfg === 'object') {
    const fromConfig = cfg.canvasPreview || cfg.canvas_preview
    if (typeof fromConfig === 'string' && fromConfig.startsWith('data:image')) {
      return fromConfig
    }
  }
  return ''
}

export function resolveWorkflowPreviewNodes(workflow) {
  if (!workflow) return []
  return workflow.nodesPreview || workflow.nodes_preview || []
}

export function resolveWorkflowPreviewEdges(workflow) {
  if (!workflow) return []
  return workflow.edgesPreview || workflow.edges_preview || []
}
