import {Buffer} from 'node:buffer';
import {createHash,randomBytes,createCipheriv,createDecipheriv,timingSafeEqual} from 'node:crypto';
export const scopes=['https://www.googleapis.com/auth/gmail.readonly','https://www.googleapis.com/auth/gmail.send'];
export const owner='orderprofit.he@gmail.com';
export function equal(a,b){const x=Buffer.from(a||''),y=Buffer.from(b||'');return x.length===y.length&&timingSafeEqual(x,y);}
export function seal(data,key){const iv=randomBytes(12),c=createCipheriv('aes-256-gcm',Buffer.from(key,'hex'),iv);const body=Buffer.concat([c.update(JSON.stringify(data)),c.final()]);return Buffer.concat([iv,c.getAuthTag(),body]).toString('base64url');}
export function unseal(data,key){const b=Buffer.from(data,'base64url'),c=createDecipheriv('aes-256-gcm',Buffer.from(key,'hex'),b.subarray(0,12));c.setAuthTag(b.subarray(12,28));return JSON.parse(Buffer.concat([c.update(b.subarray(28)),c.final()]).toString());}
export function clientConfig(input,origin){const c=input?.web;if(!c?.client_id||!c?.client_secret||!Array.isArray(c.redirect_uris)||!c.redirect_uris.includes(origin+'/api/oauth/callback'))throw Error('Нужен Web OAuth JSON с адресом возврата этого кабинета');return {client_id:c.client_id,client_secret:c.client_secret};}
export function authorization(client,origin){const state=randomBytes(32).toString('base64url'),verifier=randomBytes(64).toString('base64url');const q=new URLSearchParams({client_id:client.client_id,redirect_uri:origin+'/api/oauth/callback',response_type:'code',scope:scopes.join(' '),access_type:'offline',prompt:'consent',login_hint:owner,state,code_challenge:createHash('sha256').update(verifier).digest('base64url'),code_challenge_method:'S256'});return {state,verifier,url:'https://accounts.google.com/o/oauth2/v2/auth?'+q};}
export async function google(path,{token,form,body,fetcher=fetch}={}){
 const url=form?'https://oauth2.googleapis.com/token':'https://gmail.googleapis.com/gmail/v1/users/me/'+path;
 const response=await fetcher(url,{method:form||body?'POST':'GET',headers:form?{'Content-Type':'application/x-www-form-urlencoded'}:{Authorization:'Bearer '+token,'Content-Type':'application/json'},body:form?new URLSearchParams(form):body?JSON.stringify(body):undefined,signal:AbortSignal.timeout(20000)});
 if(!response.ok)throw Error('Google не завершил запрос');return response.json();
}
export async function tokenFor(c,fetcher=fetch){const t=await google('',{form:{client_id:c.client_id,client_secret:c.client_secret,refresh_token:c.refresh_token,grant_type:'refresh_token'},fetcher});const p=await google('profile',{token:t.access_token,fetcher});if(p.emailAddress?.toLowerCase()!==owner)throw Error('Выбрана другая почта');return t.access_token;}
function text(part){if(part.mimeType==='text/plain')return Buffer.from(part.body?.data||'','base64url').toString();return (part.parts||[]).map(text).join('\n');}
export async function messages(email,token,fetcher=fetch){
 if(!/^[^\s<>@,;]+@[^\s<>@,;]+\.[^\s<>@,;]+$/.test(email))throw Error('Неверный email');
 const threads=new Set();let page='';
 do{const p=new URLSearchParams({q:`{from:${email} to:${email}}`,maxResults:'100',includeSpamTrash:'true'});if(page)p.set('pageToken',page);const r=await google('messages?'+p,{token,fetcher});for(const m of r.messages||[])threads.add(m.threadId);page=r.nextPageToken||'';if(threads.size>100)throw Error('Большая переписка: нужен отдельный импорт');}while(page);
 const result=[];
 for(const id of threads){const t=await google('threads/'+encodeURIComponent(id)+'?format=full',{token,fetcher});for(const m of t.messages||[]){if((m.labelIds||[]).includes('DRAFT'))continue;const p=m.payload||{},h=Object.fromEntries((p.headers||[]).map(x=>[x.name.toLowerCase(),x.value]));const from=h.from||'';let direction=(m.labelIds||[]).includes('SENT')&&from.toLowerCase().includes(owner)?'OUT':'IN';if(/mailer-daemon@|postmaster@/i.test(from)||p.mimeType==='multipart/report')direction='BOUNCE';result.push({id:m.id,thread_id:id,direction,subject:h.subject||'',body:text(p)||m.snippet||'',sent_at:new Date(Number(m.internalDate)).toISOString(),source:'gmail-api'});}}
 return result;
}
export function mime(item){if(/[\r\n]/.test(item.subject)||!/^[^\s<>@,;]+@[^\s<>@,;]+\.[^\s<>@,;]+$/.test(item.recipient))throw Error('Неверные заголовки');const subject=Buffer.from(item.subject).toString('base64');const body=Buffer.from(item.body).toString('base64').match(/.{1,76}/g)?.join('\r\n')||'';return Buffer.from(`From: ${owner}\r\nTo: ${item.recipient}\r\nSubject: =?UTF-8?B?${subject}?=\r\nMessage-ID: <${item.id}@order-profit.factory>\r\nMIME-Version: 1.0\r\nContent-Type: text/plain; charset=UTF-8\r\nContent-Transfer-Encoding: base64\r\n\r\n${body}\r\n`).toString('base64url');}
