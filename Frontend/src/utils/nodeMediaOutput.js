/**
 * 多模态节点（文生图 / 文生视频等）输出解析
 */
export function unwrapMediaOutput(output) {
  if (output == null) return output
  if (typeof output !== 'object') return output
  if (output.output != null && typeof output.output === 'object') {
    const inner = output.output
    if (inner.images || inner.video_url || inner.videoUrl || inner.url || inner.image) {
      return inner
    }
  }
  return output
}

export function extractImageUrl(output) {
  const value = unwrapMediaOutput(output)
  if (!value) return null
  if (typeof value === 'string') return value
  if (Array.isArray(value.images) && value.images.length) {
    const first = value.images[0]
    if (typeof first === 'string') return first
    if (first?.url) return first.url
    if (first?.base64) return `data:image/png;base64,${first.base64}`
  }
  return value.url || value.image || value.data || null
}

export function isVideoMediaUrl(url) {
  return /\.(mp4|webm|mov|m4v)(\?|$)/i.test(String(url || ''))
}

export function extractVideoUrl(output) {
  const value = unwrapMediaOutput(output)
  if (!value) return null
  if (typeof value === 'string') {
    return isVideoMediaUrl(value) ? value : null
  }
  return value.video_url || value.videoUrl || value.url || null
}

export function extractVideoPosterUrl(output) {
  const value = unwrapMediaOutput(output)
  if (!value) return null
  if (value.thumbnail) return value.thumbnail
  if (value.thumb) return value.thumb
  const url = value.url || ''
  return url && !isVideoMediaUrl(url) ? url : null
}

function parseSizeString(size) {
  if (!size || typeof size !== 'string') return null
  const match = size.match(/(\d+)\s*[x×]\s*(\d+)/i)
  if (!match) return null
  const width = Number(match[1])
  const height = Number(match[2])
  if (!width || !height) return null
  return { width, height, ratio: width / height }
}

export function resolveMediaAspectRatio(output, fallbackSize) {
  const value = unwrapMediaOutput(output)
  if (value && typeof value === 'object') {
    const width = Number(value.width || value.w)
    const height = Number(value.height || value.h)
    if (width > 0 && height > 0) return width / height
  }
  const parsed = parseSizeString(fallbackSize)
  if (parsed) return parsed.ratio
  return null
}

export function resolveMediaDimensions(output, fallbackSize) {
  const value = unwrapMediaOutput(output)
  if (value && typeof value === 'object') {
    const width = Number(value.width || value.w)
    const height = Number(value.height || value.h)
    if (width > 0 && height > 0) return { width, height }
  }
  return parseSizeString(fallbackSize)
}
