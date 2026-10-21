import { ACCOUNT_AVATAR } from '@/config/accountAvatar'
import { COLOR_BY_ID, SHAPE_BY_ID } from '@/vendor/bloub/skins'
import { EXPRESSION_BY_ID } from '@/vendor/bloub/expressions'
import { STATE_BY_ID } from '@/vendor/bloub/states'
import { reactive } from 'vue'

const activePreferences = reactive({})

export function readAccountAvatar(user) {
  if (!user?.id) return normalizeAccountAvatar()
  const remote = user.avatarPreferences || user.avatar_preferences
  if (remote && typeof remote === 'object' && Object.keys(remote).length) return normalizeAccountAvatar(remote)
  if (!activePreferences[user.id]) {
    try { activePreferences[user.id] = normalizeAccountAvatar(JSON.parse(localStorage.getItem(`${ACCOUNT_AVATAR.storagePrefix}${user.id}`))) }
    catch { activePreferences[user.id] = normalizeAccountAvatar() }
  }
  return activePreferences[user.id]
}

export function persistAccountAvatar(userId, preferences) {
  if (!userId) return false
  const normalized = normalizeAccountAvatar(preferences)
  activePreferences[userId] = normalized
  try {
    localStorage.setItem(`${ACCOUNT_AVATAR.storagePrefix}${userId}`, JSON.stringify(normalized))
    return true
  } catch { return false }
}

export function normalizeAccountAvatar(value) {
  const source = value && typeof value === 'object' && !Array.isArray(value) ? value : {}
  const defaults = ACCOUNT_AVATAR.defaults
  return {
    mode: source.mode === 'image' ? 'image' : defaults.mode,
    shape: SHAPE_BY_ID.has(source.shape) ? source.shape : defaults.shape,
    color: COLOR_BY_ID.has(source.color) ? source.color : defaults.color,
    expression: EXPRESSION_BY_ID.has(source.expression) ? source.expression : defaults.expression,
    blocks: Array.isArray(source.blocks) ? source.blocks.slice(0, ACCOUNT_AVATAR.maxBlocks)
      .filter(block => block && STATE_BY_ID.has(block.state) && Number.isFinite(block.duration) && block.duration >= ACCOUNT_AVATAR.minDuration && block.duration <= ACCOUNT_AVATAR.maxDuration)
      .map(({ state, duration }) => ({ state, duration })) : [],
  }
}

export function resolveAccountAvatarColors(colorId, theme) {
  const selected = COLOR_BY_ID.get(colorId) || COLOR_BY_ID.get(ACCOUNT_AVATAR.defaults.color)
  if (ACCOUNT_AVATAR.monochromeColors.includes(selected.id)) {
    const dark = ACCOUNT_AVATAR.darkThemes.includes(theme)
    return { body: dark ? ACCOUNT_AVATAR.lightBody : ACCOUNT_AVATAR.darkBody,
      eyes: dark ? ACCOUNT_AVATAR.darkBody : ACCOUNT_AVATAR.lightBody }
  }
  return { body: selected.hex, eyes: ACCOUNT_AVATAR.lightBody }
}
