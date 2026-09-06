"""Durable external OAuth credential state. Graph grants remain authoritative.

No public login shortcut: consent() is an internal trusted-session entry point.
HTTP adapters must never fill its principal argument from a request parameter.
"""
from functools import wraps
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import sqlite3
import stat
import time
from urllib.parse import urlsplit

import anyio
from pydantic import AnyHttpUrl

from mcp.server.auth.provider import (
    AccessToken, AuthorizationCode, AuthorizeError, RefreshToken, RegistrationError,
    TokenError, construct_redirect_uri,
)
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def offload(method):
    @wraps(method)
    async def wrapped(*args, **kwargs):
        return await anyio.to_thread.run_sync(lambda: method(*args, **kwargs))
    return wrapped


class GraphIdentityGrants:
    def __init__(self, graph):
        self.graph = graph

    def __call__(self, principal):
        return [row['scope'] for row in self.graph.operation('read-identity-scopes', principal, 'seedforth-platform')]


class Transaction:
    # Class context manager: SDK errors are frozen dataclasses. contextmanager's
    # traceback reassignment can turn them into FrozenInstanceError on rollback.
    def __init__(self, path):
        self.path = path

    def __enter__(self):
        self.db = sqlite3.connect(self.path, timeout=5, isolation_level=None)
        self.db.row_factory = sqlite3.Row
        try:
            self.db.execute('BEGIN IMMEDIATE')
        except BaseException:
            self.db.close()
            raise
        return self.db

    def __exit__(self, kind, value, traceback):
        try:
            if kind is None:
                self.db.commit()
            else:
                self.db.rollback()
        finally:
            self.db.close()
        return False


def project_scopes(scopes):
    return sorted({s[8:] for s in scopes if s.startswith('project:')})


class OAuthStore:
    def __init__(self, path):
        self.path = Path(path)
        parent = self.path.parent
        if parent.is_symlink() or parent.stat().st_uid != os.geteuid() or parent.stat().st_mode & 0o077:
            raise ValueError('oauth_directory_must_be_private_and_owned')
        fd = os.open(self.path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        try:
            st = os.fstat(fd)
            if not stat.S_ISREG(st.st_mode) or st.st_uid != os.geteuid() or st.st_mode & 0o077:
                raise ValueError('oauth_store_must_be_private_and_owned')
        finally:
            os.close(fd)
        with self.transaction() as db:
            db.execute('CREATE TABLE IF NOT EXISTS settings (id TEXT PRIMARY KEY, value TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS clients (id TEXT PRIMARY KEY, data TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS requests (id TEXT PRIMARY KEY, data TEXT NOT NULL, expires REAL NOT NULL, used INTEGER NOT NULL DEFAULT 0)')
            db.execute('CREATE TABLE IF NOT EXISTS codes (hash TEXT PRIMARY KEY, data TEXT NOT NULL, expires REAL NOT NULL, used INTEGER NOT NULL DEFAULT 0, family TEXT)')
            db.execute('CREATE TABLE IF NOT EXISTS families (id TEXT PRIMARY KEY, data TEXT NOT NULL, expires REAL NOT NULL, revoked INTEGER NOT NULL DEFAULT 0)')
            db.execute('CREATE TABLE IF NOT EXISTS tokens (hash TEXT PRIMARY KEY, kind TEXT NOT NULL, family TEXT NOT NULL, expires REAL NOT NULL, used INTEGER NOT NULL DEFAULT 0)')
            db.execute('CREATE INDEX IF NOT EXISTS token_family ON tokens(family)')

    def transaction(self):
        return Transaction(self.path)


class DurableOAuthProvider:
    def __init__(self, store, issuer, resource, allowed_projects, grants, clock=time.time):
        self.store, self.issuer, self.resource = store, str(AnyHttpUrl(issuer)), resource
        origin, audience = urlsplit(self.issuer), urlsplit(resource)
        if (origin.query or origin.fragment or origin.username or origin.password
                or origin.path not in {'', '/'} or audience.query or audience.fragment
                or audience.username or audience.password
                or (origin.scheme, origin.netloc) != (audience.scheme, audience.netloc)
                or not (origin.scheme == 'https' or
                        (origin.scheme == 'http' and origin.hostname in {'127.0.0.1', '::1', 'localhost'}))):
            raise ValueError('invalid_oauth_issuer_resource_binding')
        binding = json.dumps({'issuer':self.issuer, 'resource':self.resource}, sort_keys=True)
        with store.transaction() as db:
            previous = db.execute('SELECT value FROM settings WHERE id=\'origin-binding-v1\'').fetchone()
            if previous and previous['value'] != binding:
                raise ValueError('oauth_store_bound_to_different_issuer_or_resource')
            db.execute('INSERT OR IGNORE INTO settings VALUES (?,?)', ('origin-binding-v1', binding))
        self.allowed_projects = set(allowed_projects)
        self.grants, self.clock = grants, clock

    def _current(self, principal):
        # Exceptions propagate to the sanitized HTTP failure boundary: no fallback.
        return set(self.grants(principal)) & self.allowed_projects

    @offload
    def get_client(self, client_id):
        with self.store.transaction() as db:
            row = db.execute('SELECT data FROM clients WHERE id=?', (client_id,)).fetchone()
        return OAuthClientInformationFull.model_validate_json(row['data']) if row else None

    @offload
    def register_client(self, client_info):
        if (client_info.token_endpoint_auth_method != 'none' or client_info.client_secret
                or not client_info.client_id or len(client_info.client_id) > 128
                or not 1 <= len(client_info.redirect_uris) <= 10
                or len(client_info.client_name or '') > 120
                or set(client_info.grant_types) - {'authorization_code', 'refresh_token'}
                or client_info.response_types != ['code']):
            raise RegistrationError('invalid_client_metadata', 'Only public authorization-code PKCE clients are supported')
        valid = {'mycelium'} | {'project:' + p for p in self.allowed_projects}
        if set((client_info.scope or '').split()) - valid:
            raise RegistrationError('invalid_client_metadata', 'Unsupported scope')
        for value in client_info.redirect_uris:
            uri = urlsplit(str(value))
            if ('#' in str(value) or uri.username or uri.password or not uri.hostname
                    or len(str(value)) > 2048 or '\\' in str(value)
                    or not (uri.scheme == 'https' or
                            (uri.scheme == 'http' and uri.hostname in {'127.0.0.1', '::1', 'localhost'}))):
                raise RegistrationError('invalid_redirect_uri', 'HTTPS or native loopback callback required')
        with self.store.transaction() as db:
            if db.execute('SELECT count(*) FROM clients').fetchone()[0] >= 1000:
                raise RegistrationError('invalid_client_metadata', 'Registration capacity reached')
            if db.execute('SELECT 1 FROM clients WHERE id=?', (client_info.client_id,)).fetchone():
                raise RegistrationError('invalid_client_metadata', 'Client already registered')
            db.execute('INSERT INTO clients VALUES (?,?)', (client_info.client_id, client_info.model_dump_json()))

    @offload
    def authorize(self, client, params):
        if params.resource != self.resource:
            raise AuthorizeError('invalid_target', 'Explicit matching resource required')
        requested = set(params.scopes or [])
        valid = {'mycelium'} | {'project:' + p for p in self.allowed_projects}
        if 'mycelium' not in requested or requested - valid:
            raise AuthorizeError('invalid_scope', 'Unsupported scope')
        if not re.fullmatch('[A-Za-z0-9_-]{43}', params.code_challenge):
            raise AuthorizeError('invalid_request', 'S256 challenge required')
        if params.state is not None and len(params.state) > 1024:
            raise AuthorizeError('invalid_request', 'State too long')
        # Exact callback binding even if an SDK relaxes loopback port matching.
        if str(params.redirect_uri) not in {str(u) for u in client.redirect_uris}:
            raise AuthorizeError('invalid_request', 'Unregistered callback')
        transaction_id = secrets.token_urlsafe(32)
        data = dict(client_id=client.client_id, params=params.model_dump(mode='json'))
        with self.store.transaction() as db:
            db.execute('DELETE FROM requests WHERE expires<=?', (self.clock(),))
            if db.execute('SELECT count(*) FROM requests WHERE used=0').fetchone()[0] >= 1000:
                raise AuthorizeError('temporarily_unavailable', 'Authorization capacity reached')
            db.execute('INSERT INTO requests(id,data,expires) VALUES (?,?,?)',
                       (transaction_id, json.dumps(data), self.clock() + 600))
        return self.issuer.rstrip('/') + '/consent?request=' + transaction_id

    def pending(self, transaction_id):
        with self.store.transaction() as db:
            row = db.execute('SELECT * FROM requests WHERE id=? AND used=0 AND expires>?',
                             (transaction_id, self.clock())).fetchone()
        return json.loads(row['data']) if row else None

    def consent(self, transaction_id, principal, selected_projects):
        """Trusted human-session call, not an HTTP operation or agent tool."""
        current = self._current(principal)
        selected = set(selected_projects)
        code = secrets.token_urlsafe(32)
        with self.store.transaction() as db:
            row = db.execute('SELECT * FROM requests WHERE id=? AND used=0 AND expires>?',
                             (transaction_id, self.clock())).fetchone()
            if not row:
                raise AuthorizeError('invalid_request', 'Expired or consumed consent request')
            request = json.loads(row['data'])
            params = request['params']
            requested_projects = set(project_scopes(params['scopes']))
            # A generic mycelium request lets the human choose from current grants;
            # an explicit project request can only be narrowed, never expanded.
            eligible = current & (requested_projects or self.allowed_projects)
            if not selected or not selected <= eligible:
                raise AuthorizeError('access_denied', 'Project selection not authorized')
            scopes = ['mycelium'] + ['project:' + p for p in sorted(selected)]
            data = dict(scopes=scopes, client_id=request['client_id'], subject=principal,
                        code_challenge=params['code_challenge'], redirect_uri=params['redirect_uri'],
                        redirect_uri_provided_explicitly=params['redirect_uri_provided_explicitly'], resource=self.resource)
            db.execute('UPDATE requests SET used=1 WHERE id=?', (transaction_id,))
            db.execute('INSERT INTO codes(hash,data,expires) VALUES (?,?,?)',
                       (digest(code), json.dumps(data), self.clock() + 120))
        return construct_redirect_uri(params['redirect_uri'], code=code, state=params['state'])

    def deny(self, transaction_id):
        with self.store.transaction() as db:
            row = db.execute('SELECT * FROM requests WHERE id=? AND used=0 AND expires>?',
                             (transaction_id, self.clock())).fetchone()
            if not row:
                raise AuthorizeError('invalid_request', 'Expired or consumed consent request')
            db.execute('UPDATE requests SET used=1 WHERE id=?', (transaction_id,))
        params = json.loads(row['data'])['params']
        return construct_redirect_uri(params['redirect_uri'], error='access_denied', state=params['state'])

    @offload
    def load_authorization_code(self, client, authorization_code):
        with self.store.transaction() as db:
            row = db.execute('SELECT * FROM codes WHERE hash=?', (digest(authorization_code),)).fetchone()
            if not row:
                return None
            data = json.loads(row['data'])
            if data['client_id'] != client.client_id:
                return None
            if row['used']:
                if row['family']:
                    db.execute('UPDATE families SET revoked=1 WHERE id=?', (row['family'],))
                return None
            if row['expires'] <= self.clock():
                return None
        return AuthorizationCode(code=authorization_code, expires_at=row['expires'], **data)

    def _mint(self, db, family_id, data, family_expiry):
        access, refresh = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        expiry = min(self.clock() + 600, family_expiry)
        db.execute('INSERT INTO tokens(hash,kind,family,expires) VALUES (?,?,?,?)',
                   (digest(access), 'access', family_id, expiry))
        db.execute('INSERT INTO tokens(hash,kind,family,expires) VALUES (?,?,?,?)',
                   (digest(refresh), 'refresh', family_id, family_expiry))
        return OAuthToken(access_token=access, refresh_token=refresh, token_type='Bearer',
                          expires_in=int(expiry - self.clock()), scope=' '.join(data['scopes']))

    @offload
    def exchange_authorization_code(self, client, authorization_code):
        replay = False
        with self.store.transaction() as db:
            row = db.execute('SELECT * FROM codes WHERE hash=?', (digest(authorization_code.code),)).fetchone()
            if not row or row['expires'] <= self.clock():
                raise TokenError('invalid_grant')
            data = json.loads(row['data'])
            if data['client_id'] != client.client_id:
                raise TokenError('invalid_grant')
            if row['used']:
                db.execute('UPDATE families SET revoked=1 WHERE id=?', (row['family'],))
                replay = True
            else:
                if not set(project_scopes(data['scopes'])) <= self._current(data['subject']):
                    raise TokenError('invalid_grant')
                family_id = secrets.token_urlsafe(24)
                expiry = self.clock() + 30 * 86400
                db.execute('INSERT INTO families(id,data,expires) VALUES (?,?,?)',
                           (family_id, json.dumps(data), expiry))
                db.execute('UPDATE codes SET used=1,family=? WHERE hash=?', (family_id, digest(authorization_code.code)))
                result = self._mint(db, family_id, data, expiry)
        if replay:
            raise TokenError('invalid_grant')
        return result

    def _load_token(self, token, kind, client_id=None):
        with self.store.transaction() as db:
            row = db.execute('SELECT t.*,f.data,f.expires AS family_expires,f.revoked FROM tokens t '
                             'JOIN families f ON f.id=t.family WHERE t.hash=? AND t.kind=?',
                             (digest(token), kind)).fetchone()
            if not row:
                return None
            data = json.loads(row['data'])
            if client_id is not None and data['client_id'] != client_id:
                return None
            if row['used'] and kind == 'refresh':
                db.execute('UPDATE families SET revoked=1 WHERE id=?', (row['family'],))
            if row['used'] or row['revoked'] or min(row['expires'], row['family_expires']) <= self.clock():
                return None
        return dict(row), data

    @offload
    def load_refresh_token(self, client, refresh_token):
        loaded = self._load_token(refresh_token, 'refresh', client.client_id)
        if not loaded:
            return None
        row, data = loaded
        return RefreshToken(token=refresh_token, client_id=client.client_id, scopes=data['scopes'],
                            expires_at=int(row['expires']), subject=data['subject'])

    @offload
    def exchange_refresh_token(self, client, refresh_token, scopes):
        replay = False
        with self.store.transaction() as db:
            row = db.execute('SELECT t.*,f.data,f.expires AS family_expires,f.revoked FROM tokens t '
                             'JOIN families f ON f.id=t.family WHERE t.hash=? AND t.kind=\'refresh\'',
                             (digest(refresh_token.token),)).fetchone()
            if not row:
                raise TokenError('invalid_grant')
            data = json.loads(row['data'])
            if data['client_id'] != client.client_id or row['revoked']:
                raise TokenError('invalid_grant')
            if row['used']:
                db.execute('UPDATE families SET revoked=1 WHERE id=?', (row['family'],))
                replay = True
            else:
                if min(row['expires'], row['family_expires']) <= self.clock():
                    raise TokenError('invalid_grant')
                if (not set(scopes) <= set(data['scopes']) or 'mycelium' not in scopes
                        or not project_scopes(scopes)
                        or not set(project_scopes(scopes)) <= self._current(data['subject'])):
                    raise TokenError('invalid_scope')
                data['scopes'] = sorted(set(scopes))
                db.execute('UPDATE families SET data=? WHERE id=?', (json.dumps(data), row['family']))
                db.execute('UPDATE tokens SET used=1 WHERE family=?', (row['family'],))
                result = self._mint(db, row['family'], data, row['family_expires'])
        if replay:
            raise TokenError('invalid_grant')
        return result

    @offload
    def load_access_token(self, token):
        if not isinstance(token, str) or not 32 <= len(token) <= 1024:
            return None
        loaded = self._load_token(token, 'access')
        if not loaded:
            return None
        row, data = loaded
        projects = set(project_scopes(data['scopes'])) & self._current(data['subject'])
        if not projects:
            return None
        return AccessToken(token=token, client_id=data['client_id'], subject=data['subject'],
                           scopes=['mycelium'] + ['project:' + p for p in sorted(projects)],
                           expires_at=int(row['expires']), resource=self.resource,
                           claims={'iss':self.issuer, 'project_scopes':sorted(projects)})

    async def verify_token(self, token):
        return await self.load_access_token(token)

    @offload
    def revoke_presented(self, client, token):
        # Revocation must work even after graph grants expire or graph is down.
        # It can only reduce authority and must be bound to the registered client.
        with self.store.transaction() as db:
            row = db.execute('SELECT f.id,f.data FROM tokens t JOIN families f ON f.id=t.family WHERE t.hash=?',
                             (digest(token),)).fetchone()
            if row and json.loads(row['data'])['client_id'] == client.client_id:
                db.execute('UPDATE families SET revoked=1 WHERE id=?', (row['id'],))

    @offload
    def revoke_token(self, token):
        with self.store.transaction() as db:
            db.execute('UPDATE families SET revoked=1 WHERE id IN (SELECT family FROM tokens WHERE hash=?)',
                       (digest(token.token),))
