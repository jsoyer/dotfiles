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

Tracked binary artifacts are allowed only when they are runtime inputs and have documented source and checksum.

| Path | Source | Update command | SHA-256 |
| --- | --- | --- | --- |
| `dot_config/zellij/plugins/zjstatus.wasm` | https://github.com/dj95/zjstatus releases | `wget https://github.com/dj95/zjstatus/releases/latest/download/zjstatus.wasm -O dot_config/zellij/plugins/zjstatus.wasm` | `4de426d20b1cbf861272e927aeeb5b49d92c17f0e2bb9d173f85bf7f0154dd53` |
| `dot_config/zellij/plugins/zellij-datetime.wasm` | https://github.com/h1romas4/zellij-datetime releases | Download the desired release asset from https://github.com/h1romas4/zellij-datetime/releases and save it to `dot_config/zellij/plugins/zellij-datetime.wasm` | `a15321dcb9457b885c63d5e67041f3f299a87727f568cbe00c7df5404bac1041` |
| `dot_config/zellij/plugins/empty_zellij-sessionizer.wasm` | Local empty placeholder for disabled/sessionizer-compatible layouts | Recreate with `: > dot_config/zellij/plugins/empty_zellij-sessionizer.wasm` when needed | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |

After updating a binary artifact, recompute checksums with:

```bash
sha256sum dot_config/zellij/plugins/*.wasm
```
