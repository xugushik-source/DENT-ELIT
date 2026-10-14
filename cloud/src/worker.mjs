import {owner,csrf,equal,hash} from './auth.mjs';
import {validate,facts,value,approved,decode,get,change} from './data.mjs';
import {dispatch} from './github.mjs';
import sample from './sample.json' with {type:'json'};
import proposals from './proposals.json' with {type:'json'};
const uuid=/^[a-f0-9-]{36}$/,sha=/^[a-f0-9]{64}$/;
const date=()=>new Date().toISOString();
const response=(body,status=200,extra={})=>new Response(typeof body==='string'||body instanceof ReadableStream?body:JSON.stringify(body),{status,headers:{'Content-Type':typeof body==='string'?'text/plain':'application/json; charset=utf-8','Cache-Control':'private, no-store','X-Robots-Tag':'noindex, nofollow, noarchive','X-Content-Type-Options':'nosniff','Referrer-Policy':'no-referrer',...extra}});
async function payload(r,max=2e6){if(!r.headers.get('content-type')?.startsWith('application/json'))throw Error('Требуется JSON');const t=await r.text();if(new TextEncoder().encode(t).length>max)throw Error('Запрос слишком велик');return JSON.parse(t);}
async function list(env){return (await env.DB.prepare('SELECT id,name,country,city,language,synthetic,status,version,revision,created_at,current_job FROM clinics ORDER BY created_at DESC').all()).results;}
async function settings(env){return {paused:Boolean((await env.DB.prepare('SELECT paused FROM settings WHERE id=1').first()).paused),mode:'DRY_RUN',mailConnected:false,publicAccess:false,cloud:true,runnerConnected:Boolean(env.GITHUB_DISPATCH_TOKEN&&env.RUNNER_REPOSITORY)};}
async function completeRecord(env,c){
 if(!c.job||c.job.status!=='DONE'||c.job.revision!==c.revision)throw Error('Нужна актуальная завершённая сборка');
 const r=c.job.report;validate(c.config);
 if(!r?.tests?.passed||r.clinicId!==c.id||r.revision!==c.revision)throw Error('Результат сборки не соответствует карточке');
 // R2 object names are content-addressed. Check each immutable version before approval.
 for(const [p,h]of Object.entries(r.files)){const obj=await env.FILES.head('site/'+c.job.id+'/'+p);if(!obj||obj.customMetadata?.sha256!==h)throw Error('Демо изменилось или файл отсутствует');}
 return r;
}
async function create(env,actor,c,name,country,city){
 validate(c);
 const t=date(),body=JSON.stringify(c);
 await env.DB.batch([
  env.DB.prepare("INSERT INTO clinics(id,name,country,city,language,synthetic,status,version,revision,config,created_at) VALUES(?,?,?,?,?,?,'DATA_REQUIRED',1,1,?,?)").bind(c.clinicId,name,country,city,c.languages.default,Number(c.synthetic),body,t),
  env.DB.prepare('INSERT INTO config_versions VALUES(?,1,?,?)').bind(c.clinicId,body,t),
  env.DB.prepare('INSERT INTO events(clinic_id,kind,actor,detail,created_at) VALUES(?,?,?,?,?)').bind(c.clinicId,'CARD_CREATED',actor,JSON.stringify({synthetic:c.synthetic}),t)
 ]);return get(env,c.clinicId);
}
export function application(verifyOwner=owner,startJob=dispatch){
 return {async fetch(request,env){
  const url=new URL(request.url),path=decodeURIComponent(url.pathname);
  try{
   if(path.startsWith('/api/runner/'))return await runner(request,env,path);
   let actor;try{actor=await verifyOwner(request,env);}catch{return response({error:'Вход только для владельца'},401);}
   if(!env.DB||!env.FILES||!env.ASSETS)return response({error:'Облачная инфраструктура ещё не подключена'},503);
   const token=await csrf(env,actor,url.origin);
   if(request.method==='GET'){
    if(path==='/api/bootstrap')return response({csrf:token,settings:await settings(env),clinics:await list(env)});
    if(path==='/api/clinics')return response(await list(env));
    if(path.startsWith('/api/clinics/'))return response(await get(env,path.split('/')[3]));
    if(path.startsWith('/demo/')){
     const p=path.split('/'),id=p[2];if(!uuid.test(id))throw Error('Недопустимый ID');
     const j=await env.DB.prepare('SELECT status,report FROM jobs WHERE id=?').bind(id).first();if(!j||j.status!=='DONE')return response('Демо не готово',404);
     let file=p.slice(3).join('/');if(!file||file.endsWith('/'))file+='index.html';
     if(file.split('/').some(s=>s==='..'||s==='.'||!s))throw Error('Недопустимый путь');
     if(!(file in JSON.parse(j.report).files))return response('Не найдено',404);
     const obj=await env.FILES.get('site/'+id+'/'+file);if(!obj)return response('Не найдено',404);
     return response(obj.body,200,{'Content-Type':obj.httpMetadata?.contentType||'application/octet-stream'});
    }
    if(['/', '/app.js','/style.css'].includes(path)){
     const asset=await env.ASSETS.fetch(request);const headers=new Headers(asset.headers);
     for(const[k,v]of Object.entries({'Cache-Control':'private, no-store','X-Robots-Tag':'noindex, nofollow','Content-Security-Policy':"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; frame-ancestors 'self'; form-action 'none'"}))headers.set(k,v);
     return new Response(asset.body,{status:asset.status,headers});
    }
    return response({error:'Не найдено'},404);
   }
   if(request.method!=='POST')return response({error:'Недопустимый метод'},405);
   if(request.headers.get('Origin')!==url.origin||!equal(request.headers.get('X-CSRF-Token'),token))return response({error:'Запрос не подтверждён владельцем'},403);
   const b=await payload(request);
   if(path==='/api/director'){if(typeof b.paused!=='boolean')throw Error('Неверный paused');await env.DB.prepare('UPDATE settings SET paused=? WHERE id=1').bind(Number(b.paused)).run();return response(await settings(env));}
   if(path==='/api/sample'){
    const c=structuredClone(sample.config),old=c.clinicId,id=crypto.randomUUID();
    const cfg=JSON.parse(JSON.stringify(c).replaceAll(old,id));cfg.revision=1;cfg.templateCommit=env.TEMPLATE_COMMIT;
    for(const[,f]of facts(cfg))if(approved.has(f.status))f.checkedAt=date();for(const s of cfg.sources)s.retrievedAt=date();
    const image=Uint8Array.from(atob(sample.image),x=>x.charCodeAt(0));const reservation=await env.DB.prepare('UPDATE settings SET stored_bytes=stored_bytes+? WHERE id=1 AND stored_bytes+?<=?').bind(image.byteLength,image.byteLength,Number(env.MAX_STORED_BYTES||200000000)).run();if(reservation.meta.changes!==1)throw Error('Достигнут лимит хранилища');
    await env.FILES.put('assets/'+id+'/synthetic-illustration',image,{httpMetadata:{contentType:'image/png'}});
    return response(await create(env,actor,cfg,'Тестовая клиника Order & Profit','Армения','Ереван'),201);
   }
   if(path==='/api/clinics'){
    // Reuse an empty neutral package: no clinic facts inherited from the sample.
    if(!['ru','en','hy'].includes(b.language)||[b.name,b.country,b.city].some(v=>typeof v!=='string'||!v.trim()||v.length>200))throw Error('Заполните название, страну, город и язык');
    const c=structuredClone(sample.config);c.clinicId=crypto.randomUUID();c.synthetic=false;c.revision=1;c.templateCommit=env.TEMPLATE_COMMIT;
    for(const[,f]of facts(c)){f.value=null;f.status='UNKNOWN';f.sourceIds=[];f.checkedAt=null;f.reviewer=null;}
    c.sources=[];c.assets=[];c.languages={enabled:['ru','en','hy'],default:b.language,uiVersion:'v1'};
    // The unknown name is valid schema but not yet buildable.
    const t=date();await env.DB.batch([env.DB.prepare("INSERT INTO clinics(id,name,country,city,language,synthetic,status,version,revision,config,created_at) VALUES(?,?,?,?,?,0,'DATA_REQUIRED',1,1,?,?)").bind(c.clinicId,b.name,b.country,b.city,b.language,JSON.stringify(c),t),env.DB.prepare('INSERT INTO config_versions VALUES(?,1,?,?)').bind(c.clinicId,JSON.stringify(c),t)]);
    return response(await get(env,c.clinicId),201);
   }
   const parts=path.split('/');if(parts.length!==5||parts[1]!=='api'||parts[2]!=='clinics')return response({error:'Отправка и публикация отключены'},404);
   const c=await get(env,parts[3]),action=parts[4];
   if(action==='validate')return response({valid:true,pending:validate(c.config),usedAssets:[]});
   if(action==='config'){
    const cfg=b.config;if(cfg.clinicId!==c.id||cfg.synthetic!==c.synthetic||cfg.deploymentMode!=='demo'||cfg.languages.default!==c.language)throw Error('Конфигурация другой карточки');
    const old=new Map(facts(c.config));for(const[p,f]of facts(cfg)){const prev=old.get(p);if(prev&&JSON.stringify(prev.value)!==JSON.stringify(f.value)&&approved.has(prev.status)&&approved.has(f.status)&&['sourceIds','checkedAt','reviewer'].every(k=>JSON.stringify(prev[k])===JSON.stringify(f[k])))f.status='SOURCED';}
    // Validate full schema, allowing an unknown name during data entry.
    const {default:schema}=await import('./schema.mjs');if(!schema(cfg))throw Error('Неверная схема');cfg.revision=c.revision+1;
    return response(await change(env,c,b.version,{config:JSON.stringify(cfg),revision:cfg.revision,status:'DATA_REQUIRED',current_job:null,approval:null,draft:null},'CONFIG_SAVED',{approvalInvalidated:true},actor,(nonce,t)=>[env.DB.prepare('INSERT INTO config_versions SELECT id,revision,config,? FROM clinics WHERE id=? AND nonce=?').bind(t,c.id,nonce)]));
   }
   if(action==='build'){
    validate(c.config);if((await settings(env)).paused)throw Error('Очередь остановлена');
    if(c.job&&['RUNNING','QUEUED'].includes(c.job.status)){if(Date.now()-Date.parse(c.job.created_at)<15*60000)throw Error('Сборка уже выполняется; не запускайте дубликат');await env.DB.prepare("UPDATE jobs SET status='EXPIRED',lease=NULL WHERE id=? AND status IN ('QUEUED','RUNNING')").bind(c.job.id).run();}
    if(!env.GITHUB_DISPATCH_TOKEN||!env.RUNNER_REPOSITORY)throw Error('Закрытый облачный исполнитель ещё не подключён');
    const n=await env.DB.prepare('SELECT COUNT(*) AS n FROM jobs WHERE created_at>=?').bind(date().slice(0,10)).first();if(n.n>=Number(env.MAX_BUILDS_DAY||5))throw Error('Достигнут дневной лимит сборок');
    const id=crypto.randomUUID();await change(env,c,b.version,{status:'QUEUED',current_job:id,approval:null,draft:null},'BUILD_QUEUED',{jobId:id},actor,(nonce,t)=>[env.DB.prepare("INSERT INTO jobs(id,clinic_id,revision,config,status,created_at) SELECT ?,id,revision,config,'QUEUED',? FROM clinics WHERE id=? AND nonce=?").bind(id,t,c.id,nonce)]);
    try{await startJob(env,id);}catch(e){await env.DB.prepare("UPDATE jobs SET status='FAILED',error=? WHERE id=? AND status='QUEUED'").bind(String(e.message),id).run();const fresh=await get(env,c.id);if(fresh.current_job===id)await change(env,fresh,fresh.version,{status:'BUILD_FAILED'},'DISPATCH_FAILED',{},'director');throw e;}
    return response({jobId:id},202);
   }
   if(action==='revise'){if(typeof b.comment!=='string'||!b.comment.trim()||b.comment.length>4000)throw Error('Укажите замечания');return response(await change(env,c,b.version,{status:'REVISION_REQUESTED',approval:null,draft:null},'REVISION_REQUESTED',{comment:b.comment},actor));}
   const r=await completeRecord(env,c);
   if(action==='viewed'){if(c.version!==b.version)throw Error('Карточка изменилась');await env.DB.prepare('UPDATE jobs SET viewed_at=? WHERE id=?').bind(date(),c.job.id).run();return response(await get(env,c.id));}
   if(action==='approve'){
    if(!c.job.viewed_at||JSON.stringify([...(b.pendingPaths||[])].sort())!==JSON.stringify(r.pending.map(p=>p.path).sort()))throw Error('Требуется просмотр и подтверждение всех неподтверждённых полей');
    const a={build_id:r.buildId,configRevision:c.revision,owner_id:actor,approved_at:date(),simulation:c.synthetic};
    return response(await change(env,c,b.version,{status:'OWNER_APPROVED',approval:JSON.stringify(a),draft:null},'OWNER_APPROVED',a,actor));
   }
   if(action==='draft'){
    if(!c.approval||c.approval.build_id!==r.buildId||c.approval.configRevision!==c.revision)throw Error('Утвердите текущую сборку');
    const d=structuredClone(proposals[c.language]);d.to=value(c.config.contact.email);if(d.to)d.blockers=d.blockers.filter(x=>x!=='RECIPIENT_UNVERIFIED');d.body=d.body.replaceAll('__CLINIC_NAME__',value(c.config.brand.name));d.subject=d.subject.replaceAll('__CLINIC_NAME__',value(c.config.brand.name));d.buildId=r.buildId;d.revision=c.revision;d.createdAt=date();d.synthetic=c.synthetic;
    return response(await change(env,c,b.version,{status:'DRAFT_READY',draft:JSON.stringify(d)},'PROPOSAL_DRAFTED',{delivery:'NOT_SENT'},actor));
   }
   return response({error:'Неизвестное действие'},404);
  }catch(e){return response({error:e.message||'Ошибка облачного процесса'},400);}
 }};
}
async function runner(request,env,path){
 if((env.BUILD_SECRET||'').length<32||!equal(request.headers.get('Authorization'),'Bearer '+env.BUILD_SECRET))return response({error:'Unauthorized runner'},401);
 const p=path.split('/'),id=p[4];if(!uuid.test(id||''))throw Error('Invalid job');
 let j=await env.DB.prepare('SELECT * FROM jobs WHERE id=?').bind(id).first();if(!j)throw Error('Missing job');if(Date.now()-Date.parse(j.created_at)>15*60000)throw Error('Job expired; owner can retry');
 if(p[5]==='claim'&&request.method==='POST'){
  const lease=crypto.randomUUID();const changed=await env.DB.prepare("UPDATE jobs SET status='RUNNING',lease=? WHERE id=? AND status='QUEUED'").bind(lease,id).run();if(changed.meta.changes!==1)throw Error('Job already claimed or expired');
  const c=await get(env,j.clinic_id);if(c.current_job===id&&c.revision===j.revision)await change(env,c,c.version,{status:'BUILDING'},'BUILD_STARTED',{jobId:id},'runner');
  return response({config:JSON.parse(j.config),lease,templateCommit:env.TEMPLATE_COMMIT});
 }
 if(!equal(request.headers.get('X-Job-Lease'),j.lease)||j.status!=='RUNNING')throw Error('Invalid or expired lease');
 if(p[5]==='asset'&&request.method==='GET'){
  const ref=p[6];const cfg=JSON.parse(j.config);if(!cfg.assets.some(a=>a.storageRef===ref))throw Error('Unknown asset');const obj=await env.FILES.get('assets/'+j.clinic_id+'/'+ref);if(!obj)throw Error('Missing asset');return new Response(obj.body);
 }
 if(p[5]==='file'&&request.method==='PUT'){
  const file=p.slice(6).join('/');if(!file||file.length>300||file.split('/').some(s=>!s||s==='..'||s==='.')||!/^[-a-zA-Z0-9_./]+$/.test(file)||!['html','css','js','txt','png','jpg','webp'].includes(file.split('.').at(-1)))throw Error('Unsafe file');
  const blob=await request.arrayBuffer();if(blob.byteLength>10e6)throw Error('File too large');const sum=await hash(blob);if(sum!==request.headers.get('X-File-SHA256'))throw Error('Hash mismatch');
  const key='site/'+id+'/'+file,existing=await env.FILES.head(key);
  if(existing){if(existing.customMetadata?.sha256!==sum)throw Error('Artifact is immutable');return response({stored:true});}
  const reservation=await env.DB.prepare('UPDATE settings SET stored_bytes=stored_bytes+? WHERE id=1 AND stored_bytes+?<=?').bind(blob.byteLength,blob.byteLength,Number(env.MAX_STORED_BYTES||200000000)).run();
  if(reservation.meta.changes!==1)throw Error('Storage budget reached; no overage or automatic upgrade');
  const types={html:'text/html; charset=utf-8',css:'text/css',js:'text/javascript',txt:'text/plain',png:'image/png',jpg:'image/jpeg',webp:'image/webp'};
  await env.FILES.put(key,blob,{customMetadata:{sha256:sum},httpMetadata:{contentType:types[file.split('.').at(-1)]}});return response({stored:true});
 }
 if(p[5]==='finish'&&request.method==='POST'){
  const b=await payload(request);const c=await get(env,j.clinic_id),r=b.report;
  if(b.error){await env.DB.prepare("UPDATE jobs SET status='FAILED',error=?,finished_at=? WHERE id=?").bind('Сборка завершилась ошибкой; требуется проверка исполнителя',date(),id).run();if(c.current_job===id)await change(env,c,c.version,{status:'BUILD_FAILED'},'BUILD_FAILED',{},'runner');return response({saved:true});}
  if(!r?.tests?.passed||r.clinicId!==j.clinic_id||r.revision!==j.revision||r.synthetic!==Boolean(c.synthetic)||r.mode!=='demo'||r.origin!==new URL(request.url).origin||!r.files||!Object.keys(r.files).length||r.basePath!=='/demo/'+id||r.templateCommit!==env.TEMPLATE_COMMIT||!sha.test(r.buildId))throw Error('Invalid report');
  if(JSON.stringify(r.pending.map(p=>p.path).sort())!==JSON.stringify(validate(JSON.parse(j.config)).map(p=>p.path).sort()))throw Error('Incomplete pending fields');
  for(const[file,h]of Object.entries(r.files)){if(!sha.test(h)||file.includes('..'))throw Error('Invalid manifest');const obj=await env.FILES.head('site/'+id+'/'+file);if(!obj||obj.customMetadata?.sha256!==h)throw Error('Incomplete artifact');}
  const stale=c.current_job!==id||c.revision!==j.revision;
  await env.DB.prepare('UPDATE jobs SET status=?,report=?,finished_at=?,lease=NULL WHERE id=?').bind(stale?'SUPERSEDED':'DONE',JSON.stringify(r),date(),id).run();
  if(!stale)await change(env,c,c.version,{status:'DEMO_READY'},'BUILD_DONE',{buildId:r.buildId},'runner');return response({saved:true,stale});
 }
 return response({error:'Unknown runner action'},404);
}
export default application();
