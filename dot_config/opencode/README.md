# OpenCode Configuration

**Platform:** Cross-platform (desktop profiles only)
**Theme:** Catppuccin
**Purpose:** AI tool configuration mirroring Claude Code MCP servers and plugins

## Overview

OpenCode is a desktop AI code tool with MCP (Model Context Protocol) server support. This config mirrors the Claude Code MCP servers defined in `dot_claude/settings.json`, enabling consistent AI assistance across tools.

## Key Files

- `opencode.json.tmpl` — Main configuration (Go template)
- `profiles/` — Profile configurations (platform/mode specific)
- `snippet/` — Code snippet templates
- `themes/` — Theme files (Catppuccin)

## Configuration Highlights

### MCP Servers (19 configured)
Mirrored from Claude Code, includes:
- **Core:** context7 (library docs), fetch (URL fetching)
- **GitHub:** Issue/PR management via `${GITHUB_TOKEN}`
- **Thinking:** sequential-thinking, memory servers
- **Tools:** 1Password, Playwright (browser automation)
- **Communication:** Slack, Discord (with token env vars)
- **Knowledge:** Obsidian, Notion (documentation tools)
- **Other:** Linear (project management), Brave Search

### Permissions
```json
"bash", "read", "edit", "glob", "grep", "task", "todowrite", "todoread",
"webfetch", "websearch"
```

### Plugins
```json
@slkiser/opencode-quota, opencode-sessions, opencode-snippets,
opencode-plugin-openspec, opencode-swarm-plugin
```

## Installation

Desktop profiles only: `mac-personal`, `fedora-desktop`, `toolbox`, `ubuntu-desktop`, `arch-desktop`

Installed via: `run_once_install-claude-plugins.sh`

## Integration

- **Sync with Claude:** Update `dot_claude/settings.json`, then run `sync-mcp-servers` (wrapper for `chezmoi apply ~/.config/opencode/opencode.json`)
- **MCP Servers:** Uses same environment variables as Claude Code
- **Theme:** Catppuccin (matching system-wide theming)
- **Capabilities:** Same as Claude Code tools (file read/edit, bash, web search, etc.)

## Environment Variables

Requires at runtime:
- `GITHUB_TOKEN` — GitHub API access
- `SLACK_BOT_TOKEN`, `SLACK_TEAM_ID` — Slack integration
- `BRAVE_API_KEY` — Search API
- `LINEAR_ACCESS_TOKEN`, `DISCORD_TOKEN`, `OBSIDIAN_API_KEY`, `NOTION_API_KEY`

## Related

- Mirrors `dot_claude/` configuration for consistency
- Part of AI tools setup alongside Claude Code, Qwen, Vibe
- Desktop-only (skipped on server/headless profiles)
- Shares MCP server configuration strategy with Claude
