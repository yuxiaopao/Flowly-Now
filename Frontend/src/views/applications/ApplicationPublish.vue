<template>
  <div>
    <section class="delivery-publish-section">
      <div class="delivery-section-heading">
        <div>
          <span class="delivery-eyebrow">
            RELEASE
          </span>
          <h2>
            发布版本
          </h2>
          <p>
            将通过测试的当前草稿固定为一个可调用版本。
          </p>
        </div>
        <div class="delivery-actions">
          <button
            v-if="application.activeRelease && application.canPublish"
            type="button"
            class="delivery-button"
            :disabled="Boolean(busy)"
            @click="$emit('unpublish')"
          >
            下线应用
          </button>
          <button
            v-if="application.canPublish"
            type="button"
            class="delivery-button delivery-button--primary"
            :disabled="!ready || Boolean(busy)"
            data-testid="application-publish"
            @click="$emit('publish')"
          >
            {{ busy === 'publish' ? '正在发布…' : '发布新版本' }}
          </button>
        </div>
      </div>
      <p
        v-if="!application.canPublish"
        class="delivery-feedback"
      >
        当前为只读或编辑权限。发布、回滚和密钥管理需要应用所有者或团队管理员。
      </p>
      <p
        v-else-if="!ready"
        class="delivery-hint"
      >
        {{ dirty ? '先保存草稿，再测试当前配置。' : '先成功测试当前草稿。源资源变化后，后台会再次校验测试是否仍有效。' }}
      </p>
      <p
        v-if="application.kind === 'knowledge'"
        class="delivery-hint"
      >
        知识助手固定集合绑定、提示词与检索配置；文档内容实时更新。修改或删除知识源可能影响线上回答。
      </p>
      <p
        v-if="application.evaluationGate?.required"
        class="delivery-feedback"
        :class="{ 'delivery-feedback--error': !application.evaluationGate.ready }"
      >
        {{ application.evaluationGate.ready ? '指定测试集的完整回归已通过。' : application.evaluationGate.reason }}
        <router-link
          class="delivery-link"
          :to="{ query: { tab: 'evaluations', suite: application.requiredEvaluationSuiteId } }"
        >
          查看发布测试集
        </router-link>
      </p>
      <div
        v-if="releases.error.value"
        class="delivery-feedback delivery-feedback--error"
        role="alert"
      >
        {{ releases.error.value }}
        <button
          class="delivery-link"
          type="button"
          @click="releases.load()"
        >
          重试发布记录
        </button>
      </div>
      <p
        v-else-if="releases.loading.value"
        class="delivery-loading"
        role="status"
      >
        正在加载发布记录…
      </p>
      <p
        v-else-if="!releases.rows.value.length"
        class="delivery-empty"
      >
        尚无发布版本。测试成功后发布第一个版本。
      </p>
      <div
        v-else
        class="delivery-table-wrap"
      >
        <table class="delivery-table">
          <thead>
            <tr>
              <th>
                版本
              </th>
              <th>
                状态
              </th>
              <th>
                发布时间
              </th>
              <th>
                配置
              </th>
              <th>
                操作
              </th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="release in releases.rows.value"
              :key="release.id"
              :data-testid="`application-release-${release.version}`"
            >
              <td class="delivery-mono">
                {{ `v${release.version}` }}
                <small v-if="release.testRequestId">
                  <router-link :to="{ path: `/applications/${application.id}`, query: { tab: 'requests', request: release.testRequestId } }">查看测试证据</router-link>
                </small>
                <small v-if="release.evaluationRunId">
                  <router-link :to="{ path: `/applications/${application.id}`, query: { tab: 'evaluations', run: release.evaluationRunId } }">查看回归证据</router-link>
                </small>
              </td>
              <td>
                {{ release.id === application.activeRelease?.id ? '线上版本' : '历史版本' }}
              </td>
              <td>
                {{ applicationDate(release.createdAt) }}
                <small v-if="release.testedAt">验证于 {{ applicationDate(release.testedAt) }}</small>
              </td>
              <td>
                <details>
                  <summary>
                    查看配置快照
                  </summary>
                  <pre
                    class="delivery-code"
                    tabindex="0"
                  >{{ JSON.stringify(release.configuration, null, 2) }}</pre>
                </details>
              </td>
              <td>
                <button
                  v-if="application.canPublish && release.id !== application.activeRelease?.id"
                  type="button"
                  class="delivery-button"
                  :disabled="Boolean(busy)"
                  data-testid="application-rollback"
                  @click="$emit('rollback', release.id)"
                >
                  {{ application.activeRelease ? '回滚到此版本' : '恢复此版本上线' }}
                </button>
                <span
                  v-else
                  class="delivery-hint"
                >
                  {{ release.id === application.activeRelease?.id ? '正在服务' : '仅查看' }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <nav
        v-if="releases.pageCount.value > 1"
        class="delivery-pagination"
        aria-label="发布记录分页"
      >
        <span>
          第
          {{ releases.page.value }}
          /
          {{ releases.pageCount.value }}
          页
        </span>
        <button
          class="delivery-button"
          type="button"
          :disabled="releases.page.value <= 1 || releases.loading.value"
          @click="releases.load(releases.page.value - 1)"
        >
          上一页
        </button>
        <button
          class="delivery-button"
          type="button"
          :disabled="releases.page.value >= releases.pageCount.value || releases.loading.value"
          @click="releases.load(releases.page.value + 1)"
        >
          下一页
        </button>
      </nav>
    </section>
    <section class="delivery-publish-section">
      <div class="delivery-section-heading">
        <div>
          <span class="delivery-eyebrow">
            CONNECT
          </span>
          <h2>
            API 接入
          </h2>
          <p>
            {{ application.activeRelease ? `当前线上版本 v${application.activeRelease.version}。请求使用应用密钥授权。` : '当前未上线。发布版本后，此端点才接受调用。' }}
          </p>
        </div>
        <button
          type="button"
          class="delivery-button"
          @click="copyCurl"
        >
          复制 cURL
        </button>
      </div>
      <p
        v-if="copyFeedback"
        role="status"
        class="delivery-hint"
      >
        {{ copyFeedback }}
      </p>
      <pre
        class="delivery-code"
        tabindex="0"
      >{{ curl }}</pre>
      <p class="delivery-hint">
        将 FLOWLY_APP_KEY 环境变量设为应用密钥。示例不会包含你的登录令牌或密钥明文。
      </p>
    </section>
    <section
      v-if="application.canPublish"
      class="delivery-publish-section"
    >
      <div class="delivery-section-heading">
        <div>
          <span class="delivery-eyebrow">
            ACCESS KEYS
          </span>
          <h2>
            调用密钥
          </h2>
          <p>
            每个接入服务使用独立密钥。密钥仅能调用当前应用。
          </p>
        </div>
      </div>
      <div
        v-if="secret"
        class="delivery-secret"
        role="status"
      >
        <strong>
          请立即保存密钥，明文只显示这一次。
        </strong>
        <code>
          {{ secret }}
        </code>
        <div class="delivery-actions">
          <button
            class="delivery-button"
            type="button"
            @click="copySecret"
          >
            复制密钥
          </button>
          <button
            class="delivery-button"
            type="button"
            @click="$emit('secret', '')"
          >
            已保存，隐藏密钥
          </button>
        </div>
      </div>
      <form
        class="delivery-key-create"
        aria-label="创建调用密钥"
        @submit.prevent="createKey"
      >
        <div class="delivery-field">
          <label for="application-key-name">
            密钥名称
          </label>
          <input
            id="application-key-name"
            v-model="keyName"
            data-testid="application-key-name"
            aria-label="密钥名称"
            :maxlength="APPLICATIONS.keyNameMaxLength"
            :disabled="Boolean(busy)"
            required
            placeholder="例如：网站服务"
          >
        </div>
        <div class="delivery-field">
          <label for="application-key-expiry">
            到期时间（选填）
          </label>
          <input
            id="application-key-expiry"
            v-model="keyExpiry"
            aria-label="密钥到期时间"
            type="datetime-local"
            :disabled="Boolean(busy)"
          >
        </div>
        <button
          data-testid="application-create-key"
          class="delivery-button"
          type="submit"
          :disabled="Boolean(busy) || Boolean(secret)"
        >
          {{ busy === 'key' ? '正在创建…' : '创建密钥' }}
        </button>
      </form>
      <p
        v-if="secret"
        class="delivery-hint"
      >
        保存并隐藏当前密钥后，才能创建下一枚。
      </p>
      <p
        v-if="keyError"
        class="delivery-feedback delivery-feedback--error"
        role="alert"
      >
        {{ keyError }}
      </p>
      <div
        v-if="keys.error.value"
        class="delivery-feedback delivery-feedback--error"
        role="alert"
      >
        {{ keys.error.value }}
        <button
          type="button"
          class="delivery-link"
          @click="keys.load()"
        >
          重试密钥列表
        </button>
      </div>
      <p
        v-else-if="keys.loading.value"
        class="delivery-loading"
        role="status"
      >
        正在加载密钥…
      </p>
      <p
        v-else-if="!keys.rows.value.length"
        class="delivery-empty"
      >
        还没有调用密钥。创建后即可为服务配置 API 接入。
      </p>
      <div
        v-else
        class="delivery-table-wrap"
      >
        <table class="delivery-table">
          <thead>
            <tr>
              <th>
                名称与前缀
              </th>
              <th>
                状态
              </th>
              <th>
                最近使用
              </th>
              <th>
                到期
              </th>
              <th>
                操作
              </th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="key in keys.rows.value"
              :key="key.id"
            >
              <td>
                {{ key.name }}
                <small class="delivery-mono">
                  {{ key.prefix }}
                </small>
              </td>
              <td>
                {{ key.revokedAt ? '已撤销' : key.isActive ? '可用' : '已到期或失效' }}
              </td>
              <td>
                {{ applicationDate(key.lastUsedAt) }}
              </td>
              <td>
                {{ key.expiresAt ? applicationDate(key.expiresAt) : '长期有效' }}
              </td>
              <td>
                <button
                  v-if="key.isActive && !key.revokedAt"
                  class="delivery-button delivery-button--danger"
                  type="button"
                  :disabled="Boolean(busy)"
                  :aria-label="`撤销密钥 ${key.name}`"
                  data-testid="application-revoke-key"
                  @click="revokeKey(key)"
                >
                  撤销密钥
                </button>
                <span
                  v-else
                  class="delivery-hint"
                >
                  已失效
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <nav
        v-if="keys.pageCount.value > 1"
        class="delivery-pagination"
        aria-label="调用密钥分页"
      >
        <span>
          第
          {{ keys.page.value }}
          /
          {{ keys.pageCount.value }}
          页
        </span>
        <button
          type="button"
          class="delivery-button"
          :disabled="keys.page.value <= 1 || keys.loading.value"
          @click="keys.load(keys.page.value - 1)"
        >
          上一页
        </button>
        <button
          type="button"
          class="delivery-button"
          :disabled="keys.page.value >= keys.pageCount.value || keys.loading.value"
          @click="keys.load(keys.page.value + 1)"
        >
          下一页
        </button>
      </nav>
    </section>
  </div>
</template>

<script setup>
import {
  computed,
  onBeforeUnmount,
  ref,
  watch
} from 'vue'
import {
  applicationsApi
} from '@/api/applications'
import {
  APPLICATIONS,
  applicationDate
} from '@/config/applications'
import {
  getPublicApiUrl
} from '@/config'
import {
  useAppStore
} from '@/stores/app'
import {
  useApplicationCollection
} from './useApplicationCollection'

const props = defineProps({
  application: {
    type: Object,
    required: true
  },
  ready: Boolean,
  dirty: Boolean,
  busy: {
    type: String,
    default: ''
  },
  secret: {
    type: String,
    default: ''
  },
  revision: {
    type: Number,
    default: 0
  }
})
const emit = defineEmits(['publish', 'rollback', 'unpublish', 'secret', 'busy'])
const app = useAppStore()
const releases = useApplicationCollection(params => applicationsApi.releases(props.application.id, params))
const keys = useApplicationCollection(params => applicationsApi.keys(props.application.id, params))
const keyName = ref('')
const keyExpiry = ref('')
const keyError = ref('')
const copyFeedback = ref('')
let disposed = false
const endpoint = computed(() => getPublicApiUrl(`/applications/${encodeURIComponent(props.application.id)}/invoke/`))
const curl = computed(() => [
  `curl '${endpoint.value.replace(/'/g, `'"'"'`)}'`,
  '  -H "Authorization: Bearer $FLOWLY_APP_KEY"',
  "  -H 'Content-Type: application/json'",
  `  --data '${JSON.stringify({ input_data: props.application.kind === 'knowledge' ? { query: '你的问题' } : {} })}'`,
].join(' \\\n'))

async function copyText(value, success) {
  try {
    await navigator.clipboard.writeText(value);
    copyFeedback.value = success
  } catch {
    copyFeedback.value = '无法访问剪贴板，请直接选择文本复制。'
  }
}

function copyCurl() {
  return copyText(curl.value, '调用示例已复制。')
}

function copySecret() {
  return copyText(props.secret, '密钥已复制，请保存到安全位置。')
}
async function createKey() {
  if (props.busy || props.secret || !props.application.canPublish) return
  keyError.value = ''
  if (!keyName.value.trim()) {
    keyError.value = '请输入密钥名称。';
    return
  }
  const expiry = keyExpiry.value ? new Date(keyExpiry.value) : null
  if (expiry && (!Number.isFinite(expiry.getTime()) || expiry.getTime() <= Date.now())) {
    keyError.value = '到期时间应晚于当前时间。';
    return
  }
  emit('busy', 'key')
  const id = props.application.id
  try {
    const result = await applicationsApi.createKey(id, {
      name: keyName.value.trim(),
      ...(expiry ? {
        expires_at: expiry.toISOString()
      } : {})
    })
    if (disposed || id !== props.application.id) return
    emit('secret', result.apiKey)
    keyName.value = ''
    keyExpiry.value = ''
    await keys.load(1)
  } catch (failure) {
    if (!disposed) keyError.value = failure.message || '密钥创建失败，请重试。'
  } finally {
    if (!disposed) emit('busy', '')
  }
}
async function revokeKey(key) {
  if (props.busy || !props.application.canPublish) return
  if (!await app.confirm({
      title: `撤销密钥「${key.name}」？`,
      message: '使用此密钥的服务将立即无法调用应用。此操作无法恢复，可重新创建密钥。',
      confirmText: '撤销密钥',
      cancelText: '保留密钥',
      confirmType: 'danger'
    }) || disposed) return
  emit('busy', 'key')
  keyError.value = ''
  try {
    await applicationsApi.revokeKey(props.application.id, key.id);
    if (!disposed) await keys.load(keys.page.value)
  } catch (failure) {
    if (!disposed) keyError.value = failure.message || '撤销失败，请重试。'
  } finally {
    if (!disposed) emit('busy', '')
  }
}
watch(() => [props.application.id, props.revision], () => {
  releases.reset();
  releases.load();
  keys.reset();
  if (props.application.canPublish) keys.load()
}, {
  immediate: true
})
onBeforeUnmount(() => {
  disposed = true
})
</script>

