# aictx (cctx)

Smart per-project context manager for AI coding CLIs. Reduces token overhead (~40K+ to ~5-8K tokens/msg) by activating only relevant skills, agents, commands, MCP servers, rules, and plugins per project.

## Features

- **Project scanning** -- auto-detects languages, frameworks, deps, infra
- **Smart recommendations** -- scores resources against project fingerprint
- **3-scope system** -- Global (`~/.claude/`), Project (`./.claude/`), UserProject (`~/.claude/projects/<hash>/`)
- **8 AI CLIs** -- claude, qwen, vibe, codex, kimi, opencode, gemini-cli, copilot-cli
- **Interactive TUI** -- browse/toggle skills, agents, commands, MCP, rules, plugins with `[L]`/`[R]` origin indicators
- **Remote discovery** -- fetch skills/agents/commands/plugins from 14+ internet sources
- **Install/uninstall** -- download remote resources to local dirs, manage from TUI (`i` key)
- **AI refinement** -- optional `--smart` flag uses Ollama/Claude/OpenAI to refine recommendations
- **File watching** -- `cctx watch` monitors project files and re-applies on change
- **Shell hooks** -- auto-apply on `cd` for zsh, bash, fish
- **Profiles** -- save/load/export/import scope-aware profiles
- **Token estimation** -- `cctx cost` shows per-resource token overhead

## Installation

```bash
# Build from source
cd tools/aictx
cargo build --release

# Copy to PATH
cp target/release/aictx ~/.local/bin/cctx

# Generate shell completions (optional)
cctx completions zsh > ~/.zsh/completions/_cctx
cctx completions bash > ~/.bash_completion.d/cctx
cctx completions fish > ~/.config/fish/completions/cctx.fish

# Generate man page (optional)
cctx man > ~/.local/share/man/man1/cctx.1
```

## Quick Start

```bash
# Scan project and see recommendations
cctx scan

# Apply recommendations interactively (TUI)
cctx

# Auto-apply based on scan
cctx apply --auto --yes

# Save as reusable profile
cctx save my-project

# Apply a saved profile
cctx apply my-project
```

## Commands

| Command | Description |
|---------|-------------|
| `cctx` | Launch interactive TUI (default) |
| `cctx scan` | Show detected tech stack |
| `cctx apply [profile]` | Apply profile or auto-recommendations |
| `cctx status` | Show current configuration |
| `cctx diff` | Compare active config vs recommendations |
| `cctx cost` | Estimate token overhead |
| `cctx save <name>` | Save current config as profile |
| `cctx profiles` | List available profiles |
| `cctx reset` | Remove per-scope config |
| `cctx init` | Bootstrap new project with starter profile |
| `cctx trim [file]` | Analyze CLAUDE.md for token reduction |
| `cctx index` | Re-index resources from source dirs |
| `cctx doctor` | Health check (all scopes, broken symlinks) |
| `cctx export <profile>` | Export profile to YAML |
| `cctx import <file>` | Import profile from YAML |
| `cctx update` | Update all installed remote resources |
| `cctx watch` | Watch project files, re-apply on change |
| `cctx hook <shell>` | Generate shell hook (zsh/bash/fish) |
| `cctx completions <shell>` | Generate shell completions |
| `cctx man` | Generate man page |

### Plugin/Resource Management

| Command | Description |
|---------|-------------|
| `cctx plugin list` | List all cached remote resources |
| `cctx plugin search <query>` | Search resources by name/description |
| `cctx plugin refresh` | Refresh cache from all sources |
| `cctx plugin install <name>` | Download resource to local dir |
| `cctx plugin uninstall <name>` | Remove downloaded resource |
| `cctx plugin add <name> <url>` | Add new source to sources.yaml |
| `cctx plugin disable-all` | Disable all plugins in settings |
| `cctx plugin enable-all` | Enable all plugins in settings |

### Config Management

| Command | Description |
|---------|-------------|
| `cctx config get <key>` | Get config value (project or global) |
| `cctx config set <key> <value>` | Set project-level config |
| `cctx config list` | List all config with scope indicators |

## TUI Keybindings

| Key | Action |
|-----|--------|
| `Tab` / `h` / `l` | Switch tabs |
| `j` / `k` | Navigate up/down |
| `Space` / `Enter` | Toggle item |
| `i` | Install (remote) / Uninstall (local) |
| `/` | Filter/search |
| `A` / `N` | Select all / Deselect all |
| `PgUp` / `PgDn` | Scroll |
| `g` / `G` | Jump to top / bottom |
| `a` | Apply selections |
| `q` | Quit |

## Scopes

| Scope | Directory | Symlinks | Use case |
|-------|-----------|----------|----------|
| Global | `~/.claude/` | Yes | Default, shared across projects |
| Project | `./.claude/` | Yes | Per-project, committed to git |
| UserProject | `~/.claude/projects/<hash>/` | No (settings only) | Private per-project overrides |

```bash
cctx apply --scope global         # Apply to global scope
cctx apply --scope project        # Apply to project scope
cctx status --scope user-project  # Check user-project settings
```

## AI Refinement

When `--smart` is used and AI is enabled, cctx queries an LLM to refine recommendations beyond what the scanner detects.

```bash
# Enable AI (disabled by default)
cctx config set ai.enabled true

# Provider options: ollama, claude, openai, auto
# "auto" detects: Ollama (local) > Claude API > OpenAI API
cctx config set ai.provider auto

# Use smart recommendations
cctx --smart
cctx apply --smart
```

## Configuration

- Global config: `~/.config/aictx/defaults.yaml`
- Project config: `.cctx.yaml` (overrides global)
- Sources: `~/.config/aictx/sources.yaml`
- Profiles: `~/.config/aictx/profiles/`

## Resource Sources

Resources are discovered from configured sources (14 default):

- **Skills**: skillhub.club, skillsmp.com, lobehub.com, mcpmarket.com, awesome-agent-skills
- **Agents**: subagents.cc, claudecodeagents.com, awesome-subagents, wshobson/agents
- **Plugins**: anthropics/official, claudemarketplaces.com, buildwithclaude.com, awesome-claude-plugins
- **Mixed**: community repos providing multiple resource types

Add custom sources:

```bash
cctx plugin add my-source https://github.com/user/repo --resources skill,agent
cctx plugin refresh
```

## Shell Integration

```bash
# zsh (~/.zshrc)
eval "$(cctx hook zsh)"

# bash (~/.bashrc)
eval "$(cctx hook bash)"

# fish (~/.config/fish/config.fish)
cctx hook fish | source
```

## Release

Tag a release to trigger cross-compilation:

```bash
git tag aictx-v0.2.0
git push --tags
```

Builds for: linux-x86_64, linux-aarch64, macos-x86_64, macos-aarch64.

## License

MIT
