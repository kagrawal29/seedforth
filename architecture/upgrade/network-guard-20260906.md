# Internal-service ingress guard

Deployed 2026-09-06 on delta2. Policy: network-policy-internal-services-v1.
Security release: afcc87be9b899b66b874d6410899401aaa429dc1.

## Verified change

Before installation, independent TCP probes from the operator workstation connected
to 185.192.96.100 ports 7474, 7687 and 6083. UFW was active but explicitly allowed
these ports. Docker's DOCKER-USER chains were empty and Neo4j published to all
IPv4/IPv6 addresses. Binding evidence alone was not used to infer reachability.

After installation, the same external IPv4 probes received ConnectionRefusedError
on all three ports, while SSH port 22 still connected. Authenticated SSH forwarding
to Neo4j HTTP returned 200. Local TCP connections to all three ports still work.
Production graph checks preserve all 47 projects and all ControlScope holds.
Docker, Delta, WhatsApp, control and broker services remain active; none restarted.

The graph owns approved NetworkPolicy fields. The deployment adapter validates a
narrow safety envelope, then projects that policy into root-private
/opt/seedforth/shared/security/network-guard.json for offline kernel enforcement.
Projection SHA-256: d26fed0c91e81222dfeb8341049d07cd0206322fb7848b2106802b42dda07e8f.
Policy cannot select SSH, arbitrary ports/interfaces or executable commands.

Both address families reject external eth0 TCP ingress to the three ports at
INPUT and DOCKER-USER. Forwarded packets match original direction/destination port
after DNAT, preserving container-originated replies. This placement follows
[Docker's firewall contract](https://docs.docker.com/engine/network/firewall-iptables/).
No shared chains, policies or UFW rules were flushed or replaced.

## Persistence and recovery

seedforth-network-guard.service reads the protected projection without graph/model
credentials. It is required before Docker and part of Docker's service lifecycle.
The effective Docker unit dependency was inspected after installation. The security
component has its own /opt/seedforth/security-current symlink; main/control/worker
releases were not changed. There is no ExecStop that removes protection.

Reapplication was verified idempotent: one INPUT rule and three DOCKER-USER rules
per address family. Do not casually stop/restart the guard unit, since Docker
requires it. Its bounded command can reapply/check rules without stopping services:

```sh
sudo /usr/bin/python3 /opt/seedforth/security-current/operations/network-guard.py
```

Before-rule snapshots are root-private at:
/opt/seedforth/shared/backups/network-guard-6f6ca18f3d164573b24e72b9cd6049e6/.
Do not blindly restore whole snapshots over changed Docker/UFW state. Any rollback
must identify only these exact tagged rules and explicitly accept renewed exposure.
No firewall rollback was needed or performed.

Until authenticated remote interfaces land, graph administration uses SSH tunnels,
not direct public Bolt/HTTP. Example for an authorized SSH operator:

```sh
ssh -N -L 17474:127.0.0.1:7474 -L 17687:127.0.0.1:7687 root@185.192.96.100
```

## Qualification and honest limits

The immutable release passed 116 tests in 18.65s. JUnit SHA-256:
8f85bd70062354fe9a7750eb944cd265da11211bfdd35ee7c36f1b09e85ec33f.
Real disposable Linux namespaces test both IP families, INPUT and Docker-style
7474→17474 DNAT, public denial, private/loopback access, SSH/messaging-port
preservation and idempotent reapplication. A hardened systemd service in its own
private network namespace separately verified the actual capability restrictions.
Fixtures initially exposed namespace creation and IPv6 neighbor-readiness issues;
after fixes, the isolated journey passed three consecutive runs and the full suite.
All created namespaces/listener processes were removed afterward.

External IPv6 reachability has not been independently probed from another network;
IPv6 evidence is the real namespace journey plus production kernel-rule readback.
Full VM reboot, Docker restart and UFW reload drills remain unperformed. Docker
port bindings and old UFW allow entries remain broad beneath this guard. Moving
bindings to loopback and testing all reload/recovery paths remain hardening work.
The guard covers one verified uplink and three TCP ports, not all possible ingress,
local untrusted users, leaked provider credentials or legacy graph writers.

### Retained noVNC application issue

Both direct localhost and SSH-tunneled HTTP requests to the retained noVNC endpoint
failed after TCP connection. Its configured /usr/share/novnc web directory does
not exist. This was not an HTTP baseline tested before installation, so its prior
working state is not established. No browser service or configuration was changed
by the guard. Investigate the effective process/configuration before repair; do
not claim the browser UI works merely because a service/port is active.

This is an ingress-security milestone, not completion of scoped remote MCP, browser
identity/credential isolation, legacy writer fencing or unattended readiness.
