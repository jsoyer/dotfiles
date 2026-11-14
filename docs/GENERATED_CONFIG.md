# Generated configuration recovery

The `dotfiles-generated-config` helper writes shell secrets and SSH
configuration without exposing secret values in logs. It serializes concurrent
runs with a private lock file and validates generated content before publishing.
If generation fails, it reports the affected operation and exits nonzero; the
chezmoi run-on-change script can then retry after the underlying issue is fixed.

## Shell secrets

Source: the `Shell Secrets` item in the 1Password `Private` vault.

Targets:

- `~/.zsh/secrets.zsh`
- `~/.bash/secrets.bash` when `~/.bash` already exists

Refresh after editing the vault item with `dotfiles-generated-config secrets`.
Both target files are rendered from one item read, checked with `bash -n`, and
published together. If an existing file is replaced, a private sibling backup
named `.secrets.zsh.before-chezmoi-…` or `.secrets.bash.before-chezmoi-…` is
retained. Failed reads, invalid item data, and failed writes leave or restore
the previous files. Backups are not automatically deleted.

## SSH configuration

On Linux, the helper preserves `~/.ssh/config` and adds the managed include for
`~/.ssh/config.d/chezmoi.conf`. It keeps the user's existing host blocks and
unknown-option allowances. A replaced root config or fragment has a private
`.before-chezmoi-…` sibling backup.

On macOS, the SSH document from `Private/SSH Config` remains the authoritative
generated `~/.ssh/config`. When 1Password is unavailable or unauthenticated,
generation skips and leaves the existing file alone. Once authenticated, a
missing, empty, invalid, or unreadable document is an error and does not replace
the existing config. A successful replacement keeps a private sibling backup.

To inspect SSH parsing without applying a config, the helper validates using
`ssh -G`. It suppresses includes and `Match exec` while checking, so validation
does not run commands from the user's config.

## aictx settings

`aictx` stores its ownership ledger and a first-change snapshot beside the
settings file, for example `~/.claude/settings.local.json.aictx-state.json` and
`~/.claude/settings.local.json.aictx-backup`. `aictx reset` restores only values
that still match entries aictx enabled; unrelated settings and later user
changes remain. A settings file with no ownership ledger (including legacy
files) is left untouched by reset because its ownership cannot be determined.
Malformed JSON or ownership data stops the operation before settings are
changed. Preserve the `.aictx-*` sidecars when moving settings if you expect
reset to reverse aictx's changes.
