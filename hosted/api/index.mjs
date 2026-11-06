import {randomBytes} from 'node:crypto';
import {readFileSync} from 'node:fs';
import {seal,unseal,equal,clientConfig,authorization,google,tokenFor,messages,mime,scopes,owner} from './core.mjs';
export default async function handler(req,res){
 const origin=process.env.FACTORY_ORIGIN||(process.env.VERCEL_URL?'https://'+process.env.VERCEL_URL:'');
 const key=process.env.FACTORY_CIPHER_KEY,bridgeKey=process.env.FACTORY_BRIDGE_KEY,bridgeURL=process.env.FACTORY_BRIDGE_URL;
 const reply=(code,data)=>{res.statusCode=code;res.setHeader('Content-Type','application/json; charset=utf-8');res.setHeader('Cache-Control','no-store');res.end(JSON.stringify(data));};
 const cookies=Object.fromEntries((req.headers.cookie||'').split(';').map(x=>x.trim().split('=')));
 const db=async(action,payload={})=>{const r=await fetch(bridgeURL,{method:'POST',headers:{'Content-Type':'application/json','x-factory-key':bridgeKey,'Authorization':'Bearer '+process.env.FACTORY_SUPABASE_JWT,'apikey':process.env.FACTORY_SUPABASE_JWT},body:JSON.stringify({action,payload}),signal:AbortSignal.timeout(25000)});if(!r.ok)throw Error('Операция базы не выполнена');return r.json();};
 try{
  if(!key||!bridgeKey||!bridgeURL||!origin.startsWith('https://'))return reply(503,{error:'Облачное подключение ещё не настроено'});
  const requestURL=new URL(req.url,origin);
  const path=requestURL.searchParams.has('route')?'/'+requestURL.searchParams.get('route'):requestURL.pathname.replace(/^\/api/,'');
  if(req.method==='GET'&&['/ui','/ui/app.mjs','/ui/style.css'].includes(path)){
   const assets={'/ui':[new URL('../public/index.html',import.meta.url),'text/html; charset=utf-8'],'/ui/app.mjs':[new URL('../public/app.mjs',import.meta.url),'text/javascript; charset=utf-8'],'/ui/style.css':[new URL('../public/style.css',import.meta.url),'text/css; charset=utf-8']};
   const [file,mime]=assets[path];res.statusCode=200;res.setHeader('Content-Type',mime);res.setHeader('Cache-Control','no-store');res.end(readFileSync(file));return;
  }
  if(req.method==='GET'&&path.startsWith('/demo/')){
   const parts=path.slice(6).split('/'),id=parts.shift();if(!/^[a-f0-9-]{36}$/.test(id))return reply(404,{error:'Сайт не найден'});
   let file=parts.join('/');if(!file||file.endsWith('/'))file+='index.html';else if(!file.split('/').pop().includes('.'))file+='/index.html';if(file.includes('..')||file.includes('\\'))return reply(404,{error:'Файл недоступен'});
   const data=await db('site',{command:'file',data:{id,path:file}});
   res.statusCode=200;res.setHeader('Content-Type',data.mime);res.setHeader('Cache-Control','no-store');res.setHeader('X-Robots-Tag','noindex, nofollow');res.end(Buffer.from(data.content,'base64'));return;
  }
  if(req.method==='GET'&&path==='/snapshot'){
   const csrf=randomBytes(32).toString('hex');res.setHeader('Set-Cookie',`factory_csrf=${csrf}; Path=/; HttpOnly; Secure; SameSite=Strict; Max-Age=3600`);
   const snapshot=await db('snapshot'),sites=await db('site',{command:'list'});return reply(200,{...snapshot,sites,csrf,origin});
  }
  if(req.method==='GET'&&path==='/oauth/callback'){
   const q=new URL(req.url,origin).searchParams,r=(await db('runtime'))[0];
   if(!r?.oauth_state?.cipher)throw Error('Подключение не начато');
   const pending=unseal(r.oauth_state.cipher,key);
   if(!equal(q.get('state'),pending.state)||!equal(cookies.factory_oauth,pending.browser)||Date.now()>pending.expires)throw Error('Срок подключения истёк или сессия другая');
   // Consume before exchanging, so callbacks cannot be replayed.
   await db('runtime_update',{oauth_state:null});
   if(!q.get('code'))throw Error('Google не предоставил доступ');
   const t=await google('',{form:{client_id:pending.client.client_id,client_secret:pending.client.client_secret,code:q.get('code'),code_verifier:pending.verifier,redirect_uri:origin+'/api/oauth/callback',grant_type:'authorization_code'}});
   if(!t.refresh_token||!scopes.every(x=>(t.scope||'').split(' ').includes(x)))throw Error('Google не выдал нужный постоянный доступ');
   const p=await google('profile',{token:t.access_token});if(p.emailAddress?.toLowerCase()!==owner)throw Error('Выбрана другая почта');
   await db('runtime_update',{gmail_cipher:seal({...pending.client,refresh_token:t.refresh_token},key),sync_error:null});
   res.setHeader('Set-Cookie','factory_oauth=; Path=/api/oauth; HttpOnly; Secure; SameSite=Lax; Max-Age=0');res.statusCode=303;res.setHeader('Location','/?gmail=connected');return res.end();
  }
  if(req.method!=='POST')return reply(405,{error:'Метод недоступен'});
  if(req.headers.origin!==origin||!equal(req.headers['x-factory-csrf'],cookies.factory_csrf)||!cookies.factory_csrf)return reply(403,{error:'Обновите кабинет и повторите действие'});
  let p=req.body;if(typeof p==='string')p=JSON.parse(p);if(!p){let b='';for await(const x of req){b+=x;if(b.length>150000)throw Error('Слишком большой запрос');}p=JSON.parse(b||'{}');}
  if(path==='/oauth/start'){
   const client=clientConfig(p,origin),auth=authorization(client,origin),browser=randomBytes(32).toString('hex');
   await db('runtime_update',{oauth_state:{cipher:seal({client,state:auth.state,verifier:auth.verifier,browser,expires:Date.now()+600000},key)}});
   res.setHeader('Set-Cookie',`factory_oauth=${browser}; Path=/api/oauth; HttpOnly; Secure; SameSite=Lax; Max-Age=600`);return reply(200,{url:auth.url});
  }
  if(path==='/sync'){
   const r=(await db('runtime'))[0];if(!r?.gmail_cipher)throw Error('Сначала подключите Gmail');
   try{const token=await tokenFor(unseal(r.gmail_cipher,key)),s=await db('snapshot');for(const l of s.leads)await db('import',{lead_id:l.id,messages:await messages(l.email,token)});await db('runtime_update',{sync_at:new Date().toISOString(),sync_error:null});return reply(200,{ok:true});}
   catch{await db('runtime_update',{sync_error:'Проверка почты не завершена. Дата успешной проверки не обновлена.'});throw Error('Не удалось завершить проверку Gmail');}
  }
  if(path==='/send'){
   // Credential verification precedes the atomic claim. No automatic retries.
   const r=(await db('runtime'))[0];if(!r?.gmail_cipher||!r.sending_enabled)throw Error('Отправка пока выключена');
   const token=await tokenFor(unseal(r.gmail_cipher,key));const item=await db('claim',{id:p.id});
   try{const sent=await google('messages/send',{token,body:{raw:mime(item)}});if(!sent.id)throw Error('Нет Gmail id');await db('sent',{id:p.id,provider_id:sent.id,thread_id:sent.threadId||''});return reply(200,{status:'SENT'});}
   catch{await db('unknown',{id:p.id});return reply(200,{status:'UNKNOWN'});}
  }
  if(path==='/site/proposal')return reply(200,await db('site',{command:'proposal',data:p}));
  if(path==='/site/approve')return reply(200,await db('site',{command:'approve',data:p}));
  const action=path.slice(1);if(!['lead','task','contact','draft','approve','cancel'].includes(action))return reply(404,{error:'Операция недоступна'});
  return reply(200,await db(action,p));
 }catch(error){return reply(400,{error:['Обновите кабинет и повторите действие','Сначала подключите Gmail','Отправка пока выключена','Нужен Web OAuth JSON с адресом возврата этого кабинета','Google не выдал нужный постоянный доступ','Выбрана другая почта','Не удалось завершить проверку Gmail'].includes(error.message)?error.message:'Действие не завершено. Обновите страницу и проверьте состояние.'});}
}
