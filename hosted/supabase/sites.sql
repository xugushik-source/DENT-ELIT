begin;
create table public.factory_sites(id uuid primary key default gen_random_uuid(),lead_id uuid references public.factory_leads, name text not null, synthetic boolean not null default false, config jsonb not null, asset_blobs jsonb not null default '{}', status text not null default 'READY' check(status in ('READY','BUILDING','BUILT','FAILED','APPROVED')), report jsonb, error text, opened_at timestamptz, reviewed_at timestamptz, approved_at timestamptz, created_at timestamptz not null default now(),proposal_id uuid references public.factory_outbox,client_preview_url text,client_preview_checked_at timestamptz);
create index factory_sites_lead on public.factory_sites(lead_id);
create table public.factory_site_files(site_id uuid not null references public.factory_sites, path text not null check(path !~ '(^/|(^|/)\.\.(/|$)|\\)' and length(path)<300), content text not null, mime text not null, primary key(site_id,path));
alter table public.factory_sites enable row level security;
alter table public.factory_site_files enable row level security;
revoke all on public.factory_sites,public.factory_site_files from anon,authenticated;
grant all on public.factory_sites,public.factory_site_files to service_role;
create or replace function public.factory_site_command(action text,payload jsonb default '{}') returns jsonb language plpgsql security invoker set search_path=public,pg_temp as $$
declare r public.factory_sites;f jsonb; sid uuid;result jsonb;
begin
 if action='list' then return coalesce((select jsonb_agg(t order by t.created_at desc) from (select id,lead_id,name,synthetic,status,report,error,opened_at,reviewed_at,approved_at,created_at,client_preview_url,client_preview_checked_at,config->'languages'->>'default' as language from factory_sites) t),'[]');
 elsif action='sent_context' then
 select * into r from factory_sites where proposal_id=(payload->>'outbox_id')::uuid and not synthetic and status='APPROVED';
 if not found then return null;end if;
 return jsonb_build_object('lead_id',r.lead_id,'outbox_id',r.proposal_id,'preview_url',r.client_preview_url,'whatsapp',case when r.config->'contact'->'whatsapp'->>'status' in ('VERIFIED','CLIENT_APPROVED') then r.config->'contact'->'whatsapp'->>'value' else null end);
 elsif action='details' then
 select * into strict r from factory_sites where id=(payload->>'id')::uuid;
 return jsonb_build_object('id',r.id,'name',r.name,'status',r.status,'synthetic',r.synthetic,'report',r.report,'languages',r.config->'languages'->'enabled');
 elsif action='create' then
 if not coalesce((payload->>'synthetic')::boolean,false) and not exists(select 1 from factory_pipeline where lead_id=(payload->>'lead_id')::uuid and consent_message_id is not null and stage='DEMO_REQUESTED') then raise exception 'Сначала нужно явное согласие клиента на демоверсию';end if;
 if not (payload->>'synthetic')::boolean and not exists(select 1 from factory_leads where id=(payload->>'lead_id')::uuid and not blocked) then raise exception 'Контакт остановлен или не найден';end if;
 perform pg_advisory_xact_lock(hashtext('factory-site-budget'));
 if (select count(*) from factory_sites where created_at>now()-interval '24 hours')>=5 then raise exception 'Лимит: 5 сборок в сутки';end if;
 insert into factory_sites(lead_id,name,synthetic,config,asset_blobs) values((payload->>'lead_id')::uuid,payload->>'name',(payload->>'synthetic')::boolean,payload->'config',coalesce(payload->'asset_blobs','{}')) returning * into r;result=to_jsonb(r);
 elsif action='proposal' then
 select * into strict r from factory_sites where id=(payload->>'id')::uuid for update;
 if r.proposal_id is not null then return jsonb_build_object('id',r.proposal_id);end if;
 if r.synthetic or r.status<>'APPROVED' or r.lead_id is null then raise exception 'Нужен утверждённый сайт реальной компании';end if;
 if exists(select 1 from factory_leads where id=r.lead_id and blocked) then raise exception 'Контакт остановлен';end if;
 if r.client_preview_url is null or r.client_preview_url !~ '^https://' or r.client_preview_checked_at is null or r.client_preview_checked_at<now()-interval '24 hours' then raise exception 'Нужна проверенная отдельная клиентская ссылка';end if;
 if not exists(select 1 from factory_pipeline where lead_id=r.lead_id and consent_message_id is not null) then raise exception 'Нет согласия клиента';end if;
 result=public.factory_command('draft',jsonb_build_object('lead_id',r.lead_id,'subject','თქვენი კლინიკის დემო — '||r.name,'body','გამარჯობა, '||r.name||E'-ის გუნდო!\n\nთქვენი თანხმობის საფუძველზე მოვამზადეთ თქვენი კლინიკის ვებგვერდის წინასწარი დემოვერსია: '||r.client_preview_url||E'\n\nეს სადემონსტრაციო ვერსიაა. პაციენტების ჩაწერა გამორთულია. საბოლოო შინაარსი და სასურველი ცვლილებები თქვენთან უნდა შევათანხმოთ.\n\nგთხოვთ, გადახედოთ და მოგვწეროთ თქვენი აზრი. შემდგომ დეტალებს პირადად განვიხილავთ.\n\nOrder & Profit'));
 update factory_sites set proposal_id=(result->>'id')::uuid where id=r.id;
 elsif action='claim' then
 update factory_sites set status='BUILDING' where id=(payload->>'id')::uuid and status='READY' returning * into r;
 if not found then raise exception 'Сборка уже начата';end if;result=to_jsonb(r);
 elsif action='finish' then
 select * into strict r from factory_sites where id=(payload->>'id')::uuid for update;
 if r.status<>'BUILDING' then raise exception 'Нет активной сборки';end if;
 if length((payload->'files')::text)>3000000 or jsonb_array_length(payload->'files')>150 then raise exception 'Превышен лимит размера сайта';end if;
 for f in select value from jsonb_array_elements(payload->'files') loop
 insert into factory_site_files values(r.id,f->>'path',f->>'content',f->>'mime');
 end loop;
 update factory_sites set status='BUILT',report=payload->'report' where id=r.id;
 result=jsonb_build_object('id',r.id,'status','BUILT');
 elsif action='fail' then
 update factory_sites set status='FAILED',error='Сборка не завершена. Проверьте исходные данные.' where id=(payload->>'id')::uuid and status='BUILDING';result='{}';
 elsif action='file' then
 select * into strict r from factory_sites where id=(payload->>'id')::uuid and status in ('BUILT','APPROVED');
 select jsonb_build_object('content',content,'mime',mime) into result from factory_site_files where site_id=r.id and path=payload->>'path';
 if result is null then raise exception 'Файл не найден';end if;
 if payload->>'path'='index.html' or payload->>'path' like '%/index.html' then update factory_sites set opened_at=now() where id=r.id;end if;
 return result;
 elsif action='approve' then
 select * into strict r from factory_sites where id=(payload->>'id')::uuid for update;
 if r.status<>'BUILT' or r.opened_at is null or coalesce((payload->>'ack_pending')::boolean,false)=false then raise exception 'Сначала откройте сайт и подтвердите просмотр неизвестных данных';end if;
 update factory_sites set status='APPROVED',reviewed_at=now(),approved_at=now() where id=r.id;
 result=jsonb_build_object('id',r.id,'status','APPROVED');
 else raise exception 'Неизвестное действие';end if;
 insert into factory_audit(kind,detail) values('site_'||action,jsonb_build_object('id',coalesce(payload->>'id',result->>'id'),'synthetic',r.synthetic));
 return result;
end $$;
revoke all on function public.factory_site_command(text,jsonb) from public,anon,authenticated;
grant execute on function public.factory_site_command(text,jsonb) to service_role;
commit;
