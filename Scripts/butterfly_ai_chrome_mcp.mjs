import fs from 'node:fs/promises'
import {McpClient,evalPage,login,delay,FRONTEND_URL,BACKEND_URL} from './chrome_mcp_client.mjs'
const directory=new URL('../test-reports/butterfly-30s/',import.meta.url)
const artifactDirectory=new URL('../output/butterfly-video/ai_60/',import.meta.url)
const workflowId=(await fs.readFile(new URL('workflow-id.txt',artifactDirectory),'utf8')).trim(),executionId=(await fs.readFile(new URL('execution-id.txt',artifactDirectory),'utf8')).trim()
const client=new McpClient(),report={provider:'chrome-devtools-mcp',workflowId,executionId,checks:[]}
function check(name,condition,details){report.checks.push({name,passed:!!condition,details});if(!condition)throw new Error(name+': '+JSON.stringify(details))}
async function waitFor(fn,predicate){let result;for(let i=0;i<40;i++){result=await evalPage(client,fn);if(predicate(result))return result;await delay(500)}throw new Error('Page did not become ready: '+JSON.stringify(result))}
async function workflow(){return evalPage(client,`async()=>{const r=await fetch('${BACKEND_URL}/api/v1/workflows/${workflowId}/',{headers:{Authorization:'Bearer '+localStorage.getItem('access_token')}});const p=await r.json();return p.data||p}`)}
try{
  check('frontend reachable',(await fetch(FRONTEND_URL)).ok);check('backend reachable',(await fetch(BACKEND_URL+'/admin/')).ok)
  check('debug port listening',(await fetch('http://127.0.0.1:9222/json/version')).ok)
  await client.initialize();const schema=await client.request('tools/list');client.pageTools=new Set(schema.tools.filter(t=>t.inputSchema.required?.includes('pageId')).map(t=>t.name));check('navigate_page available',schema.tools.some(t=>t.name==='navigate_page'))
  await login(client);const original=await workflow();const video=original.nodes.find(n=>n.node_type==='video_generation'),image=original.nodes.find(n=>n.node_type==='image_generation')
  check('AI-only graph contains six model video nodes',original.nodes.length===23&&original.edges.length===22&&original.nodes.filter(n=>n.node_type==='video_generation').length===6&&original.nodes.every(n=>n.config?.tool!=='embroidery_3d'))
  await client.tool('navigate_page',{type:'url',url:FRONTEND_URL+'/workflows/'+workflowId+'/edit',timeout:30000})
  await waitFor(`()=>document.querySelectorAll('.vue-flow__node').length`,v=>v===23)
  for(const row of[image,video]){
    const selector=row.node_type==='video_generation'?'.video-generation-config-form':'.image-generation-config-form'
    await evalPage(client,`()=>{document.querySelector('.vue-flow__node[data-id="${row.id}"]').dispatchEvent(new MouseEvent('click',{bubbles:true}));return true}`)
    await waitFor(`()=>!!document.querySelector('${selector} .prompt-input textarea')`,Boolean)
    if(row.node_type==='video_generation'){
      const refs=await evalPage(client,`()=>document.querySelector('textarea[aria-label="视频参考图片"]')?.value`)
      check('reference mode is visible and retains upstream image variable',typeof refs==='string'&&refs.includes('node_outputs.'),{references:refs})
    }
    await evalPage(client,`()=>{const input=document.querySelector('${selector} .prompt-input textarea');const original=input.value;const setter=Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype,'value').set;setter.call(input,original+' ');input.dispatchEvent(new Event('input',{bubbles:true}));input.dispatchEvent(new Event('change',{bubbles:true}));setter.call(input,original);input.dispatchEvent(new Event('input',{bubbles:true}));input.dispatchEvent(new Event('change',{bubbles:true}));return true}`)
  }
  await evalPage(client,`()=>{[...document.querySelectorAll('button')].find(b=>b.innerText.trim()==='保存').click();return true}`)
  await delay(1500);const saved=await workflow()
  for(const previous of[image,video]){
    const current=saved.nodes.find(n=>n.id===previous.id),cfg=current.config,before=previous.config
    const get=(o,camel,snake)=>o[camel]??o[snake]
    check('saved '+previous.node_type+' preserves reference URLs, selected key and strict failure policy',JSON.stringify(get(cfg,'referenceImages','reference_images'))===JSON.stringify(get(before,'referenceImages','reference_images'))&&get(cfg,'credentialId','credential_id')===get(before,'credentialId','credential_id')&&get(cfg,'requireSuccess','require_success')===true&&cfg.prompt===before.prompt,{id:current.id,model:cfg.model,referenceCount:get(cfg,'referenceImages','reference_images')?.length,requireSuccess:get(cfg,'requireSuccess','require_success')})
  }
  await client.tool('take_screenshot',{filePath:new URL('native-ai-workflow.png',directory).pathname.replace(/^\//,''),fullPage:true})
  await client.tool('navigate_page',{type:'url',url:FRONTEND_URL+'/executions/'+executionId,timeout:30000})
  const execution=await evalPage(client,`async()=>{const r=await fetch('${BACKEND_URL}/api/v1/workflows/executions/${executionId}/',{headers:{Authorization:'Bearer '+localStorage.getItem('access_token')}});const p=await r.json();return p.data||p}`)
  const hasModelVideo=(execution.artifact_outputs||[]).some(row=>row.output_data?.provider==='agnes'&&row.output_data?.video_url)
  const partial=await waitFor(`()=>({images:[...document.querySelectorAll('.artifact-image')].filter(i=>i.complete&&i.naturalWidth>0).length,videos:document.querySelectorAll('video').length,text:document.body.innerText})`,v=>v.images>=1)
  check('history shows retained references and only videos backed by real model outputs',partial.images>=1&&(hasModelVideo?partial.videos>=1:partial.videos===0),{images:partial.images,videos:partial.videos,hasModelVideo,status:execution.status})
  await client.tool('take_screenshot',{filePath:new URL('native-ai-partial-history.png',directory).pathname.replace(/^\//,''),fullPage:false});report.status='passed'
}catch(error){report.status='failed';report.error=error.message;process.exitCode=1}finally{await fs.writeFile(new URL('chrome-native-ai.json',directory),JSON.stringify(report,null,2));console.log(JSON.stringify(report,null,2));client.close()}
