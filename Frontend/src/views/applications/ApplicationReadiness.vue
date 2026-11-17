<template>
  <section
    class="application-readiness"
    aria-labelledby="application-readiness-title"
    data-testid="application-readiness"
  >
    <div class="delivery-section-heading">
      <div>
        <h2 id="application-readiness-title">
          {{ COPY.title }}
        </h2>
        <p>{{ COPY.notice }}</p>
      </div>
      <button
        class="delivery-button"
        :disabled="loading"
        @click="load"
      >
        {{ loading ? '检查中…' : '重新检查' }}
      </button>
    </div>
    <p
      v-if="dirty"
      class="delivery-feedback"
    >
      本地配置有未保存修改，以下检查仍针对服务端已保存的配置。
    </p>
    <p
      v-if="error"
      class="delivery-feedback delivery-feedback--error"
      role="alert"
    >
      {{ error }}
    </p>
    <p
      v-else-if="loading"
      class="delivery-loading"
      role="status"
    >
      正在检查资源、索引与配置…
    </p>
    <template v-else-if="evidence">
      <label class="delivery-field">
        <span>检查目标</span>
        <select
          v-model="target"
          aria-label="运行前检查目标"
        >
          <option
            v-for="(label, key) in COPY.targets"
            :key="key"
            :value="key"
            :disabled="!evidence[key]"
          >{{ label }}</option>
        </select>
      </label>
      <template v-if="selected">
        <p
          v-if="selected.source"
          class="delivery-hint"
        >
          绑定资源：{{ selected.source.name }}
        </p>
        <p
          class="delivery-hint"
          role="status"
        >
          {{ selected.configuration_ready ? '本地配置检查通过；请继续运行真实测试。' : '存在阻塞项，请先处理再测试。' }}
        </p>
        <ul class="readiness-checks">
          <li
            v-for="check in selected.checks"
            :key="check.code"
            :data-check-status="check.status"
          >
            <span
              class="delivery-state"
              :data-status="check.status === 'blocked' ? 'failed' : check.status === 'pass' ? 'completed' : 'running'"
            >{{ COPY.statuses[check.status] || check.status }}</span>
            <div><strong>{{ check.label }}</strong><p>{{ check.detail }}</p></div>
            <router-link
              v-if="check.repair_path"
              class="delivery-link"
              :to="check.repair_path"
            >
              查看资源
            </router-link>
          </li>
        </ul>
        <dl
          v-if="selected.chat"
          class="delivery-facts"
        >
          <div><dt>回答模型</dt><dd>{{ selected.chat.model }}</dd></div>
          <div><dt>配置来源</dt><dd>平台回答服务</dd></div>
          <div><dt>连接验证</dt><dd>尚未实际调用</dd></div>
        </dl>
        <p
          v-if="selected.inputs.length"
          class="delivery-hint"
        >
          流程输入：<span
            v-for="field in selected.inputs"
            :key="field.name"
          ><code>{{ field.name }}</code>{{ field.required ? '（必填）' : '（可选）' }} </span>
        </p>
        <p class="delivery-hint">
          检查时间：{{ applicationDate(selected.checked_at) }}{{ selected.knowledge_content_policy === 'live' ? '；知识内容实时更新，发布版本不冻结整份语料。' : '' }}
        </p>
      </template>
    </template>
  </section>
</template>

<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { applicationsApi } from '@/api/applications'
import { applicationDate } from '@/config/applications'
import { APPLICATION_READINESS as COPY } from '@/config/applicationReadiness'
const props = defineProps({ applicationId: { type: String, required: true }, revision: { type: Number, default: 0 }, dirty: Boolean })
const evidence = ref(null)
const loading = ref(false)
const error = ref('')
const target = ref('draft')
const selected = computed(() => evidence.value?.[target.value])
let generation = 0
async function load() {
  const current = ++generation
  loading.value = true; error.value = ''; evidence.value = null
  try {
    const result = await applicationsApi.readiness(props.applicationId)
    if (!result?.draft || !Array.isArray(result.draft.checks) || !Array.isArray(result.draft.inputs)) throw new Error(COPY.failed)
    if (result.active_release && (!Array.isArray(result.active_release.checks) || !Array.isArray(result.active_release.inputs))) throw new Error(COPY.failed)
    if (current === generation) { evidence.value = result; if (!result[target.value]) target.value = 'draft' }
  } catch (failure) { if (current === generation) error.value = failure.message || COPY.failed }
  finally { if (current === generation) loading.value = false }
}
watch(() => [props.applicationId, props.revision], load, { immediate: true })
onBeforeUnmount(() => { generation++ })
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;
.application-readiness { margin-block: $spacing-8; border-top: 1px solid var(--delivery-border); padding-top: $spacing-6; }
.readiness-checks { list-style: none; padding: 0; margin-block: $spacing-4; li { display: flex; gap: $spacing-4; align-items: baseline; padding-block: $spacing-3; border-bottom: 1px solid var(--delivery-border); > div { min-width: 0; flex: 1; } p { color: var(--text-secondary); margin-top: $spacing-1; overflow-wrap: anywhere; } strong { font-weight: $font-weight-medium; } } }
@media (max-width: 640px) { .readiness-checks li { flex-wrap: wrap; > div { flex-basis: 65%; } } }
</style>
