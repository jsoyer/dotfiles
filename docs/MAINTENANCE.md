# Maintenance Plan

This repository is the source of truth for chezmoi-managed dotfiles. Keep it focused on declarative configuration and small source tools. Generated, downloaded, compiled, and runtime state should either be ignored or have explicit provenance.

## Repository Layers

- Dotfiles: shell, terminal, editor, tmux, zellij, OS-specific config.
- Automation: `.chezmoiscripts`, package manifests, wrappers, autoupdate.
- AI context: `dot_aictx`, `dot_claude`, `dot_config/aictx`, and related symlink management.
- Source tools: `tools/aictx` and any other maintained helper source.
- Generated state: build outputs, caches, runtime databases, downloaded artifacts.

## Rules

- Do not track Rust `target/` directories or other build outputs.
- Do not rely on unattended jobs for destructive Git recovery.
- Keep system/package upgrades separate from lightweight dotfile sync.
- Prefer manifests over hardcoded package lists.
- Any vendored upstream content needs provenance: source URL, commit/version, update command, and local patches.
- Any tracked binary artifact needs source and checksum documentation.

## Current Priorities

1. Repo hygiene
   Remove tracked build artifacts, keep global ignores for `target/`, and keep compiled tools rebuilt locally.

2. Safer autoupdate
   Make `chezmoi-autoupdate` stop on conflicts or dirty state instead of resetting hard. Do not mutate Git remotes automatically. Split dotfile sync from package upgrades.

3. Package automation cleanup
   Convert evolving package lists from `run_once` to `run_onchange`. Make Windows consume `Scoopfile.json`. Avoid swallowing important package manager failures with bare `|| true`.

4. aictx correctness
   Align docs, CLI, and config. Either implement or remove documented commands like `enable` and `disable`. Make `--auto` meaningful or remove it. Only remove symlinks owned by `aictx`.

5. Vendor provenance
   Add provenance files for `dot_aictx`, `dot_claude`, and binary zellij plugins.

## Follow-up Work Items

- Fix local `bd` runtime dependency so Beads can track this cleanup work again.
- Add tests around `aictx apply` symlink behavior and cleanup ownership.
- Add a safe mode to `chezmoi-autoupdate` and make it the default.
- Review `.chezmoi.toml.tmpl` auto-add, auto-commit, and auto-push defaults per machine profile.
