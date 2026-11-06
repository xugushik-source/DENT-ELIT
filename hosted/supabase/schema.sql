begin;
create table public.factory_runtime (id integer primary key check(id=1), bridge_hash text not null, gmail_cipher text, oauth_state jsonb, sync_at timestamptz, sync_error text, sending_enabled boolean not null default false);
alter table public.factory_runtime enable row level security;
create table public.factory_leads(id uuid primary key default gen_random_uuid(), name text not null check(length(name) between 1 and 200), email text not null unique check(email ~ '^[^[:space:]<>@,;]+@[^[:space:]<>@,;]+\.[^[:space:]<>@,;]+$'), source text not null check(length(source)>0), status text not null default 'NEW', next_action text not null default 'Подготовить предложение', blocked boolean not null default false, updated_at timestamptz not null default now());
create table public.factory_tasks(id uuid primary key default gen_random_uuid(), lead_id uuid references public.factory_leads, title text not null check(length(title) between 1 and 2000), status text not null default 'OPEN' check(status in ('OPEN','DONE','BLOCKED')), reason text not null default '', updated_at timestamptz not null default now());
create table public.factory_messages(provider_id text primary key, lead_id uuid not null references public.factory_leads, thread_id text not null default '', direction text not null check(direction in ('IN','OUT','BOUNCE')), subject text not null, body text not null, sent_at timestamptz not null, source text not null);
create index factory_messages_lead on public.factory_messages(lead_id,sent_at desc);
create table public.factory_outbox(id uuid primary key default gen_random_uuid(), lead_id uuid not null references public.factory_leads, recipient text not null, subject text not null check(length(subject) between 1 and 998 and position(chr(10) in subject)=0 and position(chr(13) in subject)=0), body text not null check(length(body) between 1 and 50000), status text not null default 'DRAFT' check(status in ('DRAFT','APPROVED','SENDING','SENT','UNKNOWN','CANCELLED')), approved_hash text, approved_at timestamptz, provider_id text, error text, created_at timestamptz not null default now());
create unique index factory_outbox_unresolved on public.factory_outbox(lead_id) where status in ('DRAFT','APPROVED','SENDING','UNKNOWN');
create table public.factory_audit(id bigint generated always as identity primary key, kind text not null, detail jsonb not null default '{}', created_at timestamptz not null default now());
create index factory_outbox_lead on public.factory_outbox(lead_id);
create index factory_tasks_lead on public.factory_tasks(lead_id);
do $$ declare t text; begin
 foreach t in array array['factory_leads','factory_tasks','factory_messages','factory_outbox','factory_audit'] loop
 execute format('alter table public.%I enable row level security',t);
 execute format('revoke all on public.%I from anon, authenticated',t);
 execute format('grant all on public.%I to service_role',t);
 end loop;
end $$;
revoke all on public.factory_runtime from anon, authenticated;
grant all on public.factory_runtime to service_role;
grant usage,select on sequence public.factory_audit_id_seq to service_role;
create function public.factory_command(action text, payload jsonb default '{}') returns jsonb language plpgsql security invoker set search_path = public,pg_temp as $$
declare r public.factory_outbox; l public.factory_leads; result jsonb; oid uuid; lid uuid; m jsonb; latest text; n integer:=0;
begin
 if action='snapshot' then
 return jsonb_build_object('leads',coalesce((select jsonb_agg(t order by t.updated_at desc) from factory_leads t),'[]'), 'tasks',coalesce((select jsonb_agg(t order by t.updated_at desc) from factory_tasks t),'[]'), 'messages',coalesce((select jsonb_agg(t order by t.sent_at desc) from factory_messages t),'[]'), 'outbox',coalesce((select jsonb_agg(t order by t.created_at desc) from factory_outbox t),'[]'), 'audit',coalesce((select jsonb_agg(t order by t.id desc) from (select * from factory_audit order by id desc limit 100) t),'[]'), 'connection',(select jsonb_build_object('configured',gmail_cipher is not null,'checked_at',sync_at,'error',sync_error,'send_enabled',sending_enabled) from factory_runtime where id=1));
 elsif action='lead' then
 insert into factory_leads(name,email,source) values(trim(payload->>'name'),lower(trim(payload->>'email')),trim(payload->>'source')) on conflict(email) do update set name=excluded.name returning id into lid;
 result=jsonb_build_object('id',lid);
 elsif action='task' then
 if coalesce(trim(payload->>'title'),'')='' then raise exception 'Нужно следующее действие'; end if;
 if payload->>'id' is null then
 insert into factory_tasks(lead_id,title,status,reason) values((payload->>'lead_id')::uuid,payload->>'title',coalesce(payload->>'status','OPEN'),coalesce(payload->>'reason','')) returning id into oid;
 else
 update factory_tasks set title=payload->>'title',status=payload->>'status',reason=coalesce(payload->>'reason',''),updated_at=now() where id=(payload->>'id')::uuid returning id into oid;
 if not found then raise exception 'Задача не найдена'; end if;
 end if;
 result=jsonb_build_object('id',oid);
 elsif action='contact' then
 update factory_leads set next_action=payload->>'next_action',blocked=(payload->>'blocked')::boolean,updated_at=now() where id=(payload->>'lead_id')::uuid;
 if not found then raise exception 'Компания не найдена'; end if;
 if (payload->>'blocked')::boolean then update factory_outbox set status='CANCELLED' where lead_id=(payload->>'lead_id')::uuid and status in ('DRAFT','APPROVED'); end if;
 result='{}';
 elsif action='draft' then
 select * into strict l from factory_leads where id=(payload->>'lead_id')::uuid for update;
 if l.blocked then raise exception 'Контакт остановлен'; end if;
 if exists(select 1 from factory_outbox where lead_id=l.id and status='SENT' and subject=trim(payload->>'subject') and body=trim(payload->>'body')) then raise exception 'Такое письмо уже отправлено'; end if;
 if coalesce(payload->>'body','') ~* '(localhost|127\.0\.0\.1|\.invalid)' then raise exception 'Нельзя отправлять локальные и тестовые ссылки'; end if;
 insert into factory_outbox(lead_id,recipient,subject,body) values(l.id,l.email,trim(payload->>'subject'),trim(payload->>'body')) returning id into oid;
 result=jsonb_build_object('id',oid);
 elsif action in ('approve','cancel','claim') then
 select * into strict r from factory_outbox where id=(payload->>'id')::uuid for update;
 select * into strict l from factory_leads where id=r.lead_id for update;
 if action='cancel' then
 if r.status not in ('DRAFT','APPROVED') then raise exception 'Отмена недоступна'; end if;
 update factory_outbox set status='CANCELLED' where id=r.id;
 elsif action='approve' then
 if r.status<>'DRAFT' or l.blocked then raise exception 'Нет доступного черновика'; end if;
 update factory_outbox set status='APPROVED',approved_hash=encode(sha256(convert_to(jsonb_build_array(r.lead_id,r.recipient,r.subject,r.body)::text,'UTF8')),'hex'),approved_at=now() where id=r.id;
 else
 perform id from factory_runtime where id=1 and sending_enabled for update;
 if not found then raise exception 'Отправка отключена'; end if;
 if r.status<>'APPROVED' or l.blocked or l.email<>r.recipient or r.approved_hash is distinct from encode(sha256(convert_to(jsonb_build_array(r.lead_id,r.recipient,r.subject,r.body)::text,'UTF8')),'hex') then raise exception 'Нет утверждения этой версии'; end if;
 if (select count(*) from factory_audit where kind='claim' and (created_at at time zone 'Asia/Tbilisi')::date=(now() at time zone 'Asia/Tbilisi')::date)>=least(40,coalesce((select (policy->>'daily_limit')::integer from factory_campaign where id=1),30)) then raise exception 'Дневной лимит отправок'; end if;
 update factory_outbox set status='SENDING' where id=r.id;
 end if;
 result=to_jsonb(r);
 elsif action='sent' then
 select * into strict r from factory_outbox where id=(payload->>'id')::uuid for update;
 if r.status<>'SENDING' then raise exception 'Нет активной отправки'; end if;
 if coalesce(payload->>'provider_id','')='' then raise exception 'Нет Gmail id'; end if;
 update factory_outbox set status='SENT',provider_id=payload->>'provider_id' where id=r.id;
 insert into factory_messages values(payload->>'provider_id',r.lead_id,coalesce(payload->>'thread_id',''),'OUT',r.subject,r.body,now(),'gmail-api') on conflict do nothing;
 update factory_leads set status='WAITING_REPLY',next_action='Ожидается ответ',updated_at=now() where id=r.lead_id;
 result='{}';
 elsif action='unknown' then
 update factory_outbox set status='UNKNOWN',error='Результат неизвестен. Сверьте отправленные в Gmail; повтор заблокирован.' where id=(payload->>'id')::uuid and status='SENDING';
 result='{}';
 elsif action='import' then
 select * into strict l from factory_leads where id=(payload->>'lead_id')::uuid for update;
 for m in select value from jsonb_array_elements(payload->'messages') loop
 insert into factory_messages values(m->>'id',l.id,coalesce(m->>'thread_id',''),m->>'direction',coalesce(m->>'subject',''),coalesce(m->>'body',''),(m->>'sent_at')::timestamptz,m->>'source') on conflict do nothing;
 if found then
 n:=n+1;
 if m->>'direction' in ('IN','BOUNCE') then
 update factory_leads set blocked=true where id=l.id;
 update factory_outbox set status='CANCELLED' where lead_id=l.id and status in ('DRAFT','APPROVED');
 end if;
 end if;
 end loop;
 if n>0 then
 select direction into latest from factory_messages where lead_id=l.id order by sent_at desc limit 1;
 update factory_leads set status=case latest when 'IN' then 'REPLY_REVIEW' when 'OUT' then 'WAITING_REPLY' else 'DELIVERY_REVIEW' end,next_action=case latest when 'IN' then 'Прочитать ответ и выбрать следующий шаг' when 'OUT' then 'Проверить результат переписки' else 'Проверить возврат' end,updated_at=now() where id=l.id;
 end if;
 result=jsonb_build_object('added',n);
 else raise exception 'Неизвестное действие';
 end if;
 insert into factory_audit(kind,detail) values(action,jsonb_build_object('id',coalesce(payload->>'id',result->>'id'),'lead_id',payload->>'lead_id'));
 return result;
end $$;
revoke all on function public.factory_command(text,jsonb) from public,anon,authenticated;
grant execute on function public.factory_command(text,jsonb) to service_role;
commit;
