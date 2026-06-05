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
              <span class="node-name">{{ getNodeName(nodeId) }}</span>
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
import { ref, computed } from 'vue'
import { useCodeGraphStore } from '@/stores/codeGraph'
import { Warning } from '@element-plus/icons-vue'

const props = defineProps({
  cycles: {
    type: Array,
    default: () => []
  }
})

const store = useCodeGraphStore()
const showAll = ref(false)
const displayedLimit = 3

const displayedCycles = computed(() => {
  return showAll.value ? props.cycles : props.cycles.slice(0, displayedLimit)
})

function getNodeName(nodeId) {
  const node = store.nodes.find(n => n.id === nodeId)
  return node ? node.name : nodeId
}
</script>

<style lang="scss" scoped>
.cycles-warning {
  margin: 12px;
  padding: 12px;
  background: #fef3c7;
  border: 1px solid #fbbf24;
  border-radius: 8px;
}

.warning-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;

  .warning-icon {
    color: #f59e0b;
    font-size: 18px;
  }

  .warning-title {
    font-size: 13px;
    font-weight: 600;
    color: #92400e;
  }
}

.cycles-content {
  .cycles-summary {
    font-size: 12px;
    color: #78350f;
    margin-bottom: 12px;

    strong {
      color: #dc2626;
    }
  }
}

.cycles-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 8px;
}

.cycle-item {
  padding: 8px;
  background: rgba(255, 255, 255, 0.6);
  border-radius: 6px;
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
  color: #78350f;
  background: #fde68a;
  padding: 2px 6px;
  border-radius: 4px;
}

.node-arrow {
  font-size: 10px;
  color: #92400e;
}
</style>
