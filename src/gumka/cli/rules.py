import os
import subprocess
import sys
from pathlib import Path
from typing import Annotated

import typer

from ..config import get_app_rule_files, get_context_menu_rules_path, get_rules_dir
from ..rules.merger import merge_rule_files, rule_file_to_toml
from ..rules.parser import parse_rule_file
from ._common import console, err_console, load_rules

rules_app = typer.Typer(help="Manage rule files.", no_args_is_help=True)

_RULE_TEMPLATE = """\
[meta]
name        = "{name}"
description = ""
author      = "{author}"
version     = "1.0.0"

# [[rules]]
# name   = "Example rule"
# path   = "%USERPROFILE%/Downloads"
# match  = {{ pattern = "**/*.tmp", older_than = "30d" }}
# action = "delete"   # delete | trash | log
"""

_DEFAULT_RULE_META = """\
[meta]
name        = "Context menu"
description = "Rules added via the context menu"
author      = ""
version     = "1.0.0"
"""


@rules_app.command(name="new")
def cmd_rules_new(
    name: Annotated[str, typer.Argument(help="Name for the new rule set.")],
    output: Annotated[Path | None, typer.Option("-o", "--output", help="Output file path.")] = None,
) -> None:
    """Create a new rule file from a template."""
    if output is None:
        output = Path(name.lower().replace(" ", "_") + ".toml")
    if output.exists():
        err_console.print(f"[red]File already exists:[/red] {output}")
        raise typer.Exit(1)
    author = os.environ.get("USERNAME", "")
    output.write_text(_RULE_TEMPLATE.format(name=name, author=author), encoding="utf-8")
    console.print(f"[green]Created:[/green] {output}")


@rules_app.command(name="validate")
def cmd_rules_validate(
    file: Annotated[Path, typer.Argument(help="Rule file to validate.")],
) -> None:
    """Validate a rule file and report any errors."""
    rf = load_rules(file)
    console.print(f"[green]✓[/green] {file.name} is valid ({len(rf.rules)} rule(s))")


@rules_app.command(name="list")
def cmd_rules_list() -> None:
    """List all rule files stored in the app data directory."""
    from rich.table import Table

    rules_dir_path = get_rules_dir()
    paths = get_app_rule_files()

    console.print(f"Rules directory: [cyan]{rules_dir_path}[/cyan]\n")

    if not paths:
        console.print("[yellow]No rule files found.[/yellow]")
        return

    t = Table(title=f"{len(paths)} rule file(s)", show_lines=True)
    t.add_column("File", style="cyan")
    t.add_column("Name")
    t.add_column("Rules", justify="right")
    t.add_column("Description")

    for p in paths:
        try:
            rf = parse_rule_file(p)
            rule_count = str(len(rf.rules))
            name = rf.meta.name
            description = rf.meta.description
        except Exception:
            name = "[red]parse error[/red]"
            description = ""
            rule_count = "?"

        t.add_row(p.name, name, rule_count, description)

    console.print(t)


@rules_app.command(name="open")
def cmd_rules_open() -> None:
    """Open the rules folder in the system file explorer."""
    rules_dir_path = get_rules_dir()
    console.print(f"Opening: [cyan]{rules_dir_path}[/cyan]")
    if sys.platform == "win32":
        os.startfile(str(rules_dir_path))
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(rules_dir_path)])
    else:
        subprocess.Popen(["xdg-open", str(rules_dir_path)])


@rules_app.command(name="merge")
def cmd_rules_merge(
    files: Annotated[list[Path], typer.Argument(help="Two or more rule files to merge.")],
    output: Annotated[Path, typer.Option("-o", "--output", help="Output file path.")],
) -> None:
    """Merge two or more rule files into one (smart union)."""
    if len(files) < 2:
        err_console.print("[red]Provide at least two rule files to merge.[/red]")
        raise typer.Exit(1)
    rule_files = [load_rules(f) for f in files]
    merged = merge_rule_files(rule_files)
    output.write_text(rule_file_to_toml(merged), encoding="utf-8")
    console.print(
        f"[green]Merged {len(files)} file(s) → {output}[/green] ({len(merged.rules)} rule(s))"
    )


@rules_app.command(name="quick-add")
def cmd_rules_quick_add(
    path: Annotated[str, typer.Argument(help="Directory to add as a trash rule.")],
) -> None:
    """Append a trash rule for a directory to the default rule file (used by Explorer context menu)."""
    import tomllib

    dir_path = Path(path)
    path_str = dir_path.as_posix()

    dest = get_context_menu_rules_path()
    dest.parent.mkdir(parents=True, exist_ok=True)

    if dest.exists():
        with open(dest, "rb") as f:
            existing = tomllib.load(f)
        if any(r.get("path") == path_str for r in existing.get("rules", [])):
            console.print(f"[yellow]Rule already exists for:[/yellow] {path_str}")
            return

    rule_block = f'\n[[rules]]\npath   = "{path_str}"\naction = "trash"\n'

    if not dest.exists():
        dest.write_text(_DEFAULT_RULE_META + rule_block, encoding="utf-8")
    else:
        with open(dest, "a", encoding="utf-8") as f:
            f.write(rule_block)

    console.print(f"[green]✓ Rule added:[/green] [bold]{path_str}[/bold] → {dest}")


@rules_app.command(name="env")
def cmd_rules_env(
    filter: Annotated[
        str | None,
        typer.Argument(help="Optional substring to filter variable names (case-insensitive)."),
    ] = None,
) -> None:
    """List Windows environment variables for use in rule file paths."""
    from rich.table import Table

    items = sorted(os.environ.items())

    if filter:
        needle = filter.lower()
        items = [(k, v) for k, v in items if needle in k.lower()]

    if not items:
        console.print("[yellow]No matching environment variables found.[/yellow]")
        return

    t = Table(show_lines=False, highlight=True)
    t.add_column("Name", style="cyan", no_wrap=True)
    t.add_column("Value")

    for name, value in items:
        t.add_row(name, value)

    console.print(t)
