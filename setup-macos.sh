#!/usr/bin/env bash
# AutonDB — macOS Dev Setup
# Run once: ./setup-macos.sh
set -euo pipefail

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

info()  { echo -e "${CYAN}==> $1${NC}"; }
ok()    { echo -e "${GREEN}    ✓ $1${NC}"; }
warn()  { echo -e "${YELLOW}    → $1${NC}"; }

# ── Homebrew ─────────────────────────────────────────────────
if command -v brew &>/dev/null; then
    ok "Homebrew already installed"
else
    info "Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    eval "$(/opt/homebrew/bin/brew shellenv)" 2>/dev/null || eval "$(/usr/local/bin/brew shellenv)" 2>/dev/null || true
    ok "Homebrew installed"
fi

# ── System deps ──────────────────────────────────────────────
info "Installing system dependencies..."
brew install pkg-config

# ── Rust ──────────────────────────────────────────────────────
if command -v rustc &>/dev/null; then
    ok "Rust already installed: $(rustc --version)"
else
    info "Installing Rust via rustup..."
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
    source "$HOME/.cargo/env"
    ok "Rust installed: $(rustc --version)"
fi

# ── Node.js ──────────────────────────────────────────────────
if command -v node &>/dev/null; then
    ok "Node already installed: $(node --version)"
else
    info "Installing Node.js 22 LTS..."
    brew install node@22
    brew link node@22 2>/dev/null || true
    ok "Node installed: $(node --version)"
fi

# ── Python 3.13 ──────────────────────────────────────────────
if python3.13 --version &>/dev/null; then
    ok "Python 3.13 already installed: $(python3.13 --version)"
else
    info "Installing Python 3.13..."
    brew install python@3.13
    ok "Python installed: $(python3.13 --version)"
fi

# ── uv ────────────────────────────────────────────────────────
if command -v uv &>/dev/null; then
    ok "uv already installed: $(uv --version)"
else
    info "Installing uv..."
    brew install uv
    ok "uv installed: $(uv --version)"
fi

# ── Project deps ─────────────────────────────────────────────
info "Installing project dependencies..."
uv sync --group dev
npm install
ok "Project dependencies installed"

# ── Done ─────────────────────────────────────────────────────
echo ""
info "All done! Next steps:"
echo -e "    ${YELLOW}./build-core.sh${NC}    # Build Python sidecar binary"
echo -e "    ${YELLOW}npx tauri dev${NC}       # Run in dev mode"
echo -e "    ${YELLOW}npx tauri build${NC}     # Build production app (.dmg)"
