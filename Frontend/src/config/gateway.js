export const GATEWAY_MODEL_UI = Object.freeze({
  costPrecision: 6,
  aggregateCostPrecision: 4,
  providers: Object.freeze([
    { value: 'openai', label: 'OpenAI', type: 'primary' },
    { value: 'anthropic', label: 'Anthropic', type: 'warning' },
    { value: 'azure', label: 'Azure OpenAI', type: 'success' },
    { value: 'google', label: 'Google AI', type: 'info' },
    { value: 'ollama', label: 'Ollama', type: 'info' },
    { value: 'deepseek', label: 'DeepSeek', type: 'info' },
    { value: 'dashscope', label: '阿里云百炼', type: 'info' },
    { value: 'agnes', label: 'Agnes AI', type: 'info' },
    { value: 'mistral', label: 'Mistral', type: 'info' },
    { value: 'groq', label: 'Groq', type: 'info' },
    { value: 'custom', label: '自定义', type: 'info' },
  ].map(Object.freeze)),
})

export function gatewayErrorMessage(error, fallback) {
  const data = error?.response?.data
  return [data?.error, data?.data?.error, data?.detail, data?.message, error?.message]
    .find(message => typeof message === 'string' && message.trim()) || fallback
}
