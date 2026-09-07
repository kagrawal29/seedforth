'use strict';
const $ = id => document.getElementById(id);
let credential = '', scope = '', selected = null, online = false, generation = 0;
let portfolioMode = false;
const API_PATH = document.body.dataset.apiPath || '/api/operation';
let refreshVersion = 0, inspectionVersion = 0, conversationCursor = 0;
class Superseded extends Error {}
function text(tag, value, className) {
  const node = document.createElement(tag); node.textContent = value;
  if (className) node.className = className;
  return node;
}
async function operation(name, params = {}) {
  const requestGeneration = generation;
  const headers = {'Content-Type':'application/json'};
  if (credential) headers.Authorization = `Bearer ${credential}`;
  const csrf = document.body.dataset.csrf;
  if (csrf) headers['X-SeedForth-CSRF'] = csrf;
  const response = await fetch(API_PATH, {method:'POST', headers, body:JSON.stringify({operation:name,scope,params})});
  const result = await response.json();
  if (requestGeneration !== generation) throw new Superseded('Session changed; response discarded');
  if (!response.ok) {
    if (response.status === 401 || response.status === 403) {
      disconnect();
      $('error').textContent = result.error || 'Access denied';
      throw new Superseded('Access ended');
    }
    throw new Error(result.error || 'Request failed');
  }
  return result;
}
function fail(error) {
  if (error instanceof Superseded) return;
  if (!credential) {
    $('error').textContent = error.message;
    return;
  }
  online = false; $('connection').textContent = 'Unavailable — last known view';
  $('error').textContent = `${error.message}. Refresh to reconcile before sending another control.`;
  $('actions').replaceChildren();
}
async function refresh() {
  const requestGeneration = generation, requestVersion = ++refreshVersion;
  try {
    if (portfolioMode) {
      const portfolio = await operation('read-portfolio');
      if (requestGeneration !== generation || requestVersion !== refreshVersion) return;
      online = true; $('error').textContent = ''; $('connection').textContent = 'Connected';
      $('login').hidden = true; $('workspace').hidden = false;
      $('project-name').textContent = 'SeedForth portfolio';
      $('freshness').textContent = `Graph read ${new Date(portfolio.as_of).toLocaleString()} · portfolio projection`;
      $('freshness-detail').textContent = 'Portfolio state is read from Mycelium. Open a project to inspect work, evidence, and sensing detail.';
      $('portfolio').hidden = false; $('project-view').hidden = true;
      $('portfolio-list').replaceChildren();
      for (const item of portfolio.data) {
        const row = text('article', '', 'portfolio-row');
        row.append(text('h3', item.name || item.scope));
        row.append(text('p', `${item.portfolio_state || 'unknown'} · ${item.work_enabled ? 'new work enabled' : 'new work held'} · ${item.work_count || 0} work items · ${item.attention_count || 0} need attention`));
        row.append(text('p', `Process status: ${item.historical_status || 'unknown'} (historical only) · observation: ${item.latest_observation_at || 'unknown'}`, 'muted'));
        if (item.portfolio_state === 'active') {
          const open = text('button', 'Open project', 'portfolio-open');
          open.addEventListener('click', () => { scope = item.scope; portfolioMode = false; refresh(); });
          row.append(open);
        }
        $('portfolio-list').append(row);
      }
      $('authority').replaceChildren(text('p','Portfolio authority is graph-resident. Select a project to inspect work and evidence; process activity is not treated as progress.'));
      $('attention').textContent = '';
      return;
    }
    $('portfolio').hidden = true; $('project-view').hidden = false;
    const [project, work, sources, legacy] = await Promise.all([operation('read-scope'),operation('read-work'),operation('read-sources'),operation('read-legacy-work')]);
    if (requestGeneration !== generation || requestVersion !== refreshVersion) return;
    work.data.push(...legacy.data);
    if (project.data.length !== 1) throw new Error('Project identity unavailable or ambiguous');
    online = true; $('error').textContent = ''; $('connection').textContent = 'Connected';
    $('login').hidden = true; $('workspace').hidden = false;
    $('project-name').textContent = project.data[0].name;
    const sourceSummary=sources.data.length ? sources.data.map(s=>s.unit
      ? `${s.unit}: ${s.unit_status || 'unknown'} (exit ${s.unit_exit_status ?? 'unknown'}, ${s.evidence_status}, last success ${s.last_success_at || 'never'})`
      : s.path
        ? `${s.path}: ${s.code_status} (${s.evidence_status}, last success ${s.last_success_at || 'never'}; selected file only, not repository or hosting health)`
        : `${s.adapter}: ${s.process_status} (${s.evidence_status}, last success ${s.last_success_at || 'never'})`).join(' · ') : 'Source not registered';
    $('freshness').textContent = `Graph read ${new Date(work.as_of).toLocaleString()} · sensing detail available below`;
    $('freshness-detail').textContent = sourceSummary;
    const p = project.data[0];
    $('authority').replaceChildren();
    $('authority').append(text('p',`Portfolio: ${p.portfolio_state || 'unknown'}. New governed work: ${p.work_enabled ? 'enabled' : 'held'}. Legacy status: ${p.historical_status || 'unknown'} (not portfolio authority).`));
    await loadConversation();
    if (Number.isInteger(p.state_version) && p.portfolio_state === 'active') {
      const gate=text('button',p.work_enabled ? 'Pause new work' : 'Enable bounded work');
      gate.addEventListener('click',async()=>{
        gate.disabled=true;
        try {
          await operation('set-scope-work-enabled',{version:p.state_version,enabled:!p.work_enabled,
            reason:p.work_enabled ? 'paused from control board' : ''});
          await refresh();
        } catch(error) { fail(error); }
      });
      $('authority').append(gate,text('p',`Scope gate version ${p.state_version}. ${p.hold_reason || 'No hold reason recorded.'}`,'muted'));
    }
    const attention = work.data.filter(w => w.legacy || w.hold || ['blocked','review'].includes(w.status));
    $('attention').textContent = attention.length ? `${attention.length} items need inspection: ${attention.map(w => w.title).join(', ')}` : 'No attention items in the governed work projection. Legacy incidents are not yet included.';
    $('board').replaceChildren();
    for (const [label, states] of [['Backlog',['proposed']],['Ready',['ready']],['Working',['in_progress']],['Review',['review']],['Done',['done']]]) {
      const lane=text('div','','lane'); lane.append(text('h3',label));
      const rows=work.data.filter(w => states.includes(w.status) && !w.hold);
      if (!rows.length) lane.append(text('p','No work','muted'));
      for (const w of rows) lane.append(card(w));
      $('board').append(lane);
    }
    const blocked=work.data.filter(w => w.hold || !['proposed','ready','in_progress','review','done'].includes(w.status));
    if (blocked.length) {
      const lane=text('div','','lane'); lane.append(text('h3','Blocked / held'));
      blocked.forEach(w=>lane.append(card(w))); $('board').append(lane);
    }
    if (selected) {
      const current=work.data.find(w=>w.id===selected.id);
      if (current) await inspect(current); else {$('inspector').hidden=true;selected=null;}
    }
  } catch (error) {
    if (requestVersion === refreshVersion) fail(error);
  }
}
async function loadConversation() {
  const key = $('conversation-key').value.trim() || 'control-board';
  try {
    const result = await operation('read-conversation',{conversation_key:key,cursor:0});
    $('conversation-messages').replaceChildren();
    conversationCursor = 0;
    for (const message of result.data) {
      const item = text('article','',`conversation-message ${message.role || 'unknown'}`);
      item.append(text('strong',message.role === 'direction' ? 'You' : (message.role || 'Delta')));
      item.append(text('p',message.text || '(no text)'));
      item.append(text('small',`${message.delivery_state || 'unknown'} · ${message.execution_state || 'unknown'} · ${message.created_at || 'time unknown'}`,'muted'));
      $('conversation-messages').append(item);
      if (Number.isInteger(message.sequence)) conversationCursor = Math.max(conversationCursor,message.sequence);
    }
    if (!result.data.length) $('conversation-messages').append(text('p','No messages loaded.','muted'));
    $('conversation-status').textContent = `Conversation read through sequence ${conversationCursor}.`;
  } catch (error) {
    $('conversation-status').textContent = `Conversation unavailable: ${error.message}`;
  }
}
async function sendDirection(event) {
  event.preventDefault();
  const button = $('direction-form').querySelector('button');
  const key = $('conversation-key').value.trim() || 'control-board';
  const message = $('direction-text').value.trim();
  if (!message) return;
  button.disabled = true;
  try {
    const result = await operation('send-conversation-message',{conversation_key:key,
      request_id:`board-${crypto.randomUUID()}`,text:message});
    $('direction-text').value = '';
    const queued = result.data[0];
    $('conversation-status').textContent = `Queued as ${queued?.id || 'a durable message'}; Delta has not executed it.`;
    await loadConversation();
  } catch (error) { fail(error); }
  finally { button.disabled = false; }
}
function card(work) {
  const node=text('button',work.title || work.id,'card');
  node.append(text('span',`${work.assignee || 'Unassigned'} · ${work.verification_status || 'Unverified'}`));
  node.addEventListener('click',()=>inspect(work).catch(fail)); return node;
}
async function inspect(work) {
  const requestGeneration = generation, requestVersion = ++inspectionVersion;
  const current = () => requestGeneration === generation && requestVersion === inspectionVersion;
  selected=work; $('inspector').hidden=false; $('inspect-title').textContent=work.title;
  $('evidence').replaceChildren(text('li','Loading evidence…'));
  $('timeline').replaceChildren(text('li','Loading history…'));
  $('criteria').textContent=`Acceptance: ${work.acceptance || 'Not recorded'}`;
    $('verification').textContent=work.legacy ? `Legacy status: ${work.legacy_status} · not independently verified` : `${work.status} · version ${work.version} · ${work.verification_status || 'unverified'}`;
  $('actions').replaceChildren();
  if (online && !work.legacy) {
    const hold=text('button',work.hold?'Release hold':'Hold work');
    hold.addEventListener('click',async()=>{
      hold.disabled=true;
      try {await operation('hold-work',{id:work.id,version:work.version,hold:!work.hold});await refresh();}
      catch(error){fail(error);}
    });
    $('actions').append(hold,text('p','A hold blocks new governed actions; it does not assert that a legacy process has stopped.','muted'));
  }
  let events, evidence;
  try {
    [events,evidence] = work.legacy ? [{data:[]},{data:[]}] : await Promise.all([
      operation('read-timeline',{id:work.id}), operation('read-evidence',{id:work.id})]);
  } catch (error) { if (current()) throw error; return; }
  if (!current()) return;
  $('evidence').replaceChildren();
  for (const item of evidence.data) $('evidence').append(text('li',`${item.kind}: ${item.status}${item.tests_passed ? ` · ${item.tests_passed} tests` : ''} · ${item.recorded_at} · ${item.revision || item.artifact_hash || item.id}`));
  if (!evidence.data.length) $('evidence').append(text('li','No qualifying evidence linked to this work.'));
  const receipt=evidence.data.find(item=>item.kind==='execution_receipt' && item.artifact_hash);
  const verification=evidence.data.find(item=>item.kind==='release_qualification' && item.status==='passed' && item.artifact_hash===receipt?.artifact_hash);
  if (online && !work.legacy && work.status==='review' && receipt && verification) {
    const accept=text('button','Accept verified result');
    accept.addEventListener('click',async()=>{
      accept.disabled=true;
      try { await operation('review-work',{id:work.id,version:work.version,receipt:receipt.id,
        artifact_hash:receipt.artifact_hash,test_run:verification.id,accept:true}); await refresh(); }
      catch(error) { fail(error); }
    });
    $('actions').append(accept,text('p','Acceptance requires a separate recent test run matching the execution artifact.','muted'));
  }
  $('timeline').replaceChildren();
  for (const event of events.data.filter(e=>e.id)) $('timeline').append(text('li',`${event.created_at}: ${event.from_state} → ${event.to_state} · ${event.actor}`));
  if (!$('timeline').children.length) $('timeline').append(text('li','No recorded state transitions.'));
}
function disconnect() {
  generation++;
  refreshVersion++;inspectionVersion++;
  credential='';scope='';portfolioMode=false;selected=null;online=false;
  conversationCursor=0;
  $('token').value='';$('workspace').hidden=true;$('login').hidden=false;
  $('board').replaceChildren();$('timeline').replaceChildren();$('actions').replaceChildren();$('evidence').replaceChildren();
  $('portfolio-list').replaceChildren();$('portfolio').hidden=true;$('project-view').hidden=false;
  for (const id of ['project-name','freshness','freshness-detail','authority','attention','inspect-title','criteria','verification']) $(id).textContent='';
  $('inspector').hidden=true;$('conversation-messages').replaceChildren(text('p','No messages loaded.','muted'));
  $('conversation-status').textContent='';$('direction-text').value='';$('conversation-key').value='control-board';
  $('connection').textContent='Disconnected';
  $('error').textContent='';
}
$('connect').addEventListener('submit',event=>{event.preventDefault();generation++;credential=$('token').value;scope=$('scope').value;portfolioMode=scope==='seedforth-platform';$('token').value='';refresh();});
$('refresh').addEventListener('click',refresh);$('disconnect').addEventListener('click',disconnect);
$('direction-form').addEventListener('submit',sendDirection);
if (document.body.dataset.sessionAuth === 'true') {
  const allowed = JSON.parse(document.body.dataset.allowedScopes || '[]');
  const options = [...$('scope').options];
  options.forEach(option => { option.hidden = !allowed.includes(option.value); });
  scope = allowed.includes('seedforth-platform') ? 'seedforth-platform' : (allowed[0] || '');
  $('scope').value = scope;
  portfolioMode = scope === 'seedforth-platform';
  generation++;
  refresh();
}
