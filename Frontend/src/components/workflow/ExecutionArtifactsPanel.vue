<template>
  <div
    class="execution-artifacts"
    :class="{ compact, empty: !artifactResult.hasArtifacts }"
  >
    <div
      v-if="showHeader"
      class="artifacts-header"
    >
      <h4 class="artifacts-title">
        执行产物
      </h4>
      <span
        v-if="artifactResult.total"
        class="artifacts-count"
      >{{ artifactResult.total }} 项</span>
    </div>

    <div
      v-if="!artifactResult.hasArtifacts"
      class="artifacts-empty"
    >
      <p>{{ emptyText }}</p>
    </div>

    <div
      v-else
      class="artifacts-body"
    >
      <section
        v-for="group in visibleGroups"
        :key="group.id"
        class="artifact-group"
      >
        <div class="group-header">
          <component
            :is="groupIcon(group.id)"
            class="group-icon"
          />
          <span class="group-label">{{ group.label }}</span>
          <span class="group-count">{{ artifactResult.grouped[group.id]?.length || 0 }}</span>
        </div>

        <div
          class="artifact-grid"
          :class="`grid-${group.id}`"
        >
          <article
            v-for="artifact in artifactResult.grouped[group.id]"
            :key="artifact.id"
            class="artifact-card"
            :class="`type-${artifact.type}`"
          >
            <div class="artifact-meta">
              <span
                v-if="artifact.nodeName"
                class="artifact-node"
              >{{ artifact.nodeName }}</span>
              <span
                v-if="artifact.field"
                class="artifact-field"
              >{{ artifact.field }}</span>
            </div>

            <!-- 图片 -->
            <div
              v-if="artifact.type === 'image'"
              class="artifact-media"
            >
              <img
                :src="artifact.url || artifact.value"
                class="artifact-image"
                alt="生成图片"
                loading="lazy"
                @error="onMediaError"
                @click="openUrl(artifact.url || artifact.value)"
              >
            </div>

            <!-- 视频 -->
            <div
              v-else-if="artifact.type === 'video'"
              class="artifact-media"
            >
              <video
                v-if="isHttpUrl(artifact.url || artifact.value)"
                :src="artifact.url || artifact.value"
                class="artifact-video"
                controls
                preload="metadata"
              />
              <div
                v-else
                class="artifact-fallback"
              >
                {{ artifact.value }}
              </div>
            </div>

            <!-- 音频 -->
            <div
              v-else-if="artifact.type === 'audio'"
              class="artifact-media"
            >
              <audio
                v-if="isHttpUrl(artifact.url || artifact.value)"
                :src="artifact.url || artifact.value"
                class="artifact-audio"
                controls
                preload="metadata"
              />
              <div
                v-else
                class="artifact-fallback"
              >
                {{ artifact.value }}
              </div>
            </div>

            <!-- 提示词 / 文本 / 字幕 / 数据 -->
            <div
              v-else
              class="artifact-text-block"
            >
              <pre class="artifact-text">{{ artifact.value }}</pre>
            </div>

            <div class="artifact-actions">
              <button
                type="button"
                class="action-btn"
                @click="copyValue(artifact.value)"
              >
                <Copy class="icon-sm" />
                复制
              </button>
              <button
                v-if="canOpen(artifact)"
                type="button"
                class="action-btn"
                @click="openUrl(artifact.url || artifact.value)"
              >
                <ExternalLink class="icon-sm" />
                打开
              </button>
            </div>
          </article>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import {
  Copy, ExternalLink, FileText, Image as ImageIcon, Video, Music, Globe, File, Subtitles, Braces,
} from 'lucide-vue-next'
import { useAppStore } from '@/stores/app'
import { extractExecutionArtifacts, ARTIFACT_GROUPS } from '@/utils/executionArtifacts'

const props = defineProps({
  nodeExecutions: { type: Array, default: () => [] },
  outputData: { type: [Object, String, null], default: null },
  nodeStatusMap: { type: Object, default: null },
  execution: { type: Object, default: null },
  nodeNameMap: { type: Object, default: null },
  includeStructuredData: { type: Boolean, default: true },
  compact: { type: Boolean, default: false },
  showHeader: { type: Boolean, default: true },
  emptyText: {
    type: String,
    default: '本次执行暂无可展示产物（图片、视频、提示词、文件路径等）',
  },
})

const appStore = useAppStore()

const artifactResult = computed(() => extractExecutionArtifacts({
  nodeExecutions: props.nodeExecutions,
  outputData: props.outputData,
  nodeStatusMap: props.nodeStatusMap,
  execution: props.execution,
  nodeNameMap: props.nodeNameMap,
  includeStructuredData: props.includeStructuredData,
}))

const visibleGroups = computed(() =>
  ARTIFACT_GROUPS.filter((group) => (artifactResult.value.grouped[group.id] || []).length > 0)
    .sort((a, b) => Number(b.id === 'video') - Number(a.id === 'video'))
)

const groupIconMap = {
  prompt: FileText,
  image: ImageIcon,
  video: Video,
  audio: Music,
  website: Globe,
  file: File,
  subtitle: Subtitles,
  data: Braces,
}

function groupIcon(id) {
  return groupIconMap[id] || Braces
}

function isHttpUrl(value) {
  return typeof value === 'string' && /^https?:\/\//i.test(value.trim())
}

function canOpen(artifact) {
  const target = artifact.url || artifact.value
  return isHttpUrl(target) || (typeof target === 'string' && (target.includes('/') || target.includes('\\')))
}

function copyValue(value) {
  const text = typeof value === 'string' ? value : JSON.stringify(value, null, 2)
  navigator.clipboard.writeText(text).then(() => {
    appStore.success('已复制')
  }).catch(() => {
    appStore.error('复制失败')
  })
}

function openUrl(url) {
  if (!url) return
  if (isHttpUrl(url)) {
    window.open(url, '_blank', 'noopener,noreferrer')
    return
  }
  copyValue(url)
  appStore.info('本地路径已复制到剪贴板')
}

function onMediaError(event) {
  const el = event.target
  if (el) el.style.display = 'none'
}
</script>

<style scoped lang="scss">
.execution-artifacts {
  display: flex;
  flex-direction: column;
  gap: 12px;

  &.compact .artifact-grid {
    grid-template-columns: 1fr;
  }
}

.artifacts-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.artifacts-title {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary, #e5e5e5);
}

.artifacts-count {
  font-size: 11px;
  color: var(--text-tertiary, rgba(255, 255, 255, 0.45));
  background: rgba(255, 255, 255, 0.06);
  border-radius: 999px;
  padding: 2px 8px;
}

.artifacts-empty {
  padding: 20px 16px;
  border: 1px dashed rgba(255, 255, 255, 0.12);
  border-radius: 10px;
  text-align: center;

  p {
    margin: 0;
    font-size: 13px;
    color: var(--text-tertiary, rgba(255, 255, 255, 0.45));
  }
}

.artifacts-body {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.artifact-group {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.group-header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.group-icon {
  width: 14px;
  height: 14px;
  color: #06b6d4;
}

.group-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary, rgba(255, 255, 255, 0.75));
}

.group-count {
  font-size: 10px;
  color: rgba(255, 255, 255, 0.4);
}

.artifact-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 12px;

  &.grid-prompt,
  &.grid-video,
  &.grid-file,
  &.grid-subtitle,
  &.grid-data {
    grid-template-columns: 1fr;
  }
}

.artifact-card {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 10px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.artifact-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  padding: 8px 10px 0;
}

.artifact-node {
  font-size: 10px;
  font-weight: 600;
  color: #67e8f9;
}

.artifact-field {
  font-size: 10px;
  color: rgba(255, 255, 255, 0.35);
  font-family: ui-monospace, monospace;
}

.artifact-media {
  padding: 8px 10px;
}

.artifact-image {
  width: 100%;
  max-height: 220px;
  object-fit: contain;
  border-radius: 8px;
  background: rgba(0, 0, 0, 0.25);
  cursor: zoom-in;
}

.artifact-video {
  width: 100%;
  max-height: 240px;
  border-radius: 8px;
  background: #000;
}

.artifact-audio {
  width: 100%;
}

.artifact-fallback,
.artifact-text-block {
  padding: 8px 10px;
}

.artifact-text {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 12px;
  line-height: 1.55;
  color: var(--text-primary, #e5e5e5);
  max-height: 180px;
  overflow: auto;
  font-family: inherit;
}

.artifact-actions {
  display: flex;
  gap: 6px;
  padding: 8px 10px 10px;
  margin-top: auto;
}

.action-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  border-radius: 6px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.04);
  color: rgba(255, 255, 255, 0.7);
  font-size: 11px;
  cursor: pointer;
  transition: background 0.15s ease;

  &:hover {
    background: rgba(255, 255, 255, 0.08);
    color: #fff;
  }

  .icon-sm {
    width: 12px;
    height: 12px;
  }
}
</style>
