import {createRemoteJWKSet,jwtVerify} from 'jose';
const keys=new Map();
export async function verifyToken(token,jwks,issuer,audience,owner){
 const {payload}=await jwtVerify(token,jwks,{issuer,audience,algorithms:['RS256']});
 if(typeof payload.email!=='string'||payload.email.toLowerCase()!==owner.toLowerCase())throw Error('Not the owner');
 return payload.email.toLowerCase();
}
export async function owner(request,env){
 if(!/^https:\/\/[a-z0-9-]+\.cloudflareaccess\.com$/.test(env.ACCESS_ISSUER||'')||!env.ACCESS_AUD||!env.OWNER_EMAIL)throw Error('Access not configured');
 const token=request.headers.get('Cf-Access-Jwt-Assertion');if(!token)throw Error('Authentication required');
 if(!keys.has(env.ACCESS_ISSUER))keys.set(env.ACCESS_ISSUER,createRemoteJWKSet(new URL(env.ACCESS_ISSUER+'/cdn-cgi/access/certs')));
 return verifyToken(token,keys.get(env.ACCESS_ISSUER),env.ACCESS_ISSUER,env.ACCESS_AUD,env.OWNER_EMAIL);
}
export async function hash(data){return [...new Uint8Array(await crypto.subtle.digest('SHA-256',typeof data==='string'?new TextEncoder().encode(data):data))].map(b=>b.toString(16).padStart(2,'0')).join('');}
export async function csrf(env,email,origin){
 if((env.CSRF_SECRET||'').length<32)throw Error('CSRF not configured');
 const key=await crypto.subtle.importKey('raw',new TextEncoder().encode(env.CSRF_SECRET),{name:'HMAC',hash:'SHA-256'},false,['sign']);
 return [...new Uint8Array(await crypto.subtle.sign('HMAC',key,new TextEncoder().encode(email+':'+origin+':'+Math.floor(Date.now()/86400000))))].map(b=>b.toString(16).padStart(2,'0')).join('');
}
export function equal(a,b){if(typeof a!=='string'||typeof b!=='string'||a.length!==b.length)return false;let n=0;for(let i=0;i<a.length;i++)n|=a.charCodeAt(i)^b.charCodeAt(i);return n===0;}
