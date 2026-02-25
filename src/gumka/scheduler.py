import ctypes
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

TASK_PREFIX = "Gumka - "

VALID_DAYS = {
    "sunday", "monday", "tuesday", "wednesday",
    "thursday", "friday", "saturday",
}

_PS_TASK_FILTER = (
    f"Get-ScheduledTask | Where-Object {{ $_.TaskName -like '{TASK_PREFIX}*' }}"
)


@dataclass
class TaskResult:
    task_name: str
    time: str
    frequency: str
    success: bool
    skipped: bool = False
    message: str = ""  # error if failed, reason if skipped


def parse_time(value: str) -> str:
    """Validate and normalize a HH:MM string. Returns zero-padded HH:MM."""
    if not re.match(r"^\d{1,2}:\d{2}$", value):
        raise ValueError(f"'{value}' is not a valid time — use HH:MM (e.g. 09:00)")
    h, m = value.split(":")
    if not (0 <= int(h) <= 23 and 0 <= int(m) <= 59):
        raise ValueError(f"'{value}' is out of range — hour 0-23, minute 0-59")
    return f"{int(h):02d}:{int(m):02d}"


def find_exe() -> Path:
    found = shutil.which("gumka.exe") or shutil.which("gumka")
    if found and Path(found).suffix.lower() == ".exe":
        return Path(found)
    exe = Path(sys.executable).parent / "gumka.exe"
    if not exe.exists():
        exe = Path(sys.executable).parent / "Scripts" / "gumka.exe"
    return exe


def build_ps_trigger(time: str, day: str | None) -> str:
    if day:
        return f"New-ScheduledTaskTrigger -Weekly -DaysOfWeek {day} -At '{time}'"
    return f"New-ScheduledTaskTrigger -Daily -At '{time}'"


def _register_task(task_name: str, exe: Path, argument: str, trigger_ps: str) -> tuple[bool, str]:
    ps_script = (
        f"Register-ScheduledTask -TaskName '{task_name}' -Force"
        f" -Action (New-ScheduledTaskAction -Execute \"{exe.as_posix()}\" -Argument '{argument}')"
        f" -Trigger ({trigger_ps})"
        f" -Principal (New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited)"
        f" -Settings (New-ScheduledTaskSettingsSet -ExecutionTimeLimit 0)"
    )
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps_script],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0, result.stderr.strip()


def install_entries(entries: list[dict], exe: Path) -> list[TaskResult]:
    """Register Windows Task Scheduler tasks from schedules.toml entries."""
    results: list[TaskResult] = []
    seen_names: dict[str, int] = {}

    for entry in entries:
        time_raw = entry.get("time", "")
        day = entry.get("day")

        if not time_raw:
            results.append(TaskResult(
                task_name="?", time="", frequency="",
                success=False, skipped=True, message="missing time field",
            ))
            continue

        try:
            time = parse_time(time_raw)
        except ValueError as e:
            results.append(TaskResult(
                task_name="?", time=time_raw, frequency="",
                success=False, skipped=True, message=str(e),
            ))
            continue

        if day and day.lower() not in VALID_DAYS:
            results.append(TaskResult(
                task_name="?", time=time, frequency="",
                success=False, skipped=True, message=f"invalid day '{day}'",
            ))
            continue

        if rule_file := entry.get("rule_file"):
            rule_files = [Path(rule_file)]
        elif rule_dir := entry.get("rule_directory"):
            rule_files = sorted(Path(rule_dir).glob("*.toml"))
            if not rule_files:
                results.append(TaskResult(
                    task_name=str(rule_dir), time=time, frequency="",
                    success=False, skipped=True, message="no .toml files found in directory",
                ))
                continue
        else:
            results.append(TaskResult(
                task_name="?", time=time, frequency="",
                success=False, skipped=True, message="missing rule_file or rule_directory",
            ))
            continue

        frequency = f"weekly on {day}" if day else "daily"
        trigger = build_ps_trigger(time, day)

        for rf in rule_files:
            base_name = f"{TASK_PREFIX}{rf.stem}"
            n = seen_names.get(base_name, 0)
            seen_names[base_name] = n + 1
            task_name = base_name if n == 0 else f"{base_name} ({n + 1})"

            argument = f'clean --rules "{rf.as_posix()}" --yes'

            ok, error = _register_task(task_name, exe, argument, trigger)
            results.append(TaskResult(
                task_name=task_name, time=time, frequency=frequency,
                success=ok, message=error,
            ))

    return results


def get_installed_task_names() -> set[str]:
    """Return the names of all installed gumka Task Scheduler tasks."""
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         f"{_PS_TASK_FILTER} | Select-Object -ExpandProperty TaskName"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return set()
    return {name.strip() for name in result.stdout.splitlines() if name.strip()}


def tasks_exist() -> bool:
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", _PS_TASK_FILTER],
        capture_output=True,
        text=True,
    )
    return bool(result.stdout.strip())


def remove_all_tasks() -> tuple[bool, str]:
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         f"{_PS_TASK_FILTER} | Unregister-ScheduledTask -Confirm:$false"],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0, result.stderr.strip()


def is_admin() -> bool:
    """Return True if the current process has Administrator privileges."""
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def relaunch_as_admin(args: list[str]) -> None:
    """Relaunch gumka with the given arguments under an elevated process."""
    exe = find_exe()
    arg_str = " ".join(args)
    subprocess.run(
        ["powershell", "-Command",
         f'Start-Process "{exe}" -ArgumentList \'{arg_str}\' -Verb RunAs -Wait'],
        check=False,
    )
