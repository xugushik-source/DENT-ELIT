import test from 'node:test';import assert from 'node:assert/strict';import handler from '../api/index.mjs';
const env={FACTORY_ORIGIN:'https://office.example',FACTORY_CIPHER_KEY:'ab'.repeat(32),FACTORY_BRIDGE_KEY:'secret'.repeat(12),FACTORY_BRIDGE_URL:'https://bridge.example',FACTORY_SUPABASE_JWT:'public-jwt'};
Object.assign(process.env,env);
function response(){return {headers:{},setHeader(k,v){this.headers[k]=v;},end(v){this.body=v;}};}
test('mutations reject missing CSRF and foreign origin before accessing database',async()=>{let n=0;const old=global.fetch;global.fetch=async()=>{n++;throw Error('should not call');};try{for(const origin of ['https://evil.example','https://office.example']){const r=response();await handler({method:'POST',url:'/api/lead',headers:{origin},body:{name:'x'}},r);assert.equal(r.statusCode,403);}assert.equal(n,0);}finally{global.fetch=old;}});
test('snapshot supplies CSRF cookie without server credentials',async()=>{const old=global.fetch;global.fetch=async()=>({ok:true,json:async()=>({leads:[],tasks:[],messages:[],outbox:[],connection:{configured:false,send_enabled:false}})});try{const r=response();await handler({method:'GET',url:'/api/snapshot',headers:{}},r);assert.equal(r.statusCode,200);assert(r.headers['Set-Cookie'].includes('HttpOnly; Secure; SameSite=Strict'));assert(!r.body.includes(env.FACTORY_BRIDGE_KEY));assert(!r.body.includes(env.FACTORY_CIPHER_KEY));assert(JSON.parse(r.body).csrf);}finally{global.fetch=old;}});
test('disabled send never calls Google',async()=>{const old=global.fetch;let n=0;global.fetch=async url=>{assert.equal(url,'https://bridge.example');n++;return {ok:true,json:async()=>[{sending_enabled:false,gmail_cipher:null}]};};try{const r=response();await handler({method:'POST',url:'/api/send',headers:{origin:env.FACTORY_ORIGIN,cookie:'factory_csrf=c','x-factory-csrf':'c'},body:{id:'x'}},r);assert.equal(r.statusCode,400);assert.equal(n,1);}finally{global.fetch=old;}});

test('cabinet assets are served by the bundled Node handler without a static routing dependency',async()=>{for(const [path,mime,body] of [['ui','text/html','Order &amp; Profit'],['ui/app.mjs','text/javascript','async function load'],['ui/style.css','text/css',':root']]){const r=response();await handler({method:'GET',url:'/api/index.mjs?route='+path,headers:{}},r);assert.equal(r.statusCode,200);assert(r.headers['Content-Type'].includes(mime));assert(String(r.body).includes(body));}});

test('client link is released only after all languages and asset hashes pass; failed probes revoke it',async()=>{
 const old=global.fetch;const {createHash}=await import('node:crypto');const css=Buffer.from('body{}'),hash=createHash('sha256').update(css).digest('hex');
 for(const fail of [false,true]){
  const commands=[];global.fetch=async(url,opts)=>{
   if(url==='https://bridge.example'){
    const input=JSON.parse(opts.body);commands.push(input.payload.command);
    if(input.payload.command==='details')return Response.json({synthetic:false,status:'APPROVED',report:{tests:{passed:true},origin:'https://owner.example',files:{'css/main.css':hash}}});
    return Response.json({expires_at:'2026-11-14T00:00:00Z'});
   }
   const parsed=new URL(url),token=parsed.pathname.split('/')[2];
   if(fail&&parsed.pathname.endsWith('/en/'))return new Response('unavailable',{status:404});
   if(parsed.pathname.endsWith('.css'))return new Response(css);
   const language=parsed.pathname.split('/')[3];return new Response('<html lang="'+language+'"><a href="/p/'+token+'/">site</a></html>',{headers:{'Content-Type':'text/html'}});
  };
  const r=response();await handler({method:'POST',url:'/api/site/share',headers:{origin:env.FACTORY_ORIGIN,cookie:'factory_csrf=c','x-factory-csrf':'c'},body:{id:'x'}},r);
  assert.equal(r.statusCode,fail?400:200);assert(commands.includes('issue'));assert.equal(commands.includes('verify'),!fail);assert.equal(commands.includes('revoke'),fail);
 }
 global.fetch=old;
});
