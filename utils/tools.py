# utils/tools.py 
import subprocess
import shutil
import logging
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

@dataclass
class ToolInfo:
    name: str
    executable: str
    required: bool
    min_version: Optional[str] = None
    purpose: str = ""

class ToolValidator:
    """Validate and manage system tool dependencies"""
    
    REQUIRED_TOOLS = [
        ToolInfo("aircrack-ng", "aircrack-ng", True, "1.7", "WEP/WPA cracking"),
        ToolInfo("airodump-ng", "airodump-ng", True, None, "Packet capture"),
        ToolInfo("aireplay-ng", "aireplay-ng", True, None, "Packet injection"),
        ToolInfo("airmon-ng", "airmon-ng", True, None, "Interface management"),
        ToolInfo("hcxdumptool", "hcxdumptool", False, "6.0", "PMKID capture"),
        ToolInfo("hcxpcapngtool", "hcxpcapngtool", False, "6.0", "PCAP conversion"),
        ToolInfo("bully", "bully", False, "1.1", "WPS attack"),
        ToolInfo("reaver", "reaver", False, "1.6", "WPS brute force"),
        ToolInfo("pixiewps", "pixiewps", False, "1.4", "WPS pixie dust"),
        ToolInfo("hostapd", "hostapd", False, "2.6", "Access point"),
        ToolInfo("dnsmasq", "dnsmasq", False, "2.80", "DHCP/DNS"),
        ToolInfo("hashcat", "hashcat", False, "6.0", "GPU cracking"),
        ToolInfo("bettercap", "bettercap", False, "2.30", "Network attacks"),
    ]
    
    def __init__(self):
        self.logger = logging.getLogger("tool_validator")
        self.available = {}
        self.versions = {}
        self._validate_all()
    
    def _validate_all(self) -> None:
        """Check all required and optional tools"""
        for tool in self.REQUIRED_TOOLS:
            self._check_tool(tool)
    
    def _check_tool(self, tool: ToolInfo) -> bool:
        """Check a single tool"""
        path = shutil.which(tool.executable)
        if not path:
            if tool.required:
                self.logger.error(f"Required tool missing: {tool.name}")
            self.available[tool.name] = False
            return False
        
        version = self._get_version(tool)
        self.available[tool.name] = True
        self.versions[tool.name] = version
        
        if tool.min_version and version:
            if not self._version_ge(version, tool.min_version):
                self.logger.warning(f"{tool.name} version {version} < {tool.min_version}")
                return False
        
        return True
    
    def _get_version(self, tool: ToolInfo) -> Optional[str]:
        """Get tool version via --version"""
        try:
            result = subprocess.run(
                [tool.executable, '--version'],
                capture_output=True, text=True, timeout=5
            )
            # Parse version from output
            import re
            match = re.search(r'(\d+\.\d+(?:\.\d+)?)', result.stdout or result.stderr)
            if match:
                return match.group(1)
        except (subprocess.SubprocessError, FileNotFoundError):
            pass
        return None
    
    def _version_ge(self, version: str, min_version: str) -> bool:
        """Compare version strings"""
        def parse(v):
            return [int(x) for x in v.split('.')]
        try:
            return parse(version) >= parse(min_version)
        except:
            return False
    
    def check_prerequisites(self, required: List[str]) -> Tuple[bool, List[str]]:
        """Check if specific tools are available"""
        missing = []
        for tool in required:
            if not self.available.get(tool, False):
                missing.append(tool)
        return len(missing) == 0, missing
    
    def get_install_command(self) -> str:
        """Generate installation command for missing tools"""
        missing = [t.name for t in self.REQUIRED_TOOLS 
                  if t.required and not self.available.get(t.name, False)]
        if missing:
            return f"sudo apt install -y {' '.join(missing)}"
        return ""
