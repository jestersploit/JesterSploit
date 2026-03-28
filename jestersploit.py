#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
JESTERSPLOIT – WiFi Penetration Testing Framework
Main Orchestrator – Complete Edition
"""

import os
import sys
import hashlib
import time
import threading
import json
from pathlib import Path
from datetime import datetime

# Ensure the data directory exists
DATA_DIR = Path("data")
CAPTURES_DIR = DATA_DIR / "captures"
REPORTS_DIR = DATA_DIR / "reports"
CAPTURES_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

# Set environment variable for modules that need it
os.environ["JESTER_DATA_DIR"] = str(DATA_DIR)

# Session ID
SESSION_ID = hashlib.sha256(str(time.time()).encode()).hexdigest()[:16]

# Import utilities
from utils.colors import *
from utils.status import print_status, pause, confirm_action, clear_screen
from utils.validator import validate_bssid, validate_channel, validate_file
from utils.hardware import (
    hardware_available, adapter_detected, gpu_available, gpu_name,
    cpu_model, cpu_cores, total_ram, detect_hardware, detect_adapter
)
from utils.interface import interface, monitor_interface, enable_monitor_mode, set_channel
from utils.config import config, load_config, save_config
from utils.logger import setup_loggers, log_capture, capture_log
from utils.process import (
    active_processes, kill_all_processes, kill_attack_processes, add_process,
    is_cancelled, set_cancel_flag, setup_signal_handlers
)
from utils.telegram import send_telegram_message, telegram_command_handler, telegram_running

# Core modules
from core.scanner import start_scan
from core.pmkid import capture_pmkid
from core.handshake import capture_handshake
from core.wps import wps_attack
from core.deauth import deauth_attack
from core.evil import evil_twin_attack
from core.karma import karma_attack
from core.beacon import beacon_flood
from core.frag import fragattacks_attack
from core.krack import krack_attack
from core.broadcom import broadcom_kill
from core.airsnitch import airsnitch_attack
from core.mediatek import mediatek_heap_overflow
from core.pmksa import pmksa_poison
from core.crack import try_auto_crack
from core.report import generate_report
from core.wordlist import current_wordlists, show_wordlist_menu


# -------------------------------
# Helper: Center text within 102 chars
# -------------------------------
def center_header(text: str, width: int = 102) -> str:
    """Return centered text with padding to given width."""
    if len(text) >= width:
        return text
    padding = (width - len(text)) // 2
    return " " * padding + text


def print_centered_banner(banner: str, width: int = 102) -> None:
    """Print a multi‑line ASCII banner centered as a block within given width."""
    lines = banner.strip('\n').split('\n')
    stripped_lines = [line.rstrip() for line in lines]
    max_len = max(len(line) for line in stripped_lines)
    if max_len >= width:
        for line in stripped_lines:
            print(line)
        return
    padding = (width - max_len) // 2
    for line in stripped_lines:
        print(" " * padding + line)


# -------------------------------
# First-Time Setup Wizard
# -------------------------------
def first_time_setup():
    clear_screen()
    print(f"{COLOR_BOLD}{COLOR_CYAN}{'=' * 102}{COLOR_RESET}")
    print(f"{COLOR_BOLD}{COLOR_CRIMSON}{center_header('JESTERSPLOIT - First Time Setup')}{COLOR_RESET}")
    print(f"{COLOR_BOLD}{COLOR_CYAN}{'=' * 102}{COLOR_RESET}")
    print()
    print(f"{COLOR_YELLOW}[!] Welcome to JESTERSPLOIT{COLOR_RESET}")
    print("    This setup will run only once.")
    print("    You can change these settings later from the main menu (Option Settings).")
    print()

    # Telegram
    print(f"{COLOR_BOLD}{COLOR_GREEN}[1/3] Telegram Configuration{COLOR_RESET}")
    print("    Telegram allows remote control of JESTERSPLOIT.")
    print("    You can skip this if you only want local usage.")
    print()
    setup_telegram = confirm_action("Configure Telegram?", default=True)
    token = ""
    chat_id = ""
    if setup_telegram:
        print("\nHow to get your Bot Token:")
        print("1. Open Telegram, search for @BotFather")
        print("2. Send /newbot and follow instructions")
        print("3. Copy the token")
        token = input("Enter Bot Token (or press Enter to skip): ").strip()
        if token:
            print("\nHow to get your Chat ID:")
            print("1. Open Telegram, search for @userinfobot")
            print("2. Send /start")
            print("3. Copy your ID")
            chat_id = input("Enter Chat ID (or press Enter to skip): ").strip()
        if token and chat_id:
            if config.get("telegram") is None:
                config["telegram"] = {}
            config["telegram"]["token"] = token
            config["telegram"]["chat_id"] = chat_id
            config["telegram"]["enabled"] = True
            print_status("Testing connection...", "info")
            if send_telegram_message(f"JESTERSPLOIT online\nSession: {SESSION_ID}"):
                print_status("Telegram configured successfully!", "success")
            else:
                print_status("Telegram connection failed. You can fix it later in Settings.", "warning")
        else:
            print_status("Telegram not configured.", "info")
    else:
        print_status("Skipping Telegram configuration.", "info")

    # Wordlist
    print()
    print(f"{COLOR_BOLD}{COLOR_GREEN}[2/3] Wordlist Configuration{COLOR_RESET}")
    print("    Wordlists are used for cracking captured hashes.")
    print()
    default_wl = "/usr/share/wordlists/rockyou.txt"
    if os.path.exists(default_wl):
        print(f"    Default wordlist found: {default_wl}")
        use_default = confirm_action("Use default wordlist?", default=True)
        if use_default:
            current_wordlists.append(default_wl)
            print_status("Using default wordlist", "success")
        else:
            custom = input("Enter path to custom wordlist: ").strip()
            if custom and os.path.exists(custom):
                current_wordlists.append(custom)
                print_status(f"Using custom wordlist: {custom}", "success")
            else:
                print_status("No wordlist configured. You can add one later from the menu.", "warning")
    else:
        print(f"    Default wordlist not found: {default_wl}")
        print("    Install it with: sudo gunzip /usr/share/wordlists/rockyou.txt.gz")
        custom = input("Enter path to custom wordlist (or leave empty to skip): ").strip()
        if custom and os.path.exists(custom):
            current_wordlists.append(custom)
            print_status(f"Using custom wordlist: {custom}", "success")
        else:
            print_status("No wordlist configured. You can add one later from the menu.", "warning")

    # Scan duration
    print()
    print(f"{COLOR_BOLD}{COLOR_GREEN}[3/3] Default Scan Duration{COLOR_RESET}")
    print("    This is used when scanning networks.")
    print()
    dur = input("Scan duration in seconds [60]: ").strip()
    if dur.isdigit():
        config["hardware"]["scan_duration"] = int(dur)
    else:
        config["hardware"]["scan_duration"] = 60
    print_status(f"Scan duration set to {config['hardware']['scan_duration']} seconds", "success")

    config["first_run_done"] = True
    save_config()
    print()
    print_status("Setup complete! Press Enter to continue...", "info")
    input()


# -------------------------------
# Settings Menu (sub‑menus)
# -------------------------------
def settings_menu():
    """Main settings menu, loops after each sub‑menu."""
    while True:
        clear_screen()
        print(f"{COLOR_BOLD}{COLOR_CYAN}{'=' * 102}{COLOR_RESET}")
        print(f"{COLOR_BOLD}{COLOR_CRIMSON}{center_header('SETTINGS')}{COLOR_RESET}")
        print(f"{COLOR_BOLD}{COLOR_CYAN}{'=' * 102}{COLOR_RESET}")
        print()
        print(f"{COLOR_BOLD}1. Telegram Configuration{COLOR_RESET}")
        print(f"2. Wordlist Management")
        print(f"3. Hardware Settings")
        print(f"4. Cracking Settings")
        print(f"5. Notification Settings")
        print(f"6. Logging Settings")
        print(f"7. System Information")
        print(f"8. Reset to Defaults")
        print(f"9. View Current Config")
        print(f"0. Back to Main Menu")
        print()
        choice = input(f"{COLOR_YELLOW}[?]{COLOR_RESET} Select setting: ").strip()
        if choice == "1":
            configure_telegram()
        elif choice == "2":
            show_wordlist_menu()
        elif choice == "3":
            configure_hardware()
        elif choice == "4":
            configure_cracking()
        elif choice == "5":
            configure_notifications()
        elif choice == "6":
            configure_logging()
        elif choice == "7":
            show_system_info()
        elif choice == "8":
            reset_config()
        elif choice == "9":
            view_config()
        elif choice == "0":
            break
        else:
            print_status("Invalid choice", "error")
            time.sleep(1)


def configure_telegram():
    global config
    if config.get("telegram") is None:
        config["telegram"] = {}
    while True:
        clear_screen()
        print(f"{COLOR_BOLD}Telegram Configuration{COLOR_RESET}")
        print()
        tg = config.get("telegram", {})
        token = tg.get("token")
        if token is None or token == "":
            token = "Not set"
        chat = tg.get("chat_id")
        if chat is None or chat == "":
            chat = "Not set"
        enabled = tg.get("enabled", False)
        print(f"Status: {'Enabled' if enabled else 'Disabled'}")
        print(f"Bot Token: {token[:20] if token != 'Not set' else 'Not set'}...")
        print(f"Chat ID: {chat}")
        print()
        print("1. Enable/Disable Telegram")
        print("2. Set Bot Token")
        print("3. Set Chat ID")
        print("4. Test Connection")
        print("0. Back")
        choice = input(f"{COLOR_YELLOW}[?]{COLOR_RESET} Option: ").strip()
        if choice == "1":
            config["telegram"]["enabled"] = not enabled
            save_config()
            print_status(f"Telegram {'enabled' if config['telegram']['enabled'] else 'disabled'}", "success")
            time.sleep(1)
        elif choice == "2":
            print("\nHow to get your Bot Token:")
            print("1. Open Telegram, search for @BotFather")
            print("2. Send /newbot and follow instructions")
            print("3. Copy the token\n")
            while True:
                token = input("Enter Bot Token: ").strip()
                if token == "":
                    print_status("Token cannot be empty.", "error")
                    continue
                config["telegram"]["token"] = token
                config["telegram"]["enabled"] = True
                save_config()
                print_status("Token saved", "success")
                break
            time.sleep(1)
        elif choice == "3":
            print("\nHow to get your Chat ID:")
            print("1. Open Telegram, search for @userinfobot")
            print("2. Send /start")
            print("3. Copy your ID\n")
            while True:
                chat_id = input("Enter Chat ID: ").strip()
                if chat_id == "":
                    print_status("Chat ID cannot be empty.", "error")
                    continue
                config["telegram"]["chat_id"] = chat_id
                save_config()
                print_status("Chat ID saved", "success")
                break
            time.sleep(1)
        elif choice == "4":
            print_status("Testing connection...", "info")
            if config.get("telegram", {}).get("token") and config.get("telegram", {}).get("chat_id"):
                if send_telegram_message("Test message from JesterSploit"):
                    print_status("Connection successful!", "success")
                else:
                    print_status("Connection failed! Check your token and chat ID", "error")
            else:
                print_status("Token or Chat ID not configured", "error")
            pause()
        elif choice == "0":
            break
        else:
            print_status("Invalid choice", "error")
            time.sleep(1)


def view_config():
    clear_screen()
    print(f"{COLOR_BOLD}Current Configuration{COLOR_RESET}")
    print()
    print(f"{COLOR_BOLD}Telegram:{COLOR_RESET}")
    tg = config.get("telegram", {})
    token = tg.get("token")
    if token is None or token == "":
        token_display = "Not set"
    else:
        token_display = token[:20] + "..."
    chat = tg.get("chat_id")
    if chat is None or chat == "":
        chat_display = "Not set"
    else:
        chat_display = chat
    print(f"  Enabled: {tg.get('enabled', False)}")
    print(f"  Token: {token_display}")
    print(f"  Chat ID: {chat_display}")
    print()
    print(f"{COLOR_BOLD}Wordlists ({len(current_wordlists)}):{COLOR_RESET}")
    for wl in current_wordlists:
        print(f"  - {wl}")
    print()
    print(f"{COLOR_BOLD}Hardware:{COLOR_RESET}")
    hw = config.get("hardware", {})
    print(f"  Channel Hopping: {hw.get('channel_hopping', True)}")
    print(f"  5GHz Enabled: {hw.get('5ghz_enabled', True)}")
    print(f"  Deauth Count: {hw.get('deauth_count', 10)}")
    print(f"  Scan Duration: {hw.get('scan_duration', 60)}s")
    print()
    print(f"{COLOR_BOLD}Cracking:{COLOR_RESET}")
    cr = config.get("cracking", {})
    print(f"  GPU Enabled: {cr.get('gpu_enabled', True)}")
    print(f"  Max Crack Time: {cr.get('max_crack_time', 600)}s")
    print(f"  Auto-Crack: {cr.get('auto_crack_after_capture', True)}")
    print()
    print(f"{COLOR_BOLD}Telegram Notifications:{COLOR_RESET}")
    tg_set = config.get("telegram_settings", {})
    print(f"  Notify on Capture: {tg_set.get('notify_on_capture', True)}")
    print(f"  Notify on Crack: {tg_set.get('notify_on_crack', True)}")
    print(f"  Progress Updates: {tg_set.get('progress_updates', True)}")
    print()
    pause()


def configure_hardware():
    global config
    while True:
        clear_screen()
        print(f"{COLOR_BOLD}Hardware Settings{COLOR_RESET}")
        print()
        hw = config.get("hardware", {})
        print(f"1. Channel Hopping: {hw.get('channel_hopping', True)}")
        print(f"2. 5GHz Enabled: {hw.get('5ghz_enabled', True)}")
        print(f"3. Default Deauth Count: {hw.get('deauth_count', 10)}")
        print(f"4. Default Scan Duration: {hw.get('scan_duration', 60)}s")
        print(f"5. PMKID Timeout: {hw.get('pmkid_timeout', 60)}s")
        print(f"6. Handshake Timeout: {hw.get('handshake_timeout', 35)}s")
        print(f"0. Back")
        print()
        choice = input(f"{COLOR_YELLOW}[?]{COLOR_RESET} Option: ").strip()
        if choice == "1":
            config.setdefault("hardware", {})["channel_hopping"] = not hw.get("channel_hopping", True)
            save_config()
            print_status("Channel hopping toggled", "success")
        elif choice == "2":
            config.setdefault("hardware", {})["5ghz_enabled"] = not hw.get("5ghz_enabled", True)
            save_config()
            print_status("5GHz toggled", "success")
        elif choice == "3":
            val = input("Enter default deauth count [10]: ").strip()
            if val.isdigit():
                config.setdefault("hardware", {})["deauth_count"] = int(val)
                save_config()
                print_status("Deauth count saved", "success")
            else:
                print_status("Keeping current value", "info")
        elif choice == "4":
            val = input("Enter scan duration in seconds [60]: ").strip()
            if val.isdigit():
                config.setdefault("hardware", {})["scan_duration"] = int(val)
                save_config()
                print_status("Scan duration saved", "success")
            else:
                print_status("Keeping current value", "info")
        elif choice == "5":
            val = input("Enter PMKID timeout in seconds [60]: ").strip()
            if val.isdigit():
                config.setdefault("hardware", {})["pmkid_timeout"] = int(val)
                save_config()
                print_status("PMKID timeout saved", "success")
            else:
                print_status("Keeping current value", "info")
        elif choice == "6":
            val = input("Enter handshake timeout in seconds [35]: ").strip()
            if val.isdigit():
                config.setdefault("hardware", {})["handshake_timeout"] = int(val)
                save_config()
                print_status("Handshake timeout saved", "success")
            else:
                print_status("Keeping current value", "info")
        elif choice == "0":
            break
        else:
            print_status("Invalid choice", "error")
        time.sleep(1)


def configure_cracking():
    global config
    while True:
        clear_screen()
        print(f"{COLOR_BOLD}Cracking Settings{COLOR_RESET}")
        print()
        cr = config.get("cracking", {})
        print(f"1. GPU Acceleration: {cr.get('gpu_enabled', True)}")
        print(f"2. Max Crack Time: {cr.get('max_crack_time', 600)}s")
        print(f"3. Auto-Crack After Capture: {cr.get('auto_crack_after_capture', True)}")
        print(f"0. Back")
        print()
        choice = input(f"{COLOR_YELLOW}[?]{COLOR_RESET} Option: ").strip()
        if choice == "1":
            config.setdefault("cracking", {})["gpu_enabled"] = not cr.get("gpu_enabled", True)
            save_config()
            print_status("GPU acceleration toggled", "success")
        elif choice == "2":
            val = input("Enter max crack time in seconds [600]: ").strip()
            if val.isdigit():
                config.setdefault("cracking", {})["max_crack_time"] = int(val)
                save_config()
                print_status("Max crack time saved", "success")
            else:
                print_status("Keeping current value", "info")
        elif choice == "3":
            config.setdefault("cracking", {})["auto_crack_after_capture"] = not cr.get("auto_crack_after_capture", True)
            save_config()
            print_status("Auto-crack toggled", "success")
        elif choice == "0":
            break
        else:
            print_status("Invalid choice", "error")
        time.sleep(1)


def configure_notifications():
    global config
    while True:
        clear_screen()
        print(f"{COLOR_BOLD}Notification Settings{COLOR_RESET}")
        print()
        tg = config.get("telegram_settings", {})
        print(f"1. Notify on Capture: {tg.get('notify_on_capture', True)}")
        print(f"2. Notify on Crack: {tg.get('notify_on_crack', True)}")
        print(f"3. Progress Updates: {tg.get('progress_updates', True)}")
        print(f"0. Back")
        print()
        choice = input(f"{COLOR_YELLOW}[?]{COLOR_RESET} Option: ").strip()
        if choice == "1":
            config.setdefault("telegram_settings", {})["notify_on_capture"] = not tg.get("notify_on_capture", True)
            save_config()
            print_status("Capture notifications toggled", "success")
        elif choice == "2":
            config.setdefault("telegram_settings", {})["notify_on_crack"] = not tg.get("notify_on_crack", True)
            save_config()
            print_status("Crack notifications toggled", "success")
        elif choice == "3":
            config.setdefault("telegram_settings", {})["progress_updates"] = not tg.get("progress_updates", True)
            save_config()
            print_status("Progress updates toggled", "success")
        elif choice == "0":
            break
        else:
            print_status("Invalid choice", "error")
        time.sleep(1)


def configure_logging():
    global config
    while True:
        clear_screen()
        print(f"{COLOR_BOLD}Logging Settings{COLOR_RESET}")
        print()
        log = config.get("logging", {})
        print(f"1. Forensic Logging: {log.get('forensic_logging', True)}")
        print(f"2. Save Captures: {log.get('save_captures', True)}")
        print(f"3. Capture Directory: {log.get('capture_dir', 'data/captures')}")
        print(f"0. Back")
        print()
        choice = input(f"{COLOR_YELLOW}[?]{COLOR_RESET} Option: ").strip()
        if choice == "1":
            config.setdefault("logging", {})["forensic_logging"] = not log.get("forensic_logging", True)
            save_config()
            print_status("Forensic logging toggled", "success")
        elif choice == "2":
            config.setdefault("logging", {})["save_captures"] = not log.get("save_captures", True)
            save_config()
            print_status("Save captures toggled", "success")
        elif choice == "3":
            path = input(f"Enter capture directory [{log.get('capture_dir', 'data/captures')}]: ").strip()
            if path:
                config.setdefault("logging", {})["capture_dir"] = path
                save_config()
                print_status("Capture directory saved", "success")
            else:
                print_status("Keeping current directory", "info")
        elif choice == "0":
            break
        else:
            print_status("Invalid choice", "error")
        time.sleep(1)


def show_system_info():
    clear_screen()
    print(f"{COLOR_BOLD}System Information{COLOR_RESET}")
    print()
    print(f"CPU: {cpu_model} ({cpu_cores} cores)")
    print(f"RAM: {total_ram} MB ({round(total_ram/1024,1)} GB)")
    print(f"GPU: {gpu_name if gpu_available else 'None'}")
    if gpu_available:
        from utils.hardware import gpu_opencl, gpu_cuda
        print(f"  Type: {gpu_type}")
        print(f"  CUDA: {gpu_cuda}, OpenCL: {gpu_opencl}")
    print(f"OS: {os.uname().sysname} {os.uname().release}")
    print(f"Python: {sys.version.split()[0]}")
    print()
    pause()


def reset_config():
    global config, current_wordlists
    if confirm_action("Reset all settings to defaults?", default=False):
        from utils.config import DEFAULT_CONFIG
        config = DEFAULT_CONFIG.copy()
        current_wordlists = []
        save_config()
        print_status("Settings reset to defaults", "success")
        time.sleep(1)


def view_config():
    clear_screen()
    print(f"{COLOR_BOLD}Current Configuration{COLOR_RESET}")
    print()
    print(f"{COLOR_BOLD}Telegram:{COLOR_RESET}")
    print(f"  Enabled: {config.get('telegram', {}).get('enabled', False)}")
    print(f"  Token: {config.get('telegram', {}).get('token', 'Not set')[:20] if config.get('telegram', {}).get('token') else 'Not set'}...")
    print(f"  Chat ID: {config.get('telegram', {}).get('chat_id', 'Not set')}")
    print()
    print(f"{COLOR_BOLD}Wordlists ({len(current_wordlists)}):{COLOR_RESET}")
    for wl in current_wordlists:
        print(f"  - {wl}")
    print()
    print(f"{COLOR_BOLD}Hardware:{COLOR_RESET}")
    hw = config.get("hardware", {})
    print(f"  Channel Hopping: {hw.get('channel_hopping', True)}")
    print(f"  5GHz Enabled: {hw.get('5ghz_enabled', True)}")
    print(f"  Deauth Count: {hw.get('deauth_count', 10)}")
    print(f"  Scan Duration: {hw.get('scan_duration', 60)}s")
    print()
    print(f"{COLOR_BOLD}Cracking:{COLOR_RESET}")
    cr = config.get("cracking", {})
    print(f"  GPU Enabled: {cr.get('gpu_enabled', True)}")
    print(f"  Max Crack Time: {cr.get('max_crack_time', 600)}s")
    print(f"  Auto-Crack: {cr.get('auto_crack_after_capture', True)}")
    print()
    print(f"{COLOR_BOLD}Telegram Notifications:{COLOR_RESET}")
    tg = config.get("telegram_settings", {})
    print(f"  Notify on Capture: {tg.get('notify_on_capture', True)}")
    print(f"  Notify on Crack: {tg.get('notify_on_crack', True)}")
    print(f"  Progress Updates: {tg.get('progress_updates', True)}")
    print()
    pause()


# -------------------------------
# Main Menu (centered banner)
# -------------------------------
def show_main_menu():
    clear_screen()
    # Banner (exact from backup)
    banner = r"""
                                 ....   ....
                                .#-#. ...+-#.
                                -+ --   -+ --
                                --  +.  +  .+
           .-+++++++-.          --  -- .-  .+          .--++++++-.
        .++.        .-++.       +.  .# +.  .+       .++-.        .++.
      .#-..-+----++..   .#-.    +.  .+-#    +     -#.   ..++----++..-#.
     .#--.-+++-.    .--.  .+-   +.  .-.-.   +   -#.   --.    .-++++---+.
    .+++-.    ..++.   .--.  -#. -.  .. ..   + .#-   --.   .-+-.    .-++#.
 .-.-+-          .+-.   .+.  .+.+.   .+     +.+.  .+.   .-+.          -+-.-.
...   -            .+.    -.  .##.    -    .##.  .-.   .+.            -    ..
 -. ...    .+##+++####.    +.   #.    +    .#   .+.   .####+++##+..   .-. .-
   ..   .#-.         .+.   .-.  .+    +    +-   -.   .+.         .-#.   ..
      .+-.  .---..    --  . --   --   +   --   .-    --    ..---.  .-+.
      +. .--.... ..--..#.   .+.  .+...+...+    #.   .#..---. ....--. .+.
     +- .--#-...-#+...---..---.---------------..--..-+-...+#-...-#--- -+
    .+ .-#.        .+----...   .. --.-.- -- ..   ...----+.        .#-- --
    --.-+.           .+.     . .-... .-. ...-.  .    .+-           .+-..-
    +.-#.             -    .......--------........    -             .+-.+
    +.#.              ---------...         ....--------              .#.+
    --+              -#-...++##+-...     ...-+##++...-#-              +-+
   -....              +- .      ..+.     .+..      . -+              ....-
  ..   -              +- .---.--...-.   .-...--.---. -+              -   ..
   .....              -+...-######-..    .-######-...-+              .....
                      -#.-.+#######..   ..+######+.-.+-
                      .#..-------+- .   . -+-------..#.
                      -#..     .    ..  .    .     ..#-
                      +-            ..  -            -+
                      -# .   ..-...-.   .-...-..   ..+-
                      .#-.---.--. ...  .... .--.---.-#.
                       -#.   ..+.  ..---..  .+..   .#-
                        -#.    .##----.----##.   ..#-
                         -#.    .+###+++###+.    .++
                          -#.    .-+#####+-.    .#-
                           .#-.    .-...-.    .-#.
                            .+#.    .----    .#+.
                              .+#.         .+#.
                                .+#+-----+#+.
                                     ...
"""
    print_centered_banner(banner, width=102)
    print(f"{COLOR_CYAN}{'=' * 102}{COLOR_RESET}")
    print(f"{COLOR_BOLD}{COLOR_CRIMSON}                      JESTERSPLOIT{COLOR_RESET} -{COLOR_CYAN} Moderate WiFi Penetration Testing Framework{COLOR_RESET}")
    print(f"{COLOR_CYAN}{'=' * 102}{COLOR_RESET}")
    print()

    # Classification Box
    print(f"{COLOR_BOLD}{COLOR_GREEN}┌────────────────────────────────────────────────────────────────────────────────────────────────────┐{COLOR_RESET}")
    print(f"{COLOR_BOLD}{COLOR_GREEN}│  CLASSIFICATION: {COLOR_BLACK}Beginner-Friendly{COLOR_GREEN}                                                                 │{COLOR_RESET}")
    print(f"{COLOR_BOLD}{COLOR_GREEN}│  TIER: {COLOR_CORAL}Independent Operator{COLOR_GREEN}                                                                        │{COLOR_RESET}")
    print(f"{COLOR_BOLD}{COLOR_GREEN}│  THREAT: {COLOR_BROWN}Mid{COLOR_GREEN}                                                                                       │{COLOR_RESET}")
    print(f"{COLOR_BOLD}{COLOR_GREEN}│  CAPABILITY: {COLOR_SALMON}Tactical WiFi Compromise{COLOR_GREEN}                                                              │{COLOR_RESET}")
    print(f"{COLOR_BOLD}{COLOR_GREEN}│  DEPLOYMENT: {COLOR_DARK_CYAN}CLIENT-SERVER{COLOR_TEAL}  - Telegram C2 / Terminal{COLOR_GREEN}                                               │{COLOR_RESET}")
    print(f"{COLOR_BOLD}{COLOR_GREEN}│  TARGET: {COLOR_DARK_RED}WPA/WPA2, Personal, WPS, Chipset RCE{COLOR_GREEN}                                                      │{COLOR_RESET}")
    print(f"{COLOR_BOLD}{COLOR_GREEN}│  COUNTERMEASURES: {COLOR_DARK_BLUE}Requires physical proximity{COLOR_GREEN}                                                      │{COLOR_RESET}")
    print(f"{COLOR_BOLD}{COLOR_GREEN}│  DETECTABILITY: {COLOR_DARK_YELLOW}Moderate  {COLOR_TEAL}- deauth patterns detectable{COLOR_GREEN}                                             │{COLOR_RESET}")
    print(f"{COLOR_BOLD}{COLOR_GREEN}│  SESSION: {COLOR_SILVER}{SESSION_ID}{' ' * (86 - len(SESSION_ID))}{COLOR_GREEN}   │{COLOR_RESET}")
    print(f"{COLOR_BOLD}{COLOR_GREEN}└────────────────────────────────────────────────────────────────────────────────────────────────────┘{COLOR_RESET}")
    print()

    # Status lines
    if hardware_available and adapter_detected:
        print(f"{COLOR_GREEN}[✓] USB Adapter: {interface or 'detected'}{COLOR_RESET}")
    else:
        print(f"{COLOR_RED}[✗] NO USB ADAPTER DETECTED - Connect TL-WN722N v1 or any compatible adapters{COLOR_RESET}")
    if gpu_available:
        print(f"{COLOR_GREEN}[✓] GPU: {gpu_name}{COLOR_RESET}")
    else:
        print(f"{COLOR_YELLOW}[!] GPU: None (CPU mode){COLOR_RESET}")
    if config.get("telegram", {}).get("enabled", False):
        print(f"{COLOR_GREEN}[✓] Telegram Bot - Configured{COLOR_RESET}")
    else:
        print(f"{COLOR_RED}[✗] Telegram Bot - Not configured, try going to [20] Settings > Telegram Configuration{COLOR_RESET}")
    print()

    # Menu (horizontal, 3 columns)
    print(f"{COLOR_BOLD}OPERATIONS:{COLOR_RESET}")
    print()
    menu_items = [
        ("1", "Scan"), ("2", "PMKID"), ("3", "Handshake"), ("4", "WPS"),
        ("5", "Deauth"), ("6", "Crack"), ("7", "Wordlists"), ("8", "Report"),
        ("9", "Evil Twin"), ("10", "Karma"), ("11", "Beacon"), ("12", "Frag"),
        ("13", "KRACK"), ("14", "Broadcom"), ("15", "AirSnitch"), ("16", "MediaTek"),
        ("17", "PMKSA"), ("18", "Status"), ("19", "Channel Info"), ("20", "Settings"),
        ("0", "Exit")
    ]
    # 3 columns: first 7, next 7, rest
    col1 = menu_items[0:7]
    col2 = menu_items[7:14]
    col3 = menu_items[14:21]
    col_width = 34
    max_rows = max(len(col1), len(col2), len(col3))
    for i in range(max_rows):
        line = ""
        if i < len(col1):
            num, name = col1[i]
            line += f"  {COLOR_GREEN}[{num}]{COLOR_RESET} {name}".ljust(col_width)
        else:
            line += " " * col_width
        if i < len(col2):
            num, name = col2[i]
            line += f"  {COLOR_GREEN}[{num}]{COLOR_RESET} {name}".ljust(col_width)
        else:
            line += " " * col_width
        if i < len(col3):
            num, name = col3[i]
            line += f"  {COLOR_GREEN}[{num}]{COLOR_RESET} {name}"
        print(line)
    print()


def show_status():
    clear_screen()
    print(f"{COLOR_BOLD}System Status{COLOR_RESET}")
    print(f"  Session: {SESSION_ID}")
    print(f"  USB Adapter: {'Connected' if hardware_available else 'Not detected'}")
    print(f"  Interface: {interface or 'N/A'}")
    print(f"  Monitor: {monitor_interface or 'N/A'}")
    print(f"  GPU: {gpu_name if gpu_available else 'None'}")
    print(f"  Wordlists: {len(current_wordlists)}")
    print(f"  Captures: {len(capture_log)}")
    print()
    if capture_log:
        print(f"{COLOR_BOLD}Recent Captures:{COLOR_RESET}")
        for entry in capture_log[-5:]:
            print(f"  [{entry['timestamp'][:19]}] {entry['event']}: {entry.get('bssid', 'N/A')}")


def show_channel_info():
    from utils.hardware import CHANNELS_24GHZ, CHANNELS_24GHZ_EXTENDED, CHANNELS_5GHZ
    clear_screen()
    print(f"{COLOR_BOLD}Supported Channels{COLOR_RESET}")
    print(f"  2.4GHz: {CHANNELS_24GHZ}")
    print(f"  2.4GHz Extended (restricted): {CHANNELS_24GHZ_EXTENDED}")
    print(f"  5GHz: {CHANNELS_5GHZ[:10]}...")
    print(f"{COLOR_YELLOW}[!] Channels 12-14 may be restricted in some countries{COLOR_RESET}")
    print()


# -------------------------------
# Main Execution
# -------------------------------
def main():
    global config, current_wordlists

    # Root check
    if os.geteuid() != 0:
        print_status("Root privileges required", "error")
        sys.exit(1)

    # Load config
    load_config()

    # Setup loggers with session ID
    setup_loggers(SESSION_ID)

    # First-time setup
    if not config.get("first_run_done", False):
        first_time_setup()
        load_config()  # reload after setup

    # Detect hardware
    detect_hardware()

    # Setup signal handlers
    setup_signal_handlers()

    # Detect USB adapter
    print_status("Detecting USB wireless adapter...", "info")
    detect_adapter()

    # Start Telegram thread if enabled
    if config.get("telegram", {}).get("enabled", False):
        print_status("Starting Telegram command handler...", "info")
        telegram_thread = threading.Thread(target=telegram_command_handler, daemon=True)
        telegram_thread.start()
        print_status("Telegram bot active", "success")
        # Send welcome message after a short delay
        def send_welcome():
    time.sleep(3)
    welcome = f"""JESTERSPLOIT ONLINE
Session: {SESSION_ID}
Hardware: {'Connected' if hardware_available else 'No adapter'}
GPU: {gpu_name if gpu_available else 'None'}
Wordlists: {len(current_wordlists)}

Type /help for commands"""
    send_telegram_message(welcome)

⚠️ *Use responsibly. Authorized testing only.*"""
            send_telegram_message(welcome)
        threading.Thread(target=send_welcome, daemon=True).start()
    else:
        print_status("Telegram disabled. Enable in Settings if needed.", "info")

    # Show wordlist info
    if current_wordlists:
        print_status(f"Loaded {len(current_wordlists)} wordlist(s)", "info")
    else:
        print_status("No wordlists configured. Run option 7 to add wordlists.", "warning")

    # Main loop
    while True:
        show_main_menu()
        choice = input("\n[?] Select operation: ").strip()

        # Exit
        if choice == "0":
            print_status("Shutting down...", "info")
            send_telegram_message("Session terminated")
            save_config()
            kill_all_processes()
            sys.exit(0)

        # Scan
        elif choice == "1":
            if not hardware_available:
                print_status("No USB adapter detected", "error")
                pause()
                continue
            dur = input("[?] Duration (s) [60]: ").strip()
            start_scan(int(dur) if dur else 60)
            pause()

        # PMKID
        elif choice == "2":
            if not hardware_available:
                print_status("No USB adapter detected", "error")
                pause()
                continue
            bssid = input("[?] Target BSSID: ").strip()
            if not bssid:
                continue
            valid, _ = validate_bssid(bssid)
            if not valid:
                print_status("Invalid BSSID format", "error")
                pause()
                continue
            ch = input("[?] Channel [1]: ").strip()
            capture_pmkid(bssid, ch if ch else "1")
            pause()

        # Handshake
        elif choice == "3":
            if not hardware_available:
                print_status("No USB adapter detected", "error")
                pause()
                continue
            bssid = input("[?] Target BSSID: ").strip()
            if not bssid:
                continue
            valid, _ = validate_bssid(bssid)
            if not valid:
                print_status("Invalid BSSID format", "error")
                pause()
                continue
            ch = input("[?] Channel [auto]: ").strip()
            client = input("[?] Client MAC (optional): ").strip()
            if client:
                valid_c, _ = validate_bssid(client)
                if not valid_c:
                    print_status("Invalid client MAC", "error")
                    pause()
                    continue
            capture_handshake(bssid, ch if ch else None, client if client else None)
            pause()

        # WPS
        elif choice == "4":
            if not hardware_available:
                print_status("No USB adapter detected", "error")
                pause()
                continue
            bssid = input("[?] Target BSSID: ").strip()
            if not bssid:
                continue
            valid, _ = validate_bssid(bssid)
            if not valid:
                print_status("Invalid BSSID format", "error")
                pause()
                continue
            ch = input("[?] Channel [1]: ").strip()
            print("WPS attack methods:")
            print("  1. Auto (try bully, reaver, pixiewps)")
            print("  2. Bully only")
            print("  3. Reaver only")
            print("  4. Pixiewps (requires handshake)")
            method_choice = input("[?] Select method [1]: ").strip() or "1"
            method_map = {"1": "auto", "2": "bully", "3": "reaver", "4": "pixiewps"}
            method = method_map.get(method_choice, "auto")
            wps_attack(bssid, ch if ch else "1", method=method)
            pause()

        # Deauth
        elif choice == "5":
            if not hardware_available:
                print_status("No USB adapter detected", "error")
                pause()
                continue
            bssid = input("[?] Target BSSID: ").strip()
            if not bssid:
                continue
            valid, _ = validate_bssid(bssid)
            if not valid:
                print_status("Invalid BSSID format", "error")
                pause()
                continue
            count = input("[?] Packet count [10]: ").strip()
            client = input("[?] Client MAC (optional): ").strip()
            if client:
                valid_c, _ = validate_bssid(client)
                if not valid_c:
                    print_status("Invalid client MAC", "error")
                    pause()
                    continue
            deauth_attack(bssid, int(count) if count else 10, client if client else None)
            pause()

        # Crack
        elif choice == "6":
            file_path = input("[?] Hash file path: ").strip()
            if file_path and os.path.exists(file_path):
                try_auto_crack(file_path, "auto")
            else:
                print_status("File not found", "error")
            pause()

        # Wordlists
        elif choice == "7":
            show_wordlist_menu()

        # Report
        elif choice == "8":
            generate_report()
            pause()

        # Evil Twin
        elif choice == "9":
            if not hardware_available:
                print_status("No USB adapter detected", "error")
                pause()
                continue
            ssid = input("[?] SSID: ").strip()
            if not ssid:
                continue
            ch = input("[?] Channel [1]: ").strip()
            wpa2 = input("[?] Enable WPA2? (y/n): ").strip().lower() == 'y'
            evil_twin_attack(ssid, ch if ch else "1", wpa2)
            pause()

        # Karma
        elif choice == "10":
            if not hardware_available:
                print_status("No USB adapter detected", "error")
                pause()
                continue
            karma_attack()
            pause()

        # Beacon Flood
        elif choice == "11":
            if not hardware_available:
                print_status("No USB adapter detected", "error")
                pause()
                continue
            ssid = input("[?] SSID: ").strip()
            if not ssid:
                continue
            ch = input("[?] Channel [1]: ").strip()
            count = input("[?] Packet count [500]: ").strip()
            beacon_flood(ssid, ch if ch else "1", int(count) if count else 500)
            pause()

        # FragAttacks
        elif choice == "12":
            if not hardware_available:
                print_status("No USB adapter detected", "error")
                pause()
                continue
            bssid = input("[?] Target BSSID: ").strip()
            if not bssid:
                continue
            valid, _ = validate_bssid(bssid)
            if not valid:
                print_status("Invalid BSSID format", "error")
                pause()
                continue
            ch = input("[?] Channel [1]: ").strip()
            fragattacks_attack(bssid, ch if ch else "1")
            pause()

        # KRACK
        elif choice == "13":
            if not hardware_available:
                print_status("No USB adapter detected", "error")
                pause()
                continue
            bssid = input("[?] Target BSSID: ").strip()
            if not bssid:
                continue
            valid, _ = validate_bssid(bssid)
            if not valid:
                print_status("Invalid BSSID format", "error")
                pause()
                continue
            client = input("[?] Client MAC (optional): ").strip()
            if client:
                valid_c, _ = validate_bssid(client)
                if not valid_c:
                    print_status("Invalid client MAC", "error")
                    pause()
                    continue
            ch = input("[?] Channel [1]: ").strip()
            krack_attack(bssid, client if client else None, ch if ch else "1")
            pause()

        # Broadcom Kill
        elif choice == "14":
            if not hardware_available:
                print_status("No USB adapter detected", "error")
                pause()
                continue
            bssid = input("[?] Target BSSID: ").strip()
            if not bssid:
                continue
            valid, _ = validate_bssid(bssid)
            if not valid:
                print_status("Invalid BSSID format", "error")
                pause()
                continue
            ch = input("[?] Channel [36]: ").strip()
            broadcom_kill(bssid, ch if ch else "36")
            pause()

        # AirSnitch
        elif choice == "15":
            if not hardware_available:
                print_status("No USB adapter detected", "error")
                pause()
                continue
            bssid = input("[?] Target BSSID: ").strip()
            if not bssid:
                continue
            valid, _ = validate_bssid(bssid)
            if not valid:
                print_status("Invalid BSSID format", "error")
                pause()
                continue
            ch = input("[?] Channel [1]: ").strip()
            gateway = input("[?] Gateway MAC (optional): ").strip()
            if gateway:
                valid_g, _ = validate_bssid(gateway)
                if not valid_g:
                    print_status("Invalid gateway MAC", "error")
                    pause()
                    continue
            airsnitch_attack(bssid, ch if ch else "1", gateway if gateway else None)
            pause()

        # MediaTek Overflow
        elif choice == "16":
            if not hardware_available:
                print_status("No USB adapter detected", "error")
                pause()
                continue
            bssid = input("[?] Target BSSID: ").strip()
            if not bssid:
                continue
            valid, _ = validate_bssid(bssid)
            if not valid:
                print_status("Invalid BSSID format", "error")
                pause()
                continue
            ch = input("[?] Channel [1]: ").strip()
            mediatek_heap_overflow(bssid, ch if ch else "1")
            pause()

        # PMKSA Poison
        elif choice == "17":
            if not hardware_available:
                print_status("No USB adapter detected", "error")
                pause()
                continue
            bssid = input("[?] Target BSSID: ").strip()
            if not bssid:
                continue
            valid, _ = validate_bssid(bssid)
            if not valid:
                print_status("Invalid BSSID format", "error")
                pause()
                continue
            client = input("[?] Client MAC: ").strip()
            if not client:
                print_status("Client MAC required", "error")
                pause()
                continue
            valid_c, _ = validate_bssid(client)
            if not valid_c:
                print_status("Invalid client MAC", "error")
                pause()
                continue
            ch = input("[?] Channel [1]: ").strip()
            pmksa_poison(bssid, client, ch if ch else "1")
            pause()

        # Status
        elif choice == "18":
            show_status()
            pause()

        # Channel Info
        elif choice == "19":
            show_channel_info()
            pause()

        # Settings
        elif choice == "20":
            settings_menu()

        else:
            print_status("Invalid selection", "error")
            time.sleep(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n")
        print_status("Interrupted – Cleaning up...", "warning")
        kill_all_processes()
        save_config()
        sys.exit(0)
    except Exception as e:
        print_status(f"Fatal error: {e}", "error")
        kill_all_processes()
        save_config()
        sys.exit(1)
