
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
from typing import Any, Dict

CONFIG_FILE = os.path.expanduser("~/.jesterphishing.json")

# Default configuration
DEFAULT_CONFIG: Dict[str, Any] = {
    "telegram": {"token": None, "chat_id": None, "enabled": False},
    "wordlists": ["/usr/share/wordlists/rockyou.txt"],
    "hardware": {
        "channel_hopping": True,
        "5ghz_enabled": True,
        "deauth_count": 10,
        "scan_duration": 60,
        "pmkid_timeout": 60,
        "handshake_timeout": 35
    },
    "cracking": {
        "gpu_enabled": True,
        "max_crack_time": 600,
        "auto_crack_after_capture": True
    },
    "telegram_settings": {
        "notify_on_capture": True,
        "notify_on_crack": True,
        "progress_updates": True
    },
    "logging": {
        "forensic_logging": True,
        "save_captures": True,
        "capture_dir": "data/captures"
    },
    "first_run_done": False,
    "version": "3.0.0"
}

config = DEFAULT_CONFIG.copy()


def load_config() -> None:
    """Load configuration from file, merging with defaults."""
    global config
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                loaded = json.load(f)
                # Deep merge for nested dicts
                for key in loaded:
                    if key in config:
                        if isinstance(config[key], dict) and isinstance(loaded[key], dict):
                            config[key].update(loaded[key])
                        else:
                            config[key] = loaded[key]
                print(f"[*] Loaded configuration from {CONFIG_FILE}")
        except Exception as e:
            print(f"[!] Failed to load config: {e}")


def save_config() -> None:
    """Save current configuration to file."""
    try:
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        os.chmod(CONFIG_FILE, 0o600)
    except Exception as e:
        print(f"[!] Failed to save config: {e}")
