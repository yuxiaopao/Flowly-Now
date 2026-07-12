import { toPng } from 'html-to-image'

const DEFAULT_BG = '#0a0a14'
const EXCLUDE_ANCESTORS = ['.vue-flow__controls', '.vue-flow__minimap', '.editor-minimap']

function shouldIncludeNode(node) {
  if (!(node instanceof HTMLElement)) return true
  return !EXCLUDE_ANCESTORS.some((sel) => node.closest(sel))
}

function compressDataUrl(dataUrl, maxWidth, quality) {
  return new Promise((resolve, reject) => {
    const img = new Image()
    img.onload = () => {
      const scale = Math.min(1, maxWidth / img.width)
      const w = Math.max(1, Math.round(img.width * scale))
      const h = Math.max(1, Math.round(img.height * scale))
      const canvas = document.createElement('canvas')
      canvas.width = w
      canvas.height = h
      const ctx = canvas.getContext('2d')
      if (!ctx) {
        resolve(dataUrl)
        return
      }
      ctx.fillStyle = DEFAULT_BG
      ctx.fillRect(0, 0, w, h)
      ctx.drawImage(img, 0, 0, w, h)
      resolve(canvas.toDataURL('image/jpeg', quality))
    }
    img.onerror = () => reject(new Error('Failed to compress workflow preview'))
    img.src = dataUrl
  })
}

function waitForPaint() {
  return new Promise((resolve) => {
    requestAnimationFrame(() => requestAnimationFrame(resolve))
  })
}

function resolveCaptureRoot(vueFlowApi) {
  if (typeof vueFlowApi.getRootElement === 'function') {
    const root = vueFlowApi.getRootElement()
    if (root instanceof HTMLElement) {
      return root.querySelector('.vue-flow__viewport') || root
    }
  }

  const rootEl = vueFlowApi?.$el || vueFlowApi
  if (rootEl instanceof HTMLElement) {
    return rootEl.querySelector('.vue-flow__viewport') || rootEl
  }

  return null
}

function resolveFitView(vueFlowApi) {
  if (typeof vueFlowApi?.fitView !== 'function') return null
  return vueFlowApi.fitView.bind(vueFlowApi)
}

function resolveGetViewport(vueFlowApi) {
  if (typeof vueFlowApi?.getViewport === 'function') return vueFlowApi.getViewport.bind(vueFlowApi)
  return null
}

function resolveSetViewport(vueFlowApi) {
  if (typeof vueFlowApi?.setViewport === 'function') return vueFlowApi.setViewport.bind(vueFlowApi)
  return null
}

/**
 * 截取 Vue Flow 编辑画布为 JPEG data URL，用于列表卡片预览
 * @param {object} vueFlowApi - useVueFlow() 或 VueFlow 组件 ref（含 fitView / getViewport / setViewport）
 * @param {object} [options]
 * @returns {Promise<string|null>}
 */
export async function captureWorkflowCanvas(vueFlowApi, options = {}) {
  if (!vueFlowApi) return null

  const maxWidth = options.maxWidth ?? 720
  const quality = options.quality ?? 0.75
  const fitViewPadding = options.fitViewPadding ?? 0.14

  const getViewport = resolveGetViewport(vueFlowApi)
  const setViewport = resolveSetViewport(vueFlowApi)
  const fitView = resolveFitView(vueFlowApi)

  let savedViewport = null
  if (getViewport) {
    savedViewport = getViewport()
  }

  if (fitView) {
    await fitView({ padding: fitViewPadding, duration: 0, maxZoom: 1.25 })
  }
  await waitForPaint()

  const captureEl = resolveCaptureRoot(vueFlowApi)
  if (!(captureEl instanceof HTMLElement)) return null

  try {
    const dataUrl = await toPng(captureEl, {
      pixelRatio: 1,
      backgroundColor: DEFAULT_BG,
      cacheBust: true,
      filter: shouldIncludeNode,
    })

    return compressDataUrl(dataUrl, maxWidth, quality)
  } finally {
    if (savedViewport && setViewport) {
      await setViewport(savedViewport, { duration: 0 })
    }
  }
}

/**
 * 构建 Editor 内截图 API（useVueFlow + VueFlow 组件 ref）
 */
export function buildVueFlowCaptureApi({ fitView, getViewport, setViewport, vueFlowRef }) {
  return {
    fitView,
    getViewport,
    setViewport,
    getRootElement: () => vueFlowRef?.value?.$el || vueFlowRef?.$el || null,
  }
}
