import shutil
import sys  # System module to interact with the Python runtime environment
# (interpreters, command-line arguments, etc.)
from pathlib import Path

from break_reminder import config
from break_reminder import main as gui


# Users home directory is Path.home()
AUTOSTART_DIR = Path.home() / ".config" / "autostart"

DESKTOP_FILE = AUTOSTART_DIR / "break-reminder.desktop"
# .desktop files are plain text configuration files that act as application
# shortcuts and metadata. They dictate how a program appears in your
# application menu, which icon it uses, and how it launches.
# GNOME checks ~/.config/autostart/ every time there is a log in. Every
# .desktop file inside gets launched.


def ensure_autostart_dir():
    AUTOSTART_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )
    # Creates ~/.config/autostart if it doesnt exist


def enable_autostart():
    # Register my application with GNOME so the application launches
    # automatically.
    # Creates a .desktop file in ~/.config/autostart that launches main.py
    # when the user logs in
    ensure_autostart_dir()

    executable = shutil.which("break-reminder")

    if executable is None:
        print("Could not find the break-reminder executable.")
        raise SystemExit(1)

    desktop_contents = f"""\
[Desktop Entry]
Type=Application
Name=Break Reminder
Exec={executable}
Terminal=false
X-GNOME-Autostart-enabled=true
"""

    DESKTOP_FILE.write_text(desktop_contents)

    print("Break Reminder autostart enabled.")


# Instead of creating: Exec=/home/.../Projects/break-reminder/.venv/bin/python
# /home/.../Projects/break-reminder/main.py
# It will create: Exec=/home/vaishnavi-asawale/.local/bin/break-reminder


def disable_autostart():
    if DESKTOP_FILE.exists():
        DESKTOP_FILE.unlink()
        # This is like deleting the file. It removes the .desktop file from
        # ~/.config/autostart, which means the program will no longer launch
        # automatically when the user logs in.
        print("Break Reminder autostart disabled.")
    else:
        print("Break reminder utostart is already disabled.")


def status_autostart():

    if DESKTOP_FILE.exists():
        print("Break reminder autostart is enabled")
    else:
        print("Break reminder autostart is disabled")


def main():
    # Command-line argument handling
    if len(sys.argv) == 1:
        gui.main()
        return

    command = sys.argv[1]

    if command in ("--help", "-h"):
        print("Usage:")
        print("  break-reminder")
        print("  break-reminder <command>")
        print()
        print("Commands:")
        print("  enable")
        print("  disable")
        print("  status")
        print("  autostart enable")
        print("  autostart disable")
        print("  autostart status")
        print()
        print("Run 'break-reminder' without a command to open the app.")
        return

    if command == "enable":
        if len(sys.argv) != 2:
            print("Usage: break-reminder enable")
            raise SystemExit(1)

        config.enable()
        print("Break reminder enabled.")
        return

    if command == "disable":
        if len(sys.argv) != 2:
            print("Usage: break-reminder disable")
            raise SystemExit(1)

        config.disable()
        print("Break reminder disabled.")
        return

    if command == "status":
        if len(sys.argv) != 2:
            print("Usage: break-reminder status")
            raise SystemExit(1)

        config.status()
        return

    # Autostart configuration
    if command == "autostart":
        if len(sys.argv) != 3:
            print("Usage:")
            print("  break-reminder autostart enable")
            print("  break-reminder autostart disable")
            print("  break-reminder autostart status")
            raise SystemExit(1)

        subcommand = sys.argv[2]

        if subcommand == "enable":
            enable_autostart()
        elif subcommand == "disable":
            disable_autostart()
        elif subcommand == "status":
            status_autostart()
        else:
            print(f"Unknown autostart command: {subcommand}")
            raise SystemExit(1)

        return

    print(f"Unknown command: {command}")
    print("Run 'break-reminder --help' for usage.")
    raise SystemExit(1)


if __name__ == "__main__":
    main()
