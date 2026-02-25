from pathlib import Path
from typing import Annotated

import typer

from ..config import setup_logging
from ..scanner import scan
from ._common import console, load_app_rules, load_rules, print_matches, size_str

scan_app = typer.Typer()


@scan_app.callback(invoke_without_command=True)
def cmd_scan(
    rules: Annotated[Path | None, typer.Option("--rules", "-r", help="Rule file to use.")] = None,
    path: Annotated[
        str | None, typer.Option("--path", "-p", help="Override scan path for all rules.")
    ] = None,
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Verbose output.")] = False,
) -> None:
    """Preview files that match the rules (no changes are made)."""
    setup_logging(verbose)
    all_rules = load_rules(rules).rules if rules else load_app_rules()
    matches = scan(all_rules, path_override=path)
    print_matches(matches)
    total = sum(m.size_bytes for m in matches)
    console.print(f"\nTotal reclaimable: [bold]{size_str(total)}[/bold]")
