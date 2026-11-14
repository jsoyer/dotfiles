# Package layers

macOS, Linux and Windows select the union of three layers:

1. A small base adapted to the OS/distribution.
2. An optional usage: `personal`, `professional` or `server`.
3. The current machine's additions, using its short hostname.

`machine_profile` keeps its existing technical meaning, including the restricted
work Mac, Atomic/Toolbox and OmArchy. `package_profile` selects the package scope.
New initialization defaults to `base`; existing configurations without the field
keep the compatibility selection `legacy`. Reinitialization preserves that choice.
Saved `machine_profile = "rpi/debian"` values are accepted as `rpi` by installers
and wrappers. Reinitialization writes the canonical `rpi` value without changing
the package scope; editing existing machines' configuration is unnecessary.

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

The catalog `dot_private/package-layers.json` is read by both chezmoi and the
wrappers. The generated `~/.config/dotfiles/package-context.json` supplies saved
selection data to wrappers, including ones run outside an interactive shell.

## Add and remove packages

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
`Scoopfile.json` remain read-only compatibility inputs. Fresh usage profiles read
the new small usage files, so a new personal Mac avoids the compatibility lists.

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

`--write` backs up the local chezmoi TOML and affected host manifests under
`<chezmoi-config-directory>/package-layer-backups/<timestamp>/`. It changes only
`package_profile` in `[data]`, preserving other local configuration. Review and
commit the host manifests afterwards; migration itself does not push them.

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
