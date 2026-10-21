<template>
  <div class="forgot-password-page">
    <div class="auth-background">
      <div class="bg-gradient" />
      <div class="bg-grid" />
      <div class="bg-glow" />
    </div>

    <div class="forgot-password-card">
      <div class="card-header">
        <router-link
          to="/login"
          class="back-link"
        >
          <ArrowLeft class="back-icon" />
          返回登录
        </router-link>
        <h1 class="title">
          重置密码
        </h1>
        <p class="subtitle">
          输入您的邮箱，我们会发送一封重置链接邮件
        </p>
      </div>

      <el-form
        ref="formRef"
        :model="formData"
        :rules="formRules"
        novalidate
        @submit.prevent="handleSubmit"
      >
        <el-alert
          v-if="resultMessage"
          :title="resultMessage"
          type="success"
          :closable="false"
          show-icon
          role="status"
        />
        <el-alert
          v-if="formError"
          :title="formError"
          type="error"
          :closable="false"
          show-icon
          role="alert"
        />
        <el-form-item
          prop="email"
          label="注册邮箱"
          label-position="top"
        >
          <el-input
            v-model.trim="formData.email"
            type="email"
            autocomplete="email"
            aria-label="注册邮箱"
            placeholder="请输入邮箱地址"
            size="large"
            :prefix-icon="Mail"
          />
        </el-form-item>

        <el-form-item>
          <el-button
            type="primary"
            native-type="submit"
            size="large"
            :loading="submitting"
            class="submit-btn"
          >
            发送重置链接
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
import { ref, reactive } from 'vue'
import { ArrowLeft, Mail } from 'lucide-vue-next'
import { sendResetEmail } from '@/api/auth'
import { getSettingsError } from '@/utils/personalCenter'

const formRef = ref(null)
const submitting = ref(false)
const formError = ref('')
const resultMessage = ref('')

const formData = reactive({
  email: ''
})

const formRules = {
  email: [
    { required: true, message: '请输入邮箱地址' },
    { type: 'email', message: '请输入有效的邮箱地址' }
  ]
}

async function handleSubmit() {
  if (submitting.value) return
  submitting.value = true
  formError.value = ''
  resultMessage.value = ''
  try {
    const valid = await formRef.value.validate().catch(() => false)
    if (!valid) return
    const response = await sendResetEmail(formData.email)
    resultMessage.value = response.message
  } catch (error) {
    formError.value = getSettingsError(error, '发送失败，请检查网络后重试')
  } finally {
    submitting.value = false
  }
}
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.forgot-password-page {
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

.forgot-password-card {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: 440px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-primary);
  border-radius: 24px;
  padding: 40px;
  box-shadow: var(--shadow-xl);
}

.card-header {
  text-align: center;
  margin-bottom: 32px;
}

.back-link {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--text-secondary);
  text-decoration: none;
  font-size: 14px;
  margin-bottom: 24px;
  transition: color 0.2s, background-color 0.2s;
  padding: 8px 12px;
  border-radius: 999px;
}

.back-link:hover {
  color: var(--text-primary);
  background: var(--surface-muted);
}

.back-icon {
  width: 16px;
  height: 16px;
}

.title {
  font-size: 28px;
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
