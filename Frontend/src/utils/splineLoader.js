/**
 * Spline 3D 机器人加载（对齐 PPT/机器人登录/login-robot.html）
 */
import { Application } from '@splinetool/runtime'
import { APP_CONFIG } from '@/config'

const SPLINE_LOAD_ERROR = {
  WEBGL: '当前浏览器不支持 WebGL，无法显示 3D 机器人',
  NETWORK: '3D 机器人加载失败，请检查网络后刷新页面',
  WASM: '3D 运行时资源加载失败，请刷新页面或联系管理员',
  UNKNOWN: '3D 机器人加载失败，请刷新页面重试',
}

/** 与 login-robot.html 一致的场景地址 */
export const SPLINE_SCENE_URL =
  APP_CONFIG.auth.splineSceneUrl
  || 'https://prod.spline.design/kZDDjO5HuC9GJUM2/scene.splinecode'

/** 本地 WASM 目录（public/spline-wasm，由 scripts/copy-spline-wasm.mjs 同步） */
export const SPLINE_WASM_PATH = `${import.meta.env.BASE_URL}spline-wasm/`
export const SPLINE_UI_WASM_URL = `${import.meta.env.BASE_URL}spline-wasm/ui.wasm`

/**
 * 同步 canvas 像素尺寸，避免 WebGL 使用默认 300×150
 */
export function syncCanvasSize(canvas, container) {
  if (!canvas || !container) return

  const rect = container.getBoundingClientRect()
  const width = Math.floor(rect.width)
  const height = Math.floor(rect.height)
  if (width <= 0 || height <= 0) return

  const dpr = Math.min(window.devicePixelRatio || 1, 2)
  canvas.width = Math.max(1, Math.floor(width * dpr))
  canvas.height = Math.max(1, Math.floor(height * dpr))
  canvas.style.width = `${width}px`
  canvas.style.height = `${height}px`
}

/**
 * 等待容器具备有效尺寸后再初始化 WebGL
 */
export function waitForElementSize(element, timeoutMs = 8000) {
  if (!element) return Promise.resolve()

  if (element.clientWidth > 0 && element.clientHeight > 0) {
    return Promise.resolve()
  }

  return new Promise((resolve) => {
    let done = false
    const finish = () => {
      if (done) return
      done = true
      observer.disconnect()
      clearTimeout(timer)
      resolve()
    }

    const observer = new ResizeObserver(() => {
      if (element.clientWidth > 0 && element.clientHeight > 0) {
        finish()
      }
    })
    observer.observe(element)

    const timer = setTimeout(finish, timeoutMs)
  })
}

export function isWebGLAvailable() {
  if (typeof document === 'undefined') return false

  try {
    const canvas = document.createElement('canvas')
    return Boolean(
      canvas.getContext('webgl2', { failIfMajorPerformanceCaveat: false })
      || canvas.getContext('webgl', { failIfMajorPerformanceCaveat: false })
      || canvas.getContext('experimental-webgl', { failIfMajorPerformanceCaveat: false }),
    )
  } catch {
    return false
  }
}

async function verifySplineWasmAssets() {
  const assets = [
    `${SPLINE_WASM_PATH}process.wasm`,
    SPLINE_UI_WASM_URL,
  ]

  for (const url of assets) {
    const response = await fetch(url, { method: 'HEAD' })
    if (!response.ok) {
      throw new Error(`Spline WASM asset unavailable: ${url}`)
    }
  }
}

export function resolveSplineErrorMessage(error) {
  const message = String(error?.message || error || '')

  if (/webgl|bindtocurrentsequence|gl_vendor|gl_renderer/i.test(message)) {
    return SPLINE_LOAD_ERROR.WEBGL
  }
  if (/wasm|modelling-wasm|ui-wasm|arraybuffer|fetch/i.test(message)) {
    return SPLINE_LOAD_ERROR.WASM
  }
  if (/network|failed to fetch|load/i.test(message)) {
    return SPLINE_LOAD_ERROR.NETWORK
  }
  return SPLINE_LOAD_ERROR.UNKNOWN
}

async function loadSceneWithRetry(app, sceneUrl) {
  try {
    await app.load(sceneUrl)
  } catch {
    const retryUrl = `${sceneUrl}${sceneUrl.includes('?') ? '&' : '?'}t=${Date.now()}`
    await app.load(retryUrl)
  }
}

/**
 * 创建并加载 Spline Application（与 login-robot.html 行为一致）
 */
export async function createSplineApplication(canvas, container, sceneUrl = SPLINE_SCENE_URL) {
  if (!isWebGLAvailable()) {
    throw new Error(SPLINE_LOAD_ERROR.WEBGL)
  }

  syncCanvasSize(canvas, container || canvas.parentElement)
  await verifySplineWasmAssets()

  const app = new Application(canvas, {
    renderOnDemand: true,
    wasmPath: SPLINE_WASM_PATH,
  })

  if (typeof app.setUIWasmUrl === 'function') {
    app.setUIWasmUrl(SPLINE_UI_WASM_URL)
  }

  await loadSceneWithRetry(app, sceneUrl)
  return app
}

export function bindSplineResize(app, canvas, container) {
  if (!container) return () => {}

  const onResize = () => {
    syncCanvasSize(canvas, container)
    app?.requestRender?.()
  }

  const observer = new ResizeObserver(onResize)
  observer.observe(container)
  window.addEventListener('resize', onResize)

  return () => {
    observer.disconnect()
    window.removeEventListener('resize', onResize)
  }
}

export function bindSplineVisibility(app) {
  const onVisibility = () => {
    if (!app) return
    if (document.hidden) {
      app.stop?.()
    } else {
      app.play?.()
      app.requestRender?.()
    }
  }

  document.addEventListener('visibilitychange', onVisibility)
  return () => document.removeEventListener('visibilitychange', onVisibility)
}

export function disposeSplineApplication(app) {
  if (!app) return
  try {
    app.stop?.()
  } catch {
    // ignore
  }
}
