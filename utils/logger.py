# utils/logger.py
import os
import sys
import logging
import logging.handlers
import re
from pathlib import Path
from typing import Optional

class SecretMaskingFilter(logging.Filter):
    """Filter that masks sensitive data in logs"""
    
    PATTERNS = [
        # Discord bot tokens
        (re.compile(r'[A-Za-z0-9_-]{24}\.[A-Za-z0-9_-]{6}\.[A-Za-z0-9_-]{27}'), '[DISCORD_TOKEN]'),
        # Telegram bot tokens
        (re.compile(r'\d+:[\w-]{35}'), '[TELEGRAM_TOKEN]'),
        # Webhook URLs
        (re.compile(r'https://discord\.com/api/webhooks/[\w-]+/[\w-]+'), '[WEBHOOK_URL]'),
        # API keys (generic)
        (re.compile(r'[\w-]{32,}'), '[API_KEY]'),
        # MAC addresses (partial)
        (re.compile(r'([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})'), '[MAC]'),
    ]
    
    def filter(self, record):
        if hasattr(record, 'msg') and isinstance(record.msg, str):
            for pattern, replacement in self.PATTERNS:
                record.msg = pattern.sub(replacement, record.msg)
        return True

def setup_logging(
    log_dir: str = None,
    level: str = "INFO",
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5
) -> logging.Logger:
    """Configure logging with rotation and secret masking"""
    
    if log_dir is None:
        log_dir = Path.home() / '.cache' / 'jestersploit' / 'logs'
    
    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Main logger
    logger = logging.getLogger('jestersploit')
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    
    # Remove existing handlers
    logger.handlers.clear()
    
    # File handler with rotation
    file_handler = logging.handlers.RotatingFileHandler(
        log_dir / 'jestersploit.log',
        maxBytes=max_bytes,
        backupCount=backup_count
    )
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    ))
    file_handler.addFilter(SecretMaskingFilter())
    logger.addHandler(file_handler)
    
    # Console handler (no sensitive data)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter(
        '%(levelname)s: %(message)s'
    ))
    console_handler.addFilter(SecretMaskingFilter())
    logger.addHandler(console_handler)
    
    # Attack logs separate
    attack_logger = logging.getLogger('jestersploit.attack')
    attack_logger.setLevel(logging.INFO)
    attack_handler = logging.handlers.RotatingFileHandler(
        log_dir / 'attacks.log',
        maxBytes=max_bytes,
        backupCount=backup_count
    )
    attack_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    ))
    attack_handler.addFilter(SecretMaskingFilter())
    attack_logger.addHandler(attack_handler)
    
    return logger
