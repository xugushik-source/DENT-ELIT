begin;
create table public.factory_client_shares(id uuid primary key default gen_random_uuid(),site_id uuid not null references public.factory_sites,token_hash text not null unique check(token_hash ~ '^[a-f0-9]{64}$'),purpose text not null default 'CLIENT' check(purpose in ('CLIENT','QA')),expires_at timestamptz not null,revoked_at timestamptz,created_at timestamptz not null default now());
alter table public.factory_client_shares enable row level security;
revoke all on public.factory_client_shares from public,anon,authenticated;
grant all on public.factory_client_shares to service_role;
create function public.factory_client_file(share_hash text,file_path text) returns jsonb language plpgsql security invoker set search_path=public,pg_temp as $$
declare s factory_sites; h factory_client_shares; f factory_site_files;
begin
 if share_hash !~ '^[a-f0-9]{64}$' or file_path ~ '(^/|(^|/)\.\.(/|$)|\\)' or length(file_path)>300 then raise exception 'Unavailable';end if;
 select * into strict h from factory_client_shares where token_hash=share_hash and revoked_at is null and expires_at>now();
 select * into strict s from factory_sites where id=h.site_id and ((h.purpose='QA' and synthetic and status='BUILT') or (h.purpose='CLIENT' and not synthetic and status='APPROVED'));
 if h.purpose='CLIENT' and not exists(select 1 from factory_pipeline where lead_id=s.lead_id and consent_message_id is not null and stage not in ('SUPPRESSED','OWNER_PAUSED')) then raise exception 'Unavailable';end if;
 select * into strict f from factory_site_files where site_id=s.id and path=file_path;
 return jsonb_build_object('mime',f.mime,'content',f.content,'base_path',s.report->>'basePath','origin',s.report->>'origin');
end $$;
revoke all on function public.factory_client_file(text,text) from public,anon,authenticated;
grant execute on function public.factory_client_file(text,text) to service_role;
create function public.factory_share_command(action text,payload jsonb default '{}') returns jsonb language plpgsql security invoker set search_path=public,pg_temp as $$
declare s factory_sites;h factory_client_shares;base text;url text;raw_token text;
begin
 select * into strict s from factory_sites where id=(payload->>'site_id')::uuid for update;
 if action='issue' then
 if s.synthetic or s.status<>'APPROVED' or coalesce((s.report->'tests'->>'passed')::boolean,false)=false or not coalesce(s.config->'languages'->'enabled' @> '["ka","en","ru"]',false) then raise exception 'Нужна проверенная согласованная сборка ka/en/ru';end if;
 if not exists(select 1 from factory_pipeline where lead_id=s.lead_id and consent_message_id is not null and stage not in ('SUPPRESSED','OWNER_PAUSED')) then raise exception 'Нет согласия клиента';end if;
 select policy->>'client_preview_origin' into base from factory_campaign where id=1;
 url=payload->>'url';raw_token=split_part(url,'/',5);
 if base is null or url<>base||'/p/'||raw_token||'/' or raw_token !~ '^[a-f0-9]{64}$' or payload->>'token_hash'<>encode(sha256(convert_to(raw_token,'UTF8')),'hex') then raise exception 'Неверная клиентская ссылка';end if;
 update factory_client_shares set revoked_at=now() where site_id=s.id and revoked_at is null;
 insert into factory_client_shares(site_id,token_hash,expires_at) values(s.id,payload->>'token_hash',now()+interval '7 days') returning * into h;
 update factory_sites set client_preview_url=url,client_preview_checked_at=null where id=s.id;
 elsif action='verify' then
 select * into strict h from factory_client_shares where site_id=s.id and token_hash=payload->>'token_hash' and revoked_at is null and expires_at>now();
 if payload->'languages_checked' is distinct from '["ka","en","ru"]'::jsonb or coalesce((payload->>'assets_checked')::boolean,false)=false then raise exception 'Проверьте все языки и файлы без входа владельца';end if;
 update factory_sites set client_preview_checked_at=now() where id=s.id;
 elsif action='revoke' then
 update factory_client_shares set revoked_at=now() where site_id=s.id and revoked_at is null;
 update factory_sites set client_preview_url=null,client_preview_checked_at=null where id=s.id;
 update factory_outbox set status='CANCELLED' where id=s.proposal_id and status in ('DRAFT','APPROVED');
 else raise exception 'Unknown operation';end if;
 insert into factory_audit(kind,detail) values('client_share_'||action,jsonb_build_object('site_id',s.id,'share_id',h.id));
 return jsonb_build_object('site_id',s.id,'expires_at',h.expires_at);
end $$;
revoke all on function public.factory_share_command(text,jsonb) from public,anon,authenticated;
grant execute on function public.factory_share_command(text,jsonb) to service_role;
commit;
