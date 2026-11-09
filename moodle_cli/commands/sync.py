from datetime import datetime
from typing import List, Optional
from moodle_cli.core.config import Config
from moodle_cli.core.api import MoodleError
from moodle_cli.core.downloader import FileDownloader
from moodle_cli.core.state import StateManager
from moodle_cli.commands.check import inspect_updates
from moodle_cli.ui.console import console, display_sync_summary
from moodle_cli.ui.progress import create_download_progress


def download_file_items(config: Config, items: List[dict]) -> None:
    if not items:
        console.print("[yellow]No files selected.[/yellow]")
        return

    downloader = FileDownloader()
    state = StateManager(config.state_file)
    downloaded = []
    redownloaded = []

    progress = create_download_progress()
    with progress:
        for item in items:
            fname = item["filename"]
            task_id = progress.add_task(
                "download",
                filename=fname[:30],
                total=item.get("filesize") or None,
            )

            def update_progress(chunk_len: int) -> None:
                progress.update(task_id, advance=chunk_len)

            try:
                downloader.download(
                    url=item["url"],
                    token=config.token,
                    dest_path=item["path"],
                    progress_callback=update_progress,
                )
                progress.update(task_id, completed=item.get("filesize") or 100)

                state.record_file(
                    course_id=item["course_id"],
                    module_id=item["module_id"],
                    filename=fname,
                    path=str(item["path"]),
                    timemodified=item.get("timemodified", 0),
                    filesize=item.get("filesize", 0),
                    course_name=item["course_name"],
                    module_name=item["module_name"],
                )
                state.save()
                downloaded.append(fname)

            except Exception as e:
                console.print(f"[red]Failed downloading {fname}: {e}[/red]")

    display_sync_summary(downloaded, redownloaded, 0)
    console.print(f"[green]Saved to:[/green] [cyan]{config.download_dir}[/cyan]")


def run_sync(
    config: Config,
    course_filter: Optional[List[int]] = None,
    dry_run: bool = False,
    force: bool = False,
) -> None:
    try:
        with console.status("[bold cyan]Scanning courses and evaluating diffs...[/bold cyan]"):
            pending, new_mods, synced_count = inspect_updates(config, course_filter)

        if not pending and not force:
            console.print("[green]All courses are up to date.[/green]")
            display_sync_summary([], [], synced_count)
            return

        if dry_run:
            console.print(f"[yellow]Dry-run: {len(pending)} files to download.[/yellow]")
            for p in pending:
                console.print(f"  {p['course_name']} -> {p['filename']} ({p['reason']})")
            return

        console.print(f"[bold cyan]Downloading {len(pending)} files...[/bold cyan]")

        downloader = FileDownloader()
        state = StateManager(config.state_file)
        downloaded = []
        redownloaded = []

        progress = create_download_progress()
        with progress:
            for item in pending:
                fname = item["filename"]
                task_id = progress.add_task(
                    "download",
                    filename=fname[:30],
                    total=item["filesize"] or None,
                )

                def update_progress(chunk_len: int) -> None:
                    progress.update(task_id, advance=chunk_len)

                try:
                    downloader.download(
                        url=item["url"],
                        token=config.token,
                        dest_path=item["path"],
                        progress_callback=update_progress,
                    )
                    progress.update(task_id, completed=item["filesize"] or 100)

                    state.record_file(
                        course_id=item["course_id"],
                        module_id=item["module_id"],
                        filename=fname,
                        path=str(item["path"]),
                        timemodified=item["timemodified"],
                        filesize=item["filesize"],
                        course_name=item["course_name"],
                        module_name=item["module_name"],
                    )
                    state.save()

                    if "redownload" in item["reason"].lower():
                        redownloaded.append(fname)
                    else:
                        downloaded.append(fname)

                except Exception as e:
                    console.print(f"[red]Failed downloading {fname}: {e}[/red]")

        now_iso = datetime.now().isoformat()
        for mod in new_mods:
            state.record_module(mod.get("course_id", 0), mod.get("module_id", 0), now_iso)
        state.save()

        display_sync_summary(downloaded, redownloaded, synced_count)
        console.print(f"[green]Saved to:[/green] [cyan]{config.download_dir}[/cyan]")

    except MoodleError as e:
        console.print(f"[red]Sync failed: {e}[/red]")
