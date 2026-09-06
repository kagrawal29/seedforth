# Maverick Local Development Stack

This directory contains the Docker Compose configuration for running a complete Maverick graph stack locally on your laptop — Neo4j 5.22 with APOC, Ollama embeddings, and an embedding proxy service. All you need is Docker Desktop (macOS, Windows, or Linux).

## Quick Start

1. Copy `.env.example` to `.env` and adjust the `MAVERICK_LOCAL_PASSWORD` if desired.
2. Run `docker compose up -d` from this directory.
3. Wait for all services to become healthy (~30-60 seconds for first-time Ollama model pull).
4. Access the Neo4j Browser at `http://localhost:7474` (auth: `neo4j` / `localtest12`).
5. Test connectivity: `curl http://localhost:7701/health` should return `{"status":"ok","ollama":"up","model":"nomic-embed-text"}`.

## Services

| Service | Port | Purpose | Health Check |
|---------|------|---------|--------------|
| `neo4j` | 7687 (bolt), 7474 (http) | Local knowledge graph | `cypher-shell ... RETURN 1` |
| `ollama` | 11434 | Embedding model server | HTTP API `/api/tags` |
| `embed-proxy` | 7701 | Side-channel embedding proxy (read-only HTTP wrapper around Ollama) | HTTP GET `/health` |

## Volumes

- `maverick_local_neo4j_data`: Persists graph data between restarts.
- `maverick_local_neo4j_logs`: Neo4j logs for debugging.
- `maverick_local_ollama`: Persists downloaded models (nomic-embed-text ~274 MB).

## Stopping & Cleanup

- Stop services: `docker compose down`
- Stop and remove data: `docker compose down -v`
- Check status: `docker compose ps`

## Notes

- **Cross-platform**: Works identically on macOS (arm64 and amd64), Windows (Docker Desktop, no WSL required), and Linux.
- **First run**: The first `docker compose up` will pull the Neo4j image (~1 GB) and the nomic-embed-text model (~274 MB). Subsequent runs start in seconds.
- **No external dependencies**: All services run in containers. No need to install Java, Neo4j, Ollama, or Python locally.
- **Defaults**: Neo4j password is `localtest12` (development only; change in production or sensitive environments).

## Troubleshooting

- **Neo4j won't start**: Check Docker Desktop is running and has sufficient disk space (5 GB recommended).
- **Ollama model pull fails**: Ensure internet connectivity; the model is ~274 MB.
- **Port conflicts**: If 7687, 7474, 11434, or 7701 are already in use, edit `.env` or `docker-compose.yml` to use different ports.
- **Health check timeouts**: The first health check may take longer as Neo4j initializes. Retries are configured; wait ~30s.

## Next Steps

Once services are healthy:
- `maverick --target maverick-local shell "MATCH (n) RETURN count(n)"` to query your local graph.
- `maverick fork maverick-dev` to copy the team's shared knowledge graph into your local (after you've run `maverick bootstrap` once).
- Edit `.cypher` files and test locally before creating a PR.
