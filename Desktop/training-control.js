const { execFile } = require('node:child_process');
const { promisify } = require('node:util');

const executeFile = promisify(execFile);
const PROCESS_SETTINGS = Object.freeze({ versionTimeoutMs: 5000, terminateGraceMs: 10000 });
const exited = child => child.exitCode != null || child.signalCode != null;

function waitForExit(child, timeoutMs) {
  if (exited(child)) return Promise.resolve(true);
  return new Promise(resolve => {
    const finish = result => {
      clearTimeout(timer);
      child.removeListener('exit', onExit);
      resolve(result);
    };
    const onExit = () => finish(true);
    const timer = setTimeout(() => finish(false), timeoutMs);
    child.once('exit', onExit);
  });
}

async function stopOwnedProcess(child, { graceMs = PROCESS_SETTINGS.terminateGraceMs } = {}) {
  if (!child || exited(child)) return;
  if (!Number.isSafeInteger(child.pid) || child.pid <= 0 || child.pid === process.pid) {
    throw new Error('无法确认训练子进程身份');
  }
  if (process.platform === 'win32') {
    try {
      await executeFile('taskkill', ['/PID', String(child.pid), '/T', '/F'], { windowsHide: true, timeout: graceMs });
    } catch (error) {
      if (!await waitForExit(child, graceMs)) throw error;
    }
  } else {
    try { process.kill(-child.pid, 'SIGTERM'); }
    catch (error) { if (error.code !== 'ESRCH') throw error; child.kill('SIGTERM'); }
  }
  if (await waitForExit(child, graceMs)) return;
  try {
    if (process.platform !== 'win32') process.kill(-child.pid, 'SIGKILL');
    else child.kill('SIGKILL');
  } catch (error) { if (error.code !== 'ESRCH') throw error; child.kill('SIGKILL'); }
  if (!await waitForExit(child, graceMs)) throw new Error('训练进程未停止，请重试取消');
}

module.exports = { PROCESS_SETTINGS, stopOwnedProcess };
