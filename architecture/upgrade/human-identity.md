# Human identity and consent implementation contract

Human enrollment is invitation-only, bound by the protected operator to an
existing enabled graph principal with current read grants. Enrollment creates
login credentials, not graph permissions. Invite values are delivered out of band,
never in URLs, source, graph properties, reports or model context. Initial owner
enrollment is left for the actual person; tests use synthetic identities.

Use Argon2id (64MiB, three iterations, one lane), a long passphrase, and an
authenticator-app TOTP. Store credentials and shared TOTP secrets only in the
private external credential database. Store recovery-code and session digests,
never plaintext reusable sessions. Single-use recovery codes replace the second
factor, not the passphrase. This is MFA, not phishing-resistant WebAuthn.
[Password storage guidance](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html).
[TOTP replay and throttling guidance](https://pyauth.github.io/pyotp/).

Enrollment has a ten-minute browser-bound pending step, verifies the configured
authenticator before enabling login, and shows recovery codes only once. Login
rejects TOTP reuse across concurrent requests. Unknown users follow a dummy hash
check and receive the same error as wrong credentials. Limit expensive hash work
to two concurrent calls, and rate-limit login/enrollment by the actual peer and
account in durable storage. Do not trust arbitrary forwarding headers.

Browser sessions are eight-hour opaque Secure/HttpOnly/__Host- cookies. No token
in browser storage or URL. Rotate on login, expire server-side, revoke on logout,
and offer all-session/all-client revocation. Browser POSTs require exact Origin,
CSRF cookie/form agreement, bounded bodies and duplicate-field rejection. Escape
all client names, project identifiers and callbacks. No external scripts/images,
no framing, no caching and no cross-origin Referer propagation from consent or
secret pages. Use same-origin referrer policy: Chromium form navigation under
no-referrer can send an opaque Origin, which must not be accepted as a shortcut.

Consent shows the actual untrusted client ID/name/callback, available current
projects, and the distinction between read/direction and execution authorization.
No project is preselected. Bind the principal to the authenticated server session,
never a form field. Deny is explicit. Refresh graph grants again before approval.
Disconnect/logout does not imply stopping admitted background work.

Account recovery with a remaining recovery code still requires the passphrase.
Lost passphrase/all factors requires protected operator re-enrollment with old
sessions and OAuth families revoked. No email-only or model-asserted reset shortcut.
This operator path and public abuse controls must be qualified before exposure.
Passkeys and richer delegated teammate administration remain later hardening/UX.

Acceptance includes Playwright enrollment, authenticator confirmation, code replay,
login/logout/reconnect, project consent/deny, expired requests, CSRF, hostile client
metadata, mobile rendering, recovery login and revocation. Use synthetic identities
and a loopback-only fixture clock, never production credentials or owner approval.

## Qualified implementation, source58040af

The invitation/MFA/session layer and server-rendered human pages are implemented.
Exact-revision Playwright CLI acceptance passed on2026-09-06, using real disposable
Neo4j grants and scoped work. It covered browser enrollment, authenticator setup,
single-use recovery display, secure cookies/no browser credential storage, replay
rejection, login/reconnect, untrusted client metadata, explicit selection, forged
project/principal denial, cross-origin CSRF denial, a real separate-origin OAuth
callback, token exchange and an MCP scoped graph read. It also covered used-request
denial, explicit decline, recovery login, all-client/session revocation, recovery
replay and revocation during an injected graph-read outage.

Playwright found actual defects in the initial no-referrer/form-Origin combination
and fieldset sizing with long identifiers at390px. Both were fixed and the complete
journey rerun successfully. The final mobile screenshot was visually inspected.
All140 server-side qualification tests passed, with no skips and one SDK deprecation
warning. New authentication dependencies were installed only in isolated test envs.

This is not yet a production identity deployment. No real owner passphrase, TOTP
secret or recovery code was created. Bootstrap delivery and operator recovery CLI,
service deployment/private datastore backup, trusted reverse-proxy peer handling,
public abuse-boundary qualification, legacy graph/provider credential isolation,
identity audit sensing and actual remote-client trials remain release work. The
current access page supplies all-client revocation; finer per-client administration
and the integrated work board remain UX work. Do not equate this tested identity
surface with the full autonomous system or an elapsed unattended soak.

## Production deployment boundary

Run an independently pinned identity component as a static system user, with a
0700 state directory and root-protected loaded graph credentials. HTTP binds only
127.0.0.1:8788. A reviewed graph DeploymentPolicy names the issuer, resource and
eligible project scopes; the adapter validates a narrow deployment envelope.
Nginx application routes remain closed until legacy credential isolation and
the remote boundary are qualified. Do not install dependencies into Delta's env.

Operator invitation/reset uses a private Unix socket and Linux SO_PEERCRED uid0,
not an HTTP admin tool or a caller-supplied role. It only enrolls an existing graph
principal. The operator client writes invitations to a new0600 file, never stdout
or URLs. Root recovery is distinct from human approval of business actions.
Bootstrap files belong under /opt/seedforth/shared/identity-operator (root0700),
not the shared env directory, whose existing group traversal must be preserved.

Credential backups use SQLite's online backup API, not copying a live database
file. Restore qualification must invalidate sessions, OAuth families, pending
invites and recovery codes and disable restored logins before exposure; otherwise
restoring an old snapshot could resurrect revoked credentials. Keep original
backups private and preserve account/principal mappings for operator re-enrollment.
