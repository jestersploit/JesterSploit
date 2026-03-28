#!/bin/bash
# JesterSploit install script
# Creates a virtual environment and installs all Python dependencies

set -e  # Exit on any error
echo "[*] Starting JesterSploit installation..."

# Detect platform
OS=$(uname -s)

# Check Python3
if ! command -v python3 &>/dev/null; then
    echo "[!] Python3 not found. Installing..."
    if [[ "$OS" == "Linux" ]]; then
        sudo apt update
        sudo apt install -y python3 python3-venv python3-pip
    fi
fi

# Check pip
if ! command -v pip3 &>/dev/null; then
    echo "[!] pip3 not found. Installing..."
    if [[ "$OS" == "Linux" ]]; then
        sudo apt install -y python3-pip
    fi
fi

# Create virtual environment
VENV_DIR="./venv"
if [ ! -d "$VENV_DIR" ]; then
    echo "[*] Creating virtual environment in $VENV_DIR..."
    python3 -m venv "$VENV_DIR"
fi

# Activate virtual environment
echo "[*] Activating virtual environment..."
source "$VENV_DIR/bin/activate"

# Upgrade pip inside venv
pip install --upgrade pip

# Install Python dependencies
if [ -f "requirements.txt" ]; then
    echo "[*] Installing Python dependencies..."
    pip install -r requirements.txt
else
    echo "[!] requirements.txt not found!"
    exit 1
fi

echo "[*] Installation complete!"
echo "[*] To start JesterSploit, run:"
echo "    source $VENV_DIR/bin/activate && python jestersploit.py"
