import subprocess
import sys  # System module to interact with the Python runtime environment

# (interpreters, command-line arguments, etc.)
from break_reminder import autostart, config, ipc

RUNTIME_DIR = config.CONFIG_DIR
SOCKET_FILE = RUNTIME_DIR / "break-reminder.sock"


def ensure_runtime_dir():
    RUNTIME_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )


COMMAND_TIMEOUT = 2


def send_command(command):
    # Sends a command to the running GUI. Returns False if no GUI is running
    # or it doesn't acknowledge within COMMAND_TIMEOUT seconds.
    try:
        with ipc.connect(SOCKET_FILE, timeout=COMMAND_TIMEOUT) as sock:
            sock.sendall(command.encode())
            # Wait for the GUI to acknowledge; a hung GUI times out (an
            # OSError) instead of being reported as having acted.
            return sock.recv(len(ipc.ACK)) == ipc.ACK
    except OSError:
        # Treat the GUI as unreachable rather than crashing after the config
        # has already been saved. Don't delete the socket file here: a refused
        # connection can also mean the GUI has bound but not yet called
        # listen(). The GUI clears stale sockets itself on startup.
        return False


def show_existing_app():
    return send_command("show")


def open_gui_log():
    # The GUI's stderr goes to the shared log so a crash on startup leaves a
    # traceback there. Falls back to DEVNULL if the log can't be opened.
    try:
        config.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        return (config.CONFIG_DIR / config.LOG_NAME).open("a")
    except OSError:
        return subprocess.DEVNULL


def fail_launch(error):
    config.log_warning(f"Could not start the GUI: {error}", level="ERROR")
    print(
        f"Could not start Break Reminder: {error}\n"
        f"See {config.CONFIG_DIR / config.LOG_NAME} for details."
    )
    raise SystemExit(1)


def launch_gui():
    try:
        ensure_runtime_dir()
    except OSError as error:
        fail_launch(error)

    if show_existing_app():
        return

    gui_log = open_gui_log()
    try:
        # sys.executable tells it to use the exact Python interpreter that is
        # currently running this break-reminder command.
        subprocess.Popen(
            [sys.executable, "-m", "break_reminder.main"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=gui_log,
            start_new_session=True,
        )
    except (OSError, subprocess.SubprocessError) as error:
        fail_launch(error)
    finally:
        # The child has its own copy of the descriptor.
        if gui_log is not subprocess.DEVNULL:
            gui_log.close()
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


def run_autostart(action):
    # Permission denied, disk full, a missing executable, etc. are all
    # OSErrors (FileNotFoundError included). Show a message and exit 1
    # instead of a traceback.
    try:
        action()
    except OSError as error:
        print(f"Autostart failed: {error}")
        raise SystemExit(1)


def run_config(action):
    # Permission problems etc. in the config file are OSErrors. Show a
    # message and exit 1 instead of a traceback.
    try:
        action()
    except OSError as error:
        print(f"Config error: {error}")
        raise SystemExit(1)


def enable_autostart():
    run_autostart(autostart.enable)


def main():
    # Command-line argument handling
    if len(sys.argv) == 1:
        launch_gui()
        return

    command = sys.argv[1]

    if command == "--help":
        if len(sys.argv) != 2:
            print("Usage: break-reminder --help")
            raise SystemExit(1)

        print("Usage:")
        print("  break-reminder")
        print("  break-reminder <command>")
        print()
        print("Commands:")
        print("  enable")
        print("  disable")
        print("  status")
        print("  quit")
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

        run_config(config.enable)
        send_command("config-changed")
        print("Break reminder enabled.")
        return

    if command == "disable":
        if len(sys.argv) != 2:
            print("Usage: break-reminder disable")
            raise SystemExit(1)

        run_config(config.disable)
        send_command("config-changed")
        print("Break reminder disabled.")
        return

    if command == "status":
        if len(sys.argv) != 2:
            print("Usage: break-reminder status")
            raise SystemExit(1)

        run_config(config.status)
        return

    if command == "quit":
        if len(sys.argv) != 2:
            print("Usage: break-reminder quit")
            raise SystemExit(1)

        if send_command("quit"):
            print("Break reminder stopped.")
        else:
            print("Break reminder is not running.")
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
            run_autostart(autostart.disable)
        elif subcommand == "status":
            run_autostart(autostart.status)
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
