import time
from pathlib import Path

import pytest

from gumka.rules.parser import MatchCriteria, Rule
from gumka.scanner import _parse_duration, _parse_size, scan


def _rule(root: Path, pattern: str = "**/*.tmp", action: str = "delete", **match_kwargs) -> Rule:
    return Rule(
        name="test",
        path=str(root),
        match=MatchCriteria(pattern=pattern, **match_kwargs),
        action=action,
    )


# ── helpers ──────────────────────────────────────────────────────────────────


def test_parse_duration_days():
    assert _parse_duration("30d").days == 30


def test_parse_duration_weeks():
    assert _parse_duration("2w").days == 14


def test_parse_size_mb():
    assert _parse_size("10MB") == 10 * 1024**2


def test_parse_size_kb():
    assert _parse_size("512KB") == 512 * 1024


# ── scan ─────────────────────────────────────────────────────────────────────


def test_scan_finds_matching_files(tmp_path):
    (tmp_path / "a.tmp").write_text("x")
    (tmp_path / "b.txt").write_text("x")
    matches = scan([_rule(tmp_path)])
    assert len(matches) == 1
    assert matches[0].path.name == "a.tmp"


def test_scan_no_matches(tmp_path):
    (tmp_path / "a.txt").write_text("x")
    matches = scan([_rule(tmp_path)])
    assert matches == []


def test_scan_skips_nonexistent_path():
    rule = Rule(
        name="test",
        path="C:/NonExistentPathXYZ_12345",
        match=MatchCriteria(pattern="**/*.tmp"),
        action="delete",
    )
    assert scan([rule]) == []


def test_scan_path_override(tmp_path):
    other = tmp_path / "other"
    other.mkdir()
    (other / "c.tmp").write_text("x")
    rule = Rule(
        name="test",
        path="C:/NonExistent",
        match=MatchCriteria(pattern="**/*.tmp"),
        action="delete",
    )
    matches = scan([rule], path_override=str(other))
    assert len(matches) == 1


def test_scan_type_file_filter(tmp_path):
    (tmp_path / "file.tmp").write_text("x")
    subdir = tmp_path / "dir.tmp"
    subdir.mkdir()
    rule = _rule(tmp_path, type="file")
    matches = scan([rule])
    assert all(m.path.is_file() for m in matches)


def test_scan_type_directory_filter(tmp_path):
    (tmp_path / "file.tmp").write_text("x")
    subdir = tmp_path / "dir.tmp"
    subdir.mkdir()
    rule = _rule(tmp_path, type="directory")
    matches = scan([rule])
    assert all(m.path.is_dir() for m in matches)


def test_scan_older_than_filter(tmp_path):
    old_file = tmp_path / "old.tmp"
    old_file.write_text("x")
    new_file = tmp_path / "new.tmp"
    new_file.write_text("x")
    # backdate old_file by 100 days
    old_ts = old_file.stat().st_mtime - 100 * 86400
    import os
    os.utime(old_file, (old_ts, old_ts))
    rule = _rule(tmp_path, older_than="50d")
    matches = scan([rule])
    assert len(matches) == 1
    assert matches[0].path.name == "old.tmp"


def test_scan_no_duplicates(tmp_path):
    (tmp_path / "a.tmp").write_text("x")
    rule = _rule(tmp_path)
    matches = scan([rule, rule])
    assert len(matches) == 1
