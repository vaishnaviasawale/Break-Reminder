import fcntl
import json
import os
import shutil
import tempfile
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "break-reminder"

CONFIG_FILE = CONFIG_DIR / "config.json"

LOG_NAME = "break-reminder.log"

LOCK_NAME = "config.lock"

BACKUP_NAME = "config.json.bak"

DEFAULT_CONFIG = {
    "enabled": True,
}


def ensure_config_exists():
    CONFIG_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    if CONFIG_FILE.exists():
        return

    # Write the defaults to a temp file first, then hard-link it into place.
    # os.link fails if CONFIG_FILE already exists, so two processes starting
    # together can't clobber each other (or a config saved in between), and
    # readers never see a half-written file.
    tmp_path = _write_temp(DEFAULT_CONFIG)
    try:
        os.link(tmp_path, CONFIG_FILE)
    except FileExistsError:
        pass
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def _write_temp(config):
    # Write JSON to a temp file in CONFIG_DIR and return its path.
    fd, tmp_path = tempfile.mkstemp(dir=CONFIG_DIR, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as tmp_file:
            json.dump(config, tmp_file, indent=4)
            # Force the data to disk before the file is renamed into place,
            # so a power loss can't leave an empty config.json.
            tmp_file.flush()
            os.fsync(tmp_file.fileno())
    except BaseException:
        Path(tmp_path).unlink(missing_ok=True)
        raise
    return tmp_path


def log_warning(message, level="WARNING"):
    # Both the CLI and the GUI go through load_config, so one log file
    # next to config.json covers both. Logging must never crash the app.
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with (CONFIG_DIR / LOG_NAME).open("a") as log:
            timestamp = datetime.now().astimezone().isoformat(timespec="seconds")
            log.write(f"{timestamp} {level} {message}\n")
    except OSError:
        pass


def _backup_corrupt_config():
    # enable()/disable() save whatever load_config returned, which for a
    # corrupt file is the defaults. Keep a copy of the bad file so the user's
    # settings can still be recovered by hand. Copy rather than rename so a
    # read never removes config.json out from under another process.
    backup = CONFIG_DIR / BACKUP_NAME
    try:
        shutil.copy2(CONFIG_FILE, backup)
    except OSError as error:
        log_warning(f"Could not back up {CONFIG_FILE}: {error}")
        return
    log_warning(f"Backed up corrupt config to {backup}")


def load_config():
    try:
        ensure_config_exists()
    except OSError as error:
        log_warning(f"Could not create {CONFIG_FILE}, using defaults: {error}")
        return dict(DEFAULT_CONFIG)

    try:
        loaded = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        # json.loads is different from json.load
        # It reads the JSON {"enabled": true} to
        # {"enabled": True}
    except (ValueError, OSError) as error:
        # ValueError covers both JSONDecodeError and UnicodeDecodeError
        log_warning(f"Could not read {CONFIG_FILE}, using defaults: {error}")
        if isinstance(error, ValueError):
            _backup_corrupt_config()
        return dict(DEFAULT_CONFIG)

    if not isinstance(loaded, dict):
        log_warning(f"{CONFIG_FILE} is not a JSON object, using defaults")
        _backup_corrupt_config()
        return dict(DEFAULT_CONFIG)

    missing = sorted(DEFAULT_CONFIG.keys() - loaded.keys())
    if missing:
        log_warning(
            f"{CONFIG_FILE} is missing {', '.join(missing)}, using defaults"
        )

    if "enabled" in loaded and not isinstance(loaded["enabled"], bool):
        log_warning(
            f"{CONFIG_FILE}: 'enabled' must be true or false, using default"
        )
        del loaded["enabled"]

    # Defaults fill in any missing keys
    return {**DEFAULT_CONFIG, **loaded}


def save_config(config):
    ensure_config_exists()

    # Write to a temp file in the same directory, then swap it into place.
    # os.replace is atomic, so a crash mid-write can never leave a
    # truncated config.json behind.
    _remove_stale_temp_files()
    tmp_path = _write_temp(config)
    try:
        os.replace(tmp_path, CONFIG_FILE)
    except BaseException:
        Path(tmp_path).unlink(missing_ok=True)
        raise
    _fsync_dir(CONFIG_DIR)


def _fsync_dir(directory):
    # Persist the rename itself. Best effort: not all platforms allow
    # opening a directory.
    try:
        fd = os.open(directory, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(fd)
    except OSError:
        pass
    finally:
        os.close(fd)


def _remove_stale_temp_files(max_age_seconds=3600):
    # A process killed between mkstemp and os.replace leaves a *.tmp file
    # behind. Only delete old ones so a write in progress in another
    # process is never touched.
    cutoff = time.time() - max_age_seconds
    try:
        for path in CONFIG_DIR.glob("*.tmp"):
            try:
                if path.stat().st_mtime < cutoff:
                    path.unlink(missing_ok=True)
            except OSError:
                pass
    except OSError:
        pass


def is_enabled():
    config = load_config()
    return config["enabled"]


@contextmanager
def _config_lock():
    # Serialize read-modify-write cycles across processes. The lock is on a
    # separate file because save_config swaps config.json's inode with
    # os.replace, which would silently drop a lock held on config.json.
    # flock is released when the file closes, even if the process dies.
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_DIR / LOCK_NAME, "a") as lock_file:
        fcntl.flock(lock_file, fcntl.LOCK_EX)
        yield


def _set_enabled(value):
    with _config_lock():
        config = load_config()
        config["enabled"] = value
        save_config(config)


def enable():
    _set_enabled(True)


def disable():
    _set_enabled(False)


def status():
    if is_enabled():
        print("Break reminder is enabled")
    else:
        print("Break reminder is disabled")
