const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

function configureQaProfile(app, environment = process.env) {
  const requested = environment.FLOWLY_QA_USER_DATA_DIR;
  if (!requested && !environment.FLOWLY_QA_MODE) return null;
  if (environment.FLOWLY_QA_MODE !== '1' || !requested || !path.isAbsolute(requested)) {
    throw new Error('QA requires FLOWLY_QA_MODE=1 and an explicit absolute temporary profile');
  }
  const root = fs.realpathSync(os.tmpdir());
  const parent = fs.realpathSync(path.dirname(requested));
  const relative = path.relative(root, parent);
  if (relative.startsWith('..') || path.isAbsolute(relative) || !/^flowly-qa-[A-Za-z0-9-]+$/.test(path.basename(requested))) {
    throw new Error('QA profile must be a dedicated flowly-qa directory under the system temporary directory');
  }
  const directory = path.join(parent, path.basename(requested));
  if (fs.existsSync(directory)) {
    if (fs.lstatSync(directory).isSymbolicLink() || !fs.statSync(directory).isDirectory() || fs.readdirSync(directory).length) {
      throw new Error('QA profile must be new or empty; existing application data cannot be reused');
    }
  } else {
    fs.mkdirSync(directory);
  }
  const sessionDirectory = path.join(directory, 'Session');
  const logDirectory = path.join(directory, 'logs');
  fs.mkdirSync(sessionDirectory);
  fs.mkdirSync(logDirectory);
  app.setPath('userData', directory);
  app.setPath('sessionData', sessionDirectory);
  app.setPath('logs', logDirectory);
  return Object.freeze({ userData: directory });
}

function blockQaNetwork(webContents) {
  const localProtocols = new Set(['file:', 'data:', 'blob:', 'devtools:']);
  webContents.session.webRequest.onBeforeRequest({ urls: ['<all_urls>'] }, (details, callback) => {
    let allowed = false;
    try { allowed = localProtocols.has(new URL(details.url).protocol); } catch { /* Invalid requests stay blocked. */ }
    callback({ cancel: !allowed });
  });
}

module.exports = { configureQaProfile, blockQaNetwork };
