# core/context.py - NEW
import os
import platform
import subprocess
from dataclasses import dataclass
from typing import Optional, Dict, Any

@dataclass
class HardwareContext:
    gpu_available: bool = False
    gpu_type: Optional[str] = None
    cpu_model: str = ""
    ram_gb: int = 0
    
    @classmethod
    def detect(cls) -> 'HardwareContext':
        ctx = cls()
        ctx.cpu_model = platform.processor() or "Unknown"
        
        try:
            # Detect GPU via nvidia-smi
            result = subprocess.run(['nvidia-smi', '--query-gpu=name', '--format=csv,noheader'], 
                                   capture_output=True, text=True, timeout=5)
            if result.returncode == 0 and result.stdout.strip():
                ctx.gpu_available = True
                ctx.gpu_type = result.stdout.strip().split('\n')[0]
        except (FileNotFoundError, subprocess.TimeoutExpired):
            # Try hashcat --backend-info for AMD/OpenCL
            try:
                result = subprocess.run(['hashcat', '--backend-info'], capture_output=True, text=True, timeout=5)
                if 'OpenCL' in result.stdout and 'Platform' in result.stdout:
                    ctx.gpu_available = True
                    ctx.gpu_type = "OpenCL"
            except (FileNotFoundError, subprocess.TimeoutExpired):
                pass
        
        # Get RAM
        try:
            with open('/proc/meminfo', 'r') as f:
                for line in f:
                    if line.startswith('MemTotal:'):
                        ctx.ram_gb = int(line.split()[1]) // (1024 * 1024)
                        break
        except (IOError, ValueError):
            pass
        
        return ctx

# core/dependencies.py - NEW
from typing import Dict, Any, Optional
from .context import HardwareContext

class DependencyContainer:
    """Central dependency injection container"""
    _instance = None
    _dependencies: Dict[str, Any] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._dependencies = {}
        return cls._instance
    
    def register(self, name: str, dependency: Any) -> None:
        self._dependencies[name] = dependency
    
    def get(self, name: str) -> Any:
        return self._dependencies.get(name)
    
    def hardware(self) -> HardwareContext:
        return self._dependencies.get('hardware', HardwareContext.detect())
    
    def set_hardware(self, ctx: HardwareContext) -> None:
        self._dependencies['hardware'] = ctx

container = DependencyContainer()
