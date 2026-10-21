export const RAG_CONFIG = Object.freeze({
  topK: 5,
  maxTopK: 50,
  minSimilarity: 0,
  chunkSize: 1000,
  chunkOverlap: 200,
  pageSize: 100,
  chunkPageSize: 20,
  maxUploadFiles: 10,
  pollInterval: 3000,
  requestTimeout: 180000,
  fileAccept: '.txt,.md,.markdown,.csv,.json,.html,.htm,.pdf,.docx,.xlsx,.pptx',
  maxFileBytes: 20 * 1024 * 1024,
  systemPrompt: '根据知识库中的证据回答问题，使用 [1]、[2] 标注来源。没有依据时明确说明。',
})

export const RETRIEVAL_MODES = [
  { value: 'keyword', label: '关键词检索 · 无需嵌入模型' },
  { value: 'semantic', label: '语义检索 · 需要嵌入模型' },
  { value: 'hybrid', label: '混合检索 · 关键词 + 语义' },
]

export const CHUNK_STRATEGIES = [
  { value: 'recursive', label: '按段落和句子分块' },
  { value: 'fixed', label: '固定长度分块' },
]

export const DOCUMENT_STATUSES = {
  pending: { label: '待处理', type: 'info' },
  processing: { label: '处理中', type: 'warning' },
  completed: { label: '已处理', type: 'success' },
  failed: { label: '失败', type: 'danger' },
}

export const RAG_TEXT = {
  askTab: '知识问答',
  askHint: '回答会引用当前知识库的资料。没有相关资料时会明确告知；生成回答需要可用的对话模型。',
  queryPlaceholder: '例如：工作流失败后应该如何排查？',
  noEvidence: '未找到相关依据',
  answered: '已基于检索资料生成',
  modeHint: '关键词模式可直接使用。语义和混合模式需配置真实嵌入模型；配置变更后请重新处理文档。',
  sources: '引用资料',
  searchTitle: '知识检索测试',
  failure: '处理失败，请查看文档错误信息后重试。',
}
