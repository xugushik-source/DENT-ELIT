// Server-to-server only. No browser CORS and no credentials in responses.
Deno.serve(async (req: Request) => {
 const fail=(status:number)=>new Response(JSON.stringify({error:'Доступ или операция недоступны'}),{status,headers:{'Content-Type':'application/json','Cache-Control':'no-store'}});
 if(req.method!=='POST')return fail(405);
 const key=req.headers.get('x-factory-key')||'';
 if(key.length<40)return fail(401);
 const base=Deno.env.get('SUPABASE_URL')!;
 const service=Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!;
 const headers={'apikey':service,'Authorization':`Bearer ${service}`,'Content-Type':'application/json'};
 const rest=async(path:string,method='GET',body?:unknown)=>{
  const r=await fetch(base+'/rest/v1/'+path,{method,headers,body:body===undefined?undefined:JSON.stringify(body)});
  if(!r.ok)throw Error('database'); return r.status===204?null:await r.json();
 };
 try{
  const rows=await rest('factory_runtime?id=eq.1&select=bridge_hash');
  const hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(key)))).map(x=>x.toString(16).padStart(2,'0')).join('');
  if(!rows[0]||rows[0].bridge_hash!==hash)return fail(401);
  if(Number(req.headers.get('content-length')||0)>2000000)return fail(413);
  const input=await req.json();let result;
  const actions=['snapshot','lead','task','contact','draft','approve','cancel','claim','sent','unknown','import','runtime','runtime_update'];
  if(!actions.includes(input.action))return fail(400);
  const p=input.payload||{};
  if(typeof p!=='object'||Array.isArray(p))return fail(400);
  if(input.action==='runtime')result=await rest('factory_runtime?id=eq.1&select=gmail_cipher,oauth_state,sync_at,sync_error,sending_enabled');
  else if(input.action==='runtime_update'){
   const p=input.payload||{};
   if(Object.keys(p).some(k=>!['gmail_cipher','oauth_state','sync_at','sync_error'].includes(k)))return fail(400);
   result=await rest('factory_runtime?id=eq.1','PATCH',p);
  }else result=await rest('rpc/factory_command','POST',{action:input.action,payload:input.payload||{}});
  return new Response(JSON.stringify(result),{headers:{'Content-Type':'application/json','Cache-Control':'no-store'}});
 }catch{return fail(400);}
});
