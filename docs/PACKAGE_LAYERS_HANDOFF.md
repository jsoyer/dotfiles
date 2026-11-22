# Package layers: handoff

This note is a continuation brief for another agent or workstation. The full
user guide is [PACKAGE_LAYERS.md](PACKAGE_LAYERS.md); this file records current
implementation state and the work still needed.

## Goal and model

Manage package declarations from one catalog with three layers:

1. OS/distribution base.
2. Usage: `base`, `personal`, `professional` or `server`.
3. Current machine's short-hostname overlay and optional host exclusions.

`machine_profile` still selects the technical OS/distribution profile.
`package_profile` selects the usage. Existing machines without a saved
`package_profile` stay on `legacy`; new machines default to `base`.

## Source of truth and entry points

- `dot_private/package-layers.json`: profiles, package managers, shared layers,
  legacy mappings and host-file prefixes.
- `dot_private/package-machines.json`: optional hostname-to-profile registry;
  currently empty in this checkout.
- `.chezmoitemplates/package-files` and `package-manifest`: resolve selections
  for chezmoi installers.
- `dot_local/bin/package_layers.py`: selection, preview, TUI, migration,
  exclusions, wrappers and inventory export.
- `dot_local/bin/executable_breww`: Homebrew command and bundle inventory wrapper.
- `dot_shell_common/aliases.sh`, Fish config and Nushell config: route package
  commands through the wrappers. Nushell's direct `brew` command now uses
  `breww` too.
- `docs/PACKAGE_LAYERS.md`: user procedures and safety details.

Useful commands:

```sh
package-plan preview
package-plan manifest --manager brew
package-plan create
package-plan tui
package-plan migrate --to personal       # preview only
package-plan migrate --to personal --write
```

The TUI edits manifests locally after showing a diff and requesting confirmation.
It does not install packages, commit or push.

## Implemented

- Layered catalog, preview, guided machine registration, and shared/host editing.
- Host-local exclusions for removing inherited packages.
- Layer-aware wrapper recording and inventory dumps for existing managers.
- Alpine `apk`, Arch container `pacman`, and FreeBSD `pkg` profiles, installers,
  wrappers and `sysup` update paths. Linux container/root installs avoid requiring
  `sudo`.
- Role-specific usage manifests preserve the old declarations for Ubuntu
  desktop/server, Fedora desktop/server/Atomic, Fedora Toolbox, Arch
  desktop/server and Omarchy. The legacy source manifests remain untouched.
- `package-plan migrate --write` preserves this host's declared legacy intent in
  its host overlay, updates local chezmoi data, and updates the registry entry if
  the host is registered. It backs up changed files locally. It does not uninstall
  packages or push changes.
- Homebrew's personal/professional usage lists remain intentionally small. A Mac
  migration places packages outside those lists into that Mac's host overlay.
- `aictx` unused function and dependencies were removed; offline `cargo check`
  completed without the reported warnings.

## Important wrapper behavior

Package wrappers update the current host overlay and exclusions. Successful
`breww`, native wrapper, and promotion operations automatically commit and push
their owned manifests. This is existing product behavior. `package-plan tui` and
`package-plan migrate` are local-only; review and commit their changes manually.
Do not confuse the no-push instruction for this agent session with wrapper
behavior on a user's machine.

## Migration state

As of 2026-11-22, branch `main` is seven commits ahead of `origin/main`; nothing
has been pushed. Recent commits, newest first:

- `28cbf583` route Nushell `brew` through `breww`.
- `7f7187e3` keep registered package profile in sync during migration.
- `9aea7bb4` populate role-specific usage layers.
- `860d23ea` remove unused `aictx` function and dependencies.
- `7e20a871` add Alpine/container/FreeBSD package support.
- `3f099487` manage shared layers across machines.
- `6779081c` add guided machine manifest editor.

Do not delete historical files yet. Debian, Raspberry Pi and Windows inventories
still need a usage choice on their actual machines. The repository cannot infer
that choice safely, and existing local chezmoi configurations are not available
from this checkout. `package-machines.json` is not a complete fleet inventory.

For each existing machine, review its declared and installed package state, choose
the usage, preview migration, then write and apply:

```sh
package-plan preview
package-plan migrate --to personal
package-plan migrate --to personal --write
chezmoi apply
```

Use `--to professional` or `--to server` when appropriate. If installed state
differs from declarations, use that manager's explicit `dump` command and inspect
the result before migrating. Read the migration report: it compares declared
packages and reports packages introduced by the target base/usage.

## Remaining work

1. Migrate Debian, Raspberry Pi and Windows hosts after their usage has been
   selected on each machine. Migrate other legacy hosts individually as well.
2. Validate install, wrapper, update and rollback flows on real macOS, Linux,
   Windows, Alpine, Arch-container and FreeBSD systems. No full test suite or
   real-machine validation was performed in this work session.
3. Only after every active machine has left `legacy`, remove legacy catalog
   mappings, installer compatibility branches, baseline protection and unused
   historical manifests. Preserve machine overlays unless their owner explicitly
   verifies that they are obsolete.

Do not run a broad delete based only on this repository: an unregistered machine
may still rely on a compatibility manifest.
