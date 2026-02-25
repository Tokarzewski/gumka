from .parser import RuleFile

VALID_ACTIONS: set[str] = {"delete", "trash", "log"}
VALID_TYPES: set[str | None] = {"file", "directory", None}


def validate_rule_file(rf: RuleFile) -> list[str]:
    """Return validation error messages. Empty list means valid."""
    errors: list[str] = []

    for i, rule in enumerate(rf.rules):
        ctx = f"Rule [{i}]"

        if not rule.path.strip():
            errors.append(f"{ctx}: 'path' is required")
        if rule.action not in VALID_ACTIONS:
            errors.append(
                f"{ctx}: invalid action '{rule.action}' - must be delete, trash, or log"
            )
        if rule.match.type not in VALID_TYPES:
            errors.append(
                f"{ctx}: invalid match type '{rule.match.type}' - must be 'file' or 'directory'"
            )

    return errors
