<template>
  <div class="reset-password-page">
    <div class="auth-background">
      <div class="bg-gradient" />
      <div class="bg-grid" />
      <div class="bg-glow" />
    </div>

    <div class="reset-password-card">
      <div class="card-header">
        <div class="logo">
          <ThemeLogo
            alt="Flowly"
            class="logo-image"
          />
          <span class="logo-text">Flowly</span>
        </div>
        <h1 class="title">
          设置新密码
        </h1>
        <p class="subtitle">
          为您的账户创建一个新的安全密码
        </p>
      </div>

      <el-alert
        v-if="!validLink || formError"
        :title="formError || '重置链接无效或缺少参数，请重新申请。'"
        type="error"
        :closable="false"
        show-icon
        role="alert"
      />
      <router-link
        v-if="!validLink || formError"
        to="/forgot-password"
        class="link"
      >
        重新申请重置链接
      </router-link>
      <el-form
        v-if="validLink"
        ref="formRef"
        :model="formData"
        :rules="formRules"
        novalidate
        @submit.prevent="handleSubmit"
      >
        <el-form-item
          prop="password"
          label="新密码"
          label-position="top"
        >
          <el-input
            v-model="formData.password"
            type="password"
            aria-label="新密码"
            autocomplete="new-password"
            placeholder="输入新密码"
            size="large"
            show-password
            :prefix-icon="Lock"
          />
        </el-form-item>

        <el-form-item
          prop="confirmPassword"
          label="确认新密码"
          label-position="top"
        >
          <el-input
            v-model="formData.confirmPassword"
            type="password"
            aria-label="确认新密码"
            autocomplete="new-password"
            placeholder="再次确认新密码"
            size="large"
            show-password
            :prefix-icon="Lock"
          />
        </el-form-item>

        <div
          v-if="formData.password"
          class="password-strength"
        >
          <div class="strength-bar">
            <div
              class="strength-fill"
              :style="{ width: passwordStrength.score * 25 + '%' }"
              :class="passwordStrength.level"
            />
          </div>
          <span
            class="strength-text"
            :class="passwordStrength.level"
          >
            {{ passwordStrength.text }}
          </span>
        </div>

        <el-form-item>
          <el-button
            type="primary"
            native-type="submit"
            size="large"
            :loading="submitting"
            class="submit-btn"
          >
            更新密码
          </el-button>
        </el-form-item>
      </el-form>

      <div class="card-footer">
        <p>
          想起密码了？
          <router-link
            to="/login"
            class="link"
          >
            返回登录
          </router-link>
        </p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Lock } from 'lucide-vue-next'
import ThemeLogo from '@/components/common/ThemeLogo.vue'
import { resetPassword } from '@/api/auth'
import { useAppStore } from '@/stores/app'
import { useSiteConfigStore } from '@/stores/siteConfig'
import { clearAuthSession } from '@/utils/authSession'
import { getSettingsError } from '@/utils/personalCenter'
import { AUTH } from '@/config/auth'

const route = useRoute()
const router = useRouter()
const appStore = useAppStore()
const siteConfigStore = useSiteConfigStore()
const minimumLength = computed(() => siteConfigStore.auth.passwordMinLength || AUTH.passwordMinLength)
const resetUid = computed(() => route.query.uid || route.query.uidb64)
const validLink = computed(() => typeof route.query.token === 'string' && !!route.query.token && typeof resetUid.value === 'string' && !!resetUid.value)

const formRef = ref(null)
const submitting = ref(false)
const formError = ref('')
onMounted(() => { if (!siteConfigStore.loaded) siteConfigStore.fetchPublicConfig() })

const formData = reactive({
  password: '',
  confirmPassword: ''
})

const validateConfirmPassword = (rule, value, callback) => {
  if (value !== formData.password) {
    callback(new Error('两次输入的密码不一致'))
  } else {
    callback()
  }
}

const passwordStrength = computed(() => {
  const password = formData.password
  if (!password) return { score: 0, level: '', text: '' }

  let score = 0
  let level = ''
  let text = ''

  if (password.length >= 8) score++
  if (password.length >= 12) score++
  if (/[a-z]/.test(password)) score++
  if (/[A-Z]/.test(password)) score++
  if (/[0-9]/.test(password)) score++
  if (/[^a-zA-Z0-9]/.test(password)) score++

  if (score <= 2) {
    level = 'weak'
    text = '较弱'
  } else if (score <= 4) {
    level = 'medium'
    text = '中等'
  } else {
    level = 'strong'
    text = '较强'
  }

  return { score: Math.min(score, 4), level, text }
})

const formRules = computed(() => ({
  password: [
    { required: true, message: '请输入新密码' },
    { min: minimumLength.value, message: `密码至少需要 ${minimumLength.value} 个字符` }
  ],
  confirmPassword: [
    { required: true, message: '请再次确认密码' },
    { validator: validateConfirmPassword, trigger: 'blur' }
  ]
}))

async function handleSubmit() {
  if (submitting.value || !validLink.value) return
  submitting.value = true
  formError.value = ''
  try {
    const valid = await formRef.value.validate().catch(() => false)
    if (!valid) return
    await resetPassword({
      uid: resetUid.value,
      token: route.query.token,
      password: formData.password
    })
    appStore.success('密码已更新，请重新登录。')
    clearAuthSession()
    await router.replace(AUTH.routes.login)
  } catch (error) {
    formError.value = getSettingsError(error, '重置失败，请检查网络后重试')
  } finally {
    submitting.value = false
  }
}
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.reset-password-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-primary);
  padding: 20px;
  position: relative;
  overflow: hidden;
}

.auth-background {
  position: absolute;
  inset: 0;
  pointer-events: none;

  .bg-gradient {
    position: absolute;
    inset: 0;
    background: radial-gradient(
      ellipse 80% 52% at 50% -15%,
      var(--hero-glow) 0%,
      transparent 58%
    );
  }

  .bg-grid {
    position: absolute;
    inset: 0;
    background-image:
      linear-gradient(var(--hero-grid) 1px, transparent 1px),
      linear-gradient(90deg, var(--hero-grid) 1px, transparent 1px);
    background-size: 56px 56px;
    mask-image: radial-gradient(circle at center, black 30%, transparent 82%);
  }

  .bg-glow {
    position: absolute;
    inset: auto 10% -25% 10%;
    height: 40%;
    background: radial-gradient(circle at center, var(--hero-glow) 0%, transparent 72%);
  }
}

.reset-password-card {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: 440px;
  background: var(--bg-secondary);
  border-radius: 24px;
  padding: 40px;
  border: 1px solid var(--border-primary);
  box-shadow: var(--shadow-xl);
}

.card-header {
  text-align: center;
  margin-bottom: 32px;
}

.logo {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  margin-bottom: 24px;
}

.logo-image {
  width: 32px;
  height: 32px;
}

.logo-text {
  font-size: 24px;
  font-weight: 700;
  color: var(--text-primary);
}

.title {
  font-size: 24px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 8px 0;
}

.subtitle {
  color: var(--text-secondary);
  margin: 0;
  font-size: 15px;
}

:deep(.el-form-item) {
  margin-bottom: 20px;
}

:deep(.el-input__wrapper) {
  padding: 12px 16px;
  border-radius: 12px;
}

.password-strength {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
  padding: 0 4px;
}

.strength-bar {
  flex: 1;
  height: 4px;
  background: var(--toast-progress-track);
  border-radius: 999px;
  overflow: hidden;
}

.strength-fill {
  height: 100%;
  transition: width 0.3s, background-color 0.3s;
}

.strength-fill.weak {
  background: var(--error);
}

.strength-fill.medium {
  background: var(--warning);
}

.strength-fill.strong {
  background: var(--success);
}

.strength-text {
  font-size: 12px;
  font-weight: 600;
  min-width: 48px;
}

.strength-text.weak {
  color: var(--error);
}

.strength-text.medium {
  color: var(--warning);
}

.strength-text.strong {
  color: var(--success);
}

.submit-btn {
  width: 100%;
  height: 48px;
  border-radius: 12px;
  font-size: 16px;
  font-weight: 600;
}

.card-footer {
  text-align: center;
  margin-top: 24px;
  color: var(--text-secondary);
  font-size: 14px;
}

.card-footer .link {
  color: var(--text-primary);
  font-weight: 600;
  text-decoration: none;
}

.card-footer .link:hover {
  text-decoration: underline;
}
</style>
