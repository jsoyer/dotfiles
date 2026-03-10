# Dotfiles Audit Roadmap

All 8 phases completed. Second-pass audit by 7 agents applied.

## Phase 1 — Security & Secrets ✅
- SSH guard macOS without 1Password
- Removed hardcoded secrets from starship configs (AWS account ID + username)
- Added secret file safety net to .chezmoiignore

## Phase 2 — Chezmoi Architecture ✅
- Merged split darwin blocks in dot_profile.tmpl
- Deleted {{- if false -}} stub in configure-macos script
- Removed powerlevel10k git-repo clone from .chezmoiexternal.toml.tmpl
- Added 11 missing Windows ignore paths to .chezmoiignore.tmpl

## Phase 3 — Shell Hardening ✅
- set -euo pipefail in all scripts
- find|while → process substitution in tbx-export-apps
- printf "$var" → printf '%s' "$var" in claude-init
- Atomic write (mktemp+mv) in sync-mcp-servers
- local scope fixes in shell aliases (cup function)
- RPI_MODEL export split in bash env
- LS_COLORS via vivid added to zsh env
- Guarded oh-my-zsh source in zshrc
- Removed dead alias bcask

## Phase 4 — Homebrew Brewfile Hygiene ✅
- Removed deprecated taps (homebrew/bundle, homebrew/cask, homebrew/core)
- Removed stale formulae: autojump, bpytop, byobu, nvm, oh-my-posh, pure, vim, z, zplug
- Removed zsh-fast-syntax-highlighting (not sourced anywhere)
- Removed go@1.19, go@1.24, lsd, mcfly
- Removed temurin@8/@11/@17/@19/@20
- Removed jandedobbeleer/oh-my-posh tap

## Phase 5 — Neovim MEDIUM (keymaps & UI) ✅
- Removed conflicting keymaps (<C-h/j/k/l>, <leader>w/W, <A-j/k>, <leader>1-9)
- Fixed <Esc> → <cmd>nohlsearch<cr>
- Scoped <leader>ge GoIfErr to FileType go autocmd
- Removed lualine tabline section (bufferline handles it)
- Removed hardcoded background_colour from notify
- Removed vim.notify = require("notify") override (noice handles it)

## Phase 6 — Cross-platform & Architecture ✅
- STARSHIP_CONFIG moved into darwin block in dot_profile.tmpl
- atuin + direnv added to RPi apt package list
- Removed Fish default_prog from wezterm (login shell zsh used instead)
- Fixed tmux-rpi.conf: screen-256color → tmux-256color
- Fixed sketchybar aerospace.sh: hardcoded omerxx path → $HOME
- Fixed sketchybar icon_map.sh: unquoted echo
- Fixed writing.lua: stray ft = "markdown" in markdown-preview key spec

## Phase 7 — Documentation ✅
- starship/README.md: Gruvbox → Snazzy
- CLAUDE.md: Gruvbox references → Snazzy

## Phase 8 — Bootstrap & Misc ✅
- bootstrap.sh: #!/bin/bash → #!/usr/bin/env bash
- bootstrap.sh: install_debian + install_rpi deduplicated → install_apt()
- wezterm.lua.tmpl: macos_window_background_blur + native_macos_fullscreen_mode
  guarded under {{ if eq .chezmoi.os "darwin" }}

## Post-roadmap improvements (2026-03-09)
- wezterm.lua.tmpl: macos_window_background_blur + native_macos_fullscreen_mode
  guarded under {{ if eq .chezmoi.os "darwin" }}
- bootstrap.sh: #!/bin/bash → #!/usr/bin/env bash
- bootstrap.sh: install_debian + install_rpi deduplicated → install_apt()
- bootstrap.sh: gh CLI install added for Debian/RPi (install_gh_apt via apt keyring)
  and Fedora/Toolbox (install_gh_dnf via dnf5-plugins + config-manager addrepo)
- memory/roadmap.md: regenerated cleanly

## Phase 10 — Fedora Flavors

**Objectif** : Mirror Ubuntu's hostname-based flavor detection for Fedora.

### Convention hostname

| Hostname | MACHINE_PROFILE | Detection |
|----------|----------------|-----------|
| `fedora-server*` | `fedora-server` | hostname |
| `fedora-atomic*` ou `rpm-ostree` | `fedora-atomic` | tool (fiable) |
| `fedora-*` (tout autre) | `fedora-desktop` | hostname |

### Fichiers modifies
- `.chezmoi.toml.tmpl` -> `fedora_flavor` auto-derive (no prompt)
- `dot_zsh/00-env.zsh`, `dot_bash/00-env.bash` -> detection + case patterns
- `dot_profile.tmpl` -> branches fedora desktop/server/atomic
- `scripts/bootstrap.sh` -> hostname-based detection
- `run_once_install-linux-packages.sh.tmpl` -> split server/desktop DNF blocks
- `run_once_install-linux-flatpak.sh.tmpl` -> fedora-desktop block (user Flatpak)
- `run_once_configure-linux.sh.tmpl` -> GNOME dark mode fedora-desktop
- `dot_private/Brewfile.tmpl` + `Brewfile_fedora_desktop` (new)

## Status
Complete. No pending items.
Last updated: 2026-03-10
