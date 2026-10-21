<template>
  <div class="voice-recorder">
    <button
      ref="trigger"
      type="button"
      class="voice-trigger"
      :class="{ 'has-recording': modelValue, 'is-recording': state === 'recording' }"
      :aria-label="modelValue || busy ? copy.open : copy.start"
      :title="modelValue || busy ? copy.open : copy.start"
      :aria-expanded="showPanel"
      :disabled="disabled && !modelValue && !busy"
      @click="openRecorder"
    >
      <Mic :size="18" />
    </button>
    <section
      v-if="showPanel"
      class="voice-panel"
      :aria-label="copy.title"
      @keydown.esc.stop="closePanel"
    >
      <header>
        <strong>{{ copy.title }}</strong><button
          v-if="!busy"
          type="button"
          :aria-label="copy.close"
          @click="closePanel"
        >
          <X :size="16" />
        </button>
      </header>
      <div
        v-if="busy"
        class="voice-status"
        role="status"
      >
        <span :class="{ 'recording-dot': state === 'recording' }" />
        <span>{{ copy[state] }}</span><time v-if="state === 'recording'">{{ recordingTime(elapsed) }}</time>
      </div>
      <p
        v-if="error"
        class="voice-error"
        role="alert"
      >
        {{ error }}
      </p>
      <template v-if="modelValue && !busy">
        <audio
          ref="player"
          :src="audioUrl"
          controls
          preload="metadata"
          :aria-label="copy.title"
          @error="error = config.errors.playback"
        />
        <div class="voice-file">
          <span>{{ recordingTime(modelValue.durationMs) }}</span><a
            :href="audioUrl"
            :download="recordingFilename(modelValue)"
            @click="markDownloaded"
          ><Download :size="14" />{{ copy.download }}</a>
        </div>
      </template>
      <p class="voice-caption">
        {{ busy ? copy.limit : copy.localOnly }}
      </p>
      <footer>
        <button
          v-if="state === 'recording'"
          type="button"
          class="voice-stop"
          @click="capture.stop"
        >
          <Square :size="14" />{{ copy.stop }}
        </button>
        <button
          v-if="busy"
          type="button"
          @click="cancelRecording"
        >
          {{ copy.cancel }}
        </button>
        <template v-else>
          <button
            type="button"
            :disabled="disabled"
            @click="startRecording"
          >
            <Mic :size="14" />{{ modelValue ? copy.retry : copy.start }}
          </button>
          <button
            v-if="modelValue"
            type="button"
            @click="removeRecording"
          >
            <Trash2 :size="14" />{{ copy.remove }}
          </button>
        </template>
      </footer>
    </section>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { Download, Mic, Square, Trash2, X } from 'lucide-vue-next'
import { VOICE_RECORDER as config } from '@/config/voiceRecorder'
import { createVoiceRecorder, recordingFilename, recordingTime } from '@/utils/voiceRecorder'

const props = defineProps({ modelValue: { type: Object, default: null }, disabled: Boolean })
const emit = defineEmits(['update:modelValue', 'busy-change'])
const copy = config.labels
const state = ref('idle')
const elapsed = ref(0)
const error = ref('')
const audioUrl = ref('')
const showPanel = ref(false)
const trigger = ref(null)
const player = ref(null)
const busy = computed(() => state.value !== 'idle')
const capture = createVoiceRecorder({
  onState: value => { state.value = value; emit('busy-change', value !== 'idle') },
  onElapsed: value => { elapsed.value = value },
  onError: value => { error.value = value },
  onComplete: value => { emit('update:modelValue', value) },
})
watch(() => props.modelValue?.blob, blob => {
  player.value?.pause()
  if (audioUrl.value) URL.revokeObjectURL(audioUrl.value)
  audioUrl.value = blob ? URL.createObjectURL(blob) : ''
}, { immediate: true })
function startRecording() { error.value = ''; player.value?.pause(); capture.start() }
function openRecorder() { showPanel.value = true; if (!props.modelValue && !busy.value) startRecording() }
async function closePanel() {
  if (busy.value) return
  player.value?.pause()
  showPanel.value = false
  await nextTick()
  trigger.value?.focus()
}
function cancelRecording() { capture.cancel(); error.value = ''; closePanel() }
function removeRecording() { emit('update:modelValue', null); error.value = ''; closePanel() }
function markDownloaded() { emit('update:modelValue', { ...props.modelValue, downloaded: true }) }
onBeforeUnmount(() => {
  player.value?.pause()
  capture.dispose()
  if (audioUrl.value) URL.revokeObjectURL(audioUrl.value)
})
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;
.voice-recorder { display: flex; align-items: center; }
button { display: inline-flex; align-items: center; justify-content: center; gap: $spacing-1; background: transparent; border: 0; border-radius: $radius-md; padding: $spacing-2; color: var(--text-secondary); cursor: pointer; font: inherit;
  &:hover:not(:disabled) { background: var(--bg-hover); color: var(--text-primary); }
  &:disabled { opacity: .5; cursor: not-allowed; }
  &:focus-visible { outline: 2px solid var(--color-primary); outline-offset: 2px; }
}
.voice-trigger { width: $spacing-8; height: $spacing-8; position: relative;
  &.is-recording { color: var(--color-error); }
  &.has-recording::after { content: ''; position: absolute; top: $spacing-1; right: $spacing-1; width: $spacing-1; height: $spacing-1; background: var(--color-primary); border-radius: $radius-full; }
}
.voice-panel { position: absolute; bottom: calc(100% + #{$spacing-2}); right: 0; z-index: 4; width: min(100%, 360px); padding: $spacing-4; border: 1px solid var(--border-primary); border-radius: $radius-xl; background: var(--bg-secondary); box-shadow: $shadow-lg; font-size: $font-size-sm;
  header, footer { display: flex; align-items: center; justify-content: space-between; gap: $spacing-2; }
  header { margin-bottom: $spacing-3; color: var(--text-primary); }
  footer { justify-content: flex-end; margin-top: $spacing-3; }
  audio { width: 100%; height: $spacing-10; }
  .voice-stop { color: var(--color-error); background: var(--bg-tertiary); }
}
.voice-status, .voice-file { display: flex; align-items: center; gap: $spacing-2; color: var(--text-primary); time { margin-left: auto; font-variant-numeric: tabular-nums; } }
.recording-dot { width: $spacing-2; height: $spacing-2; background: var(--color-error); border-radius: $radius-full; }
.voice-file { justify-content: space-between; margin-top: $spacing-2; font-size: $font-size-xs; a { display: inline-flex; align-items: center; gap: $spacing-1; color: var(--text-primary); } }
.voice-caption { font-size: $font-size-xs; color: var(--text-secondary); line-height: $line-height-normal; margin: $spacing-3 0 0; }
.voice-error { color: var(--color-error); overflow-wrap: anywhere; line-height: $line-height-relaxed; }
</style>
