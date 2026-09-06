# Product repository synchronization runbook

**Status:** Operational policy  
**Last reviewed:** 2026-09-06

This runbook governs product repositories listed in
`registry/repositories.json`. It does not apply to the consolidated platform
release or the Tetrahedron reference repository.

## Authority

- GitHub's declared default branch is the source authority for versioned
  product code.
- A server checkout is a runtime observation, not an authority for source
  code. Its generated state must be captured before cleanup.
- A local checkout is a working copy. Never reset, force-push, or delete local
  work merely to make a hash match.
- Neo4j records project/runtime observations; it does not replace Git history.

## Classification procedure

Run the read-only report first:

```bash
python3 operations/reconcile.py --server root@185.192.96.100 \
  --graph root@185.192.96.100
```

Then classify each difference:

| Observation | Safe action | Required evidence |
|---|---|---|
| Clean local checkout behind GitHub | Fast-forward only | Local SHA equals remote SHA afterward |
| Dirty checkout containing only generated state | Capture inventory, then add/verify ignore boundary | Before/after status and runtime health |
| Dirty checkout containing source edits | Preserve; do not pull or reset | Diff/stat and owner decision |
| Clean checkout diverged from GitHub | Preserve branch; compare ancestry | Merge-base and left/right commit list |
| Server checkout dirty | Treat as runtime state; do not overwrite blindly | Status, diff stat, service state |
| Credential tracked or present in history | Rotate first, then scrub history | Provider rotation confirmation and scan |

## Current classified cases

- **Audioworld:** clean and fast-forward synchronized to GitHub `main`.
- **Flowing Indian local:** source/config work is dirty on a feature branch;
  preserve it. Server differences are generated Delta state plus a small
  runtime log delta.
- **Seedforthing local:** clean but diverged from the automated `master`
  history; preserve the local boundary commit and the remote history until a
  deliberate merge/rebase decision is made. The server is an older, heavily
  generated checkout and must not be reset or pulled blindly.
- **SolveOS:** dirty local checkout and not deployed on `delta2`; preserve.
- **Mycelium/Delta standalone checkouts:** preserve as provenance/upstream;
  the deployed platform release is their consolidated runtime authority.
- **Tetrahedron:** reference-only; do not reintroduce it into active runtime
  or graph authority.

## Generated-state boundary

Runtime files such as logs, inbox/outbox queues, progress, telemetry, nudge
markers, and driver state belong on the server or in the graph-derived
observation layer. They must not be committed as product source. Before
removing tracked generated files, capture the server artifact and confirm the
service can recreate it.

## Credential boundary

Do not print, copy, or pass credentials as command-line arguments. Use the
external server environment contract or a secret manager. The known
Seedforthing Vercel token file was mode-hardened in place and removed from the
current GitHub branch. Because it may exist in history and remains in the old
server checkout, the remaining required action is provider rotation followed
by repository history scrubbing and a secret scan.

The cutover utility is `operations/rotate-seedforthing-vercel-token.sh`. Run it
on the server as root (or as the token-file owner), passing the replacement on
stdin. It validates the replacement against Vercel before installing it with
mode `0600`; it does not print the token or revoke the old one. After a
successful deployment smoke test, revoke the old token from Vercel's account
token settings, then perform the history rewrite and enable secret scanning.

Example; obtain the value through a secure input mechanism, never chat or a
shell argument:

```bash
read -r -s VERCEL_REPLACEMENT
printf '%s\n' "$VERCEL_REPLACEMENT" | \
  ./operations/rotate-seedforthing-vercel-token.sh --stdin
unset VERCEL_REPLACEMENT
```

## Completion condition

A product repository is synchronized only when its canonical branch, local
checkout, and active server release have a recorded relationship, generated
state is outside Git, and no unresolved credential exception remains.
