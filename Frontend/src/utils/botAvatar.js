import { BOT_AVATAR } from '@/config/botAvatar'
import { STATE_BY_ID } from '@/vendor/bloub/states'

let avatarId = 0

export function createBotAvatarId() {
  avatarId += 1
  return `flowly-bot-${avatarId}`
}

export function resolveBotState(state) {
  const mapped = BOT_AVATAR.states[state] || state
  return STATE_BY_ID.has(mapped) ? mapped : BOT_AVATAR.states.idle
}

export function getAssistantAvatarState(message, activity = 'replying') {
  if (message?.error || message?.metadata?.error) return 'error'
  if (message?.loading) return 'thinking'
  if (message?.isStreaming) return activity === 'generating' ? 'generating' : activity === 'thinking' ? 'thinking' : 'replying'
  if (message?.workflow) return 'success'
  return 'idle'
}
