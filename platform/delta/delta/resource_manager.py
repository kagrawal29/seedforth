"""Resource manager -- hibernates idle projects to save RAM.

Any project idle for 10+ minutes with no pending followups or active/recurring
tasks gets hibernated. State is saved to git so the agent has full context
when the user returns.
"""

import logging
from datetime import datetime, timezone

from delta.provisioner import hibernate

logger = logging.getLogger(__name__)


async def resource_manager_loop(client, registry, bridges,
                                check_interval: int = 60,
                                idle_timeout_minutes: int = 10):
    """Async background loop that hibernates idle projects.

    Runs every check_interval seconds. For each active project:
    - Syncs bridge.last_activity to registry (persists across restarts)
    - If idle and no pending work, hibernates it
    """
    await client.wait_until_ready()

    while not client.is_closed():
        try:
            for name in list(registry.list_projects()):
                info = registry.get(name)
                if not info or info.status != "active":
                    continue

                bridge = bridges.get(name)
                if not bridge:
                    continue

                # Sync last_activity to registry each iteration
                registry.update(
                    name,
                    last_activity=bridge.last_activity.isoformat(),
                )

                # Check if idle and no pending work
                if bridge.is_idle(idle_timeout_minutes) and not bridge.has_pending_work():
                    logger.info(
                        f"Hibernating {name}: idle for {idle_timeout_minutes}+ min, "
                        f"no pending work"
                    )
                    hibernate(name, registry, bridges)

        except Exception as e:
            logger.warning(f"Resource manager error: {e}")

        import asyncio
        await asyncio.sleep(check_interval)
