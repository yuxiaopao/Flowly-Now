import assert from 'node:assert/strict'
import {McpClient,evalPage} from './chrome_mcp_client.mjs'
const c=new McpClient()
try {
  await c.initialize()
  const {tools}=await c.request('tools/list')
  c.pageTools=new Set(tools.filter(t=>t.inputSchema?.properties?.pageId).map(t=>t.name))
  await c.tool('new_page',{url:'http://localhost:5200/login'})
  await c.tool('wait_for',{text:['欢迎回来']})
  const config=await evalPage(c,`async()=>{const {useSiteConfigStore}=await import('/src/stores/siteConfig.js');await useSiteConfigStore().fetchPublicConfig();const {APP_CONFIG,getApiBaseUrl,getWebSocketUrl}=await import('/src/config/index.js');return {api:APP_CONFIG.apiBaseUrl,base:getApiBaseUrl(),ws:getWebSocketUrl('/ws/test/')}}`)
  assert.equal(config.api,'http://127.0.0.1:8002')
  assert.equal(config.base,'http://localhost:5200/api/v1')
  assert(config.ws.startsWith('ws://localhost:5200/ws/test/'))
  console.log('PASS local HTTP, direct API and WebSocket targets survive runtime configuration')
} finally {c.close()}
