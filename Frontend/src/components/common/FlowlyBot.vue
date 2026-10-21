<template>
  <svg
    ref="svg"
    class="flowly-bot"
    :width="size"
    :height="size"
    :viewBox="`${-VB} ${-VB} ${VB * 2} ${VB * 2}`"
    :role="decorative ? undefined : 'img'"
    :aria-hidden="decorative ? 'true' : undefined"
    :aria-label="decorative ? undefined : accessibleLabel"
    :data-bot-state="resolvedState"
    :data-bot-animated="running"
    :data-bot-shape="shape || undefined"
    :data-bot-expression="expression || undefined"
    :style="{ color }"
    focusable="false"
  >
    <defs>
      <mask
        :id="maskId"
        maskUnits="userSpaceOnUse"
        :x="-VB"
        :y="-VB"
        :width="VB * 2"
        :height="VB * 2"
      >
        <path
          :d="frame.bodyPath"
          :fill="BOT_AVATAR.maskWhite"
        />
        <path
          v-for="(eye, index) in frame.eyes"
          :key="index"
          :d="eye.d"
          :transform="eye.matrix"
          :opacity="eye.alpha"
          :fill="BOT_AVATAR.maskBlack"
        />
        <circle
          v-if="frame.notch"
          :cx="frame.notch.x"
          :cy="frame.notch.y"
          :r="frame.notch.r"
          :fill="BOT_AVATAR.maskBlack"
        />
      </mask>
      <linearGradient
        v-for="arc in frame.arcs"
        :id="`${uid}-${arc.id}`"
        :key="arc.id"
        gradientUnits="userSpaceOnUse"
        :x1="arc.grad.x1"
        :y1="arc.grad.y1"
        :x2="arc.grad.x2"
        :y2="arc.grad.y2"
      >
        <stop
          v-for="(colorStop, index) in arc.grad.stops"
          :key="index"
          :offset="index / (arc.grad.stops.length - 1)"
          :stop-color="colorStop"
        />
      </linearGradient>
    </defs>
    <g
      fill="none"
      stroke-linecap="round"
    >
      <path
        v-for="arc in frame.arcs"
        :key="`back-${arc.id}`"
        :d="arc.back"
        :stroke="`url(#${uid}-${arc.id})`"
        :stroke-width="arc.width"
        :opacity="arc.opacity"
      />
    </g>
    <g v-if="frame.dotsBehind">
      <component
        :is="dot.d ? 'path' : 'circle'"
        v-for="(dot, index) in frame.dots"
        :key="index"
        v-bind="dotAttributes(dot)"
      />
    </g>
    <g :opacity="frame.bodyAlpha">
      <path
        v-if="!transparentEyes"
        :d="frame.bodyPath"
        :fill="eyeColor"
      />
      <g :mask="`url(#${maskId})`">
        <rect
          :x="-VB"
          :y="-VB"
          :width="VB * 2"
          :height="VB * 2"
          fill="currentColor"
        />
      </g>
    </g>
    <g v-if="!frame.dotsBehind">
      <component
        :is="dot.d ? 'path' : 'circle'"
        v-for="(dot, index) in frame.dots"
        :key="index"
        v-bind="dotAttributes(dot)"
      />
    </g>
    <circle
      v-if="frame.notif"
      :cx="frame.notif.x"
      :cy="frame.notif.y"
      :r="frame.notif.r"
      :fill="NOTIF_BLUE"
    />
    <g
      fill="none"
      stroke-linecap="round"
    >
      <path
        v-for="arc in frame.arcs"
        :key="`front-${arc.id}`"
        :d="arc.front"
        :stroke="`url(#${uid}-${arc.id})`"
        :stroke-width="arc.width"
        :opacity="arc.opacity"
      />
    </g>
  </svg>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, shallowRef, triggerRef, watch } from 'vue'
import { BOT_AVATAR } from '@/config/botAvatar'
import { createBotAvatarId, resolveBotState } from '@/utils/botAvatar'
import { BotEngine } from '@/vendor/bloub/engine'
import { NOTIF_BLUE } from '@/vendor/bloub/decor'
import { RAYON, DEMI_VIEWBOX as VB } from '@/vendor/bloub/repere'
import { POSES, STATE_BY_ID } from '@/vendor/bloub/states'
import { clamp } from '@/vendor/bloub/math'
import { SHAPE_BY_ID } from '@/vendor/bloub/skins'
import { EXPRESSION_BY_ID } from '@/vendor/bloub/expressions'
import { ACCOUNT_AVATAR } from '@/config/accountAvatar'

const props = defineProps({
  state: { type: String, default: 'idle' },
  size: { type: Number, default: BOT_AVATAR.size },
  animated: { type: Boolean, default: true },
  follow: { type: Boolean, default: false },
  decorative: { type: Boolean, default: false },
  label: { type: String, default: '' },
  color: { type: String, default: BOT_AVATAR.color },
  shape: { type: String, default: '' },
  expression: { type: String, default: '' },
  transparentEyes: { type: Boolean, default: false },
  eyeColor: { type: String, default: BOT_AVATAR.eyes },
  blocks: { type: Array, default: () => [] },
})

const svg = ref(null)
const cycleState = ref(null)
const cycleBlocks = computed(() => props.blocks.slice(0, ACCOUNT_AVATAR.maxBlocks).filter(block => block && STATE_BY_ID.has(block.state) && Number.isFinite(block.duration) && block.duration >= ACCOUNT_AVATAR.minDuration && block.duration <= ACCOUNT_AVATAR.maxDuration))
const resolvedState = computed(() => resolveBotState(cycleState.value || props.state))
const accessibleLabel = computed(() => props.label || `${BOT_AVATAR.name} · ${BOT_AVATAR.labels[props.state] || props.state}`)
const engine = new BotEngine(RAYON, resolvedState.value, SHAPE_BY_ID.get(props.shape)?.radii || null, EXPRESSION_BY_ID.get(props.expression) || null)
const frame = shallowRef(engine.sample(POSES[resolvedState.value]))
const uid = createBotAvatarId()
const maskId = `${uid}-mask`
const running = ref(false)
const reducedMotion = ref(false)
const visible = ref(true)
const pageVisible = ref(true)
let mounted = false
let observer
let motionQuery
let raf = 0
let lastTick = null
let lastRender = 0
let clock = 0
let stateStart = 0
let cycleIndex = 0
let cycleStart = 0

function render() {
  frame.value = engine.sample(clock)
  triggerRef(frame)
}

function stop() {
  cancelAnimationFrame(raf)
  raf = 0
  lastTick = null
  running.value = false
}

function syncPlayback() {
  if (!mounted) return
  stop()
  if (!props.animated || reducedMotion.value) {
    engine.reset(resolvedState.value, clock - POSES[resolvedState.value])
    render()
    return
  }
  if (visible.value && pageVisible.value) {
    running.value = true
    raf = requestAnimationFrame(tick)
  }
}

function tick(timestamp) {
  if (!running.value) return
  if (lastTick !== null) {
    clock += Math.min((timestamp - lastTick) * BOT_AVATAR.secondsPerMillisecond, BOT_AVATAR.maxFrameStepSeconds)
  }
  lastTick = timestamp
  if (timestamp - lastRender >= BOT_AVATAR.frameIntervalMs) {
    lastRender = timestamp
    const definition = STATE_BY_ID.get(resolvedState.value)
    const sequence = cycleBlocks.value
    if (sequence.length && clock - cycleStart >= sequence[cycleIndex].duration) {
      cycleStart += sequence[cycleIndex].duration
      cycleIndex = (cycleIndex + 1) % sequence.length
      const nextState = sequence[cycleIndex].state
      if (nextState === resolvedState.value) engine.reset(nextState, cycleStart)
      cycleState.value = nextState
    }
    if (!sequence.length && !definition.baseFace && clock - stateStart >= definition.duration) {
      engine.reset(resolvedState.value, clock)
      stateStart = clock
    }
    render()
  }
  raf = requestAnimationFrame(tick)
}

function updateGaze(event) {
  if (!props.follow || !running.value || !STATE_BY_ID.get(resolvedState.value).baseFace || event.pointerType === 'touch') return
  const box = svg.value?.getBoundingClientRect()
  if (!box?.width || !box?.height) return
  const pointer = { x: event.clientX, y: event.clientY }
  engine.setLook({
    yaw: clamp((pointer.x - box.left - box.width / 2) / Math.max(window.innerWidth / 2, 1), -1, 1) * BOT_AVATAR.gaze.yaw,
    pitch: BOT_AVATAR.gaze.restPitch - clamp((pointer.y - box.top - box.height / 2) / Math.max(window.innerHeight / 2, 1), -1, 1) * BOT_AVATAR.gaze.pitch,
    mix: 1,
    spin: 0,
    wander: 0,
  }, clock)
}

function releaseGaze() {
  engine.setLook(null, clock)
}

function onMotionChange(event) {
  reducedMotion.value = event.matches
}

function onVisibilityChange() {
  pageVisible.value = !document.hidden
}

function dotAttributes(dot) {
  const color = dot.depth === undefined
    ? 'currentColor'
    : `color-mix(in srgb, ${BOT_AVATAR.paper} ${(1 - dot.depth) * 100}%, currentColor)`
  const common = { fill: dot.color || color, opacity: dot.opacity }
  return dot.d
    ? { ...common, d: dot.d, transform: `translate(${dot.x} ${dot.y}) rotate(${dot.rot || 0}) scale(${RAYON})` }
    : { ...common, cx: dot.x, cy: dot.y, r: dot.r }
}

watch(resolvedState, (state) => {
  releaseGaze()
  if (!props.animated || reducedMotion.value) engine.reset(state, clock - POSES[state])
  else engine.setState(state, clock)
  stateStart = clock
  render()
})
watch([() => props.animated, reducedMotion, visible, pageVisible], syncPlayback)
watch(() => props.follow, (follow) => { if (!follow) releaseGaze() })
watch(cycleBlocks, (blocks) => {
  cycleIndex = 0
  cycleStart = clock
  if (blocks.length && blocks[0].state === resolvedState.value) {
    engine.reset(resolvedState.value, clock)
    render()
  }
  cycleState.value = blocks[0]?.state || null
}, { immediate: true })
watch([() => props.shape, () => props.expression], () => {
  const now = props.animated && !reducedMotion.value ? clock : clock - BOT_AVATAR.staticMorphSeconds
  engine.setShape(SHAPE_BY_ID.get(props.shape)?.radii || null, now)
  engine.setExpression(EXPRESSION_BY_ID.get(props.expression) || null, now)
  render()
})

onMounted(() => {
  mounted = true
  motionQuery = window.matchMedia(BOT_AVATAR.reducedMotionQuery)
  reducedMotion.value = motionQuery.matches
  motionQuery.addEventListener('change', onMotionChange)
  pageVisible.value = !document.hidden
  document.addEventListener('visibilitychange', onVisibilityChange)
  window.addEventListener('pointermove', updateGaze, { passive: true })
  document.addEventListener('pointerleave', releaseGaze)
  if ('IntersectionObserver' in window) {
    observer = new IntersectionObserver(([entry]) => { visible.value = entry.isIntersecting })
    observer.observe(svg.value)
  }
  syncPlayback()
})

onBeforeUnmount(() => {
  mounted = false
  stop()
  observer?.disconnect()
  motionQuery?.removeEventListener('change', onMotionChange)
  document.removeEventListener('visibilitychange', onVisibilityChange)
  window.removeEventListener('pointermove', updateGaze)
  document.removeEventListener('pointerleave', releaseGaze)
})
</script>

<style scoped>
.flowly-bot {
  display: block;
  flex-shrink: 0;
  overflow: visible;
  pointer-events: none;
}
</style>
