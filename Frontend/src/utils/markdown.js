import { marked } from 'marked'
import DOMPurify from 'dompurify'

marked.setOptions({
  breaks: true,
  gfm: true,
})

/**
 * Render Markdown to sanitized HTML for safe v-html usage.
 * @param {string} text
 * @returns {string}
 */
export function renderMarkdown(text) {
  if (!text) return ''
  const raw = marked.parse(String(text), { async: false })
  return DOMPurify.sanitize(raw, { USE_PROFILES: { html: true } })
}
