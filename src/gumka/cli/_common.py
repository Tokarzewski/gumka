from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from ..config import get_app_rule_files
from ..rules.parser import Rule, RuleFile, parse_rule_file
from ..rules.validator import validate_rule_file

console = Console()
err_console = Console(stderr=True)


def size_str(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def load_rules(path: Path) -> RuleFile:
    if not path.exists():
        err_console.print(f"[red]Rule file not found:[/red] {path}")
        raise typer.Exit(1)
    try:
        rf = parse_rule_file(path)
    except Exception as e:
        err_console.print(f"[red]Failed to parse {path.name}:[/red] {e}")
        raise typer.Exit(1)
    errors = validate_rule_file(rf)
    if errors:
        err_console.print(f"[red]Validation errors in {path.name}:[/red]")
        for e in errors:
            err_console.print(f"  • {e}")
        raise typer.Exit(1)
    return rf


def load_app_rules() -> list[Rule]:
    """Load all rule files from the app dir and return a combined rule list."""
    paths = get_app_rule_files()
    if not paths:
        err_console.print("[yellow]No rule files found in app directory.[/yellow]")
        raise typer.Exit(1)
    all_rules = []
    for p in paths:
        rf = load_rules(p)
        all_rules.extend(rf.rules)
    return all_rules


def print_matches(matches) -> None:
    if not matches:
        console.print("[green]No matches found.[/green]")
        return
    t = Table(title=f"{len(matches)} match(es)", show_lines=True)
    t.add_column("Path", style="cyan")
    t.add_column("Size", justify="right")
    t.add_column("Modified")
    t.add_column("Action", style="bold")
    for m in matches:
        t.add_row(
            str(m.path),
            size_str(m.size_bytes),
            m.modified_time.strftime("%Y-%m-%d %H:%M"),
            m.rule.action,
        )
    console.print(t)
