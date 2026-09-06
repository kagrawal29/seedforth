async (page) => {
  const origin = 'http://localhost:18789';
  const password = 'synthetic-long-passphrase-for-browser-tests';
  const check = (v, message) => { if (!v) throw new Error(message); };
  const checks = [];
  const state = await (await page.request.get(origin+'/__fixture/state')).json();
  const otp = async (secret, now) => page.evaluate(async ({secret,now}) => {
    const alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567';
    let bits = '';
    for (const c of secret) bits += alphabet.indexOf(c).toString(2).padStart(5,'0');
    const key = new Uint8Array(Math.floor(bits.length/8));
    for (let i=0;i<key.length;i++) key[i] = parseInt(bits.slice(i*8,i*8+8),2);
    const counter = new Uint8Array(8);
    new DataView(counter.buffer).setBigUint64(0,BigInt(Math.floor(now/30)));
    const imported = await crypto.subtle.importKey('raw',key,{name:'HMAC',hash:'SHA-1'},false,['sign']);
    const signed = new Uint8Array(await crypto.subtle.sign('HMAC',imported,counter));
    const offset = signed[signed.length-1]&15;
    return ((new DataView(signed.buffer).getUint32(offset)&0x7fffffff)%1000000).toString().padStart(6,'0');
  },{secret,now});
  await page.goto(origin+'/enroll');
  await page.getByLabel('Invitation',{exact:true}).fill(state.invite);
  await page.getByLabel('Username',{exact:true}).fill('browser-operator');
  await page.getByLabel('Passphrase (14–256 characters)',{exact:true}).fill(password);
  await page.getByRole('button',{name:'Set up authenticator',exact:true}).click();
  await page.getByRole('heading',{name:'Set up your authenticator'}).waitFor();
  const secret = await page.locator('#totp-secret').innerText();
  const firstCode = await otp(secret,state.now);
  await page.getByLabel('Authenticator code',{exact:true}).fill(firstCode);
  await page.getByRole('button',{name:'Confirm authenticator'}).click();
  await page.getByRole('heading',{name:'Save your recovery codes'}).waitFor();
  const recovery = await page.locator('.recovery-code').allTextContents();
  check(recovery.length===8,'Missing recovery codes');
  await page.getByRole('link',{name:'I saved my recovery codes'}).click();
  await page.getByRole('heading',{name:'Your access'}).waitFor();
  check(await page.evaluate(()=>localStorage.length===0&&sessionStorage.length===0),'Browser storage contains credentials');
  check(await page.evaluate(()=>document.cookie===''),'Credentials readable by script');
  const cookies = await page.context().cookies();
  check(cookies.filter(c=>c.name.startsWith('__Host-seedforth')).every(c=>c.secure&&c.httpOnly&&c.path==='/'),'Cookie protection missing');
  checks.push('invitation, MFA enrollment, recovery display, secure server-side session');
  await page.getByRole('button',{name:'Sign out of this browser'}).click();
  const login = async code => {
    await page.goto(origin+'/login');
    await page.getByLabel('Username',{exact:true}).fill('browser-operator');
    await page.getByLabel('Passphrase',{exact:true}).fill(password);
    await page.getByLabel('Authenticator or recovery code',{exact:true}).fill(code);
    await page.getByRole('button',{name:'Sign in',exact:true}).click();
  };
  await login(firstCode);
  await page.getByRole('alert').filter({hasText:'Sign-in failed'}).waitFor();
  const advanced = await (await page.request.post(origin+'/__fixture/advance')).json();
  await login(await otp(secret,advanced.now));
  await page.getByRole('heading',{name:'Your access'}).waitFor();
  await page.reload();
  await page.getByRole('heading',{name:'Your access'}).waitFor();
  checks.push('TOTP replay denied, next code login, reconnect');
  const registration = await page.request.post(origin+'/register',{data:{
    client_name:'Untrusted <script>alert("injection")</script> client',token_endpoint_auth_method:'none',
    redirect_uris:['http://127.0.0.1:18790/callback'],grant_types:['authorization_code','refresh_token'],
    response_types:['code'],scope:'mycelium'}});
  check(registration.status()===201,'Registration failed');
  const client = await registration.json();
  const verifier = 'synthetic-pkce-verifier-for-private-qualification-only';
  const challenge = await page.evaluate(async value=>{
    const bytes = new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(value)));
    return btoa(String.fromCharCode(...bytes)).replaceAll('+','-').replaceAll('/','_').replace(/=+$/,'');
  },verifier);
  const authorization = origin+'/authorize?'+Object.entries({client_id:client.client_id,redirect_uri:'http://127.0.0.1:18790/callback',
      resource:origin+'/mcp',response_type:'code',scope:'mycelium',state:'browser-state',
      code_challenge:challenge,code_challenge_method:'S256'}).map(([k,v])=>encodeURIComponent(k)+'='+encodeURIComponent(v)).join('&');
  const parameters = async url => page.evaluate(value=>Object.fromEntries(new URL(value).searchParams),url);
  await page.goto(authorization);
  await page.getByRole('heading',{name:'Connect a client'}).waitFor();
  check(await page.locator('script').count()===0,'Client metadata executed');
  check(await page.locator('input[type=checkbox]').count()===1,'Ungrantable project exposed');
  check(!(await page.locator('input[type=checkbox]').isChecked()),'Project preselected');
  check((await page.locator('main').innerText()).includes('<script>'),'Client name not displayed as text');
  await page.setViewportSize({width:390,height:844});
  check(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'Mobile consent overflows');
  await page.screenshot({path:'.playwright-cli/human-consent-mobile.png',fullPage:true});
  const pendingUrl = page.url();
  const csrf = await page.locator('input[name=csrf]').inputValue();
  const requestId = (await parameters(pendingUrl)).request;
  const forged = await page.request.post(origin+'/consent',{headers:{Origin:'https://hostile.example'},
    form:{csrf,request:requestId,decision:'allow',project:state.scope}});
  check(forged.status()===403,'Cross-origin consent accepted');
  // Exercise server-side validation independently of CSP's fetch prohibition.
  const cookieHeader = (await page.context().cookies(origin)).map(c=>c.name+'='+c.value).join('; ');
  const tampered = await page.request.post(origin+'/consent',{headers:{Origin:origin,Cookie:cookieHeader},
    form:{csrf,request:requestId,decision:'allow',project:state.other}});
  check(tampered.status()===400,'Forged project scope accepted');
  const fakePerson = await page.request.post(origin+'/consent',{headers:{Origin:origin,Cookie:cookieHeader},
    form:{csrf,request:requestId,decision:'allow',project:state.scope,principal:'principal-seedforth-owner'}});
  check(fakePerson.status()===400,'Caller-supplied principal accepted');
  await page.locator('input[type=checkbox]').check();
  await page.getByRole('button',{name:'Allow selected projects'}).click();
  await page.waitForURL('http://127.0.0.1:18790/callback?**');
  const callback = await parameters(page.url());
  check(callback.state==='browser-state','OAuth state lost');
  const issued = await page.request.post(origin+'/token',{form:{client_id:client.client_id,grant_type:'authorization_code',
    code:callback.code,code_verifier:verifier,redirect_uri:'http://127.0.0.1:18790/callback',resource:origin+'/mcp'}});
  check(issued.status()===200,'Browser-approved code exchange failed');
  const token = await issued.json();
  check(token.scope.includes('project:'+state.scope)&&!token.scope.includes(state.other),'Wrong consent scope');
  const read = await page.request.post(origin+'/mcp',{headers:{Authorization:'Bearer '+token.access_token,
    Accept:'application/json, text/event-stream','MCP-Protocol-Version':'2025-11-25'},
    data:{jsonrpc:'2.0',id:1,method:'tools/call',params:{name:'read_work',arguments:{scope:state.scope}}}});
  check(read.status()===200,'Browser-approved token cannot reach MCP');
  const result = await read.json();
  check(result.result?.structuredContent?.data[0]?.title==='Synthetic human scoped work','Browser-approved MCP read not scoped to graph');
  checks.push('escaped client metadata, explicit current project selection, mobile, CSRF, actual callback and OAuth exchange');
  await page.goto(pendingUrl);
  await page.getByRole('alert').filter({hasText:'expired or was already used'}).waitFor();
  await page.goto(authorization);
  await page.getByRole('button',{name:'Deny access'}).click();
  await page.waitForURL('http://127.0.0.1:18790/callback?**');
  check((await parameters(page.url())).error==='access_denied','Consent deny failed');
  await page.goto(origin+'/account');
  await page.getByRole('button',{name:'Sign out of this browser'}).click();
  await login(recovery[0]);
  await page.getByRole('heading',{name:'Your access'}).waitFor();
  await page.getByRole('button',{name:'Revoke all sessions and clients'}).click();
  await page.getByRole('heading',{name:'Sign in',exact:true}).waitFor();
  const expired = await page.request.post(origin+'/token',{form:{client_id:client.client_id,grant_type:'refresh_token',
    refresh_token:token.refresh_token,resource:origin+'/mcp'}});
  check(expired.status()===400,'Revoked client still refreshes');
  await login(recovery[0]);
  await page.getByRole('alert').filter({hasText:'Sign-in failed'}).waitFor();
  checks.push('used request denied, explicit denial, recovery login, all-client revocation, recovery replay denied');
  await login(recovery[1]);
  await page.getByRole('heading',{name:'Your access'}).waitFor();
  await page.request.post(origin+'/__fixture/outage');
  await page.reload();
  await page.getByText('You can still revoke your login sessions and connected clients.',{exact:false}).waitFor();
  await page.getByRole('button',{name:'Revoke all sessions and clients'}).click();
  await page.getByRole('heading',{name:'Sign in',exact:true}).waitFor();
  checks.push('graph outage fails closed while human session/client revocation remains usable');
  return {status:'passed',checks,coverage:'synthetic human browser through real disposable graph; no owner approval'};
}
