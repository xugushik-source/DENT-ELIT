begin;
create table public.factory_campaign(id integer primary key check(id=1), policy jsonb not null, paused boolean not null default true, updated_at timestamptz not null default now());
create table public.factory_pipeline(lead_id uuid primary key references public.factory_leads,stage text not null default 'RESEARCH',website_state text not null default 'UNKNOWN' check(website_state in ('UNKNOWN','MISSING','WEAK','GOOD')),website_url text,email_source text,evidence jsonb not null default '[]',checked_at timestamptz,consent_message_id text references public.factory_messages(provider_id),consent_quote text,first_outbox_id uuid references public.factory_outbox,first_text_hash text,demo_outbox_id uuid references public.factory_outbox,updated_at timestamptz not null default now());
create table public.factory_owner_alerts(id uuid primary key default gen_random_uuid(),lead_id uuid references public.factory_leads,event_key text not null unique,kind text not null,detail jsonb not null,created_at timestamptz not null default now(),notified_at timestamptz);
alter table public.factory_campaign enable row level security;
alter table public.factory_pipeline enable row level security;
alter table public.factory_owner_alerts enable row level security;
revoke all on public.factory_campaign,public.factory_pipeline,public.factory_owner_alerts from anon,authenticated;
grant all on public.factory_campaign,public.factory_pipeline,public.factory_owner_alerts to service_role;
create or replace function public.factory_pipeline_command(action text,payload jsonb default '{}') returns jsonb language plpgsql security invoker set search_path=public,pg_temp as $$
declare p public.factory_pipeline; l public.factory_leads; m public.factory_messages; c public.factory_campaign; r jsonb; subject text; body text;
begin
 select * into strict c from factory_campaign where id=1;
 if action='snapshot' then return jsonb_build_object('campaign',jsonb_build_object('policy',c.policy,'paused',c.paused),'leads',coalesce((select jsonb_agg(t) from factory_pipeline t),'[]'),'alerts',coalesce((select jsonb_agg(t order by created_at desc) from factory_owner_alerts t where notified_at is null),'[]'));end if;
 if action='ack_alert' then update factory_owner_alerts set notified_at=now() where id=(payload->>'id')::uuid;return '{}';end if;
 select * into strict l from factory_leads where id=(payload->>'lead_id')::uuid for update;
 insert into factory_pipeline(lead_id) values(l.id) on conflict do nothing;
 select * into strict p from factory_pipeline where lead_id=l.id for update;
 if action='research' then
 if coalesce(payload->>'website_state','') not in ('MISSING','WEAK','GOOD') or coalesce(jsonb_typeof(payload->'evidence'),'')<>'array' or jsonb_array_length(payload->'evidence')<1 or coalesce(payload->>'email_source','') !~ '^https://' then raise exception 'Нужны проверенные источники контакта и аудита';end if;
 update factory_pipeline set website_state=payload->>'website_state',website_url=payload->>'website_url',email_source=payload->>'email_source',evidence=payload->'evidence',checked_at=now(),stage=case when payload->>'website_state' in ('MISSING','WEAK') then 'QUALIFIED' else 'NOT_QUALIFIED' end,updated_at=now() where lead_id=l.id;
 elsif action='initial_draft' then
 if l.blocked or p.stage<>'QUALIFIED' or p.checked_at<now()-interval '7 days' then raise exception 'Клиника не готова к первому обращению';end if;
 if p.first_outbox_id is not null then return jsonb_build_object('id',p.first_outbox_id);end if;
 if exists(select 1 from factory_messages where lead_id=l.id) then raise exception 'Уже есть переписка; массовое первое письмо не подходит';end if;
 if length(coalesce(payload->>'observation',''))<20 or position(payload->>'evidence_quote' in p.evidence::text)=0 or length(coalesce(payload->>'evidence_quote',''))<10 then raise exception 'Нужен конкретный проверенный факт аудита';end if;
 subject=replace(c.policy->>'first_subject','{clinic}',l.name);
 body=replace(replace(c.policy->>'first_body','{clinic}',l.name),'{observation}',payload->>'observation');
 r=factory_command('draft',jsonb_build_object('lead_id',l.id,'subject',subject,'body',body));
 update factory_pipeline set first_outbox_id=(r->>'id')::uuid,first_text_hash=encode(sha256(convert_to(jsonb_build_array(l.email,subject,body)::text,'UTF8')),'hex'),stage='FIRST_DRAFT',updated_at=now() where lead_id=l.id;
 elsif action='initial_claim' then
 perform pg_advisory_xact_lock(hashtext('factory-campaign-send'));
 if c.paused or coalesce((c.policy->>'initial_sending_enabled')::boolean,false)=false or l.blocked or p.first_outbox_id is null or p.stage<>'FIRST_DRAFT' then raise exception 'Кампания не готова к отправке';end if;
 if (select count(*) from factory_audit where kind='pipeline_initial_claim' and (created_at at time zone 'Asia/Tbilisi')::date=(now() at time zone 'Asia/Tbilisi')::date)>=least(40,(c.policy->>'daily_limit')::integer) then raise exception 'Дневной лимит';end if;
 if exists(select 1 from factory_messages where lead_id=l.id) then raise exception 'Уже есть переписка';end if;
 if not exists(select 1 from factory_outbox where id=p.first_outbox_id and factory_outbox.subject=replace(c.policy->>'first_subject','{clinic}',l.name) and encode(sha256(convert_to(jsonb_build_array(recipient,factory_outbox.subject,factory_outbox.body)::text,'UTF8')),'hex')=p.first_text_hash and status='DRAFT') then raise exception 'Текст изменён или письмо уже использовано';end if;
 perform factory_command('approve',jsonb_build_object('id',p.first_outbox_id));
 perform factory_command('claim',jsonb_build_object('id',p.first_outbox_id));
 select to_jsonb(o) into r from factory_outbox o where o.id=p.first_outbox_id;
 update factory_pipeline set stage='FIRST_SENDING',updated_at=now() where lead_id=l.id;
 elsif action='first_sent' then
 if not exists(select 1 from factory_outbox where id=p.first_outbox_id and lead_id=l.id and status='SENT') then raise exception 'Отправка не подтверждена Gmail';end if;
 update factory_pipeline set stage='WAITING_CONSENT',updated_at=now() where lead_id=l.id;
 elsif action='classify_reply' then
 select * into strict m from factory_messages where provider_id=payload->>'message_id' and lead_id=l.id and direction='IN';
 if length(coalesce(payload->>'quote',''))<2 or position(payload->>'quote' in m.body)=0 then raise exception 'Нужна точная цитата ответа';end if;
 if payload->>'classification' not in ('CONSENT','DECLINE','QUESTION','OWNER_HANDOFF','AUTO_REPLY') then raise exception 'Неизвестный ответ';end if;
 if m.sent_at<now()-interval '30 days' and coalesce((payload->>'historical_reviewed')::boolean,false)=false then raise exception 'Старый ответ требует проверки актуальности';end if;
 if payload->>'classification'='CONSENT' then
 if p.stage in ('SUPPRESSED','OWNER_PAUSED') then raise exception 'Контакт остановлен владельцем или клиентом';end if;
 update factory_leads set blocked=false,next_action='Клиент согласился на демо: собрать проверенные материалы и подготовить сайт',updated_at=now() where id=l.id;
 update factory_pipeline set stage='DEMO_REQUESTED',consent_message_id=m.provider_id,consent_quote=payload->>'quote',updated_at=now() where lead_id=l.id;
 elsif payload->>'classification'='DECLINE' then
 update factory_pipeline set stage='SUPPRESSED',updated_at=now() where lead_id=l.id;
 perform factory_command('contact',jsonb_build_object('lead_id',l.id,'blocked',true,'next_action','Отказ клиента; дальнейшие обращения запрещены'));
 elsif payload->>'classification'<>'AUTO_REPLY' then update factory_pipeline set stage='OWNER_REPLY_REVIEW',updated_at=now() where lead_id=l.id;end if;
 insert into factory_owner_alerts(lead_id,event_key,kind,detail) values(l.id,'reply-'||m.provider_id,'CLIENT_REPLY',jsonb_build_object('classification',payload->>'classification','quote',payload->>'quote','message_id',m.provider_id)) on conflict do nothing;
 elsif action='demo_sent' then
 if p.consent_message_id is null then raise exception 'Нет согласия на демоверсию';end if;
 if not exists(select 1 from factory_outbox where id=(payload->>'outbox_id')::uuid and lead_id=l.id and status='SENT') then raise exception 'Отправка демо не подтверждена';end if;
 if not exists(select 1 from factory_sites s join factory_outbox o on o.id=s.proposal_id where s.lead_id=l.id and not s.synthetic and s.status='APPROVED' and s.proposal_id=(payload->>'outbox_id')::uuid and s.client_preview_url=payload->>'preview_url' and s.client_preview_checked_at is not null and length(s.client_preview_url)>15 and position(s.client_preview_url in o.body)>0) then raise exception 'Нет подтверждённой персональной клиентской ссылки в отправленном письме';end if;
 update factory_pipeline set stage='OWNER_HANDOFF',demo_outbox_id=(payload->>'outbox_id')::uuid,updated_at=now() where lead_id=l.id;
 insert into factory_owner_alerts(lead_id,event_key,kind,detail) values(l.id,'demo-sent-'||(payload->>'outbox_id'),'WHATSAPP_HANDOFF',jsonb_build_object('clinic',l.name,'email',l.email,'outbox_id',payload->>'outbox_id','preview_url',payload->>'preview_url','whatsapp',payload->>'whatsapp','owner_action','Продублировать ссылку в WhatsApp; переговоры ведёт владелец')) on conflict do nothing;
 else raise exception 'Неизвестное действие';end if;
 insert into factory_audit(kind,detail) values('pipeline_'||action,jsonb_build_object('lead_id',l.id));
 return coalesce(r,'{}');
end $$;
revoke all on function public.factory_pipeline_command(text,jsonb) from public,anon,authenticated;
grant execute on function public.factory_pipeline_command(text,jsonb) to service_role;
commit;
