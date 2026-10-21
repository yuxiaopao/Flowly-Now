/** provide/inject：自定义节点 emit('select') 时同步 Editor PropertyPanel */
export const WORKFLOW_SELECT_NODE_KEY = Symbol('workflowSelectNode')

/** 点击节点成果时，打开编辑器底部执行面板并定位到该节点 */
export const WORKFLOW_FOCUS_EXECUTION_NODE_KEY = Symbol('workflowFocusExecutionNode')

/** Vue Flow 画布缩放与视口配置（ComfyUI 级宽区间） */
export const WORKFLOW_CANVAS_ZOOM = {
  min: 0.08,
  max: 4,
  default: 1,
  fitViewMax: 1.5,
  fitViewPadding: 0.45,
}

export const WORKFLOW_CANVAS_VIEWPORT = {
  x: 50,
  y: 50,
  zoom: WORKFLOW_CANVAS_ZOOM.default,
}

/** 工作流编辑器底部执行面板高度（拖拽拉伸预览区） */
export const WORKFLOW_EXECUTION_PANEL = {
  defaultHeight: 420,
  minHeight: 220,
  maxViewportOffset: 96,
  storageKey: 'flowly.workflow.executionPanelHeight',
}

export function clampExecutionPanelHeight(height, viewportHeight = 900) {
  const numeric = Number(height)
  const fallback = WORKFLOW_EXECUTION_PANEL.defaultHeight
  if (!Number.isFinite(numeric)) return fallback
  const maxHeight = Math.max(
    WORKFLOW_EXECUTION_PANEL.minHeight,
    Number(viewportHeight) - WORKFLOW_EXECUTION_PANEL.maxViewportOffset,
  )
  return Math.round(Math.min(maxHeight, Math.max(WORKFLOW_EXECUTION_PANEL.minHeight, numeric)))
}

export function readExecutionPanelHeight(storage, viewportHeight = 900) {
  try {
    const raw = storage?.getItem?.(WORKFLOW_EXECUTION_PANEL.storageKey)
    if (raw == null || raw === '') {
      return clampExecutionPanelHeight(WORKFLOW_EXECUTION_PANEL.defaultHeight, viewportHeight)
    }
    return clampExecutionPanelHeight(Number(raw), viewportHeight)
  } catch {
    return WORKFLOW_EXECUTION_PANEL.defaultHeight
  }
}

export function writeExecutionPanelHeight(height, storage, viewportHeight = 900) {
  const next = clampExecutionPanelHeight(height, viewportHeight)
  try {
    storage?.setItem?.(WORKFLOW_EXECUTION_PANEL.storageKey, String(next))
  } catch {
    // ignore quota / private mode
  }
  return next
}
