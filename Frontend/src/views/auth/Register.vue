<template>
  <div class="auth-page">
    <!-- 背景装饰 -->
    <div class="auth-background">
      <div class="bg-gradient" />
      <div class="bg-grid" />
      <div class="bg-glow" />
    </div>

    <!-- 返回按钮 -->
    <router-link
      to="/"
      class="back-button"
    >
      <ArrowLeft />
      <span>返回首页</span>
    </router-link>

    <div class="auth-container">
      <!-- 左侧品牌展示 -->
      <div class="auth-branding">
        <div class="brand-content">
          <div class="brand-logo">
            <ThemeLogo alt="Flowly" />
            <span class="brand-name">Flowly</span>
          </div>
          <h1 class="brand-title">
            开启 AI 工作流之旅
          </h1>
          <p class="brand-description">
            加入 Flowly，创建您的第一个 AI 工作流。
            无论是自动化任务、智能客服还是数据分析，
            Flowly 都能帮您轻松实现。
          </p>
          <div class="brand-stats">
            <div class="stat-item">
              <span class="stat-value">10K+</span>
              <span class="stat-label">活跃用户</span>
            </div>
            <div class="stat-item">
              <span class="stat-value">50K+</span>
              <span class="stat-label">工作流创建</span>
            </div>
            <div class="stat-item">
              <span class="stat-value">99.9%</span>
              <span class="stat-label">服务可用性</span>
            </div>
          </div>
        </div>
        <div class="brand-decoration">
          <div class="decoration-circle circle-1" />
          <div class="decoration-circle circle-2" />
        </div>
      </div>

      <!-- 右侧注册表单 -->
      <div class="auth-form-wrapper">
        <div class="auth-card">
          <div class="auth-header">
            <h2 class="auth-title">
              创建账号
            </h2>
            <p class="auth-subtitle">
              填写以下信息开始使用
            </p>
          </div>

          <el-form
            ref="formRef"
            :model="form"
            :rules="rules"
            class="auth-form"
            @submit.prevent="handleRegister"
          >
            <el-form-item prop="username">
              <el-input
                v-model="form.username"
                placeholder="用户名"
                size="large"
              >
                <template #prefix>
                  <User class="input-icon" />
                </template>
              </el-input>
            </el-form-item>

            <el-form-item prop="email">
              <el-input
                v-model="form.email"
                type="email"
                placeholder="邮箱地址"
                size="large"
              >
                <template #prefix>
                  <Mail class="input-icon" />
                </template>
              </el-input>
            </el-form-item>

            <el-form-item prop="password">
              <el-input
                v-model="form.password"
                type="password"
                placeholder="密码 (至少 8 位)"
                size="large"
                show-password
              >
                <template #prefix>
                  <Lock class="input-icon" />
                </template>
              </el-input>
            </el-form-item>

            <el-form-item prop="password_confirm">
              <el-input
                v-model="form.password_confirm"
                type="password"
                placeholder="确认密码"
                size="large"
                show-password
              >
                <template #prefix>
                  <Key class="input-icon" />
                </template>
              </el-input>
            </el-form-item>

            <div class="form-terms">
              <el-checkbox v-model="form.agreeTerms">
                <span class="terms-text">
                  我已阅读并同意
                  <a
                    href="#"
                    class="terms-link"
                  >服务条款</a>
                  和
                  <a
                    href="#"
                    class="terms-link"
                  >隐私政策</a>
                </span>
              </el-checkbox>
            </div>

            <el-form-item>
              <button
                type="submit"
                class="submit-button"
                :class="{ loading: authStore.isLoading }"
                :disabled="authStore.isLoading || !form.agreeTerms"
              >
                <span v-if="!authStore.isLoading">创建账号</span>
                <span
                  v-else
                  class="loading-dots"
                >
                  <span /><span /><span />
                </span>
              </button>
            </el-form-item>
          </el-form>

          <div class="auth-divider">
            <span>或</span>
          </div>

          <div class="social-login">
            <button
              class="social-button"
              type="button"
            >
              <svg
                class="social-icon"
                viewBox="0 0 24 24"
              >
                <path d="M12.545,10.239v3.821h5.445c-0.712,2.315-2.647,3.972-5.445,3.972c-3.332,0-6.033-2.701-6.033-6.032s2.701-6.032,6.033-6.032c1.498,0,2.866,0.549,3.921,1.453l2.814-2.814C17.503,2.988,15.139,2,12.545,2C7.021,2,2.543,6.477,2.543,12s4.478,10,10.002,10c3.197,0,5.983-1.216,8.006-3.274h-3.461z" />
              </svg>
              <span>使用 Google 注册</span>
            </button>
          </div>

          <div class="auth-footer">
            <span class="footer-text">已有账号?</span>
            <router-link
              to="/login"
              class="footer-link"
            >
              立即登录
              <ArrowRight class="arrow-icon" />
            </router-link>
          </div>
        </div>

        <!-- 主题切换 -->
        <ThemeSwitcher variant="pill" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useAppStore } from '@/stores/app'
import ThemeLogo from '@/components/common/ThemeLogo.vue'
import ThemeSwitcher from '@/components/common/ThemeSwitcher.vue'
import {
  User, Mail, Lock, Key, ArrowLeft, ArrowRight
} from 'lucide-vue-next'

const router = useRouter()
const authStore = useAuthStore()
const appStore = useAppStore()

const formRef = ref(null)
const form = reactive({
  username: '',
  email: '',
  password: '',
  password_confirm: '',
  agreeTerms: false
})

const validatePasswordConfirm = (rule, value, callback) => {
  if (value !== form.password) {
    callback(new Error('两次输入的密码不一致'))
  } else {
    callback()
  }
}

const rules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 20, message: '用户名 3-20 个字符', trigger: 'blur' }
  ],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入有效的邮箱地址', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 8, message: '密码至少 8 个字符', trigger: 'blur' }
  ],
  password_confirm: [
    { required: true, message: '请确认密码', trigger: 'blur' },
    { validator: validatePasswordConfirm, trigger: 'blur' }
  ]
}

async function handleRegister() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  try {
    await authStore.register({
      username: form.username,
      email: form.email,
      password: form.password,
      password_confirm: form.password_confirm
    })
    appStore.success('注册成功，请登录')
    router.push('/login')
  } catch (err) {
    // 错误已由请求拦截器通过 ElMessage 展示
  }
}
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

// 主题变量（使用 CSS 变量以支持运行时主题切换）
  // 使用 CSS 变量实现主题支持

.auth-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: var(--bg-primary);
  position: relative;
  overflow: hidden;
}

// 背景装饰
.auth-background {
  position: absolute;
  inset: 0;
  pointer-events: none;

  .bg-gradient {
    position: absolute;
    inset: 0;
    background: radial-gradient(
      ellipse 80% 50% at 50% -20%,
      var(--hero-glow) 0%,
      transparent 50%
    );
  }

  .bg-grid {
    position: absolute;
    inset: 0;
    background-image:
      linear-gradient(var(--hero-grid) 1px, transparent 1px),
      linear-gradient(90deg, var(--hero-grid) 1px, transparent 1px);
    background-size: 60px 60px;
  }

  .bg-glow {
    position: absolute;
    top: -50%;
    left: 50%;
    transform: translateX(-50%);
    width: 100%;
    height: 100%;
    background: radial-gradient(
      circle,
      var(--hero-glow) 0%,
      transparent 70%
    );
  }
}

// 返回按钮
.back-button {
  position: absolute;
  top: $spacing-6;
  left: $spacing-6;
  display: flex;
  align-items: center;
  gap: $spacing-2;
  padding: $spacing-2 $spacing-4;
  color: var(--text-primary)-secondary;
  text-decoration: none;
  font-size: $font-size-sm;
  border-radius: $radius-lg;
  transition: all $transition-fast;
  z-index: 10;

  &:hover {
    color: var(--text-primary);
    background-color: var(--bg-hover);
  }

  svg {
    width: 18px;
    height: 18px;
  }
}

// 容器
.auth-container {
  display: flex;
  width: 100%;
  max-width: 1100px;
  margin: 0 auto;
  padding: $spacing-6;
  gap: $spacing-12;
  position: relative;
  z-index: 1;
}

// 左侧品牌区
.auth-branding {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  position: relative;

  .brand-content {
    position: relative;
    z-index: 1;
  }

  .brand-logo {
    display: flex;
    align-items: center;
    gap: $spacing-3;
    margin-bottom: $spacing-8;

    img {
      width: 48px;
      height: 48px;
    }

    .brand-name {
      font-size: $font-size-3xl;
      font-weight: $font-weight-bold;
      color: var(--text-primary);
      letter-spacing: -0.02em;
    }
  }

  .brand-title {
    font-size: $font-size-4xl;
    font-weight: $font-weight-bold;
    color: var(--text-primary);
    margin: 0 0 $spacing-4;
    line-height: $line-height-tight;
    letter-spacing: -0.02em;
  }

  .brand-description {
    font-size: $font-size-lg;
    color: var(--text-primary)-secondary;
    margin: 0 0 $spacing-8;
    line-height: $line-height-relaxed;
    max-width: 400px;
  }

  .brand-stats {
    display: flex;
    gap: $spacing-8;
  }

  .stat-item {
    display: flex;
    flex-direction: column;
  }

  .stat-value {
    font-size: $font-size-2xl;
    font-weight: $font-weight-bold;
    color: var(--color-primary);
    letter-spacing: -0.02em;
  }

  .stat-label {
    font-size: $font-size-sm;
    color: var(--text-primary)-secondary;
  }
}

// 装饰圆
.brand-decoration {
  position: absolute;
  inset: 0;
  pointer-events: none;
  overflow: hidden;

  .decoration-circle {
    position: absolute;
    border-radius: 50%;
    border: 1px solid var(--decorative-line);
  }

  .circle-1 {
    width: 300px;
    height: 300px;
    bottom: -100px;
    right: -50px;
    animation: float 8s ease-in-out infinite;
  }

  .circle-2 {
    width: 150px;
    height: 150px;
    top: 20%;
    left: -50px;
    animation: float 6s ease-in-out infinite reverse;
  }
}

@keyframes float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-20px); }
}

// 右侧表单区
.auth-form-wrapper {
  flex: 1;
  max-width: 440px;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.auth-card {
  width: 100%;
  background: var(--bg-secondary);
  border: 1px solid var(--border-primary);
  border-radius: $radius-2xl;
  padding: $spacing-8;
  animation: slideUp 0.5s ease;
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.auth-header {
  text-align: center;
  margin-bottom: $spacing-6;
}

.auth-title {
  font-size: $font-size-2xl;
  font-weight: $font-weight-bold;
  color: var(--text-primary);
  margin: 0 0 $spacing-2;
}

.auth-subtitle {
  font-size: $font-size-sm;
  color: var(--text-primary)-secondary;
  margin: 0;
}

.auth-form {
  :deep(.el-form-item) {
    margin-bottom: $spacing-4;
  }

  :deep(.el-input) {
    --el-input-height: 48px;

    .el-input__wrapper {
      padding: 0 $spacing-4;
      background-color: var(--bg-tertiary);
      border: 1px solid var(--border-primary);
      border-radius: $radius-lg;
      transition: all $transition-fast;

      &:hover {
        border-color: var(--text-primary)-secondary;
      }

      &.is-focus {
        border-color: var(--color-primary);
      }
    }

    .el-input__inner {
      height: 46px;
      color: var(--text-primary);

      &::placeholder {
        color: var(--text-primary)-secondary;
      }
    }
  }
}

.input-icon {
  width: 18px;
  height: 18px;
  color: var(--text-primary)-secondary;
}

.form-terms {
  margin-bottom: $spacing-6;

  :deep(.el-checkbox) {
    align-items: flex-start;
  }

  .terms-text {
    font-size: $font-size-sm;
    color: var(--text-primary)-secondary;
    line-height: 1.5;
  }

  .terms-link {
    color: var(--color-primary);
    text-decoration: none;

    &:hover {
      text-decoration: underline;
    }
  }

  :deep(.el-checkbox__input.is-checked .el-checkbox__inner) {
    background-color: var(--color-primary);
    border-color: var(--color-primary);
  }

  :deep(.el-checkbox__input.is-checked + .el-checkbox__label) {
    color: inherit;
  }
}

.submit-button {
  width: 100%;
  height: 48px;
  background: var(--color-primary);
  color: var(--text-inverse);
  border: none;
  border-radius: $radius-lg;
  font-size: $font-size-base;
  font-weight: $font-weight-semibold;
  cursor: pointer;
  transition: all $transition-fast;
  display: flex;
  align-items: center;
  justify-content: center;

  &:hover:not(:disabled) {
    transform: translateY(-2px);
    box-shadow: var(--shadow-md);
  }

  &:active:not(:disabled) {
    transform: translateY(0);
  }

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  &.loading {
    pointer-events: none;
  }
}

.loading-dots {
  display: flex;
  gap: 4px;

  span {
    width: 8px;
    height: 8px;
    background: var(--text-inverse);
    border-radius: 50%;
    animation: bounce 1.4s ease-in-out infinite both;

    &:nth-child(1) { animation-delay: -0.32s; }
    &:nth-child(2) { animation-delay: -0.16s; }
    &:nth-child(3) { animation-delay: 0s; }
  }
}

@keyframes bounce {
  0%, 80%, 100% { transform: scale(0); }
  40% { transform: scale(1); }
}

.auth-divider {
  display: flex;
  align-items: center;
  margin: $spacing-6 0;

  &::before,
  &::after {
    content: '';
    flex: 1;
    height: 1px;
    background: var(--border-primary);
  }

  span {
    padding: 0 $spacing-4;
    font-size: $font-size-sm;
    color: var(--text-primary)-secondary;
  }
}

.social-login {
  display: flex;
  flex-direction: column;
  gap: $spacing-3;
}

.social-button {
  width: 100%;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: $spacing-3;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-primary);
  border-radius: $radius-lg;
  color: var(--text-primary);
  font-size: $font-size-sm;
  cursor: pointer;
  transition: all $transition-fast;

  &:hover {
    background: var(--bg-hover);
    border-color: var(--text-primary)-secondary;
  }
}

.social-icon {
  width: 20px;
  height: 20px;
  fill: currentColor;
}

.auth-footer {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: $spacing-2;
  margin-top: $spacing-6;
  font-size: $font-size-sm;
  color: var(--text-primary)-secondary;

  .footer-link {
    display: flex;
    align-items: center;
    gap: $spacing-1;
    color: var(--color-primary);
    text-decoration: none;
    font-weight: $font-weight-medium;
    transition: all $transition-fast;

    &:hover {
      gap: $spacing-2;
    }

    .arrow-icon {
      width: 16px;
      height: 16px;
    }
  }
}

// 响应式
@media (max-width: 1024px) {
  .auth-container {
    flex-direction: column;
    align-items: center;
    gap: $spacing-8;
  }

  .auth-branding {
    display: none;
  }

  .auth-form-wrapper {
    max-width: 100%;
  }
}

@media (max-width: 480px) {
  .auth-container {
    padding: $spacing-4;
  }

  .auth-card {
    padding: $spacing-6;
  }

  .back-button {
    top: $spacing-4;
    left: $spacing-4;

    span {
      display: none;
    }
  }

  .brand-stats {
    flex-direction: column;
    gap: $spacing-4;
  }
}
</style>
