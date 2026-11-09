# Moodle CLI

Terminal tool for Moodle course synchronization and document downloads with both an interactive menu and command-line interface.

## Quick Start

```bash
# Install
pip install -e .

# Launch interactive menu
python moodle.py
```

## Setup

Configure your Moodle URL and credentials:

```bash
python moodle.py config --setup
```

Verify your connection:

```bash
python moodle.py auth --status
```

## Common Commands

| Task | Command |
| :--- | :--- |
| **Interactive Menu** | `python moodle.py` |
| **List Courses** | `python moodle.py courses` |
| **View Course Tree** | `python moodle.py tree <COURSE_ID>` |
| **Check Updates** | `python moodle.py check` |
| **Sync All** | `python moodle.py sync` |
| **Sync Specific Course** | `python moodle.py sync -c <ID>` |
| **Clean Missing Files** | `python moodle.py clean` |
| **View Settings** | `python moodle.py config` |
| **Reset Settings** | `python moodle.py config --reset` |

## License

[MIT](LICENSE)
