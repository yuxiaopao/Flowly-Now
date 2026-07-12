<template>
  <div
    class="nl-avatar"
    :class="[`nl-avatar-${role}`, sizeClass]"
  >
    <img
      v-if="role === 'assistant'"
      :src="currentLogo"
      alt="Flowly AI"
      class="nl-avatar-img"
    >
    <img
      v-else-if="role === 'user' && authStore.user?.avatar"
      :src="authStore.user.avatar"
      :alt="authStore.user?.username"
      class="nl-avatar-img"
    >
    <span
      v-else-if="role === 'user'"
      class="nl-avatar-initial"
    >
      {{ authStore.user?.username?.[0]?.toUpperCase() || 'U' }}
    </span>
    <Sparkles
      v-else
      class="nl-avatar-svg"
    />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useAppStore } from '@/stores/app'
import { useAuthStore } from '@/stores/auth'
import logoBlack from '@/assets/logos/logo.png'
import logoWhite from '@/assets/logos/logow.png'
import { Sparkles } from 'lucide-vue-next'

const props = defineProps({
  role: {
    type: String,
    default: 'assistant',
    validator: (v) => ['assistant', 'user', 'system'].includes(v)
  },
  size: {
    type: String,
    default: 'md'
  }
})

const appStore = useAppStore()
const authStore = useAuthStore()

const darkThemes = ['dark', 'pure-bw', 'high-contrast']
const currentLogo = computed(() =>
  darkThemes.includes(appStore.theme) ? logoWhite : logoBlack
)

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

    .nl-avatar-img,
    .nl-avatar-svg {
      max-width: 100%;
      max-height: 100%;
      object-fit: contain;
    }

    .nl-avatar-initial {
      font-size: 10px;
    }
  }

  &.size-md {
    width: 36px;
    height: 36px;

    .nl-avatar-img,
    .nl-avatar-svg {
      max-width: 100%;
      max-height: 100%;
      object-fit: contain;
    }

    .nl-avatar-initial {
      font-size: 13px;
    }
  }

  &.size-lg {
    width: 44px;
    height: 44px;

    .nl-avatar-img,
    .nl-avatar-svg {
      max-width: 100%;
      max-height: 100%;
      object-fit: contain;
    }

    .nl-avatar-initial {
      font-size: 16px;
    }
  }

  &.nl-avatar-assistant {
    background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-primary-light) 100%);
    box-shadow: 0 2px 8px var(--color-primary-shadow, rgba(6, 182, 212, 0.3));
    padding: 2px;

    .nl-avatar-img {
      border-radius: 9999px;
      object-fit: contain;
      background: transparent;
    }
  }

  &.nl-avatar-user {
    background-color: var(--bg-tertiary);
    color: var(--text-secondary);

    .nl-avatar-img {
      border-radius: 9999px;
      object-fit: cover;
    }

    .nl-avatar-initial {
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 700;
      color: var(--text-secondary);
      line-height: 1;
    }
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
