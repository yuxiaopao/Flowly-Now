/**
 * Collect documents, code files, and images from a finished/running execution.
 */

function flattenOutput(output) {
  if (output == null) return {}
  if (typeof output === 'string') return { text: output }
  if (typeof output !== 'object') return {}
  const layers = [output]
  if (output.output && typeof output.output === 'object' && !Array.isArray(output.output)) {
    layers.push(output.output)
  }
  if (output.result && typeof output.result === 'object' && !Array.isArray(output.result)) {
    layers.push(output.result)
  }
  if (output.data && typeof output.data === 'object' && !Array.isArray(output.data)) {
    layers.push(output.data)
  }
  return Object.assign({}, ...layers)
}

function stripFence(text) {
  if (typeof text !== 'string') return ''
  let t = text.trim()
  t = t.replace(/^```(?:markdown|md|json|python|py)?\s*/i, '')
  t = t.replace(/\s*```$/i, '')
  return t.trim()
}

function looksLikeMarkdown(text) {
  if (typeof text !== 'string' || text.length < 40) return false
  return /^#{1,4}\s/m.test(text) || /^\*\*[^*]+\*\*/m.test(text) || /\|.+\|/.test(text)
}

function looksLikeJson(text) {
  if (typeof text !== 'string') return false
  const t = text.trim()
  return (t.startsWith('{') || t.startsWith('[') || t.startsWith('```json')) && t.length > 20
}

function looksLikeCode(text) {
  if (typeof text !== 'string' || text.length < 20) return false
  return /^(import |from |def |class |#include )/m.test(text)
}

function nodeLabel(node) {
  return node?.data?.label || node?.label || node?.name || node?.id || '节点'
}

function nodeType(node) {
  return node?.data?.type || node?.type || node?.node_type || ''
}

function nodeConfig(node) {
  return node?.data?.config || node?.config || {}
}

function dataUrlFromChart(item) {
  if (!item || typeof item !== 'object') return ''
  if (item.url && String(item.url).startsWith('data:')) return item.url
  const b64 = item.base64 || item.image || item.data
  if (!b64 || typeof b64 !== 'string') return ''
  const kind = item.type === 'svg_bar' || item.type === 'svg' ? 'image/svg+xml' : 'image/png'
  return `data:${kind};base64,${b64.replace(/^data:[^,]+,/, '')}`
}

function extractMarkdownImages(markdown) {
  if (typeof markdown !== 'string') return []
  const out = []
  const re = /!\[([^\]]*)\]\((data:image\/[a-zA-Z0-9.+-]+;base64,[^)]+)\)/g
  let match
  while ((match = re.exec(markdown))) {
    out.push({ title: match[1] || `图 ${out.length + 1}`, url: match[2] })
  }
  return out
}

function pushUnique(list, item, key) {
  if (!item) return
  if (list.some((x) => x.key === key)) return
  list.push({ ...item, key })
}

function documentRank(item) {
  if (!item) return 0
  if (item.rank) return item.rank
  const title = item.title || ''
  const path = item.path || ''
  if (title.includes('论文终稿')) return 100
  if (path.endsWith('paper/main.md') || title === 'paper/main.md') return 90
  if (item.kind === 'docx' || path.endsWith('.docx')) return 80
  if (title.includes('三线表') || path.includes('TABLE')) return 70
  return 0
}

export function collectExecutionOutputs({ nodeStatus = {}, workflowNodes = [], outputData = null } = {}) {
  const documents = []
  const codes = []
  const images = []

  Object.entries(nodeStatus || {}).forEach(([nodeId, state]) => {
    const name = (typeof state === 'object' && (state.name || state.node_name)) || nodeId
    const output = typeof state === 'object'
      ? (state.output || state.output_data || state.outputData || state)
      : {}
    const data = flattenOutput(output)

    const path = typeof data.path === 'string' ? data.path : ''
    const format = String(data.format || '')
    const content = typeof data.content === 'string' ? data.content : ''
    const text = typeof data.text === 'string' ? data.text : ''
    const tableMd = typeof data.table_markdown === 'string' ? data.table_markdown : ''

    if (path && /\.(py|js|ts|tsx|jsx|sql|sh)$/i.test(path)) {
      pushUnique(codes, {
        id: `${nodeId}:file:${path}`,
        title: path.replace(/\\/g, '/'),
        language: /\.py$/i.test(path) ? 'python' : 'text',
        nodeId,
        nodeName: name,
        path,
        content: stripFence(content || text || (typeof data.code === 'string' ? data.code : '')),
      }, `codepath:${path}`)
    }

    if (path && /\.(md|markdown|docx?|txt|pdf|tex)$/i.test(path)) {
      const body = stripFence(content || text || tableMd)
      pushUnique(documents, {
        id: `${nodeId}:file:${path}`,
        title: path.replace(/\\/g, '/'),
        kind: /\.docx?$/i.test(path) ? 'docx' : 'markdown',
        nodeId,
        nodeName: name,
        path,
        format,
        content: body,
      }, `path:${path}`)
    }

    if (typeof data.code === 'string' && data.code.trim() && looksLikeCode(data.code)) {
      pushUnique(codes, {
        id: `${nodeId}:outcode`,
        title: `${name}.py`,
        language: 'python',
        nodeId,
        nodeName: name,
        content: data.code,
      }, `outcode:${nodeId}`)
    }

    if (tableMd.trim()) {
      pushUnique(documents, {
        id: `${nodeId}:table`,
        title: `${name} · 三线表`,
        kind: 'markdown',
        nodeId,
        nodeName: name,
        content: tableMd,
      }, `table:${nodeId}`)
    }

    const paperBody = stripFence(content || text)
    if (
      (name.includes('组装') || name.includes('格式自检') || format === 'markdown')
      && looksLikeMarkdown(paperBody)
      && paperBody.length > 80
    ) {
      pushUnique(documents, {
        id: `${nodeId}:paper`,
        title: name.includes('格式自检') ? '论文终稿 (Markdown)' : `${name}.md`,
        kind: 'markdown',
        nodeId,
        nodeName: name,
        content: paperBody,
        rank: name.includes('格式自检') ? 100 : name.includes('组装') ? 40 : 30,
      }, name.includes('格式自检') ? 'paper:final' : `paper:${nodeId}`)
    } else if (looksLikeMarkdown(paperBody) && paperBody.length > 200 && /^(#{1,3}\s|## )/m.test(paperBody)) {
      pushUnique(documents, {
        id: `${nodeId}:section`,
        title: `${name}.md`,
        kind: 'markdown',
        nodeId,
        nodeName: name,
        content: paperBody,
      }, `section:${nodeId}`)
    }

    if (Array.isArray(data.chart_images)) {
      data.chart_images.forEach((item, index) => {
        const url = dataUrlFromChart(item)
        if (!url) return
        pushUnique(images, {
          id: `${nodeId}:chart:${index}`,
          title: item.title || item.caption || `图 ${item.figure_no || index + 1}`,
          url,
          nodeId,
          nodeName: name,
        }, `img:${nodeId}:chart:${index}`)
      })
    }

    if (Array.isArray(data.markdown_embeds)) {
      data.markdown_embeds.forEach((md, index) => {
        extractMarkdownImages(String(md)).forEach((img, imgIndex) => {
          pushUnique(images, {
            id: `${nodeId}:embed:${index}:${imgIndex}`,
            title: img.title,
            url: img.url,
            nodeId,
            nodeName: name,
          }, `img:${nodeId}:embed:${index}:${imgIndex}`)
        })
      })
    }

    extractMarkdownImages(paperBody).forEach((img, imgIndex) => {
      pushUnique(images, {
        id: `${nodeId}:mdimg:${imgIndex}`,
        title: img.title,
        url: img.url,
        nodeId,
        nodeName: name,
      }, `img:${nodeId}:md:${imgIndex}`)
    })

    if (looksLikeJson(text) && (name.includes('模型建立') || name.includes('求解') || name.includes('分解') || name.includes('解析'))) {
      pushUnique(codes, {
        id: `${nodeId}:json`,
        title: `${name}.json`,
        language: 'json',
        nodeId,
        nodeName: name,
        content: stripFence(text),
      }, `json:${nodeId}`)
    }
  })

  ;(workflowNodes || []).forEach((node) => {
    const type = nodeType(node)
    const cfg = nodeConfig(node)
    const code = typeof cfg.code === 'string' ? cfg.code : ''
    if ((type === 'code' || code) && code.trim()) {
      const id = String(node.id || '')
      pushUnique(codes, {
        id: `${id}:source`,
        title: `${nodeLabel(node)}.py`,
        language: 'python',
        nodeId: id,
        nodeName: nodeLabel(node),
        content: code,
      }, `src:${id}`)
    }
  })

  if (outputData && typeof outputData === 'object') {
    const nested = outputData.node_outputs || outputData.nodeOutputs
    if (nested && typeof nested === 'object') {
      Object.entries(nested).forEach(([nodeId, out]) => {
        const data = flattenOutput(out)
        if (Array.isArray(data.chart_images)) {
          data.chart_images.forEach((item, index) => {
            const url = dataUrlFromChart(item)
            if (!url) return
            pushUnique(images, {
              id: `agg:chart:${index}`,
              title: item.title || `图 ${index + 1}`,
              url,
              nodeId,
            }, `img:${nodeId}:agg:${index}`)
          })
        }
      })
    }
  }

  documents.sort((a, b) => documentRank(b) - documentRank(a))
  const namedDocuments = documents.filter((item) => !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}(?:\.md)?$/i.test(item.title || ''))

  return {
    documents: namedDocuments,
    codes,
    images,
    totals: {
      documents: namedDocuments.length,
      codes: codes.length,
      images: images.length,
    },
  }
}

export { looksLikeCode, looksLikeMarkdown }

export function summarizeNodeExecution({ nodeId, name, output } = {}) {
  if (output == null || output === '') {
    return {
      documents: [],
      codes: [],
      images: [],
      totals: { documents: 0, codes: 0, images: 0 },
      excerpt: '',
      path: '',
      hasResult: false,
    }
  }

  const bundle = collectExecutionOutputs({
    nodeStatus: {
      [nodeId || 'node']: {
        name: name || nodeId || '节点',
        output,
      },
    },
    workflowNodes: [],
  })
  const data = flattenOutput(output)
  const excerpt = stripFence(data.content || data.text || data.table_markdown || '')
  const path = typeof data.path === 'string' ? data.path : ''
  const hasResult = bundle.totals.documents > 0
    || bundle.totals.images > 0
    || Boolean(path)
    || excerpt.trim().length > 0

  return {
    ...bundle,
    excerpt: excerpt.slice(0, 220),
    path,
    hasResult,
  }
}
