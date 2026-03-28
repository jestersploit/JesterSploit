#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import subprocess
import time
import re
import os
from typing import List, Dict

from utils.hardware import interface, monitor_interface, hardware_available, adapter_detected
from utils.interface import enable_monitor_mode
from utils.status import print_status, ProgressDisplay
from utils.process import active_processes, add_process, remove_process, is_cancelled, set_cancel_flag
from utils.validator import validate_file
from utils.logger import log_capture


def start_scan(duration: int = 30) -> List[Dict]:
    """Full spectrum reconnaissance with progress display."""
    if not hardware_available or not adapter_detected:
        print_status("No USB adapter detected", "error")
        return []

    set_cancel_flag(False)
    print_status(f"Starting spectral scan ({duration}s)...", "info")

    mon_iface = enable_monitor_mode(interface)
    if not mon_iface:
        print_status("Monitor mode failed", "error")
        return []

    output_file = f"/tmp/scan_{os.environ.get('SESSION_ID', 'unknown')}"
    cmd = ["airodump-ng", "-w", output_file, "--output-format", "csv",
           "--band", "abg", mon_iface]
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    add_process(proc)

    progress = ProgressDisplay()
    progress.start(f"Scanning networks", duration)

    for i in range(duration):
        if is_cancelled():
            progress.stop()
            print_status("Scan cancelled", "warning")
            break
        time.sleep(1)
        progress.update(i + 1)

    progress.stop()
    proc.terminate()
    proc.wait()
    remove_process(proc)

    networks = []
    csv_file = f"{output_file}-01.csv"
    if os.path.exists(csv_file):
        with open(csv_file, 'r', errors='ignore') as f:
            lines = f.readlines()
        in_networks = False
        for line in lines:
            if "Station MAC" in line:
                break
            if "BSSID" in line:
                in_networks = True
                continue
            if in_networks and line.strip() and ',' in line:
                parts = [p.strip() for p in line.split(',')]
                if len(parts) >= 14 and parts[0] and ':' in parts[0]:
                    bssid = parts[0].upper()
                    if not re.match(r'^([0-9A-F]{2}:){5}[0-9A-F]{2}$', bssid):
                        continue
                    network = {
                        "bssid": bssid,
                        "essid": parts[13].strip('"') if len(parts) > 13 and parts[13] else "[Hidden]",
                        "channel": parts[3].strip() if len(parts) > 3 else "1",
                        "security": parts[5].strip() if len(parts) > 5 else "Unknown",
                        "signal": parts[8].strip() if len(parts) > 8 else "0",
                        "manufacturer": get_manufacturer(bssid)  # implement get_manufacturer elsewhere
                    }
                    networks.append(network)

    print_status(f"Scan complete: {len(networks)} networks detected", "success")
    return networks


def get_manufacturer(mac: str) -> str:
    """Simple OUI lookup (simplified)."""
    oui = mac[:8].upper()
    # Placeholder – you can expand with a real OUI database
    return "Unknown"
