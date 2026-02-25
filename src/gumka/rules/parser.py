import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal


@dataclass
class MatchCriteria:
    pattern: str | list[str] | None = None
    older_than: str | None = None
    larger_than: str | None = None
    type: Literal["file", "directory"] | None = None


@dataclass
class Rule:
    path: str
    match: MatchCriteria
    action: Literal["delete", "trash", "log"]
    name: str = ""


@dataclass
class RuleMeta:
    name: str
    description: str = ""
    author: str = ""
    version: str = "1.0.0"


@dataclass
class RuleFile:
    meta: RuleMeta
    rules: list[Rule] = field(default_factory=list)
    source_path: Path | None = None


def parse_rule_file(path: Path) -> RuleFile:
    with open(path, "rb") as f:
        data = tomllib.load(f)

    raw_meta = data.get("meta", {})
    meta = RuleMeta(
        name=raw_meta.get("name", path.stem),
        description=raw_meta.get("description", ""),
        author=raw_meta.get("author", ""),
        version=raw_meta.get("version", "1.0.0"),
    )

    rules: list[Rule] = []
    for raw in data.get("rules", []):
        raw_match = raw.get("match", {})
        match = MatchCriteria(
            pattern=raw_match.get("pattern"),
            older_than=raw_match.get("older_than"),
            larger_than=raw_match.get("larger_than"),
            type=raw_match.get("type"),
        )
        rules.append(
            Rule(
                name=raw.get("name", ""),
                path=raw["path"],
                match=match,
                action=raw.get("action", "log"),
            )
        )

    return RuleFile(meta=meta, rules=rules, source_path=path)
