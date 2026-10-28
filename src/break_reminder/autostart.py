import shutil
from pathlib import Path

# Shared by the CLI ("break-reminder autostart ...") and the "Start at login"
# checkbox in the GUI. Errors are raised rather than exiting, so a failure
# from the checkbox can't close the window. (The GUI's prints go nowhere,
# since it runs with stdout sent to /dev/null.)

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


def is_enabled():
    return DESKTOP_FILE.exists()


def enable():
    # Register my application with GNOME so the application launches
    # automatically.
    # Creates a .desktop file in ~/.config/autostart that launches
    # break-reminder when the user logs in
    executable = shutil.which("break-reminder")
    # searches your PATH for an executable.
    # /home/you/.local/bin/break-reminder
    # The .desktop file needs to know what executable GNOME should launch:
    # Exec=/home/you/.local/bin/break-reminder

    if executable is None:
        raise FileNotFoundError(
            "Could not find the break-reminder executable."
        )

    ensure_autostart_dir()

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


def disable():
    if DESKTOP_FILE.exists():
        DESKTOP_FILE.unlink()
        # This is like deleting the file. It removes the .desktop file from
        # ~/.config/autostart, which means the program will no longer launch
        # automatically when the user logs in.
        print("Break Reminder autostart disabled.")
    else:
        print("Break reminder autostart is already disabled.")


def status():
    if is_enabled():
        print("Break reminder autostart is enabled")
    else:
        print("Break reminder autostart is disabled")
