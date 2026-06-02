#!/usr/bin/env bash
# Install system dependencies required to build Tauri on Linux (Debian/Ubuntu).
# Run this script once before building: ./setup-linux.sh
set -euo pipefail

echo "==> Installing Tauri system dependencies..."
echo "    This requires sudo — you may be prompted for your password."

sudo apt update
sudo apt install -y \
    pkg-config \
    libdbus-1-dev \
    libgtk-3-dev \
    libwebkit2gtk-4.1-dev \
    libappindicator3-dev \
    librsvg2-dev \
    libsoup-3.0-dev \
    libjavascriptcoregtk-4.1-dev

echo ""
echo "==> System dependencies installed!"
echo "==> Next steps:"
echo "    1. ./build-core.sh          # Build the Python sidecar binary"
echo "    2. npx tauri dev            # Run in dev mode"
echo "    3. npx tauri build          # Build production app"
