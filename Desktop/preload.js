/**
 * Flowly Agent — Preload Script
 *
 * Exposes a safe IPC bridge to the renderer process.
 * Uses contextBridge to expose typed APIs without exposing Node.js directly.
 */

const { contextBridge, ipcRenderer } = require('electron');

/**
 * @typedef {Object} GPUInfo
 * @property {boolean} available
 * @property {string|null} name
 * @property {number} memoryTotalMb
 * @property {number} memoryFreeMb
 * @property {number|null} utilizationPercent
 * @property {string|null} driverVersion
 * @property {string|null} computeCapability
 * @property {number} deviceCount
 */

/**
 * @typedef {Object} AgentStatus
 * @property {boolean} connected
 * @property {string|null} cloudUrl
 * @property {string|null} agentId
 * @property {GPUInfo} gpu
 * @property {Object|null} training
 * @property {string} version
 */

/**
 * @typedef {Object} TrainingStatus
 * @property {string|null} jobId
 * @property {boolean} running
 * @property {number} progress
 * @property {number} currentEpoch
 * @property {number} totalEpochs
 * @property {number} bestFitness
 * @property {number|null} startTime
 * @property {number} elapsedMs
 * @property {string[]} logs
 */

/**
 * @typedef {Object} TrainingStartResult
 * @property {boolean} success
 * @property {string|null} error
 * @property {string|null} jobId
 * @property {string|null} outputDir
 */

contextBridge.exposeInMainWorld('flowlyDesktop', {
  isDesktop: true,
  training: {
    monitor: {
      start: (token, binding) => ipcRenderer.invoke('monitor:start', token, binding),
      logout: () => ipcRenderer.invoke('monitor:logout'),
      stop: () => ipcRenderer.invoke('monitor:stop'),
      refresh: () => ipcRenderer.invoke('monitor:refresh'),
      snapshot: () => ipcRenderer.invoke('monitor:snapshot'),
      reveal: id => ipcRenderer.invoke('monitor:reveal', id),
      exportSnapshot: format => ipcRenderer.invoke('monitor:export', format),
      onUpdate: callback => {
        const handler = (_event, payload) => callback(payload);
        ipcRenderer.on('monitor:update', handler);
        return () => ipcRenderer.removeListener('monitor:update', handler);
      },
    },
  },
  platform: process.platform,
  versions: {
    electron: process.versions.electron,
    chrome: process.versions.chrome,
    node: process.versions.node,
  },
  runtime: {
    startSite: (options) => ipcRenderer.invoke('runtime:startSite', options),
    stopSite: (siteId) => ipcRenderer.invoke('runtime:stopSite', siteId),
    listSites: () => ipcRenderer.invoke('runtime:listSites'),
    getManifest: () => ipcRenderer.invoke('runtime:getManifest'),
    grantPermission: (options) => ipcRenderer.invoke('runtime:grantPermission', options),
    /**
     * Create/refresh the site's self-contained venv + install requirements.txt
     * without starting the Flask process. Progress streams via onEnvProgress.
     */
    prepareEnv: (options) => ipcRenderer.invoke('runtime:prepareEnv', options),
    onEnvProgress: (callback) => {
      const handler = (_event, payload) => callback(payload)
      ipcRenderer.on('runtime:envProgress', handler)
      return () => ipcRenderer.removeListener('runtime:envProgress', handler)
    },
  },
  /** Open a local folder in the OS file explorer (e.g. generated site output dir) */
  openFolder: (targetPath) => ipcRenderer.invoke('shell:openFolder', targetPath),
});

contextBridge.exposeInMainWorld('agentAPI', {
  // ---- Agent Connection ----
  /**
   * Connect this agent to the Flowly cloud server
   * @param {{ cloudUrl: string, agentId: string, apiToken: string }} config
   * @returns {Promise<AgentStatus>}
   */
  connect: (config) => ipcRenderer.invoke('agent:connect', config),

  /**
   * Disconnect from cloud
   * @returns {Promise<AgentStatus>}
   */
  disconnect: () => ipcRenderer.invoke('agent:disconnect'),

  /**
   * Get current agent status
   * @returns {Promise<AgentStatus>}
   */
  getStatus: () => ipcRenderer.invoke('agent:status'),

  /**
   * Get persisted connection config
   * @returns {Promise<{cloudUrl: string, agentId: string, hasApiToken: boolean}>}
   */
  getConfig: () => ipcRenderer.invoke('agent:getConfig'),

  // ---- GPU ----
  /**
   * Get GPU info
   * @returns {Promise<GPUInfo>}
   */
  getGpuInfo: () => ipcRenderer.invoke('gpu:info'),

  // ---- Training ----
  /**
   * Start a YOLO training job
   * @param {Object} jobConfig - Training job configuration
   * @returns {Promise<TrainingStartResult>}
   */
  startTraining: (jobConfig) => ipcRenderer.invoke('training:start', jobConfig),

  /**
   * Stop the running training job
   * @returns {Promise<{success: boolean, error?: string}>}
   */
  stopTraining: () => ipcRenderer.invoke('training:stop'),

  /**
   * Get current training status
   * @returns {Promise<TrainingStatus>}
   */
  getTrainingStatus: () => ipcRenderer.invoke('training:status'),

  /**
   * Get training logs
   * @returns {Promise<string[]>}
   */
  getTrainingLogs: () => ipcRenderer.invoke('training:logs'),

  // ---- CLIP Index (M4.14) ----
  startClipIndex: (jobConfig) => ipcRenderer.invoke('clipIndex:start', jobConfig),
  stopClipIndex: () => ipcRenderer.invoke('clipIndex:stop'),
  getClipIndexStatus: () => ipcRenderer.invoke('clipIndex:status'),
  getClipIndexLogs: () => ipcRenderer.invoke('clipIndex:logs'),

  onClipIndexProgress: (callback) => {
    const handler = (_event, status) => callback(status);
    ipcRenderer.on('clipIndex:progress', handler);
    return () => ipcRenderer.removeListener('clipIndex:progress', handler);
  },

  onClipIndexComplete: (callback) => {
    const handler = (_event, status) => callback(status);
    ipcRenderer.on('clipIndex:complete', handler);
    return () => ipcRenderer.removeListener('clipIndex:complete', handler);
  },

  onClipIndexError: (callback) => {
    const handler = (_event, payload) => callback(payload);
    ipcRenderer.on('clipIndex:error', handler);
    return () => ipcRenderer.removeListener('clipIndex:error', handler);
  },

  onClipIndexStarted: (callback) => {
    const handler = (_event, status) => callback(status);
    ipcRenderer.on('clipIndex:started', handler);
    return () => ipcRenderer.removeListener('clipIndex:started', handler);
  },

  // ---- App Info ----
  /**
   * Get app information
   * @returns {Promise<{version: string, userData: string, platform: string, arch: string}>}
   */
  getAppInfo: () => ipcRenderer.invoke('app:info'),

  /**
   * Open directory picker
   * @param {{title?: string, defaultPath?: string}} [options]
   * @returns {Promise<string|null>} - Selected directory path or null if cancelled
   */
  selectDirectory: (options) => ipcRenderer.invoke('dialog:selectDirectory', options),

  // ---- Event Listeners ----
  /**
   * Listen to training progress updates
   * @param {(status: TrainingStatus) => void} callback
   * @returns {() => void} - Unsubscribe function
   */
  onTrainingProgress: (callback) => {
    const handler = (event, status) => callback(status);
    ipcRenderer.on('training:progress', handler);
    return () => ipcRenderer.removeListener('training:progress', handler);
  },

  /**
   * Listen to training completion
   * @param {(status: TrainingStatus) => void} callback
   * @returns {() => void}
   */
  onTrainingComplete: (callback) => {
    const handler = (event, status) => callback(status);
    ipcRenderer.on('training:complete', handler);
    return () => ipcRenderer.removeListener('training:complete', handler);
  },

  /**
   * Listen to training errors
   * @param {(payload: TrainingStatus & {error: string}) => void} callback
   * @returns {() => void}
   */
  onTrainingError: (callback) => {
    const handler = (event, payload) => callback(payload);
    ipcRenderer.on('training:error', handler);
    return () => ipcRenderer.removeListener('training:error', handler);
  },

  /**
   * Listen to training started event
   * @param {(status: TrainingStatus) => void} callback
   * @returns {() => void}
   */
  onTrainingStarted: (callback) => {
    const handler = (event, status) => callback(status);
    ipcRenderer.on('training:started', handler);
    return () => ipcRenderer.removeListener('training:started', handler);
  },

  /**
   * Listen to agent status changes
   * @param {(status: AgentStatus) => void} callback
   * @returns {() => void}
   */
  onAgentStatus: (callback) => {
    const handler = (event, status) => callback(status);
    ipcRenderer.on('agent:status', handler);
    return () => ipcRenderer.removeListener('agent:status', handler);
  },
});
