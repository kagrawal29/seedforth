async page => {
  page.setDefaultTimeout(5000);
  const errors = [];
  const onError = error => errors.push(error.message);
  page.on('pageerror', onError);
  const checks = [];
  const loops = async () => Number(await page.locator('#session-loops').innerText());
  const check = (actual, expected, label) => {
    if (actual !== expected) throw new Error(`${label}: expected ${expected}, observed ${actual}`);
    checks.push(label);
  };
  try {
    await page.clock.install();
    await page.goto('http://127.0.0.1:18801/');
    await page.evaluate(() => localStorage.clear());
    await page.reload();
    await page.getByRole('button',{name:'Basic Rock the heartbeat',exact:true}).click();
    await page.clock.runFor(200);
    check(await loops(),0,'first beat does not credit a loop');
    await page.clock.runFor(2850);
    check(await loops(),1,'one complete 80bpm cycle credits exactly one');
    await page.locator('#play-btn').click();
    await page.clock.runFor(400);
    check(await loops(),1,'pause preserves total without adding loops');
    await page.locator('#play-btn').click();
    await page.clock.runFor(200);
    check(await loops(),1,'restart first beat does not credit a loop');
    await page.clock.runFor(2850);
    check(await loops(),2,'restart full cycle credits exactly one');
    await page.clock.runFor(400);
    await page.locator('#tempo-slider').focus();
    await page.locator('#tempo-slider').press('End');
    check(await page.locator('#tempo-value').innerText(),'200','keyboard tempo control reaches 200bpm');
    await page.clock.runFor(200);
    check(await loops(),2,'tempo change discards partial cycle credit');
    await page.clock.runFor(1050);
    check(await loops(),3,'full cycle at new tempo credits once');
    await page.locator('#play-btn').click();
    await page.clock.runFor(1700);
    check(errors.length,0,'pause and resonance render without JavaScript errors');
    await page.locator('#count-in-btn').click();
    await page.locator('#play-btn').click();
    await page.clock.runFor(1250);
    check(await loops(),3,'count-in does not count as played groove');
    await page.clock.runFor(1200);
    check(await loops(),4,'post-count-in cycle credits once');
    await page.locator('#play-btn').click();
    await page.clock.runFor(200);
    await page.setViewportSize({width:390,height:844});
    await page.screenshot({path:'.playwright-cli/cajon-candidate-mobile.png',fullPage:true});
    await page.setViewportSize({width:1440,height:1000});
    await page.screenshot({path:'.playwright-cli/cajon-candidate-desktop.png',fullPage:true});
    check(errors.length,0,'desktop/mobile resize renders without errors');
    return {status:'passed',checks,coverage:'candidate browser timing; not proof of musical accuracy or live deployment'};
  } finally {
    page.removeListener('pageerror',onError);
  }
}
