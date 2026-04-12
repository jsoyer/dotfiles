# Architecture

## Repository Structure

```
~/.claude/
├── CLAUDE.md                           # The brain — all rules and workflows
├── README.md                           # Documentation for humans
├── settings.json                       # Deterministic enforcement — hooks & permissions
├── VERSION                             # Semantic version of the workflow system
├── set-compact.sh                      # Context budget management (per-window autocompact)
├── statusline-command.sh               # Status line display for Claude Code UI
├── .gitignore                          # What NOT to version control
│
├── agents/                             # Specialized agents with their own context
│   ├── orchestrator.md                 # Project manager — delegates, never implements (opus)
│   ├── sprint-executor.md              # Worker — implements a sprint in isolation (sonnet)
│   └── code-reviewer.md               # Auditor — read-only, cannot modify code (sonnet)
│
├── skills/                             # Auto-invocable workflows
│   ├── plan/                           # Planning and PRD generation
│   │   ├── SKILL.md                    # Planning workflow
│   │   ├── correctness-discovery.md    # 6-question correctness framework
│   │   ├── prd-template-minimal.md     # Minimal PRD template (Standard mode)
│   │   ├── prd-template-full.md        # Full PRD template (PRD+Sprint mode)
│   │   └── sprint-spec-template.md     # Sprint specification template
│   ├── create-project/                 # Greenfield project PRD with architecture defaults
│   │   └── SKILL.md
│   ├── plan-build-test/                # Full local pipeline
│   │   └── SKILL.md
│   ├── research/                       # Deep multi-agent research (Stochastic Consensus)
│   │   └── SKILL.md
│   ├── ship-test-ensure/               # Deploy pipeline
│   │   └── SKILL.md
│   ├── compound/                       # Post-task learning capture
│   │   └── SKILL.md
│   ├── workflow-audit/                 # Periodic system self-review
│   │   └── SKILL.md
│   ├── update-docs/                    # Analyze code and update project docs
│   │   └── SKILL.md
│   ├── playwright-stealth/             # Anti-detection browsing for content verification
│   │   └── SKILL.md
│   └── find-skills/                    # Discover and install skills from the ecosystem
│       └── SKILL.md
│
├── rules/                              # Modular rule files included via @rules/
│   ├── workflow.md                     # Sprint system, context engineering, agents
│   ├── quality.md                      # Evaluation, self-improvement, session learnings
│   └── environment.md                  # PRoot-Distro ARM64 environment rules
│
├── commands/                           # Custom slash commands
│   └── setup-hooks.md                  # /setup-hooks — detect stack, verify hook config
│
├── hooks/                              # Deterministic enforcement scripts
│   ├── lib/                            # Shared libraries
│   │   ├── detect-project.sh           # Language/project detection (16 languages)
│   │   ├── approvals.sh               # Soft-block approval helpers
│   │   ├── hook-logger.sh             # Hook execution logging
│   │   ├── project-cache.sh           # Project detection caching
│   │   └── stop-guard.sh             # Stop hook re-entrancy guard
│   ├── block-dangerous.sh              # Blocks destructive commands
│   ├── block-heavy-bash.sh             # Soft-blocks heavy build/test in main agent
│   ├── check-test-exists.sh            # TDD gate — blocks edits without test file
│   ├── check-invariants.sh             # Verifies INVARIANTS.md rules after edits
│   ├── check-docs-updated.sh           # Blocks push if workflow changed without docs
│   ├── post-edit-quality.sh            # Auto-formats code after edits (all langs)
│   ├── scan-secrets.sh                 # Scans for exposed secrets in edited files
│   ├── enforce-delegation.sh           # Enforces orchestrator delegation pattern
│   ├── reset-delegation-counter.sh     # Resets read counter each turn
│   ├── end-of-turn-typecheck.sh        # Static type checking (all langs)
│   ├── cleanup-artifacts.sh            # Moves stray media to .artifacts/
│   ├── cleanup-worktrees.sh            # Prunes stale worktrees
│   ├── compact-save.sh                 # Saves state before context compression
│   ├── compact-restore.sh              # Restores state after context compression
│   ├── compound-reminder.sh            # Blocks session end without learning capture
│   ├── verify-completion.sh            # Blocks premature completion claims
│   ├── session-start.sh                # Environment detection and session init
│   ├── approve.sh                      # Soft-block approval entry point
│   ├── scripts/                        # Utility scripts called by skills/agents
│   │   ├── approve.sh                  # Batch approval mechanism
│   │   ├── harness-health.sh           # System health diagnostic
│   │   ├── retry-with-backoff.sh       # Retry helper for external API calls
│   │   ├── validate-i18n-keys.sh       # Cross-validates i18n keys across locales
│   │   ├── validate-sprint-boundaries.sh # Sprint file boundary validation
│   │   ├── verify-worktree-merge.sh    # Detects silent overwrites in merges
│   │   └── worktree-preflight.sh       # Language-aware worktree dependency setup
│   └── tests/                          # Behavioral tests for hooks
│       ├── run-all.sh
│       ├── test-block-dangerous.sh
│       ├── test-block-heavy-bash.sh
│       ├── test-check-test-exists.sh
│       ├── test-enforce-delegation.sh
│       └── test-scan-secrets.sh
│
├── test-workflow-mods/                 # Workflow integrity test suite
│   ├── run-tests.sh                    # 405 assertions validating ~/.claude/ structure
│   └── testdata/                       # Fixture projects for hook behavioral tests
│
├── docs/                               # Reference material (loaded on demand)
│   ├── on-demand/                      # Detailed guides loaded by skills when needed
│   │   ├── anti-patterns-full.md       # 10 anti-patterns with examples and fixes
│   │   ├── browser-verification.md     # End-of-task browser verification protocol
│   │   ├── dev-server-protocol.md      # Dev server management protocol
│   │   ├── evaluation-reference.md     # Quality evaluation checklists
│   │   ├── proot-distro-environment.md # proot-distro ARM64 guide
│   │   ├── vague-requirements-translator.md
│   │   └── verification-gates.md       # 6 blocking verification gates
│   └── reference/                      # Templates and guides
│       ├── model-assignment.md         # Model assignment reference
│       ├── project-claude-md-template.md # Template for project-specific CLAUDE.md
│       └── universal-workflow-guide.md # How to use/extend for any language
│
├── workflow/                           # This documentation
│
└── evolution/                          # Cross-project learning data
    ├── error-registry.json             # Error patterns across projects
    ├── model-performance.json          # Model success rate tracking
    ├── workflow-changelog.md           # System evolution history
    └── session-postmortems/            # Structured post-session analysis
```

## The Five Layers

Each layer of the repository serves a distinct purpose with a specific enforcement model:

```
┌─────────────────────────────────────────────────────────┐
│                     CLAUDE.md                           │
│              The Constitution — fundamental rules       │
│         (loaded every session, costs context tokens)    │
├─────────────────────────────────────────────────────────┤
│                    settings.json                        │
│          The Police — deterministic enforcement         │
│              (hooks run as real code)                   │
├─────────────────────────────────────────────────────────┤
│                      agents/                            │
│         Specialized Workers — each with own role        │
│          (own context window, permissions, model)       │
├─────────────────────────────────────────────────────────┤
│                      skills/                            │
│        Operating Procedures — step-by-step workflows    │
│           (auto-invoked based on conversation)          │
├─────────────────────────────────────────────────────────┤
│                       docs/                             │
│          Reference Library — consulted on demand        │
│          (not loaded every session — saves context)     │
├─────────────────────────────────────────────────────────┤
│                     hooks/                              │
│         Enforcement Scripts — hard/soft blockers        │
│          (bash scripts, run before/after actions)       │
├─────────────────────────────────────────────────────────┤
│                    evolution/                           │
│        System Memory — cross-project learning           │
│           (error patterns, model performance)           │
└─────────────────────────────────────────────────────────┘
```

## Layer Responsibilities

### Layer 1: CLAUDE.md (The Constitution)

- **What:** ~650 lines of rules, workflows, judgment protocols, and development standards
- **When loaded:** Every session start (costs context tokens)
- **Enforcement:** Probabilistic — the model "should" follow these rules but can deviate
- **Design rule:** Keep it dense and essential. If something can live in `docs/`, move it there

### Layer 2: settings.json + hooks/ (The Police)

- **What:** Shell scripts that run as hooks at specific lifecycle points
- **When loaded:** Every tool use (PreToolUse), every edit (PostToolUse), every session end (Stop)
- **Enforcement:** Deterministic — code runs regardless of what the model thinks
- **Design rule:** The model cannot bypass a hook. Use hooks for rules that must never be broken

### Layer 3: agents/ (The Workers)

- **What:** Specialized agents with their own context window, tools, model, and permissions
- **When loaded:** When spawned by the orchestrator or skills
- **Enforcement:** Tool-level — each agent only has access to specific tools
- **Design rule:** Principle of Least Privilege — give each agent only what it needs

### Layer 4: skills/ (The Procedures)

- **What:** Step-by-step workflows that auto-invoke based on conversation context
- **When loaded:** When triggered by user intent or explicit `/skill-name` command
- **Enforcement:** Process — skills define the order of operations
- **Design rule:** Skills never hardcode project details — they read from Execution Config

### Layer 5: docs/ (The Library)

- **What:** Detailed reference material for specific topics
- **When loaded:** On demand, when a skill or agent references them
- **Enforcement:** None — purely informational
- **Design rule:** Save context by keeping detailed content here, not in CLAUDE.md

### Layer 6: evolution/ (The Memory)

- **What:** Cross-project learning data — error patterns, model performance, system changelog
- **When loaded:** During `/compound` and `/workflow-audit`
- **Enforcement:** Adaptive — data drives model selection and rule creation
- **Design rule:** Capture everything, analyze periodically, promote proven patterns

## What Gets Version Controlled

The `.gitignore` reveals an important decision about what is **shared system** vs. **ephemeral state**:

**Versioned (the system):**
- `CLAUDE.md`, `settings.json`, `README.md`
- `agents/`, `skills/`, `hooks/`, `docs/`
- `evolution/` (error-registry, model-performance, changelog)

**Not versioned (the state):**
- `.state/`, `projects/`, `backups/`, `cache/`, `history.jsonl`
- `worktrees/` (temporary directories for parallel execution)
- `settings.local.json` (machine-specific overrides)
- `todoStorage.json`, `*.log`, `plans/`, `tasks/`, `telemetry/`

The key decision: **version the system (rules, agents, skills, hooks), not the state (cache, history, temporary data)**. This allows cloning the repository on any new machine and having the system work immediately.

## How the Layers Interact

```
User says: "I need to add OAuth login"

1. CLAUDE.md classifies this as PRD+Sprint mode
2. /plan skill auto-invokes (Layer 4)
3. Contract-First pattern runs (Layer 1 rule)
4. Correctness Discovery questions asked (Layer 4 references Layer 5)
5. PRD created, sprints extracted (Layer 4)
6. /plan-build-test spawns orchestrator agent (Layer 3)
7. Orchestrator spawns sprint-executor agents in worktrees (Layer 3)
8. block-dangerous.sh prevents any destructive commands (Layer 2)
9. post-edit-quality.sh auto-formats every edit (Layer 2)
10. End-of-turn typecheck catches type errors (Layer 2)
11. /compound captures learnings (Layer 4)
12. Error patterns saved to evolution/ (Layer 6)
13. compound-reminder.sh blocks session end without learnings (Layer 2)
```

Every layer plays its part. The system works because no single layer is responsible for everything.

---

Next: [The Constitution (CLAUDE.md)](04-constitution.md)
