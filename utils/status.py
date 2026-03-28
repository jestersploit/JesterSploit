#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import time
import os
from .colors import *


def print_status(message: str, status: str = "info") -> None:
    """Print colored status message."""
    colors = {
        "info": COLOR_CYAN,
        "success": COLOR_GREEN,
        "error": COLOR_RED,
        "warning": COLOR_YELLOW
    }
    prefixes = {
        "info": "[*]",
        "success": "[+]",
        "error": "[!]",
        "warning": "[?]"
    }
    color_code = colors.get(status, COLOR_RESET)
    prefix = prefixes.get(status, "[*]")
    print(f"{color_code}{prefix} {message}{COLOR_RESET}")


def pause() -> None:
    """Wait for user input."""
    print_status("Press Enter to continue...", "info")
    input()


def confirm_action(prompt: str, default: bool = False) -> bool:
    """Get user confirmation."""
    prompt = f"{prompt} [y/N]: " if not default else f"{prompt} [Y/n]: "
    response = input(prompt).strip().lower()
    if not response:
        return default
    return response in ('y', 'yes')


def clear_screen() -> None:
    """Clear terminal screen."""
    os.system('clear' if os.name == 'posix' else 'cls')


def spinning_cursor():
    """Generator for spinner animation."""
    while True:
        for cursor in '|/-\\':
            yield cursor


def animate_loading(message: str, duration: float = 0.8, step: float = 0.1) -> None:
    """Show loading spinner."""
    spinner = spinning_cursor()
    end_time = time.time() + duration
    while time.time() < end_time:
        sys.stdout.write(f"\r{message} {next(spinner)}")
        sys.stdout.flush()
        time.sleep(step)
    sys.stdout.write("\r" + " " * (len(message) + 2) + "\r")
    sys.stdout.flush()


def animate_dots(message: str, count: int = 3, delay: float = 0.3) -> None:
    """Show animated dots."""
    for i in range(1, count + 1):
        sys.stdout.write(f"\r{message}{'.' * i}")
        sys.stdout.flush()
        time.sleep(delay)
    sys.stdout.write("\r" + " " * (len(message) + count) + "\r")
    sys.stdout.flush()


class ProgressDisplay:
    """Non-blocking progress bar."""
    def __init__(self):
        self._running = False
        self._thread = None
        self._message = ""
        self._current = 0
        self._total = 100
        self._stop_flag = threading.Event()
        self._lock = threading.Lock()

    def start(self, message: str, total: int = 100):
        with self._lock:
            self._running = True
            self._message = message
            self._current = 0
            self._total = total
            self._stop_flag.clear()
        self._thread = threading.Thread(target=self._display_loop, daemon=True)
        self._thread.start()

    def update(self, current: int):
        with self._lock:
            self._current = min(current, self._total)

    def _display_loop(self):
        width = 40
        try:
            width = min(40, os.get_terminal_size().columns - 40)
        except:
            pass
        while not self._stop_flag.is_set():
            with self._lock:
                percent = int((self._current / self._total) * 100) if self._total > 0 else 0
                filled = int(width * percent / 100)
                bar = '█' * filled + '░' * (width - filled)
                sys.stdout.write(f"\r{self._message} [{bar}] {percent}%")
                sys.stdout.flush()
                if percent >= 100:
                    break
            time.sleep(0.2)
        sys.stdout.write("\n")
        sys.stdout.flush()

    def stop(self):
        self._stop_flag.set()
        if self._thread:
            self._thread.join(timeout=2)
        self._running = False
