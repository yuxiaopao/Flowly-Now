/** provide/inject：自定义节点 emit('select') 时同步 Editor PropertyPanel */
export const WORKFLOW_SELECT_NODE_KEY = Symbol('workflowSelectNode')

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
