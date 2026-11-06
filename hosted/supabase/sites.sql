begin;
create table public.factory_sites(id uuid primary key default gen_random_uuid(),lead_id uuid references public.factory_leads, name text not null, synthetic boolean not null default false, config jsonb not null, asset_blobs jsonb not null default '{}', status text not null default 'READY' check(status in ('READY','BUILDING','BUILT','FAILED','APPROVED')), report jsonb, error text, opened_at timestamptz, reviewed_at timestamptz, approved_at timestamptz, created_at timestamptz not null default now(),proposal_id uuid references public.factory_outbox);
create index factory_sites_lead on public.factory_sites(lead_id);
create table public.factory_site_files(site_id uuid not null references public.factory_sites, path text not null check(path !~ '(^/|(^|/)\.\.(/|$)|\\)' and length(path)<300), content text not null, mime text not null, primary key(site_id,path));
alter table public.factory_sites enable row level security;
alter table public.factory_site_files enable row level security;
revoke all on public.factory_sites,public.factory_site_files from anon,authenticated;
grant all on public.factory_sites,public.factory_site_files to service_role;
create or replace function public.factory_site_command(action text,payload jsonb default '{}') returns jsonb language plpgsql security invoker set search_path=public,pg_temp as $$
declare r public.factory_sites;f jsonb; sid uuid;result jsonb;
begin
 if action='list' then return coalesce((select jsonb_agg(t order by t.created_at desc) from (select id,lead_id,name,synthetic,status,report,error,opened_at,reviewed_at,approved_at,created_at,config->'languages'->>'default' as language from factory_sites) t),'[]');
 elsif action='create' then
 if not (payload->>'synthetic')::boolean and not exists(select 1 from factory_leads where id=(payload->>'lead_id')::uuid and not blocked) then raise exception 'Контакт остановлен или не найден';end if;
 perform pg_advisory_xact_lock(hashtext('factory-site-budget'));
 if (select count(*) from factory_sites where created_at>now()-interval '24 hours')>=5 then raise exception 'Лимит: 5 сборок в сутки';end if;
 insert into factory_sites(lead_id,name,synthetic,config,asset_blobs) values((payload->>'lead_id')::uuid,payload->>'name',(payload->>'synthetic')::boolean,payload->'config',coalesce(payload->'asset_blobs','{}')) returning * into r;result=to_jsonb(r);
 elsif action='proposal' then
 select * into strict r from factory_sites where id=(payload->>'id')::uuid for update;
 if r.proposal_id is not null then return jsonb_build_object('id',r.proposal_id);end if;
 if r.synthetic or r.status<>'APPROVED' or r.lead_id is null then raise exception 'Нужен утверждённый сайт реальной компании';end if;
 if exists(select 1 from factory_leads where id=r.lead_id and blocked) then raise exception 'Контакт остановлен';end if;
 result=public.factory_command('draft',jsonb_build_object('lead_id',r.lead_id,'subject','Сайт для '||r.name,'body','Здравствуйте, команда '||r.name||E'!\n\nПредлагаем подготовить сайт вашей клиники на основе нашего образца ELIT DENT: https://dent-elit.vercel.app/ru/\n\nЭто образец дизайна, а не сайт вашей клиники. Содержание, фотографии и контакты согласуем с вами. Хотели бы посмотреть персональный вариант и обсудить пожелания?\n\nOrder & Profit'));
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
