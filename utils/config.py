# utils/config.py 
import os
import json
import getpass
from pathlib import Path
from typing import Dict, Any, Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

class SecureConfig:
    """Portable, encrypted configuration manager"""
    
    CONFIG_DIR = Path.home() / '.config' / 'jestersploit'
    CONFIG_FILE = CONFIG_DIR / 'config.json'
    KEY_FILE = CONFIG_DIR / '.key'
    
    def __init__(self):
        self.config_dir = self.CONFIG_DIR
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self._cipher = None
        self._load_or_create_key()
        
    def _load_or_create_key(self):
        """Load existing key or create new one"""
        if self.KEY_FILE.exists():
            with open(self.KEY_FILE, 'rb') as f:
                key = f.read()
        else:
            # Generate new key
            key = Fernet.generate_key()
            with open(self.KEY_FILE, 'wb') as f:
                f.write(key)
            os.chmod(self.KEY_FILE, 0o600)  # Only owner can read
        self._cipher = Fernet(key)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value"""
        config = self._load_config()
        keys = key.split('.')
        value = config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value
    
    def set(self, key: str, value: Any, encrypt: bool = False):
        """Set a configuration value"""
        config = self._load_config()
        keys = key.split('.')
        target = config
        for k in keys[:-1]:
            target = target.setdefault(k, {})
        
        if encrypt:
            value = self._encrypt_value(value)
        
        target[keys[-1]] = value
        self._save_config(config)
    
    def _load_config(self) -> Dict:
        if self.CONFIG_FILE.exists():
            with open(self.CONFIG_FILE, 'r') as f:
                return json.load(f)
        return self._default_config()
    
    def _save_config(self, config: Dict):
        with open(self.CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        os.chmod(self.CONFIG_FILE, 0o600)
    
    def _default_config(self) -> Dict:
        return {
            "telegram": {
                "bot_token": None,  # Will be encrypted
                "chat_id": None
            },
            "webhook": {
                "url": None
            },
            "logging": {
                "level": "INFO",
                "max_size_mb": 10,
                "backup_count": 5
            },
            "attacks": {
                "deauth_count": 64,
                "handshake_timeout": 60
            }
        }
    
    def _encrypt_value(self, value: Any) -> str:
        """Encrypt a sensitive value"""
        if isinstance(value, str):
            encrypted = self._cipher.encrypt(value.encode())
            return f"$ENC${base64.urlsafe_b64encode(encrypted).decode()}"
        return value
    
    def decrypt_value(self, value: str) -> str:
        """Decrypt an encrypted value"""
        if isinstance(value, str) and value.startswith("$ENC$"):
            encrypted = base64.urlsafe_b64decode(value[5:])
            return self._cipher.decrypt(encrypted).decode()
        return value
    
    def get_credentials(self, service: str) -> Optional[Dict]:
        """Get decrypted credentials for a service"""
        creds = self.get(f"credentials.{service}")
        if not creds:
            return None
        return {k: self.decrypt_value(v) for k, v in creds.items()}
