import { RAG_CONFIG } from '@/config/rag'

export async function loadRagPages(fetchPage, params = {}) {
  const results = []
  let page = 1
  for (;;) {
    const response = await fetchPage({ ...params, page, page_size: RAG_CONFIG.pageSize })
    const items = response.results || (Array.isArray(response) ? response : [])
    results.push(...items)
    if (!response.next || !items.length) return results
    page += 1
  }
}

export function chunkDistribution(chunks) {
  const distribution = { '0-100': 0, '100-500': 0, '500-1000': 0, '1000-2000': 0, '2000+': 0 }
  for (const chunk of chunks) {
    const length = chunk.content?.length || 0
    const bucket = length < 100 ? '0-100' : length < 500 ? '100-500' : length < 1000 ? '500-1000' : length < 2000 ? '1000-2000' : '2000+'
    distribution[bucket] += 1
  }
  return distribution
}

export function validateRagFile(file, maxBytes = RAG_CONFIG.maxFileBytes, accept = RAG_CONFIG.fileAccept) {
  const extension = `.${file.name.split('.').pop().toLowerCase()}`
  if (!accept.split(',').includes(extension)) return '不支持此文件格式，请选择支持的文档。'
  if (!file.size) return '不能上传空文件。'
  if (file.size > maxBytes) return `文件过大，上限为 ${Math.round(maxBytes / 1024 / 1024)} MB。`
  return ''
}
