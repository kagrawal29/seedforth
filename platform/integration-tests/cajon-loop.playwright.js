async page => {
  // Start the approved Cajon checkout on localhost:18800. Uses simulated browser
  // time to test the counter, not to claim elapsed human practice or musical skill.
  await page.clock.install();
  await page.goto('http://127.0.0.1:18800/');
  await page.locator('#play-btn').click();
  await page.clock.runFor(200);
  const loops = Number(await page.locator('#session-loops').innerText());
  await page.locator('#play-btn').click();
  if (loops !== 0) throw new Error(`Partial groove credited: expected 0, observed ${loops}`);
  return {status:'passed',scenario:'200ms at 80bpm must not credit a complete groove'};
}
