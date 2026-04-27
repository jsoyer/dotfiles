# Chezmoi Auto-Commit Defaults Audit Plan

## Context

This repository currently relies on chezmoi automation and package-manager wrappers that can add, commit, and push changes. That is convenient for a personal dotfiles fleet, but risky when generated state, package manifests, Beads exports, or AI resource caches change unexpectedly.

## Risks To Review

- `autoAdd` can stage files that should remain local or ignored.
- `autoCommit` can create noisy commits from generated/runtime state.
- `autoPush` can publish mistakes before review.
- Wrapper scripts may combine package installation side effects with Git side effects.
- Multi-machine use can create unexpected rebase/conflict loops.

## Recommended Target Defaults

- Personal primary workstation: allow wrapper-managed manifest commits, but keep broad `autoAdd` conservative.
- Servers and unattended machines: no automatic commit or push; apply only committed source state.
- CI/test destinations: never auto-commit or auto-push.
- Package wrappers: keep explicit Git sync only for manifest changes they own.

## Audit Steps

1. Read `.chezmoi.toml.tmpl` and list current `autoAdd`, `autoCommit`, and `autoPush` values by profile.
2. Map which scripts rely on chezmoi auto-commit behavior versus explicit `git` commands.
3. Classify machine profiles into primary, secondary, server, toolbox, and CI.
4. Propose profile-specific defaults without changing behavior in the first pass.
5. Run `chezmoi execute-template < .chezmoi.toml.tmpl` for representative profiles.
6. Change one profile class at a time and verify wrappers still update manifests correctly.

## Rollback

- Revert `.chezmoi.toml.tmpl`.
- Run `chezmoi apply ~/.config/chezmoi/chezmoi.toml`.
- Manually inspect `git status` before rerunning package wrappers.

## Open Decision

The main decision is whether `autoPush` should remain enabled on any machine. My recommendation is to keep automatic pushes only inside explicit wrapper scripts and disable broad chezmoi-level `autoPush` for unattended machines.
