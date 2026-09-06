# Remote TLS deployment contract

The first public ingress is an IP-address HTTPS endpoint on 185.192.96.100.
It must expose no graph, control API, credential bootstrap, agent process or
conversation until the real login/consent boundary is qualified. Initially all
HTTPS application paths return 503. HTTP serves only ACME challenge tokens.

Let's Encrypt supports IP certificates using its shortlived profile. Certbot
5.4 supports webroot validation. These certificates require frequent automatic
renewal, a tested reload hook, and certificate expiry sensing; obtaining one is
not sufficient for unattended qualification.
[Official instructions](https://letsencrypt.org/2026/03/11/shorter-certs-certbot).

Use a separate Python environment under shared/certbot-venv: the installed system
Certbot 2.9 fails importing OpenSSL and must not be used or repaired by changing
the agents' Python packages. Staging and production accounts, certificates and
logs have separate directories. No private key or account key enters the repo,
graph, browser tests or command output. The graph stores deployment intent and
public certificate evidence, not secret material.

Deployment order: staging standalone challenge on otherwise unused port80,
production issuance, install source-controlled nginx ingress, nginx syntax check,
reload (not restart), narrow TCP443 firewall allowance, external trust/path tests,
webroot renewal dry run including mandatory validation/reload, enable the six-hour
renewal timer. Systemd tracks nginx validation and reload as ExecStartPost steps:
Certbot itself can exit zero despite a failed deploy hook. Validation requires
write access to the existing /run/nginx.pid, not the whole runtime directory.
Keep the internal-service network guard and all existing services intact.

The webroot exposes only exact ACME challenge paths, never directory listings.
HTTPS does not proxy any service yet. Disable access logs to avoid later logging
authorization codes or URL tokens. TLS1.2/1.3 only, no session tickets, no caching
of application responses, no cross-origin access, no embedding or content sniffing.
Host headers other than the intended IP are rejected. Unknown paths stay closed.

Rollback removes only the newly introduced ingress after nginx validation and
reload, disables its renewal timer, and removes only its labeled443 allowance.
Retain certificates and logs privately for diagnosis. Do not restore whole-system
firewall snapshots or touch graph/browser protection. TLS readiness is separate
from OAuth, useful autonomy, desktop/mobile compatibility, and elapsed soak.
