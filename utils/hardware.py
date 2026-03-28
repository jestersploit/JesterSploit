#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import subprocess
import re
from pathlib import Path
from typing import Tuple, Optional, List, Set

# Channel lists
CHANNELS_24GHZ = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
CHANNELS_24GHZ_EXTENDED = [12, 13, 14]
CHANNELS_5GHZ = [36, 40, 44, 48, 52, 56, 60, 64, 100, 104, 108, 112, 116, 120,
                 124, 128, 132, 136, 140, 149, 153, 157, 161, 165]
ALL_CHANNELS = CHANNELS_24GHZ + CHANNELS_24GHZ_EXTENDED + CHANNELS_5GHZ
VALID_CHANNELS: Set[int] = set(ALL_CHANNELS)

# USB VID/PID for supported adapters (USB only)
USB_WIRELESS_DEVICES = {
    (0x0cf3, 0x9271): "Atheros AR9271",
    (0x148f, 0x3070): "Ralink RT3070",
    (0x148f, 0x5370): "Ralink RT5370",
    (0x148f, 0x5572): "Ralink RT5572",
    (0x0e8d, 0x7632): "MediaTek MT7632",
    (0x0e8d, 0x7612): "MediaTek MT7612",
    (0x0bda, 0x8812): "Realtek RTL8812AU",
    (0x0bda, 0x8813): "Realtek RTL8813AU",
    (0x0bda, 0x8821): "Realtek RTL8821AU",
    (0x0bda, 0x8187): "Realtek RTL8187",
    (0x0a5c, 0xbd1e): "Broadcom BCM4323",
}

# Global state (set by detection functions)
hardware_available = False
adapter_detected = False
interface = None
monitor_interface = None
gpu_available = False
gpu_type = None
gpu_name = None
gpu_opencl = False
gpu_cuda = False
cpu_model = "Unknown"
cpu_cores = 0
total_ram = 0


def detect_usb_adapter() -> Tuple[bool, Optional[str], Optional[str]]:
    """Detect USB wireless adapters only – no internal cards."""
    try:
        result = subprocess.run(['lsusb'], capture_output=True, text=True, timeout=5)
        lines = result.stdout.split('\n')
        for line in lines:
            match = re.search(r'ID ([0-9a-f]{4}):([0-9a-f]{4})', line.lower())
            if match:
                vid = int(match.group(1), 16)
                pid = int(match.group(2), 16)
                if (vid, pid) in USB_WIRELESS_DEVICES:
                    chipset = USB_WIRELESS_DEVICES[(vid, pid)]
                    iface = _find_interface_for_usb(vid, pid)
                    if iface:
                        return True, iface, chipset
                    iface = _find_any_wireless_interface()
                    if iface:
                        return True, iface, chipset
                    return True, None, chipset
    except Exception as e:
        print(f"[!] USB detection failed: {e}")
    return False, None, None


def _find_interface_for_usb(vid: int, pid: int) -> Optional[str]:
    """Find network interface associated with USB device."""
    try:
        net_path = Path('/sys/class/net')
        for iface_dir in net_path.iterdir():
            if iface_dir.is_dir():
                device_path = iface_dir / 'device'
                if device_path.exists() and device_path.is_symlink():
                    real_path = device_path.resolve()
                    if f"{vid:04x}:{pid:04x}" in str(real_path).lower():
                        return iface_dir.name
                if (iface_dir / 'wireless').exists():
                    try:
                        ethtool = subprocess.run(['ethtool', '-i', iface_dir.name],
                                                capture_output=True, text=True, timeout=3)
                        if 'usb' in ethtool.stdout.lower():
                            return iface_dir.name
                    except:
                        pass
    except Exception:
        pass
    return None


def _find_any_wireless_interface() -> Optional[str]:
    """Find any wireless interface (fallback)."""
    try:
        result = subprocess.run(['iwconfig'], capture_output=True, text=True, timeout=5)
        for line in result.stdout.split('\n'):
            if 'IEEE 802.11' in line:
                iface = line.split()[0]
                try:
                    ethtool = subprocess.run(['ethtool', '-i', iface],
                                            capture_output=True, text=True, timeout=3)
                    if 'usb' in ethtool.stdout.lower():
                        return iface
                except:
                    pass
                return iface
    except Exception:
        pass
    return None


def detect_adapter() -> bool:
    """Detect and initialize USB adapter."""
    global hardware_available, adapter_detected, interface
    adapter_detected = False
    hardware_available = False
    interface = None

    detected, iface, chipset = detect_usb_adapter()
    if detected:
        adapter_detected = True
        hardware_available = True
        interface = iface
        print(f"[+] USB adapter detected: {chipset}")
        if iface:
            print(f"[+] Interface: {iface}")
        else:
            print("[*] Interface: (will be detected after monitor mode)")
        return True
    else:
        print("[!] No USB wireless adapter detected")
        print("[*] Supported adapters: TL-WN722N v1, Alfa AWUS036ACH, etc.")
        return False


def detect_hardware() -> None:
    """Detect CPU, RAM, and GPU (hashcat-aware)."""
    global cpu_model, cpu_cores, total_ram, gpu_available, gpu_type, gpu_name, gpu_opencl, gpu_cuda

    # CPU
    try:
        with open("/proc/cpuinfo", 'r') as f:
            for line in f:
                if "model name" in line:
                    cpu_model = line.split(":")[1].strip()
                    break
                elif "Processor" in line:
                    cpu_model = line.split(":")[1].strip()
                    break
        cpu_cores = os.cpu_count() or 0
        print(f"[*] CPU: {cpu_model} ({cpu_cores} cores)")
    except:
        print("[!] CPU detection failed")

    # RAM
    try:
        with open("/proc/meminfo", 'r') as f:
            for line in f:
                if "MemTotal" in line:
                    total_ram = int(line.split(":")[1].strip().split()[0]) // 1024
                    break
        print(f"[*] RAM: {total_ram} MB")
    except:
        print("[!] RAM detection failed")

    # GPU using hashcat -I
    try:
        result = subprocess.run(["hashcat", "-I"], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            in_opencl = False
            in_cuda = False
            for line in lines:
                if "OpenCL Info" in line:
                    in_opencl = True
                    in_cuda = False
                    continue
                elif "CUDA Info" in line:
                    in_opencl = False
                    in_cuda = True
                    continue
                if in_opencl and "OpenCL Platform" in line:
                    if "NVIDIA" in line:
                        gpu_type = "nvidia"
                        gpu_opencl = True
                    elif "AMD" in line:
                        gpu_type = "amd"
                        gpu_opencl = True
                    elif "Intel" in line:
                        gpu_type = "intel"
                        gpu_opencl = True
                    continue
                if in_opencl and "Device #" in line and ":" in line:
                    gpu_name = line.split(":")[1].strip().split(",")[0]
                    gpu_available = True
                if in_cuda and "CUDA Device" in line:
                    gpu_available = True
                    gpu_cuda = True
                    gpu_type = "nvidia"
                    parts = line.split(":")
                    if len(parts) > 1:
                        gpu_name = parts[1].strip().split(",")[0]
            if gpu_available:
                print(f"[+] Usable GPU detected: {gpu_name}")
                if gpu_cuda:
                    print("  ✓ CUDA support")
                if gpu_opencl:
                    print("  ✓ OpenCL support")
                return
    except Exception as e:
        print(f"[!] hashcat detection failed: {e}")

    # Fallback: nvidia-smi
    try:
        result = subprocess.run(["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
                               capture_output=True, text=True, timeout=5)
        if result.returncode == 0 and result.stdout.strip():
            gpu_available = True
            gpu_type = "nvidia"
            gpu_name = result.stdout.strip().split('\n')[0]
            print(f"[!] NVIDIA GPU detected: {gpu_name} (but may not be usable without drivers)")
            return
    except:
        pass

    # Fallback: lspci
    try:
        result = subprocess.run(["lspci", "-v"], capture_output=True, text=True, timeout=5)
        for line in result.stdout.split('\n'):
            if "VGA" in line or "3D" in line:
                if "NVIDIA" in line:
                    gpu_available = True
                    gpu_type = "nvidia"
                    gpu_name = line.split(":")[2].strip() if ":" in line else "NVIDIA GPU"
                    print(f"[!] NVIDIA GPU detected via lspci (may not be usable)")
                    return
                elif "AMD" in line or "Radeon" in line:
                    gpu_available = True
                    gpu_type = "amd"
                    gpu_name = line.split(":")[2].strip() if ":" in line else "AMD GPU"
                    print(f"[!] AMD GPU detected via lspci (may not be usable)")
                    return
    except:
        pass

    if not gpu_available:
        print("[!] No usable GPU for cracking - CPU mode only")
        if cpu_cores > 4:
            print("  → Use: hashcat -m 22000 -O -w 4 -n 32")
        elif cpu_cores > 2:
            print("  → Use: hashcat -m 22000 -O -w 3 -n 16")
        gpu_name = "None (CPU mode)"
