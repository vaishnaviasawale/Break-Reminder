import sys # System module to interact with the Python runtime environment (interpreters, command-line arguments, etc.)
from pathlib import Path

import config

PROJECT_DIR = Path(__file__).resolve().parent
PYTHON = PROJECT_DIR / ".venv" / "bin" / "python"
MAIN = PROJECT_DIR / "main.py"

# Users home directory is Path.home()
AUTOSTART_DIR = Path.home() / ".config" / "autostart"

DESKTOP_FILE = AUTOSTART_DIR / "break-reminder.desktop"
# .desktop files are plain text configuration files that act as application shortcuts and metadata. They dictate how a program appears in your application menu, which icon it uses, and how it launches. 
# GNOME checks ~/.config/autostart/ every time there is a log in. Every .desktop file inside gets launched.

def ensure_autostart_dir():
    AUTOSTART_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )
    # Creates ~/.config/autostart if it doesnt exist

def enable_autostart():
    # Register my application with GNOME so the application launches automatically.
    # Creates a .desktop file in ~/.config/autostart that launches main.py when the user logs in
    ensure_autostart_dir()

    desktop_contents = f"""\
[Desktop Entry]
Type=Application
Name=Break Reminder
Exec={PYTHON} {MAIN}
Terminal=false
X-GNOME-Autostart-enabled=true
"""

    DESKTOP_FILE.write_text(desktop_contents)

    print("Break Reminder enabled.")

def disable_autostart():
    if DESKTOP_FILE.exists():
        DESKTOP_FILE.unlink()
        # This is like deleting the file. It removes the .desktop file from ~/.config/autostart, which means the program will no longer launch automatically when the user logs in.
        print("Break Reminder autostart disabled.")
    else:
        print("Break reminder utostart is already disabled.")

def status_autostart():

    if DESKTOP_FILE.exists():
        print("Break reminder autostart is enabled")
    else:
        print("Break reminder autostart is disabled")

# Command-line argument handling
if len(sys.argv) < 2:
    print("Usage:")
    print()
    print("  python cli.py enable")
    print("  python cli.py disable")
    print("  python cli.py status")
    print()
    print("  python cli.py autostart enable")
    print("  python cli.py autostart disable")
    print("  python cli.py autostart status")
    raise SystemExit(1)

command = sys.argv[1]

# Reminder configuration
if command == "enable":
    if len(sys.argv) != 2:
        print("Break reminder usage: python cli.py enable")
        raise SystemExit(1)

    config.enable()
    print("Break reminder enabled.")

elif command == "disable":
    if len(sys.argv) != 2: 
        print("Break reminder usage: python cli.py disable") 
        raise SystemExit(1)

    config.disable()
    print("Break reminder disabled.")

elif command == "status":
    if len(sys.argv) != 2:
        print("Break reminder usage: python cli.py status")
        raise SystemExit(1)

    config.status()

# Autostart configuration
elif command == "autostart":
    if len(sys.argv) != 3:
        print("Usage:")
        print("  python cli.py autostart enable")
        print("  python cli.py autostart disable")
        print("  python cli.py autostart status")

    subcommand = sys.argv[2]

    if subcommand == "enable":
        enable_autostart()
    elif subcommand == "disable":
        disable_autostart()
    elif subcommand == "status":
        status_autostart()
    else:
        print("Invalid subcommand.")
        raise SystemExit(1)
else:
    print("Unknown command.")
    raise SystemExit(1)