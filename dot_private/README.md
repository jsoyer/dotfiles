# Package manifests

All three operating systems use **platform base + optional usage + machine**.
The catalog is [package-layers.json](package-layers.json). See
[Package layers](../docs/PACKAGE_LAYERS.md) for setup, migration and rollback.

## Selection

`machine_profile` keeps technical configuration and permission constraints.
`package_profile` is `base`, `personal`, `professional` or `server`. New machines
choose `base` by default. Existing configurations missing that field select
`legacy`, preserving their current lists until migrated explicitly.

| Manager | New common/usage lists | Machine additions |
| --- | --- | --- |
| Homebrew/macOS | `Brewfile_macos`, `Brewfile_package_tools`, `Brewfile_usage_*` | `Brewfile_<host>` |
| Homebrew/Linux | `Brewfile_minimal`; native managers provide the OS base | `Brewfile_<host>` |
| APT | `Aptfile_base`, `Aptfile_usage_*` | `Aptfile_<host>` |
| DNF | `Dnffile_base`, `Dnffile_usage_*` | `Dnffile_<host>` |
| Pacman | `Pacfile_base`, `Pacfile_usage_*` | `Pacfile_<host>` |
| AUR | Empty until explicitly promoted | `Pacfile_aur_<host>` |
| rpm-ostree | `Rpmfile_base` | `Rpmfile_<host>` |
| Flatpak / Snap | Empty in new base/usage selections | `Flatpakfile_<host>`, `Snapfile_<host>` |
| Scoop | `Scoopfile_base.json`, `Scoopfile_personal.json`, `Scoopfile_professional.json` | `Scoopfile_<host>.json` |

An absent host file means no extra packages. Only the current short hostname is
considered. Reserved names colliding with a shared manifest are rejected.
`PackageExcludes_<host>.json` records inherited packages removed only on that host.
A new install through a wrapper clears the corresponding exclusion.

## Compatibility

The large `Brewfile_personal` / `Brewfile_pro`, Linux desktop/server lists and
`Scoopfile.json` remain compatibility inputs. New personal/professional choices
use the small new usage lists. `Dnffile_toolbox_legacy` captures the previously
inline Toolbox list. Do not add new packages to compatibility manifests.
`packages.yaml` is a historical reference, not a second source of generated lists.

Before migrating a machine, compare its installed inventory and declared scope:

```sh
package-plan preview
package-plan migrate --to personal
package-plan migrate --to personal --write
chezmoi apply
```

Migration preserves this host's declarations in its own file, with local backups;
it does not modify another host, uninstall software or automatically publish files.
Keep compatibility until actual machine inventories and hostname mappings are verified.

## Wrappers and shared changes

Wrappers record successful additions/removals in machine files. Export/dump
commands subtract every active shared layer. Brew exports retain host npm, Go
and Cargo declarations not handled by their enabled dumpers. Failed commands or
exports do not publish a partial inventory. Wrapper commits include only owned files.

Promotions require an explicit destination:

```sh
package-plan promote --manager apt htop --to usage
breww --promote cask:ghostty --to usage
```

`package-plan` edits locally for review; `breww` retains its explicit manifest
commit/push behavior. The host cask upgrade skip files remain independent of
installation scope. Package updates continue checking installed packages even
when they are no longer declared in an active list.
