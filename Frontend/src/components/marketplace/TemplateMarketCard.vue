<template>
  <article
    class="template-market-card hover-lift"
    :class="presentation.accentClass"
    @click="$emit('open', template)"
  >
    <div class="card-preview">
      <img
        v-if="hasThumbnail"
        :src="thumbnail"
        alt=""
        class="preview-image"
        loading="lazy"
      >
      <div
        v-else
        class="preview-visual"
        :style="{ background: presentation.gradient }"
      >
        <component
          :is="presentation.icon"
          :size="32"
          class="preview-icon"
          :style="{ color: presentation.color }"
        />
        <div
          v-if="nodeCount > 0"
          class="preview-node-strip"
          aria-hidden="true"
        >
          <span
            v-for="i in previewDotCount"
            :key="i"
            class="preview-node-dot"
            :style="{ borderColor: presentation.color, backgroundColor: `${presentation.color}22` }"
          />
        </div>
      </div>

      <div class="preview-badges">
        <span
          class="category-pill"
          :style="{
            backgroundColor: `${presentation.color}22`,
            color: presentation.color,
            borderColor: `${presentation.color}44`,
          }"
        >
          {{ presentation.name }}
        </span>
        <span
          v-if="isFeatured"
          class="featured-pill"
        >
          精选
        </span>
      </div>
    </div>

    <div class="card-body">
      <h3 class="card-title">
        {{ template.name }}
      </h3>
      <p class="card-desc">
        {{ template.description || '暂无描述' }}
      </p>
      <div
        v-if="difficultyLabel"
        class="difficulty-tag"
      >
        {{ difficultyLabel }}
      </div>
    </div>

    <div class="card-footer">
      <div class="card-meta">
        <span class="meta-item">
          <GitBranch :size="12" />
          {{ nodeCount }} 节点
        </span>
        <span class="meta-item">
          <Download :size="12" />
          {{ formattedUseCount }}
        </span>
        <span
          v-if="rating > 0"
          class="meta-item rating"
        >
          <Star
            :size="12"
            :fill="'currentColor'"
          />
          {{ rating.toFixed(1) }}
        </span>
      </div>
      <button
        class="use-btn"
        type="button"
        @click.stop="$emit('use', template)"
      >
        使用
        <ArrowRight :size="12" />
      </button>
    </div>
  </article>
</template>

<script setup>
import { computed } from 'vue'
import { GitBranch, Download, Star, ArrowRight } from 'lucide-vue-next'
import { getTemplateCategoryPresentation } from '@/composables/useTemplateCategoryPresentation'
import {
  getTemplateNodeCount,
  getTemplateRating,
  getTemplateUseCount,
} from '@/utils/workflowTransform'

const props = defineProps({
  template: {
    type: Object,
    required: true,
  },
  categories: {
    type: Array,
    default: () => [],
  },
})

defineEmits(['open', 'use'])

const presentation = computed(() => (
  getTemplateCategoryPresentation(props.template, props.categories)
))

const thumbnail = computed(() => (
  props.template?.thumbnail
  || props.template?.thumbnail_url
  || props.template?.thumbnailUrl
  || ''
))

const hasThumbnail = computed(() => (
  typeof thumbnail.value === 'string'
  && (thumbnail.value.startsWith('data:image') || thumbnail.value.startsWith('http'))
))

const nodeCount = computed(() => getTemplateNodeCount(props.template))
const rating = computed(() => getTemplateRating(props.template))
const formattedUseCount = computed(() => {
  const num = getTemplateUseCount(props.template)
  if (num >= 1000) return `${(num / 1000).toFixed(1)}k`
  return String(num)
})

const previewDotCount = computed(() => Math.min(Math.max(nodeCount.value, 1), 6))

const isFeatured = computed(() => Boolean(
  props.template?.isFeatured ?? props.template?.is_featured
))

const difficultyLabel = computed(() => {
  const map = {
    beginner: '入门',
    intermediate: '中级',
    advanced: '进阶',
  }
  const key = props.template?.difficulty
  return map[key] || ''
})
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.template-market-card {
  position: relative;
  display: flex;
  flex-direction: column;
  background: var(--card-bg);
  border: 1px solid var(--border-primary);
  border-radius: 18px;
  overflow: hidden;
  cursor: pointer;
  transition:
    border-color 0.25s ease,
    box-shadow 0.25s ease,
    transform 0.25s cubic-bezier(0.22, 1, 0.36, 1);

  &:hover {
    border-color: var(--border-primary);
    box-shadow: var(--shadow-lg);

    .use-btn {
      opacity: 1;
      transform: translateY(0);
    }
  }

  &.border-accent-cyan:hover,
  &.border-accent-violet:hover,
  &.border-accent-amber:hover,
  &.border-accent-emerald:hover,
  &.border-accent-rose:hover,
  &.border-accent-blue:hover {
    border-color: var(--border-primary) !important;
  }
}

.card-preview {
  position: relative;
  height: 132px;
  overflow: hidden;
  background: var(--surface-muted);
  border-bottom: 1px solid var(--border-primary);
}

.preview-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.preview-visual {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  position: relative;
}

.preview-icon {
  opacity: 0.9;
}

.preview-node-strip {
  display: flex;
  gap: 6px;
  align-items: center;
}

.preview-node-dot {
  width: 10px;
  height: 10px;
  border-radius: 3px;
  border: 1px solid;
  opacity: 0.85;
}

.preview-badges {
  position: absolute;
  top: 10px;
  left: 10px;
  right: 10px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  pointer-events: none;
}

.category-pill {
  display: inline-flex;
  align-items: center;
  max-width: 70%;
  padding: 4px 10px;
  border-radius: 999px;
  border: 1px solid;
  font-size: 11px;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  backdrop-filter: blur(8px);
}

.featured-pill {
  flex-shrink: 0;
  padding: 4px 8px;
  border-radius: 6px;
  background: var(--accent-amber-soft);
  border: 1px solid color-mix(in srgb, var(--accent-amber) 35%, transparent);
  color: var(--accent-amber);
  font-size: 10px;
  font-weight: 700;
}

.card-body {
  padding: 16px 16px 12px;
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.card-title {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
  line-height: 1.35;
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.card-desc {
  margin: 0;
  font-size: 13px;
  line-height: 1.55;
  color: var(--text-secondary);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  min-height: 2.9em;
}

.difficulty-tag {
  align-self: flex-start;
  padding: 2px 8px;
  border-radius: 6px;
  font-size: 10px;
  font-weight: 600;
  color: var(--text-tertiary);
  background: var(--surface-muted);
  border: 1px solid var(--border-primary);
}

.card-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 0 16px 16px;
}

.card-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 10px 14px;
  min-width: 0;
}

.meta-item {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: var(--text-tertiary);
  white-space: nowrap;

  &.rating {
    color: var(--accent-amber);
  }
}

.use-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
  padding: 7px 12px;
  border-radius: 8px;
  border: 1px solid var(--border-primary);
  background: var(--surface-muted);
  color: var(--text-primary);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  opacity: 0.92;
  transform: translateY(1px);
  transition:
    opacity 0.2s ease,
    transform 0.2s ease,
    border-color 0.2s ease,
    background-color 0.2s ease;

  &:hover {
    background: var(--bg-hover);
    border-color: var(--border-hover);
  }
}

@media (max-width: 768px) {
  .use-btn {
    opacity: 1;
    transform: none;
  }
}
</style>
