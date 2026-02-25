from pathlib import Path

from .parser import Rule, RuleFile, RuleMeta


def merge_rule_files(rule_files: list[RuleFile]) -> RuleFile:
    """Smart union: keep all rules; deduplicate on (name, path, action); first occurrence wins."""
    merged: dict[tuple[str, str, str], Rule] = {}
    for rf in rule_files:
        for rule in rf.rules:
            key = (rule.name, rule.path, rule.action)
            if key not in merged:
                merged[key] = rule

    names = ", ".join(rf.meta.name for rf in rule_files)
    meta = RuleMeta(name="Merged Rule Set", description=f"Merged from: {names}")
    return RuleFile(meta=meta, rules=list(merged.values()))


def rule_file_to_toml(rf: RuleFile) -> str:
    """Serialize a RuleFile to TOML without an external library."""
    lines: list[str] = [
        "[meta]",
        f'name        = "{rf.meta.name}"',
        f'description = "{rf.meta.description}"',
        f'author      = "{rf.meta.author}"',
        f'version     = "{rf.meta.version}"',
        "",
    ]

    for rule in rf.rules:
        parts: list[str] = []
        if rule.match.pattern:
            parts.append(f'pattern = "{rule.match.pattern}"')
        if rule.match.older_than:
            parts.append(f'older_than = "{rule.match.older_than}"')
        if rule.match.larger_than:
            parts.append(f'larger_than = "{rule.match.larger_than}"')
        if rule.match.type:
            parts.append(f'type = "{rule.match.type}"')

        rule_lines = [
            "[[rules]]",
            f'name   = "{rule.name}"',
            f'path   = "{Path(rule.path).as_posix()}"',
        ]
        if parts:
            rule_lines.append(f'match  = {{ {", ".join(parts)} }}')
        rule_lines += [f'action = "{rule.action}"', ""]
        lines += rule_lines

    return "\n".join(lines)
