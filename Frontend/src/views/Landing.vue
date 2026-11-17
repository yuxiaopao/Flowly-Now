<template>
  <div class="landing-page">
    <a
      class="landing-skip"
      href="#landing-main"
    >跳至页面内容</a>
    <header>
      <nav aria-label="产品导航">
        <router-link
          to="/"
          class="brand"
          aria-label="Flowly 首页"
        >
          <ThemeLogo alt="" /><strong>Flowly</strong><small>STUDIO</small>
        </router-link><div class="nav-links">
          <a href="#delivery">交付流程</a><a href="#scenarios">使用场景</a><a href="#faq">常见问题</a>
        </div><ThemeSwitcher /><router-link to="/login">
          登录
        </router-link>
      </nav>
    </header>
    <main id="landing-main">
      <section
        class="hero"
        aria-labelledby="hero-title"
      >
        <div>
          <p class="eyebrow">
            {{ LANDING.eyebrow }}
          </p><h1 id="hero-title">
            {{ LANDING.title }}<br><span>{{ LANDING.emphasis }}</span>
          </h1><p class="description">
            {{ LANDING.description }}
          </p><router-link
            :to="LANDING.primaryPath"
            class="primary"
          >
            {{ LANDING.primary }}<ArrowUpRight aria-hidden="true" />
          </router-link><p class="note">
            知识助手与工作流应用，共用一条交付路径。
          </p>
        </div>
        <div
          class="preview"
          aria-label="应用交付路径示意"
        >
          <div class="preview-heading">
            <span><Boxes aria-hidden="true" />APPLICATION DELIVERY</span><small>流程示意</small>
          </div><div class="preview-app">
            <Layers aria-hidden="true" /><div><strong>团队知识助手</strong><small>知识库 → 检索 → 有依据的回答</small></div><FlowlyBot
              :size="BOT_AVATAR.size"
              decorative
              :animated="false"
            />
          </div>
          <div
            class="stage-tabs"
            role="tablist"
            aria-label="了解交付步骤"
          >
            <button
              v-for="(stage, index) in LANDING.stages"
              :id="`delivery-tab-${index}`"
              :key="stage.label"
              type="button"
              role="tab"
              :aria-selected="activeStage === index"
              :tabindex="activeStage === index ? 0 : -1"
              :aria-controls="`delivery-panel-${index}`"
              @click="activeStage = index"
              @keydown="changeStage($event, index)"
            >
              <span>0{{ index + 1 }}</span>{{ stage.label }}
            </button>
          </div>
          <div
            v-for="(stage, index) in LANDING.stages"
            v-show="activeStage === index"
            :id="`delivery-panel-${index}`"
            :key="stage.label"
            role="tabpanel"
            :aria-labelledby="`delivery-tab-${index}`"
            class="stage-panel"
          >
            <component
              :is="icons[stage.icon]"
              aria-hidden="true"
            /><h2>{{ stage.title }}</h2><p>{{ stage.detail }}</p><code>{{ stage.code }}</code>
          </div><div class="preview-footer">
            <ShieldCheck aria-hidden="true" />应用专属密钥<span>真实测试与请求记录</span>
          </div>
        </div>
      </section>
      <section
        id="delivery"
        class="split-section"
        aria-labelledby="delivery-title"
      >
        <div class="intro">
          <span class="eyebrow">从原型，到稳定交付</span><h2 id="delivery-title">
            少一点入口切换，<br>多一条能走通的流程。
          </h2><p>应用是交付对象。知识、模型与流程是构建资源，每一步都能找到下一步。</p>
        </div><ol class="rows">
          <li
            v-for="(stage, index) in LANDING.stages"
            :key="stage.label"
          >
            <span class="number">0{{ index + 1 }}</span><div><h3>{{ stage.title }}</h3><p>{{ stage.detail }}</p></div><component
              :is="icons[stage.icon]"
              aria-hidden="true"
            />
          </li>
        </ol>
      </section>
      <section
        id="scenarios"
        class="split-section"
        aria-labelledby="scenarios-title"
      >
        <div class="intro">
          <span class="eyebrow">围绕小团队的真实工作</span><h2 id="scenarios-title">
            做出应用，<br>也把维护的路留好。
          </h2>
        </div><div class="rows">
          <article
            v-for="item in LANDING.scenarios"
            :key="item.number"
          >
            <span class="number">{{ item.number }}</span><div><h3>{{ item.title }}</h3><p>{{ item.description }}</p><small>{{ item.tags }}</small></div><ArrowUpRight aria-hidden="true" />
          </article>
        </div>
      </section>
      <section
        class="statement"
        aria-label="产品主张"
      >
        <p>发布时有把握，<br><span>迭代时有依据。</span></p><div>
          <p>版本、测试与请求记录放在同一个应用工作区。<br>先把一条真实业务跑通，再扩展下一项能力。</p><router-link
            :to="LANDING.primaryPath"
            class="primary"
          >
            开始创建应用<ArrowUpRight aria-hidden="true" />
          </router-link>
        </div>
      </section>
      <section
        id="faq"
        class="split-section faq"
        aria-labelledby="faq-title"
      >
        <div class="intro">
          <span class="eyebrow">开始之前</span><h2 id="faq-title">
            接入与使用
          </h2><p>明确能力边界，交付才有可预期的结果。</p>
        </div><div>
          <details
            v-for="item in LANDING.faqs"
            :key="item.question"
          >
            <summary>{{ item.question }}<Plus aria-hidden="true" /></summary><p>{{ item.answer }}</p>
          </details>
        </div>
      </section>
    </main>
    <footer>
      <router-link
        to="/"
        class="brand"
      >
        <strong>Flowly</strong><small>AI 应用交付工作台</small>
      </router-link><router-link to="/login">
        登录工作区<ArrowUpRight aria-hidden="true" />
      </router-link><span>知识 · 流程 · 测试 · 发布 · 观测</span>
    </footer>
  </div>
</template>
<script setup>
import { nextTick, ref } from 'vue'
import { ArrowUpRight, Boxes, FlaskConical, GitBranch, Layers, Plus, Radio, ShieldCheck } from 'lucide-vue-next'
import { LANDING } from '@/config/landing'
import { BOT_AVATAR } from '@/config/botAvatar'
import ThemeLogo from '@/components/common/ThemeLogo.vue'
import ThemeSwitcher from '@/components/common/ThemeSwitcher.vue'
import FlowlyBot from '@/components/common/FlowlyBot.vue'
const icons = { Boxes, FlaskConical, GitBranch, Radio }
const activeStage = ref(0)
async function changeStage(event, index) {
  const total = LANDING.stages.length
  const next = event.key === 'ArrowRight' ? (index + 1) % total : event.key === 'ArrowLeft' ? (index + total - 1) % total : event.key === 'Home' ? 0 : event.key === 'End' ? total - 1 : null
  if (next == null) return
  event.preventDefault()
  activeStage.value = next
  await nextTick()
  document.getElementById(`delivery-tab-${next}`)?.focus()
}
</script>
<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;
.landing-page { --landing-width: 1200px; --landing-gutter: 32px; --landing-space: 96px; --landing-display: 48px; --landing-heading: 36px; color: var(--text-primary); background: var(--delivery-surface); }
.landing-page svg { width: var(--delivery-icon); height: var(--delivery-icon); flex-shrink: 0; }
.landing-page a:hover { opacity: 1; }
.landing-page h1, .landing-page h2 { text-wrap: balance; }
.landing-page p { text-wrap: pretty; }
.landing-skip { position: fixed; top: $spacing-3; left: $spacing-3; z-index: $z-tooltip; transform: translateY(-200%); padding: $spacing-3; background: var(--bg-elevated); &:focus { transform: none; } }
header { border-bottom: 1px solid var(--delivery-border); background: var(--delivery-panel); }
nav { max-width: var(--landing-width); margin-inline: auto; padding: $spacing-4 var(--landing-gutter); display: flex; gap: $spacing-6; align-items: center; font-size: $font-size-sm; }
.brand { display: flex; align-items: center; gap: $spacing-3; color: var(--text-primary); :deep(img) { width: $spacing-8; height: $spacing-8; } strong { font-size: $font-size-xl; font-weight: $font-weight-semibold; } small { color: var(--text-tertiary); font-size: $font-size-xs; } }
.nav-links { display: flex; gap: $spacing-6; margin-left: auto; a { color: var(--text-secondary); &:hover { color: var(--delivery-accent); } } }
.hero, .split-section { max-width: var(--landing-width); margin-inline: auto; display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: $spacing-12; padding: var(--landing-space) var(--landing-gutter); }
.hero { align-items: center; }
.eyebrow { color: var(--delivery-accent); font-size: $font-size-xs; font-weight: $font-weight-medium; }
h1 { margin-block: $spacing-6; font-size: var(--landing-display); line-height: 1.2; font-weight: $font-weight-semibold; letter-spacing: -0.025em; span { color: var(--delivery-accent); } }
.description { margin-bottom: $spacing-8; max-width: 65ch; color: var(--text-secondary); font-size: $font-size-base; line-height: $line-height-relaxed; }
.primary { display: inline-flex; align-items: center; justify-content: center; gap: $spacing-4; padding: $spacing-3 $spacing-4; min-height: var(--delivery-touch-target); border-radius: var(--radius-lg); color: var(--button-primary-text); background: var(--button-primary-bg); font-size: $font-size-sm; font-weight: $font-weight-semibold; transition: background-color var(--delivery-transition); &:hover { background: var(--button-primary-hover-bg); } }
.note { margin-top: $spacing-4; color: var(--text-tertiary); font-size: $font-size-xs; }
.preview { min-width: 0; border: 1px solid var(--border-secondary); border-radius: var(--radius-xl); background: var(--delivery-panel); overflow: hidden; box-shadow: var(--shadow-md); }
.preview-heading, .preview-footer { display: flex; align-items: center; gap: $spacing-2; padding: $spacing-4 $spacing-6; color: var(--text-secondary); font-size: $font-size-xs; > span { display: inline-flex; align-items: center; gap: $spacing-2; } }
.preview-heading { border-bottom: 1px solid var(--delivery-border); font-family: var(--font-family-mono); small { margin-left: auto; color: var(--text-tertiary); } }
.preview-app { display: flex; align-items: center; gap: $spacing-3; padding: $spacing-6; > svg { color: var(--delivery-accent); } > div { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: $spacing-1; } strong { font-size: $font-size-base; font-weight: $font-weight-medium; } small { font-size: $font-size-xs; color: var(--text-secondary); } }
.stage-tabs { display: flex; padding-inline: $spacing-6; gap: $spacing-2; button { flex: 1; display: flex; justify-content: center; align-items: center; gap: $spacing-2; padding: $spacing-2; min-height: var(--delivery-touch-target); border: 1px solid transparent; border-radius: var(--radius-md); color: var(--text-secondary); font-size: $font-size-sm; span { font-family: var(--font-family-mono); font-size: $font-size-xs; line-height: $line-height-normal; color: var(--text-tertiary); } &:hover { background: var(--bg-hover); } &[aria-selected='true'] { background: var(--delivery-accent-soft); color: var(--delivery-accent); border-color: var(--delivery-border); } } }
.stage-panel { padding: $spacing-6; min-height: $spacing-16 * 4; > svg { color: var(--delivery-accent); margin-bottom: $spacing-3; } h2 { font-size: $font-size-lg; line-height: $line-height-normal; margin-bottom: $spacing-3; } p { min-height: $spacing-16; color: var(--text-secondary); font-size: $font-size-sm; line-height: $line-height-relaxed; } code { display: block; margin-top: $spacing-4; padding: $spacing-3; color: var(--delivery-accent); background: var(--bg-primary); border-radius: var(--radius-md); font-size: $font-size-xs; white-space: normal; overflow-wrap: anywhere; } }
.preview-footer { border-top: 1px solid var(--delivery-border); flex-wrap: wrap; > svg { color: var(--delivery-accent); } > span { margin-left: auto; } }
.split-section { grid-template-columns: minmax(0, 0.8fr) minmax(0, 1.2fr); gap: $spacing-16; border-top: 1px solid var(--delivery-border); scroll-margin-top: $spacing-6; }
.intro h2 { margin-block: $spacing-4; font-size: var(--landing-heading); line-height: 1.3; font-weight: $font-weight-semibold; }
.intro p { max-width: 50ch; color: var(--text-secondary); font-size: $font-size-sm; line-height: $line-height-relaxed; }
.rows { list-style: none; li, article { display: flex; gap: $spacing-4; padding-block: $spacing-6; border-bottom: 1px solid var(--delivery-border); &:first-child { padding-top: 0; } > div { flex: 1; min-width: 0; } > svg { color: var(--text-tertiary); } } h3 { font-size: $font-size-lg; line-height: $line-height-normal; font-weight: $font-weight-medium; } p { margin-block: $spacing-2 $spacing-3; color: var(--text-secondary); font-size: $font-size-sm; line-height: $line-height-relaxed; } small { color: var(--delivery-accent); font-size: $font-size-xs; } }
.number { color: var(--delivery-accent); font-family: var(--font-family-mono); font-size: $font-size-xs; line-height: $line-height-normal; }
.statement { display: flex; flex-wrap: wrap; justify-content: space-between; gap: $spacing-8; padding: var(--landing-space) max(var(--landing-gutter), calc((100% - var(--landing-width)) / 2 + var(--landing-gutter))); background: var(--delivery-panel); border-block: 1px solid var(--delivery-border); > p { font-size: var(--landing-display); line-height: 1.3; font-weight: $font-weight-semibold; span { color: var(--delivery-accent); } } > div { align-self: flex-end; > p { margin-bottom: $spacing-6; color: var(--text-secondary); font-size: $font-size-sm; line-height: $line-height-relaxed; } } }
.faq { border-top: 0; details { border-bottom: 1px solid var(--delivery-border); padding-block: $spacing-4; &:first-child { padding-top: 0; } summary { display: flex; align-items: center; justify-content: space-between; gap: $spacing-4; list-style: none; font-size: $font-size-sm; font-weight: $font-weight-medium; cursor: pointer; min-height: var(--delivery-touch-target); &::-webkit-details-marker { display: none; } svg { color: var(--text-tertiary); } } &[open] summary svg { transform: rotate(45deg); } p { color: var(--text-secondary); font-size: $font-size-sm; line-height: $line-height-relaxed; margin-block: $spacing-2 $spacing-4; max-width: 65ch; } } }
footer { display: flex; flex-wrap: wrap; align-items: center; gap: $spacing-6; max-width: var(--landing-width); padding: $spacing-8 var(--landing-gutter); margin-inline: auto; border-top: 1px solid var(--delivery-border); > a:not(.brand) { margin-left: auto; display: inline-flex; align-items: center; gap: $spacing-2; color: var(--delivery-accent); font-size: $font-size-sm; } > span { width: 100%; color: var(--text-tertiary); font-size: $font-size-xs; } }
@media (max-width: 960px) { .landing-page { --landing-gutter: 24px; --landing-space: 64px; --landing-display: 36px; --landing-heading: 30px; } .hero { gap: $spacing-6; } .split-section { gap: $spacing-8; } .nav-links { gap: $spacing-4; } .brand > small { display: none; } }
@media (max-width: 720px) { .landing-page { --landing-gutter: 16px; --landing-space: 48px; } .hero, .split-section { grid-template-columns: minmax(0, 1fr); gap: $spacing-8; } .nav-links { display: none; } nav > :nth-last-child(2) { margin-left: auto; } nav > a:last-child { min-height: var(--delivery-touch-target); display: inline-flex; align-items: center; } .preview-app, .preview-heading, .preview-footer, .stage-panel { padding: $spacing-4; } .stage-tabs { padding-inline: $spacing-4; } .preview-footer > span { margin-left: 0; flex-basis: 100%; } footer .brand { flex-basis: 100%; } footer > a:not(.brand) { margin-left: 0; } }
</style>
