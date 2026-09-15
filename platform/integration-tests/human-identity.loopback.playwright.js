async (page) => {
  // Production identity through an SSH loopback tunnel. The Host header keeps
  // the reviewed public issuer binding while no public route is contacted.
  const local = 'http://127.0.0.1:18792';
  const publicHost = '185.192.96.100';
  const callback = 'http://127.0.0.1:18791/callback';
  const password = 'loopback-qualification-passphrase-2026';
  const check = (value, message) => { if (!value) throw new Error(message); };
  const invitation = await (await page.request.get('http://127.0.0.1:18791/invitation.json')).json();
  await page.goto(local + '/enroll');
  await page.getByLabel('Invitation',{exact:true}).fill(invitation.invitation);
  await page.getByLabel('Username',{exact:true}).fill('loopback-qualification-2');
  await page.getByLabel('Passphrase (14–256 characters)',{exact:true}).fill(password);
  await page.getByRole('button',{name:'Set up authenticator',exact:true}).click();
  await page.getByRole('heading',{name:'Set up your authenticator'}).waitFor();
  const secret = await page.locator('#totp-secret').innerText();
  const otp = now => page.evaluate(async ({secret,now}) => {
    const alphabet='ABCDEFGHIJKLMNOPQRSTUVWXYZ234567'; let bits='';
    for (const c of secret) bits += alphabet.indexOf(c).toString(2).padStart(5,'0');
    const key=new Uint8Array(Math.floor(bits.length/8));
    for (let i=0;i<key.length;i++) key[i]=parseInt(bits.slice(i*8,i*8+8),2);
    const counter=new Uint8Array(8); new DataView(counter.buffer).setBigUint64(0,BigInt(Math.floor(now/30)));
    const imported=await crypto.subtle.importKey('raw',key,{name:'HMAC',hash:'SHA-1'},false,['sign']);
    const signed=new Uint8Array(await crypto.subtle.sign('HMAC',imported,counter));
    const offset=signed[signed.length-1]&15;
    return ((new DataView(signed.buffer).getUint32(offset)&0x7fffffff)%1000000).toString().padStart(6,'0');
  },{secret,now});
  await page.getByLabel('Authenticator code',{exact:true}).fill(await otp(Date.now()/1000));
  await page.getByRole('button',{name:'Confirm authenticator'}).click();
  await page.getByRole('heading',{name:'Save your recovery codes'}).waitFor();
  const recovery=await page.locator('.recovery-code').allTextContents();
  check(recovery.length===8,'Production enrollment did not issue recovery codes');
  await page.getByRole('link',{name:'I saved my recovery codes'}).click();
  await page.getByRole('heading',{name:'Your access'}).waitFor();
  check(await page.evaluate(()=>localStorage.length===0&&sessionStorage.length===0),'Credential entered browser storage');
  check(await page.evaluate(()=>document.cookie===''),'Credential readable by script');
  await page.getByRole('button',{name:'Sign out of this browser'}).click();
  await page.goto(local+'/login');
  const boundary=Math.floor(Date.now()/30000);
  await page.waitForFunction(value=>Math.floor(Date.now()/30000)!==value,boundary);
  await page.getByLabel('Username',{exact:true}).fill('loopback-qualification-2');
  await page.getByLabel('Passphrase',{exact:true}).fill(password);
  await page.getByLabel('Authenticator or recovery code',{exact:true}).fill(await otp(Date.now()/1000));
  await page.getByRole('button',{name:'Sign in',exact:true}).click();
  await page.getByRole('heading',{name:'Your access'}).waitFor();
  const registration=await page.request.post(local+'/register',{headers:{Host:publicHost},data:{
    client_name:'Loopback qualification client',token_endpoint_auth_method:'none',redirect_uris:[callback],
    grant_types:['authorization_code','refresh_token'],response_types:['code'],scope:'mycelium'}});
  check(registration.status()===201,'Loopback OAuth registration failed');
  const client=await registration.json();
  const verifier='loopback-qualification-verifier-abcdefghijklmnopqrstuvwxyz123456789';
  const challenge=await page.evaluate(async value=>{
    const bytes=new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(value)));
    return btoa(String.fromCharCode(...bytes)).replaceAll('+','-').replaceAll('/','_').replace(/=+$/,'');
  },verifier);
  const query=Object.entries({client_id:client.client_id,redirect_uri:callback,resource:'https://185.192.96.100/mcp',
    response_type:'code',scope:'mycelium',state:'loopback-state',code_challenge:challenge,code_challenge_method:'S256'})
    .map(([key,value])=>encodeURIComponent(key)+'='+encodeURIComponent(value)).join('&');
  await page.goto(local+'/authorize?'+query);
  await page.getByRole('heading',{name:'Connect a client'}).waitFor();
  const checkbox=page.locator('input[type=checkbox]'); check(await checkbox.count()===1,'Unexpected project choices');
  await checkbox.first().check();
  await page.getByRole('button',{name:'Allow selected projects'}).click();
  await page.waitForURL(callback+'?**');
  const params=await page.evaluate(()=>Object.fromEntries(new URL(location.href).searchParams));
  check(params.state==='loopback-state'&&params.code,'OAuth callback missing code');
  const issued=await page.request.post(local+'/token',{headers:{Host:publicHost},form:{client_id:client.client_id,
    grant_type:'authorization_code',code:params.code,code_verifier:verifier,redirect_uri:callback,
    resource:'https://185.192.96.100/mcp'}});
  check(issued.status()===200,'Loopback OAuth token exchange failed');
  const token=await issued.json();
  const read=await page.request.post(local+'/mcp',{headers:{Host:publicHost,Authorization:'Bearer '+token.access_token,
    Accept:'application/json, text/event-stream','MCP-Protocol-Version':'2025-11-25'},data:{jsonrpc:'2.0',id:1,
      method:'tools/call',params:{name:'read_work',arguments:{scope:'cajon-sensei'}}}});
  check(read.status()===200,'Loopback OAuth token did not reach MCP');
  const result=await read.json();
  check(result.result?.structuredContent?.data,'Loopback MCP read did not return scoped graph data');
  const denied=await page.request.post(local+'/mcp',{headers:{Host:publicHost,Authorization:'Bearer '+token.access_token,
    Accept:'application/json, text/event-stream','MCP-Protocol-Version':'2025-11-25'},data:{jsonrpc:'2.0',id:2,
      method:'tools/call',params:{name:'read_work',arguments:{scope:'flowing-indian'}}}});
  const deniedBody=await denied.json();
  check(deniedBody.result?.structuredContent?.error==='scope_denied','Loopback MCP scope isolation failed');
  return {status:'passed',checks:['production loopback enrollment and MFA','server-side session and no browser credential storage',
    'OAuth registration, PKCE consent, callback and token exchange','MCP scoped read and foreign-scope denial'],
    coverage:'loopback tunnel to deployed identity; public ingress not contacted'};
}
