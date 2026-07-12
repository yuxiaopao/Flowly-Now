// Tool Labels Configuration
// Centralized management for tool display labels (i18n-ready)

export const TOOL_LABELS = {
  calculator: '计算器',
  search: '搜索',
  weather: '天气',
  web_scraper: '网页抓取',
  text_template: '文本模板',
  json_parser: 'JSON 解析',
  datetime: '日期时间',
  knowledge_base: '知识库检索',
}

// Get tool label by tool name
export function getToolLabel(tool) {
  return TOOL_LABELS[tool] || tool
}

// Tool display options for dropdowns
export const TOOL_OPTIONS = Object.entries(TOOL_LABELS).map(([value, label]) => ({
  value,
  label,
}))

// Default model options (fallback when API is unavailable)
export const MODEL_OPTIONS = [
  { value: 'qwen2.5-coder:7b', label: 'Qwen2.5 Coder 7B (本地)' },
  { value: 'llama3', label: 'Llama 3 (本地)' },
  { value: 'mistral', label: 'Mistral (本地)' },
  { value: 'phi3', label: 'Phi-3 (本地)' },
  { value: 'gpt-4', label: 'GPT-4' },
  { value: 'gpt-4-turbo', label: 'GPT-4 Turbo' },
  { value: 'gpt-4o', label: 'GPT-4o' },
  { value: 'claude-3-opus', label: 'Claude 3 Opus' },
  { value: 'claude-3-sonnet', label: 'Claude 3 Sonnet' },
  { value: 'claude-3-haiku', label: 'Claude 3 Haiku' },
]

// Get default model label
export function getModelLabel(model) {
  const option = MODEL_OPTIONS.find((m) => m.value === model)
  return option ? option.label : model
}
