import logging
import os
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from .rules.parser import MatchCriteria, Rule

logger = logging.getLogger("gumka")


@dataclass
class ScanMatch:
    path: Path
    rule: Rule
    size_bytes: int
    modified_time: datetime


def _parse_duration(s: str) -> timedelta:
    m = re.fullmatch(r"(\d+)([dhw])", s.strip().lower())
    if not m:
        raise ValueError(f"Invalid duration '{s}'  - use e.g. '30d', '2w', '12h'")
    n, unit = int(m.group(1)), m.group(2)
    return {"d": timedelta(days=n), "w": timedelta(weeks=n), "h": timedelta(hours=n)}[unit]


def _parse_size(s: str) -> int:
    m = re.fullmatch(r"(\d+(?:\.\d+)?)\s*(B|KB|MB|GB)", s.strip(), re.IGNORECASE)
    if not m:
        raise ValueError(f"Invalid size '{s}'  - use e.g. '10MB', '500KB'")
    value, unit = float(m.group(1)), m.group(2).upper()
    return int(value * {"B": 1, "KB": 1024, "MB": 1024**2, "GB": 1024**3}[unit])


def _matches(path: Path, criteria: MatchCriteria, now: datetime) -> bool:
    if criteria.type == "file" and not path.is_file():
        return False
    if criteria.type == "directory" and not path.is_dir():
        return False

    if criteria.older_than:
        threshold = _parse_duration(criteria.older_than)
        try:
            mtime = datetime.fromtimestamp(path.stat().st_mtime)
            if now - mtime < threshold:
                return False
        except OSError:
            return False

    if criteria.larger_than:
        min_bytes = _parse_size(criteria.larger_than)
        try:
            if path.stat().st_size < min_bytes:
                return False
        except OSError:
            return False

    return True


def scan(rules: list[Rule], path_override: str | None = None) -> list[ScanMatch]:
    """Scan all rule paths and return matches. path_override replaces every rule's path."""
    matches: list[ScanMatch] = []
    seen: set[Path] = set()
    now = datetime.now()

    for rule in rules:
        root = Path(os.path.expandvars(path_override or rule.path))
        if not root.exists():
            logger.warning(f"Path does not exist, skipping: {root}")
            continue

        raw_pattern = rule.match.pattern
        patterns = raw_pattern if isinstance(raw_pattern, list) else [raw_pattern or "**/*"]
        candidates: list[Path] = []
        for pattern in patterns:
            try:
                candidates.extend(root.glob(pattern))
            except Exception as e:
                logger.warning(f"Glob error on {root!r} with pattern {pattern!r}: {e}")

        for candidate in candidates:
            if candidate in seen:
                continue
            try:
                if _matches(candidate, rule.match, now):
                    stat = candidate.stat()
                    matches.append(
                        ScanMatch(
                            path=candidate,
                            rule=rule,
                            size_bytes=stat.st_size,
                            modified_time=datetime.fromtimestamp(stat.st_mtime),
                        )
                    )
                    seen.add(candidate)
            except OSError as e:
                logger.debug(f"Skipping {candidate}: {e}")

    return matches
