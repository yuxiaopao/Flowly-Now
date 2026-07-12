<template>
  <div class="not-found">
    <div class="not-found-content">
      <h1 class="not-found-code">
        404
      </h1>
      <p class="not-found-message">
        页面不存在
      </p>
      <p class="not-found-description">
        您访问的页面可能已被删除或暂时不可用
      </p>
      <div class="not-found-actions">
        <router-link to="/">
          <AppButton variant="primary">
            返回首页
          </AppButton>
        </router-link>
        <router-link to="/workflows">
          <AppButton>浏览工作流</AppButton>
        </router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import AppButton from '@/components/common/AppButton.vue'
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.not-found {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: calc(100vh - #{$header-height} - #{$spacing-12});
}

.not-found-content {
  text-align: center;
}

.not-found-code {
  font-size: 120px;
  font-weight: $font-weight-bold;
  color: $color-primary;
  margin: 0;
  line-height: 1;
}

.not-found-message {
  font-size: $font-size-2xl;
  font-weight: $font-weight-semibold;
  color: var(--text-primary);
  margin: $spacing-4 0 $spacing-2;
}

.not-found-description {
  font-size: $font-size-base;
  color: var(--text-secondary);
  margin: 0 0 $spacing-8;
}

.not-found-actions {
  display: flex;
  gap: $spacing-4;
  justify-content: center;
}
</style>

