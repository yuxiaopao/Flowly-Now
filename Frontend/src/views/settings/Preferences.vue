<template>
  <div class="preferences-settings">
    <PageHeader
      compact
      :title="config.title"
      :subtitle="config.subtitle"
    />
    <section
      class="preference-group"
      aria-labelledby="appearance-title"
    >
      <div class="section-heading">
        <h2 id="appearance-title">
          {{ config.appearance }}
        </h2>
      </div>
      <div class="preference-item preference-item--stacked">
        <div class="preference-info">
          <span class="preference-label">{{ config.theme }}</span><span class="preference-desc">{{ config.themeDescription }}</span>
        </div>
        <ThemeSwitcher variant="pill" />
      </div>
    </section>
    <section
      class="preference-group"
      aria-labelledby="editor-preferences-title"
    >
      <div class="section-heading">
        <h2 id="editor-preferences-title">
          {{ config.editor }}
        </h2><p>{{ config.editorDescription }}</p>
      </div>
      <div
        v-for="item in config.items"
        :key="item.key"
        class="preference-item"
      >
        <div class="preference-info">
          <label
            :id="'preference-' + item.key"
            :for="'preference-control-' + item.key"
            class="preference-label"
          >{{ item.label }}</label><span
            :id="'preference-hint-' + item.key"
            class="preference-desc"
          >{{ item.description }}</span>
        </div>
        <el-switch
          :id="'preference-control-' + item.key"
          v-model="preferences[item.key]"
          :aria-label="item.label"
          :aria-labelledby="'preference-' + item.key"
          :aria-describedby="'preference-hint-' + item.key"
        />
      </div>
    </section>
    <p
      v-if="saveError"
      class="inline-error"
      role="alert"
    >
      {{ saveError }}
    </p>
    <div class="form-footer">
      <span
        class="save-status"
        role="status"
      >{{ isDirty ? config.unsaved : config.savedStatus }}</span>
      <div class="form-actions">
        <AppButton
          variant="ghost"
          @click="resetPreferences"
        >
          {{ config.reset }}
        </AppButton>
        <AppButton
          :disabled="!isDirty"
          @click="savePreferences"
        >
          {{ config.save }}
        </AppButton>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, computed, ref, onMounted, onUnmounted } from 'vue'
import { onBeforeRouteLeave } from 'vue-router'
import { useAppStore } from '@/stores/app'
import { usePreferencesStore } from '@/stores/preferences'
import { PREFERENCE_CONFIG as config, PROFILE_COPY } from '@/config/personalCenter'
import AppButton from '@/components/common/AppButton.vue'
import ThemeSwitcher from '@/components/common/ThemeSwitcher.vue'
import PageHeader from '@/components/layout/PageHeader.vue'

const appStore = useAppStore()
const preferencesStore = usePreferencesStore()
const preferences = reactive({ ...preferencesStore.editor })
const saveError = ref('')
const isDirty = computed(() => Object.keys(config.defaults).some(key => preferences[key] !== preferencesStore.editor[key]))
function savePreferences() {
  saveError.value = ''
  try { preferencesStore.save(preferences); appStore.success(config.saved) }
  catch { saveError.value = config.error }
}
function resetPreferences() {
  appStore.setTheme(config.defaultTheme)
  Object.assign(preferences, config.defaults)
  savePreferences()
}
function beforeUnload(event) {
  if (!isDirty.value) return
  event.preventDefault()
  event.returnValue = ''
}
onBeforeRouteLeave(() => !isDirty.value || appStore.confirm({
  title: PROFILE_COPY.leaveTitle, message: PROFILE_COPY.leaveMessage, confirmText: PROFILE_COPY.leave, cancelText: PROFILE_COPY.stay,
}))
onMounted(() => window.addEventListener('beforeunload', beforeUnload))
onUnmounted(() => window.removeEventListener('beforeunload', beforeUnload))
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;
@use '@/assets/styles/personal-center.scss' as *;
.preference-group + .preference-group { padding-top: $spacing-6; margin-top: $spacing-6; border-top: 1px solid var(--border-primary); }
.preference-item { display: flex; justify-content: space-between; align-items: center; gap: $spacing-4; padding-block: $spacing-4; border-bottom: 1px solid var(--border-primary); &:last-child { border-bottom: none; } }
.preference-info { display: flex; flex-direction: column; gap: $spacing-2; min-width: 0; }
.preference-label { font-size: $font-size-sm; font-weight: $font-weight-medium; color: var(--text-primary); }
.preference-desc { font-size: $font-size-sm; line-height: $line-height-normal; color: var(--text-secondary); }
@media (max-width: $personal-center-form-breakpoint) { .preference-item--stacked { align-items: flex-start; flex-direction: column; } }
</style>
