<template>
  <div class="auth-portal">
    <router-link
      to="/"
      class="auth-portal__back"
    >
      <ArrowLeft />
      <span>返回首页</span>
    </router-link>

    <!-- 左侧 70%：3D 机器人 + 项目介绍 -->
    <aside class="auth-portal__hero">
      <div class="auth-portal__hero-bg">
        <div class="bg-gradient" />
        <div class="bg-grid" />
      </div>
      <AuthSplineRobot interactive />
      <AuthRobotSpeechBubble
        :text="robotReply"
        :loading="chatLoading"
      />
      <div class="auth-portal__intro">
        <div class="intro-logo">
          <ThemeLogo alt="Flowly" />
          <span class="intro-logo__name">Flowly</span>
        </div>
        <h1 class="intro-title">
          可视化 AI 工作流平台
        </h1>
        <p class="intro-description">
          轻松创建、部署和管理 AI 工作流。支持多种 AI 模型、内置 RAG 能力、实时监控和团队协作。
        </p>
        <ul class="intro-features">
          <li class="intro-feature intro-feature--amber">
            <Zap />
            <span>拖拽式可视化编辑</span>
          </li>
          <li class="intro-feature intro-feature--blue">
            <Bot />
            <span>多模型与 Agent 编排</span>
          </li>
          <li class="intro-feature intro-feature--emerald">
            <Shield />
            <span>企业级安全与权限</span>
          </li>
        </ul>
      </div>
    </aside>

    <!-- 右侧 30%：登录 / 注册切换 -->
    <section class="auth-portal__panel">
      <div class="auth-portal__panel-inner">
        <div
          class="auth-tabs"
          role="tablist"
        >
          <button
            type="button"
            role="tab"
            class="auth-tab"
            :class="{ 'auth-tab--active': activeTab === 'login' }"
            :aria-selected="activeTab === 'login'"
            @click="switchTab('login')"
          >
            登录
          </button>
          <button
            v-if="allowRegistration"
            type="button"
            role="tab"
            class="auth-tab"
            :class="{ 'auth-tab--active': activeTab === 'register' }"
            :aria-selected="activeTab === 'register'"
            @click="switchTab('register')"
          >
            注册
          </button>
        </div>

        <!-- 登录 -->
        <div
          v-show="activeTab === 'login'"
          class="auth-form-block"
        >
          <div class="auth-form-header">
            <h2>欢迎回来</h2>
            <p>登录到您的账户继续</p>
          </div>

          <el-form
            ref="loginFormRef"
            :model="loginForm"
            :rules="loginRules"
            class="auth-form"
            @submit.prevent="handleLogin"
          >
            <el-form-item prop="username">
              <el-input
                v-model="loginForm.username"
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
                v-model="loginForm.password"
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
              <el-checkbox v-model="loginForm.remember">
                <span class="checkbox-label">记住我</span>
              </el-checkbox>
              <router-link
                to="/forgot-password"
                class="link-muted"
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
                ><span /><span /><span /></span>
              </button>
            </el-form-item>
          </el-form>
        </div>

        <!-- 注册 -->
        <div
          v-show="activeTab === 'register' && allowRegistration"
          class="auth-form-block"
        >
          <div class="auth-form-header">
            <h2>创建账号</h2>
            <p>填写以下信息开始使用</p>
          </div>

          <el-form
            ref="registerFormRef"
            :model="registerForm"
            :rules="registerRules"
            class="auth-form"
            @submit.prevent="handleRegister"
          >
            <el-form-item prop="username">
              <el-input
                v-model="registerForm.username"
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
                v-model="registerForm.email"
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
                v-model="registerForm.password"
                type="password"
                :placeholder="`密码 (至少 ${minPasswordLength} 位)`"
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
                v-model="registerForm.password_confirm"
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
              <el-checkbox v-model="registerForm.agreeTerms">
                <span class="terms-text">
                  我已阅读并同意
                  <a
                    href="#"
                    class="terms-link"
                    @click.prevent
                  >服务条款</a>
                  和
                  <a
                    href="#"
                    class="terms-link"
                    @click.prevent
                  >隐私政策</a>
                </span>
              </el-checkbox>
            </div>

            <el-form-item>
              <button
                type="submit"
                class="submit-button"
                :class="{ loading: authStore.isLoading }"
                :disabled="authStore.isLoading || !registerForm.agreeTerms"
              >
                <span v-if="!authStore.isLoading">创建账号</span>
                <span
                  v-else
                  class="loading-dots"
                ><span /><span /><span /></span>
              </button>
            </el-form-item>
          </el-form>
        </div>

        <div class="auth-portal__chat">
          <AuthRobotChatBox
            :loading="chatLoading"
            @send="handleRobotChat"
          />
        </div>

        <ThemeSwitcher
          variant="pill"
          class="auth-portal__theme"
        />
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useAppStore } from '@/stores/app'
import { useSiteConfigStore } from '@/stores/siteConfig'
import ThemeLogo from '@/components/common/ThemeLogo.vue'
import ThemeSwitcher from '@/components/common/ThemeSwitcher.vue'
import AuthSplineRobot from '@/components/auth/AuthSplineRobot.vue'
import AuthRobotSpeechBubble from '@/components/auth/AuthRobotSpeechBubble.vue'
import AuthRobotChatBox from '@/components/auth/AuthRobotChatBox.vue'
import { sendAuthAssistantMessage } from '@/api/public'
import { APP_CONFIG } from '@/config'
import {
  User, Mail, Lock, Key, ArrowLeft, Zap, Bot, Shield
} from 'lucide-vue-next'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const appStore = useAppStore()
const siteConfigStore = useSiteConfigStore()

const activeTab = ref('login')
const loginFormRef = ref(null)
const registerFormRef = ref(null)

const robotReply = ref(APP_CONFIG.auth.assistantWelcome)
const chatLoading = ref(false)
const chatHistory = ref([])

const MAX_CHAT_HISTORY = 10

const loginForm = reactive({
  username: '',
  password: '',
  remember: false,
})

const registerForm = reactive({
  username: '',
  email: '',
  password: '',
  password_confirm: '',
  agreeTerms: false,
})

const termsDoc = computed(() => siteConfigStore.terms.terms)
const privacyDoc = computed(() => siteConfigStore.terms.privacy)
const minPasswordLength = computed(() => siteConfigStore.auth.passwordMinLength || 8)
const allowRegistration = computed(() => siteConfigStore.auth.allowRegistration !== false)

const loginRules = {
  username: [
    { required: true, message: '请输入用户名或邮箱', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码至少 6 个字符', trigger: 'blur' },
  ],
}

const validatePasswordConfirm = (_rule, value, callback) => {
  if (value !== registerForm.password) {
    callback(new Error('两次输入的密码不一致'))
  } else {
    callback()
  }
}

const registerRules = computed(() => ({
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 20, message: '用户名 3-20 个字符', trigger: 'blur' },
  ],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入有效的邮箱地址', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: minPasswordLength.value, message: `密码至少 ${minPasswordLength.value} 个字符`, trigger: 'blur' },
  ],
  password_confirm: [
    { required: true, message: '请确认密码', trigger: 'blur' },
    { validator: validatePasswordConfirm, trigger: 'blur' },
  ],
}))

function syncTabFromRoute() {
  const tab = route.query.tab
  if (tab === 'register' && allowRegistration.value) {
    activeTab.value = 'register'
    return
  }
  activeTab.value = 'login'
}

function switchTab(tab) {
  if (tab === 'register' && !allowRegistration.value) return
  activeTab.value = tab
  const query = { ...route.query }
  if (tab === 'register') {
    query.tab = 'register'
  } else {
    delete query.tab
    delete query.registered
  }
  router.replace({ path: '/login', query })
}

async function handleLogin() {
  const valid = await loginFormRef.value?.validate().catch(() => false)
  if (!valid) return

  try {
    await authStore.login({
      username: loginForm.username,
      password: loginForm.password,
    })
    appStore.success('登录成功')
    const redirect = route.query.redirect || '/'
    router.push(typeof redirect === 'string' ? redirect : '/')
  } catch {
    // 错误已由请求拦截器展示
  }
}

async function handleRegister() {
  const valid = await registerFormRef.value?.validate().catch(() => false)
  if (!valid) return

  try {
    await authStore.register({
      username: registerForm.username,
      email: registerForm.email,
      password: registerForm.password,
      password_confirm: registerForm.password_confirm,
      agree_terms: registerForm.agreeTerms,
      terms_version: termsDoc.value?.version || '',
      privacy_version: privacyDoc.value?.version || '',
    })
    appStore.success('注册成功，请登录')
    switchTab('login')
  } catch {
    // 错误已由请求拦截器展示
  }
}

async function handleRobotChat(message) {
  if (chatLoading.value || !message.trim()) return

  chatLoading.value = true
  chatHistory.value.push({ role: 'user', content: message })

  try {
    const response = await sendAuthAssistantMessage({
      message,
      history: chatHistory.value.slice(0, -1).slice(-MAX_CHAT_HISTORY),
    })
    const reply = response?.reply || '抱歉，我暂时无法回答，请稍后再试。'
    robotReply.value = reply
    chatHistory.value.push({ role: 'assistant', content: reply })
    if (chatHistory.value.length > MAX_CHAT_HISTORY * 2) {
      chatHistory.value = chatHistory.value.slice(-MAX_CHAT_HISTORY * 2)
    }
  } catch (err) {
    const fallback = '网络不太稳定，请稍后再试。你也可以直接在右侧完成登录或注册。'
    robotReply.value = fallback
    chatHistory.value.push({ role: 'assistant', content: fallback })
    if (!err?.response) {
      appStore.error(fallback)
    }
  } finally {
    chatLoading.value = false
  }
}

onMounted(async () => {
  if (!siteConfigStore.loaded) {
    await siteConfigStore.fetchPublicConfig()
  }
  syncTabFromRoute()
  if (route.query.registered === '1') {
    appStore.success('注册成功，请登录')
    const query = { ...route.query }
    delete query.registered
    router.replace({ path: '/login', query })
  }
})

watch(
  () => [route.query.tab, allowRegistration.value],
  () => syncTabFromRoute(),
)
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.auth-portal {
  display: flex;
  min-height: 100vh;
  width: 100%;
  background: var(--bg-primary);
  position: relative;
  overflow: hidden;
}

.auth-portal__back {
  position: absolute;
  top: $spacing-6;
  left: $spacing-6;
  z-index: 20;
  display: flex;
  align-items: center;
  gap: $spacing-2;
  padding: $spacing-2 $spacing-4;
  color: var(--text-secondary);
  text-decoration: none;
  font-size: $font-size-sm;
  border-radius: $radius-lg;
  transition: all $transition-fast;
  background: color-mix(in srgb, var(--bg-primary) 55%, transparent);
  backdrop-filter: blur(8px);

  &:hover {
    color: var(--text-primary);
    background: var(--bg-hover);
  }

  svg {
    width: 18px;
    height: 18px;
  }
}

.auth-portal__hero {
  position: relative;
  flex: 0 0 70%;
  width: 70%;
  min-height: 100vh;
  overflow: hidden;
}

.auth-portal__hero-bg {
  position: absolute;
  inset: 0;
  pointer-events: none;
  z-index: 0;

  .bg-gradient {
    position: absolute;
    inset: 0;
    background:
      radial-gradient(ellipse 70% 55% at 35% 45%, var(--hero-glow) 0%, transparent 62%);
  }

  .bg-grid {
    position: absolute;
    inset: 0;
    opacity: 0.35;
    background-image:
      linear-gradient(var(--hero-grid) 1px, transparent 1px),
      linear-gradient(90deg, var(--hero-grid) 1px, transparent 1px);
    background-size: 60px 60px;
    mask-image: radial-gradient(circle at 40% 50%, black 20%, transparent 75%);
  }
}

.auth-portal__intro {
  position: absolute;
  left: clamp($spacing-8, 6vw, $spacing-12);
  bottom: clamp($spacing-10, 8vh, $spacing-16);
  z-index: 3;
  max-width: min(480px, 85%);
  pointer-events: none;
  text-shadow: 0 1px 12px color-mix(in srgb, var(--bg-primary) 85%, transparent);
}

.intro-logo {
  display: flex;
  align-items: center;
  gap: $spacing-3;
  margin-bottom: $spacing-6;

  img {
    width: 44px;
    height: 44px;
  }

  &__name {
    font-size: $font-size-2xl;
    font-weight: $font-weight-bold;
    color: var(--text-primary);
    letter-spacing: -0.02em;
  }
}

.intro-title {
  margin: 0 0 $spacing-4;
  font-size: clamp($font-size-2xl, 3.2vw, $font-size-4xl);
  font-weight: $font-weight-bold;
  line-height: $line-height-tight;
  color: var(--text-primary);
  letter-spacing: -0.02em;
}

.intro-description {
  margin: 0 0 $spacing-6;
  font-size: $font-size-base;
  line-height: $line-height-relaxed;
  color: var(--text-secondary);
}

.intro-features {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: $spacing-3;

  li {
    display: flex;
    align-items: center;
    gap: $spacing-3;
    font-size: $font-size-sm;
    color: var(--text-secondary);
  }
}

.auth-portal__panel {
  flex: 0 0 30%;
  width: 30%;
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: $spacing-8 $spacing-6;
  background: var(--bg-secondary);
  border-left: 1px solid var(--border-primary);
  position: relative;
  z-index: 5;
}

.auth-portal__panel-inner {
  width: 100%;
  max-width: 400px;
  display: flex;
  flex-direction: column;
  min-height: calc(100vh - #{$spacing-8 * 2});
  max-height: calc(100vh - #{$spacing-8 * 2});
  animation: slideUp 0.45s ease;
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(16px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.auth-form-block {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding-right: 2px;
}

.auth-portal__chat {
  flex-shrink: 0;
  margin-top: auto;
  padding-top: $spacing-5;
  border-top: 1px solid var(--border-primary);
}

.auth-tabs {
  display: flex;
  gap: $spacing-2;
  margin-bottom: $spacing-8;
  padding: $spacing-1;
  background: var(--bg-tertiary);
  border-radius: $radius-xl;
  border: 1px solid var(--border-primary);
}

.auth-tab {
  flex: 1;
  height: 40px;
  border: none;
  border-radius: $radius-lg;
  background: transparent;
  color: var(--text-secondary);
  font-size: $font-size-sm;
  font-weight: $font-weight-medium;
  cursor: pointer;
  transition: all $transition-fast;

  &:hover {
    color: var(--text-primary);
  }

  &--active {
    background: var(--bg-primary);
    color: var(--text-primary);
    box-shadow: var(--shadow-sm);
  }
}

.auth-form-header {
  margin-bottom: $spacing-6;

  h2 {
    margin: 0 0 $spacing-2;
    font-size: $font-size-xl;
    font-weight: $font-weight-bold;
    color: var(--text-primary);
  }

  p {
    margin: 0;
    font-size: $font-size-sm;
    color: var(--text-secondary);
  }
}

.auth-form {
  :deep(.el-form-item) {
    margin-bottom: $spacing-4;
  }

  :deep(.el-input) {
    --el-input-height: 46px;

    .el-input__wrapper {
      padding: 0 $spacing-4;
      background-color: var(--bg-tertiary);
      border: 1px solid var(--border-primary);
      border-radius: $radius-lg;
      transition: all $transition-fast;

      &:hover {
        border-color: var(--text-secondary);
      }

      &.is-focus {
        border-color: var(--accent-primary);
      }
    }

    .el-input__inner {
      height: 44px;
      color: var(--text-primary);

      &::placeholder {
        color: var(--text-secondary);
      }
    }
  }
}

.input-icon {
  width: 18px;
  height: 18px;
  color: var(--text-secondary);
}

.form-options {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: $spacing-5;

  .checkbox-label {
    color: var(--text-secondary);
  }

  :deep(.el-checkbox) {
    --el-checkbox-checked-bg-color: var(--accent-primary);
    --el-checkbox-checked-input-border-color: var(--accent-primary);
  }
}

.link-muted {
  font-size: $font-size-sm;
  color: var(--text-secondary);
  text-decoration: none;
  transition: color $transition-fast;

  &:hover {
    color: var(--accent-primary);
  }
}

.form-terms {
  margin-bottom: $spacing-5;

  .terms-text {
    font-size: $font-size-sm;
    color: var(--text-secondary);
    line-height: 1.5;
  }

  .terms-link {
    color: var(--accent-primary);
    text-decoration: none;

    &:hover {
      text-decoration: underline;
    }
  }

  :deep(.el-checkbox__input.is-checked .el-checkbox__inner) {
    background-color: var(--accent-primary);
    border-color: var(--accent-primary);
  }
}

.submit-button {
  width: 100%;
  height: 46px;
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
    transform: translateY(-1px);
    box-shadow: var(--shadow-md);
  }

  &:disabled {
    opacity: 0.65;
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
  }
}

@keyframes bounce {
  0%, 80%, 100% { transform: scale(0); }
  40% { transform: scale(1); }
}

.auth-portal__theme {
  margin-top: $spacing-6;
  display: flex;
  justify-content: center;
}

@media (max-width: 1024px) {
  .auth-portal {
    flex-direction: column;
  }

  .auth-portal__hero {
    flex: none;
    width: 100%;
    min-height: 42vh;
  }

  .auth-portal__intro {
    left: $spacing-6;
    bottom: $spacing-6;
    max-width: calc(100% - #{$spacing-12});
  }

  .intro-title {
    font-size: $font-size-2xl;
  }

  .intro-description,
  .intro-features {
    display: none;
  }

  .auth-portal__panel {
    flex: none;
    width: 100%;
    min-height: auto;
    border-left: none;
    border-top: 1px solid var(--border-primary);
    padding: $spacing-6 $spacing-4 $spacing-8;
  }

  .auth-portal__panel-inner {
    min-height: auto;
    max-height: none;
  }

  .auth-portal__back span {
    display: none;
  }
}
</style>
