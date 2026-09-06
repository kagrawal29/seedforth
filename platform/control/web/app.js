'use strict';
const $ = id => document.getElementById(id);
let credential = '', scope = '', selected = null, online = false, generation = 0;
function text(tag, value, className) {
  const node = document.createElement(tag); node.textContent = value;
  if (className) node.className = className;
  return node;
}
async function operation(name, params = {}) {
  const requestGeneration = generation;
  const response = await fetch('/api/operation', {method:'POST', headers:{'Content-Type':'application/json', Authorization:`Bearer ${credential}`}, body:JSON.stringify({operation:name,scope,params})});
  const result = await response.json();
  if (requestGeneration !== generation) throw new Error('Session changed; response discarded');
  if (!response.ok) {
    if (response.status === 401 || response.status === 403) disconnect();
    throw new Error(result.error || 'Request failed');
  }
  return result;
}
function fail(error) {
  online = false; $('connection').textContent = 'Unavailable — last known view';
  $('error').textContent = `${error.message}. Refresh to reconcile before sending another control.`;
  $('actions').replaceChildren();
}
async function refresh() {
  try {
    const [project, work, sources] = await Promise.all([operation('read-scope'),operation('read-work'),operation('read-sources')]);
    if (project.data.length !== 1) throw new Error('Project identity unavailable or ambiguous');
    online = true; $('error').textContent = ''; $('connection').textContent = 'Connected';
    $('login').hidden = true; $('workspace').hidden = false;
    $('project-name').textContent = project.data[0].name;
    const sourceSummary=sources.data.length ? sources.data.map(s=>`${s.adapter}: ${s.process_status} (${s.evidence_status}, last success ${s.last_success_at || 'never'})`).join(' · ') : 'Runtime source not registered';
    $('freshness').textContent = `Graph read ${new Date(work.as_of).toLocaleString()} · ${sourceSummary}`;
    const p = project.data[0];
    $('authority').textContent = `Portfolio: ${p.portfolio_state || 'unknown'}. New governed work: ${p.work_enabled ? 'enabled' : 'held'}. Legacy status: ${p.historical_status || 'unknown'} (not portfolio authority).`;
    const attention = work.data.filter(w => w.hold || ['blocked','review'].includes(w.status));
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
  } catch (error) { fail(error); }
}
function card(work) {
  const node=text('button',work.title || work.id,'card');
  node.append(text('span',`${work.assignee || 'Unassigned'} · ${work.verification_status || 'Unverified'}`));
  node.addEventListener('click',()=>inspect(work).catch(fail)); return node;
}
async function inspect(work) {
  selected=work; $('inspector').hidden=false; $('inspect-title').textContent=work.title;
  $('criteria').textContent=`Acceptance: ${work.acceptance || 'Not recorded'}`;
  $('verification').textContent=`${work.status} · version ${work.version} · ${work.verification_status || 'unverified'}`;
  $('actions').replaceChildren();
  if (online) {
    const hold=text('button',work.hold?'Release hold':'Hold work');
    hold.addEventListener('click',async()=>{
      hold.disabled=true;
      try {await operation('hold-work',{id:work.id,version:work.version,hold:!work.hold});await refresh();}
      catch(error){fail(error);}
    });
    $('actions').append(hold,text('p','A hold blocks new governed actions; it does not assert that a legacy process has stopped.','muted'));
  }
  const events=await operation('read-timeline',{id:work.id});
  $('timeline').replaceChildren();
  for (const event of events.data.filter(e=>e.id)) $('timeline').append(text('li',`${event.created_at}: ${event.from_state} → ${event.to_state} · ${event.actor}`));
  if (!$('timeline').children.length) $('timeline').append(text('li','No recorded state transitions.'));
}
function disconnect() {
  generation++;
  credential='';scope='';selected=null;online=false;
  $('token').value='';$('workspace').hidden=true;$('login').hidden=false;
  $('board').replaceChildren();$('timeline').replaceChildren();$('actions').replaceChildren();
  for (const id of ['project-name','freshness','authority','attention','inspect-title','criteria','verification']) $(id).textContent='';
  $('inspector').hidden=true;
  $('connection').textContent='Disconnected';
}
$('connect').addEventListener('submit',event=>{event.preventDefault();generation++;credential=$('token').value;scope=$('scope').value;$('token').value='';refresh();});
$('refresh').addEventListener('click',refresh);$('disconnect').addEventListener('click',disconnect);
