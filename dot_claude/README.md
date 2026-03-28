# Claude Code Configuration

This directory contains comprehensive Claude Code setup: specialized AI agents, slash commands, coding rules, and system hooks that integrate with the developer workflow via the Claude Code platform and Chezmoi.

## Overview

| Component | Count | Purpose |
|-----------|-------|---------|
| **Agents** | 192 | Specialized AI sub-agents for domain-specific tasks |
| **Commands** | 60 | Slash commands for quick task automation |
| **Rules** | 64 | Coding standards (9 common + 11 language-specific × 5 categories) |
| **Hooks** | 6 | System integrations (RTK optimization, state tracking, guards) |
| **MCP Servers** | 19+ | Model Context Protocol servers for external integrations |

---

## Agents (192 total)

AI sub-agents providing specialized expertise, sourced from three curated collections:

### Sources

**VoltAgent** (132 agents) — `agents/voltagen-*.md`
Foundational agents covering software engineering, product, leadership, and infrastructure:
- Code review, testing, CI/CD, infrastructure
- Language specialists (Go, Rust, TypeScript, Python, etc.)
- Architecture, security, performance
- Product, business, data analysis

**Agency** (22 agents) — `agents/agency-*.md`
Complementary agents for specialized domains:
- Database optimization, DevOps, cloud platforms
- Build troubleshooting, error detection
- Advanced testing and deployment

**Everything Claude Code** (27 agents) — `agents/ecc-*.md`
ECC ecosystem agents for enterprise patterns:
- Code quality gates, ECC-specific reviewers
- Context management, evidence collection
- Executive summaries, error coordination

**Custom** (11 agents) — `agents/custom-*.md`
Domain-specific agents tailored to this project:
- Documentation engineer, dotfiles engineer
- Specialized language reviewers
- Custom workflow agents

### Key Agents by Role

| Agent | Purpose | Trigger |
|-------|---------|---------|
| **planner** | Break down complex features into implementation plans | Before any non-trivial task |
| **tdd-guide** | Test-driven development enforcement (RED → GREEN → REFACTOR) | New features, bug fixes |
| **code-reviewer** | Comprehensive code quality review (CRITICAL/HIGH/MEDIUM issues) | Immediately after writing code |
| **architect-reviewer** | Architectural decisions and system design validation | Major feature planning |
| **build-error-resolver** | Debugging and fixing build failures | When build fails |
| **documentation-engineer** | Documentation generation and updates | When docs are stale |
| **security-auditor** | Security analysis and vulnerability scanning | Before commits |
| **[language]-reviewer** | Language-specific code review (TypeScript, Rust, Go, Python, etc.) | Language-specific code changes |

Use agents by name in chat:
```
@planner — Plan a new feature
@tdd-guide — Enforce test-first approach
@code-reviewer — Review code I just wrote
@[language]-reviewer — Review language-specific patterns
```

Agents can be used in parallel for independent tasks (runs them all concurrently instead of sequentially).

---

## Commands (60 total)

Slash commands for quick task automation from the chat interface.

### Categories

**Planning & Analysis** (8 commands)
- `/plan` — Create implementation plan with phases
- `/verify` — Verify implementation against requirements
- `/architecture` — Analyze system architecture
- `/dependencies` — Map module dependencies
- `/code-review` — Trigger code review analysis
- `/tdd` — Test-driven development workflow
- `/build-fix` — Build error diagnosis
- `/security-scan` — Security vulnerability check

**Language Build/Test** (32 commands)
- TypeScript: `/ts-build`, `/ts-check`, `/ts-test`, `/ts-review`
- Rust: `/rust-build`, `/rust-check`, `/rust-clippy`, `/rust-test`, `/rust-review`
- Python: `/py-build`, `/py-test`, `/py-lint`, `/py-review`
- Go: `/go-build`, `/go-test`, `/go-lint`, `/go-review`
- C++: `/cpp-build`, `/cpp-check`, `/cpp-test`, `/cpp-review`
- Java: `/java-build`, `/java-test`, `/java-review`
- C#/.NET: `/csharp-build`, `/csharp-test`, `/csharp-review`
- Plus: Swift, Kotlin, Perl, PHP variants

**Utilities** (20 commands)
- `/summarize` — Create executive summary
- `/refactor` — Suggest refactoring improvements
- `/test-coverage` — Analyze test coverage gaps
- `/performance` — Identify performance bottlenecks
- `/docs` — Generate or update documentation
- And more language-specific utilities

Commands are invoked directly in chat:
```
/plan Build a user authentication system
/ts-build Check TypeScript compilation
/code-review Review the code I just wrote
```

---

## Rules (64 total)

Coding standards, patterns, and best practices organized hierarchically.

### Common Rules (9 files)

Applied to all languages:

| File | Contents |
|------|----------|
| **agents.md** | Agent orchestration strategies, parallel execution, role-splitting |
| **coding-style.md** | Immutability, file organization, error handling, input validation |
| **development-workflow.md** | Feature implementation pipeline (research → plan → TDD → review) |
| **git-workflow.md** | Conventional commits, PR workflow, commit message format |
| **hooks.md** | Hook types, auto-accept permissions, TodoWrite best practices |
| **patterns.md** | Repository pattern, API response format, design patterns |
| **performance.md** | Model selection (Haiku 4.5 vs Sonnet 4.6 vs Opus 4.5), context management |
| **security.md** | Secret management, input validation, SQL injection prevention, XSS protection |
| **testing.md** | Minimum 80% test coverage, test types (unit/integration/E2E), TDD workflow |

### Language-Specific Rules (11 languages × 5 categories each)

Each language has:
- `coding-style.md` — Idiomatic patterns, naming conventions, file organization
- `hooks.md` — Pre/post-commit checks, linting, formatting
- `patterns.md` — Language-specific design patterns
- `security.md` — Language-specific vulnerabilities and mitigations
- `testing.md` — Testing frameworks, patterns, coverage tools

**Languages with rules:**
1. TypeScript
2. Python
3. Rust
4. Go
5. Swift
6. C++
7. C#
8. Java
9. Kotlin
10. Perl
11. PHP

Rules are automatically applied by Claude Code based on file extensions and code context.

---

## Hooks (6 total)

System integrations that automate quality gates and token optimization.

### Hook Scripts

| Script | Trigger | Purpose |
|--------|---------|---------|
| **rtk-rewrite.sh** | PreToolUse: Bash | Transparent command rewriting for RTK token optimization (60-90% savings) |
| **claude-island-state.py** | Multiple (SessionStart, PostToolUse, etc.) | Persist Claude Code session state, track context usage |
| **console-log-check.sh** | PostToolUse: Edit/Write/MultiEdit | Guard against accidental console.log in production code |
| **config-protection.sh** | PreToolUse: Write/Edit/MultiEdit | Prevent accidental modification of critical config files |
| **desktop-notify.sh** | SessionEnd | Send desktop notification when session completes |
| **quality-gate.sh** | PreCompact | Run quality checks before context compaction |

### RTK Hook (rtk-rewrite.sh)

Automatically rewrites Bash commands to use RTK for token optimization:

```bash
git status        → rtk git status       (80% savings)
cargo test        → rtk cargo test       (90% savings)
npm install       → rtk npm install      (90% savings)
```

Transparent — user just types normal commands, RTK applies automatically.

### Config Protection (config-protection.sh)

Prevents accidental edits to critical files:
- `~/.ssh/config` (unless explicitly confirmed)
- `.env` files
- `secrets.json`
- Other sensitive paths

### Hook Configuration

Configured in `private_settings.json.tmpl` under `hooks` section:

```json
{
  "hooks": {
    "SessionStart": [
      { "type": "command", "command": "python3 ~/.claude/hooks/claude-island-state.py" }
    ],
    "PreToolUse": [
      { "matcher": "Bash", "command": "~/.claude/hooks/rtk-rewrite.sh" },
      { "matcher": "Write|Edit|MultiEdit", "command": "~/.claude/hooks/config-protection.sh" }
    ],
    "PostToolUse": [
      { "matcher": "Edit|Write|MultiEdit", "command": "~/.claude/hooks/console-log-check.sh" }
    ],
    "SessionEnd": [
      { "type": "command", "command": "python3 ~/.claude/hooks/claude-island-state.py" }
    ]
  }
}
```

---

## Skills Symlink System

AI agent skills are synced from a centralized source into per-AI-platform consumer directories.

### Architecture

```
~/.agents/skills/               ← Source of truth (654 skills)
├── skill-1/
├── skill-2/
└── ...

~/.claude/skills/      ←─ symlink ──┐
~/.qwen/skills/        ←─ symlink ──┼─ all link to ~/.agents/skills/
~/.vibe/skills/        ←─ symlink ──┤
~/.codex/skills/       ←─ symlink ──┘
```

### Sync Mechanism

**Script:** `.chezmoiscripts/03-configure/run_onchange_sync-skill-symlinks.sh.tmpl`

**Trigger:** When `dot_agents/dot_skill-lock.json` changes (tracks dependency updates)

**Process:**
1. Check if `~/.agents/skills/` exists
2. For each consumer (.claude, .qwen, .vibe, .codex):
   - Create `~/.{consumer}/skills/` directory
   - Create relative symlinks: `../../../.agents/skills/{skill-name}`
   - Remove stale symlinks (deleted skills)
3. Output: "synced N skills to claude qwen vibe codex"

**Benefits:**
- Single source of truth for skills
- Automatic updates across all AI platforms
- No duplication, no file copies
- Clean removal when skills are deleted

---

## Settings Template (private_settings.json.tmpl)

Master configuration file with permissions, hooks, and MCP servers.

### File Structure

```json
{
  "permissions": {
    "allow": [
      "Read", "Write", "Edit", "MultiEdit", "Glob", "Grep",
      "WebFetch", "WebSearch", "Bash"
    ],
    "deny": [
      "Bash(rm -rf /*)",
      "Bash(sudo rm -rf *)",
      "Bash(curl * | bash)",
      // ... other dangerous patterns
    ]
  },

  "hooks": {
    "Notification": [...],
    "PreToolUse": [...],
    "PostToolUse": [...],
    "SessionStart": [...],
    "SessionEnd": [...],
    "PreCompact": [...]
  },

  "alwaysThinkingEnabled": true,

  "mcpServers": {
    // 19+ MCP server configurations
  }
}
```

### Permissions

**Allow** list — tools Claude Code can use:
- Read, Write, Edit, MultiEdit — File operations
- Glob, Grep — File search/content search
- WebFetch, WebSearch — Internet access
- Bash — Command execution

**Deny** list — dangerous patterns blocked:
- `rm -rf /*` — Prevent recursive deletion
- `curl ... | bash` — Prevent arbitrary code execution
- `chmod -R 777` — Prevent permission escalation
- Other destructive patterns

### MCP Servers (19+)

Model Context Protocol servers providing external integrations:

| Server | Type | Provider | Use Case | Auth |
|--------|------|----------|----------|------|
| **context7** | stdio | Upstash | Library documentation lookup | - |
| **fetch** | stdio | Python (uvx) | HTTP requests, URL fetching | - |
| **github** | stdio | Anthropic | GitHub API, repos, PRs, issues | `GITHUB_TOKEN` |
| **sequential-thinking** | stdio | Anthropic | Extended reasoning mode | - |
| **memory** | stdio | Anthropic | Persistent conversation memory | - |
| **1password** | stdio | 1Password | Secret management via 1Password CLI | - |
| **slack** | stdio | Anthropic | Slack integration | `SLACK_BOT_TOKEN`, `SLACK_TEAM_ID` |
| **brave-search** | stdio | Anthropic | Web search | `BRAVE_API_KEY` |
| **linear** | stdio | Linear | Issue tracking | `LINEAR_ACCESS_TOKEN` |
| **playwright** | stdio | Anthropic | Browser automation | - |
| **discord** | stdio | Discord | Discord bot integration | `DISCORD_TOKEN` |
| **obsidian** | stdio | Obsidian | Note-taking integration | `OBSIDIAN_API_KEY` |
| **notion** | stdio | Notion | Notion database access | `NOTION_API_KEY` |
| **drawio** | stdio | Draw.io | Diagram creation | - |
| **cloudflare-docs** | http | Cloudflare | Cloudflare API documentation | - |
| **cloudflare-workers-builds** | http | Cloudflare | Workers build cache | - |

**Type:**
- `stdio` — Direct command execution
- `http` — HTTP endpoint

**Auth pattern:**
Environment variables with `${VAR}` syntax, resolved at runtime from shell environment.

#### Installing MCP Servers

MCP servers are invoked on-demand:
- `npx -y` — Auto-install npm packages
- `uvx` — Auto-install Python packages

No pre-installation required — they install on first use and cache locally.

---

## install_ocx Toggle

Defined in `.chezmoi.toml.tmpl` (line 51), this boolean option controls optional OpenCode setup:

```toml
{{- if has $mp $desktopProfiles }}
install_ocx = {{ promptBoolOnce . "install_ocx" "Install OpenCode extensions (ocx + npm plugins)?" false }}
{{- end }}
```

**Prompt location:** First apply on desktop profiles (mac-personal, fedora-desktop, toolbox, ubuntu-desktop, arch-desktop, omarchy)

**Default:** `false` (does not auto-install)

**When enabled (true):**
1. `.chezmoiscripts/02-install/run_once_install-claude-plugins.sh` triggers
   - Installs Claude Code plugins: `octo@nyldn-plugins`, LSP plugins (lua, pyright, swift, typescript, gopls)
2. `.chezmoiscripts/02-install/run_once_install-opencode-tools.sh` triggers
   - Installs `ocx` (OpenCode CLI) and `oh-my-openagent` (OpenCode agent management)

**When disabled (false):**
- Scripts are skipped
- Standard Claude Code environment without OpenCode extensions

**Why optional?**
OpenCode is an alternative LLM orchestrator (similar to Claude Code). Most users stick with Claude Code, so it's opt-in to avoid bloat.

---

## File Organization

```
dot_claude/
├── README.md                           ← You are here
├── private_settings.json.tmpl          ← Master config (permissions, hooks, MCP servers)
├── agents/                             ← 192 AI agents
│   ├── planner.md
│   ├── tdd-guide.md
│   ├── code-reviewer.md
│   └── ... (189 more)
├── commands/                           ← 60 slash commands
│   ├── plan.md
│   ├── tdd.md
│   ├── code-review.md
│   └── ... (57 more)
├── rules/                              ← 64 coding rule files
│   ├── common/                         ← 9 files (all languages)
│   │   ├── agents.md
│   │   ├── coding-style.md
│   │   ├── development-workflow.md
│   │   ├── git-workflow.md
│   │   ├── hooks.md
│   │   ├── patterns.md
│   │   ├── performance.md
│   │   ├── security.md
│   │   └── testing.md
│   ├── typescript/                    ← 5 files per language
│   ├── python/
│   ├── rust/
│   ├── go/
│   ├── swift/
│   ├── cpp/
│   ├── csharp/
│   ├── java/
│   ├── kotlin/
│   ├── perl/
│   └── php/
└── hooks/                              ← 6 executable scripts
    ├── rtk-rewrite.sh                  ← Token optimization hook
    ├── claude-island-state.py          ← Session state tracking
    ├── console-log-check.sh            ← Production guard
    ├── config-protection.sh            ← Critical file guard
    ├── desktop-notify.sh               ← Completion notification
    └── quality-gate.sh                 ← Pre-compaction checks
```

---

## Integration with Chezmoi

This directory (`dot_claude/`) is placed in chezmoi source as-is:
- **Applied to:** `~/.claude/` on all platforms
- **Hooks trigger on:** Apply and update operations
- **Symlinks:** Skills are synced from `dot_agents/` via chezmoi script

During `chezmoi apply` or `chezmoi update`:
1. All files copied to `~/.claude/`
2. Templates in `private_settings.json.tmpl` processed (interpolate paths, env vars)
3. `run_onchange_sync-skill-symlinks.sh` (from .chezmoiscripts/03-configure) creates skill symlinks

---

## Usage Patterns

### For Planning Complex Features

```
@planner
Build a user authentication system with OAuth2 integration.
Include phases, risk analysis, and tech choices.
```

### For Test-Driven Development

```
@tdd-guide
Implement a payment processing module.
Start with tests first, then implementation.
```

### For Code Review

```
@code-reviewer
Review the code I just wrote in src/auth.ts.
Focus on security, error handling, and edge cases.
```

### For Language-Specific Work

```
@rust-reviewer
Review this Rust code for idiomatic patterns.

@python-reviewer
Check Python code for PEP 8 compliance.

@typescript-reviewer
Review TypeScript for type safety.
```

### Using Slash Commands

```
/plan Build authentication system
/ts-build Check TypeScript errors
/code-review Review my changes
/test-coverage Show coverage gaps
/security-scan Find vulnerabilities
```

### Running Agents in Parallel

For independent tasks, list multiple agents:

```
I need:
1. @security-auditor to review the auth module
2. @performance to optimize the cache system
3. @typescript-reviewer to check type safety

Run these in parallel.
```

Claude Code orchestrates them concurrently instead of sequentially.

---

## Configuration Workflow

### First-Time Setup

1. **Chezmoi apply** runs the full pipeline:
   - `.chezmoiscripts/02-install/run_once_install-claude-plugins.sh` (if install_ocx=true)
   - Copies `dot_claude/` to `~/.claude/`
   - Processes `private_settings.json.tmpl` → `~/.claude/settings.json`

2. **Hooks activate** when Claude Code next starts
3. **Skills sync** creates symlinks from `~/.agents/skills/`

### Updating Configuration

Edit files in `dot_claude/`, then:
```bash
chezmoi apply        # Copy changes to ~/.claude/
# or
chezmoi re-add dot_claude  # Auto-commit + auto-push
```

### Customizing Rules

To add a TypeScript rule:
1. Create `dot_claude/rules/typescript/my-rule.md`
2. Define pattern, examples, enforcement
3. `chezmoi apply` to sync to `~/.claude/rules/typescript/`

### Customizing Agents

To add a custom agent:
1. Create `dot_claude/agents/custom-my-agent.md`
2. Write agent system prompt and behavior
3. `chezmoi apply` to sync to `~/.claude/agents/`

---

## Troubleshooting

### Skills not syncing?
Check if `dot_agents/dot_skill-lock.json` was modified:
```bash
ls -la ~/.agents/skills/        # Verify source exists
ls -la ~/.claude/skills/        # Check symlinks
```

### MCP servers not connecting?
Verify environment variables are set:
```bash
echo $GITHUB_TOKEN
echo $SLACK_BOT_TOKEN
```

### Hooks not firing?
Check `~/.claude/settings.json` has valid hook config, and hooks are executable:
```bash
ls -la ~/.claude/hooks/
chmod +x ~/.claude/hooks/*.sh
```

### RTK optimization not working?
Verify RTK is installed:
```bash
which rtk
rtk --version
rtk gain                # Show savings analytics
```

---

## Related Documentation

- **CLAUDE.md** — Global Claude Code instructions (environment, aliases, MCP servers)
- **RTK.md** — Token optimization guide with command reference
- **Agent orchestration** — See `rules/common/agents.md` for parallel execution patterns
- **Chezmoi pipeline** — See `.chezmoiscripts/README.md` for script execution flow
