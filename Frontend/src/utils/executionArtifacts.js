import { unwrapNodeExecutionOutput } from '@/utils/workflowTransform'

const PROMPT_KEYS = new Set([
  'prompt', 'user_input', 'userInput', 'text', 'input', 'instruction',
  'description', 'query', 'content', 'message', 'negative_prompt', 'negativePrompt',
])

const IMAGE_KEYS = new Set([
  'image_url', 'imageUrl', 'image', 'thumbnail', 'screenshot', 'preview', 'cover',
])

const VIDEO_KEYS = new Set(['video_url', 'videoUrl', 'video', 'mp4'])

const AUDIO_KEYS = new Set(['audio_url', 'audioUrl', 'audio', 'voice_url', 'voiceUrl', 'dubbed_audio_url', 'dubbedAudioUrl'])

const FILE_KEYS = new Set([
  'file_path', 'filePath', 'path', 'output_dir', 'outputDir', 'dataset_yaml_path',
  'model_path', 'modelPath', 'weights_path', 'weightsPath', 'checkpoint', 'weights',
  'dataset_path', 'datasetPath', 'yaml_path', 'yamlPath', 'local_path', 'localPath',
  'artifact_path', 'artifactPath', 'export_path', 'exportPath', 'bundle_path',
])

const WEBSITE_KEYS = new Set([
  'website_url', 'websiteUrl', 'site_url', 'siteUrl', 'html_path', 'htmlPath',
  'deploy_url', 'deployUrl', 'preview_url', 'previewUrl', 'site_id', 'siteId',
])

const SUBTITLE_KEYS = new Set([
  'srt', 'vtt', 'subtitle', 'subtitles', 'subtitle_url', 'subtitleUrl', 'transcript',
  'caption', 'captions',
])

const MEDIA_EXT = /\.(png|jpe?g|gif|webp|bmp|svg|mp4|webm|mov|avi|mkv|mp3|wav|ogg|m4a|flac|srt|vtt|pdf|zip|tar|gz|pt|pth|safetensors|onnx|bin|yaml|yml|json|csv|html)$/i
const WEIGHT_EXT = /\.(pt|pth|safetensors|onnx|bin|ckpt)$/i
const DATA_EXT = /\.(csv|json|yaml|yml|txt|md|pdf|docx?|xlsx?)$/i

/** 工作流元数据字段，不作为用户可见产物展示 */
const META_FIELD_KEYS = new Set([
  'workflowid', 'executionid', 'startedat', 'endedat', 'started_at', 'ended_at',
  'duration', 'status', 'taskid', 'task_id', 'mode', 'model', 'metadata',
  'variables', 'input_data', 'inputdata', 'node_outputs', 'nodeoutputs',
  'progress', 'version', 'trigger_type', 'triggered_by',
  'video_translation_step', 'lip_sync_applied', 'source_segments', 'source_video_url',
])

const SUMMARY_GROUP_IDS = ['prompt', 'image', 'video', 'audio', 'website', 'file', 'subtitle']

export const ARTIFACT_GROUPS = [
  { id: 'prompt', label: '提示词 / 文本', icon: 'text' },
  { id: 'image', label: '图片', icon: 'image' },
  { id: 'video', label: '视频', icon: 'video' },
  { id: 'audio', label: '音频', icon: 'audio' },
  { id: 'website', label: '网站', icon: 'website' },
  { id: 'file', label: '文件 / 权重 / 数据集', icon: 'file' },
  { id: 'subtitle', label: '字幕 / 资料', icon: 'subtitle' },
  { id: 'data', label: '结构化数据', icon: 'data' },
]

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i

function isNonEmptyString(value) {
  return typeof value === 'string' && value.trim().length > 0
}

function looksLikeUuid(value) {
  return isNonEmptyString(value) && UUID_RE.test(value.trim())
}

/**
 * 从工作流节点列表构建 id -> 可读名称 映射
 */
export function buildNodeNameMap(nodes = []) {
  const map = {}
  nodes.forEach((node) => {
    const id = node.id || node.node_id || node.nodeId
    if (!id) return
    const config = node.config || node.data || {}
    map[id] = config.label
      || node.name
      || node.label
      || node.nodeTypeDisplay
      || node.node_type_display
      || node.nodeType
      || node.node_type
      || node.type
      || id
  })
  return map
}

function resolveNodeLabel(nodeId, nodeName, nodeNameMap = {}, nodeTypeDisplay = null) {
  if (nodeName && !looksLikeUuid(nodeName)) return nodeName
  if (nodeId && nodeNameMap[nodeId]) return nodeNameMap[nodeId]
  if (nodeTypeDisplay && String(nodeTypeDisplay).trim()) return String(nodeTypeDisplay).trim()
  return nodeName || nodeId || null
}

function isMetaField(key) {
  return META_FIELD_KEYS.has(String(key || '').toLowerCase())
}

function nodeHasOutput(nodeExecution) {
  const output = nodeExecution?.outputData ?? nodeExecution?.output_data ?? nodeExecution?.output
  return output != null && (typeof output !== 'object' || Object.keys(output).length > 0)
}

function isHttpUrl(value) {
  return isNonEmptyString(value) && /^https?:\/\//i.test(value.trim())
}

function looksLikePath(value) {
  if (!isNonEmptyString(value)) return false
  const v = value.trim()
  return v.includes('/') || v.includes('\\') || MEDIA_EXT.test(v)
}

function inferTypeFromKey(key, value) {
  const k = String(key || '').toLowerCase()
  if (PROMPT_KEYS.has(k)) return 'prompt'
  if (IMAGE_KEYS.has(k)) return 'image'
  if (VIDEO_KEYS.has(k)) return 'video'
  if (AUDIO_KEYS.has(k)) return 'audio'
  if (WEBSITE_KEYS.has(k)) return 'website'
  if (SUBTITLE_KEYS.has(k)) return 'subtitle'
  if (FILE_KEYS.has(k)) return 'file'
  if (k === 'url' && isNonEmptyString(value)) {
    const v = value.trim().toLowerCase()
    if (/\.(png|jpe?g|gif|webp)(\?|$)/i.test(v)) return 'image'
    if (/\.(mp4|webm|mov)(\?|$)/i.test(v)) return 'video'
    if (/\.(mp3|wav|ogg|m4a)(\?|$)/i.test(v)) return 'audio'
    if (/\.(srt|vtt)(\?|$)/i.test(v)) return 'subtitle'
    if (isHttpUrl(value)) return 'image'
  }
  if (isNonEmptyString(value)) {
    if (WEIGHT_EXT.test(value)) return 'file'
    if (DATA_EXT.test(value)) return 'subtitle'
    if (looksLikePath(value) && !isHttpUrl(value)) return 'file'
  }
  return null
}

function inferTypeFromValue(value) {
  if (!isNonEmptyString(value)) return null
  const v = value.trim().toLowerCase()
  if (/\.(png|jpe?g|gif|webp)(\?|$)/i.test(v)) return 'image'
  if (/\.(mp4|webm|mov)(\?|$)/i.test(v)) return 'video'
  if (/\.(mp3|wav|ogg|m4a)(\?|$)/i.test(v)) return 'audio'
  if (/\.(srt|vtt)(\?|$)/i.test(v)) return 'subtitle'
  if (WEIGHT_EXT.test(v)) return 'file'
  if (isHttpUrl(value) && !/\.html?(\?|$)/i.test(v)) return null
  if (/^https?:\/\/.+\.html?(\?|$)/i.test(v)) return 'website'
  return null
}

function makeArtifact(type, value, meta = {}) {
  const text = typeof value === 'string' ? value.trim() : value
  if (text == null || text === '') return null

  const artifact = {
    id: `${meta.nodeId || 'global'}:${type}:${typeof text === 'string' ? text.slice(0, 80) : JSON.stringify(text).slice(0, 80)}`,
    type,
    label: meta.label || meta.field || type,
    value: typeof text === 'string' ? text : JSON.stringify(text, null, 2),
    nodeId: meta.nodeId || null,
    nodeName: meta.nodeName || null,
    nodeType: meta.nodeType || null,
    nodeTypeDisplay: meta.nodeTypeDisplay || null,
    field: meta.field || null,
  }

  if (['image', 'video', 'audio', 'website', 'subtitle', 'file'].includes(type)) {
    artifact.url = typeof text === 'string' ? text : null
    artifact.preview = ['image', 'video'].includes(type)
    artifact.openable = isHttpUrl(artifact.url) || looksLikePath(artifact.url)
  }

  if (type === 'prompt' && typeof text === 'string' && text.length > 500) {
    artifact.truncated = true
  }

  return artifact
}

function walkOutput(output, meta, push) {
  const data = unwrapNodeExecutionOutput(output)
  if (data == null) return

  if (typeof data === 'string') {
    const type = inferTypeFromValue(data) || (data.length > 80 ? 'prompt' : 'data')
    const artifact = makeArtifact(type, data, meta)
    if (artifact) push(artifact)
    return
  }

  if (typeof data !== 'object') return

  if (Array.isArray(data.images)) {
    data.images.forEach((item, index) => {
      const url = typeof item === 'string' ? item : item?.url || item?.image_url || item?.imageUrl
      if (!url) return
      push(makeArtifact('image', url, { ...meta, field: `images[${index}]`, label: `图片 ${index + 1}` }))
    })
  }

  if (Array.isArray(data.results)) {
    data.results.forEach((item, index) => {
      if (!item || typeof item !== 'object') return
      const lang = item.target_language || item.targetLanguage || `lang-${index + 1}`
      if (item.video_url) {
        push(makeArtifact('video', item.video_url, { ...meta, field: `results[${index}].video_url`, label: `翻译视频 (${lang})` }))
      }
      if (item.dubbed_audio_url) {
        push(makeArtifact('audio', item.dubbed_audio_url, { ...meta, field: `results[${index}].dubbed_audio_url`, label: `配音 (${lang})` }))
      }
      if (item.subtitles) {
        push(makeArtifact('subtitle', item.subtitles, { ...meta, field: `results[${index}].subtitles`, label: `字幕 (${lang})` }))
      }
    })
  }

  Object.entries(data).forEach(([key, raw]) => {
    if (raw == null || key.startsWith('_')) return

    if (key === 'images' && Array.isArray(raw)) return

    if (Array.isArray(raw)) {
      raw.forEach((item, index) => {
        if (typeof item === 'string' || typeof item === 'number') {
          walkOutput({ [key]: item }, { ...meta, field: `${key}[${index}]` }, push)
        } else if (item && typeof item === 'object') {
          walkOutput(item, { ...meta, field: `${key}[${index}]` }, push)
        }
      })
      return
    }

    if (typeof raw === 'object') {
      if (raw.url || raw.image_url || raw.video_url || raw.audio_url) {
        walkOutput(raw, { ...meta, field: key }, push)
      } else if (raw.text || raw.content || raw.prompt) {
        walkOutput(raw, { ...meta, field: key }, push)
      } else if (Object.keys(raw).length <= 12) {
        walkOutput(raw, { ...meta, field: key }, push)
      } else {
        push(makeArtifact('data', raw, { ...meta, field: key, label: key }))
      }
      return
    }

    const inferred = inferTypeFromKey(key, raw) || inferTypeFromValue(raw)
    if (inferred) {
      const artifact = makeArtifact(inferred, String(raw), { ...meta, field: key, label: key })
      if (artifact) push(artifact)
      return
    }

    if (
      typeof raw === 'string'
      && raw.length >= 8
      && !/^[\d.]+$/.test(raw)
      && !isMetaField(key)
    ) {
      push(makeArtifact('data', raw, { ...meta, field: key, label: key }))
    }
  })
}

export function nodeExecutionsFromStatus(execution) {
  const raw = execution?.nodeStatus || execution?.node_status
  if (!raw || typeof raw !== 'object') return []

  return Object.entries(raw).map(([nodeId, state]) => {
    if (typeof state === 'string') {
      return {
        nodeId,
        node_id: nodeId,
        nodeName: nodeId,
        status: state,
        outputData: null,
        output_data: null,
      }
    }
    return {
      nodeId,
      node_id: nodeId,
      nodeName: state?.node_name || state?.nodeName || state?.node_type_display || nodeId,
      nodeType: state?.node_type || state?.nodeType || '',
      nodeTypeDisplay: state?.node_type_display || state?.nodeTypeDisplay || null,
      status: state?.status || 'pending',
      outputData: state?.output ?? state?.output_data ?? state?.outputData ?? null,
      output_data: state?.output ?? state?.output_data ?? state?.outputData ?? null,
      error_message: state?.error ?? state?.error_message ?? null,
    }
  })
}

/**
 * 从节点执行记录与工作流输出中提取可视化产物
 */
export function extractExecutionArtifacts({
  nodeExecutions = [],
  outputData = null,
  nodeStatusMap = null,
  execution = null,
  nodeNameMap = null,
  includeWorkflowAggregate = null,
  includeStructuredData = true,
} = {}) {
  const artifacts = []
  const seen = new Set()
  const nameMap = nodeNameMap || {}

  const push = (artifact) => {
    if (!artifact) return
    if (!includeStructuredData && artifact.type === 'data') return
    if (artifact.type === 'data' && isMetaField(artifact.field)) return

    artifact.nodeName = resolveNodeLabel(
      artifact.nodeId,
      artifact.nodeName,
      nameMap,
      artifact.nodeTypeDisplay,
    )

    const dedupeKey = `${artifact.type}|${artifact.value}|${artifact.field || ''}`
    if (seen.has(dedupeKey)) return
    seen.add(dedupeKey)
    artifacts.push(artifact)
  }

  let resolvedNodeExecutions = nodeExecutions
  if (!resolvedNodeExecutions.length && execution) {
    resolvedNodeExecutions = nodeExecutionsFromStatus(execution)
  }

  const hasNodeLevelOutputs = resolvedNodeExecutions.some(nodeHasOutput)
    || (nodeStatusMap && Object.values(nodeStatusMap).some(
      (state) => typeof state === 'object' && state?.output != null
    ))

  const shouldIncludeAggregate = includeWorkflowAggregate ?? !hasNodeLevelOutputs

  resolvedNodeExecutions.forEach((nodeExecution) => {
    const nodeId = nodeExecution.nodeId || nodeExecution.node_id || nodeExecution.node
    const rawName = nodeExecution.nodeName || nodeExecution.node_name || nodeExecution.name || nodeId
    const nodeType = nodeExecution.nodeType || nodeExecution.node_type || nodeExecution.type || ''
    const nodeTypeDisplay = nodeExecution.nodeTypeDisplay || nodeExecution.node_type_display || null
    const nodeName = resolveNodeLabel(nodeId, rawName, nameMap, nodeTypeDisplay)
    let output = nodeExecution.outputData ?? nodeExecution.output_data ?? nodeExecution.output
    if (output == null && nodeStatusMap && nodeId && nodeStatusMap[nodeId]) {
      const state = nodeStatusMap[nodeId]
      output = typeof state === 'object'
        ? (state.output ?? state.output_data ?? state.outputData)
        : null
    }
    walkOutput(output, { nodeId, nodeName, nodeType, nodeTypeDisplay }, push)
  })

  if (nodeStatusMap && typeof nodeStatusMap === 'object') {
    const coveredNodeIds = new Set(
      resolvedNodeExecutions
        .map((n) => n.nodeId || n.node_id || n.node)
        .filter(Boolean)
    )
    Object.entries(nodeStatusMap).forEach(([nodeId, state]) => {
      if (coveredNodeIds.has(nodeId)) return
      const payload = typeof state === 'object' ? (state?.output ?? state?.output_data) : null
      if (payload) {
        walkOutput(payload, {
          nodeId,
          nodeName: resolveNodeLabel(
            nodeId,
            state?.node_name || state?.nodeName || nodeId,
            nameMap,
            state?.node_type_display || state?.nodeTypeDisplay,
          ),
          nodeType: state?.node_type || state?.nodeType || '',
          nodeTypeDisplay: state?.node_type_display || state?.nodeTypeDisplay || null,
        }, push)
      }
    })
  }

  if (outputData && shouldIncludeAggregate) {
    walkOutput(outputData, { nodeName: '工作流汇总', nodeType: 'output' }, push)
  }

  if (outputData && hasNodeLevelOutputs) {
    const nodeOutputs = outputData.nodeOutputs || outputData.node_outputs
    if (nodeOutputs && typeof nodeOutputs === 'object') {
      const coveredNodeIds = new Set(
        resolvedNodeExecutions
          .map((n) => n.nodeId || n.node_id || n.node)
          .filter(Boolean)
      )
      Object.entries(nodeOutputs).forEach(([nodeId, out]) => {
        if (coveredNodeIds.has(nodeId)) return
        walkOutput(out, {
          nodeId,
          nodeName: resolveNodeLabel(nodeId, nodeId, nameMap),
          nodeType: '',
        }, push)
      })
    }
  }

  const grouped = Object.fromEntries(ARTIFACT_GROUPS.map((g) => [g.id, []]))
  artifacts.forEach((artifact) => {
    const bucket = grouped[artifact.type] || grouped.data
    bucket.push(artifact)
  })

  return {
    artifacts,
    grouped,
    total: artifacts.length,
    hasArtifacts: artifacts.length > 0,
  }
}

export function getArtifactPreviewUrl(artifact) {
  if (!artifact) return null
  if (artifact.type === 'image' || artifact.type === 'video') {
    return artifact.url || (isHttpUrl(artifact.value) ? artifact.value : null)
  }
  return null
}

/**
 * 列表行轻量摘要：缩略图 + 各类型数量（不额外请求 API）
 */
export function getExecutionArtifactSummary(execution, options = {}) {
  const result = extractExecutionArtifacts({
    nodeExecutions: execution?.nodeExecutions ?? execution?.node_executions ?? [],
    outputData: execution?.outputData ?? execution?.output_data ?? null,
    nodeStatusMap: execution?.nodeStatus ?? execution?.node_status ?? null,
    execution,
    includeWorkflowAggregate: false,
    includeStructuredData: false,
    ...options,
  })

  const counts = {}
  SUMMARY_GROUP_IDS.forEach((id) => {
    const n = (result.grouped[id] || []).length
    if (n > 0) counts[id] = n
  })

  const thumbnail = result.artifacts.find((a) => a.type === 'image')
    || result.artifacts.find((a) => a.type === 'video')

  return {
    total: Object.values(counts).reduce((sum, n) => sum + n, 0),
    counts,
    thumbnailUrl: getArtifactPreviewUrl(thumbnail),
    hasArtifacts: result.hasArtifacts,
  }
}
