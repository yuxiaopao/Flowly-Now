const path = require('node:path');
const { fileURLToPath } = require('node:url');

const rendererTargets = new WeakMap();
const IPC_TRUST_ERROR = '此操作仅允许来自受信任的 Flowly 主页面';

function normalizedFilePath(filePath) {
  const resolved = path.resolve(filePath);
  return process.platform === 'win32' ? resolved.toLowerCase() : resolved;
}

function isTrustedRendererUrl(value, target) {
  if (!target || typeof value !== 'string') return false;
  try {
    const actual = new URL(value);
    if (actual.username || actual.password) return false;
    if (target.mode === 'file') {
      return actual.protocol === 'file:'
        && normalizedFilePath(fileURLToPath(actual)) === normalizedFilePath(target.filePath);
    }
    if (target.mode === 'url') {
      const allowed = new URL(target.url);
      return ['http:', 'https:'].includes(allowed.protocol) && !allowed.username && !allowed.password
        && actual.origin === allowed.origin;
    }
  } catch { /* Invalid and opaque URLs never gain native privileges. */ }
  return false;
}

function registerTrustedRenderer(window, target) {
  rendererTargets.set(window.webContents, Object.freeze({ ...target }));
}

function assertTrustedRenderer(event, window) {
  if (!window || window.isDestroyed() || event.sender !== window.webContents
    || event.senderFrame !== window.webContents.mainFrame
    || !isTrustedRendererUrl(event.senderFrame?.url, rendererTargets.get(window.webContents))) {
    throw new Error(IPC_TRUST_ERROR);
  }
  return window;
}

function protectRendererNavigation(window, shell) {
  const target = rendererTargets.get(window.webContents);
  function openWebLink(value) {
    try {
      const url = new URL(value);
      if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password) return;
      Promise.resolve(shell.openExternal(url.href)).catch(() => {});
    } catch { /* File, custom-protocol, and malformed links stay outside the native shell. */ }
  }
  window.webContents.on('will-navigate', (event, url) => {
    if (isTrustedRendererUrl(url, target)) return;
    event.preventDefault();
    openWebLink(url);
  });
  window.webContents.on('will-redirect', (event, url, _isInPlace, isMainFrame) => {
    if (isMainFrame === false || isTrustedRendererUrl(url, target)) return;
    event.preventDefault();
  });
  window.webContents.setWindowOpenHandler(({ url }) => {
    openWebLink(url);
    return { action: 'deny' };
  });
}

module.exports = { assertTrustedRenderer, isTrustedRendererUrl, registerTrustedRenderer, protectRendererNavigation };
