# Flowing Indian GitHub access investigation

Date: 2026-09-08

The local Flowing Indian checkout is configured with this remote:

`https://github.com/kartiksahu/flowing-indian-website.git`

The available GitHub CLI identity is `kagrawal29`. The following read-only
operations returned repository-not-found:

- `gh api repos/kartiksahu/flowing-indian-website`
- `gh repo view kartiksahu/flowing-indian-website`
- authenticated `git ls-remote origin`

The local checkout is therefore not currently verifiable against a GitHub
canonical repository through this CLI identity. The likely resolutions are:

1. Confirm the repository owner or URL if it has moved or been renamed.
2. Grant `kagrawal29` access to the private repository.
3. Authenticate the GitHub account that owns the access with `gh auth login` or
   `gh auth switch`.

## Delta credential verification

Delta's protected server environment has a working GitHub credential with pull,
push, and triage access to the private repository. The current read-only
baseline is:

| Location | Revision/state |
|---|---|
| GitHub `main` | `49926b4ebd087936db31f230eccb50e12bf82b3b` |
| Local checkout | feature branch at `e47098255fad6c7d3c06a3036a81b160f77505aa`, dirty |
| Server checkout | `main` at `2d07670e0abdbddf1952969e40440eab3d09c63c`, dirty |

Access is therefore available through Delta, but the three-way source and
runtime relationship is divergent and must be reconciled before product work
is dispatched. No reset, force-push, pull, or cleanup was performed.
