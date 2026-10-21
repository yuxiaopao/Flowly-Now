import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import { McpClient, evalPage, resultText, login, FRONTEND_URL } from './chrome_mcp_client.mjs'

const output = path.resolve(import.meta.dirname, '../Docs/verification/rag-20261019')
assert.ok(process.env.FLOWLY_E2E_USERNAME?.startsWith('rag_qa_'), 'Use the isolated RAG QA account')
assert.ok(FRONTEND_URL.endsWith(':5201'), 'Use the isolated frontend')
const c = new McpClient(), checks = []
const pass = name => { checks.push(name); console.log(`PASS ${name}`) }
const snapshot = async () => resultText(await c.tool('take_snapshot'))
async function uid(role, name, last = false) {
  const lines = (await snapshot()).split('\n').filter(line => line.includes(`${role} "${name}"`) || line.includes(`${role} "*${name}"`))
  const line = last ? lines.at(-1) : lines[0]
  assert.ok(line, `${role} ${name} not found`)
  return line.match(/uid=(\S+)/)[1]
}
async function click(name, last = false) {
  const target = await uid('button', name, last)
  try { await c.tool('click', { uid: target }) }
  catch (error) {
    if (!error.message.includes('did not become interactive')) throw error
    if ((await snapshot()).includes(`button "${name}"`)) await c.tool('click', { uid: await uid('button', name, last) })
  }
}
async function tab(name) { await c.tool('click', { uid: await uid('tab', name) }) }
async function fill(name, value) { await c.tool('fill', { uid: await uid('textbox', name), value }) }
async function api(body) { return evalPage(c, `async()=>{const {ragApi}=await import('/src/api/rag.js');${body}}`) }
async function waitFor(expression) {
  assert.equal(await evalPage(c, `async()=>{const until=Date.now()+20000;while(Date.now()<until){if(${expression})return true;await new Promise(r=>setTimeout(r,100))}return false}`, 25000), true, expression)
}
async function capture(name) { await c.tool('take_screenshot', { filePath: path.join(output, `${name}.png`), fullPage: true }) }
async function closeDialog() {
  await waitFor(`Array.from(document.querySelectorAll('[role="dialog"]')).some(el=>el.checkVisibility())`)
  await click('关闭此对话框')
  await waitFor(`!Array.from(document.querySelectorAll('[role="dialog"]')).some(el=>el.checkVisibility())`)
}

try {
  await c.initialize()
  const { tools } = await c.request('tools/list')
  assert.ok(tools.some(tool => tool.name === 'navigate_page'))
  c.pageTools = new Set(tools.filter(tool => tool.inputSchema?.properties?.pageId).map(tool => tool.name))
  await login(c)
  await c.tool('navigate_page', { url: `${FRONTEND_URL}/knowledge` })
  await c.tool('wait_for', { text: ['知识库'] })
  if (process.env.RAG_INSPECT === '1') {
    console.log(await snapshot())
  } else {
    const collection = await api(`return ragApi.createCollection({name:'RAG 浏览器验证',retrieval_mode:'keyword'})`)
    assert.ok(collection.id)
    await c.tool('navigate_page', { url: `${FRONTEND_URL}/knowledge/${collection.id}` })
    await c.tool('wait_for', { text: ['RAG 浏览器验证'] })
    await click('上传文档')
    await tab('文本输入')
    await click('上传', true)
    await c.tool('wait_for', { text: ['请填写标题和内容'] })
    pass('空文本提交有明确校验反馈')
    await fill('标题', '工作流故障排查指南')
    await fill('内容', '工作流失败后应先查看执行历史，再检查失败节点的错误日志。确认输入参数、模型配置和外部接口状态。排障标识：FLOWLY_RAG_QA。')
    await click('上传', true)
    await c.tool('wait_for', { text: ['工作流故障排查指南', '已处理'] })
    const docs = await api(`return ragApi.getDocuments({collection:'${collection.id}'})`)
    assert.equal(docs.count, 1)
    assert.equal(docs.results[0].status, 'completed')
    assert.ok(docs.results[0].chunk_count > 0)
    pass('文本录入完成真实分块并刷新统计')
    fs.writeFileSync(path.join(output, 'fixture.json'), JSON.stringify({ collectionId: collection.id, documentId: docs.results[0].id }))
    await tab('搜索测试')
    await fill('输入搜索查询...', '工作流失败')
    await click('搜索')
    await c.tool('wait_for', { text: ['搜索结果 (1)'] })
    await click('工作流故障排查指南')
    await c.tool('wait_for', { text: ['FLOWLY_RAG_QA'] })
    pass('关键词检索返回真实内容并可查看来源文档')
    await closeDialog()
    await tab('知识问答')
    await fill('知识库问题', '工作流失败怎么排查？')
    await click('提问')
    await c.tool('wait_for', { text: ['已基于检索资料生成', '引用资料'] })
    assert.ok((await snapshot()).includes('先查看执行历史，再检查失败节点的错误日志。[1]'))
    await capture('grounded-answer')
    pass('受控 HTTP 模型生成带编号来源的回答')
    await click('[1] 工作流故障排查指南 · 分块 1')
    await c.tool('wait_for', { text: ['FLOWLY_RAG_QA'] })
    await closeDialog()
    pass('问答引用跳转到原始文档')
    await fill('知识库问题', 'ZXQNOEVIDENCE98765')
    await click('提问')
    await c.tool('wait_for', { text: ['未找到相关依据'] })
    assert.ok(!(await snapshot()).includes('引用资料'))
    await capture('no-evidence')
    pass('无检索证据时明确拒答并清除旧引用')
    await fill('知识库问题', '工作流失败 故障模拟')
    await click('提问')
    await c.tool('wait_for', { text: ['资料已检索到，但回答模型不可用'] }, 30000)
    assert.ok(!(await snapshot()).includes('已基于检索资料生成'))
    await capture('model-unavailable')
    pass('模型不可用时显示错误并清除旧回答')
    await tab('文档')
    await click('重新处理')
    await click('确定')
    await c.tool('wait_for', { text: ['文档重新处理完成'] })
    const reprocessed = await api(`return ragApi.getDocuments({collection:'${collection.id}'})`)
    assert.equal(reprocessed.count, 1)
    assert.equal(reprocessed.results[0].id, docs.results[0].id)
    pass('重新处理保留文档 ID 且不产生重复文档')
    await click('上传文档')
    await tab('文件上传')
    const uploadPath = path.join(output, 'upload-fixture.md')
    fs.writeFileSync(uploadPath, '# 上传文件验证\n账单查询请联系财务。唯一标识 BILLING_RAG_FILE。')
    await c.tool('upload_file', { uid: await uid('button', '将文件拖到此处，或点击上传'), filePaths: [uploadPath] })
    await click('上传', true)
    await c.tool('wait_for', { text: ['upload-fixture.md'] })
    const uploaded = await api(`return ragApi.getDocuments({collection:'${collection.id}'})`)
    assert.equal(uploaded.count, 2)
    assert.equal(uploaded.results.find(d=>d.title==='upload-fixture.md').source_type, 'file')
    pass('真实 Markdown 文件上传并保存来源类型')
    await tab('设置')
    await c.tool('fill', { uid: await uid('spinbutton', '分块大小'), value: '100' })
    await click('保存设置')
    await c.tool('wait_for', { text: ['分块重叠必须小于分块大小'] })
    pass('分块重叠边界校验')
    await c.tool('fill', { uid: await uid('spinbutton', '分块大小'), value: '500' })
    await click('保存设置')
    await click('确定')
    await c.tool('wait_for', { text: ['设置已保存'] })
    const invalidated = await api(`return ragApi.getDocuments({collection:'${collection.id}'})`)
    assert.ok(invalidated.results.every(d=>d.status==='pending'))
    assert.equal((await api(`return ragApi.searchCollection('${collection.id}',{query:'工作流'})`)).count, 0)
    await click('重新处理')
    await click('确定')
    await c.tool('wait_for', { text: ['2 个文档重新处理完成'] })
    assert.equal((await api(`return ragApi.searchCollection('${collection.id}',{query:'工作流'})`)).count, 1)
    pass('配置变更停用旧索引，整库重建后恢复检索')
    await click('导入 Flowly 使用指南')
    await c.tool('wait_for', { text: ['Flowly 使用指南已导入'] })
    const imported = await api(`return ragApi.getDocuments({collection:'${collection.id}'})`)
    assert.equal(imported.count, 5)
    await click('导入 Flowly 使用指南')
    await waitFor(`!Array.from(document.querySelectorAll('button')).find(b=>b.textContent.includes('导入 Flowly 使用指南'))?.classList.contains('is-loading')`)
    const repeated = await api(`return ragApi.getDocuments({collection:'${collection.id}'})`)
    assert.deepEqual(repeated.results.map(d=>d.id).sort(), imported.results.map(d=>d.id).sort())
    pass('系统指南导入成功且重复导入不增加文档')
    await c.tool('navigate_page', { url: `${FRONTEND_URL}/knowledge/${collection.id}` })
    await c.tool('wait_for', { text: ['upload-fixture.md', '已处理'] })
    pass('页面重新加载后文档与处理状态持久保留')
    await tab('知识问答')
    await fill('知识库问题', '工作流失败怎么排查？')
    await click('提问')
    await c.tool('wait_for', { text: ['已基于检索资料生成'] })
    await c.tool('emulate', { viewport: '390x844x1,mobile,touch' })
    await capture('mobile-answer')
    const dimensions = await evalPage(c, `()=>({width:window.innerWidth,scroll:document.documentElement.scrollWidth})`)
    assert.ok(dimensions.scroll <= dimensions.width + 1, JSON.stringify(dimensions))
    pass('390px 移动视口无页面横向溢出')
    await c.tool('emulate', { viewport: '1440x1000x1' })
    await tab('文档')
    await click('删除', true)
    await click('确定')
    await c.tool('wait_for', { text: ['删除成功'] })
    const deleted = await api(`return ragApi.getDocuments({collection:'${collection.id}'})`)
    assert.equal(deleted.count, 4)
    const missing = imported.results.find(d=>!deleted.results.some(remaining=>remaining.id===d.id))
    const query = missing.id === docs.results[0].id ? 'FLOWLY_RAG_QA' : missing.title === 'upload-fixture.md' ? 'BILLING_RAG_FILE' : null
    if (query) assert.equal((await api(`return ragApi.searchCollection('${collection.id}',{query:'${query}'})`)).count, 0)
    pass('删除文档更新计数且删除的专属内容不再可检索')
    await capture('documents-final')
    fs.writeFileSync(path.join(output, 'console.txt'), resultText(await c.tool('list_console_messages', { types: ['error', 'warn'] })))
    console.log(await snapshot())
  }
} catch (error) {
  fs.writeFileSync(path.join(output, 'failure-snapshot.txt'), await snapshot().catch(() => 'unavailable'))
  console.error(error.stack)
  process.exitCode = 1
} finally {
  fs.writeFileSync(path.join(output, 'checks.json'), JSON.stringify({ transport: 'chrome-devtools MCP', checks }, null, 2))
  c.close()
}
