"""External human credentials/sessions; graph principals and grants are authority."""
import json
import re
import secrets
import threading
import time

from argon2 import PasswordHasher, Type
from argon2.exceptions import VerificationError, InvalidHashError
import pyotp

from control.oauth_provider import digest


class IdentityError(Exception):
    def __init__(self, code, status=400):
        self.code, self.status = code, status
        super().__init__(code)


class HumanIdentity:
    def __init__(self, store, grants, clock=time.time):
        self.store, self.grants, self.clock = store, grants, clock
        self.hasher = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=1, type=Type.ID)
        self.hash_slots = threading.BoundedSemaphore(2)
        self.dummy = self.hasher.hash(secrets.token_urlsafe(32))
        with store.transaction() as db:
            db.execute('CREATE TABLE IF NOT EXISTS human_invites (hash TEXT PRIMARY KEY, principal TEXT NOT NULL, expires REAL NOT NULL, used INTEGER NOT NULL DEFAULT 0)')
            db.execute('CREATE TABLE IF NOT EXISTS human_pending (hash TEXT PRIMARY KEY, principal TEXT NOT NULL, username TEXT NOT NULL, password TEXT NOT NULL, otp_secret TEXT NOT NULL, expires REAL NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS human_users (username TEXT PRIMARY KEY, principal TEXT UNIQUE NOT NULL, password TEXT NOT NULL, otp_secret TEXT NOT NULL, last_step INTEGER NOT NULL, enabled INTEGER NOT NULL DEFAULT 1)')
            db.execute('CREATE TABLE IF NOT EXISTS human_sessions (hash TEXT PRIMARY KEY, principal TEXT NOT NULL, expires REAL NOT NULL, created REAL NOT NULL, revoked INTEGER NOT NULL DEFAULT 0)')
            db.execute('CREATE TABLE IF NOT EXISTS human_recovery (hash TEXT PRIMARY KEY, principal TEXT NOT NULL, used INTEGER NOT NULL DEFAULT 0)')
            db.execute('CREATE TABLE IF NOT EXISTS human_limits (key TEXT PRIMARY KEY, started REAL NOT NULL, count INTEGER NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS human_events (id TEXT PRIMARY KEY, principal TEXT, kind TEXT NOT NULL, at REAL NOT NULL)')

    def _event(self, db, principal, kind):
        db.execute('INSERT INTO human_events VALUES (?,?,?,?)',
                   (secrets.token_hex(16), principal, kind, self.clock()))

    def rate(self, key, maximum, window):
        now = self.clock()
        with self.store.transaction() as db:
            db.execute('DELETE FROM human_limits WHERE started<?', (now - 86400,))
            row = db.execute('SELECT * FROM human_limits WHERE key=?', (digest(key),)).fetchone()
            count = row['count'] + 1 if row and row['started'] > now - window else 1
            started = row['started'] if row and row['started'] > now - window else now
            db.execute('INSERT OR REPLACE INTO human_limits VALUES (?,?,?)', (digest(key), started, count))
        if count > maximum:
            raise IdentityError('try_again_later', 429)

    def _hash(self, password, encoded=None):
        if not self.hash_slots.acquire(blocking=False):
            raise IdentityError('authentication_busy', 503)
        try:
            if encoded is None:
                return self.hasher.hash(password)
            try:
                return self.hasher.verify(encoded, password)
            except (VerificationError, InvalidHashError):
                return False
        finally:
            self.hash_slots.release()

    def issue_invite(self, principal, *, reset=False, lifetime=86400):
        """Protected operator-only enrollment/recovery. Never an agent/browser API."""
        if not self.grants(principal) or not 60 <= lifetime <= 86400:
            raise IdentityError('principal_not_enrollable')
        token = secrets.token_urlsafe(32)
        with self.store.transaction() as db:
            user = db.execute('SELECT * FROM human_users WHERE principal=?', (principal,)).fetchone()
            if user and not reset:
                raise IdentityError('identity_already_enrolled')
            if reset:
                self._revoke_all(db, principal)
                db.execute('DELETE FROM human_users WHERE principal=?', (principal,))
                db.execute('DELETE FROM human_recovery WHERE principal=?', (principal,))
            db.execute('DELETE FROM human_pending WHERE principal=?', (principal,))
            db.execute('UPDATE human_invites SET used=1 WHERE principal=?', (principal,))
            db.execute('INSERT INTO human_invites(hash,principal,expires) VALUES (?,?,?)',
                       (digest(token), principal, self.clock() + lifetime))
            self._event(db, principal, 'operator_reenrollment' if reset else 'operator_invitation')
        return token

    def start_enrollment(self, invite, username, password, peer):
        self.rate('enrollment-peer:' + peer, 10, 3600)
        username = username.strip().lower()
        if (not re.fullmatch('[a-z0-9][a-z0-9._-]{2,63}', username)
                or not 14 <= len(password) <= 256 or len(password.encode()) > 1024
                or len(set(password)) < 5 or not 32 <= len(invite) <= 128):
            raise IdentityError('invalid_enrollment_details')
        with self.store.transaction() as db:
            row = db.execute('SELECT * FROM human_invites WHERE hash=? AND used=0 AND expires>?',
                             (digest(invite), self.clock())).fetchone()
        if not row or not self.grants(row['principal']):
            raise IdentityError('invalid_enrollment_details')
        encoded = self._hash(password)
        secret, pending = pyotp.random_base32(), secrets.token_urlsafe(32)
        with self.store.transaction() as db:
            if (db.execute('SELECT 1 FROM human_users WHERE username=? OR principal=?', (username, row['principal'])).fetchone()
                    or db.execute('SELECT 1 FROM human_pending WHERE username=? AND expires>?', (username, self.clock())).fetchone()):
                raise IdentityError('invalid_enrollment_details')
            changed = db.execute('UPDATE human_invites SET used=1 WHERE hash=? AND used=0 AND expires>?',
                                 (digest(invite), self.clock())).rowcount
            if changed != 1:
                raise IdentityError('invalid_enrollment_details')
            db.execute('INSERT INTO human_pending VALUES (?,?,?,?,?,?)',
                       (digest(pending), row['principal'], username, encoded, secret, self.clock() + 600))
        return pending

    def pending(self, token):
        with self.store.transaction() as db:
            row = db.execute('SELECT username,otp_secret,expires FROM human_pending WHERE hash=? AND expires>?',
                             (digest(token), self.clock())).fetchone()
        return dict(row) if row else None

    def _step(self, secret, code, previous):
        if not re.fullmatch('[0-9]{6}', code):
            return None
        current = int(self.clock() // 30)
        totp = pyotp.TOTP(secret)
        for step in (current, current-1, current+1):
            if step > previous and secrets.compare_digest(totp.at(step*30), code):
                return step
        return None

    def _new_session(self, db, principal):
        value = secrets.token_urlsafe(32)
        db.execute('INSERT INTO human_sessions(hash,principal,expires,created) VALUES (?,?,?,?)',
                   (digest(value), principal, self.clock() + 8*3600, self.clock()))
        return value

    def finish_enrollment(self, pending, code, peer):
        self.rate('enrollment-confirm:' + peer, 20, 600)
        with self.store.transaction() as db:
            row = db.execute('SELECT * FROM human_pending WHERE hash=? AND expires>?',
                             (digest(pending), self.clock())).fetchone()
            if not row or not self.grants(row['principal']):
                raise IdentityError('enrollment_expired')
            step = self._step(row['otp_secret'], code, -1)
            if step is None:
                raise IdentityError('invalid_authenticator_code')
            db.execute('INSERT INTO human_users(username,principal,password,otp_secret,last_step) VALUES (?,?,?,?,?)',
                       (row['username'], row['principal'], row['password'], row['otp_secret'], step))
            db.execute('DELETE FROM human_pending WHERE hash=?', (digest(pending),))
            recovery = [secrets.token_hex(10) for _ in range(8)]
            for value in recovery:
                db.execute('INSERT INTO human_recovery(hash,principal) VALUES (?,?)', (digest(value), row['principal']))
            session = self._new_session(db, row['principal'])
            self._event(db, row['principal'], 'enrollment_completed')
        return session, recovery

    def login(self, username, password, code, peer):
        username = username.strip().lower()[:64]
        self.rate('login-peer:' + peer, 30, 600)
        self.rate('login-account:' + username, 10, 600)
        if len(password) > 256 or len(code) > 128:
            raise IdentityError('invalid_credentials', 401)
        with self.store.transaction() as db:
            user = db.execute('SELECT * FROM human_users WHERE username=? AND enabled=1', (username,)).fetchone()
        valid = self._hash(password, user['password'] if user else self.dummy)
        if not valid or not user or not self.grants(user['principal']):
            raise IdentityError('invalid_credentials', 401)
        with self.store.transaction() as db:
            current = db.execute('SELECT * FROM human_users WHERE username=? AND enabled=1', (username,)).fetchone()
            if not current or current['password'] != user['password'] or current['principal'] != user['principal']:
                raise IdentityError('invalid_credentials', 401)
            step = self._step(current['otp_secret'], code, current['last_step'])
            recovery = False
            if step is None:
                recovery = db.execute('UPDATE human_recovery SET used=1 WHERE hash=? AND principal=? AND used=0',
                    (digest(code), current['principal'])).rowcount == 1
                if not recovery:
                    raise IdentityError('invalid_credentials', 401)
            else:
                db.execute('UPDATE human_users SET last_step=? WHERE username=?', (step, username))
            session = self._new_session(db, current['principal'])
            self._event(db, current['principal'], 'recovery_login' if recovery else 'mfa_login')
        return session

    def _credential_session(self, value):
        if not isinstance(value, str) or not 32 <= len(value) <= 128:
            return None
        with self.store.transaction() as db:
            row = db.execute('SELECT s.principal,s.created,s.expires,u.username FROM human_sessions s '
                             'JOIN human_users u ON u.principal=s.principal '
                             'WHERE s.hash=? AND s.revoked=0 AND s.expires>? AND u.enabled=1',
                             (digest(value), self.clock())).fetchone()
        return dict(row) if row else None

    def session(self, value):
        row = self._credential_session(value)
        if not row or not self.grants(row['principal']):
            return None
        return row

    def logout(self, value):
        with self.store.transaction() as db:
            db.execute('UPDATE human_sessions SET revoked=1 WHERE hash=?', (digest(value),))

    def _revoke_all(self, db, principal):
        db.execute('UPDATE human_sessions SET revoked=1 WHERE principal=?', (principal,))
        for row in db.execute('SELECT id,data FROM families WHERE revoked=0').fetchall():
            if json.loads(row['data']).get('subject') == principal:
                db.execute('UPDATE families SET revoked=1 WHERE id=?', (row['id'],))

    def revoke_all(self, session):
        authenticated = self._credential_session(session)
        if not authenticated:
            raise IdentityError('authentication_required', 401)
        with self.store.transaction() as db:
            self._revoke_all(db, authenticated['principal'])
            self._event(db, authenticated['principal'], 'all_sessions_and_clients_revoked')

    def connections(self, session):
        authenticated = self.session(session)
        if not authenticated:
            raise IdentityError('authentication_required', 401)
        with self.store.transaction() as db:
            values = []
            for row in db.execute('SELECT id,data,expires FROM families WHERE revoked=0 AND expires>?', (self.clock(),)):
                data = json.loads(row['data'])
                if data.get('subject') == authenticated['principal']:
                    values.append(dict(id=row['id'], client=data['client_id'], scopes=data['scopes'], expires=row['expires']))
        return values
