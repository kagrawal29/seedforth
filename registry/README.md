# SeedForth Registry

`repositories.json` is the machine-readable inventory of platform and product repositories. It is a declaration, not an automatic synchronization command.

- `platform` repositories are candidates for the unified platform repository.
- `product` repositories remain independent.
- `reference` repositories are retained but excluded from active runtime architecture.
- `observed_server_path` describes the current checkout location.
- `target_server_path` describes the desired post-consolidation location.
- Neither field authorizes moving or deleting anything.

Commands that change a checkout, server deployment, GitHub branch, or graph state must require an explicit execution step outside this manifest.
