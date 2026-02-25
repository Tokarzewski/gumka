import shutil
import sys

import typer

from ..config import get_resources_dir
from ._common import console, err_console

shell_app = typer.Typer(help="Windows Explorer shell integration.", no_args_is_help=True)

_REG_SHELL_KEY = r"Software\Classes\Directory\shell\AddToGumka"


@shell_app.command(name="install")
def cmd_shell_install() -> None:
    """Register the 'Add to Gumka' right-click context menu entry in Windows Explorer."""

    import winreg

    exe = shutil.which("gumka") or "gumka"
    cmd_value = f'"{exe}" rules quick-add "%1"'
    ico_path = get_resources_dir() / "gumka.ico"

    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, _REG_SHELL_KEY) as key:
        winreg.SetValueEx(key, "", 0, winreg.REG_SZ, "Add to Gumka")
        if ico_path.exists():
            winreg.SetValueEx(key, "Icon", 0, winreg.REG_SZ, str(ico_path))
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, _REG_SHELL_KEY + r"\command") as key:
        winreg.SetValueEx(key, "", 0, winreg.REG_SZ, cmd_value)

    console.print("[green]✓ Context menu entry installed.[/green]")
    console.print(f"  Command: {cmd_value}")
    if ico_path.exists():
        console.print(f"  Icon:    {ico_path}")
    else:
        console.print("[yellow]  Icon not found — run scripts/png_to_ico.py first.[/yellow]")


@shell_app.command(name="uninstall")
def cmd_shell_uninstall() -> None:
    """Remove the 'Add to Gumka' right-click context menu entry from Windows Explorer."""

    import winreg

    try:
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, _REG_SHELL_KEY + r"\command")
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, _REG_SHELL_KEY)
        console.print("[green]✓ Context menu entry removed.[/green]")
    except FileNotFoundError:
        err_console.print("[yellow]Context menu entry not found — already removed?[/yellow]")
        raise typer.Exit(1)
