<template>
  <div class="landing-page">
    <!-- Navigation -->
    <nav class="landing-nav">
      <div class="nav-container">
        <div class="nav-brand">
          <router-link
            to="/"
            class="brand-link"
          >
            <ThemeLogo
              alt="Flowly"
              class="brand-logo-img"
            />
            <span class="brand-name">Flowly</span>
          </router-link>
        </div>

        <div class="nav-links">
          <a
            href="#features"
            class="nav-link"
          >功能</a>
          <a
            href="#pricing"
            class="nav-link"
          >定价</a>
          <a
            href="#faq"
            class="nav-link"
          >常见问题</a>
        </div>

        <div class="nav-actions">
          <ThemeSwitcher variant="pill" />
          <router-link
            to="/login"
            class="btn btn-ghost"
          >
            登录
          </router-link>
          <router-link
            to="/register"
            class="btn btn-primary"
          >
            开始免费试用
          </router-link>
        </div>
      </div>
    </nav>

    <!-- Hero Section -->
    <section class="hero">
      <div class="hero-bg">
        <div class="hero-gradient" />
        <div class="hero-grid" />
      </div>
      <div class="hero-container">
        <div class="hero-badge">
          <span class="badge-dot" />
          AI驱动的下一代工作流平台
        </div>

        <h1 class="hero-title">
          用自然语言构建
          <span class="title-emphasis">AI 工作流</span>
        </h1>

        <p class="hero-description">
          Flowly 让您通过简单的对话描述，自动生成复杂的 AI 工作流。
          无需编程，即可构建自动化流程、集成多种 AI 能力。
        </p>

        <div class="hero-actions">
          <router-link
            to="/register"
            class="btn btn-primary btn-lg"
          >
            <Zap class="btn-icon" />
            免费开始
          </router-link>
          <router-link
            to="/nl-create"
            class="btn btn-outline btn-lg"
          >
            <Play class="btn-icon" />
            观看演示
          </router-link>
        </div>

        <div class="hero-stats">
          <div class="stat">
            <span class="stat-value">10K+</span>
            <span class="stat-label">活跃用户</span>
          </div>
          <div class="stat-divider" />
          <div class="stat">
            <span class="stat-value">100K+</span>
            <span class="stat-label">工作流执行</span>
          </div>
          <div class="stat-divider" />
          <div class="stat">
            <span class="stat-value">99.9%</span>
            <span class="stat-label">可用性</span>
          </div>
        </div>
      </div>
    </section>

    <!-- Features Section -->
    <section
      id="features"
      class="features"
    >
      <div class="container">
        <div class="section-header">
          <h2 class="section-title">
            强大的功能，简单的体验
          </h2>
          <p class="section-description">
            从自然语言描述到可视化工作流，Flowly 让 AI 开发变得前所未有的简单。
          </p>
        </div>

        <div class="features-grid">
          <div class="feature-card feature-pill feature-pill--blue">
            <div class="feature-icon">
              <MessageSquare class="icon" />
            </div>
            <h3 class="feature-title">
              自然语言生成
            </h3>
            <p class="feature-description">
              用日常语言描述您的需求，AI 自动为您构建完整的工作流程。无需学习复杂的语法。
            </p>
          </div>

          <div class="feature-card feature-pill feature-pill--blue">
            <div class="feature-icon">
              <GitBranch class="icon" />
            </div>
            <h3 class="feature-title">
              可视化编辑器
            </h3>
            <p class="feature-description">
              直观的拖拽式界面，让您轻松设计和编辑工作流。实时预览，每一步都清晰可见。
            </p>
          </div>

          <div class="feature-card feature-pill feature-pill--amber">
            <div class="feature-icon">
              <Bot class="icon" />
            </div>
            <h3 class="feature-title">
              AI Agent 编排
            </h3>
            <p class="feature-description">
              构建智能代理，赋予它们工具调用能力。多 Agent 协作，处理复杂任务。
            </p>
          </div>

          <div class="feature-card feature-pill feature-pill--rose">
            <div class="feature-icon">
              <Zap class="icon" />
            </div>
            <h3 class="feature-title">
              实时流式输出
            </h3>
            <p class="feature-description">
              即时查看 AI 生成的每一个字符。告别等待，获得流畅的交互体验。
            </p>
          </div>

          <div class="feature-card feature-pill feature-pill--emerald">
            <div class="feature-icon">
              <Database class="icon" />
            </div>
            <h3 class="feature-title">
              RAG 知识库
            </h3>
            <p class="feature-description">
              上传文档，构建私有知识库。让 AI 在您的数据基础上提供精准答案。
            </p>
          </div>

          <div class="feature-card feature-pill feature-pill--rose">
            <div class="feature-icon">
              <Users class="icon" />
            </div>
            <h3 class="feature-title">
              团队协作
            </h3>
            <p class="feature-description">
              与团队成员共享工作流，实时协作编辑。权限控制，确保安全共享。
            </p>
          </div>
        </div>
      </div>
    </section>

    <!-- How It Works Section -->
    <section class="how-it-works">
      <div class="container">
        <div class="section-header">
          <h2 class="section-title">
            三步创建您的 AI 工作流
          </h2>
          <p class="section-description">
            简单、直观、高效
          </p>
        </div>

        <div class="steps">
          <div class="step">
            <div class="step-number">
              1
            </div>
            <div class="step-content">
              <h3 class="step-title">
                描述您的需求
              </h3>
              <p class="step-description">
                用自然语言告诉 Flowly 您想要实现的功能，比如"创建一个客服机器人，能够回答产品相关问题"。
              </p>
            </div>
          </div>

          <div class="step-connector">
            <svg viewBox="0 0 100 20">
              <path
                d="M0 10 L100 10"
                stroke="currentColor"
                stroke-width="2"
                stroke-dasharray="6 4"
              />
            </svg>
          </div>

          <div class="step">
            <div class="step-number">
              2
            </div>
            <div class="step-content">
              <h3 class="step-title">
                AI 自动生成
              </h3>
              <p class="step-description">
                Flowly 的 AI 引擎理解您的意图，自动构建可视化工作流，包含所有必要的节点和连接。
              </p>
            </div>
          </div>

          <div class="step-connector">
            <svg viewBox="0 0 100 20">
              <path
                d="M0 10 L100 10"
                stroke="currentColor"
                stroke-width="2"
                stroke-dasharray="6 4"
              />
            </svg>
          </div>

          <div class="step">
            <div class="step-number">
              3
            </div>
            <div class="step-content">
              <h3 class="step-title">
                一键执行
              </h3>
              <p class="step-description">
                预览工作流，调整细节，然后一键执行。实时查看执行状态和输出结果。
              </p>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- Use Cases Section -->
    <section class="use-cases">
      <div class="container">
        <div class="use-cases-grid">
          <div class="use-case-content">
            <h2 class="section-title">
              适用于各种场景
            </h2>
            <p class="section-description">
              无论是客户服务、内容创作还是数据分析，Flowly 都能助您一臂之力。
            </p>

            <div class="use-case-list">
              <div class="use-case-item">
                <div class="use-case-icon">
                  <Headphones class="icon" />
                </div>
                <div class="use-case-text">
                  <h4>智能客服</h4>
                  <p>构建 7x24 小时在线的 AI 客服，自动回答常见问题</p>
                </div>
              </div>

              <div class="use-case-item">
                <div class="use-case-icon">
                  <FileText class="icon" />
                </div>
                <div class="use-case-text">
                  <h4>内容生成</h4>
                  <p>自动化生成营销文案、社交媒体内容、产品描述</p>
                </div>
              </div>

              <div class="use-case-item">
                <div class="use-case-icon">
                  <BarChart class="icon" />
                </div>
                <div class="use-case-text">
                  <h4>数据分析</h4>
                  <p>自动采集、处理和分析数据，生成可视化报告</p>
                </div>
              </div>
            </div>
          </div>

          <div class="use-case-visual">
            <div class="workflow-preview">
              <div class="preview-header">
                <span class="preview-dot red" />
                <span class="preview-dot yellow" />
                <span class="preview-dot green" />
              </div>
              <div class="preview-content">
                <div class="preview-node start">
                  <MessageSquare class="node-icon" />
                  <span>用户输入</span>
                </div>
                <div class="preview-arrow">
                  <ChevronRight class="arrow-icon" />
                </div>
                <div class="preview-node ai">
                  <Bot class="node-icon" />
                  <span>AI 分析</span>
                </div>
                <div class="preview-arrow">
                  <ChevronRight class="arrow-icon" />
                </div>
                <div class="preview-node output">
                  <FileText class="node-icon" />
                  <span>生成回复</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- Pricing Section -->
    <section
      id="pricing"
      class="pricing"
    >
      <div class="container">
        <div class="section-header">
          <h2 class="section-title">
            简单透明的定价
          </h2>
          <p class="section-description">
            从免费开始，根据需求升级。所有方案均包含 14 天免费试用。
          </p>
        </div>

        <div class="pricing-grid">
          <div class="pricing-card">
            <div class="pricing-header">
              <h3 class="plan-name">
                免费版
              </h3>
              <div class="plan-price">
                <span class="price">¥0</span>
                <span class="period">/月</span>
              </div>
              <p class="plan-description">
                适合个人探索和小规模使用
              </p>
            </div>
            <ul class="plan-features">
              <li>
                <Check class="check-icon" />
                3 个工作流
              </li>
              <li>
                <Check class="check-icon" />
                100 次执行/月
              </li>
              <li>
                <Check class="check-icon" />
                基础模板
              </li>
              <li>
                <Check class="check-icon" />
                社区支持
              </li>
            </ul>
            <router-link
              to="/register"
              class="btn btn-outline btn-block"
            >
              免费开始
            </router-link>
          </div>

          <div class="pricing-card featured">
            <div class="featured-badge">
              最受欢迎
            </div>
            <div class="pricing-header">
              <h3 class="plan-name">
                专业版
              </h3>
              <div class="plan-price">
                <span class="price">¥99</span>
                <span class="period">/月</span>
              </div>
              <p class="plan-description">
                适合团队和中小型企业
              </p>
            </div>
            <ul class="plan-features">
              <li>
                <Check class="check-icon" />
                无限工作流
              </li>
              <li>
                <Check class="check-icon" />
                10,000 次执行/月
              </li>
              <li>
                <Check class="check-icon" />
                高级模板库
              </li>
              <li>
                <Check class="check-icon" />
                团队协作
              </li>
              <li>
                <Check class="check-icon" />
                优先支持
              </li>
            </ul>
            <router-link
              to="/register"
              class="btn btn-primary btn-block"
            >
              立即升级
            </router-link>
          </div>

          <div class="pricing-card">
            <div class="pricing-header">
              <h3 class="plan-name">
                企业版
              </h3>
              <div class="plan-price">
                <span class="price">¥399</span>
                <span class="period">/月</span>
              </div>
              <p class="plan-description">
                适合大型企业和高需求场景
              </p>
            </div>
            <ul class="plan-features">
              <li>
                <Check class="check-icon" />
                无限所有
              </li>
              <li>
                <Check class="check-icon" />
                私有化部署
              </li>
              <li>
                <Check class="check-icon" />
                SSO 集成
              </li>
              <li>
                <Check class="check-icon" />
                SLA 保障
              </li>
              <li>
                <Check class="check-icon" />
                专属客服
              </li>
            </ul>
            <router-link
              to="/register"
              class="btn btn-outline btn-block"
            >
              联系销售
            </router-link>
          </div>
        </div>
      </div>
    </section>

    <!-- FAQ Section -->
    <section
      id="faq"
      class="faq"
    >
      <div class="container">
        <div class="section-header">
          <h2 class="section-title">
            常见问题
          </h2>
        </div>

        <div class="faq-list">
          <div class="faq-item">
            <button
              class="faq-question"
              @click="toggleFaq(0)"
            >
              <span>Flowly 支持哪些 AI 模型？</span>
              <ChevronDown
                class="faq-icon"
                :class="{ active: openFaq === 0 }"
              />
            </button>
            <div
              class="faq-answer"
              :class="{ open: openFaq === 0 }"
            >
              <p>Flowly 支持 OpenAI GPT 系列、Anthropic Claude、阿里通义千问、百度文心一言等多种主流 AI 模型。您可以根据需求自由选择和切换。</p>
            </div>
          </div>

          <div class="faq-item">
            <button
              class="faq-question"
              @click="toggleFaq(1)"
            >
              <span>是否需要编程基础？</span>
              <ChevronDown
                class="faq-icon"
                :class="{ active: openFaq === 1 }"
              />
            </button>
            <div
              class="faq-answer"
              :class="{ open: openFaq === 1 }"
            >
              <p>完全不需要！Flowly 的核心理念是降低 AI 开发门槛。您可以通过自然语言描述需求，或使用可视化拖拽来构建工作流。</p>
            </div>
          </div>

          <div class="faq-item">
            <button
              class="faq-question"
              @click="toggleFaq(2)"
            >
              <span>我的数据安全吗？</span>
              <ChevronDown
                class="faq-icon"
                :class="{ active: openFaq === 2 }"
              />
            </button>
            <div
              class="faq-answer"
              :class="{ open: openFaq === 2 }"
            >
              <p>我们非常重视数据安全。所有数据传输使用 TLS 加密，数据存储符合 SOC 2 标准。企业版还支持私有化部署，完全掌控您的数据。</p>
            </div>
          </div>

          <div class="faq-item">
            <button
              class="faq-question"
              @click="toggleFaq(3)"
            >
              <span>可以集成到现有系统吗？</span>
              <ChevronDown
                class="faq-icon"
                :class="{ active: openFaq === 3 }"
              />
            </button>
            <div
              class="faq-answer"
              :class="{ open: openFaq === 3 }"
            >
              <p>可以！Flowly 提供完整的 REST API 和 Webhook 支持，可以轻松与您的网站、应用或其他 SaaS 服务集成。</p>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- CTA Section -->
    <section class="cta">
      <div class="container">
        <div class="cta-content">
          <h2 class="cta-title">
            准备好开始了吗？
          </h2>
          <p class="cta-description">
            免费注册，立即体验 Flowly 的强大功能。
          </p>
          <div class="cta-actions">
            <router-link
              to="/register"
              class="btn btn-primary btn-lg"
            >
              开始免费试用
            </router-link>
          </div>
        </div>
      </div>
    </section>

    <!-- Footer -->
    <footer class="landing-footer">
      <div class="container">
        <div class="footer-grid">
          <div class="footer-brand">
            <div class="nav-brand">
              <router-link
                to="/"
                class="brand-link"
              >
                <ThemeLogo
                  alt="Flowly"
                  class="brand-logo-img"
                />
                <span class="brand-name">Flowly</span>
              </router-link>
            </div>
            <p class="footer-tagline">
              AI Agent 工作流编排平台
            </p>
          </div>

          <div class="footer-links">
            <h4>产品</h4>
            <a href="#features">功能</a>
            <a href="#pricing">定价</a>
            <a href="#faq">常见问题</a>
          </div>

          <div class="footer-links">
            <h4>资源</h4>
            <a href="#">文档</a>
            <a href="#">API</a>
            <a href="#">教程</a>
          </div>

          <div class="footer-links">
            <h4>公司</h4>
            <a href="#">关于我们</a>
            <a href="#">博客</a>
            <a href="#">联系我们</a>
          </div>
        </div>

        <div class="footer-bottom">
          <p>&copy; 2026 Flowly. 保留所有权利。</p>
        </div>
      </div>
    </footer>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import ThemeLogo from '@/components/common/ThemeLogo.vue'
import ThemeSwitcher from '@/components/common/ThemeSwitcher.vue'
import {
  Zap, Play, MessageSquare, GitBranch, Bot, Database, Users,
  FileText, Headphones, BarChart, ChevronRight, ChevronDown, Check
} from 'lucide-vue-next'

const openFaq = ref(null)

function toggleFaq(index) {
  openFaq.value = openFaq.value === index ? null : index
}
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

// 主题自适应颜色
$primary: var(--accent-primary);
$primary-dark: var(--accent-secondary);
$white: var(--text-inverse);

.landing-page {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  color: var(--text-primary);
  line-height: 1.6;
  background-color: var(--bg-primary);
  transition: background-color 0.3s, color 0.3s;
}

.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 $spacing-6;
}

// Navigation
.landing-nav {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 100;
  background: var(--glass-bg);
  backdrop-filter: blur(var(--glass-blur));
  -webkit-backdrop-filter: blur(var(--glass-blur));
  border-bottom: 1px solid var(--glass-border);
  box-shadow: var(--glass-shadow);
  transition: background-color 0.3s, border-color 0.3s, backdrop-filter 0.3s;
}

.nav-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: $spacing-4 $spacing-6;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.nav-brand {
  display: flex;
  align-items: center;
  gap: $spacing-2;

  .brand-link {
    display: flex;
    align-items: center;
    gap: $spacing-2;
    text-decoration: none;
  }

  .brand-logo-img {
    width: 32px;
    height: 32px;
  }

  .brand-name {
    font-size: $font-size-xl;
    font-weight: $font-weight-bold;
    color: var(--text-primary);
  }
}

.nav-links {
  display: flex;
  gap: $spacing-8;

  .nav-link {
    color: var(--text-secondary);
    text-decoration: none;
    font-size: $font-size-sm;
    transition: color 0.2s;

    &:hover {
      color: var(--text-primary);
    }
  }
}

.nav-actions {
  display: flex;
  align-items: center;
  gap: $spacing-3;
}

// Buttons
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: $spacing-2;
  padding: $spacing-2 $spacing-4;
  border-radius: $radius-lg;
  font-size: $font-size-sm;
  font-weight: $font-weight-medium;
  text-decoration: none;
  transition: all 0.2s;
  cursor: pointer;
  border: none;

  &-icon {
    width: 16px;
    height: 16px;
  }

  &-lg {
    padding: $spacing-3 $spacing-6;
    font-size: $font-size-base;
  }

  &-block {
    width: 100%;
  }

  &-primary {
    background: var(--button-primary-bg);
    color: var(--button-primary-text);
    box-shadow: var(--button-primary-shadow, var(--shadow-sm));

    &:hover {
      background: var(--button-primary-hover-bg);
      color: var(--button-primary-text);
      transform: translateY(-2px);
      box-shadow: var(--shadow-md);
    }
  }

  &-outline {
    background: transparent;
    border: 1px solid var(--border-primary);
    color: var(--text-primary);

    &:hover {
      border-color: var(--border-hover);
      color: var(--text-primary);
      background: var(--bg-hover);
    }
  }

  &-ghost {
    background: transparent;
    color: var(--text-primary);

    &:hover {
      background: var(--bg-hover);
      color: var(--text-primary);
    }
  }

  &-white {
    background: var(--text-inverse);
    color: var(--bg-primary);

    &:hover {
      transform: translateY(-1px);
      box-shadow: var(--shadow-md);
    }
  }
}

// Hero Section
.hero {
  position: relative;
  padding: 160px 0 100px;
  text-align: center;
  overflow: hidden;
}

.hero-bg {
  position: absolute;
  inset: 0;
  z-index: -1;
}

.hero-gradient {
  position: absolute;
  top: -50%;
  left: 50%;
  transform: translateX(-50%);
  width: 150%;
  height: 150%;
  background: radial-gradient(ellipse at center, var(--hero-glow) 0%, transparent 60%);
}

.hero-grid {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(var(--hero-grid) 1px, transparent 1px),
    linear-gradient(90deg, var(--hero-grid) 1px, transparent 1px);
  background-size: 60px 60px;
  mask-image: radial-gradient(ellipse at center, black 30%, transparent 70%);
}

.hero-container {
  max-width: 900px;
  margin: 0 auto;
  padding: 0 $spacing-6;
}

.hero-badge {
  display: inline-flex;
  align-items: center;
  gap: $spacing-2;
  padding: $spacing-2 $spacing-4;
  background: var(--surface-muted);
  border: 1px solid var(--accent-blue-soft);
  border-radius: $radius-full;
  color: var(--text-primary);
  margin-bottom: $spacing-6;
  font-size: $font-size-sm;
  font-weight: $font-weight-medium;

  .badge-dot {
    width: 8px;
    height: 8px;
    background: var(--accent-blue);
    border-radius: 50%;
    animation: pulse 2s infinite;
  }
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.hero-title {
  font-size: 4rem;
  font-weight: $font-weight-bold;
  line-height: 1.1;
  margin-bottom: $spacing-6;
  color: var(--text-primary);

  @media (max-width: $breakpoint-md) {
    font-size: 2.5rem;
  }
}

.title-emphasis {
  color: var(--text-primary);
  border-bottom: 2px solid var(--accent-blue-soft);
  padding-bottom: 0.06em;
}

.hero-description {
  font-size: $font-size-xl;
  color: var(--text-secondary);
  max-width: 700px;
  margin: 0 auto $spacing-8;
}

.hero-actions {
  display: flex;
  gap: $spacing-4;
  justify-content: center;
  flex-wrap: wrap;
  margin-bottom: $spacing-12;
}

.hero-stats {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: $spacing-8;
}

.stat {
  text-align: center;

  .stat-value {
    display: block;
    font-size: $font-size-2xl;
    font-weight: $font-weight-bold;
    color: var(--text-primary);
  }

  .stat-label {
    font-size: $font-size-sm;
    color: var(--text-secondary);
  }
}

.stat-divider {
  width: 1px;
  height: 40px;
  background: var(--border-primary);
}

// Section Styles
.section-header {
  text-align: center;
  margin-bottom: $spacing-12;
}

.section-title {
  font-size: $font-size-3xl;
  font-weight: $font-weight-bold;
  margin-bottom: $spacing-4;
  color: var(--text-primary);
}

.section-description {
  font-size: $font-size-lg;
  color: var(--text-secondary);
  max-width: 600px;
  margin: 0 auto;
}

// Features Section
.features {
  padding: 100px 0;
  background: var(--bg-secondary);
  transition: background-color 0.3s;
}

.features-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: $spacing-6;

  @media (max-width: $breakpoint-lg) {
    grid-template-columns: repeat(2, 1fr);
  }

  @media (max-width: $breakpoint-sm) {
    grid-template-columns: 1fr;
  }
}

.feature-card {
  position: relative;
  background: var(--card-bg);
  padding: $spacing-6;
  border-radius: var(--radius-card, $radius-xl);
  border: 1px solid var(--card-border);
  box-shadow: var(--shadow-sm);
  overflow: hidden;
  transition: transform 0.3s cubic-bezier(0.22, 1, 0.36, 1),
              box-shadow 0.3s ease,
              border-color 0.3s ease;

  &::before {
    content: '';
    position: absolute;
    inset: 0;
    pointer-events: none;
    background: var(--card-inner-highlight);
  }

  &:hover {
    transform: translateY(-6px);
    border-color: var(--item-accent-soft, var(--border-hover));
    box-shadow: var(--shadow-md);
  }
}

.feature-icon {
  position: relative;
  z-index: 1;
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-tertiary);
  border-radius: $radius-lg;
  margin-bottom: $spacing-4;
  box-shadow: inset 0 0 0 1px var(--item-accent-soft, var(--accent-blue-soft));

  .icon {
    width: 24px;
    height: 24px;
    color: var(--item-accent, var(--accent-blue));
  }
}

.feature-title {
  font-size: $font-size-lg;
  font-weight: $font-weight-semibold;
  margin-bottom: $spacing-2;
  color: var(--text-primary);
}

.feature-description {
  font-size: $font-size-sm;
  color: var(--text-secondary);
  line-height: 1.7;
}

// How It Works
.how-it-works {
  padding: 100px 0;
  background: var(--bg-primary);
  transition: background-color 0.3s;
}

.steps {
  display: flex;
  align-items: flex-start;
  justify-content: center;
  gap: $spacing-4;

  @media (max-width: $breakpoint-md) {
    flex-direction: column;
    align-items: center;
  }
}

.step {
  display: flex;
  gap: $spacing-4;
  flex: 1;
  max-width: 300px;
}

.step-number {
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--accent-primary);
  color: var(--text-inverse);
  font-size: $font-size-xl;
  font-weight: $font-weight-bold;
  border-radius: 50%;
  flex-shrink: 0;
}

.step-content {
  .step-title {
    font-size: $font-size-lg;
    font-weight: $font-weight-semibold;
    margin-bottom: $spacing-2;
    color: var(--text-primary);
  }

  .step-description {
    font-size: $font-size-sm;
    color: var(--text-secondary);
  }
}

.step-connector {
  width: 100px;
  color: var(--border-primary);
  padding-top: 12px;

  @media (max-width: $breakpoint-md) {
    transform: rotate(90deg);
    width: 60px;
  }

  svg {
    width: 100%;
  }
}

// Use Cases
.use-cases {
  padding: 100px 0;
  background: var(--bg-secondary);
  transition: background-color 0.3s;
}

.use-cases-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: $spacing-12;
  align-items: center;

  @media (max-width: $breakpoint-lg) {
    grid-template-columns: 1fr;
  }
}

.use-case-list {
  display: flex;
  flex-direction: column;
  gap: $spacing-6;
}

.use-case-item {
  display: flex;
  gap: $spacing-4;
}

.use-case-icon {
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-tertiary);
  border-radius: $radius-lg;
  flex-shrink: 0;
  box-shadow: var(--shadow-sm);

  .icon {
    width: 24px;
    height: 24px;
    color: var(--accent-primary);
  }
}

.use-case-text {
  h4 {
    font-size: $font-size-base;
    font-weight: $font-weight-semibold;
    margin-bottom: $spacing-1;
    color: var(--text-primary);
  }

  p {
    font-size: $font-size-sm;
    color: var(--text-secondary);
  }
}

.workflow-preview {
  background: var(--bg-tertiary);
  border-radius: $radius-xl;
  overflow: hidden;
  box-shadow: var(--shadow-xl);
}

.preview-header {
  display: flex;
  gap: $spacing-2;
  padding: $spacing-3 $spacing-4;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-primary);
}

.preview-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;

  &.red { background: var(--text-tertiary); }
  &.yellow { background: var(--text-secondary); }
  &.green { background: var(--text-primary); }
}

.preview-content {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: $spacing-4;
  padding: $spacing-8;
  flex-wrap: wrap;
}

.preview-node {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: $spacing-2;
  padding: $spacing-4;
  border-radius: $radius-lg;
  min-width: 100px;

  .node-icon {
    width: 24px;
    height: 24px;
  }

  span {
    font-size: $font-size-xs;
    font-weight: $font-weight-medium;
    color: var(--text-primary);
  }

  &.start {
    background: var(--surface-muted);
    color: var(--accent-primary);
  }

  &.ai {
    background: var(--accent-primary);
    color: var(--text-inverse);
  }

  &.output {
    background: var(--surface-muted);
    color: var(--accent-primary);
  }
}

.preview-arrow {
  .arrow-icon {
    width: 20px;
    height: 20px;
    color: var(--border-primary);
  }
}

// Pricing
.pricing {
  padding: 100px 0;
  background: var(--bg-primary);
  transition: background-color 0.3s;
}

.pricing-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: $spacing-6;
  align-items: start;

  @media (max-width: $breakpoint-lg) {
    grid-template-columns: 1fr;
    max-width: 400px;
    margin: 0 auto;
  }
}

.pricing-card {
  background: var(--bg-tertiary);
  border-radius: $radius-xl;
  padding: $spacing-6;
  border: 1px solid var(--border-primary);
  position: relative;
  transition: all 0.3s;

  &.featured {
    border: 2px solid $primary;
    transform: scale(1.05);

    @media (max-width: $breakpoint-lg) {
      transform: none;
    }
  }
}

.featured-badge {
  position: absolute;
  top: -12px;
  left: 50%;
  transform: translateX(-50%);
  background: var(--accent-primary);
  color: var(--text-inverse);
  padding: $spacing-1 $spacing-3;
  border-radius: 100px;
  font-size: $font-size-xs;
  font-weight: $font-weight-semibold;
}

.pricing-header {
  text-align: center;
  padding-bottom: $spacing-6;
  border-bottom: 1px solid var(--border-primary);
  margin-bottom: $spacing-6;
}

.plan-name {
  font-size: $font-size-lg;
  font-weight: $font-weight-semibold;
  margin-bottom: $spacing-2;
  color: var(--text-primary);
}

.plan-price {
  .price {
    font-size: $font-size-3xl;
    font-weight: $font-weight-bold;
    color: var(--text-primary);
  }

  .period {
    font-size: $font-size-sm;
    color: var(--text-secondary);
  }
}

.plan-description {
  font-size: $font-size-sm;
  color: var(--text-secondary);
  margin-top: $spacing-2;
}

.plan-features {
  list-style: none;
  padding: 0;
  margin: 0 0 $spacing-6;

  li {
    display: flex;
    align-items: center;
    gap: $spacing-2;
    padding: $spacing-2 0;
    font-size: $font-size-sm;
    color: var(--text-secondary);

    .check-icon {
      width: 16px;
      height: 16px;
      color: var(--success);
    }
  }
}

// FAQ
.faq {
  padding: 100px 0;
  background: var(--bg-secondary);
  transition: background-color 0.3s;
}

.faq-list {
  max-width: 800px;
  margin: 0 auto;
}

.faq-item {
  background: var(--bg-tertiary);
  border-radius: $radius-lg;
  margin-bottom: $spacing-3;
  overflow: hidden;
}

.faq-question {
  width: 100%;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: $spacing-4 $spacing-5;
  background: transparent;
  border: none;
  font-size: $font-size-base;
  font-weight: $font-weight-medium;
  color: var(--text-primary);
  cursor: pointer;
  text-align: left;
  transition: background-color 0.2s;

  &:hover {
    background: var(--bg-hover);
  }
}

.faq-icon {
  width: 20px;
  height: 20px;
  color: var(--text-secondary);
  transition: transform 0.3s;

  &.active {
    transform: rotate(180deg);
  }
}

.faq-answer {
  max-height: 0;
  overflow: hidden;
  transition: max-height 0.3s;

  &.open {
    max-height: 200px;
  }

  p {
    padding: 0 $spacing-5 $spacing-4;
    font-size: $font-size-sm;
    color: var(--text-secondary);
    line-height: 1.7;
  }
}

// CTA
.cta {
  padding: 100px 0;
  background: var(--bg-primary);
  color: var(--text-primary);
  text-align: center;
  border-top: 1px solid var(--border-primary);
}

.cta-content {
  max-width: 600px;
  margin: 0 auto;
}

.cta-title {
  font-size: $font-size-3xl;
  font-weight: $font-weight-bold;
  color: var(--text-primary);
  margin-bottom: $spacing-4;
}

.cta-description {
  font-size: $font-size-lg;
  color: var(--text-secondary);
  margin-bottom: $spacing-8;
}

// Footer
.landing-footer {
  padding: 60px 0 30px;
  background: var(--bg-tertiary);
  color: var(--text-secondary);
  border-top: 1px solid var(--border-primary);
}

.footer-grid {
  display: grid;
  grid-template-columns: 2fr 1fr 1fr 1fr;
  gap: $spacing-8;
  margin-bottom: $spacing-8;

  @media (max-width: $breakpoint-lg) {
    grid-template-columns: repeat(2, 1fr);
  }

  @media (max-width: $breakpoint-sm) {
    grid-template-columns: 1fr;
  }
}

.footer-brand {
  .nav-brand {
    margin-bottom: $spacing-2;

    .brand-name {
      color: var(--text-primary);
    }
  }

  .footer-tagline {
    font-size: $font-size-sm;
    color: var(--text-secondary);
  }
}

.footer-links {
  h4 {
    color: var(--text-primary);
    font-size: $font-size-sm;
    font-weight: $font-weight-semibold;
    margin-bottom: $spacing-4;
  }

  a {
    display: block;
    color: var(--text-secondary);
    font-size: $font-size-sm;
    text-decoration: none;
    padding: $spacing-1 0;
    transition: color 0.2s;

    &:hover {
      color: var(--text-primary);
    }
  }
}

.footer-bottom {
  padding-top: $spacing-6;
  border-top: 1px solid var(--border-primary);
  text-align: center;

  p {
    font-size: $font-size-sm;
    color: var(--text-secondary);
  }
}
</style>
