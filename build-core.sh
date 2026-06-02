#!/usr/bin/env bash
# Build the AutonDB Python core binary and copy it to Tauri's sidecar directory.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "==> Installing PyInstaller..."
uv sync --group dev

echo "==> Building Python core binary..."
uv run pyinstaller autondb-core.spec --noconfirm --clean

SIDE_CAR_DIR="src-tauri/binaries"
mkdir -p "$SIDE_CAR_DIR"

# Determine the platform-specific binary name
OS="$(uname -s)"
ARCH="$(uname -m)"

if [ "$OS" = "Linux" ]; then
    TARGET="autondb-core-x86_64-unknown-linux-gnu"
elif [ "$OS" = "Darwin" ]; then
    if [ "$ARCH" = "arm64" ]; then
        TARGET="autondb-core-aarch64-apple-darwin"
    else
        TARGET="autondb-core-x86_64-apple-darwin"
    fi
else
    TARGET="autondb-core-x86_64-pc-windows-msvc.exe"
fi

cp "dist/autondb-core" "$SIDE_CAR_DIR/$TARGET" 2>/dev/null || \
cp "dist/autondb-core.exe" "$SIDE_CAR_DIR/$TARGET" 2>/dev/null || \
{ echo "Error: binary not found in dist/"; exit 1; }

chmod +x "$SIDE_CAR_DIR/$TARGET"
echo "==> Core binary copied to $SIDE_CAR_DIR/$TARGET"
echo "==> Done! Run 'npx tauri dev' or 'npx tauri build' to build the desktop app."
