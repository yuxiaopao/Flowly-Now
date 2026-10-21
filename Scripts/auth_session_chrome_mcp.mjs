import assert from 'node:assert/strict'
import {McpClient,evalPage} from './chrome_mcp_client.mjs'
import {execFileSync} from 'node:child_process'
const c=new McpClient()
const username=`authqa_${Date.now()}`
try {
 await c.initialize();const {tools}=await c.request('tools/list');c.pageTools=new Set(tools.filter(t=>t.inputSchema?.properties?.pageId).map(t=>t.name));
 await c.tool('new_page',{url:'http://localhost:5200/login'});
 await c.tool('wait_for',{text:['欢迎回来']});
 const result=await evalPage(c,`async()=>{
  const {useSiteConfigStore}=await import('/src/stores/siteConfig.js');const site=useSiteConfigStore();await site.fetchPublicConfig();
  const {useAuthStore}=await import('/src/stores/auth.js');const auth=useAuthStore();
  await auth.register({username:'${username}',email:'${username}@example.invalid',password:'Cobalt!48219',password_confirm:'Cobalt!48219',agree_terms:true,terms_version:site.terms.terms?.version||'',privacy_version:site.terms.privacy?.version||''});
  await auth.login({username:'${username}',password:'Cobalt!48219',remember:true});return true;
 }`); assert.equal(result,true);
 await c.tool('navigate_page',{url:'http://localhost:5200/workflows'});
 await c.tool('wait_for',{text:['工作流']});
 assert.equal(await evalPage(c,'()=>location.pathname'),'/workflows');
 await evalPage(c,`()=>{window.dispatchEvent(new StorageEvent('storage',{key:'auth_logout',newValue:String(Date.now())}));return true}`);
 await c.tool('wait_for',{text:['欢迎回来']});
 assert.equal(await evalPage(c,'()=>location.pathname'),'/login');
 console.log('PASS cross-tab logout removes protected UI and redirects to login');
} finally {
 execFileSync('E:/Flowly-now/.venv/Scripts/python.exe',['E:/Flowly-now/Scripts/auth_e2e_fixture.py',username,'--cleanup'],{windowsHide:true});
 c.close();
}
