# Check Existing State Before Running Scripts

Before running any initialization, setup, or data processing script, check if output files or state files already exist. Resume from existing state rather than starting fresh.

Claude's default behavior is to begin every task from scratch. When resuming interrupted work — restarting a batch process, re-running a setup script, or continuing data collection — this causes completed work to be redone. Check for existing output first, and only run steps that haven't completed yet.

This applies to: init scripts, data pipelines, batch processors, setup wizards, migration scripts, and any multi-step process that writes files.
