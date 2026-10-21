<template>
  <PageShell width="wide">
    <PageHeader
      title="我的网站"
      subtitle="查看 Site Factory 生成的识别站点，预览、部署与下载"
    >
      <template #actions>
        <el-button
          type="primary"
          @click="router.push('/nl-create')"
        >
          语创生成新站点
        </el-button>
        <el-button
          :loading="loading"
          @click="loadSites"
        >
          刷新
        </el-button>
      </template>
    </PageHeader>

    <PageToolbar>
      <el-select
        v-model="statusFilter"
        placeholder="状态"
        clearable
        class="filter-control"
        @change="loadSites"
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
          label="生成中"
          value="generating"
        />
        <el-option
          label="失败"
          value="failed"
        />
      </el-select>
    </PageToolbar>

    <el-skeleton
      v-if="loading"
      :rows="5"
      animated
    />

    <el-empty
      v-else-if="!sites.length"
      description="暂无生成的网站，可通过语创或 YOLO 工作流生成"
    />

    <div
      v-else
      class="site-grid"
    >
      <div
        v-for="site in sites"
        :key="site.id"
        class="site-card hover-lift"
        @click="openSite(site)"
      >
        <div class="site-card__head">
          <Globe :size="22" />
          <el-tag
            :type="statusType(site.status)"
            size="small"
          >
            {{ site.statusDisplay || site.status }}
          </el-tag>
        </div>
        <h3>{{ site.name }}</h3>
        <p class="desc">
          {{ site.description || 'YOLO 识别站点' }}
        </p>
        <div class="meta">
          <span>{{ site.websiteTypeDisplay || site.websiteType || 'detection' }}</span>
          <span>{{ formatDate(site.completedAt || site.completed_at || site.createdAt || site.created_at) }}</span>
        </div>
        <div
          v-if="site.classNames?.length || site.class_names?.length"
          class="tags"
        >
          <el-tag
            v-for="cls in (site.classNames || site.class_names || []).slice(0, 4)"
            :key="cls"
            size="small"
            type="info"
          >
            {{ cls }}
          </el-tag>
        </div>
        <div class="actions">
          <el-button
            size="small"
            type="primary"
            :disabled="site.status !== 'completed'"
            @click.stop="openSite(site)"
          >
            查看详情
          </el-button>
          <el-button
            v-if="site.lastPreviewUrl || site.last_preview_url"
            size="small"
            @click.stop="openPreview(site)"
          >
            预览
          </el-button>
        </div>
      </div>
    </div>
  </PageShell>
</template>

<script setup>
import PageToolbar from '@/components/layout/PageToolbar.vue'
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Globe } from 'lucide-vue-next'
import PageShell from '@/components/layout/PageShell.vue'
import PageHeader from '@/components/layout/PageHeader.vue'
import { websiteGeneratorApi } from '@/api/websiteGenerator'

const router = useRouter()
const loading = ref(false)
const sites = ref([])
const statusFilter = ref('')

function formatDate(value) {
  if (!value) return '—'
  return new Date(value).toLocaleString('zh-CN')
}

function statusType(status) {
  if (status === 'completed') return 'success'
  if (status === 'failed') return 'danger'
  if (status === 'generating') return 'warning'
  return 'info'
}

function normalizeList(res) {
  if (Array.isArray(res)) return res
  return res?.results || res?.data || []
}

async function loadSites() {
  loading.value = true
  try {
    const params = {}
    if (statusFilter.value) params.status = statusFilter.value
    const res = await websiteGeneratorApi.list(params)
    sites.value = normalizeList(res)
  } catch {
    sites.value = []
  } finally {
    loading.value = false
  }
}

function openSite(site) {
  router.push(`/projects/${site.id}`)
}

function openPreview(site) {
  const url = site.lastPreviewUrl || site.last_preview_url
  if (url) window.open(url, '_blank', 'noopener')
}

onMounted(loadSites)
</script>

<style lang="scss" scoped>

.site-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(min(100%, var(--content-card-min-width)), 1fr));
  gap: 1rem;
}

.site-card {
  border: 1px solid var(--border-primary);
  border-radius: var(--content-card-radius);
  padding: var(--content-card-padding);
  background: var(--card-bg);
  cursor: pointer;

  &__head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 0.75rem;
    color: var(--text-secondary);
  }

  h3 {
    margin: 0 0 0.35rem;
    font-size: 1.05rem;
  }

  .desc {
    margin: 0 0 0.75rem;
    color: var(--text-secondary);
    font-size: 0.9rem;
    line-height: 1.45;
    min-height: 2.6em;
  }

  .meta {
    display: flex;
    justify-content: space-between;
    font-size: 0.8rem;
    color: var(--text-tertiary);
    margin-bottom: 0.75rem;
  }

  .tags {
    display: flex;
    flex-wrap: wrap;
    gap: 0.35rem;
    margin-bottom: 0.75rem;
  }

  .actions {
    display: flex;
    gap: 0.5rem;
  }
}
</style>
