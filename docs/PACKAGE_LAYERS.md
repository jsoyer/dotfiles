# Package layers

For current implementation status and continuation notes, see
[PACKAGE_LAYERS_HANDOFF.md](PACKAGE_LAYERS_HANDOFF.md).

Package selection follows the three-part hierarchy you described:

1. **System**: macOS, Linux, Windows or BSD.
2. **Base profile**: for example `mac-personal`, `mac-professional`,
   `debian-personal`, `fedora-server` or `arch-container`.
3. **Machine**: additions for the short hostname.

The catalog's existing `machine_profile` plus package variant are presented as
one **base profile**; their old config keys remain in place for compatibility.
For example, the personal Mac is shown as `mac-personal`. New initialization
defaults to the base-only variant. Existing configurations without a saved
variant keep using their historical manifests until migrated. `package-plan
preview` prints system, base profile and machine separately; legacy selections
are explicitly marked as compatibility mode.
Saved `machine_profile = "rpi/debian"` values are accepted as `rpi` by installers
and wrappers. Reinitialization writes the canonical `rpi` value without changing
the package scope; editing existing machines' configuration is unnecessary.
Linux profiles include Alpine and Arch containers. Their package base is kept
small and uses `apk` or `pacman`; FreeBSD uses `pkg`. The machine registry also
records whether a Linux selection is a host or container. Alpine is detected
from `/etc/os-release`; Arch initialization offers a container profile.

## New MacBook Neo

Choose a unique hostname for a new machine. If a package file already exists for
that name, initialization stops unless you explicitly identify it as the same
machine (`DOTFILES_REUSE_HOST_PACKAGES=1`). This protects a Neo named simply `Mac`
from inheriting an older Mac's packages.

With Homebrew installed, initialize without applying first:

```sh
brew install chezmoi
DOTFILES_PACKAGE_PROFILE=base chezmoi init --branch main jsoyer
chezmoi execute-template '{{ includeTemplate "package-manifest" (dict "data" . "manager" "brew") }}'
chezmoi apply
exec zsh
```

The preview works before Python or the wrappers are installed. The macOS base
contains the 18 common formulae plus Python (wrapper runtime) and mise (project
versions). Homebrew also installs their dependencies. Personal/professional
applications, global language toolchains, AI plugins, wallpapers and agent stacks
are outside this fresh base. Intel Macs use the existing prebuilt mise fallback
for core CLIs and Python, with active chezmoi/carapace defaults.

Alternatively use `scripts/bootstrap.sh`, which now installs only prerequisites
before chezmoi selects the packages. Set `DOTFILES_PACKAGE_PROFILE=base` to select
the scope explicitly. The PowerShell bootstrap accepts `-PackageProfile base`.

Optional `install_ocx`, `install_mas` and `install_docker` default to false in base.
Additional applications can be installed individually and recorded for the Neo.

## Inspect the selection

After the first apply:

```sh
package-plan preview
package-plan preview --json
package-plan --profile personal preview
package-plan manifest --manager brew
```

The global `--profile` option previews another usage without changing the saved
configuration. Previews report declarations and their source files; they do not
inspect installed state or install software. `install_mas=false` filters App Store
declarations from installation; compatibility keeps explicit legacy host MAS entries.

## Create a machine or edit its packages

On a machine with the chezmoi source checkout available, use the guided terminal
menus:

```sh
package-plan create
package-plan tui
```

`create` asks for the short hostname, system, base profile and its variant.
It shows the selected shared files and host manifest names, then asks before
recording the choice in `dot_private/package-machines.json`. Existing host
manifests are detected and require explicit association. Registered values
drive package selection on the next `chezmoi apply`; a first initialization
also saves them in chezmoi's local configuration. Unregistered machines keep
their current saved values, including `legacy`. No packages are installed while
choosing the profile. The final `chezmoi apply` action can install packages from
the selected manifests. Changing a selection does not uninstall packages
already present on the machine.

`tui` opens full-screen menus in terminals with `curses`. Choose one of three
areas: **Système et base** to assign an OS/distribution profile to a machine,
**Base** to edit shared package manifests, or **Machine** to edit one host's
packages. In the checklist, use arrows to move, Space to tick or untick, `/` to
filter, `a` to add a package, `*` to select visible entries, `-` to clear them,
and Enter to confirm. The editor shows which profiles consume a shared
manifest. Removing an inherited package from one machine writes a host
exclusion.

After reviewing and confirming the diff, choose how to finish. For the current
machine, the default action runs `chezmoi apply` and creates a commit; pushing is
an additional explicit choice. `chezmoi apply` runs the existing install hooks,
so it can install packages from the selected manifests. For another machine, the
TUI does not apply changes locally; that machine applies them on its next
`chezmoi update` or `chezmoi apply`. Commits include only files changed in the
TUI session, excluding unrelated staged work. Terminals without `curses` use a
numbered selection fallback. `package-plan promote` remains available for
explicit promotion from a machine overlay.

The `apk` and `pkg` wrappers mirror the existing native-manager wrappers. `sysup`
updates Alpine with `apk update/upgrade` and FreeBSD with `pkg update/upgrade`;
container execution as root does not require sudo.

The catalog `dot_private/package-layers.json` is read by both chezmoi and the
wrappers. The generated `~/.config/dotfiles/package-context.json` supplies saved
selection data to wrappers, including ones run outside an interactive shell.

## Add and remove packages

You can edit the inventory files in the chezmoi source directly. First use
`package-plan preview` to see which files are active. For a migrated machine,
edit its short-hostname file or the base/usage inventory when the package should
apply to every machine in that layer. Examples include
`dot_private/Brewfile_Jerome-Soyers-Mac-Mini-M6`, `dot_private/Aptfile_rpi`,
and `dot_private/Scoopfile_personal.json`; use the filename pattern for your
own machine and keep JSON inventories valid JSON.
Review and commit manual edits normally. The wrappers update inventories after
successful installs and uninstalls, so avoid editing a file while a wrapper is
running.

Unmigrated `legacy` machines still read compatibility files such as
`Brewfile_personal` and `Brewfile_pro`. Those files are protected by the hashes
in `docs/PACKAGE_BASELINE_2026-11-14.json`; migrate before changing their
package selection where possible. An intentional compatibility fix (such as a
Homebrew rename) must update its baseline hash in the same commit.

These files describe desired packages. Removing a line does not uninstall a
package. A later `dump` can add back a removed line if that package is still
installed, because dumps export the machine's installed inventory. Also,
removing a package from a host file does not cancel an inherited base/usage
package; use the host's `PackageExcludes_<hostname>.json` for that.

Use `breww`, `aptw`, `dnfw`, `pacmanw`, `yayw`, `ostreew`, `flatpakw` or `snapw`.
Their normal installation syntax records additions in the current host file.
An inherited package removed through a wrapper gets a machine-local exclusion in
`PackageExcludes_<hostname>.json`, leaving the shared files and other machines
unchanged. Installing it again clears the exclusion.

Windows has `~/.local/bin/scoopw.ps1`. Setup adds an import to the all-hosts
profiles of PowerShell 7 and Windows PowerShell, preserving their original bytes
and saving a backup first. The owned module aliases `scoop` and `package-plan`;
custom per-host profiles still load afterwards. Redirected Documents folders
are supported. The wrapper resolves native Scoop without recursing through its
alias. The Unix `scoopw` launcher requires `pwsh`.

Successful wrapper changes commit/push only their own manifests, including newly
created host/exclusion files. An installation or export failure prevents publishing
an incomplete inventory. Other staged work is excluded from wrapper commits.

Promote a host entry only when it belongs on every matching machine:

```sh
package-plan promote --manager apt htop --to usage
package-plan promote --manager brew cask:ghostty --to usage
# Homebrew shorthand also commits/pushes its two changed files:
breww --promote ghostty --to usage
```

`--to base` selects the common layer; `--to usage` selects the current usage layer.
The `package-plan` commands edit files locally for review; commit them explicitly.
Compatibility manifests cannot be promoted into: migrate the machine first.

## Migrate an existing machine

Existing machines keep their existing package lists until migrated individually.
The large `Brewfile_personal`, `Brewfile_pro`, Linux profile manifests and
`Scoopfile.json` remain read-only compatibility inputs. Role-labelled Linux
profiles now have matching usage-layer manifests, so migration can retain their
shared declarations instead of copying everything into each host overlay.
Debian, Raspberry Pi and Windows inventories remain in compatibility mode until
their intended usage is selected on the machine; their contents are not assigned
to personal or server use by guessing.

```sh
chezmoi git -- status --short --branch
chezmoi update
package-plan preview
package-plan migrate --to personal
package-plan migrate --to personal --write
chezmoi apply
exec zsh
```

Use a checkout of `main`; `chezmoi update` follows the checkout's current branch.

Migration previews by default. It preserves this host's **declared** package
intent in its host manifests, subtracting the selected new base/usage, and reports
any packages introduced by that new base/usage. It does not infer the actual
installed applications from another host or guess ownership of old hostname files.
Use the wrappers' explicit `dump` commands and inspect installed state first when
that differs from the declarations. Brew exports preserve host npm/Go/Cargo entries
which its enabled dumpers cannot represent.

`--write` backs up the local chezmoi TOML, affected host manifests and any
registered machine entry it changes under
`<chezmoi-config-directory>/package-layer-backups/<timestamp>/`. It updates only
`package_profile` in `[data]` and, when the machine is registered,
`package-machines.json`; other local configuration and registry fields are kept.
Review and commit the changed manifests afterwards; migration itself does not
push them.

No software is uninstalled by migration. Existing package updates still cover
installed packages outside the selected manifests and report incomplete updates.
Compatibility can be retired after the affected machines' installed inventories
and host allocations have been checked. That fleet inventory is not available
from this repository alone.

To roll back, use the backup's `migration.json` mapping to restore each file at
its original location, removing only files marked as previously absent; then
reapply chezmoi and open a new shell. Restoring only the repository commit would
leave the changed local `package_profile` behind.

## Validation

`scripts/test_package_layers.py` covers selection on every supported technical
profile, compatibility hashes, first init/reinit, host isolation, exclusions,
metadata conflicts, migration and wrapper failures. With `pwsh` installed it also
executes Scoop scenarios against fake Scoop/Git commands. No real packages are
installed by these tests. Native CI jobs cover Linux, macOS and Windows; simulated
renders complement native checks and do not prove a complete installation on a
physical MacBook Neo.
