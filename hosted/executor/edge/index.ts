import {tokenFor,unseal,messages,google,mime} from './core.mjs';
const base=Deno.env.get('SUPABASE_URL')+'/rest/v1';
const key=Deno.env.get('SUPABASE_SERVICE_ROLE_KEY');
async function rest(path,method='GET',body){const r=await fetch(base+'/'+path,{method,headers:{apikey:key,Authorization:'Bearer '+key,'Content-Type':'application/json',Prefer:'return=representation,resolution=ignore-duplicates'},body:body===undefined?undefined:JSON.stringify(body),signal:AbortSignal.timeout(20000)});if(!r.ok)throw Error('Database operation failed '+r.status);return r.json();}
const rpc=(name,action,payload)=>rest('rpc/'+name,'POST',{action,payload});
Deno.serve(async req=>{
 const token=req.headers.get('x-factory-executor')||'';
 const lease=await rest('rpc/factory_executor_lease','POST',{token});
 if(!lease)return new Response('Unavailable',{status:403});
 const out={dry_run:lease.dry_run,checked:0,sent:0,errors:[],discovered:0};
 const deadline=Date.now()+90000;
 try{
 const c=(await rest('factory_campaign?id=eq.1'))[0];
 const runtime=(await rest('factory_runtime?id=eq.1&select=gmail_cipher,sending_enabled'))[0];
 if(!c.policy.server_gmail_transport_authorized)throw Error('Server transport not authorized');
 const access=await tokenFor(unseal(runtime.gmail_cipher,lease.cipher_key));
 out.account_verified=true;
 const regions=['Kutaisi','Rustavi','Batumi','Telavi','Kobuleti','Akhaltsikhe','Poti','Borjomi','Marneuli','Senaki','Khashuri','Zugdidi'];
 const cur=lease.cursor||0,city=regions[Math.floor(cur/3)%regions.length],page=cur%3+1;
 const source='https://www.yell.ge/companies.php?lan=eng&rub=420&SI_1='+city+'&SR_pg='+page;
 const fetched=await fetch(source,{signal:AbortSignal.timeout(15000)});
 if(fetched.ok){
 const html=await fetched.text();
 const addresses=[...new Set([...html.matchAll(/mailto:([^"'<>? ]+)/gi)].map(x=>x[1].trim().toLowerCase()).filter(x=>/^[^@;]+@[^@;]+\.[^@;]+$/.test(x)))];
 const existing=await rest('factory_leads?select=email');
 for(const email of addresses){
 if(existing.some(x=>x.email.toLowerCase()===email))continue;
 await rest('factory_executor_candidates?on_conflict=email','POST',{email,name:'Pending verification',source,city,state:'RESEARCH',evidence:[{url:source,observed_at:new Date().toISOString(),type:'published_email',note:'Directory email only; clinic identity/activity/site and Gmail dedup not yet verified'}]});
 out.discovered++;
 }
 await rest('factory_executor_control?id=eq.1&run_id=eq.'+lease.run_id,'PATCH',{cursor:cur+1});
 }
 const pending=await rest('factory_pipeline?stage=eq.FIRST_DRAFT&select=lead_id,checked_at,email_source,evidence&limit=3');
 for(const p of pending){
 if(Date.now()>deadline)break;
 const l=(await rest('factory_leads?id=eq.'+p.lead_id+'&select=id,name,email,blocked'))[0];
 if(l.blocked)continue;
 const history=await messages(l.email,access);
 await rpc('factory_command','import',{lead_id:l.id,messages:history});
 out.checked++;
 if(history.length||Date.now()-Date.parse(p.checked_at)>86400000||!p.email_source?.startsWith('https://'))continue;
 const contactResponse=await fetch(p.email_source,{signal:AbortSignal.timeout(15000)});
 if(!contactResponse.ok)continue;
 const contactText=(await contactResponse.text()).toLowerCase();
 if(!contactText.includes(l.email.toLowerCase()))continue;
 const mx=await (await fetch('https://dns.google/resolve?name='+encodeURIComponent(l.email.split('@')[1])+'&type=MX')).json();
 if(mx.Status!==0||!mx.Answer?.some(x=>x.type===15&&x.data!=='0 .'))continue;
 if(lease.dry_run||c.paused||!runtime.sending_enabled||!c.policy.initial_sending_enabled)continue;
 // Only verified drafts already qualified by the source-backed research pipeline.
 const item=await rpc('factory_pipeline_command','initial_claim',{lead_id:l.id});
 if(item.status!=='SENDING'||item.recipient!==l.email)throw Error('Claim mismatch');
 let receipt;
 try{receipt=await google('messages/send',{token:access,body:{raw:mime(item)}});if(!receipt.id)throw Error('No provider ID');}
 catch{await rpc('factory_command','unknown',{id:item.id});throw Error('UNKNOWN send result; no retry');}
 // Preserve receipt before final state changes; never auto retry claimed letters.
 await rest('factory_audit','POST',{kind:'executor_provider_receipt',detail:{outbox_id:item.id,provider_id:receipt.id,thread_id:receipt.threadId}});
 await rpc('factory_command','sent',{id:item.id,provider_id:receipt.id,thread_id:receipt.threadId});
 await rpc('factory_pipeline_command','first_sent',{lead_id:l.id});out.sent++;
 }
 }catch(e){out.errors.push(String(e.message).slice(0,160));}
 await rest('factory_executor_control?id=eq.1&run_id=eq.'+lease.run_id,'PATCH',{heartbeat:new Date().toISOString(),lease_until:null,last_result:out});
 return Response.json(out);
});