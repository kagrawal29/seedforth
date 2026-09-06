# Durable OAuth authorization boundary

This slice supplies the authorization provider behind the real human login and
consent surface. It is not permission to publish an unimplemented login route.
The public nginx application gate remains closed until the complete flow passes.

Use the pinned MCP SDK's authorization-code/S256 PKCE, registration, revocation
and metadata handlers. Add strict resource binding at the HTTP token boundary:
the inspected SDK2.1.1 handler parses but does not enforce resource for code and
refresh exchanges. Reject duplicate parameters and malformed verifier/challenge
inputs before forwarding to SDK handlers. No implicit/password/client-credentials
grant or client-supplied principal is accepted.
[MCP authorization](https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization).

External OAuth state belongs in a private SQLite credential store, not Mycelium
task nodes. Store digests of opaque codes/access/refresh values. One-use code
exchange and refresh rotation are transactions, durable across process restart.
Refresh replay revokes its entire family, including newly rotated credentials.
Code replay after successful exchange also revokes its issued family. Access
tokens last ten minutes, refresh families have an absolute thirty-day limit.
Revocation is not dependent on a process-local cache.

Mycelium remains the authority for identities, grants and project state. Selected
project scopes are the intersection of authenticated human consent, requested
OAuth scopes and current graph grants. Issuance, refresh and resource verification
read the graph again; graph failure fails closed. Authenticated names come only
from the trusted login/session layer, never authorization query parameters or
conversation text. Consent does not create business grants or approve work.

First supported clients are public PKCE clients with exact registered HTTPS or
native loopback HTTP callbacks. Public registration is not a trust badge: consent
must display the actual client ID and callback, escape metadata, and require an
explicit project selection. No client metadata URLs are fetched in this slice.
Confidential clients and client-ID metadata documents remain compatibility work;
do not advertise unsupported methods. Bound registration/transaction storage and
enforce HTTP abuse limits before public launch.

Remaining human layer: secure enrollment, durable login credentials/sessions,
CSRF/origin enforcement, explicit consent/deny, account recovery, session and client
revocation, responsive UI and Playwright flows. The internal consent method must
never become a route accepting a caller-supplied principal. Qualify official SDK
client discovery through actual HTTP in addition to provider unit tests.
