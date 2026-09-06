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
