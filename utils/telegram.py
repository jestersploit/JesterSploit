#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import subprocess
import time
import json
import threading
import logging
from typing import Optional

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    print("[!] requests library not available, falling back to curl")

from .config import config
from .status import print_status

telegram_running = True
logger = logging.getLogger(__name__)


def send_telegram_message(message: str, retries: int = 3) -> bool:
    """Send message to Telegram with exponential backoff."""
    if not config.get("telegram", {}).get("enabled", False):
        return False
    token = config["telegram"].get("token")
    chat_id = config["telegram"].get("chat_id")
    if not token or not chat_id:
        return False
    for attempt in range(retries):
        try:
            if len(message) > 4000:
                message = message[:3997] + "..."
            if REQUESTS_AVAILABLE:
                url = f"https://api.telegram.org/bot{token}/sendMessage"
                data = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
                response = requests.post(url, data=data, timeout=10)
                if response.status_code == 200:
                    return True
            else:
                cmd = ["curl", "-s", "-X", "POST",
                       f"https://api.telegram.org/bot{token}/sendMessage",
                       "-d", f"chat_id={chat_id}",
                       "-d", f"text={message}",
                       "-d", "parse_mode=Markdown",
                       "--max-time", "10"]
                result = subprocess.run(cmd, capture_output=True, timeout=15)
                if result.returncode == 0:
                    return True
        except Exception as e:
            logger.warning(f"Telegram error (attempt {attempt+1}): {e}")
        if attempt < retries - 1:
            time.sleep(2 ** attempt)
    return False


def send_telegram_progress(message: str, progress_percent: Optional[int] = None) -> None:
    """Send progress update with optional percentage bar."""
    if progress_percent is not None:
        bar_length = 20
        filled = int(bar_length * progress_percent / 100)
        bar = "█" * filled + "░" * (bar_length - filled)
        message = f"[{bar}] {progress_percent}% - {message}"
    send_telegram_message(message)


def telegram_command_handler():
    """Background thread to process Telegram commands."""
    global telegram_running
    last_update_id = 0
    while telegram_running:
        try:
            if REQUESTS_AVAILABLE and config.get("telegram", {}).get("enabled", False):
                token = config["telegram"]["token"]
                url = f"https://api.telegram.org/bot{token}/getUpdates"
                params = {"offset": last_update_id + 1, "timeout": 30}
                response = requests.get(url, params=params, timeout=35)
                if response.status_code == 200:
                    data = response.json()
                    if data.get("ok") and data.get("result"):
                        for update in data["result"]:
                            last_update_id = update["update_id"]
                            if "message" in update:
                                msg = update["message"]
                                if msg.get("chat", {}).get("id") == config["telegram"]["chat_id"]:
                                    text = msg.get("text", "").strip()
                                    if text:
                                        process_telegram_command(text)
        except Exception as e:
            logger.debug(f"Telegram polling error: {e}")
        time.sleep(1)


def process_telegram_command(command: str) -> None:
    """Process incoming Telegram commands."""
    import shlex
    from .hardware import hardware_available, gpu_name, gpu_available
    from .hardware import interface, monitor_interface
    from .validator import validate_bssid
    from .logger import capture_log, SESSION_ID
    from core.wordlist import current_wordlists
    from core.scanner import start_scan
    from core.pmkid import capture_pmkid
    from core.handshake import capture_handshake
    from core.deauth import deauth_attack
    from core.wps import wps_attack
    from core.crack import try_auto_crack
    from core.report import generate_report
    from .process import kill_all_processes

    parts = shlex.split(command)
    if not parts:
        return
    cmd = parts[0].lower()

    if cmd == "/start":
        msg = f"""🔥 *JESTERSPLOIT ACTIVE* 🔥

*Session:* `{SESSION_ID}`
*Hardware:* {'✅ Connected' if hardware_available else '❌ No adapter'}
*GPU:* {gpu_name if gpu_available else '❌ None'}
*Wordlists:* {len(current_wordlists)}

━━━━━━━━━━━━━━━━━━━━━━
📖 *Available Commands:*
━━━━━━━━━━━━━━━━━━━━━━

🔍 *RECONNAISSANCE*
`/scan [duration]` - Scan for networks
`/status` - System status

🎯 *ATTACKS*
`/attack pmkid <BSSID>` - PMKID capture
`/attack handshake <BSSID> [client]` - Handshake capture
`/attack deauth <BSSID>` - Deauth attack
`/attack wps <BSSID>` - WPS attack

🔓 *CRACKING*
`/crack <file>` - Crack hash file
`/wordlist [path]` - Set wordlist

📊 *RESULTS*
`/results` - Recent captures
`/report` - Generate full report

🛑 *CONTROL*
`/stop` - Stop all attacks
`/help` - Show this menu

━━━━━━━━━━━━━━━━━━━━━━
💡 *Quick Start:*
1. `/scan 30` - Find networks
2. `/attack pmkid <BSSID>` - Capture PMKID
3. `/crack /tmp/pmkid_*.22000` - Crack it

⚠️ *Use responsibly. Authorized testing only.*"""
        send_telegram_message(msg)
    elif cmd == "/help":
        help_text = """🔧 *JESTERSPLOIT Commands*

*Recon:*
`/scan [duration]` - Scan networks
`/status` - System status

*Attacks:*
`/attack pmkid <BSSID>` - PMKID capture
`/attack handshake <BSSID>` - Handshake capture
`/attack deauth <BSSID>` - Deauth attack
`/attack wps <BSSID>` - WPS attack

*Cracking:*
`/crack <file>` - Crack hash
`/wordlist [path]` - Set wordlist

*Results:*
`/results` - Recent captures
`/report` - Full report

*Control:*
`/stop` - Stop all attacks
`/help` - This menu

*Example:*
`/attack pmkid 00:11:22:33:44:55`
`/crack /tmp/pmkid_xxx.22000`

Type `/start` for full welcome message."""
        send_telegram_message(help_text)
    elif cmd == "/status":
        adapter_status = "✅ Connected" if hardware_available else "❌ Not connected"
        gpu_status = f"✅ {gpu_name}" if gpu_available else "❌ None"
        recent = ""
        if capture_log:
            recent = "\n\n📦 *Recent Captures:*\n"
            for entry in capture_log[-3:]:
                recent += f"   • {entry.get('event', 'unknown')}: `{entry.get('bssid', 'N/A')}`\n"
        else:
            recent = "\n\n📦 *No captures yet*"
        status = f"""📊 *JESTERSPLOIT STATUS*

━━━━━━━━━━━━━━━━━━━━━━
🔌 *HARDWARE*
━━━━━━━━━━━━━━━━━━━━━━
USB Adapter: {adapter_status}
{'   Interface: ' + interface if hardware_available else ''}
{'   Monitor: ' + monitor_interface if monitor_interface else ''}

🖥️ *GPU*
━━━━━━━━━━━━━━━━━━━━━━
Status: {gpu_status}
CPU: {cpu_model} ({cpu_cores} cores)
RAM: {total_ram} MB

📚 *WORDLISTS*
━━━━━━━━━━━━━━━━━━━━━━
Files: {len(current_wordlists)}
Total lines: {sum(os.path.getsize(wl) / 1024 for wl in current_wordlists if os.path.exists(wl)):.0f} KB

🆔 *SESSION*
━━━━━━━━━━━━━━━━━━━━━━
ID: `{SESSION_ID}`
Uptime: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
{recent}

━━━━━━━━━━━━━━━━━━━━━━
💡 `/help` for commands"""
        send_telegram_message(status)
    elif cmd == "/scan":
        duration = 30
        if len(parts) > 1:
            try:
                duration = int(parts[1])
                if duration < 5: duration = 5
                if duration > 120: duration = 120
            except:
                pass
        if not hardware_available:
            send_telegram_message("❌ *No USB adapter detected* - Connect your adapter and try again.")
            return
        send_telegram_message(f"🔍 *Starting scan* ({duration}s)...\nThis will take about {duration} seconds.")
        threading.Thread(target=start_scan, args=(duration,), daemon=True).start()
    elif cmd == "/attack":
        if len(parts) < 3:
            send_telegram_message("❌ *Usage:* `/attack <type> <BSSID> [client]`\n\n*Types:* pmkid, handshake, deauth, wps\n\n*Example:* `/attack pmkid 00:11:22:33:44:55`")
            return
        if not hardware_available:
            send_telegram_message("❌ *No USB adapter detected* - Connect your adapter and try again.")
            return
        attack_type = parts[1].lower()
        bssid = parts[2].upper()
        valid, err = validate_bssid(bssid)
        if not valid:
            send_telegram_message(f"❌ *Invalid BSSID format:* `{bssid}`\n\n{err}")
            return
        if attack_type == "pmkid":
            send_telegram_message(f"🎯 *PMKID attack started* on `{bssid}`\nThis will take ~60 seconds...")
            threading.Thread(target=capture_pmkid, args=(bssid,), daemon=True).start()
        elif attack_type == "handshake":
            client = parts[3] if len(parts) > 3 else None
            if client:
                valid_c, err_c = validate_bssid(client)
                if not valid_c:
                    send_telegram_message(f"❌ *Invalid client MAC:* `{client}`\n\n{err_c}")
                    return
            msg = f"🎯 *Handshake capture started* on `{bssid}`"
            if client:
                msg += f"\nTargeting client: `{client}`"
            msg += "\nSending deauth frames... This will take ~35 seconds."
            send_telegram_message(msg)
            threading.Thread(target=capture_handshake, args=(bssid, None, client), daemon=True).start()
        elif attack_type == "deauth":
            count = 10
            if len(parts) > 3:
                try:
                    count = int(parts[3])
                except:
                    pass
            send_telegram_message(f"⚠️ *Deauth attack* on `{bssid}`\nSending {count} frames...")
            threading.Thread(target=deauth_attack, args=(bssid, count, None), daemon=True).start()
        elif attack_type == "wps":
            send_telegram_message(f"🔑 *WPS attack started* on `{bssid}`\nThis may take several minutes...")
            threading.Thread(target=wps_attack, args=(bssid,), daemon=True).start()
        else:
            send_telegram_message("❌ *Invalid attack type*\n\nAvailable: `pmkid`, `handshake`, `deauth`, `wps`\n\nExample: `/attack pmkid 00:11:22:33:44:55`")
    elif cmd == "/crack":
        if len(parts) > 1:
            file_path = parts[1]
            valid_f, err_f = validate_file(file_path)
            if not valid_f:
                send_telegram_message(f"❌ *File not found:* `{file_path}`\n\n{err_f}")
            else:
                send_telegram_message(f"🔓 *Cracking started* on `{os.path.basename(file_path)}`\nThis may take time...")
                threading.Thread(target=try_auto_crack, args=(file_path,), daemon=True).start()
        else:
            send_telegram_message("❌ *Usage:* `/crack <file_path>`\n\nExample: `/crack /tmp/pmkid_xxx.22000`")
    elif cmd == "/wordlist":
        if len(parts) > 1:
            path = " ".join(parts[1:])
            valid_f, err_f = validate_file(path)
            if valid_f:
                current_wordlists = [path]
                save_config()
                send_telegram_message(f"✅ *Wordlist set:* `{path}`")
            else:
                send_telegram_message(f"❌ *Wordlist not found:* `{path}`\n\n{err_f}")
        else:
            wl_list = "\n".join([f"   • `{wl}`" for wl in current_wordlists])
            send_telegram_message(f"📚 *Current wordlists ({len(current_wordlists)}):*\n{wl_list}")
    elif cmd == "/results":
        if capture_log:
            recent = capture_log[-10:]
            msg = "📋 *Recent Captures:*\n\n"
            for entry in reversed(recent):
                timestamp = entry['timestamp'][:19]
                event = entry.get('event', 'unknown')
                bssid = entry.get('bssid', 'N/A')
                file = entry.get('file', '')
                file_name = os.path.basename(file) if file else ''
                msg += f"• `{timestamp}`\n  *{event}* on `{bssid}`"
                if file_name:
                    msg += f"\n  📁 {file_name}"
                msg += "\n\n"
            if len(capture_log) > 10:
                msg += f"\n_... and {len(capture_log) - 10} more captures_"
            send_telegram_message(msg)
        else:
            send_telegram_message("📭 *No captures yet*\n\nRun `/scan` to find networks, then `/attack` to capture.")
    elif cmd == "/report":
        send_telegram_message("📄 *Generating report...*")
        report_path = generate_report()
        send_telegram_message(f"✅ *Report generated:* `{report_path}`")
    elif cmd == "/stop":
        send_telegram_message("🛑 *Stopping all attacks...*")
        kill_all_processes()
        send_telegram_message("✅ *All processes stopped*")
    else:
        send_telegram_message(f"❌ *Unknown command:* `{cmd}`\n\nType `/help` to see available commands.")
