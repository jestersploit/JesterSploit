#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from datetime import datetime, timezone
from utils.logger import capture_log
from utils.hardware import interface, gpu_available, gpu_name
from core.wordlist import current_wordlists


def generate_report():
    """Generate comprehensive operation report."""
    from utils.logger import SESSION_ID
    report_path = f"/tmp/jester_report_{SESSION_ID}.txt"
    with open(report_path, 'w') as f:
        f.write("=" * 60 + "\n")
        f.write("JESTERSPLOIT OPERATION REPORT\n")
        f.write("=" * 60 + "\n")
        f.write(f"Session ID: {SESSION_ID}\n")
        f.write(f"Timestamp: {datetime.now(timezone.utc).isoformat()}\n")
        f.write(f"Interface: {interface}\n")
        f.write(f"GPU: {gpu_name if gpu_available else 'None'}\n")
        f.write(f"Wordlists ({len(current_wordlists)}):\n")
        for wl in current_wordlists:
            f.write(f"  - {wl}\n")
        f.write("-" * 60 + "\n\n")
        f.write("CAPTURED INTELLIGENCE\n")
        f.write("-" * 40 + "\n")
        for entry in capture_log:
            f.write(f"[{entry['timestamp']}] {entry['event']}\n")
            f.write(f"  BSSID: {entry.get('bssid', 'N/A')}\n")
            f.write(f"  File: {entry.get('file', 'N/A')}\n")
            f.write(f"  SHA256: {entry.get('sha256', 'N/A')}\n\n")
    print(f"[+] Report generated: {report_path}")
    return report_path
