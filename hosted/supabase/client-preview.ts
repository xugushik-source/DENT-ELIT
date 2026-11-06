// Read-only scoped transport. The viewer never receives service-role or CRM credentials.
Deno.serve(async(req:Request)=>{
 const denied=()=>new Response(JSON.stringify({error:'Unavailable'}),{status:404,headers:{'Content-Type':'application/json','Cache-Control':'no-store'}});
 if(req.method!=='POST'||Number(req.headers.get('content-length')||0)>2000)return denied();
 try{
  const p=await req.json();if(typeof p.token!=='string'||!/^[a-f0-9]{64}$/.test(p.token)||typeof p.path!=='string'||p.path.length>300||p.path.includes('..')||p.path.includes('\\')||p.path.startsWith('/'))return denied();
  const hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(p.token)))).map(x=>x.toString(16).padStart(2,'0')).join('');
  const key=Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!;
  const response=await fetch(Deno.env.get('SUPABASE_URL')+'/rest/v1/rpc/factory_client_file',{method:'POST',headers:{apikey:key,Authorization:'Bearer '+key,'Content-Type':'application/json'},body:JSON.stringify({share_hash:hash,file_path:p.path})});
  if(!response.ok)return denied();
  return new Response(await response.text(),{headers:{'Content-Type':'application/json','Cache-Control':'no-store','X-Content-Type-Options':'nosniff'}});
 }catch{return denied();}
});
