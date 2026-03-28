#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import subprocess
from typing import Optional

from .hardware import hardware_available, adapter_detected, interface, monitor_interface, VALID_CHANNELS
from .status import print_status


def enable_monitor_mode(interface_name: str) -> Optional[str]:
    """Enable monitor mode with multiple fallback methods."""
    global monitor_interface
    if not hardware_available or not adapter_detected:
        print_status("No USB adapter detected", "error")
        return None

    print_status(f"Enabling monitor mode on {interface_name}...", "info")
    for attempt in range(3):
        # Method 1: airmon-ng
        try:
            subprocess.run(["airmon-ng", "check", "kill"], capture_output=True, timeout=10)
            time.sleep(1)
            result = subprocess.run(["airmon-ng", "start", interface_name],
                                   capture_output=True, text=True, timeout=15)
            for line in result.stdout.split('\n'):
                if 'mon' in line and interface_name in line:
                    parts = line.split()
                    for part in parts:
                        if 'mon' in part or part == f"{interface_name}mon":
                            monitor_interface = part
                            break
            if not monitor_interface:
                monitor_interface = f"{interface_name}mon"
            time.sleep(2)
            iwconfig = subprocess.run(['iwconfig', monitor_interface],
                                     capture_output=True, text=True, timeout=5)
            if 'Monitor' in iwconfig.stdout:
                print_status(f"Monitor mode enabled: {monitor_interface}", "success")
                return monitor_interface
        except Exception as e:
            print_status(f"Attempt {attempt + 1} failed: {e}", "warning")

        # Method 2: iw
        try:
            subprocess.run(['ip', 'link', 'set', interface_name, 'down'], capture_output=True, timeout=5)
            subprocess.run(['iw', 'dev', interface_name, 'set', 'type', 'monitor'],
                          capture_output=True, timeout=5)
            subprocess.run(['ip', 'link', 'set', interface_name, 'up'], capture_output=True, timeout=5)
            monitor_interface = interface_name
            print_status(f"Monitor mode enabled (iw): {monitor_interface}", "success")
            return monitor_interface
        except Exception:
            pass

        # Method 3: create monitor interface
        try:
            mon_name = f"{interface_name}mon"
            subprocess.run(['iw', 'dev', interface_name, 'interface', 'add', mon_name, 'type', 'monitor'],
                          capture_output=True, timeout=5)
            subprocess.run(['ip', 'link', 'set', mon_name, 'up'], capture_output=True, timeout=5)
            monitor_interface = mon_name
            print_status(f"Monitor interface created: {monitor_interface}", "success")
            return monitor_interface
        except Exception:
            pass

        time.sleep(2)

    print_status("Failed to enable monitor mode", "error")
    return None


def disable_monitor_mode() -> None:
    """Disable monitor mode and clean up."""
    global monitor_interface
    if monitor_interface:
        try:
            subprocess.run(['airmon-ng', 'stop', monitor_interface],
                          capture_output=True, timeout=10)
        except Exception:
            pass
        monitor_interface = None


def set_channel(channel: str) -> bool:
    """Set channel on monitor interface with validation."""
    global monitor_interface
    valid, _, warning = validate_channel(channel)  # from validator
    if not valid:
        print_status(warning, "error")
        return False
    if warning:
        print_status(warning, "warning")
    if monitor_interface:
        subprocess.run(["iw", "dev", monitor_interface, "set", "channel", str(channel)], capture_output=True)
        subprocess.run(["iwconfig", monitor_interface, "channel", str(channel)], capture_output=True)
    return True
