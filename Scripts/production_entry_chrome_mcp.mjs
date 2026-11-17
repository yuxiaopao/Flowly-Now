import assert from 'node:assert/strict'
import { McpClient, evalPage, delay } from './chrome_mcp_client.mjs'

const target = new URL(process.env.FLOWLY_PRODUCTION_QA_URL || 'http://127.0.0.1:0')
assert(['127.0.0.1', 'localhost'].includes(target.hostname) && Number(target.port) > 0, 'Use an isolated local production frontend container')
const client = new McpClient()
try {
  await client.initialize()
  await client.tool('new_page', { url: `${target.origin}/`, timeout: 30000 })
  await client.tool('emulate', { viewport: '1440x1000x1', prefersReducedMotion: 'reduce' })
  await delay(1000)
  const result = await evalPage(client, `async () => {
    for (let attempt = 0; attempt < 100 && !document.querySelector('#app')?.__vue_app__; attempt++) {
      await new Promise(resolve => setTimeout(resolve, 100));
    }
    const app = document.querySelector('#app')?.__vue_app__;
    const auth = app?.config.globalProperties.$pinia?._s.get('auth');
    if (!auth) return {ok:false,stage:'production app initialization'};
    const calls = [];
    const observer = new PerformanceObserver(list => calls.push(...list.getEntries()));
    observer.observe({type:'resource'});
    try {
      await auth.login({ username: 'nlwftest@flowly.test', password: 'Test123456!', remember: true });
      await app.config.globalProperties.$router.push('/workflows');
      await new Promise(resolve => setTimeout(resolve, 800));
      const wait = async predicate => { for (let n = 0; n < 100; n++) { if (predicate()) return; await new Promise(resolve => setTimeout(resolve, 100)); }; throw new Error('Production UI did not settle'); };
      const listed = await fetch('/api/v1/applications/', { headers: { Authorization: 'Bearer ' + localStorage.getItem('access_token') } }).then(response => response.json());
      const application = (listed.data || listed).results[0];
      if (!application) return {ok:false,stage:'missing isolated application fixture'};
      await app.config.globalProperties.$router.push('/applications/' + application.id);
      await wait(() => document.querySelector('#application-tab-test'));
      document.querySelector('#application-tab-test').click();
      await wait(() => document.querySelector('.applications-page .delivery-workbench'));
      const applicationGrid = getComputedStyle(document.querySelector('.applications-page .delivery-workbench')).display === 'grid';
      await app.config.globalProperties.$router.push('/home');
      await wait(() => document.querySelector('.delivery-pulse')?.getAttribute('aria-busy') === 'false');
      const shell = document.querySelector('.delivery-workbench');
      const sections = ['.page-header', '.delivery-pulse', '.delivery-path', '.workbench-columns'].map(selector => shell.querySelector(selector).getBoundingClientRect());
      const homeFlow = sections.every((rect, index) => rect.width >= shell.clientWidth * .9 && (!index || rect.top >= sections[index - 1].bottom - 1));
      const health = await fetch('/api/health/');
      await new Promise(resolve => setTimeout(resolve, 50));
      const requests = calls.filter(entry => new URL(entry.name).pathname.startsWith('/api/'));
      const sameOrigin = requests.every(entry => new URL(entry.name).origin === location.origin);
      const loginObserved = requests.some(entry => entry.name.includes('/api/v1/auth/login/'));
      const ok = auth.isAuthenticated && location.pathname === '/home' && health.ok && sameOrigin && loginObserved && applicationGrid && homeFlow;
      await auth.logout();
      return { ok, loginObserved, sameOrigin, apiRequests:requests.length, proxyStatus:health.status, applicationGrid, homeFlow };
    } finally { observer.disconnect(); }
  }`, 45000)
  assert.equal(result.ok, true, JSON.stringify(result))
  console.log(JSON.stringify({ browser: 'chrome-devtools-mcp', productionBundle: true, ...result }))
} finally { client.close() }
