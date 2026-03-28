#!/bin/bash
# Install.sh - UPDATED with validation

set -e

echo "[*] Installing JesterSploit..."

# Check Python version
PY_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
REQUIRED_VERSION="3.9"

if [[ "$(echo -e "$PY_VERSION\n$REQUIRED_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]]; then
    echo "Error: Python $REQUIRED_VERSION+ required, found $PY_VERSION"
    exit 1
fi

# Install Python dependencies
echo "[*] Installing Python packages..."
pip3 install -r requirements.txt

# Install system tools
echo "[*] Installing system tools..."
apt update
apt install -y \
    aircrack-ng \
    hcxtools \
    bully \
    reaver \
    pixiewps \
    hostapd \
    dnsmasq \
    hashcat \
    bettercap \
    iw \
    wireless-tools \
    usbutils

# Create directories
echo "[*] Creating directories..."
mkdir -p ~/.config/jestersploit
mkdir -p ~/.cache/jestersploit/logs

# Set permissions
chmod +x jestersploit.py

echo "[+] Installation complete!"
echo "[!] Run with: sudo ./jestersploit.py"
