# Documentation Index

Reference index for understanding, operating, and extending this chezmoi dotfiles repository.

## Getting Started

- **[ONBOARDING.md](ONBOARDING.md)** — Post-bootstrap setup, templates, profiles, AI skills (`dot_aictx/`), and secrets
- **[QUICKREF.md](QUICKREF.md)** — Compact daily command cheat sheet
- **[ALIASES.md](ALIASES.md)** — Full command aliases reference across shells

## Architecture & Systems

- **[ARCHITECTURE.md](ARCHITECTURE.md)** — System overview, profile detection, 4-phase lifecycle, package wrappers, AI ecosystem
- **[CHEZMOISCRIPTS.md](CHEZMOISCRIPTS.md)** — Lifecycle scripts reference (`01-setup` through `04-update`)
- **[PACKAGE_LAYERS.md](PACKAGE_LAYERS.md)** — Layered package model (`base` / `personal` / `professional` / `server` / `legacy`), previews, and host migration
- **[PACKAGE_MANIFEST_INVENTORY.md](PACKAGE_MANIFEST_INVENTORY.md)** — Inventory of tracked manifests in `dot_private/`
- **[GENERATED_CONFIG.md](GENERATED_CONFIG.md)** — Ownership and atomic regeneration of SSH config and 1Password shell secrets
- **[FLEET.md](FLEET.md)** — `fleet` tailnet updater (Linux hosts, appliances, workstations, pull mode, invariants in [`../INVARIANTS.md`](../INVARIANTS.md))

## Operations & Maintenance

- **[RUNBOOK.md](RUNBOOK.md)** — Day-to-day operations, troubleshooting, and disaster recovery
- **[MAINTENANCE.md](MAINTENANCE.md)** — Periodic hygiene and update routines
- **[PROFILE-MIGRATION.md](PROFILE-MIGRATION.md)** — Changing machine profiles (server ↔ desktop, distro changes, OmArchy)
- **[PROVENANCE.md](PROVENANCE.md)** — Provenance of vendored components
- **[CLAUDE_LOCAL_PATCHES.md](CLAUDE_LOCAL_PATCHES.md)** — Local patches applied on top of vendored `dot_claude/`
- **[session-learnings.md](session-learnings.md)** — Chronological lessons learned and regression notes

## Work-in-Progress & Archive

- **[tasks/](tasks/)** — Active multi-sprint specs and build candidates (e.g., `tasks/infra/`)
- **[archive/](archive/)** — Completed audits, historical migration plans, and merged handoffs

## Related Guides Outside `docs/`

- **[../README.md](../README.md)** — Project overview and bootstrap quickstart
- **[../CLAUDE.md](../CLAUDE.md)** — AI assistant instructions for this repository
- **[../INVARIANTS.md](../INVARIANTS.md)** — Verifiable contracts for `fleet`
- **[../dot_local/bin/README.md](../dot_local/bin/README.md)** — Utility scripts, wrappers, and self-hosted agent stacks
- **[../dot_config/CONFIGURATION_INDEX.md](../dot_config/CONFIGURATION_INDEX.md)** — Tool configurations index
- **[../dot_config/systemd/README.md](../dot_config/systemd/README.md)** — User systemd units
- **[../dot_zsh/README.md](../dot_zsh/README.md)** & **[../dot_bash/README.md](../dot_bash/README.md)** — Modular shell configuration
- **[../scripts/README.md](../scripts/README.md)** — Bootstrap scripts reference

## Key Concepts

### 4-Phase Lifecycle

Scripts in `.chezmoiscripts/` run in numbered order:

1. **01-setup** — Prerequisites (sudo preflight, OS setup)
2. **02-install** — Package managers, layered packages, one-time cleanup migrations
3. **03-configure** — Post-install configuration (SSH, 1Password secrets, `aictx`, `mise`, `fleet-agent`, autoupdate)
4. **04-update** — Package updates

See [CHEZMOISCRIPTS.md](CHEZMOISCRIPTS.md) and [ARCHITECTURE.md#4-phase-lifecycle](ARCHITECTURE.md#4-phase-lifecycle).

### Package Layers & Wrappers

Package scope (`package_profile`) is independent of `machine_profile`. Shell aliases route package commands (`brew`, `apt`, `dnf`, `pacman`, `yay`, `rpm-ostree`, `flatpak`, `snap`, `apk`, `pkg`, `scoop`, `mise`) through wrappers in `dot_local/bin/` that update the host overlay manifest. See [PACKAGE_LAYERS.md](PACKAGE_LAYERS.md).

### AI Resources (`dot_aictx/` & `dot_claude/`)

Shared skills, agents, commands, rules, and hooks live in `dot_aictx/` (deployed to `~/.aictx/`) and `dot_claude/`. The Rust CLI `aictx` (`tools/aictx/`) manages per-CLI symlinks and runs automatically after `chezmoi apply` via `run_after_sync-aictx.sh`.
