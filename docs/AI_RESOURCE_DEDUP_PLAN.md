# AI Resource Deduplication Plan

## Goal

Reduce duplication between `dot_claude/` and `dot_aictx/` without breaking Claude Code, OpenCode, Qwen, Codex, or other AI CLI resource loading.

## Current Model

- `dot_aictx/` is the intended cache/source for reusable skills, agents, commands, hooks, rules, plugins, and MCP placeholders.
- `tools/aictx` links selected resources from `~/.aictx/` into CLI-specific directories such as `~/.claude/`.
- `dot_claude/` also contains vendored workflow system files and many resources that overlap conceptually with `dot_aictx/`.

## Proposed Source Of Truth

- Keep `dot_aictx/` as the source of truth for portable AI resources.
- Keep `dot_claude/` for Claude-specific runtime configuration, workflow docs, settings, hooks, and compatibility shims that cannot be represented as portable `aictx` resources.
- Use `aictx apply`/`aictx reset` to materialize shared resources into `~/.claude/` and other CLI directories.

## Migration Steps

1. Inventory overlaps by category: `skills`, `agents`, `commands`, `hooks`, `rules`.
2. For each overlapping category, compare names and content hashes between `dot_claude/` and `dot_aictx/`.
3. Classify each duplicate as identical, Claude-specific variant, or stale copy.
4. Remove only identical/stale duplicates from `dot_claude/` after verifying `aictx apply` recreates the expected links.
5. Preserve Claude-specific variants in `dot_claude/` and document why they cannot move to `dot_aictx/`.
6. Add a verification command that checks required Claude resources are either real Claude-specific files or symlinks to `~/.aictx/`.
7. Roll out category by category, starting with lowest-risk `rules`, then `commands`, then `agents`, then `skills`, then `hooks`.

## Risks

- Removing real files from `dot_claude/` before `aictx apply` can recreate them may break Claude startup or workflow hooks.
- Some resources may intentionally diverge between Claude and portable AI CLIs.
- Chezmoi cannot track symlinked runtime state the same way as vendored source files; this needs explicit verification.

## Rollback

- Revert the category-specific commit.
- Run `chezmoi apply` to restore `dot_claude/` files.
- Run `aictx reset && aictx apply` only after confirming the reverted state is healthy.

## Recommendation

Start with an inventory-only script/report. Do not delete duplicated resources until the report proves which files are byte-identical and which are semantic variants.
