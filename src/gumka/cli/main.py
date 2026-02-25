import typer

from .clean import clean_app
from .rules import rules_app
from .scan import scan_app
from .schedules import schedules_app
from .shell import shell_app
from .trash import trash_app

app = typer.Typer(name="gumka", help="Gumka - rubbery disk cleaner.", no_args_is_help=True)
app.add_typer(scan_app, name="scan")
app.add_typer(clean_app, name="clean")
app.add_typer(rules_app, name="rules")
app.add_typer(schedules_app, name="schedules")
app.add_typer(shell_app, name="shell")
app.add_typer(trash_app, name="trash")
