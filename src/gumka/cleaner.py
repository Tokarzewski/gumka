import ctypes
import logging
import shutil
import sys
from dataclasses import dataclass

from send2trash import send2trash

from .scanner import ScanMatch

logger = logging.getLogger("gumka")


@dataclass
class CleanResult:
    match: ScanMatch
    success: bool
    skipped: bool = False
    skip_reason: str = ""
    error: str = ""


def _refresh_explorer() -> None:
    """Flush Windows Explorer's shell cache so it releases stale directory handles."""
    if sys.platform != "win32":
        return
    try:
        SHCNE_ALLEVENTS = 0x7FFFFFFF
        SHCNF_FLUSH = 0x1000
        ctypes.windll.shell32.SHChangeNotify(SHCNE_ALLEVENTS, SHCNF_FLUSH, None, None)
    except Exception:
        pass


def clean(matches: list[ScanMatch]) -> list[CleanResult]:
    results = [_process(m) for m in matches]
    _refresh_explorer()
    return results


def _process(match: ScanMatch) -> CleanResult:
    path = match.path
    action = match.rule.action

    try:
        if action == "delete":
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
            logger.info(f"Deleted: {path}")
        elif action == "trash":
            send2trash(str(path))
            logger.info(f"Moved to Recycle Bin: {path}")
        elif action == "log":
            logger.info(f"Log only: {path}")

        return CleanResult(match=match, success=True)

    except PermissionError as e:
        reason = f"Permission denied or file locked - {e}"
        logger.warning(f"Skipped {path}: {reason}")
        return CleanResult(match=match, success=False, skipped=True, skip_reason=reason)
    except Exception as e:
        msg = str(e)
        logger.error(f"Error processing {path}: {msg}")
        return CleanResult(match=match, success=False, error=msg)
