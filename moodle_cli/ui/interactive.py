from pathlib import Path
from typing import Any, Dict, List
import questionary

from moodle_cli.core.config import Config
from moodle_cli.core.api import MoodleClient, MoodleError
from moodle_cli.core.downloader import sanitize_filename
from moodle_cli.commands.auth import run_auth_setup, run_auth_status, run_auth_reset, show_config
from moodle_cli.commands.courses import get_courses, view_course_contents
from moodle_cli.commands.check import check_updates
from moodle_cli.commands.sync import run_sync, download_file_items
from moodle_cli.core.state import StateManager
from moodle_cli.ui.console import console, print_banner


MENU_STYLE = questionary.Style([
    ("qmark", "fg:#00d7ff bold"),
    ("question", "bold fg:#ffffff"),
    ("answer", "fg:#00ff87 bold"),
    ("pointer", "fg:#00d7ff bold"),
    ("highlighted", "fg:#00d7ff bold"),
    ("selected", "fg:#00ff87 bold"),
    ("instruction", "fg:#808080 italic"),
])


def extract_course_files(course_id: int, course_name: str, contents: List[Dict[str, Any]], download_dir: str) -> List[Dict[str, Any]]:
    files = []
    download_root = Path(download_dir)
    safe_course = sanitize_filename(course_name)

    for sec in contents:
        sec_name = sec.get("name", "General")
        safe_sec = sanitize_filename(sec_name)

        for mod in sec.get("modules", []):
            mod_id = mod.get("id", 0)
            mod_name = mod.get("name", "Module")

            for item in mod.get("contents", []):
                if item.get("type") == "file":
                    fname = sanitize_filename(item.get("filename", "file"))
                    fsize = item.get("filesize", 0)
                    timemod = item.get("timemodified", 0)
                    furl = item.get("fileurl")
                    target_path = download_root / safe_course / safe_sec / fname

                    files.append({
                        "course_id": course_id,
                        "course_name": course_name,
                        "section_name": sec_name,
                        "module_id": mod_id,
                        "module_name": mod_name,
                        "filename": fname,
                        "url": furl,
                        "filesize": fsize,
                        "timemodified": timemod,
                        "path": target_path,
                        "is_downloaded": target_path.is_file(),
                    })
    return files


def format_size(size_bytes: int) -> str:
    if not size_bytes:
        return ""
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes / (1024 * 1024):.1f} MB"


def course_file_manager(config: Config, course_id: int, course_name: str) -> None:
    client = MoodleClient(config)
    try:
        with console.status("[bold cyan]Loading course materials...[/bold cyan]"):
            contents = client.get_course_contents(course_id)
    except MoodleError as e:
        console.print(f"[red]Failed loading contents: {e}[/red]")
        return

    while True:
        files = extract_course_files(course_id, course_name, contents, config.download_dir)
        downloaded_count = sum(1 for f in files if f["is_downloaded"])
        total_count = len(files)

        console.print(f"\n[bold cyan]Course: {course_name}[/bold cyan]")
        console.print(f"[dim]{total_count} files total | {downloaded_count} downloaded | {total_count - downloaded_count} new[/dim]\n")

        action = questionary.select(
            "Course action:",
            choices=[
                questionary.Choice("Select files to download   (multi-select checklist)", value="multi"),
                questionary.Choice("Download a single file      (choose one file)", value="single"),
                questionary.Choice("Download entire course      (sync all course materials)", value="all"),
                questionary.Choice("View course outline tree    (hierarchy of sections and files)", value="tree"),
                questionary.Choice("Back to courses", value="back"),
            ],
            style=MENU_STYLE,
        ).ask()

        if action in (None, "back"):
            break

        if action == "multi":
            if not files:
                console.print("[yellow]No files in this course.[/yellow]")
                continue

            choices = []
            for f in files:
                tag = "[Downloaded]" if f["is_downloaded"] else "[New]       "
                size_str = f" ({format_size(f['filesize'])})" if f["filesize"] else ""
                title = f"{tag} {f['section_name']} / {f['filename']}{size_str}"
                choices.append(questionary.Choice(title=title, value=f))

            selected = questionary.checkbox(
                "Select files (Space to toggle, Enter to download):",
                choices=choices,
                style=MENU_STYLE,
            ).ask()

            if selected:
                download_file_items(config, selected)

        elif action == "single":
            if not files:
                console.print("[yellow]No files in this course.[/yellow]")
                continue

            choices = []
            for f in files:
                tag = "[Downloaded]" if f["is_downloaded"] else "[New]       "
                size_str = f" ({format_size(f['filesize'])})" if f["filesize"] else ""
                title = f"{tag} {f['section_name']} / {f['filename']}{size_str}"
                choices.append(questionary.Choice(title=title, value=f))
            choices.append(questionary.Choice(title="Back", value="back"))

            chosen = questionary.select(
                "Select file to download:",
                choices=choices,
                style=MENU_STYLE,
            ).ask()
            if chosen and chosen != "back":
                download_file_items(config, [chosen])

        elif action == "all":
            run_sync(config, course_filter=[course_id])

        elif action == "tree":
            view_course_contents(config, course_id)


def browse_courses_menu(config: Config) -> None:
    while True:
        try:
            courses = get_courses(config)
        except MoodleError as e:
            console.print(f"[red]Error loading courses: {e}[/red]")
            return

        if not courses:
            console.print("[yellow]No enrolled courses found.[/yellow]")
            return

        choices = [
            questionary.Choice(
                title=f"[{c['id']}] {c.get('shortname', '')} - {c.get('fullname', '')}",
                value=c,
            )
            for c in courses
        ]
        choices.append(questionary.Choice(title="Back to main menu", value="back"))

        chosen = questionary.select(
            "Select course to browse files:",
            choices=choices,
            style=MENU_STYLE,
        ).ask()

        if chosen in (None, "back") or not isinstance(chosen, dict):
            break

        course_file_manager(config, chosen["id"], chosen.get("fullname", f"Course {chosen['id']}"))


def configuration_menu(config: Config) -> None:
    while True:
        action = questionary.select(
            "Configuration options:",
            choices=[
                questionary.Choice("View configuration      (display active portal, user, paths)", value="view"),
                questionary.Choice("Verify connection       (test token against site)", value="test"),
                questionary.Choice("Edit settings           (re-run configuration wizard)", value="edit"),
                questionary.Choice("Reset credentials       (wipe saved configuration)", value="reset"),
                questionary.Choice("Back to main menu", value="back"),
            ],
            style=MENU_STYLE,
        ).ask()

        if action in (None, "back"):
            break

        if action == "view":
            show_config(config)
        elif action == "test":
            run_auth_status(config)
        elif action == "edit":
            run_auth_setup(config)
        elif action == "reset":
            run_auth_reset(config)


def start_interactive_session(config: Config) -> None:
    print_banner(config)

    if not config.is_configured():
        console.print("[yellow]No configuration found.[/yellow]")
        if not run_auth_setup(config):
            return

    while True:
        action = questionary.select(
            "Main Menu:",
            choices=[
                questionary.Choice("Browse courses and files    (explore sections, pick & download files)", value="browse"),
                questionary.Choice("Sync all courses            (download all new and modified materials)", value="sync"),
                questionary.Choice("Check for updates           (quick scan for changes without downloading)", value="check"),
                questionary.Choice("Configuration               (view settings, test connection, or reset)", value="config"),
                questionary.Choice("Clean missing files         (prune deleted local files from sync cache)", value="clean"),
                questionary.Choice("Exit", value="exit"),
            ],
            style=MENU_STYLE,
        ).ask()

        if action in (None, "exit"):
            break

        console.rule()

        if action == "browse":
            browse_courses_menu(config)
        elif action == "sync":
            run_sync(config)
        elif action == "check":
            check_updates(config)
        elif action == "config":
            configuration_menu(config)
        elif action == "clean":
            state = StateManager(config.state_file)
            cleaned = state.clean_missing_files()
            console.print(f"[green]Removed {cleaned} missing file records.[/green]")

        console.rule()
