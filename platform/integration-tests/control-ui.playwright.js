async (page) => {
  // Run through @playwright/cli run-code --filename. Synthetic API responses,
  // real shipped DOM/JS and Chromium. Never supply production credentials here.
  const check = (ok, message) => { if (!ok) throw new Error(message); };
  const checks = [];
  await page.unroute('**/api/operation');
  page.setDefaultTimeout(10000);
  const token = 'synthetic-browser-credential-not-a-secret';
  let denied = false, conflict = false, outage = false, delayA = false;
  let pendingA, releaseA;
  let items = [
    {id:'a',title:'Work A',status:'ready',version:1,hold:false,acceptance:'Criterion A'},
    {id:'b',title:'Work B',status:'review',version:2,hold:false,acceptance:'Criterion B'},
  ];
  await page.route('**/api/operation', async route => {
    const request = route.request(), body = request.postDataJSON();
    const reply = (status, value) => route.fulfill({status,contentType:'application/json',body:JSON.stringify(value)});
    if (request.headers().authorization !== `Bearer ${token}`) return reply(401,{error:'invalid_credentials'});
    if (denied || body.scope !== 'flowing-indian') return reply(403,{error:'scope_denied'});
    if (outage) return reply(503,{error:'graph_unavailable'});
    let data = [];
    if (body.operation === 'read-scope') data = [{name:'Flowing Indian fixture',portfolio_state:'active',work_enabled:false}];
    if (body.operation === 'read-work') data = JSON.parse(JSON.stringify(items));
    if (body.operation === 'read-sources') data = [{adapter:'fixture',process_status:'unknown',evidence_status:'stale',last_success_at:null}];
    if (body.operation === 'read-legacy-work') data = [{id:'legacy',title:'Legacy <img src=x onerror=alert(1)>',legacy:true,status:'legacy_needs_triage',legacy_status:'done'}];
    if (body.operation === 'read-timeline' && body.params.id === 'a' && delayA) {
      pendingA();
      await new Promise(resolve => { releaseA = resolve; });
    }
    if (body.operation === 'read-evidence') data = [{kind:'TestRun',status:`evidence-${body.params.id}`,recorded_at:'fixture',id:body.params.id}];
    if (body.operation === 'hold-work') {
      const work = items.find(w => w.id === body.params.id);
      if (conflict || work.version !== body.params.version) return reply(409,{error:'transition_denied_or_version_conflict'});
      work.hold = body.params.hold; work.version++; data = [work];
    }
    return reply(200,{data,as_of:new Date().toISOString(),scope:body.scope});
  });
  const connect = async () => {
    await page.locator('#token').fill(token);
    await page.getByRole('button',{name:'Connect',exact:true}).click();
    await page.waitForFunction(() => document.querySelector('#connection').textContent === 'Connected');
  };
  const inspect = async title => {
    await page.getByRole('button',{name:new RegExp(`^${title}`)}).click();
    await page.waitForFunction(id => document.querySelector('#evidence').textContent.includes(`evidence-${id}`),title === 'Work A' ? 'a' : 'b');
  };
  await page.goto('http://127.0.0.1:18787/');
  await page.setViewportSize({width:1440,height:1000});
  await connect();
  check(await page.locator('#token').inputValue() === '', 'Credential input retained');
  check(await page.evaluate(() => localStorage.length === 0 && sessionStorage.length === 0), 'Credential persisted in browser storage');
  check((await page.locator('#freshness').innerText()).includes('stale'), 'Stale sensing hidden');
  check(await page.locator('#board img').count() === 0, 'Graph text interpreted as HTML');
  checks.push('login, memory-only credential, stale sensing, graph-text escaping');
  await page.getByRole('button',{name:/^Legacy/}).click();
  check(await page.locator('#actions button').count() === 0, 'Legacy work exposes controls');
  check((await page.locator('#verification').innerText()).includes('not independently verified'), 'Legacy done credited as verified');
  checks.push('legacy status is unverified and non-actionable');
  await inspect('Work A');
  await page.getByRole('button',{name:'Hold work',exact:true}).click();
  await page.getByRole('button',{name:'Release hold',exact:true}).waitFor();
  check(items[0].hold && items[0].version === 2, 'Hold not versioned');
  conflict = true;
  await page.getByRole('button',{name:'Release hold',exact:true}).click();
  await page.waitForFunction(() => document.querySelector('#error').textContent.includes('version_conflict'));
  check(await page.locator('#actions button').count() === 0, 'Failed control remains actionable');
  conflict = false;
  await page.getByRole('button',{name:'Refresh',exact:true}).click();
  await page.getByRole('button',{name:'Release hold',exact:true}).waitFor();
  checks.push('hold, stale-version rejection, explicit refresh recovery');
  await page.setViewportSize({width:390,height:844});
  check(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), 'Mobile page overflows');
  await page.screenshot({path:'.playwright-cli/control-mobile.png',fullPage:true});
  await page.setViewportSize({width:1440,height:1000});
  await page.screenshot({path:'.playwright-cli/control-desktop.png',fullPage:true});
  checks.push('390px mobile and desktop rendering');
  outage = true;
  await page.getByRole('button',{name:'Refresh',exact:true}).click();
  await page.waitForFunction(() => document.querySelector('#error').textContent.includes('graph_unavailable'));
  check(await page.locator('#actions button').count() === 0, 'Outage permits controls');
  outage = false;
  await page.getByRole('button',{name:'Refresh',exact:true}).click();
  await page.getByRole('button',{name:'Release hold',exact:true}).waitFor();
  checks.push('graph outage clears controls and refresh recovers');
  delayA = true;
  const started = new Promise(resolve => { pendingA = resolve; });
  await page.getByRole('button',{name:/^Work A/}).click();
  await started;
  await inspect('Work B');
  releaseA();
  await page.waitForTimeout(300);
  check((await page.locator('#evidence').innerText()).includes('evidence-b'), 'Late Work A response overwrote Work B evidence');
  checks.push('late inspector response cannot cross work identity');
  delayA = true;
  const logoutStarted = new Promise(resolve => { pendingA = resolve; });
  await page.getByRole('button',{name:/^Work A/}).click();
  await logoutStarted;
  await page.getByRole('button',{name:'Disconnect',exact:true}).click();
  releaseA();
  await page.waitForTimeout(300);
  check(await page.locator('#board').innerText() === '' && await page.locator('#evidence').innerText() === '', 'Logout leaked retained work');
  check(await page.locator('#connection').innerText() === 'Disconnected', 'Old request changed logout state');
  delayA = false;
  await connect();
  denied = true;
  await page.getByRole('button',{name:'Refresh',exact:true}).click();
  await page.locator('#login').waitFor({state:'visible'});
  check(await page.locator('#board').innerText() === '', 'Revocation retained scope data');
  checks.push('in-flight logout and revocation clear scoped content');
  return {status:'passed',checks,coverage:'synthetic API browser regression; not live graph acceptance'};
}
