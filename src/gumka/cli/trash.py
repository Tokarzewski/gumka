import ctypes
import sys
from typing import Annotated

import typer

from ._common import console, err_console, size_str

trash_app = typer.Typer(help="Inspect and manage the Windows Recycle Bin.", no_args_is_help=True)


def _recycle_bin_stats() -> tuple[int, int]:
    """Return (total_bytes, item_count) for the Recycle Bin using SHQueryRecycleBinW."""
    import ctypes.wintypes

    class SHQUERYRBINFO(ctypes.Structure):
        _fields_ = [
            ("cbSize", ctypes.wintypes.DWORD),
            ("i64Size", ctypes.c_int64),
            ("i64NumItems", ctypes.c_int64),
        ]

    info = SHQUERYRBINFO()
    info.cbSize = ctypes.sizeof(SHQUERYRBINFO)
    ctypes.windll.shell32.SHQueryRecycleBinW(None, ctypes.byref(info))
    return info.i64Size, info.i64NumItems


@trash_app.command(name="stats")
def cmd_trash_stats() -> None:
    """Show Recycle Bin item count and total size."""
    if sys.platform != "win32":
        err_console.print("[red]Recycle Bin management is only supported on Windows.[/red]")
        raise typer.Exit(1)

    total_bytes, item_count = _recycle_bin_stats()
    console.print(
        f"Recycle Bin: [bold]{item_count}[/bold] item(s), [bold]{size_str(total_bytes)}[/bold]"
    )


@trash_app.command(name="empty")
def cmd_trash_empty(
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation prompt.")] = False,
) -> None:
    """Empty the Recycle Bin."""
    total_bytes, item_count = _recycle_bin_stats()
    console.print(
        f"Recycle Bin: [bold]{item_count}[/bold] item(s), [bold]{size_str(total_bytes)}[/bold]"
    )

    if item_count == 0:
        console.print("[yellow]Recycle Bin is already empty.[/yellow]")
        return
    if not yes and not typer.confirm("Empty the Recycle Bin?", default=False):
        console.print("Aborted.")
        return
    SHERB_NOCONFIRMATION = 0x00000001
    SHERB_NOPROGRESSUI = 0x00000002
    SHERB_NOSOUND = 0x00000004
    hr = ctypes.windll.shell32.SHEmptyRecycleBinW(
        None, None, SHERB_NOCONFIRMATION | SHERB_NOPROGRESSUI | SHERB_NOSOUND
    )
    if hr == 0:
        console.print("[green]Recycle Bin emptied.[/green]")
    else:
        err_console.print(f"[red]Failed to empty Recycle Bin (HRESULT: {hr:#010x}).[/red]")
        raise typer.Exit(1)
