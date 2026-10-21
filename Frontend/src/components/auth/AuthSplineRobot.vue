<template>
  <div
    ref="rootRef"
    class="auth-spline-robot"
    :class="{ 'auth-spline-robot--interactive': interactive }"
    aria-hidden="true"
  >
    <canvas
      ref="canvasRef"
      class="auth-spline-robot__canvas"
    />
    <div
      v-if="loading"
      class="auth-spline-robot__hint"
    >
      正在加载 3D 机器人…
    </div>
    <div
      v-else-if="error"
      class="auth-spline-robot__hint auth-spline-robot__hint--error"
    >
      {{ error }}
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, nextTick } from 'vue'
import {
  SPLINE_SCENE_URL,
  bindSplineResize,
  bindSplineVisibility,
  createSplineApplication,
  disposeSplineApplication,
  resolveSplineErrorMessage,
  waitForElementSize,
} from '@/utils/splineLoader'

defineProps({
  /** 启用鼠标交互（Spline 场景内 Look At / Follow 等） */
  interactive: {
    type: Boolean,
    default: true,
  },
})

const rootRef = ref(null)
const canvasRef = ref(null)
const loading = ref(true)
const error = ref('')

let splineApp = null
let cleanupResize = null
let cleanupVisibility = null
let disposed = false

async function initSpline() {
  await nextTick()

  const canvas = canvasRef.value
  const container = rootRef.value
  if (!canvas || !container) return

  if (!SPLINE_SCENE_URL) {
    loading.value = false
    error.value = '未配置 3D 场景地址'
    return
  }

  try {
    await waitForElementSize(container)
    if (disposed) return
    const app = await createSplineApplication(canvas, container, SPLINE_SCENE_URL)
    if (disposed) { disposeSplineApplication(app); return }
    splineApp = app
    splineApp.play?.()
    cleanupResize = bindSplineResize(splineApp, canvas, container)
    cleanupVisibility = bindSplineVisibility(splineApp)
    loading.value = false
  } catch (err) {
    if (disposed) return
    console.error('Spline 加载失败:', err)
    loading.value = false
    error.value = resolveSplineErrorMessage(err)
  }
}

onMounted(() => {
  initSpline()
})

onBeforeUnmount(() => {
  disposed = true
  cleanupResize?.()
  cleanupResize = null
  cleanupVisibility?.()
  cleanupVisibility = null
  disposeSplineApplication(splineApp)
  splineApp = null
})
</script>

<style lang="scss" scoped>
.auth-spline-robot {
  position: absolute;
  inset: 0;
  z-index: 1;
  overflow: hidden;
  pointer-events: none;

  &--interactive {
    pointer-events: auto;

    .auth-spline-robot__canvas {
      pointer-events: auto;
    }
  }

  &__canvas {
    display: block;
    width: 100% !important;
    height: 100% !important;
    pointer-events: none;
  }

  &__hint {
    position: absolute;
    left: 50%;
    bottom: 24px;
    transform: translateX(-50%);
    z-index: 2;
    font-size: 12px;
    color: var(--text-tertiary);
    pointer-events: none;
    transition: opacity 0.4s ease;

    &--error {
      color: var(--warning);
    }
  }
}

@media (max-width: 768px) {
  .auth-spline-robot__hint {
    bottom: 16px;
  }
}
</style>
