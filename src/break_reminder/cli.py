import shutil
import socket
import subprocess
import sys  # System module to interact with the Python runtime environment
# (interpreters, command-line arguments, etc.)
from pathlib import Path

from break_reminder import config


# Users home directory is Path.home()
AUTOSTART_DIR = Path.home() / ".config" / "autostart"

DESKTOP_FILE = AUTOSTART_DIR / "break-reminder.desktop"
# .desktop files are plain text configuration files that act as application
# shortcuts and metadata. They dictate how a program appears in your
# application menu, which icon it uses, and how it launches.
# GNOME checks ~/.config/autostart/ every time there is a log in. Every
# .desktop file inside gets launched.

RUNTIME_DIR = Path.home() / ".config" / "break-reminder"
SOCKET_FILE = RUNTIME_DIR / "break-reminder.sock"


def ensure_runtime_dir():
    RUNTIME_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )


def show_existing_app():
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.connect(str(SOCKET_FILE))
            sock.sendall(b"show")
        return True
    except (FileNotFoundError, ConnectionRefusedError):
        SOCKET_FILE.unlink(missing_ok=True)
        return False


def launch_gui():
    ensure_runtime_dir()

    if show_existing_app():
        return

    # sys.executable tells it to use the exact Python interpreter that is
    # currently running this break-reminder command.
    subprocess.Popen(
        [sys.executable, "-m", "break_reminder.main"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    # The GUI doesn't need input from the terminal, so we disconnect its
    # standard input. The GUI shouldn't print things into your terminal,
    # so we disconnect the standard output and standard errors too.
    # We don't want the GUI to behave like a foreground child of the
    # terminal command. We want:
    # terminal
    #    │
    #    └── break-reminder
    #           │
    #           └── GUI process
    # where the GUI continues running independently. So we can run
    # "break-reminder" and immediately get your shell prompt back. So we use
    # start_new_session=True


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
    # searches your PATH for an executable.
    # /home/you/.local/bin/break-reminder
    # The .desktop file needs to know what executable GNOME should launch:
    # Exec=/home/you/.local/bin/break-reminder

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
        launch_gui()
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


# When I type "break-reminder" in the terminal, I don't want:
#
# GUI process #1
#     └── timer #1
#
# GUI process #2
#     └── timer #2
#
# I only want one GUI process:
#
# GUI process #1
#     └── timer #1
#
# If another "break-reminder" command is run while the GUI is already
# running, it should show the existing application instead of starting
# another GUI process.
#
# The Unix socket acts like a tiny communication channel between separate
# invocations of "break-reminder".
#
# Terminal command
#        │
#        │ "show"
#        ▼
# Unix socket
#        │
#        ▼
# Existing GUI process
#        │
#        ▼
# Show window
#
# The Unix socket is only for communication. It does NOT by itself guarantee
# that only one GUI process exists.
#
# The fcntl lock is what guarantees that only one GUI process becomes the
# active application instance. If another GUI process starts at the same
# time, it cannot acquire the lock, so it sends "show" to the existing
# application and exits.
#
# We could have used a PID file, a TCP port, D-Bus, or other desktop-specific
# mechanisms. A Unix socket gives us a local communication mechanism without
# opening a network port.
#
# The socket file looks like:
#
# ~/.config/break-reminder/break-reminder.sock
#
# The existing application listens on this socket. A second
# "break-reminder" invocation connects to it and sends "show".
#
# The lock file looks like:
#
# ~/.config/break-reminder/break-reminder.lock
#
# The first "break-reminder" invocation acquires the lock and becomes the
# active GUI process. A second GUI process cannot acquire the lock.
#
# For the first "break-reminder" there isn't an existing GUI, so cli.py
# needs to start the GUI as a separate process. subprocess.Popen(...)
# starts another process and runs break_reminder.main.
#
# break-reminder command
#         │
#         ▼
#       cli.py
#         │
#         │ Start GUI process
#         ▼
#       main.py
#         │
#         │ Try to acquire fcntl lock
#         │
#         ├── LOCK AVAILABLE ──> become GUI instance
#         │                         │
#         │                         └── listen on Unix socket
#         │
#         └── LOCK TAKEN ───────> send "show"
#                                  │
#                                  ▼
#                            Existing GUI
