#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JesterSploit Installer
Automatically sets up Python dependencies, system tools, and permissions
"""

import os
import subprocess
import sys
import platform

# Check if running as root
if os.geteuid() != 0:
    print("Please run this script as root.")
    sys.exit(1)

# Paths
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))

# Python dependencies
PY_DEPS = ["requests>=2.25.0", "scapy>=2.4.5"]

# System tools
SYS_TOOLS = [
    "aircrack-ng",
    "hcxtools",
    "bully",
    "reaver",
    "pixiewps",
    "hostapd",
    "dnsmasq",
    "hashcat",
    "bettercap"
]

def run(cmd, check=True):
    """Run a shell command"""
    try:
        subprocess.run(cmd, shell=True, check=check)
    except subprocess.CalledProcessError as e:
        print(f"[!] Command failed: {cmd}")
        sys.exit(1)

def install_python_packages():
    """Install Python packages in virtual environment"""
    venv_path = os.path.join(PROJECT_DIR, "venv")
    if not os.path.exists(venv_path):
        print("[*] Creating virtual environment...")
        run(f"python3 -m venv {venv_path}")

    pip_path = os.path.join(venv_path, "bin", "pip")
    print("[*] Upgrading pip...")
    run(f"{pip_path} install --upgrade pip")

    print("[*] Installing Python dependencies...")
    for package in PY_DEPS:
        run(f"{pip_path} install {package}")

def install_system_tools():
    """Install system packages via apt if missing"""
    print("[*] Updating package list...")
    run("apt update")
    for tool in SYS_TOOLS:
        # Check if tool exists
        if subprocess.call(f"command -v {tool}", shell=True, stdout=subprocess.DEVNULL) != 0:
            print(f"[*] Installing {tool}...")
            run(f"apt install -y {tool}")

def set_permissions():
    """Make main script executable"""
    main_script = os.path.join(PROJECT_DIR, "jestersploit.py")
    if os.path.exists(main_script):
        run(f"chmod +x {main_script}")
        print("[*] Permissions set for jestersploit.py")

def main():
    print("=== JesterSploit Installer ===")
    install_python_packages()
    install_system_tools()
    set_permissions()
    print("[*] Installation complete! Run the main script with:")
    print(f"sudo {os.path.join(PROJECT_DIR, 'jestersploit.py')}")

if __name__ == "__main__":
    main()
