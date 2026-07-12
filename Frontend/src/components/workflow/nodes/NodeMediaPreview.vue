<template>
  <div
    class="node-media-preview"
    :class="[`node-media-preview--${kind}`, { 'node-media-preview--fill': fill }]"
    :style="containerStyle"
  >
    <img
      v-if="kind === 'image' && src"
      :src="src"
      class="node-media-preview__media"
      :alt="alt"
      referrerpolicy="no-referrer"
      @error="emit('error')"
      @click="emit('click')"
    >
    <video
      v-else-if="kind === 'video' && src"
      :src="src"
      class="node-media-preview__media"
      :poster="poster || undefined"
      muted
      autoplay
      playsinline
      loop
      preload="auto"
      referrerpolicy="no-referrer"
      @click="emit('click')"
    />
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  kind: {
    type: String,
    default: 'image',
    validator: (value) => ['image', 'video'].includes(value),
  },
  src: {
    type: String,
    default: '',
  },
  poster: {
    type: String,
    default: '',
  },
  alt: {
    type: String,
    default: 'Preview',
  },
  aspectRatio: {
    type: Number,
    default: null,
  },
  maxHeight: {
    type: Number,
    default: null,
  },
  fill: {
    type: Boolean,
    default: true,
  },
})

const emit = defineEmits(['error', 'click'])

const containerStyle = computed(() => {
  const style = {}
  if (props.aspectRatio && Number.isFinite(props.aspectRatio) && props.aspectRatio > 0) {
    style.aspectRatio = String(props.aspectRatio)
    style.width = '100%'
  }
  if (props.maxHeight) {
    style.maxHeight = `${props.maxHeight}px`
  }
  return style
})
</script>

<style lang="scss" scoped>
.node-media-preview {
  width: 100%;
  flex: 0 0 auto;
  min-height: 80px;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;

  &--fill {
    height: auto;
  }

  &__media {
    width: 100%;
    height: auto;
    max-width: 100%;
    max-height: 100%;
    object-fit: contain;
    display: block;
  }

  &--video &__media {
    background: #000;
    min-height: 120px;
  }
}
</style>
