import json
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "break-reminder"

CONFIG_FILE = CONFIG_DIR / "config.json"

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

def load_config():
    ensure_config_exists()

    return json.loads(
        CONFIG_FILE.read_text()
    )
    # json.loads is different from json.load
    # It reads the JSON {"enabled": true} to
    # {"enabled": True}

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
        print("Enabled")
    else:
        print("Disabled")