// DOM integration against the real authenticated API; no browser or external navigation.
const fs=require('node:fs');
const path=require('node:path');
const assert=require('node:assert/strict');
const {JSDOM}=require(process.env.ORDER_PROFIT_JSDOM||'jsdom');
const origin=process.env.ORDER_PROFIT_TEST_ORIGIN;
const authorization='Basic '+Buffer.from('owner:'+process.env.ORDER_PROFIT_TEST_PASSWORD).toString('base64');
const root=path.resolve(__dirname,'..');
const fetchPrivate=(url,options={})=>{
 const target=new URL(url,origin);assert.equal(target.origin,origin);
 return fetch(target,{...options,headers:{...options.headers,Authorization:authorization}});
};
const wait=async(predicate)=>{for(let i=0;i<300;i++){if(predicate())return;await new Promise(r=>setTimeout(r,50));}throw Error('UI timeout');};
(async()=>{
 const dom=new JSDOM(fs.readFileSync(path.join(root,'office/web/index.html'),'utf8'),{url:origin,runScripts:'outside-only',pretendToBeVisual:true});
 const w=dom.window;w.fetch=fetchPrivate;w.confirm=()=>true;
 w.eval(fs.readFileSync(path.join(root,'office/web/app.js'),'utf8'));
 const $=id=>w.document.getElementById(id);
 await wait(()=>$('director').textContent==='Работает'&&$('cards').textContent.includes('Карточек пока нет'));
 $('sample').click();await wait(()=>$('clinic-name').textContent.includes('Тестовая'));
 $('build').click();await wait(()=>$('clinic-status').textContent==='Демо на проверке');
 assert.match($('test-results').textContent,/Проверки сборки пройдены/);
 assert.equal($('approve').disabled,true);
 $('viewed').click();await wait(()=>$('notice').textContent.includes('Просмотр этой версии'));
 $('ack').click();assert.equal($('approve').disabled,false);$('approve').click();
 await wait(()=>$('clinic-status').textContent==='Утверждено владельцем');
 w.document.querySelector('[data-tab="mail"]').click();$('make-draft').click();
 await wait(()=>$('clinic-status').textContent==='Черновик готов');
 assert.match($('letter').textContent,/НЕ ОТПРАВЛЕНО/);assert.match($('letter').textContent,/\$700/);assert.match($('letter').textContent,/\$1000/);
 w.document.querySelector('[data-tab="history"]').click();assert.match($('history').textContent,/PROPOSAL_DRAFTED/);
 const cards=await (await fetchPrivate('/api/clinics')).json();
 const card=await (await fetchPrivate('/api/clinics/'+cards[0].id)).json();
 if(process.env.ORDER_PROFIT_TEST_SNAPSHOT){
   const frame=$('preview');const demoPath=frame.getAttribute('src');
   const demo=new JSDOM(await (await fetchPrivate(demoPath)).text(),{url:new URL(demoPath,origin).href});
   for(const link of [...demo.window.document.querySelectorAll('link[rel="stylesheet"]')]){
     const style=demo.window.document.createElement('style');style.textContent=await(await fetchPrivate(link.href)).text();link.replaceWith(style);
   }
   for(const image of demo.window.document.querySelectorAll('img')){
     const response=await fetchPrivate(image.src);image.src='data:'+response.headers.get('content-type')+';base64,'+Buffer.from(await response.arrayBuffer()).toString('base64');
   }
   demo.window.document.querySelectorAll('script,link').forEach(e=>e.remove());
   frame.removeAttribute('src');frame.setAttribute('srcdoc',demo.serialize());
   $('open-demo').removeAttribute('href');
   w.document.querySelectorAll('script,link[rel="stylesheet"]').forEach(e=>e.remove());
   const style=w.document.createElement('style');style.textContent=fs.readFileSync(path.join(root,'office/web/style.css'),'utf8');w.document.head.append(style);
   const banner=w.document.createElement('p');banner.textContent='СНИМОК ВЫПОЛНЕННОГО ТЕСТА · Это вид реального кабинета после прогона, не удалённая работающая база. Рабочие действия доступны при локальном запуске run-office.cmd. Письмо не отправлено.';banner.style.cssText='background:#fff2d9;padding:16px;border-radius:8px';w.document.querySelector('main').prepend(banner);
   w.document.querySelectorAll('button,input,select,textarea').forEach(e=>e.setAttribute('disabled',''));
   w.document.querySelectorAll('[data-tab]').forEach(e=>e.removeAttribute('disabled'));
   $('preview-lang').setAttribute('disabled','');
   w.document.querySelectorAll('[data-panel]').forEach(e=>e.hidden=e.dataset.panel!=='mail');
   const tabs=w.document.createElement('script');tabs.textContent="document.querySelectorAll('[data-tab]').forEach(b=>b.onclick=()=>{document.querySelectorAll('[data-panel]').forEach(p=>p.hidden=p.dataset.panel!==b.dataset.tab);document.querySelectorAll('[data-tab]').forEach(x=>x.classList.toggle('active',x===b))});";w.document.body.append(tabs);
   fs.writeFileSync(process.env.ORDER_PROFIT_TEST_SNAPSHOT,dom.serialize());
 }
 console.log(JSON.stringify({passed:true,mode:'DRY_RUN',clinicId:card.id,status:card.status,buildId:card.job.report.buildId,htmlPages:card.job.report.tests.htmlPages,delivery:card.draft.delivery,simulatedApproval:true,uiActions:['create','build','view','acknowledge','approve','draft'],databasePersistent:true}));
 dom.window.close();
})().catch(e=>{console.error(e);process.exitCode=1;});
