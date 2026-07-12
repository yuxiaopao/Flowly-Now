<template>
  <SiteFactoryNodeShell
    :id="id"
    :data="data"
    :selected="selected"
    node-type="project_profiler"
  >
    <template #expanded>
      <div v-if="profile.domain || classSummary.total" class="profile-card">
        <div v-if="classSummary.total" class="class-summary">
          <p><strong>类别分析</strong> 共 {{ classSummary.total }} 类</p>
          <p v-if="classSummary.preview">{{ classSummary.preview }}</p>
          <p v-if="classSummary.metrics"><strong>指标</strong> {{ classSummary.metrics }}</p>
          <p v-if="!classSummary.total && !profile.domain" class="warn-hint">
            等待上游训练节点输出 class_names
          </p>
        </div>
        <p><strong>领域</strong> {{ profile.domain }}</p>
        <p><strong>场景</strong> {{ profile.scenario }}</p>
        <p v-if="profile.ui_tone"><strong>风格</strong> {{ profile.ui_tone }}</p>
        <ul v-if="profile.copy_hints?.length">
          <li v-for="(h, i) in profile.copy_hints" :key="i">{{ h }}</li>
        </ul>
      </div>
    </template>
  </SiteFactoryNodeShell>
</template>

<script setup>
import { computed } from 'vue'
import SiteFactoryNodeShell from './SiteFactoryNodeShell.vue'

const props = defineProps({
  id: { type: String, default: '' },
  data: { type: Object, default: () => ({}) },
  selected: { type: Boolean, default: false },
})

const profile = computed(() => {
  const out = props.data.output || props.data.result || {}
  return out.profile || props.data.profile || {}
})

const classSummary = computed(() => {
  const out = props.data.output || props.data.result || {}
  const names = profile.value.class_names || out.class_names || []
  const metrics = out.metrics || profile.value.metrics || {}
  const parts = []
  if (metrics.map50 != null) parts.push(`mAP50=${metrics.map50}`)
  if (metrics.recall_at_5 != null) parts.push(`R@5=${metrics.recall_at_5}`)
  return {
    total: names.length,
    preview: names.slice(0, 5).join('、') + (names.length > 5 ? '…' : ''),
    metrics: parts.join(', '),
  }
})
</script>

<style scoped lang="scss">
.profile-card {
  font-size: 11px;
  line-height: 1.5;
  color: var(--text-secondary, #a1a1aa);
  p { margin: 0 0 4px; }
  ul { margin: 6px 0 0; padding-left: 16px; }
}
.class-summary {
  margin-bottom: 8px;
  padding-bottom: 8px;
  border-bottom: 1px dashed rgba(255,255,255,0.1);
}
.warn-hint { color: #f59e0b; }
</style>
