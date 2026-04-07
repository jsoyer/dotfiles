<div align="center">

# 🎯 claude-context (cctx)

**Smart per-project context manager for AI coding CLIs**

Reduce token overhead by ~80% by activating only relevant skills, agents, commands, MCP servers, rules, and plugins per project.

[![Rust](https://img.shields.io/badge/rust-1.80%2B-orange?logo=rust)](https://www.rust-lang.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

</div>

---

## 🚀 What it does

`cctx` scans your project, detects your tech stack, and configures your AI coding CLIs with only the tools that matter. No more 40K+ tokens of overhead on every message.

| Before | After |
|--------|-------|
| 648 skills loaded globally | ~25 relevant skills per project |
| 192 agents loaded globally | ~8 relevant agents per project |
| 60 commands loaded globally | ~15 relevant commands per project |
| 19 MCP servers connected | ~5 relevant servers per project |
| All 12 language rulesets | Only detected languages |
| All 278 plugins enabled | Only matching plugins |
| **~40-45K tokens/msg overhead** | **~5-8K tokens/msg overhead** |

## 📦 Installation

`cctx` is built and installed automatically by [chezmoi](https://chezmoi.io/):

```bash
chezmoi apply
```

Or build manually:

```bash
cd tools/claude-context
cargo build --release
cp target/release/claude-context ~/.local/bin/
```

## 🎮 Usage

### Interactive TUI

```bash
cctx                          # Launch TUI with project scan + recommendations
```

Tabs: `[Skills]` `[Agents]` `[Commands]` `[MCP]` `[Rules]` `[Plugins]`

### Quick commands

```bash
cctx scan                     # Show project fingerprint (detected tech stack)
cctx apply <profile>          # Apply a saved profile
cctx apply --auto             # Auto-apply based on scan results
cctx apply --smart            # Auto-apply with AI refinement
cctx status                   # Show current project config
cctx diff                     # Compare active config vs current recommendations
cctx cost                     # Estimate token overhead (current vs global)
cctx save <name>              # Save current config as reusable profile
cctx profiles                 # List available profiles
cctx reset                    # Remove per-project config, revert to global
cctx init                     # Bootstrap a new project with starter profile
cctx trim <file>              # Analyze CLAUDE.md for token reduction opportunities
cctx trim --auto              # Auto-trim with backup
cctx index                    # Re-index skills/agents/commands from source
cctx doctor                   # Check integrity (broken symlinks, stale profiles)
cctx export <profile>         # Export profile to portable YAML
cctx import <file>            # Import profile from YAML file
```

### Flags

| Flag | Description |
|------|-------------|
| `--smart` | Enable AI-powered recommendations (requires Ollama or API key) |
| `--yes` | Skip confirmation prompts (for CI/automation) |

### TUI Keybindings

| Key | Action |
|-----|--------|
| `Tab` / `h` / `l` | Switch tabs |
| `j` / `k` / `Up` / `Down` | Navigate |
| `Space` / `Enter` | Toggle item |
| `/` | Filter/search |
| `A` | Select all (filtered) |
| `N` | Deselect all (filtered) |
| `PgUp` / `PgDn` | Scroll page |
| `g` / `G` | Top / bottom |
| `a` | Apply selections |
| `q` / `Esc` | Quit |

## 🔍 How it works

### 1. Project scanning

`cctx` analyzes your project to build a fingerprint:

- **Config files**: `tsconfig.json`, `Cargo.toml`, `go.mod`, `pyproject.toml`...
- **File extensions**: counts `.ts`, `.rs`, `.py`, `.go` files
- **Dependencies**: parses `package.json`, `Cargo.lock`, `requirements.txt`
- **Frameworks**: detects Next.js, Django, Axum, Spring Boot, Astro, Remix...
- **Infrastructure**: `Dockerfile`, `terraform/`, `helm/`, `.github/workflows/`
- **Databases**: `prisma/schema.prisma`, `migrations/`

Detection patterns are configurable via `~/.config/claude-context/patterns.yaml`.

### 2. Matching

Each skill, agent, and command has `match:` tags in its frontmatter:

```yaml
---
name: nextjs-developer
match:
  files: ["next.config.*", "app/**/page.tsx"]
  deps: ["next"]
  languages: ["typescript", "javascript"]
  tags: ["frontend", "fullstack", "react"]
  min_confidence: 0.7
---
```

The scanner crosses the project fingerprint with these tags to produce ranked recommendations with confidence tiers: CRIT (>95%), HIGH (>80%), MED (>60%), LOW.

### 3. AI refinement (optional)

With `--smart`, `cctx` sends the fingerprint to a local LLM (Ollama) or cloud API to catch context that file detection alone can't:

- Business domain from CLAUDE.md ("fintech" -> payment, compliance skills)
- Architectural patterns ("event-driven" -> websocket, chaos engineering)
- Migration intent ("moving to Rust" -> Rust skills even with 0 `.rs` files)

```bash
cctx --smart                     # One-time AI refinement
cctx config set ai.enabled true  # Make AI default for this project
```

### 4. Per-project config generation

`cctx` creates symlinks and settings for each detected AI CLI:

```
project/.claude/
  skills/               -> symlinks to ~/.skills/
  agents/               -> symlinks to ~/.agents/
  commands/             -> symlinks to ~/.claude/commands/
  rules/                -> symlinks to ~/.claude/rules/<lang>/
  settings.local.json   -> MCP overrides + plugin enables

project/.qwen/skills/   -> symlinks to ~/.skills/ (if Qwen installed)
project/.vibe/skills/   -> symlinks to ~/.skills/ (if Vibe installed)
project/.codex/skills/  -> symlinks to ~/.skills/ (if Codex installed)
```

## 🤖 Supported AI CLIs

| CLI | Full support | Skills | Detection |
|-----|-------------|--------|-----------|
| Claude Code | 6 resource types | ✅ | always |
| Qwen Code | Skills only | ✅ | `which qwen` |
| Vibe (Mistral) | Skills only | ✅ | `which vibe` |
| Codex (OpenAI) | Skills only | ✅ | `which codex` |
| Kimi CLI | Skills only | ✅ | `which kimi` |
| OpenCode | Skills only | ✅ | `which opencode` |

Add new CLIs via `~/.config/claude-context/cli-registry.yaml`.

## 📋 Profiles

### Built-in profiles (14)

| Profile | Focus |
|---------|-------|
| `dotfiles` | Shell scripting, chezmoi, CLI tools |
| `frontend` | React, Vue, Next.js, Tailwind |
| `backend-ts` | TypeScript/Node, Prisma, PostgreSQL |
| `fullstack` | Frontend + backend-ts combined |
| `rust` | Rust systems programming |
| `python` | Python, FastAPI, Django, data science |
| `golang` | Go services, microservices |
| `devops` | Docker, Terraform, K8s, CI/CD |
| `mobile` | React Native, Flutter, Swift, Kotlin |
| `ai-ml` | PyTorch, LangChain, RAG, fine-tuning |
| `security` | Pentesting, auditing, compliance |
| `data-engineering` | Spark, Airflow, dbt, Kafka |
| `cli-tools` | Building CLI applications |
| `monorepo` | Nx, Turborepo, PNPM workspaces |
| `saas-platform` | Full SaaS stack + auth, billing |

### Custom profiles

```bash
cctx save my-project          # Save current config
cctx profiles                 # List all profiles
cctx apply my-project         # Re-apply later
cctx export my-project        # Share with team
```

## 🏥 Health checks

```bash
$ cctx doctor

  [OK]   Source directories       skills, agents, commands, rules
  [OK]   Config directory         defaults.yaml and profiles/ present
  [OK]   Index                    646 skills, 192 agents, 60 commands
  [OK]   Profiles                 14 profiles valid
  [OK]   Symlinks: skills         25 symlinks OK
  [WARN] Symlinks: agents         1/8 broken symlinks
  [OK]   Detected CLIs            3/6 (claude, qwen, vibe)
```

## 💰 Token savings

```bash
$ cctx cost

  Skills (18)     ~4,200 tokens/msg
  Agents (6)      ~2,800 tokens/msg
  Commands (12)   ~1,500 tokens/msg
  MCP (5)         ~2,000 tokens/msg
  Rules (2 langs) ~1,200 tokens/msg
  Plugins (2)     ~800 tokens/msg
  -----------------------------------
  Total overhead  ~12,500 tokens/msg
  vs global:      ~43,000 tokens/msg
  Savings:        70% (-30,500 tokens/msg)
```

## 🔧 Configuration

```yaml
# ~/.config/claude-context/defaults.yaml
base:
  skills: [git-commit, code-review, plan, verify, debugger, ...]
  agents: [code-reviewer, planner, debugger, security-reviewer, ...]
  commands: [plan, verify, code-review, tdd, build-fix, ...]
  mcp: [context7, fetch, github, 1password, obsidian]
  rules: [common]
  plugins: []

ai:
  enabled: false          # Default: scanner only. Use --smart for AI.
  provider: ollama        # ollama | claude | openai
  model: "qwen3:8b"
  fallback: claude
  cache_ttl: "7d"
```

## 🏗️ Architecture

```
~/.skills/              <- 648 skills (source of truth)
~/.agents/              <- 192 agents (source of truth)
~/.claude/commands/     <- 60 commands (source of truth)
~/.claude/rules/        <- rules (source of truth)
~/.config/claude-context/
  ├── defaults.yaml     <- base config
  ├── patterns.yaml     <- scanner detection patterns
  ├── cli-registry.yaml <- supported CLIs
  ├── profiles/         <- saved profiles
  └── project-map.yaml  <- project -> profile mapping
```

## 📖 Related tools

- **RTK (Rust Token Killer)** — Reduces command *output* tokens (60-90%). Complementary to cctx which reduces *input* tokens (system prompt).
- **chezmoi** — Dotfiles manager. cctx is built and distributed via chezmoi.

## 📄 License

MIT
