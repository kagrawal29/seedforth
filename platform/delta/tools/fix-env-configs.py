"""Fix supervisor configs — read env vars from delta.env and inject into all proj-*.conf files."""
import os
import re
import subprocess

env_vars = {}
with open("/opt/delta/delta.env") as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env_vars[k] = v.strip('"').strip("'")

env_keys = [
    "DEEPSEEK_API_KEY", "OPENROUTER_API_KEY", "RUBE_BEARER_TOKEN",
    "GITHUB_TOKEN", "VERCEL_TOKEN", "UNIPILE_DSN", "UNIPILE_API_KEY",
    "COMPOSIO_API_KEY", "MYCELIUM_TARGET"
]

conf_dir = "/etc/supervisor/conf.d"
for conf_name in os.listdir(conf_dir):
    if not conf_name.startswith("proj-") or not conf_name.endswith(".conf"):
        continue
    conf_path = os.path.join(conf_dir, conf_name)

    with open(conf_path) as f:
        config = f.read()

    env_parts = ['PATH="/usr/local/bin:/usr/bin:/bin"']
    for key in env_keys:
        if key in env_vars and env_vars[key]:
            env_parts.append(f'{key}="{env_vars[key]}"')

    env_str = ",".join(env_parts)
    config = re.sub(r"environment=.*", f"environment={env_str}", config)

    with open(conf_path, "w") as f:
        f.write(config)
    print(f"Fixed: {conf_name}")

subprocess.run(["supervisorctl", "update"], check=True)
subprocess.run(["supervisorctl", "restart", "all"], check=True)
print("Done — all agents restarted with env vars")
