begin;
set local role service_role;
do $$
declare lid uuid; oid uuid; r jsonb;
begin
 r:=public.factory_command('lead','{"name":"QA rolled back","email":"qa@example.invalid","source":"transactional regression"}'); lid:=(r->>'id')::uuid;
 r:=public.factory_command('draft',jsonb_build_object('lead_id',lid,'subject','Test','body','Approved content')); oid:=(r->>'id')::uuid;
 perform public.factory_command('approve',jsonb_build_object('id',oid));
 begin
 perform public.factory_command('claim',jsonb_build_object('id',oid));
 raise exception 'TEST: disabled send unexpectedly claimed';
 exception when others then if sqlerrm like 'TEST:%' then raise; end if; end;
 update public.factory_runtime set sending_enabled=true where id=1;
 perform public.factory_command('claim',jsonb_build_object('id',oid));
 begin
 perform public.factory_command('claim',jsonb_build_object('id',oid));
 raise exception 'TEST: duplicate claim accepted';
 exception when others then if sqlerrm like 'TEST:%' then raise; end if; end;
 perform public.factory_command('unknown',jsonb_build_object('id',oid));
 if (select status from public.factory_outbox where id=oid)<>'UNKNOWN' then raise exception 'unknown not persisted'; end if;
 perform public.factory_command('import',jsonb_build_object('lead_id',lid,'messages',jsonb_build_array(jsonb_build_object('id','qa-rollback-only','direction','IN','subject','Reply','body','Stop','sent_at',now(),'source','regression'))));
 if not (select blocked from public.factory_leads where id=lid) then raise exception 'reply did not stop contact'; end if;
 if not (public.factory_command('snapshot')->'connection'->>'send_enabled')::boolean then raise exception 'snapshot missing config'; end if;
end $$;
rollback;
