<template>
  <div class="join-page">
    <div class="join-card">
      <div
        v-if="status === 'loading'"
        class="join-state"
      >
        <el-icon class="spin-icon">
          <Loader2 />
        </el-icon>
        <h2>正在处理邀请…</h2>
        <p>请稍候，正在为您加入团队</p>
      </div>

      <div
        v-else-if="status === 'success'"
        class="join-state"
      >
        <CheckCircle2 class="state-icon success" />
        <h2>加入成功</h2>
        <p>您已成功加入团队「{{ joinedTenantName }}」</p>
        <el-button
          type="primary"
          @click="goToTeam"
        >
          前往团队页面
        </el-button>
      </div>

      <div
        v-else
        class="join-state"
      >
        <XCircle class="state-icon error" />
        <h2>无法加入团队</h2>
        <p>{{ errorMessage }}</p>
        <el-button @click="goToTeam">
          返回团队列表
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useTenantStore } from '@/stores/tenant'
import { Loader2, CheckCircle2, XCircle } from 'lucide-vue-next'

const route = useRoute()
const router = useRouter()
const tenantStore = useTenantStore()

const status = ref('loading')
const errorMessage = ref('')
const joinedTenantName = ref('')

function goToTeam() {
  router.replace('/team')
}

onMounted(async () => {
  const token = String(route.query.token || '')
  if (!token) {
    status.value = 'error'
    errorMessage.value = '邀请链接缺少 token 参数，请确认链接完整。'
    return
  }

  try {
    const response = await tenantStore.joinTenant(token)
    joinedTenantName.value = response?.tenant?.name || response?.membership?.tenant_name || ''
    status.value = 'success'
  } catch (err) {
    status.value = 'error'
    errorMessage.value = err?.response?.data?.error || err?.message || '邀请无效或已过期'
  }
})
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.join-page {
  min-height: calc(100vh - 60px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: $spacing-6;
}

.join-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-primary);
  border-radius: $radius-xl;
  padding: $spacing-12 $spacing-8;
  max-width: 420px;
  width: 100%;
  text-align: center;
}

.join-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: $spacing-3;

  h2 {
    margin: 0;
    font-size: $font-size-xl;
    font-weight: $font-weight-semibold;
  }

  p {
    margin: 0 0 $spacing-2;
    color: var(--text-secondary);
  }
}

.spin-icon {
  font-size: 40px;
  color: $color-primary;
  animation: join-spin 1s linear infinite;
}

.state-icon {
  width: 48px;
  height: 48px;

  &.success {
    color: $color-success;
  }

  &.error {
    color: $color-error;
  }
}

@keyframes join-spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
