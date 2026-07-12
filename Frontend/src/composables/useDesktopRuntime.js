/**
 * Desktop site runtime bridge (Electron IPC).
 * Falls back gracefully in browser-only mode.
 */

function getRuntimeApi() {
  if (typeof window !== 'undefined' && window.flowlyDesktop?.runtime) {
    return window.flowlyDesktop.runtime
  }
  return null
}

export function useDesktopRuntime() {
  const isDesktop = Boolean(typeof window !== 'undefined' && window.flowlyDesktop?.isDesktop)

  async function startSite(options) {
    const api = getRuntimeApi()
    if (!api?.startSite) {
      return { success: false, error: 'Desktop runtime 不可用（请在 Flowly Desktop 中运行）' }
    }
    return api.startSite(options)
  }

  /**
   * Create/refresh the generated site's self-contained venv and install its
   * requirements.txt, without starting the Flask process yet.
   */
  async function prepareEnv(options) {
    const api = getRuntimeApi()
    if (!api?.prepareEnv) {
      return { success: false, error: 'Desktop runtime 不可用' }
    }
    return api.prepareEnv(options)
  }

  /** Subscribe to venv-creation / pip-install / startup progress events. */
  function onEnvProgress(callback) {
    const api = getRuntimeApi()
    if (!api?.onEnvProgress) return () => {}
    return api.onEnvProgress(callback)
  }

  /** Native OS folder picker — only available inside Flowly Desktop. */
  async function selectDirectory(options) {
    if (typeof window === 'undefined' || !window.agentAPI?.selectDirectory) {
      return null
    }
    return window.agentAPI.selectDirectory(options)
  }

  /** Reveal a local path in the OS file explorer (Finder/Explorer). */
  async function openFolder(targetPath) {
    if (typeof window === 'undefined' || !window.flowlyDesktop?.openFolder) {
      return { success: false, error: 'Desktop runtime 不可用' }
    }
    return window.flowlyDesktop.openFolder(targetPath)
  }

  async function stopSite(siteId) {
    const api = getRuntimeApi()
    if (!api?.stopSite) {
      return { success: false, error: 'Desktop runtime 不可用' }
    }
    return api.stopSite(siteId)
  }

  async function listSites() {
    const api = getRuntimeApi()
    if (!api?.listSites) return []
    return api.listSites()
  }

  async function getManifest() {
    const api = getRuntimeApi()
    if (!api?.getManifest) return null
    return api.getManifest()
  }

  async function grantPermission(options) {
    const api = getRuntimeApi()
    if (!api?.grantPermission) {
      return { success: false, error: 'Desktop runtime 不可用' }
    }
    return api.grantPermission(options)
  }

  return {
    isDesktop,
    startSite,
    stopSite,
    listSites,
    getManifest,
    grantPermission,
    prepareEnv,
    onEnvProgress,
    selectDirectory,
    openFolder,
  }
}
