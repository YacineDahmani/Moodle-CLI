#!/usr/bin/env python3
"""Legacy entrypoint for backward compatibility. Delegates to moodle_cli."""
import sys
from moodle_cli.core.config import Config
from moodle_cli.commands.sync import run_sync
from moodle_cli.ui.console import console

if __name__ == "__main__":
    console.print("[dim]Notice: moodle-scraper.py is maintained for compatibility. Consider using 'python moodle.py' or 'moodle sync'.[/dim]")
    config = Config.load()
    if not config.is_configured():
        console.print("[red]Error: Credentials or URL not configured in config.py or ~/.config/moodle-cli/config.json[/red]")
        sys.exit(1)
    run_sync(config)
