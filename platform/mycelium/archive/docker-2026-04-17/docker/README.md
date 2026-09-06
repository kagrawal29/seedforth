# Maverick Meta Intelligence System — Docker Container

Runs the automated intelligence cycle (synthesis, feedback, distribution) on a cron schedule inside a container. The container clones the repo on startup and agents commit/push changes, so state persists beyond restarts.

## Prerequisites

- Docker installed
- A `.env` file with the required API keys (see `.env.example`)

## Build

```bash
cd /path/to/maverick-meta
docker build -t maverick-meta -f docker/Dockerfile docker/
```

## Run

### Test mode (sandboxed — no pushes to GitHub)
```bash
docker run -d \
  --name maverick-meta \
  --env-file docker/.env \
  -e MODE=test \
  --restart unless-stopped \
  maverick-meta
```

### Production mode (full pipeline with distribution)
```bash
docker run -d \
  --name maverick-meta \
  --env-file docker/.env \
  -e MODE=production \
  --restart unless-stopped \
  maverick-meta
```

## Set File Permissions

After cloning or pulling, ensure the scripts are executable:

```bash
chmod +x docker/entrypoint.sh docker/healthcheck.sh
```

The Dockerfile handles this inside the image, but if you run the scripts locally you will need to set permissions manually.

## Monitor

### Health check

```bash
# Full status report
docker exec maverick-meta /healthcheck.sh

# Quick pass/fail (used by Docker HEALTHCHECK)
docker exec maverick-meta /healthcheck.sh --quiet && echo OK || echo FAILING
```

### Logs

```bash
# Follow cron output
docker logs -f maverick-meta

# Or read the log file directly
docker exec maverick-meta tail -50 /var/log/cron.log
```

### Run a job manually

```bash
# Trigger synthesis now
docker exec maverick-meta /workspace/bin/run-job-wrapper.sh synthesis

# Trigger full cycle
docker exec maverick-meta /workspace/bin/run-job-wrapper.sh full-cycle
```

## Cron Schedule

All times in UTC. IST = UTC + 5:30.

| Job | UTC | IST | Frequency |
|-----|-----|-----|-----------|
| Synthesis | 04:30, 07:30, 10:30, 13:30, 16:30 | 10:00, 13:00, 16:00, 19:00, 22:00 | Every 3h during work hours |
| Entry feedback | 16:45 | 22:15 | Daily |
| Skill feedback | 16:55 | 22:25 | Daily (self-skips if <2 days) |

## Architecture

```
Container starts
  -> entrypoint.sh validates env vars
  -> Clones maverick-meta repo (or pulls if already present)
  -> Writes run-job.sh and wrapper (for cron env)
  -> Exports env vars for cron subprocess
  -> Starts cron daemon
  -> Tails /var/log/cron.log (keeps container alive)

Each cron trigger:
  -> run-job-wrapper.sh sources env vars
  -> run-job.sh pulls latest repo state
  -> Runs the appropriate Python agent
  -> Records success/failure timestamp in /workspace/status/
  -> Agents commit and push changes to the repo
```

## Troubleshooting

**Container exits immediately:** Check env vars are set. Run `docker logs maverick-meta` to see which variable is missing.

**Jobs not running:** Exec into the container and check `crontab -l`. Verify cron is running with `pgrep cron`.

**Agent failures:** Check `/var/log/cron.log` for Python tracebacks. Common causes: expired API keys, rate limits, git push conflicts.

**Git push fails:** The bot user needs write access to the Qubit-Capital/maverick-meta repo. Verify the GH_TOKEN has the `repo` scope.
