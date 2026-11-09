// Adapter for the existing encrypted owner-account connection. No new transport secrets.
export const ACCOUNT = 'orderprofit.he@gmail.com';

export async function sendInitial({leadId, db, pipeline, credentials, tokenFor,
  messages, google, mime, verifyContact, checkpoint}) {
  // Validate authorization, token/account and fresh contact before consuming a claim.
  const snapshot = await pipeline('snapshot', {});
  const campaign = snapshot.campaign;
  const runtime = (await db('runtime', {}))[0];
  if (campaign.paused || campaign.policy.initial_sending_enabled !== true ||
      campaign.policy.server_gmail_transport_authorized !== true ||
      runtime?.sending_enabled !== true) throw Error('Sending is disabled');
  if (campaign.policy.sender !== ACCOUNT) throw Error('Wrong sender');
  const token = await tokenFor(await credentials(runtime));
  const crm = await db('snapshot', {});
  const lead = crm.leads.find(x => x.id === leadId);
  if (!lead || lead.blocked) throw Error('Lead unavailable or blocked');
  await db('import', {lead_id:leadId, messages:await messages(lead.email, token)});
  // Implementation must verify published exact email + domain MX + aliases/name/domain dedup.
  const preflight = await verifyContact(lead);
  if (preflight?.ok !== true || preflight.email !== lead.email ||
      preflight.duplicate !== false || preflight.mx !== 'VALID') throw Error('Contact preflight failed');
  const item = await pipeline('initial_claim', {lead_id:leadId});
  if (item.status !== 'SENDING' || item.recipient !== lead.email) throw Error('Claim mismatch');
  // Persist before the external side effect. Never send if checkpoint cannot be written.
  await checkpoint({outbox_id:item.id,stage:'CLAIMED'});
  let sent;
  try {
    sent = await google('messages/send', {token,body:{raw:mime(item)}});
    if (!sent?.id) throw Error('No provider acknowledgement');
  } catch (error) {
    await db('unknown', {id:item.id});
    throw Error('UNKNOWN send result: reconcile Gmail; no automatic retry');
  }
  // If persistence fails after acknowledgement, recover this receipt, never resend.
  await checkpoint({outbox_id:item.id,stage:'ACKNOWLEDGED',provider_id:sent.id,thread_id:sent.threadId||''});
  await db('sent', {id:item.id,provider_id:sent.id,thread_id:sent.threadId||''});
  await pipeline('first_sent', {lead_id:leadId});
  await checkpoint({outbox_id:item.id,stage:'RECORDED',provider_id:sent.id});
  return {outbox_id:item.id,provider_id:sent.id};
}
