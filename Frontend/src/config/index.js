// Flowly 前端配置文件
// 用于管理所有硬编码的配置值
// 所有硬编码值应优先从环境变量读取，环境变量不存在时使用默认值

import Cookies from 'js-cookie'

export const APP_CONFIG = {
  // 应用信息
  appName: 'Flowly',
  appFullName: 'Flowly - AI Agent 工作流编排平台',

  // API 配置 - 从环境变量读取，默认为本地开发服务器
  apiBaseUrl: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  apiPrefix: import.meta.env.VITE_API_PREFIX || '/api/v1',

  // 请求超时配置 (毫秒) - 从环境变量读取
  requestTimeout: Number(import.meta.env.VITE_API_TIMEOUT_MS) || 30000,

  // NL 工作流生成/对话（LLM 耗时长，单独放宽）
  nlWorkflowRequestTimeout: Number(import.meta.env.VITE_NL_WORKFLOW_TIMEOUT_MS) || 600000,

  // 重试次数配置 - 从环境变量读取
  maxRetries: Number(import.meta.env.VITE_API_MAX_RETRIES) || 1,

  // WebSocket 配置
  wsUrl: import.meta.env.VITE_WS_URL || '',

  // 向量存储默认配置
  vectorStore: {
    defaultHost: import.meta.env.VITE_VECTOR_STORE_DEFAULT_HOST || 'localhost',
    defaultPort: Number(import.meta.env.VITE_VECTOR_STORE_DEFAULT_PORT) || 6333,
    defaultProtocol: import.meta.env.VITE_VECTOR_STORE_DEFAULT_PROTOCOL || 'http',
    defaultDimension: 1536,
    defaultCollection: 'default',
  },

  // 域名配置
  domains: {
    mainDomain: import.meta.env.VITE_MAIN_DOMAIN || 'flowly.com',
    apiSubdomain: import.meta.env.VITE_API_SUBDOMAIN || 'api.flowly.com',
    tenantSubdomain: import.meta.env.VITE_TENANT_SUBDOMAIN || 'tenant.flowly.com'
  },

  // 文档链接
  documentation: {
    docsUrl: import.meta.env.VITE_DOCS_URL || 'https://docs.flowly.com',
    apiDocsUrl: import.meta.env.VITE_API_DOCS_URL || 'https://docs.flowly.com/api',
    supportUrl: import.meta.env.VITE_SUPPORT_URL || 'https://flowly.com/support'
  },

  // 社交登录配置
  socialLogin: {
    google: {
      clientId: import.meta.env.VITE_GOOGLE_CLIENT_ID || '',
      redirectUri: import.meta.env.VITE_GOOGLE_REDIRECT_URI || ''
    }
  },

  // 分页配置
  pagination: {
    default: 20,
    sizes: [10, 20, 50, 100],
    execution: 20,
    agent: 12,
    marketplace: 24,
  },

  // Canvas 配置
  canvas: {
    viewport: { x: 0, y: 0, zoom: 1 },
    size: { width: 4000, height: 3000 },
  },

  // LLM 默认配置
  llm: {
    defaultModel: import.meta.env.VITE_LLM_DEFAULT_MODEL || 'qwen2.5-coder:7b',
    defaultTemperature: Number(import.meta.env.VITE_LLM_DEFAULT_TEMPERATURE) || 0.7,
    defaultMaxTokens: Number(import.meta.env.VITE_LLM_DEFAULT_MAX_TOKENS) || 2000,
    contextWindow: Number(import.meta.env.VITE_LLM_CONTEXT_WINDOW) || 10,
  },

  // Embedding 默认配置
  embedding: {
    defaultModel: import.meta.env.VITE_DEFAULT_EMBEDDING_MODEL || 'nomic-embed-text',
  },

  // 桌面端 Agent 下载与默认配置
  desktopAgent: {
    downloadBaseUrl: import.meta.env.VITE_DESKTOP_AGENT_DOWNLOAD_BASE_URL || 'https://flowly.app/downloads',
    downloads: {
      win: import.meta.env.VITE_DESKTOP_AGENT_DOWNLOAD_WIN || 'https://flowly.app/downloads/FlowlyAgent-Setup.exe',
      mac: import.meta.env.VITE_DESKTOP_AGENT_DOWNLOAD_MAC || 'https://flowly.app/downloads/FlowlyAgent.dmg',
      linux: import.meta.env.VITE_DESKTOP_AGENT_DOWNLOAD_LINUX || 'https://flowly.app/downloads/FlowlyAgent.AppImage',
    },
    defaultEpochs: Number(import.meta.env.VITE_DESKTOP_AGENT_DEFAULT_EPOCHS) || 100,
    defaultYoloVersion: import.meta.env.VITE_DESKTOP_AGENT_DEFAULT_YOLO_VERSION || 'v8',
    defaultModelVariant: import.meta.env.VITE_DESKTOP_AGENT_DEFAULT_MODEL_VARIANT || 'n',
  },

  // 登录/注册页 Spline 3D 机器人
  auth: {
    splineSceneUrl:
      import.meta.env.VITE_AUTH_SPLINE_SCENE_URL
      || 'https://prod.spline.design/kZDDjO5HuC9GJUM2/scene.splinecode',
    assistantWelcome:
      import.meta.env.VITE_AUTH_ASSISTANT_WELCOME
      || '你好！我是小流，Flowly 的登录助手。有什么想了解的吗？',
    assistantTimeoutMs: Number(import.meta.env.VITE_AUTH_ASSISTANT_TIMEOUT_MS) || 60000,
  },
}

// 生成完整的 API URL
export function getApiUrl(path = '') {
  return `${APP_CONFIG.apiBaseUrl}${APP_CONFIG.apiPrefix}${path}`
}

// 生成完整的 API Base URL
export function getApiBaseUrl() {
  return `${APP_CONFIG.apiBaseUrl}${APP_CONFIG.apiPrefix}`
}

/** 从后端 public site-config 合并运行时默认值（模型、API 地址等） */
export function applyRuntimeConfig(runtime) {
  if (!runtime || typeof runtime !== 'object') return

  if (runtime.api_base_url) {
    APP_CONFIG.apiBaseUrl = runtime.api_base_url
  }
  if (runtime.ws_url) {
    APP_CONFIG.wsUrl = runtime.ws_url
  }
  if (runtime.llm) {
    if (runtime.llm.default_model) APP_CONFIG.llm.defaultModel = runtime.llm.default_model
    if (runtime.llm.default_temperature != null) {
      APP_CONFIG.llm.defaultTemperature = Number(runtime.llm.default_temperature)
    }
    if (runtime.llm.default_max_tokens != null) {
      APP_CONFIG.llm.defaultMaxTokens = Number(runtime.llm.default_max_tokens)
    }
  }
  if (runtime.embedding?.default_model) {
    APP_CONFIG.embedding.defaultModel = runtime.embedding.default_model
  }
  if (runtime.vector_store) {
    if (runtime.vector_store.default_host) {
      APP_CONFIG.vectorStore.defaultHost = runtime.vector_store.default_host
    }
    if (runtime.vector_store.default_port != null) {
      APP_CONFIG.vectorStore.defaultPort = Number(runtime.vector_store.default_port)
    }
    if (runtime.vector_store.default_protocol) {
      APP_CONFIG.vectorStore.defaultProtocol = runtime.vector_store.default_protocol
    }
  }
}

function resolveApiHost() {
  try {
    return new URL(APP_CONFIG.apiBaseUrl).host
  } catch {
    return window.location.host
  }
}

/** 追加 JWT 到 WebSocket URL（浏览器 WS 握手无法带 Authorization 头） */
function appendAccessToken(url) {
  const token = Cookies.get('access_token') || localStorage.getItem('access_token')
  if (!token) return url
  const separator = url.includes('?') ? '&' : '?'
  return `${url}${separator}token=${encodeURIComponent(token)}`
}

/** 构建 WebSocket URL（支持 VITE_WS_URL 为完整 ws(s):// 地址或 host） */
export function getWebSocketUrl(path = '') {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  const configured = (APP_CONFIG.wsUrl || '').trim()

  let wsUrl
  if (configured) {
    if (configured.startsWith('ws://') || configured.startsWith('wss://')) {
      wsUrl = `${configured.replace(/\/$/, '')}${normalizedPath}`
    } else {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      wsUrl = `${protocol}//${configured.replace(/\/$/, '')}${normalizedPath}`
    }
  } else {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    wsUrl = `${protocol}//${resolveApiHost()}${normalizedPath}`
  }

  return appendAccessToken(wsUrl)
}

// 生成租户域名
export function getTenantDomain(tenantSlug) {
  return `${tenantSlug}.${APP_CONFIG.domains.tenantSubdomain}`
}

// 导出默认配置
export default APP_CONFIG

/** 后端 API 完整前缀 URL，用于 Webhook/SSE 等不能走 Vite 代理的场景 */
export function getPublicApiUrl(path = '') {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  return `${APP_CONFIG.apiBaseUrl}${APP_CONFIG.apiPrefix}${normalizedPath}`
}
