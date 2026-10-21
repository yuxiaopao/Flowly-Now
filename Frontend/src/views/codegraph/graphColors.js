/** Shared CodeGraph node/type color palette — bright for 3D readability */

export const TYPE_COLORS = {
  vue: '#86efac',
  js: '#fde047',
  ts: '#7dd3fc',
  py: '#93c5fd',
  json: '#fcd34d',
  md: '#e2e8f0',
  function: '#ddd6fe',
  css: '#f9a8d4',
  scss: '#f9a8d4',
  html: '#fdba74',
  default: '#67e8f9',
}

export function getTypeColor(type) {
  if (!type) return TYPE_COLORS.default
  const key = String(type).replace(/^file:/, '').split('.').pop()?.toLowerCase()
  return TYPE_COLORS[key] || TYPE_COLORS[type] || TYPE_COLORS.default
}

export function hexToRgba(hex, alpha = 1) {
  const raw = hex.replace('#', '')
  const full = raw.length === 3
    ? raw.split('').map(c => c + c).join('')
    : raw
  const n = parseInt(full, 16)
  const r = (n >> 16) & 255
  const g = (n >> 8) & 255
  const b = n & 255
  return `rgba(${r}, ${g}, ${b}, ${alpha})`
}
