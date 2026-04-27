# Chezmoi Auto-Commit Defaults Audit Plan

## Context

This repository currently relies on chezmoi automation and package-manager wrappers that can add, commit, and push changes. That is convenient for a personal dotfiles fleet, but risky when generated state, package manifests, Beads exports, or AI resource caches change unexpectedly.

## Risks To Review

- `autoAdd` can stage files that should remain local or ignored.
- `autoCommit` can create noisy commits from generated/runtime state.
- `autoPush` can publish mistakes before review.
- Wrapper scripts may combine package installation side effects with Git side effects.
- Multi-machine use can create unexpected rebase/conflict loops.

## Final Defaults

- Broad chezmoi `[git] autoAdd`, `autoCommit`, and `autoPush` are disabled by default.
- Set `CHEZMOI_AUTO_GIT=1` only for an explicit interactive render if broad chezmoi Git automation is desired.
- Package wrappers commit and push only the manifest files they own with explicit Git commands.
- Servers, unattended machines, and CI should leave `CHEZMOI_AUTO_GIT` unset.

## Audit Steps

1. Read `.chezmoi.toml.tmpl` and list current `autoAdd`, `autoCommit`, and `autoPush` values by profile.
2. Map which scripts rely on chezmoi auto-commit behavior versus explicit `git` commands.
3. Classify machine profiles into primary, secondary, server, toolbox, and CI.
4. Render `.chezmoi.toml.tmpl` with `CHEZMOI_AUTO_GIT` unset and verify all three global auto flags are false.
5. Render with `CHEZMOI_AUTO_GIT=1` and verify all three global auto flags are true.
6. Verify wrappers that previously used `chezmoi re-add` now commit their owned manifests explicitly.

## Rollback

- Revert `.chezmoi.toml.tmpl`.
- Run `chezmoi apply ~/.config/chezmoi/chezmoi.toml`.
- Manually inspect `git status` before rerunning package wrappers.

## Decision

Broad `autoPush` no longer remains enabled by default on any machine. Automatic pushes are limited to explicit wrapper scripts and only for wrapper-owned package manifests.
