.DEFAULT_GOAL := help

.PHONY: help install install-dev test lint run run-migrate build-sidecar tauri-dev tauri-stop tauri-build setup-linux setup-macos setup-windows clean

help:
	@echo "AutonDB — available targets:"
	@echo ""
	@echo "  make install          Install/sync runtime dependencies"
	@echo "  make install-dev      Install runtime + dev dependencies"
	@echo "  make test             Run test suite"
	@echo "  make lint             Lint + format check (ruff)"
	@echo "  make run-migrate      Run a migration (set SOURCE_DSN, SOURCE_DIALECT, TARGET_DSN, TARGET_DIALECT)"
	@echo "  make build-sidecar    Build Python sidecar binary for Tauri"
	@echo "  make tauri-dev         Run Tauri in dev mode"
	@echo "  make tauri-stop        Stop Tauri dev server"
	@echo "  make tauri-build      Build Tauri desktop app"
	@echo "  make setup-linux      Install ALL dev deps on Debian/Ubuntu (first time)"
	@echo "  make setup-macos      Install ALL dev deps on macOS (first time)"
	@echo "  make setup-windows    Install ALL dev deps on Windows (first time)"
	@echo "  make clean            Remove caches and build artifacts"

install:
	uv sync

install-dev:
	uv sync --group dev

test:
	uv run pytest tests/ -v

lint:
	uv run ruff check src/ tests/
	uv run ruff format --check src/ tests/

run:
	@echo "Usage: make run SOURCE_DSN=<path> SOURCE_DIALECT=<sqlite|postgresql|mysql> TARGET_DSN=<path> TARGET_DIALECT=<sqlite|postgresql|mysql>"
	@exit 2

run-migrate: install
	uv run src/main.py \
		--source-dsn "$(SOURCE_DSN)" \
		--source-dialect "$(SOURCE_DIALECT)" \
		--target-dsn "$(TARGET_DSN)" \
		--target-dialect "$(TARGET_DIALECT)" \
		$(EXTRA_ARGS)

build-sidecar: install-dev
	./build-core.sh

tauri-dev: build-sidecar
	npx tauri dev

 tauri-stop:
	pkill -f "tauri dev" || pkill -f "src-tauri/target/debug/autondb" || true

tauri-build: build-sidecar
	npx tauri build

setup-linux:
	./setup-linux.sh

setup-macos:
	./setup-macos.sh

setup-windows:
	powershell -ExecutionPolicy Bypass -File ./setup-windows.ps1

clean:
	rm -rf .pytest_cache __pycache__ src/__pycache__ src/**/__pycache__
	rm -rf .ruff_cache
	rm -rf src-tauri/binaries/autondb-core*
	rm -rf target/
