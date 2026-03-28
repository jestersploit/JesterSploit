#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import subprocess
import time
import re
import select
from typing import Optional

from utils.validator import validate_file
from utils.hardware import gpu_available, gpu_type
from utils.logger import attack_logger, bug_logger, log_capture
from utils.process import active_processes, add_process, remove_process, is_cancelled, set_cancel_flag
from utils.config import config
from core.wordlist import current_wordlists


def set_wordlists(wordlists) -> None:
    """Set the wordlists to be used for cracking (external call)."""
    global current_wordlists
    current_wordlists = wordlists


def try_auto_crack(file_path: str, hash_type: str = "auto", session_id: str = None) -> Optional[str]:
    """
    Attempt to crack a captured hash using configured wordlists.
    Returns the cracked password or None.
    """
    set_cancel_flag(False)

    if not current_wordlists:
        print("[!] No wordlists configured")
        return None

    valid, err = validate_file(file_path)
    if not valid:
        print(f"[!] {err}")
        return None

    # Determine hash type
    if hash_type == "auto":
        if file_path.endswith('.22000'):
            hash_type = "pmkid"
        elif file_path.endswith('.cap'):
            hash_type = "handshake"
        else:
            print("[?] Unknown hash type, assuming PMKID")
            hash_type = "pmkid"

    print(f"[*] Cracking: {file_path}")
    print(f"[*] Wordlists: {len(current_wordlists)} file(s)")

    output_file = f"{file_path}.cracked"

    for wl_idx, wordlist in enumerate(current_wordlists, 1):
        if is_cancelled():
            print("[!] Cracking cancelled")
            return None

        valid_wl, err_wl = validate_file(wordlist)
        if not valid_wl:
            print(f"[!] Wordlist not found: {wordlist} - {err_wl}")
            continue

        print(f"[*] Using wordlist {wl_idx}/{len(current_wordlists)}: {wordlist}")

        if hash_type == "pmkid":
            # Optional benchmark for first wordlist if GPU available
            if wl_idx == 1 and gpu_available:
                print("[*] Running GPU benchmark...")
                try:
                    bench = subprocess.run(
                        ['hashcat', '-b', '-m', '22000', '--force', '--quiet'],
                        capture_output=True, text=True, timeout=60
                    )
                    speed_match = re.search(r'Speed.*?(\d+\.?\d*)\s*([KMGT]?H/s)', bench.stdout)
                    if speed_match:
                        print(f"[*] Benchmark speed: {speed_match.group(1)} {speed_match.group(2)}")
                except:
                    pass

            cmd = [
                'hashcat', '-m', '22000', file_path, wordlist,
                '-o', output_file, '--force', '--quiet', '--status', '--status-timer=2'
            ]
            if config.get('cracking', {}).get('gpu_enabled', True) and gpu_available:
                cmd.append('-O')
                if gpu_type == 'nvidia':
                    cmd.extend(['--gpu-temp-abort', '90'])
                    print("[*] Using NVIDIA GPU acceleration")
                elif gpu_type == 'amd':
                    print("[*] Using AMD GPU acceleration")

            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            add_process(proc)

            max_time = config.get('cracking', {}).get('max_crack_time', 600)
            # Check every 2 seconds
            for _ in range(max_time // 2):
                if is_cancelled():
                    proc.terminate()
                    remove_process(proc)
                    return None
                if proc.poll() is not None:
                    break
                if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
                    proc.terminate()
                    remove_process(proc)
                    with open(output_file, 'r') as f:
                        password = f.read().strip().split('\n')[-1]
                        if ':' in password:
                            password = password.split(':')[-1]
                        elif ' ' in password:
                            password = password.split()[-1]
                    print(f"[+] CRACKED: {password}")
                    log_capture("cracked", "", "", output_file)
                    return password
                time.sleep(2)
            proc.terminate()
            remove_process(proc)

        else:  # handshake
            cmd = ['aircrack-ng', '-w', wordlist, file_path, '-l', output_file]
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            add_process(proc)
            for _ in range(60):  # 60 * 2 = 120 seconds
                if is_cancelled():
                    proc.terminate()
                    remove_process(proc)
                    return None
                if proc.poll() is not None:
                    break
                if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
                    proc.terminate()
                    remove_process(proc)
                    with open(output_file, 'r') as f:
                        password = f.read().strip()
                    print(f"[+] CRACKED: {password}")
                    log_capture("cracked", "", "", output_file)
                    return password
                time.sleep(2)
            proc.terminate()
            remove_process(proc)

        print(f"[!] Wordlist {wl_idx}/{len(current_wordlists)} failed")

    print("[!] Cracking failed with all wordlists")
    return None
