# Maverick Meta Intelligence System — Automated Cycle Runner
# Multi-stage build for a lean production image

# Stage 1: Build dependencies
FROM python:3.12-slim AS builder

RUN pip install --no-cache-dir \
    claude_agent_sdk \
    pyyaml \
    requests \
    falkordb \
    redis

# Stage 2: Runtime
FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    cron \
    curl \
    jq \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Install gh CLI
RUN curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
      -o /usr/share/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
      > /etc/apt/sources.list.d/github-cli.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends gh \
    && rm -rf /var/lib/apt/lists/*

# Install Claude Code CLI (required by Agent SDK — spawns claude as subprocess)
RUN curl -fsSL https://claude.ai/install.sh | bash \
    && ln -sf /root/.claude/local/bin/claude /usr/local/bin/claude

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages

# Create non-root user (Agent SDK refuses bypassPermissions as root)
RUN useradd -m -s /bin/bash maverick

# Set up working directory
WORKDIR /workspace
RUN chown maverick:maverick /workspace

# Copy cron schedule and scripts
COPY crontab /etc/cron.d/maverick-cron
RUN chmod 0644 /etc/cron.d/maverick-cron \
    && crontab /etc/cron.d/maverick-cron \
    && touch /var/log/cron.log

COPY entrypoint.sh /entrypoint.sh
COPY healthcheck.sh /healthcheck.sh
RUN chmod +x /entrypoint.sh /healthcheck.sh

HEALTHCHECK --interval=5m --timeout=10s --retries=2 \
    CMD /healthcheck.sh --quiet

ENTRYPOINT ["/entrypoint.sh"]
