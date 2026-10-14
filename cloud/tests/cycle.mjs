import {JSDOM} from 'jsdom';
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {generateKeyPair,exportJWK,SignJWT} from 'jose';
import {build} from 'esbuild';
import {Miniflare} from 'miniflare';
import {readFileSync,writeFileSync,mkdtempSync,mkdirSync,readdirSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join,resolve} from 'node:path';
import {createServer} from 'node:http';
import {promisify} from 'node:util';
import {execFile,execFileSync} from 'node:child_process';
import {hash} from '../src/auth.mjs';
const root=resolve('..'),origin='https://office.example.invalid',commit=execFileSync('git',['rev-parse','HEAD'],{cwd:root,encoding:'utf8'}).trim();

test('private cloud cycle with actual D1, R2 and Python generator', {timeout:120000},async()=>{
 const {privateKey,publicKey}=await generateKeyPair('RS256');const jwk=await exportJWK(publicKey);jwk.kid='test';
 const entry=`import {application} from './src/worker.mjs'; import {verifyToken} from './src/auth.mjs'; import {createLocalJWKSet} from 'jose';
 const keys=createLocalJWKSet({keys:[${JSON.stringify(jwk)}]});const app=application(r=>verifyToken(r.headers.get('Cf-Access-Jwt-Assertion'),keys,'https://test.cloudflareaccess.com','office','owner@example.invalid'),async()=>{});
 export default {async fetch(r,e){if(new URL(r.url).pathname==='/test-init'){await e.DB.exec(${JSON.stringify(readFileSync('migrations/0001.sql','utf8').replaceAll('\n',' '))});return new Response('ok');}return app.fetch(r,e);}};`;
 const bundled=await build({stdin:{contents:entry,resolveDir:resolve('.'),sourcefile:'test-entry.mjs'},bundle:true,write:false,format:'esm',platform:'browser',target:'es2022'});
 const mf=new Miniflare({modules:true,script:bundled.outputFiles[0].text,compatibilityDate:'2026-07-30',d1Databases:['DB'],r2Buckets:['FILES'],bindings:{CSRF_SECRET:'c'.repeat(40),BUILD_SECRET:'b'.repeat(40),TEMPLATE_COMMIT:commit,GITHUB_DISPATCH_TOKEN:'test-only',RUNNER_REPOSITORY:'test/private',MAX_BUILDS_DAY:'2'},serviceBindings:{ASSETS:()=>new Response('office')}});
 try{
 await mf.ready;
 const req=async(path,{method='GET',body,token,extra={}}={})=>mf.dispatchFetch(origin+path,{method,headers:{...(token?{'Cf-Access-Jwt-Assertion':token}:{}),...(body?{'Content-Type':'application/json'}:{}),...extra},body:body?JSON.stringify(body):undefined});
 const token=await new SignJWT({email:'owner@example.invalid'}).setProtectedHeader({alg:'RS256',kid:'test'}).setIssuer('https://test.cloudflareaccess.com').setAudience('office').setExpirationTime('5m').sign(privateKey);
 assert.equal((await req('/test-init')).status,200);
 for(const p of ['/','/app.js','/api/bootstrap','/demo/123/'])assert.equal((await req(p)).status,401);
 const wrong=await new SignJWT({email:'other@example.invalid'}).setProtectedHeader({alg:'RS256',kid:'test'}).setIssuer('https://test.cloudflareaccess.com').setAudience('office').setExpirationTime('5m').sign(privateKey);
 assert.equal((await req('/api/bootstrap',{token:wrong})).status,401);
 for(const [aud,exp]of [['wrong','5m'],['office','-5m']]){const t=await new SignJWT({email:'owner@example.invalid'}).setProtectedHeader({alg:'RS256',kid:'test'}).setIssuer('https://test.cloudflareaccess.com').setAudience(aud).setExpirationTime(exp).sign(privateKey);assert.equal((await req('/api/bootstrap',{token:t})).status,401);}
 const bootstrap=await(await req('/api/bootstrap',{token})).json();assert.equal(bootstrap.settings.mailConnected,false);
 const post=async(path,body)=>{const r=await req(path,{method:'POST',body,token,extra:{Origin:origin,'X-CSRF-Token':bootstrap.csrf}});const b=await r.json();return {status:r.status,body:b};};
 assert.equal((await req('/api/sample',{method:'POST',body:{},token})).status,403);
 let result=await post('/api/sample',{});assert.equal(result.status,201,JSON.stringify(result.body));let c=result.body;
 const get=async()=> (await req('/api/clinics/'+c.id,{token})).json();
 assert.equal((await post('/api/clinics/'+c.id+'/validate',{})).status,200);
 result=await post('/api/clinics/'+c.id+'/build',{version:c.version});assert.equal(result.status,202,JSON.stringify(result.body));const job=result.body.jobId;c=await get();
 assert.equal((await post('/api/clinics/'+c.id+'/build',{version:c.version})).status,400);
 const runnerHeaders={Authorization:'Bearer '+'b'.repeat(40)};
 const claim=await(await req('/api/runner/jobs/'+job+'/claim',{method:'POST',body:{},extra:runnerHeaders})).json();assert.ok(claim.lease);
 assert.equal((await req('/api/runner/jobs/'+job+'/claim',{method:'POST',body:{},extra:runnerHeaders})).status,400);
 const headers={...runnerHeaders,'X-Job-Lease':claim.lease};
 const work=mkdtempSync(join(tmpdir(),'cloud-cycle-'));const assets=join(work,'assets');mkdirSync(assets);
 for(const a of claim.config.assets){const r=await req('/api/runner/jobs/'+job+'/asset/'+a.storageRef,{extra:headers});assert.equal(r.status,200);writeFileSync(join(assets,a.storageRef),Buffer.from(await r.arrayBuffer()));}
 const config=join(work,'config.json');writeFileSync(config,JSON.stringify(claim.config));
 const output=execFileSync('python',['factory.py','build','--config',config,'--assets',assets,'--workspace',join(work,'builds'),'--origin',origin,'--base-path','/demo/'+job],{cwd:root,encoding:'utf8',maxBuffer:10e6});const report=JSON.parse(output);assert.equal(report.tests.passed,true);
 const folder=join(work,'builds',report.clinicId,report.buildId,'site');
 for(const [file,sum]of Object.entries(report.files)){const r=await mf.dispatchFetch(origin+'/api/runner/jobs/'+job+'/file/'+file,{method:'PUT',headers:{...headers,'X-File-SHA256':sum},body:readFileSync(join(folder,file))});assert.equal(r.status,200,await r.text());}
 const bad=structuredClone(report);bad.origin='https://wrong.invalid';assert.equal((await req('/api/runner/jobs/'+job+'/finish',{method:'POST',body:{report:bad},extra:headers})).status,400);
 result=await req('/api/runner/jobs/'+job+'/finish',{method:'POST',body:{report},extra:headers});assert.equal(result.status,200,await result.text());
 c=await get();assert.equal(c.status,'DEMO_READY');
 assert.equal((await req('/demo/'+job+'/ru/')).status,401);
 const preview=await req('/demo/'+job+'/ru/',{token});assert.equal(preview.status,200);assert.match(await preview.text(),/noindex/);
 assert.equal((await post('/api/clinics/'+c.id+'/approve',{version:c.version,pendingPaths:report.pending.map(p=>p.path)})).status,400);
 assert.equal((await post('/api/clinics/'+c.id+'/viewed',{version:c.version})).status,200);
 result=await post('/api/clinics/'+c.id+'/approve',{version:c.version,pendingPaths:report.pending.map(p=>p.path)});assert.equal(result.status,200,JSON.stringify(result.body));c=result.body;
 result=await post('/api/clinics/'+c.id+'/draft',{version:c.version});assert.equal(result.status,200);c=result.body;assert.equal(c.status,'DRAFT_READY');assert.equal(c.draft.delivery,'NOT_SENT');assert.equal(c.draft.sendEnabled,false);assert.match(c.draft.body,/700/);
 assert.equal((await post('/api/send',{})).status,404);
 const changed=structuredClone(c.config);changed.brand.name.value='Changed';result=await post('/api/clinics/'+c.id+'/config',{version:c.version,config:changed});assert.equal(result.status,200);assert.equal(result.body.approval,null);assert.equal(result.body.config.brand.name.status,'SOURCED');
 assert.equal((await post('/api/clinics/'+c.id+'/config',{version:c.version,config:changed})).status,400);
 // Exercise the actual Python runner too; only its HTTPS transport is replaced
 // by this test-local bridge. Production CLI has no HTTP mode or auth bypass.
 result=await post('/api/sample',{});let second=result.body;
 result=await post('/api/clinics/'+second.id+'/build',{version:second.version});const secondJob=result.body.jobId;assert.ok(secondJob);
 const server=createServer(async(r,res)=>{try{const chunks=[];for await(const chunk of r)chunks.push(chunk);const reply=await mf.dispatchFetch(origin+r.url,{method:r.method,headers:r.headers,body:r.method==='GET'?undefined:Buffer.concat(chunks)});res.writeHead(reply.status,Object.fromEntries(reply.headers));res.end(Buffer.from(await reply.arrayBuffer()));}catch{res.writeHead(500);res.end('test bridge failure');}});
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
 const py=`import importlib.util,urllib.request,os
s=importlib.util.spec_from_file_location('runner','cloud/runner.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class Bridge:
 def open(self,r,timeout):
  u='http://127.0.0.1:'+os.environ['TEST_PORT']+r.full_url.removeprefix(os.environ['FACTORY_CLOUD_ORIGIN'])
  return urllib.request.urlopen(urllib.request.Request(u,data=r.data,headers=r.headers,method=r.method),timeout=timeout)
m.run(os.environ['FACTORY_JOB_ID'],opener=Bridge())
`;
 try{await promisify(execFile)('python',['-c',py],{cwd:root,env:{...process.env,FACTORY_JOB_ID:secondJob,FACTORY_CLOUD_ORIGIN:origin,FACTORY_BUILD_SECRET:'b'.repeat(40),CF_ACCESS_CLIENT_ID:'test-only',CF_ACCESS_CLIENT_SECRET:'test-only',TRUSTED_TEMPLATE_SHA:commit,TEST_PORT:String(server.address().port)}});}finally{await new Promise(resolve=>server.close(resolve));}
 second=await(await req('/api/clinics/'+second.id,{token})).json();assert.equal(second.status,'DEMO_READY');assert.equal(second.job.report.tests.passed,true);
 result=await post('/api/clinics/'+second.id+'/build',{version:second.version});assert.equal(result.status,400);assert.match(result.body.error,/лимит/);
 await post('/api/director',{paused:true});result=await post('/api/clinics/'+second.id+'/build',{version:second.version});assert.equal(result.status,400);assert.match(result.body.error,/остановлена/);
 // Real office event handlers operate against the authenticated emulated API.
 const dom=new JSDOM(readFileSync('public/index.html','utf8'),{url:origin,runScripts:'outside-only'}),w=dom.window;
 w.setInterval=()=>0;w.confirm=()=>true;
 w.fetch=async(path,options={})=>mf.dispatchFetch(origin+path,{...options,headers:{...options.headers,'Cf-Access-Jwt-Assertion':token,Origin:origin}});
 w.eval(readFileSync('public/app.js','utf8'));
 const wait=async(fn)=>{for(let i=0;i<100;i++){if(fn())return;await new Promise(r=>setTimeout(r,20));}throw Error('Office UI timeout');};
 await wait(()=>w.document.querySelector('[data-id="'+second.id+'"]'));
 w.document.querySelector('[data-id="'+second.id+'"]').click();await wait(()=>w.document.getElementById('revision').textContent.includes(second.id.slice(0,8)));
 const el=id=>w.document.getElementById(id);w.document.querySelector('[data-tab="demo"]').click();el('viewed').click();await wait(()=>el('notice').textContent.includes('Просмотр этой версии'));el('ack').click();el('approve').click();await wait(()=>el('clinic-status').textContent==='Утверждено владельцем');
 w.document.querySelector('[data-tab="mail"]').click();el('make-draft').click();await wait(()=>el('clinic-status').textContent==='Черновик готов');assert.match(el('letter').textContent,/НЕ ОТПРАВЛЕНО/);
 if(process.env.FACTORY_OFFICE_SNAPSHOT){
  const frame=el('preview');const page=await req('/demo/'+secondJob+'/ru/',{token});const demo=new JSDOM(await page.text(),{url:origin+'/demo/'+secondJob+'/ru/'});
  for(const link of [...demo.window.document.querySelectorAll('link[rel="stylesheet"]')]){const css=await mf.dispatchFetch(link.href,{headers:{'Cf-Access-Jwt-Assertion':token}});const style=demo.window.document.createElement('style');style.textContent=await css.text();link.replaceWith(style);}
  for(const image of demo.window.document.querySelectorAll('img')){const img=await mf.dispatchFetch(image.src,{headers:{'Cf-Access-Jwt-Assertion':token}});image.src='data:'+img.headers.get('content-type')+';base64,'+Buffer.from(await img.arrayBuffer()).toString('base64');}
  demo.window.document.querySelectorAll('script,link').forEach(e=>e.remove());frame.removeAttribute('src');frame.setAttribute('srcdoc',demo.serialize());el('open-demo').removeAttribute('href');
  w.document.querySelectorAll('script,link[rel="stylesheet"]').forEach(e=>e.remove());const style=w.document.createElement('style');style.textContent=readFileSync('public/style.css','utf8');w.document.head.append(style);
  const banner=w.document.createElement('p');banner.textContent='СНИМОК ПРОВЕРЕННОГО КАБИНЕТА · Цикл выполнен в эмуляторе Cloudflare с настоящим генератором. Это сохранённый результат теста, не размещённый облачный сервис. Для постоянного входа нужно подключить Cloudflare и закрытый исполнитель. Письмо не отправлено.';banner.style.cssText='background:#fff2d9;padding:16px;border-radius:8px';w.document.querySelector('main').prepend(banner);
  w.document.querySelectorAll('button,input,select,textarea').forEach(e=>e.disabled=true);w.document.querySelectorAll('[data-tab]').forEach(e=>e.disabled=false);
  const tabs=w.document.createElement('script');tabs.textContent="document.querySelectorAll('[data-tab]').forEach(b=>b.onclick=()=>{document.querySelectorAll('[data-panel]').forEach(p=>p.hidden=p.dataset.panel!==b.dataset.tab);document.querySelectorAll('[data-tab]').forEach(x=>x.classList.toggle('active',x===b))});";w.document.body.append(tabs);
  writeFileSync(process.env.FACTORY_OFFICE_SNAPSHOT,dom.serialize());
 }
 dom.window.close();
 if(process.env.FACTORY_TEST_SNAPSHOT)writeFileSync(process.env.FACTORY_TEST_SNAPSHOT,JSON.stringify({card:c,report,platform:'Miniflare D1/R2',hosted:false}));
 console.log(JSON.stringify({status:c.status,delivery:c.draft.delivery,htmlPages:report.tests.htmlPages,files:Object.keys(report.files).length,buildAI:report.cost.buildAI,platform:'Miniflare D1/R2 + actual generator'}));
 }finally{await mf.dispose();}
});
