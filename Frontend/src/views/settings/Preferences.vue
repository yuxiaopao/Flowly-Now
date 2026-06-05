<template>
  <div class="preferences-settings">
    <h2 class="section-title">
      偏好设置
    </h2>

    <div class="preference-group">
      <h3 class="group-title">
        外观
      </h3>
      <div class="preference-item preference-item--stacked">
        <div class="preference-info">
          <span class="preference-label">主题</span>
          <span class="preference-desc">选择完整支持的四套界面主题</span>
        </div>
        <div class="theme-switcher-wrap">
          <ThemeSwitcher variant="pill" />
        </div>
      </div>
    </div>

    <el-divider />

    <div class="preference-group">
      <h3 class="group-title">
        编辑器
      </h3>
      <div class="preference-item">
        <div class="preference-info">
          <span class="preference-label">自动保存</span>
          <span class="preference-desc">编辑时自动保存更改</span>
        </div>
        <el-switch v-model="preferences.autoSave" />
      </div>
      <div class="preference-item">
        <div class="preference-info">
          <span class="preference-label">对齐网格</span>
          <span class="preference-desc">拖拽节点时自动对齐网格</span>
        </div>
        <el-switch v-model="preferences.snapToGrid" />
      </div>
      <div class="preference-item">
        <div class="preference-info">
          <span class="preference-label">显示迷你地图</span>
          <span class="preference-desc">在编辑器右下角显示迷你地图</span>
        </div>
        <el-switch v-model="preferences.showMinimap" />
      </div>
    </div>

    <el-divider />

    <div class="preference-group">
      <h3 class="group-title">
        通知
      </h3>
      <div class="preference-item">
        <div class="preference-info">
          <span class="preference-label">执行完成通知</span>
          <span class="preference-desc">工作流执行完成时发送通知</span>
        </div>
        <el-switch v-model="preferences.notifyOnComplete" />
      </div>
      <div class="preference-item">
        <div class="preference-info">
          <span class="preference-label">执行失败通知</span>
          <span class="preference-desc">工作流执行失败时发送通知</span>
        </div>
        <el-switch v-model="preferences.notifyOnError" />
      </div>
    </div>

    <el-divider />

    <div class="preference-actions">
      <AppButton @click="resetPreferences">
        恢复默认
      </AppButton>
      <AppButton
        variant="primary"
        @click="savePreferences"
      >
        保存设置
      </AppButton>
    </div>
  </div>
</template>

<script setup>
import { reactive, onMounted } from 'vue'
import { useAppStore } from '@/stores/app'
import AppButton from '@/components/common/AppButton.vue'
import ThemeSwitcher from '@/components/common/ThemeSwitcher.vue'

const appStore = useAppStore()

const preferences = reactive({
  theme: 'dark',
  autoSave: true,
  snapToGrid: true,
  showMinimap: true,
  notifyOnComplete: true,
  notifyOnError: true
})

onMounted(() => {
  preferences.theme = appStore.theme

  const saved = localStorage.getItem('user_preferences')
  if (saved) {
    try {
      Object.assign(preferences, JSON.parse(saved))
    } catch (e) {
      // Invalid JSON
    }
  }

  preferences.theme = appStore.theme
})

function savePreferences() {
  preferences.theme = appStore.theme
  localStorage.setItem('user_preferences', JSON.stringify(preferences))
  appStore.success('设置已保存')
}

function resetPreferences() {
  appStore.setTheme('dark')
  Object.assign(preferences, {
    theme: 'dark',
    autoSave: true,
    snapToGrid: true,
    showMinimap: true,
    notifyOnComplete: true,
    notifyOnError: true
  })
  savePreferences()
}
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.section-title {
  font-size: $font-size-xl;
  font-weight: $font-weight-semibold;
  color: var(--text-primary);
  margin: 0 0 $spacing-6;
}

.preference-group {
  margin-bottom: $spacing-4;
}

.group-title {
  font-size: $font-size-sm;
  font-weight: $font-weight-medium;
  color: var(--text-secondary);
  margin: 0 0 $spacing-4;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.preference-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: $spacing-4;
  padding: $spacing-4 0;
  border-bottom: 1px solid var(--border-primary);

  &:last-child {
    border-bottom: none;
  }

  &--stacked {
    align-items: flex-start;
  }
}

.preference-info {
  display: flex;
  flex-direction: column;
  gap: $spacing-1;
}

.preference-label {
  font-weight: $font-weight-medium;
  color: var(--text-primary);
}

.preference-desc {
  font-size: $font-size-sm;
  color: var(--text-secondary);
}

.theme-switcher-wrap {
  flex-shrink: 0;
}

.preference-actions {
  display: flex;
  justify-content: flex-end;
  gap: $spacing-3;
  margin-top: $spacing-6;
}
</style>
