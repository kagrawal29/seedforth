## Delta credential verification

Delta's protected server environment has a working GitHub credential with pull,
push, and triage access to the private repository.

Current read-only baseline:

| Location | Revision/state |
|---|---|
| GitHub `main` | `49926b4ebd087936db31f230eccb50e12bf82b3b` |
| Local checkout | feature branch at `e47098255fad6c7d3c06a3036a81b160f77505aa`, dirty |
| Server checkout | `main` at `2d07670e0abdbddf1952969e40440eab3d09c63c`, dirty |

Access is available through Delta. The three-way source/runtime relationship is
divergent and must be reconciled before product work is dispatched. No reset,
force-push, pull, or cleanup was performed.
