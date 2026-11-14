# My Learning: building Break Reminder

Notes on the technologies in this app, why I chose what I chose, and what I
would watch out for next time. 

---

## 1. The big picture

A break reminder looks like a 50-line script: a timer and a popup. It grew
because real use exposed real problems: duplicate windows, a laptop going to
sleep, a corrupt config file, a slow image download. 

The final design:

- `main.py`: a long-running GUI process (Tkinter).
- `cli.py`: a short-lived command that controls the GUI.
- `ipc.py`: a Unix socket linking the two.
- `config.py`, `autostart.py`: small, careful file handling.
- Packaged with `uv`/`hatchling` and installed as a command.

---

## 2. Python project structure and packaging

### What I learned

- A **package** is a folder of modules with an `__init__.py`. Mine is
  `src/break_reminder/`.
- The **`src/` layout** keeps the code out of the project root. Tests can't
  accidentally import the local folder instead of the installed package, so
  packaging mistakes show up early.
- **`pyproject.toml`** is the single config file: name, version, dependencies,
  entry points, build system, tool settings (ruff, pytest).
- **Entry points** turn a function into a command:
  ```toml
  [project.scripts]
  break-reminder = "break_reminder.cli:main"
  ```
  On install, a small launcher script called `break-reminder` is created that
  imports `break_reminder.cli` and calls `main()`.
- **Absolute imports** (`from break_reminder import config`) work once the
  code is a package. Running `python cli.py` directly stops working, so I run
  `python -m break_reminder.cli` or use the installed command.
- **Package data:** the fallback PNGs live inside the package and are found
  with `Path(__file__).parent / "assets"`. I confirmed the built wheel
  contains them (about 9 MB in total, so the images are large).

### Build and distribution

- A **wheel** (`.whl`) is a prebuilt, ready-to-unpack zip. A **sdist**
  (`.tar.gz`) is the source archive that can be built into a wheel. `uv build`
  makes both in `dist/`.
- **`hatchling`** is the build backend: the tool that turns the project into
  those files. `[tool.hatch.build.targets.wheel] packages = [...]` tells it
  where the code is.
- **Stale `dist/` folders** hold old builds. Delete `dist/` before building so
  nothing old gets installed by accident.
- **Same version, new code:** installers may reuse a cached build if the
  version number doesn't change. That is why updating uses `--reinstall`, or
  bumping the version.

### Trade-offs

| Choice | Why | Cost |
| ------ | --- | ---- |
| Wheel installed as a tool | Real command on `PATH`, works from anywhere, autostart has a stable path | Must rebuild and reinstall to see changes (use `uv run` while developing) |
| `src/` layout | Catches packaging bugs | Slightly more setup |
| Large PNG fallbacks inside the wheel | Works offline | 9 MB package; smaller or compressed images would help |
| `requires-python >= 3.14` | Matches what I develop with | Excludes anyone on older Python; looser pin would widen reach |

---

## 3. uv

### What I learned

`uv` is one tool replacing several: `pip`, `venv`, `pipx`, `pip-tools`.

| Command | What it does |
| ------- | ------------ |
| `uv sync` | Create `.venv`, install exactly what `uv.lock` says |
| `uv run pytest` | Run a command inside the project environment |
| `uv build` | Build wheel + sdist |
| `uv tool install .` | Install the app as a global command in its own isolated environment |
| `uv tool list` / `uninstall` | Manage installed tools |

- **`uv.lock`** records exact versions of every dependency, so every machine
  builds the same environment. Commit it for applications.
- **`uv tool`** gives each app its own virtualenv under
  `~/.local/share/uv/tools/<name>/`, and symlinks the command into
  `~/.local/bin`. That's why my installed app doesn't see my project's `.venv`,
  and why the running app doesn't change when I edit source.
- **Two copies of the app exist:** the installed one (what autostart runs) and
  the source tree. Editing code does not change the installed app until I
  reinstall.

---

## 4. Tkinter (the GUI)

### Concepts

- **Event loop:** `root.mainloop()` runs forever, waiting for events (clicks,
  key presses, timers). Everything in the GUI is a callback the loop runs. A
  callback must finish quickly, or the window freezes.
- **Widgets and layout:** `Label`, `Entry`, `Button`, `Checkbutton`, placed with
  `.pack()`.
- **Callbacks:** `command=start_timer` passes the function itself. Writing
  `start_timer()` would call it immediately. `bind("<Return>", ...)` passes an
  event argument, so I wrap it: `lambda event: start_timer()`.
- **`root.after(ms, func)`:** schedule a function on the event loop. It returns
  an id I keep so I can `after_cancel` it (needed when the user starts a new
  timer or disables the reminder).
- **`root.withdraw()` / `deiconify()` / `lift()` / `focus_force()`:** hide the
  window, show it, bring it to the front, give it focus.
- **`protocol("WM_DELETE_WINDOW", root.withdraw)`:** closing the window hides it
  instead of quitting, so the timer keeps running.
- **`tk.BooleanVar`:** a checkbox can't hold a plain Python `bool`; it reads and
  writes through a Tk variable.
- **Keeping a reference to images:** `image_label.image = photo`. Tkinter does
  not keep the image alive by itself. Without this reference Python's garbage
  collector frees it and the image disappears.

### Threads and Tkinter

The most important rule: **Tkinter is not thread-safe. Only the main thread
may touch widgets.**

My problem: downloading an image is slow (network). Doing it on the main thread
froze the whole window ("Prevent UI freezes when image downloads" in the git
history).

My solution:

```
main thread (Tk)               worker thread
      |  start thread --------->  download + decode image (PIL)
      |                                  |
      |   poll_images() every 100 ms     v
      |  <------ image_queue.put((id, image, title))
      v
  create PhotoImage, update widgets
```

- The worker produces a **PIL image**, never a Tk `PhotoImage` (that is a Tk
  object and must be created on the main thread).
- `queue.Queue` is the safe handoff. The main thread polls with
  `get_nowait()` using `root.after`.
- The socket server runs in another thread and uses the same pattern with
  `command_queue`.
- A **request id** protects against stale results. If a newer break started
  (or it was cancelled), old results are dropped.
- A **3-second deadline** (`IMAGE_DEADLINE_MS`) shows a local fallback image if
  the network is slow, so the popup never waits on the internet.
- `daemon=True` threads die automatically when the app exits.

### Time, sleep and clocks

- `after()` uses a **monotonic clock** that doesn't count time spent suspended.
  If you close the laptop lid, the countdown pauses.
- The deadline I show the user is **wall-clock** time.
- Fix: the once-a-second refresh checks `datetime.now() >= timer_end_time` and
  fires the break if the deadline has passed ("Prevent timer drift after
  suspend").
- **Rule of thumb:** monotonic time measures durations; wall-clock time
  answers "what time is it?". Mixing them causes bugs on suspend/resume.

### Trade-offs

| Choice | Why | Cost |
| ------ | --- | ---- |
| Tkinter | Ships with Python, no extra dependency, enough for one small window | Dated look; limited layout tools; the Fedora package must be installed separately |
| Module-level globals for widgets | Simple for a small script, avoids passing state around | Harder to test and reason about; a class (`App`) would be cleaner as it grows |
| Polling queues every 100 ms | Easy and safe | Tiny constant wake-up cost; up to 100 ms latency |
| Fixed 700x700 window | Predictable | Not responsive on small screens |

---

## 5. Sockets and IPC (inter-process communication)

### The problem

`break-reminder enable` is a **different process** from the running GUI.
Processes have separate memory, so the CLI can't call a function in the GUI. It
needs a communication channel. Options I weighed:

| Mechanism | Verdict |
| --------- | ------- |
| PID file + signals | Stale PID files after a crash; signals carry no message |
| TCP port on localhost | Works, but opens a network port: port clashes, firewall prompts, other local users could connect |
| D-Bus | The "proper" desktop way, but adds a dependency and is more complex |
| **Unix domain socket** | Local only, no port, protected by file permissions, simple. Chosen |

### What I learned

- A **socket** is an endpoint for two-way communication. `AF_UNIX` sockets live
  at a **file path** (`~/.config/break-reminder/break-reminder.sock`) instead
  of an IP address and port.
- **Server side** (GUI): `bind(path)` -> `listen()` -> loop `accept()` ->
  `recv()` -> reply.
  **Client side** (CLI): `connect(path)` -> `sendall()` -> `recv()`.
- `SOCK_STREAM` is a reliable byte stream (like TCP). Messages are just short
  strings: `show`, `config-changed`, `quit`.
- **Acknowledgements:** the GUI replies `ok`. Without a reply, the CLI can't
  tell "GUI acted on it" from "GUI is hung". I added `ACK` and a **2-second
  timeout** so a frozen GUI doesn't freeze the CLI.
- **Stale socket files:** if the app crashes, the socket file is left behind
  and `bind` fails with "address already in use". The GUI unlinks any old file
  before binding. The CLI deliberately does *not* delete the file on a failed
  connect, because "connection refused" can also mean the GUI has bound but not
  yet called `listen()`.
- **Path limit:** `AF_UNIX` paths can only be about 107 bytes. If the
  preferred path is too long or unwritable, both sides independently compute
  the same fallback (`/tmp/break-reminder-<uid>/...`) so they still agree.
- **Security:** the socket directory is created with mode `0700`, and the shared
  `/tmp` fallback checks the directory is owned by me, so another user can't
  pre-create it and intercept commands.
- **Retries:** binding retries a few times to ride out transient errors, and
  failures are logged instead of crashing.

### Trade-offs

- Simple text protocol: easy to debug, but no versioning or structure. If
  commands needed arguments I would switch to JSON.
- One message per connection: simple, but not suited to streaming updates.
- `listen(1)` allows a small backlog, which is fine for one human typing
  commands.

---

## 6. File locking and "only one instance"

### What I learned

- A **socket does not guarantee a single instance.** It's just a channel.
  Two GUIs starting at the same moment could both try to run.
- **`fcntl.flock(file, LOCK_EX | LOCK_NB)`** takes an exclusive lock on a file.
  `LOCK_NB` means "don't wait, fail now". A second process gets
  `BlockingIOError` and knows an instance exists.
- **The OS releases the lock when the process dies**, even on a crash or
  `kill -9`. A PID file can't promise that.
- The lock object must stay alive for the whole run. If it's garbage-collected,
  the file closes and the lock disappears.
- A second lock (`config.lock`) serialises **read-modify-write** on the config,
  so the CLI and GUI can't clobber each other's changes ("Add lock for
  read-modify-write to config").

### Trade-offs

- `fcntl` is **Unix-only**, so the app doesn't run on Windows. Acceptable for a
  Fedora/GNOME tool; a portable version would need another approach.
- Advisory locks only work if every process cooperates, which is fine because
  I control all of them.

---

## 7. Safe file handling (config and autostart)

Losing or corrupting a user's settings file is a bad bug even for a tiny app.

### Atomic writes

Never write straight into the real file. If the program or machine dies
halfway, you get an empty or half-written file.

```
write new content -> temp file (same folder)
flush + fsync     -> force it to disk
os.replace(temp, real)   -> atomic swap; readers see old or new, never partial
fsync the folder  -> make the rename itself durable
```

Same folder matters: `os.replace` is only atomic within one filesystem.

### Other details I handled

- `os.link` for creating the default config is atomic and fails if the file
  already exists, so two processes can't both write defaults.
- Corrupt JSON, invalid UTF-8, a non-object value, or `"enabled": "yes"` all
  fall back to defaults. Corrupt files are copied to `config.json.bak` first,
  so nothing is silently destroyed.
- Stale `.tmp` files from crashes are cleaned up.
- A **log file** records warnings, so "it silently used defaults" is
  discoverable.
- The `.desktop` autostart file has special quoting rules: spaces and symbols
  in `Exec=` must be quoted/escaped, and a literal `%` must be `%%`.

### Trade-offs

More code than `json.dump(open(...))`, and harder to read. Worth it for
user-owned data, overkill for throwaway scripts. Tests cover these paths, which
is what keeps the complexity safe to change.

---

## 8. Linux desktop integration (autostart)

- GNOME reads `.desktop` files in `~/.config/autostart/` at every login and
  runs their `Exec=` line. Creating or deleting that file is how "Start at
  login" works. No root and no systemd needed.
- **Use the installed command path** (`shutil.which("break-reminder")` gives
  `~/.local/bin/break-reminder`), not a path into the project's `.venv`. The
  project folder can move or be deleted, and the installed command stays valid.
- **Autostart vs reminder-enabled** are two independent settings
  (`.desktop` file vs `config.json`). I wrote a test matrix to prove changing
  one doesn't affect the other.
- **Alternatives:** a systemd user service (restarts on crash, journald logs,
  but more setup) or a GNOME extension. XDG autostart is simplest and works on
  most desktops.

---

## 9. Calling the internet safely (requests, DuckDuckGo, Pillow)

Images from the internet are **untrusted input**.

- **`requests`** with `timeout=5` always. The default is no timeout, which can
  hang forever.
- **`stream=True`** + chunked reading + a 10 MB cap, so a huge response can't
  exhaust memory.
- **Pillow** `Image.open(..., formats=[...])` checks the actual file
  contents against an allow-list instead of trusting the extension or
  `Content-Type`.
- A **pixel-count limit** guards against "decompression bombs": small files
  that decode to enormous images.
- `image.load()` forces a full decode inside the `try` block, so corrupt files
  fail early, not later inside Tkinter.
- **Only `http(s)` URLs**, so `file://` and other schemes are refused.
- **`ddgs`** (DuckDuckGo search) has no API key, but it's unofficial and can
  break or rate-limit. That's why there's a layered fallback:
  xkcd/DDG -> bundled images -> text only. The popup must always appear.
- **AI-image filtering is keyword matching** on titles and URLs. It is
  best-effort, and the README says so rather than overpromising.
- `except Exception` is normally a smell, but here it is deliberate at the
  boundary where *any* failure must degrade to the fallback. I marked it with
  `# noqa` so the choice is visible.

---

## 10. Testing

- **`pytest`** with 5 test files (about 2,300 lines), more than the code
  itself. Testing was where I found many of the edge cases.
- `pythonpath = ["src"]` lets tests import the package.
- Tests **mock** the outside world (network, sockets, files, Tk widgets) so
  they're fast and repeatable.
- Bugs that need a real desktop (suspend/resume, lock screen, reboot,
  autostart) can't be unit-tested. `tests/test_notes.txt` is my **manual test
  checklist** for those.


## 11. Linting and tools

- **`ruff`** is a fast linter/formatter (line length 80 here). The `# noqa`
  comments mark deliberate rule exceptions.
- **`git`**: small, focused commits with descriptive messages ("Fix corrupt
  config overwriting") make history readable and bugs easy to bisect.
- `.gitignore` keeps `.venv`, caches and `__pycache__` out of the repo.


---

## 12. Design principles I take away

1. **Make failure harmless.** The popup must show even without internet; a bad
   config must not crash the app; a crash mid-write must not lose data.
2. **Single source of truth.** One lock decides ownership; one config file
   holds state; `RUNTIME_DIR` is defined once ("Define runtime dir only once").
3. **Don't trust inputs.** Config files, network data and socket messages can
   all be wrong.
4. **Keep the UI thread free.** Slow work goes in a worker thread; results come
   back through a queue.
5. **Prefer simple, local, OS-provided mechanisms** (file locks, Unix sockets,
   `.desktop` files) over extra dependencies.
6. **Tell the truth in docs.** Best-effort features are described as
   best-effort.
7. **Tests plus a manual checklist.** Automate what you can; write down what
   you can't.


## 13. Glossary

- **Process:** a running program with its own memory.
- **Thread:** a parallel path of execution inside one process (shared memory).
- **Event loop:** a loop that waits for events and runs callbacks.
- **IPC:** inter-process communication.
- **Unix domain socket:** local two-way channel addressed by a file path.
- **Daemon thread:** a background thread that doesn't keep the program alive.
- **Atomic:** happens completely or not at all, with no visible middle state.
- **`fsync`:** ask the OS to physically write buffered data to disk.
- **Wheel / sdist:** built / source distribution formats for Python packages.
- **Entry point:** a name that maps a command to a Python function.
- **Monotonic clock:** a clock that only moves forward, unaffected by clock
  changes (but paused during suspend here).
- **`.desktop` file:** a Linux file describing how to launch an application.
