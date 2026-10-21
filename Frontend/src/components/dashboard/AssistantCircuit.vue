<template>
  <div
    class="assistant-circuit"
    role="group"
    :aria-label="`${AI_WORKBENCH.label}：${AI_WORKBENCH.subtitle}`"
  >
    <svg
      class="assistant-circuit__connections"
      viewBox="0 0 440 224"
      preserveAspectRatio="none"
      fill="none"
      aria-hidden="true"
    >
      <path
        class="circuit-line circuit-line--violet"
        d="M132 56 H158 Q174 56 174 72 V96 Q174 112 190 112 H220"
      />
      <path
        class="circuit-line circuit-line--cyan"
        d="M220 112 H262 Q278 112 278 96 V52 H310"
      />
      <path
        class="circuit-line circuit-line--blue"
        d="M220 112 H262 Q278 112 278 128 V172 H310"
      />
      <path
        class="circuit-signal circuit-line--violet"
        pathLength="100"
        d="M132 56 H158 Q174 56 174 72 V96 Q174 112 190 112 H220"
      />
      <path
        class="circuit-signal circuit-line--cyan"
        pathLength="100"
        d="M220 112 H262 Q278 112 278 96 V52 H310"
      />
      <path
        class="circuit-signal circuit-line--blue"
        pathLength="100"
        d="M220 112 H262 Q278 112 278 128 V172 H310"
      />
      <circle
        cx="174"
        cy="80"
        r="3"
        class="circuit-junction circuit-line--violet"
      />
      <circle
        cx="278"
        cy="82"
        r="3"
        class="circuit-junction circuit-line--cyan"
      />
      <circle
        cx="278"
        cy="150"
        r="3"
        class="circuit-junction circuit-line--blue"
      />
    </svg>

    <router-link
      v-for="capability in AI_WORKBENCH.capabilities"
      :key="capability.id"
      :to="capability.route"
      class="assistant-circuit__node"
      :class="[`assistant-circuit__node--${capability.id}`, `assistant-circuit__node--${capability.tone}`]"
    >
      <component
        :is="icons[capability.icon]"
        aria-hidden="true"
      />
      <span>
        <strong>{{ capability.label }}</strong>
        <small>{{ capability.detail }}</small>
      </span>
    </router-link>

    <div class="assistant-circuit__center">
      <button
        type="button"
        class="assistant-circuit__core assistant-welcome__bot"
        :aria-label="BOT_AVATAR.home.greetingLabel"
        @click="$emit('greet')"
      >
        <FlowlyBot
          :size="BOT_AVATAR.heroSize"
          :state="state"
          follow
          decorative
        />
      </button>
      <span class="assistant-circuit__name">{{ AI_WORKBENCH.coreLabel }}</span>
    </div>
  </div>
</template>

<script setup>
import { Cpu, Database, GitBranch } from 'lucide-vue-next'
import FlowlyBot from '@/components/common/FlowlyBot.vue'
import { AI_WORKBENCH } from '@/config/productUi'
import { BOT_AVATAR } from '@/config/botAvatar'

defineProps({ state: { type: String, default: 'idle' } })
defineEmits(['greet'])
const icons = { Cpu, Database, GitBranch }
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.assistant-circuit {
  position: relative;
  width: 100%;
  max-width: 440px;
  height: var(--tech-circuit-height);
  margin-inline: auto;
  isolation: isolate;
  container: assistant-circuit / inline-size;

  &__connections { position: absolute; inset: 0; width: 100%; height: 100%; pointer-events: none; }
  &__node {
    --circuit-accent: var(--tech-blue);
    --circuit-soft: var(--tech-blue-soft);
    position: absolute;
    display: flex;
    align-items: center;
    gap: $spacing-2;
    width: var(--tech-circuit-node-width);
    padding: $spacing-3;
    border: 1px solid color-mix(in srgb, var(--circuit-accent) 32%, var(--border-primary));
    border-radius: $radius-xl;
    background: var(--bg-secondary);
    box-shadow: inset 0 1px 0 var(--circuit-soft), var(--shadow-sm);
    color: var(--text-primary);
    transition: border-color $transition-fast, box-shadow $transition-fast, background $transition-fast;
    svg { width: $spacing-5; height: $spacing-5; flex-shrink: 0; color: var(--circuit-accent); }
    span { display: flex; flex-direction: column; gap: $spacing-1; min-width: 0; }
    strong { font-size: $font-size-xs; font-weight: $font-weight-semibold; }
    small { font-size: $font-size-xs; color: var(--text-secondary); white-space: nowrap; }
    &:hover, &:focus-visible {
      opacity: 1;
      border-color: var(--circuit-accent);
      background: color-mix(in srgb, var(--circuit-soft) 30%, var(--bg-secondary));
      box-shadow: 0 0 20px var(--circuit-soft);
    }
    &--models { top: 12%; left: 0; }
    &--knowledge { top: 10%; right: 0; }
    &--workflows { bottom: 10%; right: 0; }
    &--violet { --circuit-accent: var(--tech-violet); --circuit-soft: var(--tech-violet-soft); }
    &--cyan { --circuit-accent: var(--tech-cyan); --circuit-soft: var(--tech-cyan-soft); }
  }
  &__center {
    position: absolute; left: 50%; top: 50%; transform: translate(-50%, -50%);
    width: var(--tech-circuit-core-size); height: var(--tech-circuit-core-size);
    display: flex; flex-direction: column; align-items: center;
  }
  &__core {
    width: var(--tech-circuit-core-size); height: var(--tech-circuit-core-size);
    display: grid; place-items: center; border-radius: $radius-full;
    border: 1px solid var(--tech-border); background: var(--bg-secondary);
    box-shadow: 0 0 0 $spacing-3 var(--tech-blue-soft), 0 0 44px var(--tech-core-glow);
    transition: box-shadow $transition-fast, border-color $transition-fast;
    &:hover, &:focus-visible { border-color: var(--tech-blue); box-shadow: 0 0 0 $spacing-3 var(--tech-blue-soft), 0 0 56px var(--tech-core-glow); }
  }
  &__name { position: absolute; top: 100%; margin-top: $spacing-3; color: var(--text-secondary); font-size: $font-size-xs; }
}
.circuit-line { stroke: currentColor; stroke-width: 1.5; opacity: 0.35; }
.circuit-line--violet { color: var(--tech-violet); }
.circuit-line--cyan { color: var(--tech-cyan); }
.circuit-line--blue { color: var(--tech-blue); }
.circuit-junction { fill: currentColor; }
.circuit-signal {
  stroke: currentColor; stroke-width: 2; stroke-dasharray: 7 93;
  animation: circuit-connect var(--tech-circuit-loop-duration) linear 2;
  opacity: 0;
}
.assistant-circuit:hover .circuit-signal,
.assistant-circuit:focus-within .circuit-signal { animation-iteration-count: infinite; opacity: 0.9; }
@keyframes circuit-connect {
  0% { stroke-dashoffset: 100; opacity: 0; }
  20%, 80% { opacity: 0.85; }
  100% { stroke-dashoffset: 0; opacity: 0; }
}
@container assistant-circuit (max-width: 380px) {
  .assistant-circuit__node { width: 112px; padding: $spacing-2; gap: $spacing-1; svg { width: $spacing-4; height: $spacing-4; } }
  .assistant-circuit__center { --tech-circuit-core-size: 88px; left: 43%; top: 54%; }
  .assistant-circuit__core { --tech-circuit-core-size: 88px; }
  .assistant-circuit__node--models { top: 8%; }
  .assistant-circuit__node--knowledge { top: 8%; }
  .assistant-circuit__node--workflows { bottom: 0; }
}
@media (prefers-reduced-motion: reduce) {
  .circuit-signal { animation: none !important; opacity: 0 !important; }
}
</style>
