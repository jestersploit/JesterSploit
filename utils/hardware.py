# utils/hardware_v2.py - NEW
import subprocess
import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

class ChipsetFamily(Enum):
    ATHEROS = "atheros"
    RALINK = "ralink"
    MEDIATEK = "mediatek"
    REALTEK = "realtek"
    INTEL = "intel"
    BROADCOM = "broadcom"
    UNKNOWN = "unknown"

class AdapterCapability(Enum):
    FULL = "full"           # Monitor + Injection
    MONITOR_ONLY = "monitor_only"  # Monitor mode only
    NONE = "none"           # Basic client only

@dataclass
class WiFiAdapter:
    interface: str
    driver: str
    chipset: ChipsetFamily
    chipset_model: str
    capabilities: AdapterCapability
    supports_5ghz: bool = False
    supports_wpa3: bool = False
    
class AdapterDetector:
    """Advanced WiFi adapter detection with injection testing"""
    
    # Known working chipsets (full injection)
    FULL_SUPPORT = {
        ChipsetFamily.ATHEROS: ['AR9271', 'AR9285', 'AR9287', 'AR9380'],
        ChipsetFamily.RALINK: ['RT3070', 'RT3072', 'RT3572', 'RT5370', 'RT5372'],
        ChipsetFamily.MEDIATEK: ['MT7612U', 'MT7610U', 'MT7921U', 'MT7922']
    }
    
    # Monitor-only chipsets
    MONITOR_ONLY = {
        ChipsetFamily.REALTEK: ['RTL8812AU', 'RTL8814AU', 'RTL8821AU', 'RTL8822BU'],
        ChipsetFamily.BROADCOM: ['BCM4360', 'BCM43602', 'BCM4331']
    }
    
    @classmethod
    def detect_all(cls) -> List[WiFiAdapter]:
        """Detect all WiFi adapters with capabilities"""
        adapters = []
        try:
            # Use iwconfig for interface list
            result = subprocess.run(['iwconfig'], capture_output=True, text=True)
            interfaces = re.findall(r'^(\w+)\s+IEEE', result.stdout, re.MULTILINE)
            
            for iface in interfaces:
                adapter = cls._inspect_adapter(iface)
                if adapter:
                    adapters.append(adapter)
        except (subprocess.SubprocessError, FileNotFoundError):
            pass
        
        return adapters
    
    @classmethod
    def _inspect_adapter(cls, interface: str) -> Optional[WiFiAdapter]:
        """Deep inspection of a single adapter"""
        try:
            # Get driver info via ethtool or sysfs
            driver = cls._get_driver(interface)
            if not driver:
                return None
            
            chipset = cls._identify_chipset(driver)
            model = cls._get_chipset_model(interface)
            
            # Test capabilities
            caps = cls._test_capabilities(interface)
            
            # Check 5GHz support
            supports_5ghz = cls._supports_5ghz(interface)
            
            # Check WPA3 support (via driver features)
            supports_wpa3 = cls._supports_wpa3(driver)
            
            return WiFiAdapter(
                interface=interface,
                driver=driver,
                chipset=chipset,
                chipset_model=model,
                capabilities=caps,
                supports_5ghz=supports_5ghz,
                supports_wpa3=supports_wpa3
            )
        except Exception:
            return None
    
    @classmethod
    def _get_driver(cls, interface: str) -> str:
        """Get driver name from sysfs"""
        try:
            result = subprocess.run(
                ['readlink', f'/sys/class/net/{interface}/device/driver'],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                return result.stdout.strip().split('/')[-1]
        except:
            pass
        return "unknown"
    
    @classmethod
    def _identify_chipset(cls, driver: str) -> ChipsetFamily:
        """Map driver to chipset family"""
        driver_lower = driver.lower()
        if any(x in driver_lower for x in ['ath', 'ar9', 'carl']):
            return ChipsetFamily.ATHEROS
        if any(x in driver_lower for x in ['rt', 'ralink']):
            return ChipsetFamily.RALINK
        if any(x in driver_lower for x in ['mt', 'mediatek']):
            return ChipsetFamily.MEDIATEK
        if any(x in driver_lower for x in ['rtl', 'r88']):
            return ChipsetFamily.REALTEK
        if 'iwl' in driver_lower:
            return ChipsetFamily.INTEL
        if 'brcm' in driver_lower:
            return ChipsetFamily.BROADCOM
        return ChipsetFamily.UNKNOWN
    
    @classmethod
    def _test_capabilities(cls, interface: str) -> AdapterCapability:
        """Test actual monitor mode and injection support"""
        # Check if monitor mode is supported
        try:
            # Try to set monitor mode temporarily
            subprocess.run(['ip', 'link', 'set', interface, 'down'], capture_output=True)
            subprocess.run(['iw', 'dev', interface, 'set', 'type', 'monitor'], capture_output=True)
            subprocess.run(['ip', 'link', 'set', interface, 'up'], capture_output=True)
            
            # Check if interface is now in monitor mode
            result = subprocess.run(['iw', 'dev', interface, 'info'], capture_output=True, text=True)
            if 'type monitor' in result.stdout:
                # Test injection with a single packet
                # Use aireplay-ng test if available
                test_result = subprocess.run(
                    ['timeout', '2', 'aireplay-ng', '-9', interface],
                    capture_output=True, text=True
                )
                if 'Injection is working' in test_result.stdout:
                    caps = AdapterCapability.FULL
                else:
                    caps = AdapterCapability.MONITOR_ONLY
            else:
                caps = AdapterCapability.NONE
        except:
            caps = AdapterCapability.NONE
        finally:
            # Restore managed mode
            try:
                subprocess.run(['ip', 'link', 'set', interface, 'down'], capture_output=True)
                subprocess.run(['iw', 'dev', interface, 'set', 'type', 'managed'], capture_output=True)
                subprocess.run(['ip', 'link', 'set', interface, 'up'], capture_output=True)
            except:
                pass
        
        return caps
    
    @classmethod
    def _supports_5ghz(cls, interface: str) -> bool:
        """Check if adapter supports 5GHz"""
        try:
            result = subprocess.run(['iw', 'list'], capture_output=True, text=True)
            # Find the section for this interface
            # Simplified: check if 5GHz frequencies appear
            return '5180 MHz' in result.stdout or '5200 MHz' in result.stdout
        except:
            return False
    
    @classmethod
    def _supports_wpa3(cls, driver: str) -> bool:
        """Check if driver supports WPA3"""
        # WPA3 requires drivers from ~2018+
        # Simplified check
        return driver not in ['ath9k_htc', 'rt2800usb', 'rt73usb']  # Legacy drivers
    
    @classmethod
    def _get_chipset_model(cls, interface: str) -> str:
        """Get specific chipset model"""
        try:
            result = subprocess.run(['lsusb'], capture_output=True, text=True)
            # Find USB devices with network interfaces
            # This is simplified; real implementation would parse USB IDs
            for line in result.stdout.split('\n'):
                if interface in line or '802.11' in line:
                    parts = line.split()
                    if len(parts) > 2:
                        return ' '.join(parts[2:])
        except:
            pass
        return "unknown"
