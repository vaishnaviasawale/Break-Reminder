import json
from datetime import datetime
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "break-reminder"

CONFIG_FILE = CONFIG_DIR / "config.json"

LOG_NAME = "break-reminder.log"

DEFAULT_CONFIG = {
    "enabled": True,
}


def ensure_config_exists():
    CONFIG_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    if not CONFIG_FILE.exists():
        CONFIG_FILE.write_text(
            json.dumps(
                DEFAULT_CONFIG,
                indent=4,
            )
            # json.dumps is different from json.dump
            # It turns config = {"enabled": True}
            # {"enabled": true} as a string
        )


def log_warning(message):
    # Both the CLI and the GUI go through load_config, so one log file
    # next to config.json covers both. Logging must never crash the app.
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with (CONFIG_DIR / LOG_NAME).open("a") as log:
            timestamp = datetime.now().astimezone().isoformat(timespec="seconds")
            log.write(f"{timestamp} WARNING {message}\n")
    except OSError:
        pass


def load_config():
    ensure_config_exists()

    try:
        loaded = json.loads(CONFIG_FILE.read_text())
        # json.loads is different from json.load
        # It reads the JSON {"enabled": true} to
        # {"enabled": True}
    except (json.JSONDecodeError, OSError) as error:
        log_warning(f"Could not read {CONFIG_FILE}, using defaults: {error}")
        return dict(DEFAULT_CONFIG)

    if not isinstance(loaded, dict):
        log_warning(f"{CONFIG_FILE} is not a JSON object, using defaults")
        return dict(DEFAULT_CONFIG)

    # Defaults fill in any missing keys
    return {**DEFAULT_CONFIG, **loaded}


def save_config(config):
    ensure_config_exists()

    CONFIG_FILE.write_text(
        json.dumps(
            config,
            indent=4,
        )
    )


def is_enabled():
    config = load_config()
    return config["enabled"]


def enable():
    config = load_config()
    config["enabled"] = True
    save_config(config)


def disable():
    config = load_config()
    config["enabled"] = False
    save_config(config)


def status():
    if is_enabled():
        print("Break reminder is enabled")
    else:
        print("Break reminder is disabled")
