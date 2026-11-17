const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { configureQaProfile, blockQaNetwork } = require('../qa-profile');

function temporaryProfile(context) {
  const directory = fs.mkdtempSync(path.join(fs.realpathSync(os.tmpdir()), 'flowly-qa-'));
  context.after(() => {
    const relative = path.relative(fs.realpathSync(os.tmpdir()), directory);
    assert(!relative.startsWith('..') && !path.isAbsolute(relative));
    assert(path.basename(directory).startsWith('flowly-qa-'));
    fs.rmSync(directory, { recursive: true, force: true });
  });
  return directory;
}

test('normal startup does not override the application profile', () => {
  assert.equal(configureQaProfile({ setPath() { assert.fail('normal profile changed'); } }, {}), null);
});

test('QA profile requires an explicit test flag and absolute path', () => {
  assert.throws(() => configureQaProfile({}, { FLOWLY_QA_MODE: '1' }), /explicit absolute/);
  assert.throws(() => configureQaProfile({}, { FLOWLY_QA_USER_DATA_DIR: 'relative' }), /explicit absolute/);
});

test('QA cannot reuse a directory outside the temporary root', () => {
  assert.throws(() => configureQaProfile({}, {
    FLOWLY_QA_MODE: '1', FLOWLY_QA_USER_DATA_DIR: path.resolve(__dirname, '../flowly-qa-test'),
  }), /system temporary/);
});

test('QA refuses an existing profile without modifying its stored data', context => {
  const directory = temporaryProfile(context);
  const config = path.join(directory, 'config.json');
  fs.writeFileSync(config, '{"apiToken":"fixture-token"}');
  assert.throws(() => configureQaProfile({}, {
    FLOWLY_QA_MODE: '1', FLOWLY_QA_USER_DATA_DIR: directory,
  }), /existing application data/);
  assert.equal(fs.readFileSync(config, 'utf8'), '{"apiToken":"fixture-token"}');
});

test('QA isolates user data, session and logs and blocks HTTP and WebSocket traffic', context => {
  const directory = temporaryProfile(context);
  const paths = {};
  const profile = configureQaProfile({ setPath: (key, value) => { paths[key] = value; } }, {
    FLOWLY_QA_MODE: '1', FLOWLY_QA_USER_DATA_DIR: directory,
  });
  assert.equal(profile.userData, directory);
  assert.equal(paths.userData, directory);
  assert.equal(paths.sessionData, path.join(directory, 'Session'));
  assert.equal(paths.logs, path.join(directory, 'logs'));
  let handler;
  blockQaNetwork({ session: { webRequest: { onBeforeRequest: (_filter, callback) => { handler = callback; } } } });
  for (const url of ['https://production.example/api/', 'http://127.0.0.1:8000/api/', 'wss://production.example/ws/']) {
    handler({ url }, result => assert.equal(result.cancel, true));
  }
  handler({ url: 'file:///renderer/index.html' }, result => assert.equal(result.cancel, false));
});
