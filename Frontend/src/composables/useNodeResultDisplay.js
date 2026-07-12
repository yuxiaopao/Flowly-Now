/**
 * 从节点执行输出中解析可展示内容（文本 / 图片 / 视频 / 音频 / 图表）
 */

const TEXT_KEYS = [
  'Display', 'display', '_display', 'result', 'text', 'output', 'content',
  'message', 'data', 'answer', 'response', 'translation', 'translated_text',
]

const MEDIA_KEYS = {
  image: ['url', 'image', 'image_url', 'imageUrl', 'src', 'thumbnail'],
  video: ['video', 'video_url', 'videoUrl', 'mp4'],
  audio: ['audio', 'audio_url', 'audioUrl', 'mp3', 'wav'],
}

function isLikelyUrl(value) {
  if (typeof value !== 'string') return false
  return /^(https?:\/\/|data:image\/|data:video\/|data:audio\/|\/)/i.test(value.trim())
}

function pickFirst(obj, keys) {
  if (!obj || typeof obj !== 'object') return null
  for (const key of keys) {
    const val = obj[key]
    if (val != null && val !== '') return val
  }
  return null
}

function extractTextFromValue(value, depth = 0) {
  if (value == null || depth > 4) return ''
  if (typeof value === 'string') return value
  if (typeof value === 'number' || typeof value === 'boolean') return String(value)
  if (Array.isArray(value)) {
    return value.map((item) => extractTextFromValue(item, depth + 1)).filter(Boolean).join('\n')
  }
  if (typeof value === 'object') {
    for (const key of TEXT_KEYS) {
      if (value[key] != null) {
        const nested = extractTextFromValue(value[key], depth + 1)
        if (nested) return nested
      }
    }
    if (value.error) return String(value.error)
    try {
      return JSON.stringify(value, null, 2)
    } catch {
      return String(value)
    }
  }
  return String(value)
}

function extractMediaUrl(output, kind) {
  if (!output) return null
  const keys = MEDIA_KEYS[kind] || []

  if (Array.isArray(output)) {
    for (const item of output) {
      const url = extractMediaUrl(item, kind)
      if (url) return url
    }
    return null
  }

  if (typeof output === 'string' && isLikelyUrl(output)) {
    if (kind === 'image' && !/\.(mp4|webm|mov|mp3|wav|ogg)(\?|$)/i.test(output)) return output
    if (kind === 'video' && /\.(mp4|webm|mov)(\?|$)/i.test(output)) return output
    if (kind === 'audio' && /\.(mp3|wav|ogg|m4a)(\?|$)/i.test(output)) return output
    if (kind === 'image') return output
  }

  if (typeof output === 'object') {
    const direct = pickFirst(output, keys)
    if (typeof direct === 'string' && isLikelyUrl(direct)) return direct

    if (kind === 'image' && Array.isArray(output.images) && output.images.length) {
      const first = output.images[0]
      if (typeof first === 'string' && isLikelyUrl(first)) return first
      if (first && typeof first === 'object') {
        const nestedUrl = pickFirst(first, keys) || first.url
        if (typeof nestedUrl === 'string' && isLikelyUrl(nestedUrl)) return nestedUrl
        if (typeof first.base64 === 'string' && first.base64) {
          return first.base64.startsWith('data:') ? first.base64 : `data:image/png;base64,${first.base64}`
        }
      }
    }

    if (kind === 'audio' && typeof output.audio_base64 === 'string' && output.audio_base64) {
      const b64 = output.audio_base64
      return b64.startsWith('data:') ? b64 : `data:audio/mpeg;base64,${b64}`
    }

    for (const key of TEXT_KEYS) {
      const nested = output[key]
      if (nested && typeof nested === 'object') {
        const url = pickFirst(nested, keys)
        if (typeof url === 'string' && isLikelyUrl(url)) return url
      }
    }
  }
  return null
}

function detectMediaKind(output, preferredFormat) {
  const format = String(preferredFormat || '').toLowerCase()
  if (['image', 'img', 'picture'].includes(format)) return 'image'
  if (['video', 'mp4'].includes(format)) return 'video'
  if (['audio', 'sound', 'voice'].includes(format)) return 'audio'
  if (['chart', 'graph'].includes(format)) return 'chart'

  if (Array.isArray(output)) {
    if (extractMediaUrl(output, 'video')) return 'video'
    if (extractMediaUrl(output, 'audio')) return 'audio'
    if (extractMediaUrl(output, 'image')) return 'image'
  }

  if (extractMediaUrl(output, 'video')) return 'video'
  if (extractMediaUrl(output, 'audio')) return 'audio'
  if (extractMediaUrl(output, 'image')) return 'image'

  const text = extractTextFromValue(output)
  if (isLikelyUrl(text)) {
    if (/\.(mp4|webm|mov)(\?|$)/i.test(text)) return 'video'
    if (/\.(mp3|wav|ogg|m4a)(\?|$)/i.test(text)) return 'audio'
    if (/^data:image\//i.test(text) || /\.(png|jpe?g|gif|webp|svg)(\?|$)/i.test(text)) return 'image'
  }

  if (output && typeof output === 'object') {
    if (!preferredFormat) {
      const fmt = String(output._format || output.format || output.Format || '').toLowerCase()
      const TEXT_FORMATS = ['text', 'json', 'markdown', 'html', 'string', 'plain']
      if (fmt && !TEXT_FORMATS.includes(fmt)) {
        return detectMediaKind(output, fmt)
      }
    }
    if (output.chart || output.chartOption || output.labels) return 'chart'
  }

  return 'text'
}

function extractChartOption(output) {
  if (!output || typeof output !== 'object') return null
  if (output.chartOption && typeof output.chartOption === 'object') return output.chartOption
  if (output.chart && typeof output.chart === 'object') return output.chart
  if (Array.isArray(output.labels) && Array.isArray(output.values)) {
    return {
      xAxis: { type: 'category', data: output.labels },
      yAxis: { type: 'value' },
      series: [{ type: 'bar', data: output.values }],
      grid: { left: 40, right: 12, top: 24, bottom: 28 },
    }
  }
  if (Array.isArray(output.series)) {
    return {
      xAxis: { type: 'category', data: output.categories || output.labels || [] },
      yAxis: { type: 'value' },
      series: output.series,
      grid: { left: 40, right: 12, top: 24, bottom: 28 },
    }
  }
  return null
}

function tryParseJsonOutput(value) {
  if (typeof value !== 'string') return null
  const trimmed = value.trim()
  if (!trimmed.startsWith('{') && !trimmed.startsWith('[')) return null
  try {
    return JSON.parse(trimmed)
  } catch {
    return null
  }
}

/**
 * @param {*} output - 节点原始输出
 * @param {{ format?: string, outputFormat?: string }} [config]
 */
export function resolveNodeDisplayContent(output, config = {}) {
  const rawOutput = output
  let normalizedOutput = output
  if (typeof normalizedOutput === 'string') {
    normalizedOutput = tryParseJsonOutput(normalizedOutput) ?? normalizedOutput
  } else if (normalizedOutput && typeof normalizedOutput === 'object') {
    const hintedFormat = String(
      config.format || config.outputFormat || config.output_format
      || normalizedOutput._format || normalizedOutput.format || normalizedOutput.Format || '',
    ).toLowerCase()
    const hasChartFields = Array.isArray(normalizedOutput.labels) && Array.isArray(normalizedOutput.values)

    if (hintedFormat === 'chart' && hasChartFields) {
      // Keep normalized chart payload as-is.
    } else {
      for (const key of ['Display', 'display', 'result', 'text']) {
        const nested = normalizedOutput[key]
        if (typeof nested === 'string') {
          const parsed = tryParseJsonOutput(nested)
          if (parsed) {
            if (hintedFormat === 'chart' && Array.isArray(parsed) && hasChartFields) {
              normalizedOutput = { ...normalizedOutput, labels: parsed }
            } else if (hintedFormat === 'chart' && parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
              normalizedOutput = { ...normalizedOutput, ...parsed }
            } else if (hintedFormat !== 'chart') {
              normalizedOutput = parsed
            }
            break
          }
        }
      }
    }

    if (hintedFormat === 'chart' && rawOutput && typeof rawOutput === 'object') {
      const labels = rawOutput.labels || normalizedOutput.labels
      const values = rawOutput.values || normalizedOutput.values
      if (Array.isArray(labels) && Array.isArray(values)) {
        normalizedOutput = { ...normalizedOutput, labels, values }
        if (rawOutput.title && !normalizedOutput.title) normalizedOutput.title = rawOutput.title
      }
    }
  }

  const preferredFormat = config.format || config.outputFormat || config.output_format
    || (normalizedOutput && typeof normalizedOutput === 'object'
      ? (normalizedOutput._format || normalizedOutput.format || normalizedOutput.Format)
      : null)

  let kind = detectMediaKind(normalizedOutput, preferredFormat)
  let imageUrl = extractMediaUrl(normalizedOutput, 'image')
  let videoUrl = extractMediaUrl(normalizedOutput, 'video')
  let audioUrl = extractMediaUrl(normalizedOutput, 'audio')

  const pref = String(preferredFormat || '').toLowerCase()
  if (pref === 'image' && imageUrl) kind = 'image'
  if (pref === 'video' && videoUrl) kind = 'video'
  if (pref === 'audio' && audioUrl) kind = 'audio'

  const text = kind === 'text' ? extractTextFromValue(normalizedOutput) : ''
  const chartOption = kind === 'chart' ? extractChartOption(normalizedOutput) : null

  if (kind === 'image' && !imageUrl) imageUrl = null
  if (kind === 'video' && !videoUrl) videoUrl = null
  if (kind === 'audio' && !audioUrl) audioUrl = null
  if (kind === 'image') {
    videoUrl = null
    audioUrl = null
  } else if (kind === 'video') {
    imageUrl = null
    audioUrl = null
  } else if (kind === 'audio') {
    imageUrl = null
    videoUrl = null
  }

  return {
    kind,
    text,
    imageUrl: kind === 'image' ? imageUrl : null,
    videoUrl: kind === 'video' ? videoUrl : null,
    audioUrl: kind === 'audio' ? audioUrl : null,
    chartOption,
    hasContent: Boolean(text || imageUrl || videoUrl || audioUrl || chartOption),
  }
}

export function truncateText(text, maxLen = 120) {
  if (!text) return ''
  const normalized = String(text).replace(/\s+/g, ' ').trim()
  if (normalized.length <= maxLen) return normalized
  return `${normalized.slice(0, maxLen)}…`
}
