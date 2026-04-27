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
- Binary upgrades should be reproducible: pin source, release/version, asset URL, and SHA-256 before replacing tracked binaries.
- Keep provenance in `docs/PROVENANCE.md` when adding or updating vendored resources or binary artifacts.
- Audit tracked file size with `docs/LARGE_FILES.md` before adding new binaries or large vendored assets.
- Use `cmupgrade` for manual package upgrades; unattended autoupdate must stay lightweight.
- Use `chezmoi-test-scripts` before changing `.chezmoiscripts/` behavior.
- Use `ai-resource-dedup-report` before removing duplicated `dot_claude` or `dot_aictx` resources.

## Current Priorities

1. Repo hygiene
   Remove tracked build artifacts, keep global ignores for `target/`, and keep compiled tools rebuilt locally.

2. Safer autoupdate
   Make `chezmoi-autoupdate` stop on conflicts or dirty state instead of resetting hard. Do not mutate Git remotes automatically. Split dotfile sync from package upgrades.

   Unattended autoupdate sets `CHEZMOI_AUTOUPDATE=1`. Package upgrade scripts must skip in that mode unless `CHEZMOI_AUTOUPDATE_UPGRADES=1` is explicitly set. Manual `chezmoi apply` or direct script execution can still run upgrades.

   `chezmoi-autoupdate` must never wait for prompts. It runs source pull and apply as separate phases with stdin closed and `CHEZMOI_AUTOUPDATE_TIMEOUT` guarding each phase.

3. Package automation cleanup
   Keep evolving package lists in manifests or `run_onchange` scripts. Windows consumes `dot_private/Scoopfile.json`.

4. aictx correctness
   Align docs, CLI, and config. Either implement or remove documented commands like `enable` and `disable`. Make `--auto` meaningful or remove it. Only remove symlinks owned by `aictx`.

5. Vendor provenance
    Keep `docs/PROVENANCE.md` current for `dot_aictx`, `dot_claude`, and binary zellij plugins.

6. Zellij plugin updates
   Add a pinned Zellij plugin manifest and `update-zellij-plugins` command so WASM upgrades download to a temporary file, verify SHA-256, then replace tracked binaries only on checksum match. Track this in Beads issue `dotfiles-b49`.

## Follow-up Work Items

- Fix local `bd` runtime dependency so Beads can track this cleanup work again.
- Add tests around `aictx apply` symlink behavior and cleanup ownership.
- Add a safe mode to `chezmoi-autoupdate` and make it the default.
- Review `.chezmoi.toml.tmpl` auto-add, auto-commit, and auto-push defaults per machine profile.
- Add a reproducible updater for Zellij WASM plugins (`dotfiles-b49`).
