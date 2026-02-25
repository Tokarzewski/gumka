import os
import tomllib
from pathlib import Path
from typing import Annotated

import typer

from ..config import get_rules_dir, get_schedules_path
from ..scheduler import *
from ._common import console, err_console

schedules_app = typer.Typer(help="Manage scheduled jobs.", no_args_is_help=True)

_SCHEDULE_TEMPLATE = """\
# Gumka - schedules.toml
# Each [[schedules]] block registers one recurring job.
#
# [[schedules]]
# rule_file      = "path/to/rules.toml"   # single rule file
# rule_directory = "path/to/rules/"       # or a directory — one task per .toml inside
# time           = "12:20"                # HH:MM — required
# day            = "Monday"               # optional — weekly on this day; omit for daily
"""


@schedules_app.command(name="new")
def cmd_schedule_new(
    output: Annotated[Path | None, typer.Option("-o", "--output", help="Output file path.")] = None,
) -> None:
    """Create a new schedules.toml file."""
    dest = output or get_schedules_path()
    if dest.exists():
        err_console.print(
            f"[red]File already exists:[/red] {dest}. Edit it manually or delete it first."
        )
        raise typer.Exit(1)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(_SCHEDULE_TEMPLATE, encoding="utf-8")
    console.print(f"[green]Created:[/green] {dest}")


@schedules_app.command(name="add")
def cmd_schedule_add(
    at: Annotated[str, typer.Option("--at", help="Time to run, e.g. 12:20.")],
    rule_path: Annotated[str | None, typer.Argument(help="Path to a rule file or directory. Defaults to the app rules directory.")] = None,
    weekly: Annotated[
        str | None,
        typer.Option("--weekly", help="Run weekly on this day (e.g. Monday). Default: daily."),
    ] = None,
) -> None:
    """Register a scheduled job in schedules.toml."""
    try:
        time = parse_time(at)
    except ValueError as e:
        err_console.print(f"[red]Invalid time:[/red] {e}")
        raise typer.Exit(1)

    if weekly and weekly.lower() not in VALID_DAYS:
        err_console.print(
            f"[red]Invalid day:[/red] '{weekly}'. "
            "Use a full day name: Monday, Tuesday, Wednesday, Thursday, Friday, Saturday, Sunday."
        )
        raise typer.Exit(1)

    schedules_path = get_schedules_path()
    schedules_path.parent.mkdir(parents=True, exist_ok=True)
    if not schedules_path.exists():
        schedules_path.write_text(_SCHEDULE_TEMPLATE, encoding="utf-8")

    resolved = Path(rule_path) if rule_path else get_rules_dir()
    is_dir = resolved.is_dir()
    entry_lines = [
        "",
        "[[schedules]]",
        f'rule_directory = "{resolved.as_posix()}"' if is_dir else f'rule_file = "{resolved.as_posix()}"',
        f'time           = "{time}"',
    ]
    if weekly:
        entry_lines.append(f'day            = "{weekly.capitalize()}"')

    with open(schedules_path, "a", encoding="utf-8") as f:
        f.write("\n".join(entry_lines) + "\n")

    frequency = f"weekly on {weekly.capitalize()}" if weekly else "daily"
    kind = "directory" if is_dir else "file"
    console.print(f"[green]Added schedule:[/green] {resolved} ({kind}) @ {time} ({frequency})")
    console.print(f"Saved to: {schedules_path}")
    console.print("Run [bold]gumka schedules install[/bold] to apply to Windows Task Scheduler.")


@schedules_app.command(name="list")
def cmd_schedule_list() -> None:
    """List all scheduled jobs defined in schedules.toml."""
    from rich.table import Table

    schedules_path = get_schedules_path()
    console.print(f"Schedules file: [cyan]{schedules_path}[/cyan]\n")

    if not schedules_path.exists():
        console.print("[yellow]No schedules.toml found.[/yellow]")
        return

    with open(schedules_path, "rb") as f:
        data = tomllib.load(f)

    schedules = data.get("schedules", [])
    if not schedules:
        console.print("[yellow]No schedules defined.[/yellow]")
        return

    installed = get_installed_task_names()

    t = Table(title=f"{len(schedules)} schedule(s)", show_lines=True)
    t.add_column("Source", style="cyan")
    t.add_column("Type")
    t.add_column("Time", justify="center")
    t.add_column("Frequency")
    t.add_column("Active", justify="center")

    for entry in schedules:
        if rule_file := entry.get("rule_file"):
            source = Path(rule_file).name
            kind = "file"
            expected = {f"Gumka - {Path(rule_file).stem}"}
        elif rule_dir := entry.get("rule_directory"):
            source = str(rule_dir)
            kind = "directory"
            expected = {f"Gumka - {rf.stem}" for rf in Path(rule_dir).glob("*.toml")}
        else:
            source = "[red]missing[/red]"
            kind = "—"
            expected = set()

        time = entry.get("time", "[red]missing[/red]")
        day = entry.get("day")
        frequency = f"weekly — {day}" if day else "daily"

        if not expected:
            active = "[red]no[/red]"
        elif expected <= installed:
            active = "[green]yes[/green]"
        elif expected & installed:
            active = "[yellow]partial[/yellow]"
        else:
            active = "[red]no[/red]"

        t.add_row(source, kind, time, frequency, active)

    console.print(t)


@schedules_app.command(name="open")
def cmd_schedule_open() -> None:
    """Open schedules.toml in the default editor."""
    schedules_path = get_schedules_path()
    if not schedules_path.exists():
        err_console.print(
            "[red]schedules.toml not found.[/red] "
            "Run [bold]gumka schedules new[/bold] first."
        )
        raise typer.Exit(1)
    console.print(f"Opening: [cyan]{schedules_path}[/cyan]")
    os.startfile(str(schedules_path))


@schedules_app.command(name="install")
def cmd_schedule_install() -> None:
    """Register each schedule from schedules.toml as a Windows Task Scheduler task."""
    exe = find_exe()
    if not exe.exists():
        err_console.print(f"[red]Could not locate gumka.exe.[/red] Tried PATH and {exe.parent}")
        raise typer.Exit(1)

    schedules_path = get_schedules_path()
    if not schedules_path.exists():
        err_console.print(
            "[red]schedules.toml not found.[/red] "
            "Run [bold]gumka schedules add[/bold] first."
        )
        raise typer.Exit(1)

    with open(schedules_path, "rb") as f:
        data = tomllib.load(f)

    schedules = data.get("schedules", [])
    if not schedules:
        err_console.print(
            "[red]No entries in schedules.toml.[/red] "
            "Run [bold]gumka schedules add[/bold] first."
        )
        raise typer.Exit(1)

    results = install_entries(schedules, exe)

    registered = 0
    for r in results:
        if r.skipped:
            err_console.print(f"[yellow]Skipped '{r.task_name}':[/yellow] {r.message}")
        elif r.success:
            console.print(f"[green]Registered:[/green] '{r.task_name}' @ {r.time} ({r.frequency})")
            registered += 1
        else:
            err_console.print(f"[red]Failed '{r.task_name}':[/red] {r.message}")

    console.print(f"\n[green]{registered}[/green] task(s) installed.")


@schedules_app.command(name="uninstall")
def cmd_schedule_uninstall() -> None:
    """Remove all gumka Windows Task Scheduler tasks."""
    if not tasks_exist():
        err_console.print("[yellow]No gumka tasks found in Task Scheduler.[/yellow]")
        raise typer.Exit(0)

    ok, error = remove_all_tasks()
    if not ok:
        if not is_admin() and "access is denied" in error.lower():
            err_console.print("[yellow]Administrator privileges are required to remove tasks.[/yellow]")
            if typer.confirm("Re-run as Administrator?", default=True):
                relaunch_as_admin(["schedules", "uninstall"])
            raise typer.Exit(0)
        err_console.print(f"[red]Failed to remove tasks:[/red]\n{error}")
        raise typer.Exit(1)

    console.print("[green]Uninstalled:[/green] All gumka tasks removed from Task Scheduler.")
