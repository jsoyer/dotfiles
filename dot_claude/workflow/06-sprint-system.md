# Sprint System

## What Are Sprints?

For large PRDs, work is decomposed into **Sprints** — self-contained units designed for one agent in a healthy context window. Each sprint can be independently verified and should produce a working state.

## Sprint Rules

1. Each Sprint **MUST be independently verifiable** (own acceptance criteria and tests)
2. Each Sprint **SHOULD produce a working state** (builds and passes tests)
3. Ordered by dependency (N+1 may depend on N, never reverse)
4. Target size: **30-90 minutes** of agent work. Larger: decompose further
5. Maximum **5 sprints per PRD**. If more needed: split the PRD
6. Each sprint is **extracted into its own spec file** (not inline in the PRD)
7. Sprint agents load **ONLY their sprint spec file** — never the full PRD

### Why These Limits Exist

**Context Window:** AI models have a maximum number of tokens they can process. The longer the conversation, the more the model "forgets" earlier instructions — a phenomenon called "context rot." Sprints of 30-90 minutes keep context healthy.

**5 Sprint Limit:** Guards against the "Kitchen Sink" anti-pattern — stuffing everything into one monstrous PRD. If you need more than 5 sprints, the work is too large for a single PRD and should be split by independent deliverable.

## Sprint File Structure

```
docs/tasks/<area>/<category>/YYYY-MM-DD_HHmm-name/
├── spec.md                     # The PRD itself
├── progress.json               # Sprint tracking state
└── sprints/
    ├── 01-setup-auth.md        # Sprint 1 spec (self-contained)
    ├── 02-login-ui.md          # Sprint 2 spec (self-contained)
    └── 03-route-protection.md  # Sprint 3 spec (self-contained)
```

## File Boundaries

Each sprint spec declares **file boundaries** — which files it creates, modifies, reads, and shares:

```
files_to_create:    [new files this sprint builds]
files_to_modify:    [existing files this sprint can touch]
files_read_only:    [files to reference but NOT modify]
shared_contracts:   [interfaces/types shared across sprints]
```

**Why file boundaries matter:** If two sprints both modify `src/app/layout.tsx`, they cannot run in parallel — their changes would conflict. File boundaries make this explicit during planning, before any code is written.

## Sprint Spec Template

Each sprint gets its own file:

```markdown
## Meta
Sprint: N | Batch: M | Model: sonnet | Depends on: [list]

## Objective
[One sentence describing what this sprint accomplishes]

## File Boundaries
files_to_create: [list]
files_to_modify: [list]
files_read_only: [list]
shared_contracts: [list]

## Tasks
- [ ] Task 1
- [ ] Task 2
- [ ] Task 3

## Acceptance Criteria
- [ ] Criterion 1
- [ ] Criterion 2

## Verification
[Specific commands to run]

## Context
[Relevant details from PRD — NOT the entire PRD]

## Agent Notes (filled by executor)
### Decisions Made
### Assumptions
### Issues Found
```

## Progress Tracking (progress.json)

The orchestrator tracks sprint state with `progress.json`:

```json
{
  "sprints": [
    {
      "id": "01-setup-auth",
      "status": "complete",
      "batch": 1,
      "depends_on": [],
      "started_at": "2026-03-14T14:00:00Z",
      "completed_at": "2026-03-14T14:45:00Z"
    },
    {
      "id": "02-login-ui",
      "status": "in_progress",
      "batch": 2,
      "depends_on": ["01-setup-auth"],
      "started_at": "2026-03-14T14:50:00Z"
    },
    {
      "id": "03-route-protection",
      "status": "pending",
      "batch": 2,
      "depends_on": ["01-setup-auth"]
    }
  ]
}
```

Status values: `pending` → `in_progress` → `complete` or `blocked`

## Batch Planning

Sprints are grouped into **batches** based on dependencies:

```
Batch 1:  Sprint 1 (no dependencies — runs first)
          │
          ▼
Batch 2:  Sprint 2 + Sprint 3 (both depend on Sprint 1, but not on each other)
          │              │
          ▼              ▼
          (run in parallel — different files)
```

**Rules for batching:**
1. Analyze tasks for file overlap and dependencies
2. **DEPENDENT** if: same files, same component tree, shared config, output feeds another
3. **INDEPENDENT** if: different files/dirs, unrelated features, no shared deps
4. When in doubt, run sequentially — safe > fast

## PRD Templates

### Minimal PRD (Standard Mode)

```markdown
# [Task Title]

## What & Why
**Problem:** [What is wrong or missing]
**Desired Outcome:** [What success looks like]

## Correctness Contract
**Audience:** [Who uses this output]
**Verification:** [How to check correctness]

## Acceptance Criteria
- [ ] [Binary testable condition 1]
- [ ] [Binary testable condition 2]

## Non-Goals / Boundaries
- [What this task will NOT do]

## If Uncertain
[Default policy: Guess / Flag / Stop]

## Verification
- [ ] [Specific test/lint/typecheck command]

## Implementation
- [ ] [Step 1]
- [ ] [Step 2]

## Learnings (filled after completion)
```

### Full PRD (PRD+Sprint Mode)

Adds to the minimal template:
- **Justification** — Why this is worth doing now
- **Failure/Danger definitions** — What makes output useless or harmful
- **Risk Tolerance** — Confident wrong or refusal?
- **Success Metrics** — Current values and targets
- **User Stories** — GIVEN/WHEN/THEN format
- **Shared Contracts** — Interfaces/types shared across sprints
- **Technical Constraints** — Stack, architecture, performance, security
- **Open Questions** — Known unknowns
- **Sprint Decomposition** — Table of sprints with dependencies and models

Full templates are in `~/.claude/skills/plan/prd-template-minimal.md` and `prd-template-full.md`.

## Why Each PRD Field Exists

| Field | Purpose |
|---|---|
| **What & Why** | Problem before solution. If you can't articulate the problem, you shouldn't be building |
| **Correctness Contract** | Defines "correct" before implementation |
| **Acceptance Criteria** | Binary conditions (pass/fail). If you can't write a test for it, it's not valid |
| **Non-Goals** | As important as goals. Prevents scope creep |
| **Verification** | If you can't describe how to verify, the spec is incomplete |
| **Learnings** | Filled after completion. Entry point for the Compound step |

---

Next: [Agents](07-agents.md)
