# Provenance

This file documents tracked third-party or generated content that is not authored primarily in this repository.

## AI Resources

### `dot_claude/`

- Purpose: vendored Claude Workflow System deployed to `~/.claude/` by chezmoi.
- Upstream: https://github.com/vinicius91carvalho/.claude
- Pinned revision: `e1b64fcb` as documented in `CLAUDE.md`.
- Update command: refresh from the upstream repository, review local changes, then re-run `chezmoi diff` before applying.
- Local patches: repository-specific RTK, Beads, and personal workflow instructions may be layered through this dotfiles repository. Review `git diff dot_claude/` after any upstream refresh.

### `dot_aictx/`

- Purpose: AI resource cache deployed to `~/.aictx/` and linked into AI CLI config directories by `tools/aictx`.
- Primary provenance index: `dot_aictx/dot_skill-lock.json` contains per-skill source names, source URLs, source types, install timestamps, and folder hashes where available.
- Update command: use the maintained `aictx`/`cctx` workflow, typically `cctx plugin refresh`, resource install/update actions, then `chezmoi re-add ~/.aictx` for intentional cache changes.
- Local patches: content may include curated local rules, commands, and workflow resources. Treat changes outside `dot_skill-lock.json` entries as local curation unless their source is documented in-file.

## Binary Artifacts

Tracked binary artifacts are allowed only when they are runtime inputs and have documented source and checksum. Zellij plugin versions are pinned in `dot_config/zellij/plugins/plugins.lock.json` and managed with `update-zellij-plugins`.

| Path | Source | Update command | SHA-256 |
| --- | --- | --- | --- |
| `dot_config/zellij/plugins/zjstatus.wasm` | https://github.com/dj95/zjstatus releases | `update-zellij-plugins --bump zjstatus` | See `plugins.lock.json` |
| `dot_config/zellij/plugins/zellij-datetime.wasm` | https://github.com/h1romas4/zellij-datetime releases | `update-zellij-plugins --bump zellij-datetime` | See `plugins.lock.json` |
| `dot_config/zellij/plugins/empty_zellij-sessionizer.wasm` | Local empty placeholder for disabled/sessionizer-compatible layouts | Recreate with `: > dot_config/zellij/plugins/empty_zellij-sessionizer.wasm` when needed | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |

Routine commands:

```bash
update-zellij-plugins          # verify/reinstall pinned files
update-zellij-plugins --check  # report newer GitHub releases
update-zellij-plugins --bump zjstatus
```
