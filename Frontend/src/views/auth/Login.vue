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
            可视化 AI 工作流平台
          </h1>
          <p class="brand-description">
            轻松创建、部署和管理 AI 工作流。
            支持多种 AI 模型、内置 RAG 能力、
            实时监控和团队协作。
          </p>
          <div class="brand-features">
            <div class="feature-item">
              <div class="feature-icon">
                <Zap />
              </div>
              <div class="feature-text">
                <strong>拖拽式编辑</strong>
                <span>直观的可视化编辑器</span>
              </div>
            </div>
            <div class="feature-item">
              <div class="feature-icon">
                <Bot />
              </div>
              <div class="feature-text">
                <strong>多模型支持</strong>
                <span>OpenAI、Claude 等</span>
              </div>
            </div>
            <div class="feature-item">
              <div class="feature-icon">
                <Shield />
              </div>
              <div class="feature-text">
                <strong>安全可靠</strong>
                <span>企业级安全保障</span>
              </div>
            </div>
          </div>
        </div>
        <div class="brand-decoration">
          <div class="decoration-circle circle-1" />
          <div class="decoration-circle circle-2" />
          <div class="decoration-circle circle-3" />
        </div>
      </div>

      <!-- 右侧登录表单 -->
      <div class="auth-form-wrapper">
        <div class="auth-card">
          <div class="auth-header">
            <h2 class="auth-title">
              欢迎回来
            </h2>
            <p class="auth-subtitle">
              登录到您的账户继续
            </p>
          </div>

          <el-form
            ref="formRef"
            :model="form"
            :rules="rules"
            class="auth-form"
            @submit.prevent="handleLogin"
          >
            <el-form-item prop="username">
              <el-input
                v-model="form.username"
                placeholder="用户名或邮箱"
                size="large"
              >
                <template #prefix>
                  <User class="input-icon" />
                </template>
              </el-input>
            </el-form-item>

            <el-form-item prop="password">
              <el-input
                v-model="form.password"
                type="password"
                placeholder="密码"
                size="large"
                show-password
              >
                <template #prefix>
                  <Lock class="input-icon" />
                </template>
              </el-input>
            </el-form-item>

            <div class="form-options">
              <el-checkbox v-model="form.remember">
                <span class="checkbox-label">记住我</span>
              </el-checkbox>
              <router-link
                to="/forgot-password"
                class="forgot-link"
              >
                忘记密码?
              </router-link>
            </div>

            <el-form-item>
              <button
                type="submit"
                class="submit-button"
                :class="{ loading: authStore.isLoading }"
                :disabled="authStore.isLoading"
              >
                <span v-if="!authStore.isLoading">登录</span>
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
              title="微信登录"
            >
              <svg
                class="social-icon"
                viewBox="0 0 24 24"
                fill="currentColor"
              >
                <path d="M8.691 2.188C3.891 2.188 0 5.476 0 9.53c0 2.212 1.17 4.203 3.002 5.55a.59.59 0 0 1 .213.665l-.39 1.48c-.019.07-.048.141-.048.213 0 .163.13.295.29.295a.326.326 0 0 0 .167-.054l1.903-1.114a.864.864 0 0 1 .717-.098 10.16 10.16 0 0 0 2.837.403c.276 0 .543-.027.811-.05-.857-2.578.157-4.972 1.932-6.446 1.703-1.415 3.882-1.98 5.853-1.838-.576-3.583-4.196-6.348-8.596-6.348zM5.785 5.991c.642 0 1.162.529 1.162 1.18a1.17 1.17 0 0 1-1.162 1.178A1.17 1.17 0 0 1 4.623 7.17c0-.651.52-1.18 1.162-1.18zm5.813 0c.642 0 1.162.529 1.162 1.18a1.17 1.17 0 0 1-1.162 1.178 1.17 1.17 0 0 1-1.162-1.178c0-.651.52-1.18 1.162-1.18zm5.34 2.867c-1.797-.052-3.746.512-5.28 1.786-1.72 1.428-2.687 3.72-1.78 6.22.942 2.453 3.666 4.229 6.884 4.229.826 0 1.622-.12 2.361-.336a.722.722 0 0 1 .598.082l1.584.926a.272.272 0 0 0 .14.047c.134 0 .24-.111.24-.247 0-.06-.023-.12-.038-.177l-.327-1.233a.582.582 0 0 1-.023-.156.49.49 0 0 1 .201-.398C23.024 18.48 24 16.82 24 14.98c0-3.21-2.931-5.837-6.656-6.088V8.89a5.718 5.718 0 0 0-.406-.032zm-.997 2.541c.536 0 .97.44.97.983a.976.976 0 0 1-.97.983.976.976 0 0 1-.97-.983c0-.543.434-.983.97-.983zm4.857 0c.536 0 .97.44.97.983a.976.976 0 0 1-.97.983.976.976 0 0 1-.97-.983c0-.543.434-.983.97-.983z" />
              </svg>
              <span>微信登录</span>
            </button>
            <button
              class="social-button"
              type="button"
              title="QQ登录"
            >
              <svg
                class="social-icon"
                viewBox="0 0 24 24"
                fill="currentColor"
              >
                <path d="M12.003 2c-2.265 0-6.29 1.364-6.29 7.325v1.195S3.55 14.96 3.55 16.218c0 .378.187.665.245.665.057 0 .184-.287.184-.665 0-1.259 2.249-3.568 5.024-3.568s5.023 2.309 5.023 3.568c0 .378.128.665.186.665.057 0 .242-.287.242-.665 0-1.258-2.167-4.522-2.167-7.533V9.325C18.292 3.364 14.27 2 12.003 2zm-.96 6.272c-.53 0-.96-.446-.96-.997s.43-.998.96-.998.96.447.96.998-.43.997-.96.997zm4.06 0c-.53 0-.96-.446-.96-.997s.43-.998.96-.998.96.447.96.998-.43.997-.96.997z" />
              </svg>
              <span>QQ登录</span>
            </button>
          </div>

          <div class="auth-footer">
            <span class="footer-text">还没有账号?</span>
            <router-link
              to="/register"
              class="footer-link"
            >
              立即注册
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
import { ref, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useAppStore } from '@/stores/app'
import ThemeLogo from '@/components/common/ThemeLogo.vue'
import ThemeSwitcher from '@/components/common/ThemeSwitcher.vue'
import {
  User, Lock, ArrowLeft, ArrowRight,
  Zap, Bot, Shield
} from 'lucide-vue-next'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const appStore = useAppStore()

const formRef = ref(null)
const form = reactive({
  username: '',
  password: '',
  remember: false
})

const rules = {
  username: [
    { required: true, message: '请输入用户名或邮箱', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码至少 6 个字符', trigger: 'blur' }
  ]
}

async function handleLogin() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  try {
    await authStore.login({
      username: form.username,
      password: form.password
    })
    appStore.success('登录成功')

    const redirect = route.query.redirect || '/'
    router.push(redirect)
  } catch (err) {
    // 错误已由请求拦截器通过 ElMessage 展示
  }
}
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

// 主题变量（使用 CSS 变量以支持运行时主题切换）
// 注意：不要用 SCSS 变量 $auth-*，它们在编译时就固定了，无法响应主题变化

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

  .brand-features {
    display: flex;
    flex-direction: column;
    gap: $spacing-4;
  }

  .feature-item {
    display: flex;
    align-items: center;
    gap: $spacing-4;
    padding: $spacing-4;
    background: var(--bg-secondary);
    border: 1px solid var(--border-primary);
    border-radius: $radius-xl;
    transition: all $transition-fast;

    &:hover {
      border-color: var(--accent-primary);
      transform: translateX(4px);
    }
  }

  .feature-icon {
    width: 44px;
    height: 44px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--bg-tertiary);
    border-radius: $radius-lg;
    color: var(--accent-primary);

    svg {
      width: 22px;
      height: 22px;
    }
  }

  .feature-text {
    display: flex;
    flex-direction: column;

    strong {
      font-size: $font-size-base;
      font-weight: $font-weight-semibold;
      color: var(--text-primary);
    }

    span {
      font-size: $font-size-sm;
      color: var(--text-primary)-secondary;
    }
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
    top: -100px;
    right: -50px;
    animation: float 8s ease-in-out infinite;
  }

  .circle-2 {
    width: 200px;
    height: 200px;
    bottom: 0;
    right: 50px;
    animation: float 6s ease-in-out infinite reverse;
  }

  .circle-3 {
    width: 100px;
    height: 100px;
    top: 50%;
    left: -30px;
    animation: float 5s ease-in-out infinite;
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
  margin-bottom: $spacing-8;
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
    margin-bottom: $spacing-5;
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
        border-color: var(--accent-primary);
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

.form-options {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: $spacing-6;

  .checkbox-label {
    color: var(--text-primary)-secondary;
  }

  :deep(.el-checkbox) {
    --el-checkbox-checked-bg-color: var(--accent-primary);
    --el-checkbox-checked-input-border-color: var(--accent-primary);
    --el-checkbox-checked-text-color: var(--text-inverse);
  }
}

.forgot-link {
  font-size: $font-size-sm;
  color: var(--text-primary)-secondary;
  text-decoration: none;
  transition: color $transition-fast;

  &:hover {
    color: var(--accent-primary);
  }
}

.submit-button {
  width: 100%;
  height: 48px;
  background: var(--accent-primary);
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
    opacity: 0.7;
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
  border: 1px solid var(--border-secondary);
  border-radius: $radius-lg;
  color: var(--text-primary);
  font-size: $font-size-sm;
  cursor: pointer;
  transition: all $transition-fast;

  &:hover {
    background: var(--bg-hover);
    border-color: var(--accent-primary);
    color: var(--accent-primary);
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  }

  &:active {
    transform: translateY(0);
  }

  .social-icon {
    width: 22px;
    height: 22px;
  }
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
    color: var(--accent-primary);
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
}
</style>
