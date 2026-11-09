from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from moodle_cli.core.config import Config
from moodle_cli.core.api import MoodleClient, MoodleError
from moodle_cli.core.state import StateManager
from moodle_cli.core.downloader import sanitize_filename
from moodle_cli.ui.console import console
from rich.table import Table


def inspect_updates(
    config: Config,
    course_filter: Optional[List[int]] = None,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], int]:
    client = MoodleClient(config)
    state = StateManager(config.state_file)
    state.clean_missing_files()

    courses = client.get_courses()
    if course_filter:
        courses = [c for c in courses if c.get("id") in course_filter]

    pending_downloads = []
    new_modules = []
    synced_count = 0
    download_root = Path(config.download_dir)

    for course in courses:
        course_id = course["id"]
        course_name = course.get("fullname", f"Course_{course_id}")
        safe_course = sanitize_filename(course_name)

        contents = client.get_course_contents(course_id)

        for sec in contents:
            sec_name = sec.get("name", "General")
            safe_sec = sanitize_filename(sec_name)

            for mod in sec.get("modules", []):
                mod_id = mod["id"]
                mod_name = mod.get("name", "Module")
                mod_type = mod.get("modname", "")

                if not state.is_module_seen(course_id, mod_id):
                    new_modules.append({
                        "course": course_name,
                        "section": sec_name,
                        "name": mod_name,
                        "type": mod_type,
                    })

                for content in mod.get("contents", []):
                    if content.get("type") != "file":
                        continue

                    fname = sanitize_filename(content.get("filename", "file"))
                    furl = content.get("fileurl")
                    fsize = content.get("filesize", 0)
                    timemodified = content.get("timemodified", 0)

                    target_path = download_root / safe_course / safe_sec / fname
                    record = state.get_file_record(course_id, mod_id, fname)

                    file_on_disk = target_path.is_file()
                    needs_download = False
                    reason = ""

                    if not record:
                        needs_download = True
                        reason = "New file"
                    elif not file_on_disk:
                        needs_download = True
                        reason = "Deleted locally"
                    elif timemodified and record.get("timemodified", 0) < timemodified:
                        needs_download = True
                        reason = "Updated on site"
                    elif fsize and record.get("filesize", 0) != fsize:
                        needs_download = True
                        reason = "Size mismatch"

                    if needs_download:
                        pending_downloads.append({
                            "course_id": course_id,
                            "module_id": mod_id,
                            "course_name": course_name,
                            "module_name": mod_name,
                            "filename": fname,
                            "url": furl,
                            "path": target_path,
                            "filesize": fsize,
                            "timemodified": timemodified,
                            "reason": reason,
                        })
                    else:
                        synced_count += 1

    return pending_downloads, new_modules, synced_count


def check_updates(config: Config, course_filter: Optional[List[int]] = None) -> None:
    try:
        with console.status("[bold cyan]Checking for updates...[/bold cyan]"):
            pending, new_mods, synced = inspect_updates(config, course_filter)

        if not pending and not new_mods:
            console.print("[green]All courses are up to date.[/green]")
            console.print(f"[dim]{synced} files verified.[/dim]")
            return

        if pending:
            table = Table(title=f"Pending Downloads ({len(pending)})", header_style="bold yellow")
            table.add_column("Course", style="cyan")
            table.add_column("File", style="white")
            table.add_column("Reason", style="green")

            for item in pending:
                table.add_row(item["course_name"], item["filename"], item["reason"])

            console.print(table)

        if new_mods:
            table = Table(title=f"New Items ({len(new_mods)})", header_style="bold magenta")
            table.add_column("Course", style="cyan")
            table.add_column("Section", style="white")
            table.add_column("Name", style="yellow")
            table.add_column("Type", style="dim")

            for mod in new_mods:
                table.add_row(mod["course"], mod["section"], mod["name"], mod["type"])

            console.print(table)

    except MoodleError as e:
        console.print(f"[red]Check failed: {e}[/red]")
