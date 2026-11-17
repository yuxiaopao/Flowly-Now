const test = require('node:test');
const assert = require('node:assert/strict');
const { spawn } = require('node:child_process');
const { once } = require('node:events');
const { stopOwnedProcess } = require('../training-control');

test('cancellation waits until the owned process and its child have stopped', async context => {
  const source = `const {spawn}=require('node:child_process');
    const child=spawn(process.execPath,['-e','setInterval(()=>{},1000)'],{stdio:'ignore',windowsHide:true});
    console.log(child.pid);setInterval(()=>{},1000);`;
  const child = spawn(process.execPath, ['-e', source], {
    stdio: ['ignore', 'pipe', 'pipe'], detached: process.platform !== 'win32', windowsHide: true,
  });
  let descendant;
  context.after(async () => {
    await stopOwnedProcess(child).catch(() => {});
    if (descendant) {
      try { process.kill(descendant, 'SIGKILL'); } catch (error) { if (error.code !== 'ESRCH') throw error; }
    }
  });
  descendant = Number(String((await once(child.stdout, 'data'))[0]).trim());
  assert(Number.isSafeInteger(descendant) && descendant > 0 && descendant !== process.pid);
  await stopOwnedProcess(child);
  assert(child.exitCode !== null || child.signalCode !== null);
  for (let attempt = 0; attempt < 40; attempt++) {
    try { process.kill(descendant, 0); } catch (error) { if (error.code === 'ESRCH') return; throw error; }
    await new Promise(resolve => setTimeout(resolve, 50));
  }
  assert.fail('owned descendant is still running after cancellation');
});

test('process control rejects the host process and invalid child identities', async () => {
  for (const pid of [process.pid, -1, 0, undefined]) {
    await assert.rejects(stopOwnedProcess({ pid, exitCode: null, signalCode: null }), /身份/);
  }
});
