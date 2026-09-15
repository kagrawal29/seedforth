import asyncio
import base64
import hashlib
import json
from pathlib import Path
import sys
import time
from urllib.parse import parse_qs, urlsplit

import pytest

pytest.importorskip('mcp')
from mcp.server.auth.provider import AuthorizationParams, AuthorizeError, TokenError
from mcp.shared.auth import OAuthClientInformationFull
from starlette.applications import Starlette
from starlette.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parents[1]))
from control.oauth_provider import DurableOAuthProvider, OAuthStore
from control.oauth_http import auth_routes

ISSUER = 'https://identity.example'
RESOURCE = ISSUER + '/mcp'
VERIFIER = 'synthetic-pkce-verifier-for-private-qualification-only'
CHALLENGE = base64.urlsafe_b64encode(hashlib.sha256(VERIFIER.encode()).digest()).decode().rstrip('=')


def run(awaitable):
    return asyncio.run(awaitable)


@pytest.fixture
def case(tmp_path):
    tmp_path.chmod(0o700)
    allowed = {'person': {'cajon-sensei', 'flowing-indian'}}
    provider = DurableOAuthProvider(OAuthStore(tmp_path/'oauth.db'), ISSUER, RESOURCE,
        {'cajon-sensei', 'flowing-indian'}, lambda person: allowed.get(person, set()))
    client = OAuthClientInformationFull(client_id='synthetic-client', client_name='Untrusted <script>client</script>',
        token_endpoint_auth_method='none', redirect_uris=['http://127.0.0.1:9911/callback'],
        grant_types=['authorization_code', 'refresh_token'], response_types=['code'],
        scope='mycelium project:cajon-sensei project:flowing-indian')
    run(provider.register_client(client))
    return provider, client, allowed


def pending(case, scopes=None):
    provider, client, _ = case
    params = AuthorizationParams(state='client-state', scopes=scopes or ['mycelium'],
        code_challenge=CHALLENGE, redirect_uri=client.redirect_uris[0],
        redirect_uri_provided_explicitly=True, resource=RESOURCE)
    url = run(provider.authorize(client, params))
    return parse_qs(urlsplit(url).query)['request'][0]


def code(case, selected=None):
    provider, client, _ = case
    callback = provider.consent(pending(case), 'person', selected or ['cajon-sensei'])
    values = parse_qs(urlsplit(callback).query)
    assert values['state'] == ['client-state']
    return values['code'][0]


def tokens(case, selected=None):
    provider, client, _ = case
    loaded = run(provider.load_authorization_code(client, code(case, selected)))
    return run(provider.exchange_authorization_code(client, loaded))


def test_durable_restart_private_digests_and_grant_recheck(case):
    provider, client, allowed = case
    result = tokens(case, ['cajon-sensei', 'flowing-indian'])
    restarted = DurableOAuthProvider(OAuthStore(provider.store.path), ISSUER, RESOURCE,
        provider.allowed_projects, provider.grants)
    assert run(restarted.get_client(client.client_id)).client_name == client.client_name
    with pytest.raises(ValueError):
        DurableOAuthProvider(OAuthStore(provider.store.path), ISSUER, ISSUER+'/other',
            provider.allowed_projects, provider.grants)
    assert run(restarted.verify_token(result.access_token)).subject == 'person'
    raw = provider.store.path.read_bytes()
    assert result.access_token.encode() not in raw and result.refresh_token.encode() not in raw
    assert provider.store.path.stat().st_mode & 0o077 == 0
    allowed['person'] = {'cajon-sensei'}
    assert run(restarted.verify_token(result.access_token)).claims['project_scopes'] == ['cajon-sensei']
    allowed['person'] = set()
    assert run(restarted.verify_token(result.access_token)) is None


def test_consent_no_escalation_one_use_and_deny(case):
    provider, client, _ = case
    transaction = pending(case, ['mycelium', 'project:cajon-sensei'])
    with pytest.raises(AuthorizeError):
        provider.consent(transaction, 'person', ['flowing-indian'])
    with pytest.raises(AuthorizeError):
        provider.consent(transaction, 'hostile-person', ['cajon-sensei'])
    provider.consent(transaction, 'person', ['cajon-sensei'])
    with pytest.raises(AuthorizeError):
        provider.consent(transaction, 'person', ['cajon-sensei'])
    denied = pending(case)
    assert parse_qs(urlsplit(provider.deny(denied)).query)['error'] == ['access_denied']
    assert provider.pending(denied) is None


def test_code_exchange_race_and_replay_revoke_issued_family(case):
    provider, client, _ = case
    loaded = run(provider.load_authorization_code(client, code(case)))
    async def race():
        return await asyncio.gather(*(provider.exchange_authorization_code(client, loaded) for _ in range(2)), return_exceptions=True)
    results = run(race())
    assert sum(isinstance(r, TokenError) for r in results) == 1
    token = next(r for r in results if not isinstance(r, Exception))
    assert run(provider.verify_token(token.access_token)) is None
    assert run(provider.load_authorization_code(client, loaded.code)) is None


def test_refresh_rotation_narrowing_and_replay_revokes_family(case):
    provider, client, _ = case
    first = tokens(case, ['cajon-sensei', 'flowing-indian'])
    loaded = run(provider.load_refresh_token(client, first.refresh_token))
    with pytest.raises(TokenError):
        run(provider.exchange_refresh_token(client, loaded, ['mycelium', 'project:admin']))
    second = run(provider.exchange_refresh_token(client, loaded, ['mycelium', 'project:cajon-sensei']))
    assert second.refresh_token != first.refresh_token
    assert run(provider.verify_token(first.access_token)) is None
    assert run(provider.verify_token(second.access_token)).claims['project_scopes'] == ['cajon-sensei']
    assert run(provider.load_refresh_token(client, first.refresh_token)) is None
    assert run(provider.verify_token(second.access_token)) is None
    assert run(provider.load_refresh_token(client, second.refresh_token)) is None


def test_refresh_race_and_revocation(case):
    provider, client, _ = case
    first = tokens(case)
    loaded = run(provider.load_refresh_token(client, first.refresh_token))
    async def race():
        return await asyncio.gather(*(provider.exchange_refresh_token(client, loaded, loaded.scopes) for _ in range(2)), return_exceptions=True)
    results = run(race())
    assert sum(isinstance(r, TokenError) for r in results) == 1
    token = next(r for r in results if not isinstance(r, Exception))
    assert run(provider.verify_token(token.access_token)) is None
    fresh = tokens(case)
    access = run(provider.verify_token(fresh.access_token))
    run(provider.revoke_token(access))
    assert run(provider.load_refresh_token(client, fresh.refresh_token)) is None


def test_other_client_cannot_load_exchange_or_revoke_tokens(case):
    provider, client, _ = case
    other = client.model_copy(update={'client_id':'other-client'})
    run(provider.register_client(other))
    auth_code = code(case)
    assert run(provider.load_authorization_code(other, auth_code)) is None
    loaded = run(provider.load_authorization_code(client, auth_code))
    with pytest.raises(TokenError):
        run(provider.exchange_authorization_code(other, loaded))
    token = run(provider.exchange_authorization_code(client, loaded))
    assert run(provider.load_refresh_token(other, token.refresh_token)) is None
    run(provider.revoke_presented(other, token.refresh_token))
    assert run(provider.verify_token(token.access_token)) is not None
    run(provider.revoke_presented(client, token.refresh_token))
    assert run(provider.verify_token(token.access_token)) is None


def test_access_and_family_absolute_expiry(case):
    provider, client, _ = case
    fresh = tokens(case)
    provider.clock = lambda: time.time() + 601
    assert run(provider.verify_token(fresh.access_token)) is None
    provider.clock = lambda: time.time() + 31 * 86400
    assert run(provider.load_refresh_token(client, fresh.refresh_token)) is None


def test_store_rejects_public_files_and_symlinks(tmp_path):
    tmp_path.chmod(0o755)
    with pytest.raises(ValueError):
        OAuthStore(tmp_path/'oauth.db')
    tmp_path.chmod(0o700)
    file = tmp_path/'oauth.db'
    file.touch(mode=0o644)
    with pytest.raises(ValueError):
        OAuthStore(file)
    link = tmp_path/'link.db'
    link.symlink_to(file)
    with pytest.raises(OSError):
        OAuthStore(link)


def test_http_metadata_registration_resource_pkce_redirect_and_revoke(case):
    provider, client, _ = case
    with TestClient(Starlette(routes=auth_routes(provider)), base_url=ISSUER) as http:
        metadata = http.get('/.well-known/oauth-authorization-server').json()
        assert metadata['issuer'].rstrip('/') == ISSUER
        assert metadata['code_challenge_methods_supported'] == ['S256']
        assert metadata['token_endpoint_auth_methods_supported'] == ['none']
        assert metadata['revocation_endpoint_auth_methods_supported'] == ['none']
        registration = dict(token_endpoint_auth_method='none', redirect_uris=['http://127.0.0.1:9912/cb'],
                            grant_types=['authorization_code', 'refresh_token'], response_types=['code'], scope='mycelium')
        assert http.post('/register', json=registration).status_code == 201
        for uri in ['https://good.example/cb#fragment', 'https://user:pass@good.example/cb', 'http://evil.example/cb', 'javascript:alert(1)', 'https://bad;host.example/cb']:
            assert http.post('/register', json={**registration, 'redirect_uris':[uri]}).status_code == 400
        assert http.post('/register', json={**registration, 'token_endpoint_auth_method':'client_secret_post'}).status_code == 400
        params = dict(client_id=client.client_id, redirect_uri=str(client.redirect_uris[0]), resource=RESOURCE,
                      response_type='code', scope='mycelium', state='state', code_challenge=CHALLENGE, code_challenge_method='S256')
        assert http.get('/authorize', params={**params, 'redirect_uri':'https://evil.example/cb'}, follow_redirects=False).status_code == 400
        assert http.get('/authorize', params={**params, 'code_challenge_method':'plain'}, follow_redirects=False).status_code == 400
        response = http.get('/authorize', params=params, follow_redirects=False)
        assert response.status_code == 302
        transaction = parse_qs(urlsplit(response.headers['location']).query)['request'][0]
        # Synthetic trusted human-session adapter. No public bypass/login route.
        redirect = provider.consent(transaction, 'person', ['cajon-sensei'])
        auth_code = parse_qs(urlsplit(redirect).query)['code'][0]
        form = dict(client_id=client.client_id, grant_type='authorization_code', code=auth_code,
                    redirect_uri=str(client.redirect_uris[0]), resource=RESOURCE, code_verifier=VERIFIER)
        assert http.post('/token', data={**form, 'resource':'https://evil.example/mcp'}).json()['error'] == 'invalid_target'
        assert http.post('/token', data={**form, 'code_verifier':'wrong-but-valid-length-verifier-aaaaaaaaaaaaaaaaaaaa'}).json()['error'] == 'invalid_grant'
        assert http.post('/token', data={**form, 'redirect_uri':'http://127.0.0.1:9912/callback'}).json()['error'] == 'invalid_request'
        response = http.post('/token', data=form)
        assert response.status_code == 200, response.text
        assert response.headers['cache-control'] == 'no-store'
        token = response.json()
        assert run(provider.verify_token(token['access_token'])).resource == RESOURCE
        refresh = dict(client_id=client.client_id, grant_type='refresh_token', refresh_token=token['refresh_token'], resource=RESOURCE)
        assert http.post('/token', data={**refresh, 'resource':'https://evil.example/mcp'}).json()['error'] == 'invalid_target'
        refreshed = http.post('/token', data=refresh)
        assert refreshed.status_code == 200
        assert http.post('/revoke', data=dict(client_id=client.client_id, token=refreshed.json()['refresh_token'])).status_code == 200
        assert run(provider.verify_token(refreshed.json()['access_token'])) is None


def test_http_duplicate_parameter_body_bounds_and_graph_failure(case):
    provider, client, _ = case
    with TestClient(Starlette(routes=auth_routes(provider)), base_url=ISSUER) as http:
        response = http.post('/token', content='resource=a&resource=b', headers={'Content-Type':'application/x-www-form-urlencoded'})
        assert response.json()['error'] == 'invalid_request'
        assert http.post('/register', content=b'x'*32769).status_code == 413
        result = tokens(case)
        def unavailable(_):
            raise RuntimeError('synthetic-private-diagnostic-do-not-return')
        provider.grants = unavailable
        response = http.post('/token', data=dict(client_id=client.client_id, grant_type='refresh_token',
            refresh_token=result.refresh_token, resource=RESOURCE))
        assert response.status_code == 503
        assert 'private-diagnostic' not in response.text
        assert http.post('/revoke', data=dict(client_id=client.client_id, token=result.refresh_token)).status_code == 200
