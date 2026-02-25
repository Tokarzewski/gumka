# gumka

**gumka** (Polish for *eraser*) is a rule-based disk cleaner for Windows. 
Define TOML rule files that describe which files and folders to target, 
then scan, clean, or schedule automated runs — all from the command line.

## Features

- Rule-based scanning with glob patterns, age filters, and size filters
- Three actions per rule: `delete`, `trash` (Recycle Bin), or `log`
- Scheduled runs via Windows Task Scheduler
- Windows Explorer right-click context menu integration ("Add to Gumka")
- Recycle Bin inspection and emptying

## Installation

```
pip install gumka
```

## Quick start

**1. Create a rule file**

```
gumka rules new my-rules
```

This creates `my_rules.toml`. Open it and add rules:

```toml
[meta]
name        = "My rules"
description = "Clean up temp files"
author      = "Your Name"
version     = "1.0.0"

[[rules]]
name   = "Old downloads"
path   = "C:/Users/YourName/Downloads"
match  = { pattern = "**/*.zip", older_than = "30d" }
action = "trash"

[[rules]]
name   = "Large log files"
path   = "C:/Logs"
match  = { pattern = "**/*.log", larger_than = "50MB" }
action = "delete"
```

**2. Install the rule file**

Copy or move the file to the rules directory:

```
gumka rules open
```

**3. Scan**

```
gumka scan --rules my_rules.toml
```

**4. Clean**

```
gumka clean --rules my_rules.toml
```

Add `--yes` to skip the confirmation prompt.

## Rule file format

Rule files are TOML. Each file has an optional `[meta]` block and one or more `[[rules]]` entries.

```toml
[meta]
name        = "Rule set name"
description = "Optional description"
author      = "Author"
version     = "1.0.0"

[[rules]]
name   = "Optional rule name"
path   = "C:/path/to/scan"        # required
action = "trash"                  # delete | trash | log

# All match fields are optional — omit to match everything in path
[rules.match]
pattern    = "**/*.tmp"           # glob pattern
older_than = "30d"                # 30d, 2w, 12h
larger_than = "10MB"              # B, KB, MB, GB
type       = "file"               # file | directory
```

### Actions

| Action   | Effect                         |
|----------|--------------------------------|
| `delete` | Permanently delete the item    |
| `trash`  | Move to the Windows Recycle Bin |
| `log`    | Report the match, no changes   |

### Match criteria

| Field        | Examples             | Description                          |
|--------------|----------------------|--------------------------------------|
| `pattern`    | `**/*.tmp`, `*.log`  | Glob pattern relative to `path`      |
| `older_than` | `30d`, `2w`, `12h`   | Only match if last modified before   |
| `larger_than`| `50MB`, `500KB`      | Only match files above this size     |
| `type`       | `file`, `directory`  | Restrict to files or directories     |

## Commands

### `scan`

Preview matches without making any changes.

```
gumka scan [--rules FILE] [--path DIR] [--verbose]
```

### `clean`

Scan and apply actions.

```
gumka clean [--rules FILE] [--path DIR] [--yes] [--verbose]
```

### `rules`

Manage rule files stored in `%APPDATA%\gumka\rules\`.

```
gumka rules new <name> [-o output.toml]   # create a rule file from template
gumka rules validate <file>               # check a rule file for errors
gumka rules list                          # list installed rule files
gumka rules open                          # open the rules folder in Explorer
gumka rules merge <file1> <file2> -o out  # merge multiple rule files
gumka rules quick-add <path>              # add a trash rule via context menu
```

### `schedules`

Register rules as recurring Windows Task Scheduler tasks.

```
gumka schedules new                              # create schedules.toml
gumka schedules add --at 08:00 [path]            # add a daily job
gumka schedules add --at 12:00 --weekly Monday   # add a weekly job
gumka schedules list                             # show all schedules
gumka schedules open                             # edit schedules.toml
gumka schedules install                          # apply to Task Scheduler
gumka schedules uninstall                        # remove all gumka tasks
```

### `shell`

Install or remove the Windows Explorer right-click context menu entry.

```
gumka shell install     # add "Add to Gumka" to the folder context menu
gumka shell uninstall   # remove it
```

Once installed, right-clicking any folder in Explorer shows **Add to Gumka**, which appends a `trash` rule for that folder to `%APPDATA%\gumka\rules\context_menu.toml`.

### `trash`

Inspect and empty the Windows Recycle Bin.

```
gumka trash stats         # show item count and total size
gumka trash empty [--yes] # empty the Recycle Bin
```

## Data directories

| Path                                   | Contents              |
|----------------------------------------|-----------------------|
| `%APPDATA%\gumka\rules\`              | Installed rule files  |
| `%APPDATA%\gumka\schedules.toml`      | Schedule definitions  |
| `%APPDATA%\gumka\logs\`               | Log files             |

## Development

```
git clone https://github.com/Tokarzewski/gumka
cd gumka
uv sync --group dev
uv run pytest
uv run ruff check src
```

## Icon attribution

<a href="https://www.flaticon.com/free-icons/eraser" title="eraser icons">
Eraser icons created by Freepik - Flaticon</a>
