<template>
  <div class="cycles-warning">
    <div class="warning-header">
      <el-icon class="warning-icon">
        <Warning />
      </el-icon>
      <span class="warning-title">循环依赖警告</span>
    </div>

    <div class="cycles-content">
      <div class="cycles-summary">
        检测到 <strong>{{ cycles.length }}</strong> 处循环依赖
      </div>
      <div class="cycles-hint">
        树形 / 层次布局会自动忽略回边，仍可正常使用
      </div>

      <div class="cycles-list">
        <div
          v-for="(cycle, index) in displayedCycles"
          :key="index"
          class="cycle-item"
        >
          <div class="cycle-path">
            <span
              v-for="(nodeId, i) in cycle.nodes"
              :key="i"
              class="cycle-node"
            >
              <button
                type="button"
                class="node-name"
                @click="$emit('select', getNode(nodeId))"
              >
                {{ getNodeName(nodeId) }}
              </button>
              <span
                v-if="i < cycle.nodes.length - 1"
                class="node-arrow"
              >→</span>
            </span>
          </div>
        </div>
      </div>

      <el-button
        v-if="cycles.length > displayedLimit"
        text
        size="small"
        @click="showAll = !showAll"
      >
        {{ showAll ? '收起' : `查看全部 (${cycles.length})` }}
      </el-button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { normalizeCycles } from '@/utils/codeGraph'
import { CODE_GRAPH } from '@/config/codeGraph'
import { useCodeGraphStore } from '@/stores/codeGraph'
import { Warning } from '@element-plus/icons-vue'

const props = defineProps({
  cycles: {
    type: Array,
    default: () => [],
  },
})

defineEmits(['select'])

const store = useCodeGraphStore()
const showAll = ref(false)
const displayedLimit = CODE_GRAPH.cyclePreviewLimit

const displayedCycles = computed(() => {
  const cycles = normalizeCycles(props.cycles)
  return showAll.value ? cycles : cycles.slice(0, displayedLimit)
})
watch(() => props.cycles, () => { showAll.value = false })

function getNode(nodeId) {
  return store.relationships.byId.get(nodeId)
}

function getNodeName(nodeId) {
  const node = store.relationships.byId.get(nodeId)
  return node ? node.name : nodeId
}
</script>

<style lang="scss" scoped>
.cycles-warning {
  padding: 12px 14px 14px;
}

.warning-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;

  .warning-icon {
    color: #fb7185;
    font-size: 18px;
  }

  .warning-title {
    font-size: 13px;
    font-weight: 600;
    color: #fecdd3;
  }
}

.cycles-content {
  .cycles-summary {
    font-size: 12px;
    color: #fda4af;
    margin-bottom: 6px;

    strong {
      color: #fb7185;
    }
  }

  .cycles-hint {
    font-size: 11px;
    color: var(--text-tertiary);
    margin-bottom: 12px;
    line-height: 1.4;
  }
}

.cycles-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 8px;
}

.cycle-item {
  padding: 8px 10px;
  background: rgba(251, 113, 133, 0.08);
  border: 1px solid rgba(251, 113, 133, 0.22);
  border-radius: 10px;
}

.cycle-path {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px;
}

.cycle-node {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.node-name {
  font-size: 11px;
  color: #ffe4e6;
  background: rgba(251, 113, 133, 0.18);
  border: 1px solid rgba(251, 113, 133, 0.3);
  padding: 2px 6px;
  border-radius: 6px;
  cursor: pointer;
  font: inherit;

  &:hover {
    background: rgba(251, 113, 133, 0.32);
  }
}

.node-arrow {
  font-size: 10px;
  color: #fb7185;
}
</style>
