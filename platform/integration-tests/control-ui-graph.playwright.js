async (page) => {
  // Real browser -> HTTP Boundary -> authored Cypher -> disposable Neo4j.
  // Only the synthetic gateway at this fixed port is an allowed target.
  await page.unroute('**/api/operation');
  page.setDefaultTimeout(10000);
  await page.goto('http://127.0.0.1:18788/');
  await page.locator('#scope').selectOption('seedforth-platform');
  await page.locator('#token').fill('synthetic-browser-credential-not-a-secret');
  await page.getByRole('button',{name:'Connect',exact:true}).click();
  await page.waitForFunction(() => document.querySelector('#connection').textContent === 'Connected');
  if (await page.locator('#board .card').count() !== 22) throw new Error('Expected exact graph plan');
  await page.getByRole('button',{name:/^Verify current baseline and writer census/}).click();
  await page.waitForFunction(() => !document.querySelector('#timeline').textContent.includes('Loading'));
  const initiallyHeld = await page.getByRole('button',{name:'Release hold',exact:true}).count() === 1;
  const first = initiallyHeld ? 'Release hold' : 'Hold work';
  const second = initiallyHeld ? 'Hold work' : 'Release hold';
  const prior = await page.locator('#verification').innerText();
  await page.getByRole('button',{name:first,exact:true}).click();
  await page.getByRole('button',{name:second,exact:true}).waitFor();
  const changed = await page.locator('#verification').innerText();
  if (prior === changed) throw new Error('Graph control did not advance version');
  await page.getByRole('button',{name:'Disconnect',exact:true}).click();
  await page.reload();
  if (await page.locator('#workspace').isVisible()) throw new Error('Session persisted after logout');
  await page.locator('#scope').selectOption('seedforth-platform');
  await page.locator('#token').fill('synthetic-browser-credential-not-a-secret');
  await page.getByRole('button',{name:'Connect',exact:true}).click();
  await page.getByRole('button',{name:/^Verify current baseline and writer census/}).click();
  await page.getByRole('button',{name:second,exact:true}).waitFor();
  await page.getByRole('button',{name:second,exact:true}).click();
  await page.getByRole('button',{name:first,exact:true}).waitFor();
  await page.screenshot({path:'.playwright-cli/control-real-graph.png',fullPage:true});
  await page.getByRole('button',{name:'Disconnect',exact:true}).click();
  await page.locator('#scope').selectOption('cajon-sensei');
  await page.locator('#token').fill('synthetic-browser-credential-not-a-secret');
  await page.getByRole('button',{name:'Connect',exact:true}).click();
  await page.waitForFunction(() => document.querySelector('#error').textContent.includes('scope_denied'));
  if (await page.locator('#workspace').isVisible()) throw new Error('Scope denial exposed workspace');
  return {status:'passed',checks:['22 graph-backed work packages','versioned hold applied and survived logout/reload','initial hold disposition restored','scoped gateway denial'],coverage:'real HTTP and Cypher on disposable Neo4j; no production mutation'};
}
