import {
  Sparkles, Bot, FileText, Database, Brain, Zap,
  Settings, MessageSquare, Code, Globe, Clock, Video, BookOpen,
} from 'lucide-vue-next'
import { getCssColor } from '@/utils/chartTheme'
import { getTemplateCategory } from '@/utils/workflowTransform'

export function getTemplateCategorySlug(template, categories = []) {
  const direct = template?.categorySlug ?? template?.category_slug
  if (direct) return direct

  if (template?.category && typeof template.category === 'object') {
    return template.category.slug || template.category.id || ''
  }

  const categoryName = template?.categoryName ?? template?.category_name
  if (categoryName && categories.length) {
    const matched = categories.find((cat) => cat.name === categoryName)
    if (matched) return matched.slug ?? matched.id
  }

  const fallback = getTemplateCategory(template)
  const matched = categories.find((cat) => (
    (cat.slug ?? cat.id) === fallback || cat.name === fallback
  ))
  if (matched) return matched.slug ?? matched.id

  return fallback
}

const ICON_MAP = {
  sparkles: Sparkles,
  bot: Bot,
  'file-text': FileText,
  filetext: FileText,
  database: Database,
  brain: Brain,
  zap: Zap,
  settings: Settings,
  message: MessageSquare,
  code: Code,
  globe: Globe,
  clock: Clock,
  video: Video,
  bookopen: BookOpen,
  Video,
  Bot,
  BookOpen,
  Brain,
  Database,
  FileText,
}

const SLUG_ICON_MAP = {
  'ai-agent': Bot,
  'rag-knowledge': BookOpen,
  'data-pipeline': Database,
  'office-automation': FileText,
  'video-generation': Video,
  'model-training': Brain,
  multimodal: Sparkles,
  rag: BookOpen,
  agent: Bot,
  data: Database,
  mlops: Brain,
  utility: Zap,
  ai: Bot,
  automation: Zap,
}

const SLUG_COLOR_VARS = {
  'ai-agent': '--accent-violet',
  'rag-knowledge': '--accent-cyan',
  'data-pipeline': '--accent-emerald',
  'office-automation': '--accent-blue',
  'video-generation': '--accent-rose',
  'model-training': '--accent-amber',
  multimodal: '--accent-rose',
  data: '--accent-amber',
  mlops: '--accent-amber',
  rag: '--accent-cyan',
  agent: '--accent-violet',
  utility: '--accent-emerald',
  ai: '--accent-violet',
  automation: '--accent-cyan',
  default: '--accent-blue',
}

const SLUG_ACCENT_CLASS = {
  'ai-agent': 'border-accent-violet',
  'rag-knowledge': 'border-accent-cyan',
  'data-pipeline': 'border-accent-emerald',
  'office-automation': 'border-accent-blue',
  'video-generation': 'border-accent-rose',
  'model-training': 'border-accent-amber',
  multimodal: 'border-accent-rose',
  data: 'border-accent-amber',
  mlops: 'border-accent-amber',
  rag: 'border-accent-cyan',
  agent: 'border-accent-violet',
  utility: 'border-accent-emerald',
  ai: 'border-accent-violet',
  automation: 'border-accent-cyan',
  default: 'border-accent-blue',
}

function normalizeIconKey(key) {
  return String(key || '')
    .replace(/([a-z])([A-Z])/g, '$1-$2')
    .toLowerCase()
}

export function resolveCategoryIcon(iconKey, slug) {
  if (iconKey && ICON_MAP[iconKey]) return ICON_MAP[iconKey]
  const normalized = normalizeIconKey(iconKey)
  if (normalized && ICON_MAP[normalized]) return ICON_MAP[normalized]
  if (slug && SLUG_ICON_MAP[slug]) return SLUG_ICON_MAP[slug]
  return Sparkles
}

export function resolveCategoryColor(categoryMeta, slug) {
  if (categoryMeta?.color) return categoryMeta.color
  const cssVar = SLUG_COLOR_VARS[slug] || SLUG_COLOR_VARS.default
  return getCssColor(cssVar, '#6366f1')
}

export function resolveCategoryAccentClass(slug) {
  return SLUG_ACCENT_CLASS[slug] || SLUG_ACCENT_CLASS.default
}

export function findTemplateCategory(template, categories = []) {
  const slug = getTemplateCategorySlug(template, categories)
  return categories.find((cat) => (cat.slug ?? cat.id) === slug) || null
}

export function getTemplateCategoryDisplayName(template, categories = []) {
  return (
    template?.categoryName
    ?? template?.category_name
    ?? template?.displayCategory
    ?? findTemplateCategory(template, categories)?.name
    ?? getTemplateCategory(template)
  )
}

export function getTemplateCategoryPresentation(template, categories = []) {
  const slug = getTemplateCategorySlug(template, categories)
  const categoryMeta = findTemplateCategory(template, categories)
  const color = resolveCategoryColor(categoryMeta, slug)
  const icon = resolveCategoryIcon(categoryMeta?.icon, slug)

  return {
    slug,
    name: getTemplateCategoryDisplayName(template, categories),
    icon,
    color,
    accentClass: resolveCategoryAccentClass(slug),
    gradient: `linear-gradient(135deg, ${color}55 0%, ${color}22 55%, transparent 100%)`,
  }
}
