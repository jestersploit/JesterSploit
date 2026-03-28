#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import os
from typing import Tuple, Optional

from .hardware import VALID_CHANNELS, CHANNELS_24GHZ_EXTENDED


def validate_bssid(bssid: str) -> Tuple[bool, str]:
    """Validate MAC address format."""
    if not re.match(r'^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$', bssid):
        return False, "BSSID must be in format AA:BB:CC:DD:EE:FF"
    return True, ""


def validate_channel(channel: str) -> Tuple[bool, str, Optional[str]]:
    """Validate channel and return warning if restricted."""
    try:
        ch = int(channel)
    except ValueError:
        return False, "Channel must be a number", None
    if ch not in VALID_CHANNELS:
        return False, f"Invalid channel {ch}. Valid channels: 1-14, 36-165", None
    if ch in CHANNELS_24GHZ_EXTENDED:
        return True, "", f"Warning: Channel {ch} may be restricted in some countries"
    return True, "", None


def validate_file(path: str) -> Tuple[bool, str]:
    """Check if file exists and is readable."""
    if not os.path.exists(path):
        return False, f"File not found: {path}"
    if not os.path.isfile(path):
        return False, f"Not a regular file: {path}"
    if not os.access(path, os.R_OK):
        return False, f"File not readable (permissions): {path}"
    return True, ""


def validate_positive_int(val: str, name: str = "value") -> Tuple[bool, str, Optional[int]]:
    """Validate positive integer input."""
    if val == "":
        return True, "", None
    try:
        num = int(val)
        if num <= 0:
            return False, f"{name} must be a positive integer", None
        return True, "", num
    except ValueError:
        return False, f"{name} must be a number", None


def validate_optional_int(val: str, name: str = "value") -> Tuple[bool, str, Optional[int]]:
    """Validate optional integer; empty is OK."""
    if val == "":
        return True, "", None
    return validate_positive_int(val, name)
