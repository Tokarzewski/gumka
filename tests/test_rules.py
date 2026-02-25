from pathlib import Path

import pytest

from gumka.rules.merger import merge_rule_files, rule_file_to_toml
from gumka.rules.parser import MatchCriteria, Rule, RuleFile, RuleMeta, parse_rule_file
from gumka.rules.validator import validate_rule_file

_VALID_TOML = """\
[meta]
name        = "Test Rules"
description = "Test"
author      = "Test"
version     = "1.0.0"

[[rules]]
name   = "Temp files"
path   = "C:/Temp"
match  = { pattern = "**/*.tmp" }
action = "delete"
"""


def _write(tmp_path: Path, content: str) -> Path:
    p = tmp_path / "rules.toml"
    p.write_text(content, encoding="utf-8")
    return p


# ── parser ───────────────────────────────────────────────────────────────────


def test_parse_valid_rule_file(tmp_path):
    rf = parse_rule_file(_write(tmp_path, _VALID_TOML))
    assert rf.meta.name == "Test Rules"
    assert len(rf.rules) == 1
    assert rf.rules[0].name == "Temp files"
    assert rf.rules[0].action == "delete"
    assert rf.rules[0].match.pattern == "**/*.tmp"


def test_parse_defaults_action_to_log(tmp_path):
    toml = "[meta]\nname = 'X'\n[[rules]]\nname = 'R'\npath = 'C:/'\nmatch = {pattern = '*'}\n"
    rf = parse_rule_file(_write(tmp_path, toml))
    assert rf.rules[0].action == "log"


# ── validator ────────────────────────────────────────────────────────────────


def test_validate_valid_file(tmp_path):
    rf = parse_rule_file(_write(tmp_path, _VALID_TOML))
    assert validate_rule_file(rf) == []


def test_validate_missing_path(tmp_path):
    toml = "[[rules]]\nname = 'R'\npath = ''\nmatch = {pattern = '*'}\naction = 'delete'\n"
    rf = parse_rule_file(_write(tmp_path, toml))
    errors = validate_rule_file(rf)
    assert any("path" in e for e in errors)


def test_validate_invalid_action(tmp_path):
    toml = "[[rules]]\nname='R'\npath='C:/'\nmatch={pattern='*'}\naction='nuke'\n"
    rf = parse_rule_file(_write(tmp_path, toml))
    errors = validate_rule_file(rf)
    assert any("action" in e for e in errors)


def test_validate_empty_match_is_valid(tmp_path):
    toml = "[[rules]]\nname='R'\npath='C:/'\nmatch={}\naction='delete'\n"
    rf = parse_rule_file(_write(tmp_path, toml))
    errors = validate_rule_file(rf)
    assert errors == []


# ── merger ───────────────────────────────────────────────────────────────────


def _make_rf(name: str, rule_name: str, path: str, action: str = "delete") -> RuleFile:
    return RuleFile(
        meta=RuleMeta(name=name),
        rules=[Rule(name=rule_name, path=path, match=MatchCriteria(pattern="*"), action=action)],
    )


def test_merge_combines_distinct_rules():
    rf1 = _make_rf("A", "rule-a", "C:/A")
    rf2 = _make_rf("B", "rule-b", "C:/B")
    merged = merge_rule_files([rf1, rf2])
    assert len(merged.rules) == 2


def test_merge_different_action_means_distinct_rules():
    rf1 = _make_rf("A", "shared", "C:/Same", action="delete")
    rf2 = _make_rf("B", "shared", "C:/Same", action="trash")
    merged = merge_rule_files([rf1, rf2])
    assert len(merged.rules) == 2


def test_merge_exact_duplicate_deduplicates():
    rf1 = _make_rf("A", "shared", "C:/Same", action="delete")
    rf2 = _make_rf("B", "shared", "C:/Same", action="delete")
    merged = merge_rule_files([rf1, rf2])
    assert len(merged.rules) == 1
    assert merged.rules[0].action == "delete"


def test_rule_file_to_toml_round_trip(tmp_path):
    rf = _make_rf("Test", "my-rule", "C:/Temp")
    toml_str = rule_file_to_toml(rf)
    out = tmp_path / "out.toml"
    out.write_text(toml_str, encoding="utf-8")
    parsed = parse_rule_file(out)
    assert parsed.rules[0].name == "my-rule"
    assert parsed.rules[0].path == "C:/Temp"
