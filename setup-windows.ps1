# AutonDB — Windows Setup (PowerShell)
# Run this once to install all dev dependencies on Windows.

Write-Host "==> AutonDB Windows Dev Setup" -ForegroundColor Cyan

# Rust
if (-not (Get-Command rustc -ErrorAction SilentlyContinue)) {
    Write-Host "==> Installing Rust..." -ForegroundColor Yellow
    winget install Rustlang.Rustup --accept-source-agreements --accept-package-agreements
} else {
    Write-Host "==> Rust already installed: $(rustc --version)" -ForegroundColor Green
}

# Node.js
if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    Write-Host "==> Installing Node.js..." -ForegroundColor Yellow
    winget install OpenJS.NodeJS.LTS --accept-source-agreements --accept-package-agreements
} else {
    Write-Host "==> Node already installed: $(node --version)" -ForegroundColor Green
}

# Python 3.13
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "==> Installing Python 3.13..." -ForegroundColor Yellow
    winget install Python.Python.3.13 --accept-source-agreements --accept-package-agreements
} else {
    Write-Host "==> Python already installed: $(python --version)" -ForegroundColor Green
}

# uv (Python package manager)
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "==> Installing uv..." -ForegroundColor Yellow
    winget install astral-sh.uv --accept-source-agreements --accept-package-agreements
} else {
    Write-Host "==> uv already installed: $(uv --version)" -ForegroundColor Green
}

Write-Host ""
Write-Host "==> Refreshing PATH..." -ForegroundColor Yellow
$env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")

Write-Host ""
Write-Host "==> Installing project dependencies..." -ForegroundColor Yellow
uv sync --group dev
npm install

Write-Host ""
Write-Host "==> All done! Run:" -ForegroundColor Cyan
Write-Host "    npx tauri dev" -ForegroundColor White
