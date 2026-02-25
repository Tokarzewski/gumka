from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from gumka.cleaner import clean
from gumka.rules.parser import MatchCriteria, Rule
from gumka.scanner import ScanMatch


def _match(path: Path, action: str = "delete") -> ScanMatch:
    return ScanMatch(
        path=path,
        rule=Rule(
            name="test",
            path=str(path.parent),
            match=MatchCriteria(pattern="*"),
            action=action,
        ),
        size_bytes=path.stat().st_size,
        modified_time=datetime.now(),
    )


# ── delete ───────────────────────────────────────────────────────────────────


def test_clean_deletes_file(tmp_path):
    f = tmp_path / "delete_me.txt"
    f.write_text("bye")
    results = clean([_match(f)])
    assert results[0].success
    assert not f.exists()


def test_clean_deletes_directory(tmp_path):
    d = tmp_path / "mydir"
    d.mkdir()
    (d / "inner.txt").write_text("x")
    results = clean([_match(d)])
    assert results[0].success
    assert not d.exists()


# ── log only ─────────────────────────────────────────────────────────────────


def test_clean_log_only_keeps_file(tmp_path):
    f = tmp_path / "keep_me.txt"
    f.write_text("keep")
    results = clean([_match(f, action="log")])
    assert results[0].success
    assert f.exists()


# ── trash ────────────────────────────────────────────────────────────────────


def test_clean_trash_calls_send2trash(tmp_path):
    f = tmp_path / "trash_me.txt"
    f.write_text("x")
    with patch("gumka.cleaner.send2trash") as mock_trash:
        results = clean([_match(f, action="trash")])
    assert results[0].success
    mock_trash.assert_called_once_with(str(f))


# ── error handling ────────────────────────────────────────────────────────────


def test_clean_permission_error_marks_skipped(tmp_path):
    f = tmp_path / "locked.txt"
    f.write_text("x")
    with patch("pathlib.Path.unlink", side_effect=PermissionError("locked")):
        results = clean([_match(f)])
    assert not results[0].success
    assert results[0].skipped
    assert "locked" in results[0].skip_reason.lower() or "permission" in results[0].skip_reason.lower()


# ── batch ────────────────────────────────────────────────────────────────────


def test_clean_returns_result_per_match(tmp_path):
    files = [tmp_path / f"f{i}.tmp" for i in range(3)]
    for f in files:
        f.write_text("x")
    results = clean([_match(f) for f in files])
    assert len(results) == 3
    assert all(r.success for r in results)
