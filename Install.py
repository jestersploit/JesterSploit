#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import subprocess
import sys

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
VENV_DIR = os.path.join(PROJECT_DIR, "venv")


def run(cmd):
    try:
        subprocess.run(cmd, shell=True, check=True)
    except subprocess.CalledProcessError:
        print(f"[!] Failed: {cmd}")
        sys.exit(1)


def check_root():
    if os.geteuid() != 0:
        print("[!] Run as root")
        sys.exit(1)


def create_venv():
    if not os.path.exists(VENV_DIR):
        print("[*] Creating virtual environment...")
        run(f"python3 -m venv {VENV_DIR}")
    else:
        print("[*] Virtual environment already exists")


def install_python_deps():
    pip = os.path.join(VENV_DIR, "bin", "pip")

    print("[*] Upgrading pip...")
    run(f"{pip} install --upgrade pip")

    print("[*] Installing Python dependencies...")
    run(f"{pip} install -r {PROJECT_DIR}/requirements.txt")


def install_system_tools():
    tools = [
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

    print("[*] Updating apt...")
    run("apt update")

    for tool in tools:
        if subprocess.call(f"which {tool}", shell=True,
                           stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL) != 0:
            print(f"[*] Installing {tool}...")
            run(f"apt install -y {tool}")
        else:
            print(f"[+] {tool} already installed")


def set_permissions():
    main = os.path.join(PROJECT_DIR, "jestersploit.py")

    if os.path.exists(main):
        run(f"chmod +x {main}")
        print("[*] Permission set: jestersploit.py")


def final_message():
    print("\n=== DONE ===")
    print("[*] Activate venv:")
    print(f"source {VENV_DIR}/bin/activate")
    print("[*] Run:")
    print("sudo ./jestersploit.py\n")


def main():
    check_root()
    create_venv()
    install_python_deps()
    install_system_tools()
    set_permissions()
    final_message()


if __name__ == "__main__":
    main()
