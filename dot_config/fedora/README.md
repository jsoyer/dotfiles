# Fedora Configuration

RPM-OSTree base layer configuration for Fedora Atomic systems.

## Files

- `rpm-ostree.conf` — Persistent package list for layering

## Details

- **Tool**: rpm-ostree (Fedora Atomic)
- **Platform**: Fedora Atomic (Linux)
- **Purpose**: Define base packages that survive system upgrades
- **Theme**: N/A (system configuration)

## Configuration

### Packages

- `git` — Version control
- `openssh-server` — SSH access
- `curl` — HTTP requests
- `wget` — File downloads
- `chezmoi` — Dotfiles manager

## Usage

```bash
rpm-ostree install <package>       # Add to base layer
rpm-ostree status                  # Show installed packages
rpm-ostree upgrade                 # Update base + overlays
```

## Notes

- Packages in this config are **layered** (persist across system upgrades)
- Contrast with `ostree update` (replaces entire base)
- Minimal base layer = faster upgrades and reduced image size
- Tool packages prefer Toolbox containers when possible

## System

- Fedora Atomic (immutable base OS)
- SELinux enabled
- Uses Toolbox for development environments
