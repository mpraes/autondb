# Release Guide

## Overview

The release pipeline is triggered by **semver tags** (`v*.*.*`) or **manually** via GitHub Actions. It compiles the Python binary once per architecture, packages the Tauri app for all platforms, and publishes everything to a GitHub Release.

> **Tests CI**: the `.github/workflows/tests.yml` workflow runs lint + tests on every push/PR to `main`. See [docs/contributing.md](contributing.md) for details.

## Full Flow

### 1. Prepare the CHANGELOG

Before tagging, move changes from `[Unreleased]` to the new version in `CHANGELOG.md`:

```markdown
## [1.2.0] - 2025-07-15

### Added
- New feature X

### Fixed
- Bug Y fixed

## [Unreleased]

### Added
- (empty — future changes go here)
```

Update the footer links:

```markdown
[unreleased]: https://github.com/renan/autondb/compare/v1.2.0...HEAD
[1.2.0]: https://github.com/renan/autondb/compare/v1.1.0...v1.2.0
```

### 2. Commit and tag

```bash
# Commit the updated changelog
git add CHANGELOG.md
git commit -m "chore: update CHANGELOG for v1.2.0"

# Create the tag
git tag v1.2.0

# Push commit + tag
git push origin main
git push origin v1.2.0
```

> Alternatively, push everything at once: `git push origin main v1.2.0`

### 3. The pipeline runs automatically

When it detects the tag `v1.2.0`, the workflow `.github/workflows/release.yml` runs:

| Job | Description |
|-----|-------------|
| `prepare` | Validates tag, extracts version, detects prerelease, extracts CHANGELOG section |
| `build-sidecar` | Compiles `autondb-core` via PyInstaller (4 architectures) |
| `build-tauri` | Downloads pre-built sidecar, compiles Rust, packages installers |
| `publish-cli` | Publishes standalone CLI binaries to the Release |

### 4. The Release is created

The Release appears in **GitHub → Releases** with:

- **Title**: `AutonDB v1.2.0`
- **Body**: section extracted from `CHANGELOG.md`
- **Artifacts**: installers + CLI binaries

## Reference Commands

### Create a normal release

```bash
git tag v1.2.0
git push origin v1.2.0
```

### Create a prerelease (alpha/beta/rc)

```bash
git tag v1.2.0-beta.1
git push origin v1.2.0-beta.1
```

Tags containing `alpha`, `beta`, `rc` or `pre` are automatically marked as **prerelease**.

### Manual release (no tag)

1. Go to **GitHub → Actions → Release**
2. Click **Run workflow**
3. Enter the version (e.g. `v1.2.0`)
4. Click **Run**

### Extract changelog for a version (local)

```bash
# Specific version
awk -v ver="1.2.0" '
  BEGIN { hdr = "## [" ver "]" }
  index($0, hdr) == 1 { flag=1; next }
  flag && index($0, "## [") == 1 { exit }
  flag && index($0, "[") == 1 && index($0, "]:") == 1 { exit }
  flag { print }
' CHANGELOG.md

# Unreleased
awk -v ver="Unreleased" '
  BEGIN { hdr = "## [" ver "]" }
  index($0, hdr) == 1 { flag=1; next }
  flag && index($0, "## [") == 1 { exit }
  flag && index($0, "[") == 1 && index($0, "]:") == 1 { exit }
  flag { print }
' CHANGELOG.md
```

### List local tags

```bash
git tag --list 'v*'
```

### Delete tag (if you need to fix)

```bash
# Local
git tag -d v1.2.0

# Remote
git push origin :refs/tags/v1.2.0
```

### Delete release via GitHub CLI

```bash
gh release delete v1.2.0 --yes
```

## Artifacts by Platform

| Artifact | Platform | Install |
|----------|----------|---------|
| `.msi` | Windows | Double-click to install |
| `.dmg` | macOS | Open, drag to Applications |
| `.deb` | Debian/Ubuntu | `sudo dpkg -i <file>` |
| `.AppImage` | Any Linux | `chmod +x <file> && ./<file>` |
| `autondb-core-x86_64-pc-windows-msvc.exe` | Windows | Standalone CLI |
| `autondb-core-x86_64-unknown-linux-gnu` | Linux x86_64 | Standalone CLI |
| `autondb-core-aarch64-apple-darwin` | macOS Apple Silicon | Standalone CLI |
| `autondb-core-x86_64-apple-darwin` | macOS Intel | Standalone CLI |

## Pipeline Architecture

```
git tag v1.2.0 ──push──▶ GitHub Actions
                              │
                              ▼
                         ┌─────────┐
                         │ prepare  │  validates tag, extracts changelog
                         └────┬─────┘
                              │
                              ▼
                     ┌───────────────┐
                     │ build-sidecar │  PyInstaller × 4 architectures
                     └───────┬───────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
     ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
     │ build-tauri  │ │ build-tauri  │ │ build-tauri  │  Windows/macOS/Linux
     │   (Windows)  │ │   (macOS)    │ │   (Linux)    │
     └──────┬───────┘ └──────┬───────┘ └──────┬───────┘
            │                │                │
            └────────────────┼────────────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │  publish-cli    │  Publishes CLI binaries to Release
                    └─────────────────┘
```

## App Versions

The version is defined in **3 places** that must be kept in sync:

| File | Field | Example |
|------|-------|---------|
| `CHANGELOG.md` | `## [1.2.0]` | Section header |
| `src-tauri/tauri.conf.json` | `"version": "1.2.0"` | Tauri bundle version |
| `pyproject.toml` | `version = "1.2.0"` | Python package version |

> The workflow reads the version from the **tag**, not from these files. But they must be in sync for consistency.

## Release Checklist

- [ ] Move entries from `[Unreleased]` to `[x.y.z]` in `CHANGELOG.md`
- [ ] Update date in version header
- [ ] Update footer links (`[unreleased]` and `[x.y.z]`)
- [ ] Update `version` in `src-tauri/tauri.conf.json`
- [ ] Update `version` in `pyproject.toml`
- [ ] Commit: `git commit -m "chore: release v1.2.0"`
- [ ] Tag: `git tag v1.2.0`
- [ ] Push: `git push origin main v1.2.0`
- [ ] Verify the workflow in **GitHub → Actions**
- [ ] Confirm the Release in **GitHub → Releases**
- [ ] Download and test the installer for your platform
