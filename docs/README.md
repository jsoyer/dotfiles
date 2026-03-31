# Documentation Index

Complete reference for understanding, using, and extending the chezmoi dotfiles system.

## Getting Started

- **[ONBOARDING.md](ONBOARDING.md)** — Post-bootstrap setup and customization
  - Understanding your machine profile and how to customize it
  - Adding new tool configurations and packages
  - Working with templates and template data
  - Adding new platform profiles
  - Working with AI agents and skills
  - Managing secrets via 1Password and age encryption
  - Quick reference of common tasks

## Architecture & Design

- **[ARCHITECTURE.md](ARCHITECTURE.md)** — System design and component overview
  - System overview diagram showing data flow
  - Profile detection logic and decision tree
  - 5-phase lifecycle (01-setup through 05-maintenance)
  - Package management wrapper system
  - AI agent and skill ecosystem
  - External dependencies management

## Operations & Troubleshooting

- **[RUNBOOK.md](RUNBOOK.md)** — Day-to-day operations and disaster recovery
  - Daily sync operations (chezmoi update, apply, upgrade)
  - Common tasks (install packages, add dotfiles, convert to templates)
  - Re-running lifecycle scripts
  - Updating agents and skills from upstream
  - Comprehensive troubleshooting guide
  - Disaster recovery procedures
  - Maintenance calendar

- **[PROFILE-MIGRATION.md](PROFILE-MIGRATION.md)** — Changing machine profiles
  - All 14 available profiles with detection methods
  - 3 methods to change profiles (direct edit, re-init, hostname)
  - 5 real-world migration scenarios (server↔desktop, distro changes, OmArchy)
  - Cleanup procedures after migration
  - Detailed troubleshooting for profile issues

## Directory Structure

```
docs/
├── README.md              # This file (documentation index)
├── ONBOARDING.md          # Setup & customization guide
├── ARCHITECTURE.md        # System design & component overview
├── RUNBOOK.md             # Operations & troubleshooting
├── PROFILE-MIGRATION.md   # Changing machine profiles
├── ALIASES.md             # Command aliases reference
└── CHEZMOISCRIPTS.md      # Lifecycle scripts reference
```

## Quick Start

**For a new machine:**
```bash
curl -sL https://raw.githubusercontent.com/jsoyer/dotfiles/main/scripts/bootstrap.sh | bash
```

**On an existing machine:**
```bash
cu   # chezmoi update -v (git pull + apply)
```

**Full system update (dotfiles + packages):**
```bash
cup  # chezmoi update + brew upgrade/apt upgrade/dnf upgrade
```

## Key Concepts

### Profiles

Your machine's profile determines which configs apply and which packages install. Profiles are auto-detected but can be overridden in `~/.config/chezmoi/chezmoi.toml`.

See [ARCHITECTURE.md#profile-detection](ARCHITECTURE.md#profile-detection) for all profiles.

### Templates

Most config files use Go text/template syntax to adapt to platform, profile, and environment. Templates are evaluated at apply time.

See [ONBOARDING.md#understanding-templates](ONBOARDING.md#understanding-templates) for template functions and examples.

### Lifecycle Scripts

Scripts in `.chezmoiscripts/` are organized into 5 phases:

1. **01-setup** — Prerequisites (Xcode, build tools, etc.)
2. **02-install** — Package managers and packages
3. **03-configure** — Post-install configuration
4. **04-update** — Package updates
5. **05-maintenance** — Ongoing tasks

See [ARCHITECTURE.md#5-phase-lifecycle](ARCHITECTURE.md#5-phase-lifecycle) for script reference.

### Package Wrappers

Aliases intercept package manager commands and auto-update tracked manifests:

| Platform | Command | Manifest |
|----------|---------|----------|
| macOS | `brew install foo` | `Brewfile_*` |
| Linux (Homebrew) | `brew install foo` | `Brewfile_brew_only` |
| Debian/Ubuntu | `apt install foo` | `Aptfile_*` |
| Fedora | `dnf install foo` | `Dnffile_*` |
| Arch | `pacman -S foo` | `Pacfile_*` |
| AUR | `yay -S foo` | `Pacfile_aur_*` |
| Windows | `scoop install foo` | `Scoopfile.json` |

### AI Skills

646+ reusable AI skills are synced from `~/.agents/skills/` to `~/.claude/`, `~/.qwen/`, `~/.vibe/`, and `~/.codex/` via symlinks whenever `dot_agents/dot_skill-lock.json` changes.

See [ONBOARDING.md#working-with-ai-agents-and-skills](ONBOARDING.md#working-with-ai-agents-and-skills) for adding skills.

## Common Tasks

| Task | See |
|------|-----|
| Apply dotfiles | [ONBOARDING.md](ONBOARDING.md#quick-reference) |
| Add a new tool config | [ONBOARDING.md](ONBOARDING.md#adding-a-new-tool-configuration) |
| Install a package | [RUNBOOK.md](RUNBOOK.md#install-a-new-package) |
| Make config platform-specific | [ONBOARDING.md](ONBOARDING.md#understanding-templates) |
| Add a new machine profile | [ONBOARDING.md](ONBOARDING.md#adding-a-new-platform-profile) |
| Change machine profile | [PROFILE-MIGRATION.md](PROFILE-MIGRATION.md#changing-your-profile) |
| Migrate server ↔ desktop | [PROFILE-MIGRATION.md](PROFILE-MIGRATION.md#migration-scenarios) |
| Migrate to different distro | [PROFILE-MIGRATION.md](PROFILE-MIGRATION.md#scenario-3-ubuntu--arch-distro-change) |
| Fix chezmoi issues | [RUNBOOK.md](RUNBOOK.md#troubleshooting) |
| Recover from a bad change | [RUNBOOK.md](RUNBOOK.md#rollback-a-bad-change) |

## Related Files

- `README.md` — Main project README
- `scripts/README.md` — Bootstrap script reference
- `dot_local/bin/README.md` — Utility script reference
- `dot_agents/README.md` — AI skills system
- `.chezmoi.toml.tmpl` — Profile detection and template data
- `.chezmoiignore.tmpl` — Platform-specific file exclusions
- `.chezmoiscripts/` — Lifecycle script phases

## Feedback & Issues

- Questions? Check [RUNBOOK.md troubleshooting](RUNBOOK.md#troubleshooting)
- Found a bug? See [RUNBOOK.md disaster recovery](RUNBOOK.md#disaster-recovery)
- Suggestions? Open a GitHub issue or PR
