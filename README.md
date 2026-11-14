# Break Reminder

A small desktop app for Linux (GNOME) that reminds you to take a break.

You tell it how many minutes until your next break. The window hides itself
and, when the time is up, pops back up on top of everything with a random
picture (an xkcd comic, or a photo of landscapes, seaside views, European
towns, fairy illustrations or puppies). You can control it from the window or
from the terminal.

## What it does

- Starts a countdown timer (1 minute to 24 hours) and hides the window while
  it runs.
- When the timer ends, shows a "Time for a break!" popup above other windows.
- Fetches the picture from the internet in the background. If the download
  fails or takes longer than 3 seconds, it shows one of four bundled
  fallback images instead, so the popup always appears.
- Can be switched on/off ("Enable Reminder" / "Disable Reminder"). When off,
  no timer can be started and any running timer is cancelled.
- Can start automatically when you log in ("Start at login" checkbox).
- Closing the window with X only hides it. The app keeps running. Use
  `break-reminder quit` to stop it.
- Only one copy ever runs. Running `break-reminder` again just brings the
  existing window to the front.

## Requirements

- Linux with a desktop session (built and tested on Fedora / GNOME)
- Python 3.14 or newer
- [uv](https://docs.astral.sh/uv/)
- Tkinter available for your Python (on Fedora: `sudo dnf install python3-tkinter`)
- Internet access for the pictures (optional, there are local fallbacks)

Linux only: the app uses `fcntl` file locks, Unix domain sockets, and the
XDG autostart folder.

## Installing

Install it as a global command with uv:

```bash
uv tool install .
```

This puts `break-reminder` in `~/.local/bin`. Make sure that folder is on your
`PATH`.

### Updating an existing install

```bash
break-reminder quit                # stop the old version
rm -rf dist
uv build                           # creates dist/*.whl and dist/*.tar.gz
uv tool install --force --reinstall dist/break_reminder-*.whl
break-reminder                     # start the new version
```

Bump `version` in `pyproject.toml` first if you want `uv tool list` to show
that the update happened. Your settings are kept, and the autostart entry
keeps working because the install path does not change.

## Usage

```
break-reminder                      Open the app (or show it if already running)
break-reminder enable               Turn the reminder on
break-reminder disable              Turn the reminder off (cancels the timer)
break-reminder status               Print whether the reminder is on or off
break-reminder quit                 Stop the running app
break-reminder autostart enable     Launch automatically at login
break-reminder autostart disable    Stop launching at login
break-reminder autostart status     Print whether autostart is on or off
break-reminder --help               Show the command list
```

Commands take no extra arguments. Anything else prints a usage message and
exits with code 1.

`enable`, `disable` and `status` work even if the app is not running (they
just read/write the config file). If the app is running, `enable` and
`disable` also tell it to update straight away.

### In the window

1. Type the number of minutes and press Enter (or click **Start Timer**).
2. The window hides. Click the app again with `break-reminder` to see the
   countdown ("Next break in 24:59, break at 3:30 PM").
3. At zero, the window returns with a picture.

## Files the app creates

All in `~/.config/break-reminder/`:

| File                  | Purpose                                              |
| --------------------- | ---------------------------------------------------- |
| `config.json`         | Settings. Currently only `{"enabled": true}`         |
| `config.json.bak`     | Copy of a corrupt config, kept before resetting it   |
| `config.lock`         | Lock so two commands can't edit the config at once   |
| `break-reminder.lock` | Held by the running app to guarantee a single copy   |
| `break-reminder.sock` | Unix socket the CLI uses to talk to the running app  |
| `break-reminder.log`  | Warnings and errors (also GUI crash tracebacks)      |

Autostart is a separate file: `~/.config/autostart/break-reminder.desktop`.

Reminder on/off and autostart on/off are independent settings. Changing one
never changes the other.

If something goes wrong (the window does not appear, a command is ignored),
look at `~/.config/break-reminder/break-reminder.log` first.

## How it works

There are two programs in one package, plus a few helper modules:

```
src/break_reminder/
  cli.py        the `break-reminder` command (short-lived)
  main.py       the Tkinter GUI (long-lived, one copy)
  ipc.py        Unix socket helpers shared by both
  config.py     reading/writing config.json safely
  autostart.py  creating/removing the .desktop autostart file
  assets/       four fallback images
```

### Starting and the single-instance rule

```
break-reminder
     |
     v
  cli.py ---- "show" over the socket ----> running GUI? --yes--> raise window
     |                                          |
     no                                         no reply
     |                                          |
     +--------- subprocess.Popen <--------------+
                      |
                      v
                  main.py (GUI)
                      |
          try to lock break-reminder.lock (flock, non-blocking)
              |                         |
          got the lock             lock already held
              |                         |
      become THE instance       send "show", exit
      listen on the socket
```

- The **lock file** (`fcntl.flock`) decides who the single instance is. The OS
  releases it automatically if the app crashes, so there is no stale PID file.
- The **Unix socket** is only for talking to that instance. The CLI sends a
  short text command (`show`, `config-changed`, `quit`) and waits up to 2
  seconds for an `ok` reply.
- If the socket path can't be used (unwritable folder, path too long), both
  sides fall back to `/tmp/break-reminder-<uid>/break-reminder.sock`.

### Inside the GUI

- **Threads:** Tkinter is not thread-safe, so only the main thread touches
  widgets. Two background threads exist: one accepts socket connections, one
  downloads the image. They hand results to the main thread through
  `queue.Queue`s, which the main thread checks every 100 ms.
- **Timer:** uses Tkinter's `after()`, plus a once-a-second refresh that also
  compares against the wall clock. `after()` pauses while the laptop is
  suspended, so without that check the popup would never fire after resume.
- **Stale downloads:** each break gets a request id. If you cancel or restart
  while an image is downloading, the late result is ignored.
- **Images from the internet are treated as untrusted:** only http(s) URLs;
  PNG/JPEG/GIF/WEBP only (checked by file contents); max 10 MB and 25 million
  pixels; DuckDuckGo safe search on; results that look AI-generated are
  filtered out on a best-effort basis (keyword match, so some will get
  through).
- **Config safety:** writes go to a temp file, are flushed to disk with
  `fsync`, then atomically renamed over `config.json`. A lock serialises
  read-modify-write. A corrupt or wrongly-typed config falls back to defaults
  and is backed up instead of crashing the app.

## Development

```bash
uv sync                  # create .venv and install dependencies
uv run pytest            # run the tests
uv run ruff check .      # lint
uv run python -m break_reminder.cli --help
```

Run the GUI directly from source (without installing):

```bash
uv run python -m break_reminder.main
```

Note: an installed `break-reminder` and a source run share the same lock and
socket, so stop one (`break-reminder quit`) before running the other.

### Packaging

`pyproject.toml` uses `hatchling` as the build backend and declares one entry
point:

```toml
[project.scripts]
break-reminder = "break_reminder.cli:main"
```

`uv build` produces a wheel (`.whl`) and a source archive (`.tar.gz`) in
`dist/`. The wheel includes the `assets/` images.

## Uninstalling

```bash
break-reminder quit
break-reminder autostart disable
uv tool uninstall break-reminder
rm -rf ~/.config/break-reminder      # optional: removes settings and logs
```
