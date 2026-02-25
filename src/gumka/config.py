import logging
import os
from datetime import datetime
from pathlib import Path


def get_app_dir() -> Path:
    app_dir = Path(os.environ["APPDATA"]) / "gumka"
    app_dir.mkdir(parents=True, exist_ok=True)
    return app_dir


def get_rules_dir() -> Path:
    rules_dir = get_app_dir() / "rules"
    rules_dir.mkdir(parents=True, exist_ok=True)
    return rules_dir


def get_schedules_path() -> Path:
    return get_app_dir() / "schedules.toml"


def get_resources_dir() -> Path:
    """Return the path to the bundled resources directory (gumka.png etc.).

    Works for both editable installs (resources/ at project root) and
    installed wheels (resources/ bundled alongside the package files).
    """
    pkg_resources = Path(__file__).parent / "resources"
    if pkg_resources.exists():
        return pkg_resources
    return Path(__file__).parent.parent.parent / "resources"


def get_context_menu_rules_path() -> Path:
    return get_rules_dir() / "context_menu.toml"


def get_app_rule_files() -> list[Path]:
    """Return all .toml files in the rules dir."""
    return sorted(get_rules_dir().glob("*.toml"))


def get_log_path() -> Path:
    log_dir = get_app_dir() / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir / f"gumka_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log"


def setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    log_path = get_log_path()
    logging.basicConfig(
        level=level,
        format="%(asctime)s  %(levelname)-8s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )
