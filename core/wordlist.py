#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time
from utils.status import clear_screen, print_status, confirm_action
from utils.config import config, save_config
from utils.validator import validate_file

# Global list of wordlists (shared across modules)
current_wordlists = []


def set_wordlists(wordlists):
    global current_wordlists
    current_wordlists = wordlists


def show_wordlist_menu():
    """Interactive multi-wordlist selection menu."""
    global current_wordlists
    while True:
        clear_screen()
        print("=" * 50)
        print("WORDLIST SELECTION")
        print("=" * 50)
        print(f"Current wordlists ({len(current_wordlists)}):")
        for i, wl in enumerate(current_wordlists, 1):
            exists = "✓" if os.path.exists(wl) else "✗"
            color = "\033[92m" if os.path.exists(wl) else "\033[91m"
            print(f"  {color}{i}. {wl} [{exists}]\033[0m")
        print("\n1. Add wordlist")
        print("2. Remove wordlist")
        print("3. Clear all")
        print("4. Use default (rockyou.txt)")
        print("5. Keep current")
        print("6. Back to main menu")
        print("=" * 50)

        choice = input("[?] Select option [5]: ").strip() or "5"

        if choice == "1":
            while True:
                path = input("[?] Enter wordlist path: ").strip()
                if path == "":
                    print_status("Path cannot be empty. Try again or type 'cancel'.", "error")
                    if input().strip().lower() == "cancel":
                        break
                    continue
                valid, err = validate_file(path)
                if valid:
                    if path not in current_wordlists:
                        current_wordlists.append(path)
                        save_config()
                        print_status(f"Added: {path}", "success")
                    else:
                        print_status("Wordlist already in list", "warning")
                    break
                else:
                    print_status(err, "error")
                    if input("Press Enter to try again, or type 'cancel' to abort: ").strip().lower() == "cancel":
                        break
            time.sleep(1)

        elif choice == "2":
            if current_wordlists:
                idx = input("[?] Enter number to remove: ").strip()
                try:
                    idx = int(idx) - 1
                    if 0 <= idx < len(current_wordlists):
                        removed = current_wordlists.pop(idx)
                        save_config()
                        print_status(f"Removed: {removed}", "success")
                    else:
                        print_status("Invalid number", "error")
                except:
                    print_status("Invalid input", "error")
            else:
                print_status("No wordlists to remove", "warning")
            time.sleep(1)

        elif choice == "3":
            current_wordlists = []
            save_config()
            print_status("All wordlists cleared", "success")
            time.sleep(1)

        elif choice == "4":
            default_wl = "/usr/share/wordlists/rockyou.txt"
            if os.path.exists(default_wl):
                current_wordlists = [default_wl]
                save_config()
                print_status(f"Wordlist set: {default_wl}", "success")
            else:
                print_status(f"Default wordlist not found: {default_wl}", "error")
            time.sleep(1)

        elif choice == "5":
            print_status(f"Current wordlists: {len(current_wordlists)}", "info")
            break

        elif choice == "6":
            break

        else:
            print_status("Invalid choice", "error")
            time.sleep(1)
