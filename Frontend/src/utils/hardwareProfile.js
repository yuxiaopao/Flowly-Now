/**
 * Collect browser-side hardware hints for NL workflow / YOLO training tuning.
 */

export function collectClientCapabilities() {
  const nav = typeof navigator !== 'undefined' ? navigator : {}
  const screenObj = typeof window !== 'undefined' ? window.screen : {}
  return {
    platform: nav.platform || '',
    navigator: {
      platform: nav.platform || '',
      hardwareConcurrency: nav.hardwareConcurrency || 0,
      deviceMemory: nav.deviceMemory || 0,
      userAgent: nav.userAgent || '',
    },
    screen: {
      width: screenObj.width || 0,
      height: screenObj.height || 0,
    },
    preferLocalTraining: true,
    collectedAt: new Date().toISOString(),
  }
}

export async function fetchSystemCapabilities(api) {
  const clientCapabilities = collectClientCapabilities()
  try {
    const res = await api.getCapabilities(clientCapabilities)
    return res?.data || res
  } catch {
    return { client_capabilities: clientCapabilities }
  }
}

export function nlPayloadWithCapabilities(extra = {}) {
  return {
    ...extra,
    client_capabilities: collectClientCapabilities(),
  }
}
