import click
from moodle_cli.core.config import Config
from moodle_cli.commands.auth import run_auth_setup, run_auth_status, run_auth_reset, show_config
from moodle_cli.commands.courses import list_courses, view_course_contents
from moodle_cli.commands.check import check_updates
from moodle_cli.commands.sync import run_sync
from moodle_cli.core.state import StateManager
from moodle_cli.ui.console import console
from moodle_cli.ui.interactive import start_interactive_session


@click.group(invoke_without_command=True)
@click.option("--config-file", "-c", type=click.Path(), help="Path to config file.")
@click.pass_context
def cli(ctx: click.Context, config_file: str) -> None:
    """Moodle resource sync and inspection tool."""
    ctx.ensure_object(dict)
    cfg = Config._from_file(config_file) if config_file else Config.load()
    ctx.obj["config"] = cfg

    if ctx.invoked_subcommand is None:
        start_interactive_session(cfg)


@cli.command("sync")
@click.option("--course", "-c", "courses", multiple=True, type=int, help="Course ID(s) to sync.")
@click.option("--dry-run", is_flag=True, help="List files without downloading.")
@click.option("--force", is_flag=True, help="Force redownload of files.")
@click.pass_context
def sync_cmd(ctx: click.Context, courses: tuple, dry_run: bool, force: bool) -> None:
    """Download new and modified course files."""
    cfg: Config = ctx.obj["config"]
    run_sync(cfg, course_filter=list(courses) if courses else None, dry_run=dry_run, force=force)


@cli.command("check")
@click.option("--course", "-c", "courses", multiple=True, type=int, help="Course ID(s) to inspect.")
@click.pass_context
def check_cmd(ctx: click.Context, courses: tuple) -> None:
    """Check for new or modified content."""
    cfg: Config = ctx.obj["config"]
    check_updates(cfg, course_filter=list(courses) if courses else None)


@cli.command("courses")
@click.option("--json", "json_output", is_flag=True, help="Output JSON.")
@click.pass_context
def courses_cmd(ctx: click.Context, json_output: bool) -> None:
    """List enrolled courses."""
    cfg: Config = ctx.obj["config"]
    list_courses(cfg, json_output=json_output)


@cli.command("tree")
@click.argument("course_id", type=int)
@click.pass_context
def tree_cmd(ctx: click.Context, course_id: int) -> None:
    """Display course sections and files as a tree."""
    cfg: Config = ctx.obj["config"]
    view_course_contents(cfg, course_id)


@cli.command("auth")
@click.option("--setup", is_flag=True, help="Configure credentials.")
@click.option("--status", is_flag=True, help="Check connection status.")
@click.option("--reset", is_flag=True, help="Reset saved credentials.")
@click.option("--show", is_flag=True, help="Show current configuration.")
@click.pass_context
def auth_cmd(ctx: click.Context, setup: bool, status: bool, reset: bool, show: bool) -> None:
    """Manage authentication and settings."""
    cfg: Config = ctx.obj["config"]
    if reset:
        run_auth_reset(cfg)
    elif setup:
        run_auth_setup(cfg)
    elif show:
        show_config(cfg)
    else:
        run_auth_status(cfg)


@cli.command("config")
@click.option("--setup", is_flag=True, help="Configure settings.")
@click.option("--reset", is_flag=True, help="Reset settings.")
@click.pass_context
def config_cmd(ctx: click.Context, setup: bool, reset: bool) -> None:
    """Manage configuration."""
    ctx.invoke(auth_cmd, setup=setup, reset=reset, show=not (setup or reset))


@cli.command("clean")
@click.pass_context
def clean_cmd(ctx: click.Context) -> None:
    """Prune missing files from sync state."""
    cfg: Config = ctx.obj["config"]
    state = StateManager(cfg.state_file)
    cleaned = state.clean_missing_files()
    console.print(f"[green]Removed {cleaned} missing file records.[/green]")


@cli.command("ui")
@click.pass_context
def ui_cmd(ctx: click.Context) -> None:
    """Launch interactive menu."""
    cfg: Config = ctx.obj["config"]
    start_interactive_session(cfg)


if __name__ == "__main__":
    cli()
