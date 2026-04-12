# Agents

Agents are specialized workers that live in `~/.claude/agents/`. Each has its **own context window**, tool permissions, model, and system prompt. They follow the **Principle of Least Privilege** — each agent has only the permissions necessary for its role.

## Architecture Overview

```
┌───────────────────────────────────────────────────────────────────┐
│                        ORCHESTRATOR                               │
│  Model: opus    |  Tools: ALL (including Agent)                  │
│  Role: Delegates, coordinates, merges. NEVER implements.          │
│  Context: System instructions + progress.json + agent summaries  │
│                                                                   │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │ SPRINT-EXECUTOR │  │ SPRINT-EXECUTOR │  │  CODE-REVIEWER  │  │
│  │ Model: sonnet   │  │ Model: sonnet   │  │  Model: sonnet  │  │
│  │ Tools: R/W/E/B  │  │ Tools: R/W/E/B  │  │  Tools: R only  │  │
│  │ Isolation:      │  │ Isolation:      │  │  Cannot modify   │  │
│  │ worktree        │  │ worktree        │  │  any files       │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
│                                                                   │
│         Sprint 1              Sprint 2          Post-merge        │
│       (own branch)          (own branch)        review            │
└───────────────────────────────────────────────────────────────────┘
```

## Agent Frontmatter

Each agent file begins with a YAML block defining its properties:

```yaml
---
name: sprint-executor
description: >
  Executes a single sprint from a sprint spec file...
model: sonnet
tools: Read, Write, Edit, Bash, Glob, Grep
isolation: worktree
permissionMode: default
maxTurns: 200
---
```

| Property | Purpose |
|---|---|
| `name` | Unique identifier |
| `description` | When and how to invoke (Claude Code uses this for automatic selection) |
| `model` | Which Claude model to use (haiku/sonnet/opus) |
| `tools` | Available tools (Principle of Least Privilege) |
| `isolation` | `worktree` creates an isolated working directory with its own Git branch |
| `maxTurns` | Maximum interactions the agent can make |

## Agent Comparison

| Agent | Model | Tools | Why This Model | Why These Tools |
|---|---|---|---|---|
| orchestrator | opus | ALL + Agent | Handles complex coordination, merge conflicts, and sprint lifecycle management | Needs to spawn/manage other agents |
| sprint-executor | sonnet | Read, Write, Edit, Bash, Glob, Grep | Good cost-benefit for implementation work | Needs to write code but NOT delegate |
| code-reviewer | sonnet | Read, Grep, Glob | Read-only analysis | ONLY read — reviewer must report, not fix |

## The Orchestrator

The orchestrator is the most important agent. It follows a **deterministic checklist** — it is a workflow engine, not a strategist.

### The 11-Step Protocol

```
Step 0:  Preflight
         ├── Git readiness (init if needed)
         ├── Working tree hygiene (dirty → snapshot commit)
         ├── Stale worktree cleanup
         ├── proot-distro detection
         └── Dependency baseline

Step 1:  Read progress.json + project CLAUDE.md

Step 2:  Load sprint spec files, validate file boundaries

Step 3:  Update progress.json → "in_progress"

Step 4:  Spawn sprint-executor agents
         (parallel for independent sprints, sequential for dependent)

Step 5:  Collect structured results from executors

Step 6:  Merge (for parallel batches)
         ├── Sequential merge (lowest sprint number first)
         ├── Conflict resolution (≤3 files: direct, >3: opus agent)
         ├── Post-merge test suite
         ├── File boundary validation
         ├── Worktree cleanup
         └── Code review (spawn code-reviewer agent)

Step 7:  Coherence check (full test suite)

Step 8:  Dev server smoke test (content-verified, not just HTTP 200)

Step 8.5: Plan completeness audit (re-read specs, cite evidence)

Step 9:  Update progress.json → "complete" or "blocked"

Step 10: Return structured report with metrics
```

### What the Orchestrator NEVER Does

- Implement code directly (delegates to sprint-executor)
- Read the full PRD (sprint spec files are self-contained)
- Make strategic decisions about sprint ordering (progress.json has the plan)
- Modify session-learnings (the caller does that)
- Proceed to the next batch (returns to caller for fresh context)
- Accept "environment limitation" as reason to skip dev server test

**One orchestrator invocation = one batch.** After completing its batch, it returns control. The caller spawns the next orchestrator for the next batch, ensuring fresh context.

### Why Opus

The orchestrator handles complex coordination: sprint lifecycle management, merge conflict resolution, coherence verification, and plan completeness audits. While it follows a deterministic checklist, the decisions at each step (conflict resolution, coherence assessment, when to mark blocked vs retry) benefit from stronger reasoning. The CLAUDE.md model assignment matrix specifies opus for sprint orchestration.

## The Sprint Executor

The sprint-executor receives a spec and implements it within an isolated worktree.

### Key Characteristics

- Runs in **isolated worktree** — own branch and directory
- Has `maxTurns: 200` — can iterate extensively
- Does NOT have the `Agent` tool — cannot delegate
- Does NOT run dev server or E2E (integration concerns handled by orchestrator)

### Protocol

```
Step 0:  Worktree bootstrap (verify deps, set proot env)

Step 1:  Parse sprint spec
         ├── Extract objective, file boundaries, tasks, criteria
         ├── ONLY create files in files_to_create
         ├── ONLY modify files in files_to_modify
         └── Out-of-boundary needs: log in Agent Notes, do NOT modify

Steps 2-6: Execute tasks one by one with TDD
            ├── Update checkboxes IMMEDIATELY after each task
            └── If task fails: retry 3x, then mark BLOCKED

Step 7:  Fill Agent Notes (decisions, assumptions, issues)

Step 8:  Anti-Goodhart verification

Step 9:  Sprint acceptance criteria

Step 10: Full verification (build → lint → type-check → test)

Step 11: SKIP dev server and E2E (orchestrator handles post-merge)

Step 12: Plan Completeness Audit (MANDATORY last step)

Step 13: Return structured summary
```

### Why Executors Skip Dev Server

Sprint-executors work in isolated worktrees. Running a dev server per worktree would be redundant and wasteful. The orchestrator runs dev server verification after merging all sprints — testing the integrated code, which is what matters.

## The Code Reviewer

The code-reviewer is intentionally limited to **read-only** access.

### Checklist

1. **Correctness** — Does code match the spec?
2. **Security** — Any auth bypass, data leak, unvalidated input?
3. **Patterns** — Does new code follow existing project patterns?
4. **Edge Cases** — Error paths handled? Null/empty/boundary inputs?
5. **Tests** — Verify behavior or just output? Missing coverage?
6. **Coherence** — Consistent with rest of codebase?

### Output Format

```
Verdict: PASS / NEEDS CHANGES / BLOCKING ISSUES
Findings: severity-coded (minor / should fix / must fix)
```

### Why Read-Only?

A reviewer who can edit has incentive to "fix" instead of report. Forcing read-only means the reviewer reports and the executor (or another agent) fixes — separation of responsibilities.

## Worktree Isolation

Sprint agents use `isolation: worktree` in their frontmatter. Each gets its **own working copy** of the Git repository:

```
Main Repository
├── main branch (orchestrator's territory)
│
├── Worktree 1: sprint/01-setup-auth
│   └── Sprint-executor 1 works here
│       (own branch, own directory, own files)
│
├── Worktree 2: sprint/02-login-ui
│   └── Sprint-executor 2 works here
│       (can run IN PARALLEL with executor 1)
│
└── After completion:
    Orchestrator merges worktree branches → main
    Worktrees auto-cleaned
```

### Why Worktrees?

1. **Safe parallelism:** Independent sprints run simultaneously without interference
2. **Easy rollback:** If a sprint goes wrong, discard the worktree and delete the branch

## Context Budget Rules

The main agent is an **orchestrator**, not a worker. Its context should contain only: system instructions + session learnings + subagent summaries + user messages.

**Rules:**
- If you need to read file contents or build output, delegate to a subagent
- Every subagent prompt ends with: "Return a structured summary: [specify exact fields]"
- Never ask a subagent to "return everything" — specify exact data points
- Target 10-20 lines of actionable info per subagent result
- Chain subagents: extract only relevant fields from agent A to pass to agent B

---

Next: [Skills Reference](08-skills-reference.md)
