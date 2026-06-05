<template>
  <div class="api-keys-redirect-page">
    <el-result
      icon="info"
      title="API 密钥入口已合并"
      sub-title="为避免凭证体系分裂，API 密钥管理已统一收敛到“凭证管理”页面。当前页面仅保留兼容跳转。"
    >
      <template #extra>
        <div class="actions">
          <el-button
            type="primary"
            @click="goToCredentials"
          >
            前往统一凭证管理
          </el-button>
          <el-button @click="goBack">
            返回上一页
          </el-button>
        </div>
      </template>
    </el-result>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

function goToCredentials() {
  router.replace('/settings/credentials')
}

function goBack() {
  router.back()
}

onMounted(() => {
  goToCredentials()
})
</script>

<style scoped>
.api-keys-redirect-page {
  min-height: 320px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}

.actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  justify-content: center;
}
</style>
