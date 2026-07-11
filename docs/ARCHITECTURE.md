# Architecture

This document describes how the chezmoi dotfiles system works: how files flow from this repository to your home directory, how platform profiles are detected, and how the various subsystems (packages, agents, shells) are orchestrated.

## System Overview

```mermaid
graph TD
    A[Git Repository<br>~/.local/share/chezmoi] --> B[chezmoi engine]
    C[.chezmoi.toml.tmpl<br>Profile data & secrets] --> B
    D[.chezmoiexternal.toml.tmpl<br>External git repos] --> B
    E[.chezmoiignore.tmpl<br>Platform exclusions] --> B
    B --> F{Template evaluation<br>Go text/template}
    F --> G[Target files<br>~/.*]
    F --> H[Lifecycle scripts<br>.chezmoiscripts/]
    H --> I[01-setup]
    H --> J[02-install]
    H --> K[03-configure]
    H --> L[04-update]
    H --> M[05-maintenance]
```

Key inputs:
- **`.chezmoi.toml.tmpl`** -- profile detection, user data, encryption config
- **`.chezmoiexternal.toml.tmpl`** -- Oh-My-Zsh, zsh plugins, TPM (weekly refresh)
- **`.chezmoiignore.tmpl`** -- conditional file exclusion per platform

## Profile Detection

The `machine_profile` variable is the primary branching mechanism. It is resolved once during `chezmoi init` and stored in `~/.config/chezmoi/chezmoi.toml`.

```mermaid
flowchart TD
    START[chezmoi init] --> OS{.chezmoi.os?}

    OS -->|windows| WIN[windows]
    OS -->|darwin| MAC{hostname?}
    MAC -->|jsoyer-macOS| MACPRO[mac-pro]
    MAC -->|other| MACPERS[mac-personal]

    OS -->|linux| LINUX{Distribution?}
    LINUX -->|raspbian/raspios| RPI[rpi]
    LINUX -->|/proc/device-tree/model| RPIPROMPT[prompt: rpi/debian]
    LINUX -->|CI env set| UBSERV[ubuntu-server]
    LINUX -->|ubuntu| UB{hostname prefix?}
    UB -->|ubuntu-server-*| UBSERV2[ubuntu-server]
    UB -->|ubuntu-desktop-*| UBDESK[ubuntu-desktop]
    UB -->|other| UBPROMPT[prompt: server/desktop]
    LINUX -->|rpm-ostree + not toolbox| ATOMIC[fedora-atomic]
    LINUX -->|.toolboxenv or TOOLBOX_PATH| TBX[toolbox]
    LINUX -->|dnf| FED{hostname prefix?}
    FED -->|fedora-server-*| FEDSERV[fedora-server]
    FED -->|fedora-desktop-*| FEDDESK[fedora-desktop]
    FED -->|other| FEDPROMPT[prompt: desktop/server]
    LINUX -->|arch| ARCH{hostname prefix?}
    ARCH -->|arch-server-*| ARCHSERV[arch-server]
    ARCH -->|arch-desktop-*| ARCHDESK[arch-desktop]
    ARCH -->|other| ARCHPROMPT[prompt: desktop/server]
    LINUX -->|debian| DEB[debian]
    LINUX -->|other| DEBPROMPT[prompt: fallback debian]
```

See the [README profile table](../README.md#-platform-profiles) for the full feature matrix per profile.

## 5-Phase Lifecycle

Scripts in `.chezmoiscripts/` are organized into numbered phases. chezmoi runs them in lexicographic order based on trigger type.

```mermaid
graph LR
    A[01-setup<br>Prerequisites] --> B[02-install<br>Packages & tools]
    B --> C[03-configure<br>Post-install config]
    C --> D[04-update<br>Package updates]
    D --> E[05-maintenance<br>Ongoing tasks]
```

**Trigger types:**
- `run_once_` -- runs once per machine (state tracked by chezmoi)
- `run_onchange_` -- re-runs when file content hash changes
- `run_always_` -- runs on every `chezmoi apply`

### Script Reference

| Phase | Script | Trigger | Platform |
|-------|--------|---------|----------|
| 01 | `setup-macos.sh` | once | macOS |
| 01 | `setup-linux.sh` | once | Linux |
| 02 | `install-1password.sh` | once | macOS, Linux |
| 02 | `install-1password.ps1` | once | Windows |
| 02 | `install-linuxbrew.sh` | once | Linux desktop (not RPi, not Atomic) |
| 02 | `install-linux-flatpak.sh` | once | Linux (Flatpak support) |
| 02 | `install-toolboxes.sh` | once | Fedora Atomic only |
| 02 | `install-opencode-tools.sh` | once | Desktop profiles |
| 02 | `install-claude-plugins.sh` | once | Desktop profiles |
| 02 | `install-windows-packages.ps1` | once | Windows |
| 02 | `brew-bundle.sh` | onchange | macOS, Linux (Homebrew) |
| 02 | `install-linux-packages.sh` | onchange | Linux |
| 03 | `configure-atuin.sh` | once | All (interactive) |
| 03 | `configure-gpg.sh` | once | macOS (1Password) |
| 03 | `configure-linux.sh` | once | Linux |
| 03 | `configure-mail.sh` | onchange | All |
| 03 | `generate-ssh-config.sh` | onchange | All |
| 03 | `sync-aictx.sh` | after apply | All |
| 04 | `update-appstore.sh` | onchange | mac-personal |
| 04 | `update-homebrew.sh` | onchange | macOS |
| 04 | `update-linux.sh` | onchange | Linux |
| 04 | `update-windows.ps1` | onchange | Windows |
| 05 | `maintenance-container.sh` | always | All |

## Package Management

Every supported package manager has a wrapper script that installs packages **and** updates a tracked manifest. The manifest change triggers chezmoi's `run_onchange_` scripts on all machines.

```mermaid
graph TD
    USER[User runs<br>brew install foo] --> ALIAS[Alias intercepts<br>brew -> breww]
    ALIAS --> WRAPPER[Wrapper script<br>breww / aptw / dnfw / ...]
    WRAPPER --> PKG[Package manager<br>installs package]
    WRAPPER --> MANIFEST[Updates manifest<br>Brewfile_* / Aptfile_* / ...]
    MANIFEST --> GIT[explicit wrapper commit/push<br>syncs to GitHub]
    GIT --> OTHER[Other machines<br>chezmoi apply]
    OTHER --> ONCHANGE[run_onchange_<br>detects manifest hash change]
    ONCHANGE --> INSTALL[Installs missing<br>packages from manifest]
```

| Wrapper | Package Manager | Manifest | Platforms |
|---------|----------------|----------|-----------|
| `breww` | Homebrew | `Brewfile_macos` (macOS) / `Brewfile_brew_only` (Linux) + profile | macOS, Linux |
| `aptw` | APT | `Aptfile_{debian,rpi,ubuntu_desktop,ubuntu_server}` | Debian, Ubuntu, RPi |
| `dnfw` | DNF/YUM | `Dnffile_{fedora_desktop,fedora_server}` | Fedora |
| `pacmanw` | Pacman | `Pacfile_{arch_desktop,arch_server}` | Arch |
| `yayw` | YAY (AUR) | `Pacfile_aur_desktop` | Arch |
| `ostreew` | rpm-ostree | `Rpmfile_fedora_atomic` | Fedora Atomic |
| `scoopw` | Scoop | `Scoopfile.json` | Windows |

All manifests live in `dot_private/` (mapped to `~/.private/`).

## AI Agent & Skill Ecosystem

```mermaid
graph TD
    subgraph Sources
        VA[VoltAgent<br>132 agents]
        MS[msitarzewski<br>22 agents]
        ECC[ECC<br>27 agents]
        CU[Custom<br>11 agents]
        SK[Skills<br>654 modules]
    end

    subgraph Scripts
        UCA[update-claude-agents]
        UCS[update-claude-skills]
        SYNC[sync-aictx.sh<br>runs after chezmoi apply]
    end

    subgraph Targets
        CA[~/.claude/agents/]
        CS[~/.claude/skills/]
        QS[~/.qwen/skills/]
        VS[~/.vibe/skills/]
    end

    VA --> UCA
    MS --> UCA
    ECC --> UCA
    CU --> UCA
    UCA --> CA

    SK --> UCS
    UCS --> |dot_agents/skills/| SYNC
    SYNC --> CS
    SYNC --> QS
    SYNC --> VS
```

**Plugins** (managed via `run_once_install-claude-plugins.sh`):
- `octo@nyldn-plugins` -- Claude Octopus multi-AI orchestrator (39 commands, 32 personas, 50 skills)
- LSP plugins: lua, pyright, swift, typescript, gopls

**Commands**: 60 slash commands in `dot_claude/commands/` (`/plan`, `/verify`, `/code-review`, `/tdd`, `/build-fix`, language builds/reviews, etc.)

**Rules**: 64 rule files in `dot_claude/rules/` (common best practices + 12 language-specific: TypeScript, Python, Rust, Go, Swift, C++, C#, Java, Kotlin, Perl, PHP)

**Hooks**: `rtk-rewrite.sh` (token optimization on Bash calls), `claude-island-state.py` (state tracking), `console-log-check.sh` (debug statement warnings), `config-protection.sh` (protected file guard), `desktop-notify.sh` (macOS/Linux notifications)

**MCP Servers**: 19 provided by the vendored `dot_claude/private_settings.json` (context7, fetch, github, 1password, playwright, 4x cloudflare, token-optimizer, etc.)

## Shell Configuration

```mermaid
graph LR
    A[.zshrc / .bashrc] --> B[Oh-My-Zsh init<br>zsh only]
    B --> C[00-env<br>Platform detection<br>Environment vars]
    C --> D[01-path<br>PATH management<br>Lazy loading]
    D --> E[02-completions<br>zsh only]
    E --> F[10-aliases<br>Modern CLI replacements]
    F --> G[20-functions<br>Custom functions]
    G --> H[30-keybindings<br>Vim-style bindings]
    H --> I[99-integrations<br>FZF, Atuin, etc.]
    I --> J[Starship prompt]
```

Numbered files are loaded in order. See [dot_zsh/README.md](../dot_zsh/README.md) and [dot_bash/README.md](../dot_bash/README.md) for details.

## Template System

Templates use [Go text/template](https://pkg.go.dev/text/template) with chezmoi extensions. Common patterns:

- **Platform branching**: `{{ if eq .chezmoi.os "darwin" }}...{{ end }}`
- **Tool detection**: `{{ if lookPath "op" }}...{{ end }}`
- **Environment checks**: `{{ if env "TOOLBOX_PATH" }}...{{ end }}`
- **1Password secrets**: `{{ onepasswordRead "op://vault/item/field" }}`

See [CLAUDE.md Templating Patterns](../CLAUDE.md#templating-patterns) for code examples.

**Testing templates locally:**

```bash
chezmoi execute-template < dot_config/tool/config.toml.tmpl
chezmoi diff   # preview what would change
chezmoi cat    # show rendered content of a managed file
```

## External Dependencies

Managed via `.chezmoiexternal.toml.tmpl`. Git repos are cloned and refreshed every 168 hours (1 week):

| Path | Repository | Purpose |
|------|-----------|---------|
| `.oh-my-zsh` | ohmyzsh/ohmyzsh | Shell framework |
| `.oh-my-zsh/custom/plugins/zsh-autosuggestions` | zsh-users/zsh-autosuggestions | Shell suggestions |
| `.oh-my-zsh/custom/plugins/zsh-syntax-highlighting` | zsh-users/zsh-syntax-highlighting | Syntax highlighting |
| `.config/tmux/plugins/tpm` | tmux-plugins/tpm | Tmux plugin manager |
| `.wallpapers` | orangci/walls-catppuccin-mocha | Desktop wallpapers |

Wallpapers are only fetched on `mac-personal` and `ubuntu-desktop` profiles. Everything is skipped on `fedora-atomic`.

## Security Architecture

- **Secrets**: managed via 1Password CLI (`op`) or age encryption. Never hardcoded.
- **Age encryption**: identity file at `~/.config/chezmoi/key.txt`, recipient public key from 1Password.
- **File permissions**: `private_` prefix in chezmoi sets 0600 on target files.
- **SSH config**: generated from 1Password vault. Gracefully skips when 1Password is unavailable.
- **MCP tokens**: environment variable references (`${ENV_VAR}`) resolved at runtime.
- **`.chezmoiignore`**: excludes `secrets.zsh` and platform-inappropriate files.

See the [README Security section](../README.md#-security--secrets) for operational details.
