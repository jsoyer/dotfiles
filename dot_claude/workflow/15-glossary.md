# Glossary

| Term | Definition |
|---|---|
| **ADR** | Architecture Decision Record — document capturing a significant architectural decision with context, options, and consequences |
| **Anti-Goodhart** | Verification that tests measure real behavior, not just metrics. Named after Goodhart's Law: "When a measure becomes a target, it ceases to be a good measure" |
| **Batch** | A group of sprints that can run in parallel because they have no file overlaps or dependencies |
| **Biome** | Fast Rust-based formatter and linter for JS/TS/JSON/CSS, alternative to Prettier + ESLint |
| **CLS** | Cumulative Layout Shift — how much a page "jumps" during loading. Target: < 0.1 |
| **Compound** | The phase where learnings from a task are captured and the system improves itself |
| **Compound Engineering** | Engineering approach where each task not only delivers the result but improves the system for future tasks |
| **Contract-First** | Pattern: user describes intent → agent mirrors understanding → user confirms before execution begins |
| **Context Budget** | Per-window token targets for autocompact (128K: 100K, 200K: 125K, 1M: 150K) managed by `set-compact.sh` |
| **Context Rot** | Quality degradation when the context window fills up, causing the model to "forget" earlier instructions |
| **Context Window** | Maximum tokens the model can process at once — the model's "working memory" |
| **Correctness Discovery** | 6-question framework for defining what "correct" means before building anything |
| **Delegation** | Pattern where the main agent (orchestrator) delegates file reads and heavy commands to subagents, enforced by `enforce-delegation.sh` |
| **E2E** | End-to-End testing — tests that simulate complete user flows through the application |
| **Error Registry** | Cross-project database (`error-registry.json`) of error patterns, root causes, fixes, and failed approaches |
| **Evolution** | The system's self-improvement mechanism — tracking errors, model performance, and system changes across all projects |
| **Execution Config** | Project-specific commands and URLs defined in a project's `CLAUDE.md` that skills read to know how to build, test, deploy, etc. |
| **File Boundaries** | Declaration in sprint specs of which files a sprint creates, modifies, reads, and shares — prevents parallel sprint conflicts |
| **Frontmatter** | YAML block at the start of a markdown file defining metadata (name, model, tools, etc.) |
| **Haiku** | Claude's lightest/fastest model — used for scanning, discovery, and simple tasks |
| **Hook** | Script that runs automatically at lifecycle points in Claude Code (PreToolUse, PostToolUse, Stop, Notification) |
| **INP** | Interaction to Next Paint — response time to user interactions. Target: < 200ms |
| **LCP** | Largest Contentful Paint — time until the largest visible element renders. Target: < 2.5s |
| **LSP** | Language Server Protocol — understands code semantics for precise navigation (goToDefinition, findReferences, etc.) |
| **Micro-Compound** | Abbreviated compound for Quick Fix mode: one question — "Would the system catch this next time?" |
| **Mode Fluency** | The practice of switching freely between Quick Fix, Standard, and PRD+Sprint modes within a single task |
| **Opus** | Claude's most powerful/expensive model — used for complex refactoring, architecture decisions, and merge conflicts |
| **Orchestrator** | Agent that manages sprint lifecycle, delegates to executors, and handles merging — never implements code directly |
| **pnpm** | Fast, efficient Node.js package manager that shares dependencies via hard links instead of copying |
| **PRD** | Product Requirements Document — specification that defines what to build and why |
| **proot-distro** | User-space process emulator for running Linux on ARM64 devices (e.g., Termux on Android) |
| **Quick Fix** | Execution mode for trivial fixes — single file, < 30 lines, no architectural impact |
| **Session Learnings** | File-based session memory that survives context compression (`/compact`) |
| **Skill** | Auto-invocable workflow defined in `skills/` with a `SKILL.md` file |
| **Soft Block** | Hook-enforced pause that requires user approval to proceed (vs hard block which always denies) |
| **Sonnet** | Claude's balanced model — used for standard implementation, testing, bug fixes, and code review |
| **Stochastic Consensus** | Research method: N agents explore independently, then a synthesizer arbitrates — surfaces real disagreements instead of averaging |
| **Sprint** | Self-contained unit of work within a PRD, designed for one agent in a healthy context window |
| **Sprint Executor** | Agent that receives a sprint spec and implements it within an isolated worktree |
| **TDD** | Test-Driven Development — write tests before production code (Red → Green → Refactor) |
| **Verification Gate** | One of 6 blocking quality checks that must pass before work can be marked complete |
| **Worktree** | Isolated Git working copy with its own branch — used for parallel sprint execution without file conflicts |
| **XSS** | Cross-Site Scripting — web security vulnerability where malicious scripts are injected into web pages |

---

Back to [Documentation Index](README.md)
