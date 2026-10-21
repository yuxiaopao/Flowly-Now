import { AVATAR_STUDIO } from '@/config/avatarStudio'

export function getAvatarStudioUrl(userId, base = import.meta.env.BASE_URL) {
  const query = new URLSearchParams({ account: String(userId), embedded: '1' })
  return `${base}${AVATAR_STUDIO.entry}?${query}`
}

export function isAvatarStudioMessage(event, frameWindow, origin) {
  return Boolean(frameWindow && event.source === frameWindow && event.origin === origin &&
    event.data?.channel === AVATAR_STUDIO.channel && event.data?.version === AVATAR_STUDIO.version)
}

export function makeAvatarStudioMessage(type, requestId) {
  return { channel: AVATAR_STUDIO.channel, version: AVATAR_STUDIO.version, type, requestId }
}

