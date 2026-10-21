<template>
  <PageShell width="wide">
    <PageHeader
      title="我的权重"
      subtitle="管理 YOLO 训练权重，供工作流复用，避免重复训练"
    >
      <template #actions>
        <el-button
          :loading="loading"
          @click="loadWeights"
        >
          刷新
        </el-button>
      </template>
    </PageHeader>

    <el-alert
      type="info"
      :closable="false"
      show-icon
      class="hint"
      title="工作流 YOLO 训练节点可配置「复用已有权重」，语创生成时也会自动匹配同类权重。"
    />

    <PageToolbar>
      <el-select
        v-model="statusFilter"
        placeholder="状态"
        clearable
        class="filter-control"
        @change="loadWeights"
      >
        <el-option
          label="全部"
          value=""
        />
        <el-option
          label="已完成"
          value="completed"
        />
        <el-option
          label="训练中"
          value="running"
        />
        <el-option
          label="排队中"
          value="queued"
        />
        <el-option
          label="失败"
          value="failed"
        />
      </el-select>
    </PageToolbar>

    <el-skeleton
      v-if="loading"
      :rows="6"
      animated
    />

    <el-empty
      v-else-if="!weights.length"
      description="暂无训练权重，请先运行 YOLO 训练工作流"
    />

    <el-table
      v-else
      :data="weights"
      stripe
      style="width: 100%"
      @row-click="openDetail"
    >
      <el-table-column
        prop="name"
        label="名称"
        min-width="180"
      />
      <el-table-column
        label="模型"
        width="120"
      >
        <template #default="{ row }">
          YOLO{{ row.yoloVersion || row.yolo_version }}{{ row.modelVariant || row.model_variant }}
        </template>
      </el-table-column>
      <el-table-column
        label="类别"
        min-width="160"
      >
        <template #default="{ row }">
          <span class="class-tags">
            {{ (row.classNames || row.class_names || []).join(', ') || '—' }}
          </span>
        </template>
      </el-table-column>
      <el-table-column
        label="mAP50"
        width="90"
      >
        <template #default="{ row }">
          {{ formatMetric(row, 'mAP50') }}
        </template>
      </el-table-column>
      <el-table-column
        label="Precision"
        width="90"
      >
        <template #default="{ row }">
          {{ formatMetric(row, 'precision') }}
        </template>
      </el-table-column>
      <el-table-column
        label="Recall"
        width="90"
      >
        <template #default="{ row }">
          {{ formatMetric(row, 'recall') }}
        </template>
      </el-table-column>
      <el-table-column
        label="状态"
        width="100"
      >
        <template #default="{ row }">
          <el-tag
            :type="statusType(row.status)"
            size="small"
          >
            {{ row.statusDisplay || row.status }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column
        label="完成时间"
        width="170"
      >
        <template #default="{ row }">
          {{ formatDate(row.completedAt || row.completed_at) }}
        </template>
      </el-table-column>
      <el-table-column
        label="操作"
        width="200"
        fixed="right"
      >
        <template #default="{ row }">
          <el-button
            link
            type="primary"
            @click.stop="openDetail(row)"
          >
            详情
          </el-button>
          <el-button
            link
            :disabled="row.status !== 'completed'"
            @click.stop="copyWeightId(row)"
          >
            复制 ID
          </el-button>
          <el-button
            link
            :disabled="row.status !== 'completed'"
            @click.stop="generateSite(row)"
          >
            生成网站
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-drawer
      v-model="drawerOpen"
      :title="selected?.name || '权重详情'"
      size="520px"
    >
      <template v-if="selected">
        <div class="detail-grid">
          <div><span class="label">ID</span><code>{{ selected.id }}</code></div>
          <div><span class="label">权重路径</span><code class="mono">{{ selected.bestWeightPath || selected.best_weight_path || '—' }}</code></div>
          <div><span class="label">Epochs</span>{{ selected.currentEpoch || selected.current_epoch || 0 }} / {{ selected.totalEpochs || selected.total_epochs || '—' }}</div>
          <div><span class="label">Best fitness</span>{{ selected.bestFitness ?? selected.best_fitness ?? '—' }}</div>
          <div><span class="label">工作流</span>{{ selected.workflowName || selected.workflow_name || '—' }}</div>
        </div>

        <h4>评估指标</h4>
        <div class="metrics-grid">
          <div
            v-for="item in metricCards"
            :key="item.key"
            class="metric-card"
          >
            <span class="metric-label">{{ item.label }}</span>
            <span class="metric-value">{{ item.value }}</span>
          </div>
        </div>

        <h4 v-if="historyRows.length">
          训练曲线（末 10 轮）
        </h4>
        <el-table
          v-if="historyRows.length"
          :data="historyRows"
          size="small"
          max-height="240"
        >
          <el-table-column
            prop="epoch"
            label="Epoch"
            width="70"
          />
          <el-table-column
            prop="map50"
            label="mAP50"
          />
          <el-table-column
            prop="loss"
            label="Loss"
          />
        </el-table>
      </template>
    </el-drawer>
  </PageShell>
</template>

<script setup>
import PageToolbar from '@/components/layout/PageToolbar.vue'
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import PageShell from '@/components/layout/PageShell.vue'
import PageHeader from '@/components/layout/PageHeader.vue'
import trainingApi from '@/api/training'
import { websiteGeneratorApi } from '@/api/websiteGenerator'

const router = useRouter()
const loading = ref(false)
const weights = ref([])
const statusFilter = ref('completed')
const drawerOpen = ref(false)
const selected = ref(null)
const detailLoading = ref(false)

function normalizeList(res) {
  if (Array.isArray(res)) return res
  return res?.results || res?.data || []
}

function formatDate(value) {
  if (!value) return '—'
  return new Date(value).toLocaleString('zh-CN')
}

function statusType(status) {
  if (status === 'completed') return 'success'
  if (status === 'failed') return 'danger'
  if (status === 'running') return 'warning'
  return 'info'
}

function formatMetric(row, key) {
  const summary = row.metricsSummary || row.metrics_summary || {}
  const metrics = row.metrics || {}
  const val = summary[key] ?? metrics[key]
  if (val == null || val === '') return '—'
  const num = Number(val)
  return Number.isFinite(num) ? num.toFixed(3) : val
}

const metricCards = computed(() => {
  if (!selected.value) return []
  const s = selected.value.metricsSummary || selected.value.metrics_summary || {}
  const m = selected.value.metrics || {}
  const pick = (k) => s[k] ?? m[k]
  return [
    { key: 'mAP50', label: 'mAP50', value: pick('mAP50') ?? '—' },
    { key: 'mAP50-95', label: 'mAP50-95', value: pick('mAP50-95') ?? pick('map50_95') ?? '—' },
    { key: 'precision', label: 'Precision', value: pick('precision') ?? '—' },
    { key: 'recall', label: 'Recall', value: pick('recall') ?? '—' },
  ]
})

const historyRows = computed(() => {
  const hist = selected.value?.map50History || selected.value?.map50_history || []
  const loss = selected.value?.lossBoxHistory || selected.value?.loss_box_history || []
  if (!Array.isArray(hist) || !hist.length) return []
  return hist.slice(-10).map((map50, idx) => ({
    epoch: hist.length - 10 + idx + 1,
    map50: typeof map50 === 'number' ? map50.toFixed(4) : map50,
    loss: loss[Math.max(0, loss.length - 10 + idx)] ?? '—',
  }))
})

async function loadWeights() {
  loading.value = true
  try {
    const params = {}
    if (statusFilter.value) params.status = statusFilter.value
    const res = await trainingApi.listYoloRuns(params)
    weights.value = normalizeList(res)
  } catch {
    weights.value = []
  } finally {
    loading.value = false
  }
}

async function openDetail(row) {
  drawerOpen.value = true
  detailLoading.value = true
  try {
    selected.value = await trainingApi.getYoloRun(row.id)
  } catch {
    selected.value = row
  } finally {
    detailLoading.value = false
  }
}

function copyWeightId(row) {
  navigator.clipboard?.writeText(String(row.id))
  ElMessage.success('已复制训练任务 ID，可在 YOLO 节点配置 reuseTrainingJobId')
}

async function generateSite(row) {
  try {
    const site = await websiteGeneratorApi.generateFromTraining(row.id, row.name)
    ElMessage.success('已开始生成网站')
    if (site?.id) router.push(`/projects/${site.id}`)
    window.dispatchEvent(new CustomEvent('flowly:assets-updated'))
  } catch (err) {
    ElMessage.error(err?.message || '生成网站失败')
  }
}

onMounted(loadWeights)
</script>

<style lang="scss" scoped>
.hint {
  margin-bottom: 1rem;
}

.class-tags {
  font-size: 0.85rem;
  color: var(--text-secondary);
}

.detail-grid {
  display: grid;
  gap: 0.75rem;
  margin-bottom: 1.25rem;

  .label {
    display: block;
    font-size: 0.75rem;
    color: var(--text-tertiary);
    margin-bottom: 0.15rem;
  }

  code.mono {
    word-break: break-all;
    font-size: 0.78rem;
  }
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 0.75rem;
  margin-bottom: 1rem;
}

.metric-card {
  border: 1px solid var(--border-color, rgba(255, 255, 255, 0.08));
  border-radius: 8px;
  padding: 0.75rem;

  .metric-label {
    display: block;
    font-size: 0.75rem;
    color: var(--text-tertiary);
  }

  .metric-value {
    font-size: 1.1rem;
    font-weight: 600;
  }
}
</style>
