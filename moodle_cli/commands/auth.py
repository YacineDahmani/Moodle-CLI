from rich.table import Table
import questionary

from moodle_cli.core.config import Config
from moodle_cli.core.api import MoodleClient, MoodleError
from moodle_cli.ui.console import console


def show_config(config: Config) -> None:
    table = Table(title="Configuration", show_header=True, header_style="bold cyan")
    table.add_column("Setting", style="white")
    table.add_column("Value", style="yellow")

    table.add_row("Moodle URL", config.url or "[dim]Not set[/dim]")
    table.add_row("Username", config.username or "[dim]Not set[/dim]")
    table.add_row("Password", "********" if config.password else "[dim]Not set[/dim]")
    token_display = f"{config.token[:6]}...{config.token[-4:]}" if len(config.token) > 10 else ("[green]Saved[/green]" if config.token else "[dim]None[/dim]")
    table.add_row("Token", token_display)
    table.add_row("Download Directory", config.download_dir)
    table.add_row("State File", config.state_file)

    console.print(table)


def run_auth_status(config: Config) -> bool:
    if not config.url:
        console.print("[red]Moodle URL is not configured.[/red]")
        return False

    client = MoodleClient(config)
    try:
        with console.status("[bold cyan]Connecting to Moodle...[/bold cyan]"):
            info = client.get_site_info()
            console.print("[green]Authentication valid.[/green]")
            console.print(f"Site: [bold]{info.get('sitename', config.url)}[/bold]")
            console.print(f"User: [bold]{info.get('fullname', '')}[/bold] (ID: {info.get('userid', '')})")
            return True
    except MoodleError as e:
        console.print(f"[red]Authentication failed: {e}[/red]")
        return False


def run_auth_reset(config: Config) -> bool:
    confirmed = questionary.confirm(
        "Reset all saved credentials and configuration?",
        default=False,
    ).ask()

    if confirmed:
        deleted = config.reset()
        console.print("[green]Configuration cleared.[/green]")
        return deleted
    return False


def run_auth_setup(config: Config, global_config: bool = True) -> bool:
    console.print("\n[bold]Moodle Configuration[/bold]\n")

    while True:
        default_url = config.url if config.url and "university-site.edu" not in config.url else "https://"
        url = questionary.text(
            "Moodle URL:",
            default=default_url,
            validate=lambda val: True if val.strip().startswith(("http://", "https://")) and len(val.strip()) > 8 else "Enter a valid URL starting with http:// or https://",
        ).ask()
        if not url:
            return False

        default_user = config.username if config.username != "your_username" else ""
        username = questionary.text(
            "Username:",
            default=default_user,
            validate=lambda val: True if len(val.strip()) > 0 else "Username cannot be empty",
        ).ask()
        if not username:
            return False

        password = questionary.password(
            "Password:",
            validate=lambda val: True if len(val) > 0 else "Password cannot be empty",
        ).ask()
        if not password:
            return False

        download_dir = questionary.text(
            "Download directory:",
            default=config.download_dir or "moodle_downloads",
        ).ask()

        config.url = url.strip().rstrip("/")
        config.username = username.strip()
        config.password = password
        config.download_dir = download_dir.strip() or "moodle_downloads"

        client = MoodleClient(config)
        try:
            with console.status("[bold cyan]Verifying credentials...[/bold cyan]"):
                token = client.authenticate(username, password)
                info = client.get_site_info()
            config.token = token
            target = config.save(global_config=global_config)
            console.print(f"\n[green]Authentication verified.[/green]")
            console.print(f"Logged in: [bold]{info.get('fullname', username)}[/bold]")
            console.print(f"Saved: [cyan]{target}[/cyan]\n")
            return True

        except MoodleError as e:
            console.print(f"\n[red]Authentication failed: {e}[/red]\n")
            choice = questionary.select(
                "Action:",
                choices=[
                    "Retry",
                    "Save anyway",
                    "Cancel",
                ],
            ).ask()

            if choice == "Retry":
                continue
            elif choice == "Save anyway":
                target = config.save(global_config=global_config)
                console.print(f"[yellow]Saved without verification: {target}[/yellow]")
                return True
            else:
                return False
