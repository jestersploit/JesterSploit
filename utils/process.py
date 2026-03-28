#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import threading
import subprocess
import signal
import atexit
import sys
from typing import List

# Global list of active subprocesses
active_processes: List[subprocess.Popen] = []

# Cancellation flag for long operations
operation_cancel_flag = threading.Event()


def add_process(proc: subprocess.Popen) -> None:
    """Add a subprocess to the global tracking list."""
    if proc not in active_processes:
        active_processes.append(proc)


def remove_process(proc: subprocess.Popen) -> None:
    """Remove a subprocess from the global tracking list."""
    if proc in active_processes:
        active_processes.remove(proc)


def kill_all_processes() -> None:
    """Terminate all tracked processes and kill common attack tools."""
    operation_cancel_flag.set()
    for proc in active_processes[:]:
        try:
            proc.terminate()
            proc.wait(timeout=2)
        except:
            try:
                proc.kill()
            except:
                pass
    active_processes.clear()
    for name in ['airodump-ng', 'hcxdumptool', 'aireplay-ng', 'hostapd', 'dnsmasq',
                 'hashcat', 'bully', 'reaver', 'airbase-ng', 'bettercap', 'tcpdump']:
        try:
            subprocess.run(['pkill', '-f', name], capture_output=True, timeout=2)
        except:
            pass


def kill_attack_processes() -> None:
    """Convenience function to kill attack processes."""
    kill_all_processes()


def set_cancel_flag(val: bool) -> None:
    """Set or clear the cancellation flag."""
    if val:
        operation_cancel_flag.set()
    else:
        operation_cancel_flag.clear()


def is_cancelled() -> bool:
    """Return True if the cancellation flag is set."""
    return operation_cancel_flag.is_set()


def cleanup() -> None:
    """Clean up on exit."""
    kill_all_processes()


atexit.register(cleanup)


def setup_signal_handlers() -> None:
    """Set up signal handlers to clean up on SIGINT/SIGTERM."""
    def signal_handler(signum, frame):
        print("\n[!] Interrupted – cleaning up...")
        cleanup()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
