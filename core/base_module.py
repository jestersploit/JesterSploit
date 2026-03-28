# core/base_module.py - NEW
import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from .dependencies import container

class BaseAttackModule(ABC):
    """Base class for all attack modules with dependency injection"""
    
    def __init__(self, interface: Optional[str] = None, **kwargs):
        self.interface = interface
        self.hardware = container.hardware()
        self.logger = logging.getLogger(f"module.{self.__class__.__name__}")
        self.config = kwargs
        self._running = False
        
    @abstractmethod
    def validate_prerequisites(self) -> bool:
        """Check if all required tools/hardware are available"""
        pass
    
    @abstractmethod
    def run(self) -> Dict[str, Any]:
        """Execute the attack, return results dict"""
        pass
    
    def stop(self) -> None:
        """Gracefully stop execution"""
        self._running = False
    
    def _check_tool(self, tool: str) -> bool:
        """Check if a system tool is available"""
        import shutil
        return shutil.which(tool) is not None
    
    def _log_secret(self, data: str) -> str:
        """Mask sensitive data in logs"""
        import re
        # Mask tokens (Discord, Telegram, etc)
        masked = re.sub(r'[A-Za-z0-9_-]{20,}', '[REDACTED_TOKEN]', data)
        masked = re.sub(r'bot\d+:[\w-]+', 'bot[REDACTED]:[REDACTED]', masked)
        return masked
