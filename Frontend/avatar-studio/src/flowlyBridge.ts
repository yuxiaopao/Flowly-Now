import protocol from '../protocol.json'

/** Only the containing Flowly window can request a frame. No credentials cross this bridge. */
export function installAvatarBridge(preferences: () => Record<string, unknown>) {
  if (window.parent === window) return
  const targetOrigin = location.origin === 'null' ? '*' : location.origin
  const send = (type: string, detail: Record<string, unknown> = {}) => {
    window.parent.postMessage({ channel: protocol.channel, version: protocol.version, type, ...detail }, targetOrigin)
  }
  let capturing = false
  window.addEventListener('message', event => {
    if (event.source !== window.parent || event.origin !== location.origin ||
      event.data?.channel !== protocol.channel || event.data?.version !== protocol.version) return
    if (event.data.type === protocol.ping) {
      send(protocol.ready)
      return
    }
    if (event.data.type !== protocol.request || typeof event.data.requestId !== 'string' || capturing) return
    capturing = true
    const requestId = event.data.requestId
    try {
      const settings = preferences()
      send(protocol.response, { requestId, preferences: settings })
    } catch {
      send(protocol.response, { requestId, error: 'capture-failed' })
    } finally {
      capturing = false
    }
  })
  send(protocol.ready)
}
