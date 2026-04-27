# Claude Local Patches

`dot_claude/` is a vendored snapshot of `vinicius91carvalho/.claude` with local modifications tracked directly in this dotfiles repository.

## Local Patch Policy

- Keep upstream provenance in `docs/CLAUDE_UPSTREAM.json` and `docs/PROVENANCE.md`.
- Treat every commit touching `dot_claude/` after an upstream update as a local patch.
- Do not edit `~/.claude` directly for durable changes; edit `dot_claude/` or re-add intentional changes into this repo.
- Run `verify-claude-vendor` before pushing changes touching `dot_claude/`.

## Known Local Patch Areas

- RTK integration and token-saving guidance.
- Beads/project workflow integration.
- Personal workflow rules and model-routing preferences.
- Hook and settings adjustments needed for this dotfiles environment.

## Update Workflow

1. Check upstream status:
   ```bash
   update-claude-upstream --check
   ```
2. Review local patch inventory:
   ```bash
   update-claude-upstream --patch-report
   ```
3. Preview an update:
   ```bash
   update-claude-upstream --update --dry-run
   ```
4. Apply the update:
   ```bash
   update-claude-upstream --update
   ```
5. If conflicts are reported, resolve conflict markers in `dot_claude/`, then rerun validation.
6. Review local patch diff:
   ```bash
   git diff dot_claude docs/CLAUDE_UPSTREAM.json docs/PROVENANCE.md
   ```
7. Commit the upstream merge plus any local patch resolutions in dotfiles.

## Replication

Because `dot_claude/` is tracked as normal files in this chezmoi source tree, all upstream updates and local patches replicate to other machines through `chezmoi update`.
