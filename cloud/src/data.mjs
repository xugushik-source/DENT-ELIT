import schema from './schema.mjs';
export const approved=new Set(['VERIFIED','CLIENT_APPROVED']);
export const value=f=>approved.has(f.status)?f.value:null;
export function facts(o,p=''){
 if(o&&typeof o==='object'&&!Array.isArray(o)&&'value'in o&&'status'in o)return [[p,o]];
 return o&&typeof o==='object'?Object.entries(o).flatMap(([k,v])=>facts(v,p+'/'+k)):[];
}
export function validate(c){
 if(!schema(c))throw Error('Конфигурация не соответствует строгой схеме');
 if(c.deploymentMode!=='demo'||c.languages.uiVersion!=='v1'||c.languages.enabled.includes('ka'))throw Error('Поддерживаются только демо ru/en/hy');
 if(!c.languages.enabled.includes(c.languages.default))throw Error('Язык по умолчанию не включён');
 if(['beforeAfterEnabled','offersEnabled','blogEnabled'].some(k=>c.features[k]))throw Error('Функция пока не поддерживается');
 const sources=new Map(c.sources.map(s=>[s.id,s])),assets=new Map(c.assets.map(a=>[a.id,a]));
 if(sources.size!==c.sources.length||assets.size!==c.assets.length)throw Error('Повтор источника или изображения');
 const sourceRefs=ids=>{for(const id of ids){const s=sources.get(id);if(!s||s.clinicId!==c.clinicId||s.accessStatus!=='ALLOWED'||Date.parse(s.retrievedAt)>Date.now())throw Error('Источник не разрешён или принадлежит другой клинике');}};
 const pending=[],used=new Set();
 for(const [path,f]of facts(c)){
  sourceRefs(f.sourceIds);
  if(!approved.has(f.status)){pending.push({path,status:f.status,sourceIds:f.sourceIds});continue;}
  const age=Date.now()-Date.parse(f.checkedAt);if(age<0||age>90*86400000)throw Error('Нужна повторная проверка устаревшего поля');
 }
   if(c.features.multilingualEnabled===false&&c.languages.enabled.length>1)throw Error('Несовместимая настройка языков');
 for(const [path,f]of facts(c))if(approved.has(f.status)){
  if(typeof f.value==='string'&&f.value.startsWith('https://')){const u=new URL(f.value);if(!u.hostname||u.username||u.password||/[\\\r\n]/.test(f.value))throw Error('Небезопасная ссылка');}
  if(/\/(logo|logoSplash|favicon|photo|heroPhoto|workingPhoto|hero|team|reception|finalCta)$/.test(path)||path.startsWith('/media/gallery/')){if(!assets.has(f.value))throw Error('Изображение отсутствует');used.add(f.value);}
 }
 for(const group of ['services','doctors','technologies','reviews','statistics','links'])for(const key of ['id','slug']){const ids=c[group].filter(i=>key in i).map(i=>i[key]);if(new Set(ids).size!==ids.length)throw Error('Повтор ID или slug');}
 const ids=Object.fromEntries(['services','doctors','technologies'].map(g=>[g,new Set(c[g].map(i=>i.id))]));
 for(const [group,mapping]of [['services',{doctorIds:'doctors',technologyIds:'technologies',relatedServiceIds:'services'}],['doctors',{serviceIds:'services'}]])for(const i of c[group])for(const [key,target]of Object.entries(mapping))if(i[key].some(id=>!ids[target].has(id)))throw Error('Ссылка на отсутствующую услугу или врача');
 for(const i of c.services){const p=value(i.price);if(p&&(!['USD','AMD','GEL','EUR','RUB','GBP'].includes(p.currency)||(p.basis==='range'?(p.maxAmountMinor===null||p.maxAmountMinor<p.amountMinor):p.maxAmountMinor!==null)))throw Error('Некорректная цена');}
 for(const i of c.doctors){const n=value(i.experienceYears);if(n!==null&&(!Number.isInteger(n)||n<0))throw Error('Некорректный стаж');}
 function localized(o){if(o&&typeof o==='object'){if(!Array.isArray(o)&&Object.keys(o).length&&Object.keys(o).every(k=>['hy','ru','en','ka'].includes(k))){if(c.languages.enabled.some(k=>!(k in o)))throw Error('Отсутствует перевод');}else Object.values(o).forEach(localized);}}localized(c);
 const rating=value(c.rating.value),count=value(c.rating.count);if(rating!==null&&(rating<0||rating>5)||count!==null&&(!Number.isInteger(count)||count<0))throw Error('Некорректный рейтинг');
 const hours=value(c.contact.hours)||[];if(new Set(hours.map(h=>h.day)).size!==hours.length||hours.some(h=>h.closed&&(h.byAppointment||h.intervals.length)||h.intervals.some(i=>i.open>=i.close)))throw Error('Некорректные часы работы');
 for(const aid of used){const a=assets.get(aid),r=a.rights;sourceRefs(r.sourceIds);if(r.status!=='PERMITTED'||!r.allowedUses.includes('demo')||r.expiresAt&&Date.parse(r.expiresAt)<=Date.now()||a.mime==='image/svg+xml'||a.depiction!=='generic_illustration'&&(a.scope!=='clinic'||a.subjectClinicId!==c.clinicId))throw Error('Нет подтверждённых прав на изображение');}
 if(c.reviews.some(r=>r.permission==='PERMITTED'&&!r.proofRef))throw Error('Нет подтверждения прав на отзыв');
 if(!value(c.brand.name))throw Error('Название клиники должно быть проверено');
 for(const r of c.reviews)if(r.permission!=='PERMITTED')pending.push({path:'/reviews/'+c.reviews.indexOf(r)+'/permission',status:r.permission,sourceIds:[]});
 for(const a of c.assets){sourceRefs(a.rights.sourceIds);if(a.scope==='clinic'&&a.subjectClinicId!==c.clinicId)throw Error('Изображение другой клиники');}
 return pending;
}
export function decode(r){if(!r)return null;const c={...r};for(const k of ['config','approval','draft'])c[k]=c[k]?JSON.parse(c[k]):null;c.synthetic=Boolean(c.synthetic);delete c.nonce;return c;}
export async function get(env,id){
 const c=decode(await env.DB.prepare('SELECT * FROM clinics WHERE id=?').bind(id).first());if(!c)throw Error('Карточка не найдена');
 const j=await env.DB.prepare('SELECT * FROM jobs WHERE id=?').bind(c.current_job).first();
 c.job=j?{...j,report:j.report?JSON.parse(j.report):null}:null;if(c.job){delete c.job.config;delete c.job.lease;}
 c.events=(await env.DB.prepare('SELECT kind,actor,detail,created_at FROM events WHERE clinic_id=? ORDER BY id DESC').bind(id).all()).results.map(e=>({...e,detail:JSON.parse(e.detail)}));return c;
}
export async function change(env,c,version,values,kind,detail,actor,extra=()=>[]){
 const nonce=crypto.randomUUID(),fields=Object.keys(values),t=new Date().toISOString();
 const update=env.DB.prepare('UPDATE clinics SET '+fields.map(k=>k+'=?').join(',')+',version=version+1,nonce=? WHERE id=? AND version=?').bind(...fields.map(k=>values[k]),nonce,c.id,version);
 const event=env.DB.prepare('INSERT INTO events(clinic_id,kind,actor,detail,created_at) SELECT id,?,?,?,? FROM clinics WHERE id=? AND nonce=?').bind(kind,actor,JSON.stringify(detail),t,c.id,nonce);
 const result=await env.DB.batch([update,event,...extra(nonce,t)]);
 if(result[0].meta.changes!==1)throw Error('Карточка изменилась; обновите её');return get(env,c.id);
}
