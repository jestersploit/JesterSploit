#!/bin/bash
# cleanup_repo.sh - Remove versioned scripts

echo "[*] Cleaning up repository..."

# Remove duplicate versioned files
find . -name "*_v2.py" -type f -delete
find . -name "*_fixed.py" -type f -delete
find . -name "*_prototype.py" -type f -delete
find . -name "*_old.py" -type f -delete

# Ensure consistent shebangs
find . -name "*.py" -type f -exec sed -i '1s|^#!.*|#!/usr/bin/env python3|' {} \;

# Set correct permissions
chmod +x *.py
chmod +x Install.sh

echo "[+] Cleanup complete"
