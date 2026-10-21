<template>
  <div class="hotspots-panel">
    <div class="panel-header">
      <span class="panel-title">
        <Flame class="title-icon" />
        热点文件
      </span>
    </div>

    <div class="hotspots-list">
      <button
        v-for="(hotspot, index) in hotspots"
        :key="hotspot.id"
        class="hotspot-item"
        type="button"
        :title="hotspot.path"
        @click="$emit('select', getNodeFromHotspot(hotspot))"
      >
        <span
          class="hotspot-rank"
          :class="`rank-${index + 1}`"
        >{{ index + 1 }}</span>
        <div class="hotspot-info">
          <span class="hotspot-name">{{ hotspot.name }}</span>
          <span class="hotspot-path">{{ hotspot.path }}</span>
        </div>
        <div class="hotspot-score">
          <span class="score-value">{{ (hotspot.score * 100).toFixed(0) }}%</span>
        </div>
      </button>
    </div>
  </div>
</template>

<script setup>
import { useCodeGraphStore } from '@/stores/codeGraph'
import { Flame } from 'lucide-vue-next'

defineProps({
  hotspots: {
    type: Array,
    default: () => []
  }
})

defineEmits(['select'])

const store = useCodeGraphStore()

function getNodeFromHotspot(hotspot) {
  return store.nodes.find(n => n.id === hotspot.id || n.path === hotspot.path)
    || { ...hotspot, name: hotspot.name, path: hotspot.path }
}
</script>

<style lang="scss" scoped>
.hotspots-panel {
  padding: 12px 14px 14px;
}

.panel-header {
  margin-bottom: 12px;
}

.panel-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);

  .title-icon {
    width: 16px;
    height: 16px;
    color: #fb923c;
  }
}

.hotspots-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.hotspot-item {
  width: 100%;
  text-align: left;
  font: inherit;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 10px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.25s cubic-bezier(0.22, 1, 0.36, 1);

  &:hover,
  &:focus-visible {
    background: var(--bg-hover);
    border-color: var(--border-secondary);
  }
}

.hotspot-rank {
  width: 22px;
  height: 22px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  font-size: 11px;
  font-weight: 700;
  background: rgba(255, 255, 255, 0.06);
  color: var(--text-secondary);

  &.rank-1 {
    background: #fbbf24;
    color: #111;
  }

  &.rank-2 {
    background: #94a3b8;
    color: #111;
  }

  &.rank-3 {
    background: #ea580c;
    color: #fff;
  }
}

.hotspot-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;

  .hotspot-name {
    font-size: 12px;
    font-weight: 500;
    color: var(--text-primary);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .hotspot-path {
    font-size: 10px;
    color: var(--text-secondary);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
}

.hotspot-score {
  .score-value {
    font-size: 12px;
    font-weight: 700;
    color: #fb923c;
  }
}
</style>
