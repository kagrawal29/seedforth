"""Trusted human identity surface. No client-supplied principal or bearer storage."""
from contextlib import asynccontextmanager
from html import escape
from pathlib import Path
import re
import secrets
from urllib.parse import urlencode, urlsplit

import anyio
from mcp.server.auth.provider import AuthorizeError
from mcp.server.transport_security import RequestBodyLimitMiddleware
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse, Response
from starlette.routing import Route, Mount

from control.graph import GraphError
from control.human_identity import IdentityError
from control.oauth_http import auth_routes
from control.oauth_provider import project_scopes

SESSION = '__Host-seedforth-session'
CSRF = '__Host-seedforth-csrf'
PENDING = '__Host-seedforth-enroll'


def cookie(response, name, value, age=28800):
    response.set_cookie(name, value, max_age=age, path='/', secure=True, httponly=True,
                        samesite='lax' if name == SESSION else 'strict')


def clear(response, name):
    cookie(response, name, '', 0)


def hidden(name, value):
    return f'<input type="hidden" name="{escape(name)}" value="{escape(value)}">'


def field(label, name, kind='text', autocomplete='off'):
    return (f'<label>{escape(label)}<input name="{escape(name)}" type="{kind}" '
            f'autocomplete="{autocomplete}" required maxlength="256"></label>')


class HumanUI:
    def __init__(self, identity, provider):
        self.identity, self.provider = identity, provider
        self.origin = provider.issuer.rstrip('/')

    async def io(self, method, *args):
        return await anyio.to_thread.run_sync(lambda: method(*args))

    def csrf(self, request):
        if '_seedforth_csrf' in request.scope:
            return request.scope['_seedforth_csrf']
        value = request.cookies.get(CSRF, '')
        request.scope['_seedforth_csrf'] = value if re.fullmatch('[A-Za-z0-9_-]{43}', value) else secrets.token_urlsafe(32)
        return request.scope['_seedforth_csrf']

    def page(self, request, title, body, status=200):
        response = HTMLResponse('<!doctype html><html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            f'<title>{escape(title)} · SeedForth</title><link rel="stylesheet" href="/identity.css">'
            '</head><body><main><header>SeedForth / Mycelium</header>'
            f'<h1>{escape(title)}</h1>{body}<footer>Graph grants define access. '
            'Conversation text cannot expand it.</footer></main></body></html>', status_code=status)
        cookie(response, CSRF, self.csrf(request))
        return response

    async def form(self, request, fields, repeated=()):
        if request.headers.get('origin') != self.origin:
            raise IdentityError('request_origin_rejected', 403)
        form = await request.form()
        if set(form) - (set(fields) | {'csrf'}):
            raise IdentityError('invalid_form')
        if any(len(form.getlist(k)) > 1 for k in form if k not in repeated):
            raise IdentityError('invalid_form')
        if any(not isinstance(v, str) or len(v) > 2048 for _, v in form.multi_items()):
            raise IdentityError('invalid_form')
        csrf = request.cookies.get(CSRF, '')
        if not csrf or not secrets.compare_digest(csrf, form.get('csrf', '')):
            raise IdentityError('request_expired_or_untrusted', 403)
        return form

    def request_id(self, value):
        return value if isinstance(value, str) and re.fullmatch('[A-Za-z0-9_-]{43}', value) else ''

    def login_url(self, request_id=''):
        return '/login' + ('?' + urlencode({'request':request_id}) if request_id else '')

    async def login_page(self, request):
        request_id = self.request_id(request.query_params.get('request', ''))
        body = '<p>Use your passphrase and an authenticator code or one-use recovery code.</p>'
        body += '<form method="post" action="/login">' + hidden('csrf', self.csrf(request)) + hidden('request', request_id)
        body += field('Username', 'username', autocomplete='username')
        body += field('Passphrase', 'password', 'password', 'current-password')
        body += field('Authenticator or recovery code', 'code', autocomplete='one-time-code')
        body += '<button>Sign in</button></form><p><a href="/enroll">Use an enrollment invitation</a></p>'
        body += '<p class="muted">Lost all factors or your passphrase? An authorized operator must reset enrollment. No agent message can reset access.</p>'
        return self.page(request, 'Sign in', body)

    async def login(self, request):
        form = await self.form(request, {'username', 'password', 'code', 'request'})
        session = await self.io(self.identity.login, form.get('username',''), form.get('password',''),
                                form.get('code',''), request.client.host)
        await self.io(self.identity.logout, request.cookies.get(SESSION, ''))
        request_id = self.request_id(form.get('request',''))
        response = RedirectResponse('/consent?'+urlencode({'request':request_id}) if request_id else '/account', status_code=303)
        cookie(response, SESSION, session)
        cookie(response, CSRF, secrets.token_urlsafe(32))
        return response

    async def enrollment(self, request):
        pending = await self.io(self.identity.pending, request.cookies.get(PENDING, ''))
        if pending:
            body = '<p>Add this secret to your authenticator app as a time-based, six-digit code. Keep it private.</p>'
            body += '<p>Account: ' + escape(pending['username']) + '</p>'
            body += '<code id="totp-secret">' + escape(pending['otp_secret']) + '</code>'
            body += '<form method="post" action="/enroll/finish">' + hidden('csrf', self.csrf(request))
            body += field('Authenticator code', 'code', autocomplete='one-time-code')
            body += '<button>Confirm authenticator</button></form><p>This enrollment step expires in ten minutes.</p>'
            return self.page(request, 'Set up your authenticator', body)
        body = '<p>An invitation links your login to an existing graph identity. It does not grant new permissions.</p>'
        body += '<form method="post" action="/enroll/start">' + hidden('csrf', self.csrf(request))
        body += field('Invitation', 'invite', 'password') + field('Username', 'username', autocomplete='username')
        body += field('Passphrase (14–256 characters)', 'password', 'password', 'new-password')
        body += '<button>Set up authenticator</button></form><p><a href="/login">Back to sign in</a></p>'
        return self.page(request, 'Enroll your identity', body)

    async def enroll_start(self, request):
        form = await self.form(request, {'invite','username','password'})
        pending = await self.io(self.identity.start_enrollment, form.get('invite',''), form.get('username',''),
                                form.get('password',''), request.client.host)
        response = RedirectResponse('/enroll', status_code=303)
        cookie(response, PENDING, pending, 600)
        return response

    async def enroll_finish(self, request):
        form = await self.form(request, {'code'})
        session, recovery = await self.io(self.identity.finish_enrollment, request.cookies.get(PENDING,''),
                                          form.get('code',''), request.client.host)
        await self.io(self.identity.logout, request.cookies.get(SESSION,''))
        body = '<p>Save these recovery codes in your password manager. Each replaces an authenticator code once and still requires your passphrase. They will not be shown again.</p><ul>'
        body += ''.join('<li><code class="recovery-code">'+escape(code)+'</code></li>' for code in recovery)
        body += '</ul><p><a class="button" href="/account">I saved my recovery codes</a></p>'
        response = self.page(request, 'Save your recovery codes', body)
        cookie(response, SESSION, session)
        clear(response, PENDING)
        cookie(response, CSRF, secrets.token_urlsafe(32))
        return response

    async def account(self, request):
        session = await self.io(self.identity.session, request.cookies.get(SESSION,''))
        if not session:
            return RedirectResponse('/login', status_code=303)
        connections = await self.io(self.identity.connections, request.cookies.get(SESSION,''))
        body = '<p>Signed in as <strong>'+escape(session['username'])+'</strong>.</p>'
        body += '<p class="muted">Identity: '+escape(session['principal'])+'</p><h2>Connected clients</h2>'
        if not connections:
            body += '<p>No active client authorizations.</p>'
        for connection in connections:
            body += '<article><strong>'+escape(connection['client'])+'</strong><p>'+escape(', '.join(connection['scopes']))+'</p></article>'
        body += '<form method="post" action="/logout">'+hidden('csrf',self.csrf(request))+'<button>Sign out of this browser</button></form>'
        body += '<form method="post" action="/sessions/revoke">'+hidden('csrf',self.csrf(request))+'<button class="danger">Revoke all sessions and clients</button></form>'
        body += '<p class="muted">Signing out does not cancel accepted background work. Use the work controls to stop execution.</p>'
        return self.page(request, 'Your access', body)

    async def logout(self, request):
        await self.form(request, set())
        await self.io(self.identity.logout, request.cookies.get(SESSION,''))
        response = RedirectResponse('/login', status_code=303)
        clear(response, SESSION); clear(response, CSRF)
        return response

    async def revoke(self, request):
        await self.form(request, set())
        await self.io(self.identity.revoke_all, request.cookies.get(SESSION,''))
        response = RedirectResponse('/login', status_code=303)
        clear(response, SESSION); clear(response, CSRF)
        return response

    async def consent(self, request):
        request_id = self.request_id(request.query_params.get('request',''))
        pending = await self.io(self.provider.pending, request_id)
        if not pending:
            raise IdentityError('consent_expired_or_used', 410)
        session = await self.io(self.identity.session, request.cookies.get(SESSION,''))
        if not session:
            return RedirectResponse(self.login_url(request_id), status_code=303)
        client = await self.provider.get_client(pending['client_id'])
        allowed = set(await self.io(self.identity.grants, session['principal'])) & self.provider.allowed_projects
        requested = set(project_scopes(pending['params']['scopes']))
        projects = sorted(allowed & (requested or allowed))
        body = '<p>Signed in as <strong>'+escape(session['username'])+'</strong>.</p>'
        body += '<h2>'+escape(client.client_name or 'Unnamed client')+'</h2>'
        body += '<p>Client ID: <code>'+escape(client.client_id)+'</code></p>'
        callback = pending['params']['redirect_uri']
        body += '<p>Callback: <code>'+escape(callback)+'</code></p>'
        body += '<p>Client metadata is supplied by the client, not a SeedForth trust endorsement.</p>'
        body += '<p>Allow scoped graph/work reads and direction to Delta. This does not approve execution, spending or external effects.</p>'
        body += '<form method="post" action="/consent">'+hidden('csrf',self.csrf(request))+hidden('request',request_id)
        body += '<fieldset><legend>Select projects explicitly</legend>'
        body += ''.join('<label class="choice"><input type="checkbox" name="project" value="'+escape(p)+'">'+escape(p)+'</label>' for p in projects)
        body += '</fieldset><button name="decision" value="allow">Allow selected projects</button>'
        body += '<button class="secondary" name="decision" value="deny">Deny access</button></form>'
        response = self.page(request, 'Connect a client', body)
        # Browsers may enforce form-action across the OAuth callback redirect.
        # This page contains no credential fields and only the validated callback
        # origin is added; no arbitrary script/content source is permitted.
        target = urlsplit(callback)
        response.headers['Content-Security-Policy'] = security_policy(f'{target.scheme}://{target.netloc}')
        return response

    async def decide(self, request):
        form = await self.form(request, {'request','project','decision'}, repeated={'project'})
        session = await self.io(self.identity.session, request.cookies.get(SESSION,''))
        if not session:
            raise IdentityError('authentication_required', 401)
        request_id = self.request_id(form.get('request',''))
        if form.get('decision') == 'deny':
            redirect = await self.io(self.provider.deny, request_id)
        elif form.get('decision') == 'allow':
            redirect = await self.io(self.provider.consent, request_id, session['principal'], form.getlist('project'))
        else:
            raise IdentityError('invalid_form')
        return RedirectResponse(redirect, status_code=303)

    def routes(self):
        async def css(request):
            return Response(Path(__file__).with_name('identity.css').read_text(), media_type='text/css')
        return [Route('/login', self.login_page, methods=['GET']), Route('/login',self.login,methods=['POST']),
            Route('/enroll',self.enrollment),Route('/enroll/start',self.enroll_start,methods=['POST']),
            Route('/enroll/finish',self.enroll_finish,methods=['POST']),Route('/account',self.account),
            Route('/logout',self.logout,methods=['POST']),Route('/sessions/revoke',self.revoke,methods=['POST']),
            Route('/consent',self.consent),Route('/consent',self.decide,methods=['POST']),Route('/identity.css',css)]


def security_policy(callback=''):
    return "default-src 'none'; style-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'" + (' '+callback if callback else '')


class IdentitySecurity:
    def __init__(self, app, identity, origin):
        self.app, self.identity = app, identity
        self.host = urlsplit(origin).netloc

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)
        request = Request(scope)
        if request.headers.get('host') != self.host:
            return await Response('Host rejected',status_code=421)(scope,receive,send)
        try:
            await anyio.to_thread.run_sync(lambda:self.identity.rate('http-peer:'+request.client.host,200,60))
        except IdentityError:
            return await Response('Try again later',status_code=429)(scope,receive,send)
        async def protected(message):
            if message['type'] == 'http.response.start':
                headers = list(message.get('headers',[]))
                existing = {key.lower() for key, _ in headers}
                extras = {b'cache-control':b'no-store',b'referrer-policy':b'same-origin',
                    b'x-content-type-options':b'nosniff',b'x-frame-options':b'DENY',
                    b'content-security-policy':security_policy().encode()}
                for key,value in extras.items():
                    if key not in existing:
                        headers.append((key,value))
                message = {**message,'headers':headers}
            await send(message)
        await self.app(scope,receive,protected)


def create_identity_app(identity, provider, graph=None):
    ui = HumanUI(identity, provider)
    routes = ui.routes()+auth_routes(provider)
    @asynccontextmanager
    async def lifespan(app):
        if graph is None:
            yield
        else:
            async with mcp_app.router.lifespan_context(mcp_app):
                yield
    if graph is not None:
        from control.mcp_gateway import create_mcp, http_app
        mcp_app = http_app(create_mcp(graph,provider,provider.issuer,provider.resource),
                          [urlsplit(provider.issuer).netloc],[provider.issuer.rstrip('/')])
        routes.append(Mount('/', app=mcp_app))
    async def problem(request, exc):
        code = exc.code if isinstance(exc,IdentityError) else 'consent_not_authorized' if isinstance(exc,AuthorizeError) else 'service_unavailable'
        status = exc.status if isinstance(exc,IdentityError) else 400 if isinstance(exc,AuthorizeError) else 503
        messages = {'invalid_credentials':'Sign-in failed. Check your credentials or try a remaining recovery code.',
            'invalid_authenticator_code':'That authenticator code is not valid. Try the current code.',
            'consent_expired_or_used':'This connection request expired or was already used. Start again from your client.',
            'try_again_later':'Too many attempts. Please wait before trying again.'}
        body = ('<p role="alert">'+escape(messages.get(code,code.replace('_',' ')))+
            '</p><p><a href="/login">Sign in</a> · <a href="/enroll">Enrollment</a> · <a href="/account">Your access</a></p>')
        if isinstance(exc,GraphError) and request.cookies.get(SESSION):
            body += '<p>Graph access is unavailable. You can still revoke your login sessions and connected clients.</p>'
            body += '<form method="post" action="/sessions/revoke">'+hidden('csrf',ui.csrf(request))+'<button class="danger">Revoke all sessions and clients</button></form>'
        return ui.page(request, 'Unable to continue', body,status)
    app = Starlette(routes=routes, lifespan=lifespan,
        exception_handlers={IdentityError:problem,AuthorizeError:problem,GraphError:problem})
    return RequestBodyLimitMiddleware(IdentitySecurity(app,identity,provider.issuer),32768)
