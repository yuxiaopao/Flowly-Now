<template>
  <div class="hotspots-panel">
    <div class="panel-header">
      <span class="panel-title">
        <Flame class="title-icon" />
        热点文件
      </span>
    </div>

    <div class="hotspots-list">
      <div
        v-for="(hotspot, index) in hotspots"
        :key="hotspot.id"
        class="hotspot-item"
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
      </div>
    </div>
  </div>
</template>

<script setup>
import { useCodeGraphStore } from '@/stores/codeGraph'
import { Flame } from 'lucide-vue-next'

const props = defineProps({
  hotspots: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['select'])

const store = useCodeGraphStore()

function getNodeFromHotspot(hotspot) {
  return store.nodes.find(n => n.id === hotspot.id)
}
</script>

<style lang="scss" scoped>
.hotspots-panel {
  padding: 12px;
  border-top: 1px solid var(--border-color);
}

.panel-header {
  margin-bottom: 12px;
}

.panel-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);

  .title-icon {
    width: 16px;
    height: 16px;
    color: #f97316;
  }
}

.hotspots-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.hotspot-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px;
  background: var(--bg-hover);
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    background: var(--color-primary-light-9);
  }
}

.hotspot-rank {
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  font-size: 11px;
  font-weight: 600;
  background: var(--bg-secondary);
  color: var(--text-secondary);

  &.rank-1 {
    background: #fbbf24;
    color: #000;
  }

  &.rank-2 {
    background: #9ca3af;
    color: #000;
  }

  &.rank-3 {
    background: #d97706;
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
    font-weight: 600;
    color: var(--color-primary);
  }
}
</style>
