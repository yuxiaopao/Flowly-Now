export const AGENT_DEBUG = Object.freeze({ maxSseFrameChars: 1024 * 1024, fallbackMaxOutputTokens: 2000, promptPreviewChars: 200 })

export function reportedTokenUsage(session) {
  const value = session?.usage?.totalTokens ?? session?.usage?.total_tokens
  return typeof value === 'number' && Number.isSafeInteger(value) && value >= 0 ? value : null
}
