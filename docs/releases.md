# Guia de Releases e GitHub Actions

## Visão Geral

O pipeline de release é acionado por **tags semver** (`v*.*.*`) ou **manualmente** via GitHub Actions. Ele compila o binário Python uma vez por arquitetura, empacota o app Tauri para todas as plataformas e publica tudo em uma GitHub Release.

## Fluxo Completo

### 1. Preparar o CHANGELOG

Antes de taggear, mova as mudanças de `[Unreleased]` para a nova versão em `CHANGELOG.md`:

```markdown
## [1.2.0] - 2025-07-15

### Added
- Nova funcionalidade X

### Fixed
- Bug Y corrigido

## [Unreleased]

### Added
- (vazio — próximas mudanças entram aqui)
```

Atualize os links do rodapé:

```markdown
[unreleased]: https://github.com/renan/autondb/compare/v1.2.0...HEAD
[1.2.0]: https://github.com/renan/autondb/compare/v1.1.0...v1.2.0
```

### 2. Commitar e taggear

```bash
# Commitar o changelog atualizado
git add CHANGELOG.md
git commit -m "chore: update CHANGELOG for v1.2.0"

# Criar a tag
git tag v1.2.0

# Push do commit + tag
git push origin main
git push origin v1.2.0
```

> Alternativamente, push tudo de uma vez: `git push origin main v1.2.0`

### 3. O pipeline executa automaticamente

Ao detectar a tag `v1.2.0`, o workflow `.github/workflows/release.yml` executa:

| Job | Descrição |
|-----|-----------|
| `prepare` | Valida a tag, extrai versão, detecta prerelease, extrai seção do CHANGELOG |
| `build-sidecar` | Compila `autondb-core` via PyInstaller (4 arquiteturas) |
| `build-tauri` | Baixa sidecar pré-compilado, compila Rust, empacota instaladores |
| `publish-cli` | Publica binários CLI standalone na Release |

### 4. A Release é criada

A Release aparece em **GitHub → Releases** com:

- **Título**: `AutonDB v1.2.0`
- **Body**: seção extraída do `CHANGELOG.md`
- **Artifacts**: instaladores + binários CLI

## Comandos de Referência

### Criar release normal

```bash
git tag v1.2.0
git push origin v1.2.0
```

### Criar prerelease (alpha/beta/rc)

```bash
git tag v1.2.0-beta.1
git push origin v1.2.0-beta.1
```

Tags contendo `alpha`, `beta`, `rc` ou `pre` são automaticamente marcadas como **prerelease**.

### Release manual (sem tag)

1. Ir em **GitHub → Actions → Release**
2. Clicar **Run workflow**
3. Inserir a versão (ex: `v1.2.0`)
4. Clicar **Run**

### Extrair changelog de uma versão (local)

```bash
# Versão específica
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

### Listar tags locais

```bash
git tag --list 'v*'
```

### Deletar tag (se precisar corrigir)

```bash
# Local
git tag -d v1.2.0

# Remoto
git push origin :refs/tags/v1.2.0
```

### Deletar release via GitHub CLI

```bash
gh release delete v1.2.0 --yes
```

## Artifacts por Plataforma

| Artifact | Plataforma | Instalação |
|----------|------------|------------|
| `.msi` | Windows | Duplo-clique para instalar |
| `.dmg` | macOS | Abrir, arrastar para Applications |
| `.deb` | Debian/Ubuntu | `sudo dpkg -i <file>` |
| `.AppImage` | Qualquer Linux | `chmod +x <file> && ./<file>` |
| `autondb-core-x86_64-pc-windows-msvc.exe` | Windows | CLI standalone |
| `autondb-core-x86_64-unknown-linux-gnu` | Linux x86_64 | CLI standalone |
| `autondb-core-aarch64-apple-darwin` | macOS Apple Silicon | CLI standalone |
| `autondb-core-x86_64-apple-darwin` | macOS Intel | CLI standalone |

## Arquitetura do Pipeline

```
git tag v1.2.0 ──push──▶ GitHub Actions
                              │
                              ▼
                         ┌─────────┐
                         │ prepare  │  valida tag, extrai changelog
                         └────┬─────┘
                              │
                              ▼
                     ┌───────────────┐
                     │ build-sidecar │  PyInstaller × 4 arquiteturas
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
                    │  publish-cli    │  Publica binários CLI na Release
                    └─────────────────┘
```

## Versões do App

A versão é definida em **3 lugares** que devem ser sincronizados:

| Arquivo | Campo | Exemplo |
|---------|-------|---------|
| `CHANGELOG.md` | `## [1.2.0]` | Header da seção |
| `src-tauri/tauri.conf.json` | `"version": "1.2.0"` | Versão do bundle Tauri |
| `pyproject.toml` | `version = "1.2.0"` | Versão do pacote Python |

> O workflow lê a versão da **tag**, não desses arquivos. Mas eles devem estar em sync para consistência.

## Checklist de Release

- [ ] Mover entradas de `[Unreleased]` para `[x.y.z]` no `CHANGELOG.md`
- [ ] Atualizar data no header da versão
- [ ] Atualizar links do rodapé (`[unreleased]` e `[x.y.z]`)
- [ ] Atualizar `version` em `src-tauri/tauri.conf.json`
- [ ] Atualizar `version` em `pyproject.toml`
- [ ] Commitar: `git commit -m "chore: release v1.2.0"`
- [ ] Taggear: `git tag v1.2.0`
- [ ] Push: `git push origin main v1.2.0`
- [ ] Verificar o workflow em **GitHub → Actions**
- [ ] Confirmar a Release em **GitHub → Releases**
- [ ] Baixar e testar o instalador da sua plataforma
