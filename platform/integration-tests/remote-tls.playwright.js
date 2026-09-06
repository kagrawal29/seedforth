async (page) => {
  // No ignoreHTTPSErrors, owner credential, client token or graph mutation.
  const check = (value, message) => { if (!value) throw new Error(message); };
  const response = await page.goto('https://185.192.96.100/mcp');
  check(response.status() === 503, 'Application unexpectedly exposed');
  check((await page.locator('h1').innerText()).includes('503'), 'Closed state missing');
  const security = await response.securityDetails();
  check(security && security.protocol.startsWith('TLS'), 'Trusted TLS not established');
  check(await page.context().cookies().then(cookies => cookies.length === 0), 'Unexpected cookie');
  await page.setViewportSize({width:390,height:844});
  check(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), 'Closed response overflows mobile');
  console.log(JSON.stringify({status:'passed',coverage:'browser TLS and closed ingress only',security}));
}
