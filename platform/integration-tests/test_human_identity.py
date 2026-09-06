import concurrent.futures
from pathlib import Path
import re
import sys
import time

import pytest

pytest.importorskip('argon2')
import pyotp
from starlette.testclient import TestClient

sys.path.insert(0,str(Path(__file__).parents[1]))
from control.human_identity import HumanIdentity, IdentityError
from control.oauth_provider import OAuthStore, DurableOAuthProvider
from control.identity_web import create_identity_app, SESSION, CSRF
from control.graph import GraphError

PASSWORD = 'synthetic-long-passphrase-for-browser-tests'


@pytest.fixture
def human(tmp_path):
    tmp_path.chmod(0o700)
    now = [time.time()]
    allowed = {'person':{'cajon-sensei'}}
    store = OAuthStore(tmp_path/'oauth.db')
    provider = DurableOAuthProvider(store,'https://identity.example','https://identity.example/mcp',
        {'cajon-sensei','flowing-indian'},lambda p:allowed.get(p,set()),clock=lambda:now[0])
    identity = HumanIdentity(store,provider.grants,clock=lambda:now[0])
    return identity,provider,now,allowed


def enrolled(human):
    identity,_,now,_ = human
    invite = identity.issue_invite('person')
    pending = identity.start_enrollment(invite,'operator',PASSWORD,'fixture')
    secret = identity.pending(pending)['otp_secret']
    session,recovery = identity.finish_enrollment(pending,pyotp.TOTP(secret).at(now[0]),'fixture')
    return session,recovery,secret


def test_enrollment_is_one_use_private_and_requires_current_graph_grant(human):
    identity,provider,now,allowed = human
    with pytest.raises(IdentityError):
        identity.issue_invite('unknown')
    invite = identity.issue_invite('person')
    pending = identity.start_enrollment(invite,'operator',PASSWORD,'fixture')
    with pytest.raises(IdentityError):
        identity.start_enrollment(invite,'another',PASSWORD,'fixture')
    with pytest.raises(IdentityError):
        identity.finish_enrollment(pending,'wrong','fixture')
    allowed['person'] = set()
    with pytest.raises(IdentityError):
        identity.finish_enrollment(pending,'000000','fixture')
    raw = identity.store.path.read_bytes()
    for secret in [invite,pending,PASSWORD]:
        assert secret.encode() not in raw


def test_mfa_replay_race_recovery_and_restart(human):
    identity,provider,now,_ = human
    session,recovery,secret = enrolled(human)
    assert identity.session(session)['principal'] == 'person'
    with pytest.raises(IdentityError):
        identity.login('operator',PASSWORD,pyotp.TOTP(secret).at(now[0]),'fixture')
    now[0] += 31
    code = pyotp.TOTP(secret).at(now[0])
    def attempt(_):
        try:
            return identity.login('operator',PASSWORD,code,'fixture')
        except IdentityError:
            return None
    with concurrent.futures.ThreadPoolExecutor(2) as pool:
        results = list(pool.map(attempt,range(2)))
    assert sum(r is not None for r in results) == 1
    restored = HumanIdentity(OAuthStore(identity.store.path),provider.grants,clock=lambda:now[0])
    assert restored.session(session)['principal'] == 'person'
    assert restored.session(restored.login('operator',PASSWORD,recovery[0],'fixture'))
    with pytest.raises(IdentityError):
        restored.login('operator',PASSWORD,recovery[0],'fixture')
    raw = identity.store.path.read_bytes()
    assert session.encode() not in raw and recovery[0].encode() not in raw


def test_operator_recovery_revoke_and_absolute_session_expiry(human):
    identity,_,now,_ = human
    session,recovery,secret = enrolled(human)
    with pytest.raises(IdentityError):
        identity.issue_invite('person')
    now[0] += 8*3600+1
    assert identity.session(session) is None
    session = identity.login('operator',PASSWORD,recovery[0],'fixture')
    replacement = identity.issue_invite('person',reset=True)
    assert identity.session(session) is None
    with pytest.raises(IdentityError):
        identity.login('operator',PASSWORD,recovery[1],'fixture')
    assert identity.start_enrollment(replacement,'operator',PASSWORD,'fixture')


def test_login_rate_limit_is_durable_and_unknown_users_fail_uniformly(human):
    identity,provider,now,_ = human
    enrolled(human)
    for username in ['operator','missing']:
        with pytest.raises(IdentityError) as exc:
            identity.login(username,'incorrect','000000','fixture')
        assert exc.value.code == 'invalid_credentials'
    for _ in range(10):
        identity.rate('bucket',10,600)
    restored = HumanIdentity(identity.store,provider.grants,clock=lambda:now[0])
    with pytest.raises(IdentityError) as exc:
        restored.rate('bucket',10,600)
    assert exc.value.status == 429


def csrf(response):
    return re.search(r'name="csrf" value="([^"]+)"',response.text).group(1)


def test_http_csrf_host_cookie_enrollment_and_recovery_login(human):
    identity,provider,now,_ = human
    app = create_identity_app(identity,provider)
    with TestClient(app,base_url='https://identity.example') as http:
        response = http.get('/enroll')
        assert response.status_code == 200
        assert response.headers['referrer-policy'] == 'same-origin'
        assert 'frame-ancestors' in response.headers['content-security-policy']
        token = csrf(response)
        assert http.cookies.get(CSRF) == token
        assert 'Secure' in response.headers['set-cookie'] and 'HttpOnly' in response.headers['set-cookie']
        form = dict(csrf=token,invite=identity.issue_invite('person'),username='operator',password=PASSWORD)
        assert http.post('/enroll/start',data=form).status_code == 403
        assert http.post('/enroll/start',data=form,headers={'Origin':'https://hostile.example'}).status_code == 403
        headers = {'Origin':'https://identity.example'}
        response = http.post('/enroll/start',data=form,headers=headers)
        assert 'Set up your authenticator' in response.text
        secret = re.search(r'id="totp-secret">([^<]+)',response.text).group(1)
        response = http.post('/enroll/finish',data=dict(csrf=csrf(response),code=pyotp.TOTP(secret).at(now[0])),headers=headers)
        assert 'Save your recovery codes' in response.text
        recovery = re.findall(r'class="recovery-code">([^<]+)',response.text)
        assert len(recovery) == 8
        cookie = next(c for c in http.cookies.jar if c.name == SESSION)
        assert cookie.secure and not cookie.value in response.text
        account = http.get('/account')
        assert 'Signed in as' in account.text
        assert http.post('/logout',data=dict(csrf=csrf(account),principal='another'),headers=headers).status_code == 400
        response = http.post('/logout',data=dict(csrf=csrf(account)),headers=headers)
        assert 'Sign in' in response.text
        login = http.get('/login')
        response = http.post('/login',data=dict(csrf=csrf(login),username='operator',password=PASSWORD,code=recovery[0]),headers=headers)
        assert 'Your access' in response.text
        response = http.post('/sessions/revoke',data=dict(csrf=csrf(response)),headers=headers)
        assert 'Sign in' in response.text
        assert http.get('/account',follow_redirects=False).status_code == 303
        assert http.get('/login',headers={'Host':'evil.example'}).status_code == 421
        assert http.post('/login',content=b'x'*32769).status_code == 413


def test_revoke_ui_still_works_during_graph_outage(human):
    identity,provider,_,_ = human
    session,_,_ = enrolled(human)
    def unavailable(_):
        raise GraphError('synthetic_graph_outage')
    identity.grants = unavailable
    with TestClient(create_identity_app(identity,provider),base_url='https://identity.example') as http:
        http.cookies.set(SESSION,session)
        response = http.get('/account')
        assert response.status_code == 503
        assert 'You can still revoke' in response.text
        revoked = http.post('/sessions/revoke',data=dict(csrf=csrf(response)),headers={'Origin':'https://identity.example'})
        assert revoked.status_code == 200
        assert identity._credential_session(session) is None
