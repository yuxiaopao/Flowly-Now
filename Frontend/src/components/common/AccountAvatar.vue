<template>
  <span
    class="account-avatar"
    :style="{ width: `${size}px`, height: `${size}px`, '--account-avatar-scale': ACCOUNT_AVATAR.iconScale }"
    :data-account-avatar="usingImage ? 'image' : 'robot'"
    role="img"
    :aria-label="usingImage ? ACCOUNT_AVATAR.imageLabel : ACCOUNT_AVATAR.robotLabel"
  >
    <img
      v-if="usingImage"
      class="account-avatar-image"
      :src="authStore.user.avatar"
      alt=""
      @error="imageFailed = true"
    >
    <FlowlyBot
      v-else
      class="account-avatar-bot"
      :size="size"
      :shape="settings.shape"
      :expression="settings.expression"
      :color="colors.body"
      :eye-color="colors.eyes"
      :blocks="settings.blocks"
      :animated="animated"
      :follow="animated"
      decorative
    />
  </span>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useAppStore } from '@/stores/app'
import FlowlyBot from './FlowlyBot.vue'
import { ACCOUNT_AVATAR } from '@/config/accountAvatar'
import { readAccountAvatar, resolveAccountAvatarColors } from '@/utils/accountAvatar'

defineProps({ size: { type: Number, default: ACCOUNT_AVATAR.headerSize }, animated: { type: Boolean, default: true } })
const authStore = useAuthStore()
const appStore = useAppStore()
const imageFailed = ref(false)
const settings = computed(() => readAccountAvatar(authStore.user))
const colors = computed(() => resolveAccountAvatarColors(settings.value.color, appStore.theme))
const usingImage = computed(() => settings.value.mode === 'image' && authStore.user?.avatar && !imageFailed.value)
watch(() => authStore.user?.avatar, () => { imageFailed.value = false })
</script>

<style scoped>
.account-avatar { display: inline-grid; place-items: center; flex-shrink: 0; background: transparent; border: none; }
.account-avatar-image { display: block; width: 100%; height: 100%; object-fit: cover; border-radius: var(--radius-md, 8px); }
.account-avatar-bot { transform: scale(var(--account-avatar-scale)); }
</style>
