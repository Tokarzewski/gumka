from pathlib import Path
from typing import Annotated

import typer

from ..cleaner import clean
from ..config import setup_logging
from ..scanner import scan
from ._common import console, load_app_rules, load_rules, print_matches, size_str

clean_app = typer.Typer()


@clean_app.callback(invoke_without_command=True)
def cmd_clean(
    rules: Annotated[Path | None, typer.Option("--rules", "-r", help="Rule file to use.")] = None,
    path: Annotated[
        str | None, typer.Option("--path", "-p", help="Override scan path for all rules.")
    ] = None,
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation prompt.")] = False,
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Verbose output.")] = False,
) -> None:
    """Scan and clean files that match the rules."""
    setup_logging(verbose)
    all_rules = load_rules(rules).rules if rules else load_app_rules()
    matches = scan(all_rules, path_override=path)
    print_matches(matches)

    if not matches:
        return

    total = sum(m.size_bytes for m in matches)
    console.print(
        f"\n[bold]{len(matches)}[/bold] item(s) - [bold]{size_str(total)}[/bold] reclaimable"
    )

    if not yes and not typer.confirm("Proceed with cleaning?", default=False):
        console.print("Aborted.")
        return

    results = clean(matches)
    done = sum(1 for r in results if r.success and r.match.rule.action != "log")
    skipped = [r for r in results if r.skipped]
    failed = [r for r in results if not r.success and not r.skipped]

    console.print(f"\n[green]Done:[/green] {done} item(s) cleaned.")
    if skipped:
        console.print(f"[yellow]Skipped (locked / permission denied):[/yellow] {len(skipped)}")
        for r in skipped:
            console.print(f"  • {r.match.path}: {r.skip_reason}")
    if failed:
        console.print(f"[red]Failed:[/red] {len(failed)}")
        for r in failed:
            console.print(f"  • {r.match.path}: {r.error}")
