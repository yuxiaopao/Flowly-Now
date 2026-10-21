import { writeFileSync } from 'node:fs'
import { McpClient, evalPage, resultText, login, delay } from './chrome_mcp_client.mjs'

const client = new McpClient()
const output = 'E:/Flowly-now/Docs/verification/nl-creator-20261017'
const checks = []
const evaluate = fn => evalPage(client, fn)
async function wait(expression, seconds = 60) {
  for (let index=0; index<seconds; index++) {
    if (await evaluate(`() => Boolean(${expression})`)) return
    await delay(1000)
  }
  throw new Error(`Timed out: ${expression}`)
}
function check(name, passed) {
  checks.push({name, passed:Boolean(passed)})
  console.log(`${passed?'PASS':'FAIL'} ${name}`)
  writeFileSync(`${output}/stream-results.json`,JSON.stringify(checks,null,2))
  if (!passed) throw new Error(name)
}
async function uid(role, name) {
  const snapshot=resultText(await client.tool('take_snapshot'))
  const line=snapshot.split('\n').find(line=>line.includes(`${role} "${name}"`))
  if (!line) throw new Error(`Missing ${role} ${name}`)
  return line.match(/uid=(\S+)/)[1]
}
async function click(name) { await client.tool('click',{uid:await uid('button',name)}) }
async function fill(value) { await client.tool('fill',{uid:await uid('textbox','输入工作流描述'),value}) }
try {
  await client.initialize()
  const {tools}=await client.request('tools/list')
  client.pageTools=new Set(tools.filter(tool=>tool.inputSchema?.properties?.pageId).map(tool=>tool.name))
  await login(client)
  await client.tool('emulate',{viewport:'1440x1000x1',prefersReducedMotion:'reduce'})
  await client.tool('navigate_page',{url:'http://localhost:5200/nl-create'})
  await wait(`document.querySelector('.model-info')?.textContent.includes('agnes')`)
  await click('新标签')
  await click('深度思考')
  await fill('这是界面测试，请仅回复：语创连接正常。不要生成工作流。')
  await click('发送')
  await wait(`document.querySelectorAll('.message-user').length===1 && !document.querySelector('.streaming-progress')`,90)
  const reply=await evaluate(`() => [...document.querySelectorAll('.message-assistant .message-text')].at(-1)?.textContent`)
  check('real model chat stream completes without generating a workflow', reply?.includes('语创连接正常') && !await evaluate(`() => document.querySelector('.mini-workflow-preview')`))
  await click('生成工作流')
  await fill('创建一个简单工作流：开始节点连接 Python 代码节点，代码 result = {"ok": True}，最后连接结束节点。不要调用外部接口。')
  await click('发送')
  await wait(`document.querySelectorAll('.vue-flow__node').length>=3 && !document.querySelector('.streaming-progress')`,120)
  check('real model generates a visible connected workflow', await evaluate(`() => document.querySelectorAll('.vue-flow__node').length>=3 && document.querySelectorAll('.vue-flow__edge').length>=2`))
  await client.tool('take_screenshot',{filePath:`${output}/real-generation.png`,fullPage:true})
  await click('深度思考')
  await fill('请详细分析这个流程可以如何增加输入验证、异常处理和输出检查，给出逐条说明，暂不修改流程。')
  await click('发送')
  await wait(`document.querySelector('.streaming-progress')`)
  await click('停止接收')
  await wait(`document.body.innerText.includes('已停止接收')`)
  check('stop aborts stream and offers recovery without resending', await evaluate(`() => document.body.innerText.includes('后台可能仍在处理') && !document.querySelector('.streaming-progress')`))
  console.log(resultText(await client.tool('list_console_messages',{types:['error','warn']})))
} catch(error) {
  console.error(error.stack)
  writeFileSync(`${output}/stream-failure.txt`,resultText(await client.tool('take_snapshot').catch(()=>({}))))
  process.exitCode=1
} finally {client.close()}
