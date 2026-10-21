<template>
  <div
    class="nl-avatar"
    :class="[`nl-avatar-${role}`, sizeClass]"
  >
    <FlowlyBot
      v-if="role === 'assistant'"
      :size="avatarSize * BOT_AVATAR.compactScale"
      :state="state"
      :animated="animated"
    />
    <AccountAvatar
      v-else-if="role === 'user'"
      :size="avatarSize"
      :animated="false"
    />
    <Sparkles
      v-else
      class="nl-avatar-svg"
    />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import AccountAvatar from '@/components/common/AccountAvatar.vue'
import FlowlyBot from '@/components/common/FlowlyBot.vue'
import { BOT_AVATAR } from '@/config/botAvatar'
import { Sparkles } from 'lucide-vue-next'

const props = defineProps({
  role: {
    type: String,
    default: 'assistant',
    validator: (v) => ['assistant', 'user', 'system'].includes(v)
  },
  size: {
    type: String,
    default: 'md',
    validator: (value) => Object.hasOwn(BOT_AVATAR.sizes, value)
  },
  state: { type: String, default: 'idle' },
  animated: { type: Boolean, default: false }
})

const avatarSize = computed(() => BOT_AVATAR.sizes[props.size] || BOT_AVATAR.sizes.md)
const sizeClass = computed(() => `size-${props.size}`)
</script>

<style scoped lang="scss">
$root: '.nl-avatar';

#{$root} {
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 9999px;
  flex-shrink: 0;
  overflow: hidden;

  &.size-sm {
    width: 28px;
    height: 28px;

    .nl-avatar-svg {
      max-width: 100%;
      max-height: 100%;
      object-fit: contain;
    }
  }

  &.size-md {
    width: 36px;
    height: 36px;

    .nl-avatar-svg {
      max-width: 100%;
      max-height: 100%;
      object-fit: contain;
    }
  }

  &.size-lg {
    width: 44px;
    height: 44px;

    .nl-avatar-svg {
      max-width: 100%;
      max-height: 100%;
      object-fit: contain;
    }
  }

  &.nl-avatar-assistant {
    overflow: visible;
  }

  &.nl-avatar-user {
    background-color: var(--bg-tertiary);
    color: var(--text-secondary);
  }

  &.nl-avatar-system {
    background-color: var(--color-primary-10);
    color: var(--color-primary);

    .nl-avatar-svg {
      width: 16px;
      height: 16px;
      color: var(--color-primary);
    }
  }
}
</style>
