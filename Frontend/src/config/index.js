// Flowly 前端配置文件
// 用于管理所有硬编码的配置值
// 所有硬编码值应优先从环境变量读取，环境变量不存在时使用默认值

export const APP_CONFIG = {
  // 应用信息
  appName: 'Flowly',
  appFullName: 'Flowly - AI Agent 工作流编排平台',

  // API 配置 - 从环境变量读取，默认为本地开发服务器
  apiBaseUrl: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  apiPrefix: import.meta.env.VITE_API_PREFIX || '/api/v1',

  // 请求超时配置 (毫秒) - 从环境变量读取
  requestTimeout: Number(import.meta.env.VITE_API_TIMEOUT_MS) || 30000,

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

  // 管理后台默认配置
  admin: {
    rateLimitPerMinute: 60,
    maxTokens: 4096,
    executionTimeout: 300,
  },

  // LLM 默认配置
  llm: {
    defaultModel: 'qwen2.5-coder:7b',
    defaultTemperature: 0.7,
    defaultMaxTokens: 2000,
    contextWindow: 10,
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

// 生成租户域名
export function getTenantDomain(tenantSlug) {
  return `${tenantSlug}.${APP_CONFIG.domains.tenantSubdomain}`
}

// 导出默认配置
export default APP_CONFIG
