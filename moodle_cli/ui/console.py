from typing import Any, Dict, List, Optional
from rich.console import Console, Group
from rich.table import Table
from rich.tree import Tree
from rich.panel import Panel
from rich.text import Text


console = Console()


def print_banner(config: Optional[Any] = None) -> None:
    banner_raw = (
        "  __  __  ___   ___  ___  _     ___ \n"
        " |  \\/  |/ _ \\ / _ \\|   \\| |   | __|\n"
        " | |\\/| | (_) | (_) | |) | |__ | _| \n"
        " |_|  |_|\\___/ \\___/|___/|____||___|"
    )
    banner_text = Text(banner_raw, style="bold cyan")

    info_grid = Table.grid(padding=(0, 2))
    info_grid.add_column(style="bold white", justify="right")
    info_grid.add_column(style="dim")

    if config and config.is_configured():
        info_grid.add_row("Site:", f"[cyan]{config.url}[/cyan]")
        info_grid.add_row("User:", f"[green]{config.username}[/green]")
        info_grid.add_row("Target:", f"[yellow]{config.download_dir}/[/yellow]")
    else:
        info_grid.add_row("Status:", "[yellow]Not configured (first-run setup required)[/yellow]")

    content = Group(
        Text(""),
        banner_text,
        Text("Course Materials & Document Synchronization", style="dim italic"),
        Text(""),
        info_grid,
        Text(""),
    )

    console.print(
        Panel(
            content,
            subtitle="v1.0.0",
            border_style="cyan",
            padding=(0, 3),
            expand=False,
        )
    )
    console.print()


def display_courses_table(courses: List[Dict[str, Any]], title: str = "Enrolled Courses") -> None:
    if not courses:
        console.print("[yellow]No courses found.[/yellow]")
        return

    table = Table(title=title, show_header=True, header_style="bold magenta")
    table.add_column("ID", style="cyan", width=8, justify="right")
    table.add_column("Short Name", style="green", width=18)
    table.add_column("Full Name", style="white")

    for c in courses:
        table.add_row(
            str(c.get("id", "")),
            str(c.get("shortname", "")),
            str(c.get("fullname", "")),
        )

    console.print(table)


def display_course_tree(course_name: str, sections: List[Dict[str, Any]]) -> None:
    root = Tree(f"[bold cyan]{course_name}[/bold cyan]")

    for sec in sections:
        sec_name = sec.get("name", "General")
        sec_node = root.add(f"[bold yellow]{sec_name}[/bold yellow]")
        modules = sec.get("modules", [])

        if not modules:
            sec_node.add("[dim]Empty[/dim]")
            continue

        for mod in modules:
            mod_name = mod.get("name", "Module")
            mod_type = mod.get("modname", "")
            contents = mod.get("contents", [])

            if contents:
                mod_node = sec_node.add(f"[green][{mod_type}] {mod_name}[/green]")
                for item in contents:
                    if item.get("type") == "file":
                        fname = item.get("filename", "file")
                        fsize = item.get("filesize", 0)
                        size_kb = f"{fsize / 1024:.1f} KB" if fsize else ""
                        size_str = f" [dim]({size_kb})[/dim]" if size_kb else ""
                        mod_node.add(f"[white]{fname}[/white]{size_str}")
                    else:
                        mod_node.add(f"[dim]{item.get('filename', 'item')}[/dim]")
            else:
                sec_node.add(f"[dim][{mod_type}] {mod_name}[/dim]")

    console.print(root)


def display_sync_summary(downloaded: List[str], redownloaded: List[str], skipped: int) -> None:
    table = Table(title="Summary", show_header=True, header_style="bold blue")
    table.add_column("Status", style="cyan")
    table.add_column("Files", justify="right")

    table.add_row("Downloaded", f"[green]{len(downloaded)}[/green]")
    table.add_row("Re-downloaded", f"[yellow]{len(redownloaded)}[/yellow]")
    table.add_row("Up-to-date", f"[dim]{skipped}[/dim]")

    console.print(table)
