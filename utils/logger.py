#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import os
import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

# Global capture log (list of entries)
capture_log = []

SESSION_ID = None  # will be set by main

attack_logger = None
bug_logger = None
engine_logger = None


def setup_loggers(session_id: str) -> None:
    """Initialize loggers with session ID."""
    global SESSION_ID, attack_logger, bug_logger, engine_logger
    SESSION_ID = session_id

    # Ensure log directories exist
    for sub in ["attacks", "bugs", "engine"]:
        Path(f"data/logs/{sub}").mkdir(parents=True, exist_ok=True)

    attack_logger = logging.getLogger("attack")
    attack_logger.setLevel(logging.INFO)
    attack_handler = logging.FileHandler(f"data/logs/attacks/attack_{SESSION_ID}.log")
    attack_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
    attack_logger.addHandler(attack_handler)

    bug_logger = logging.getLogger("bug")
    bug_logger.setLevel(logging.ERROR)
    bug_handler = logging.FileHandler(f"data/logs/bugs/bug_{SESSION_ID}.log")
    bug_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
    bug_logger.addHandler(bug_handler)

    engine_logger = logging.getLogger("engine")
    engine_logger.setLevel(logging.INFO)
    engine_handler = logging.FileHandler(f"data/logs/engine/engine_{SESSION_ID}.log")
    engine_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
    engine_logger.addHandler(engine_handler)


def log_capture(event_type: str, bssid: str, essid: str, file_path: Optional[str]) -> str:
    """Log capture event with SHA256."""
    sha256 = None
    if file_path and os.path.exists(file_path):
        with open(file_path, 'rb') as f:
            sha256 = hashlib.sha256(f.read()).hexdigest()
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "session_id": SESSION_ID,
        "event": event_type,
        "bssid": bssid,
        "essid": essid,
        "file": file_path,
        "sha256": sha256
    }
    capture_log.append(entry)
    # Write to report file
    report_file = f"/tmp/jester_report_{SESSION_ID}.jsonl"
    with open(report_file, 'a') as f:
        f.write(json.dumps(entry) + '\n')
    if attack_logger:
        attack_logger.info(f"{event_type}: {bssid} {essid} {file_path}")
    return sha256
