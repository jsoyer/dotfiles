# Workflow: Sprint System & Context Engineering

## Sprint Decomposition

Large PRDs decompose into Sprints — self-contained units for one agent in a healthy context window.

**Rules:**

1. Each Sprint MUST be independently verifiable (own acceptance criteria and tests)
2. Each Sprint SHOULD produce a working state (builds and passes tests)
3. Ordered by dependency (N+1 may depend on N, never reverse)
4. Target size: 30-90 minutes of agent work. Larger: decompose further
5. Maximum 5 sprints per PRD. If >5 needed, split by independent deliverable — the test: "could these be built by two teams who never talk?" If yes, split. If they share files, keep together.
6. Each sprint is extracted into its own spec file during planning (not inline in the PRD)
7. Sprint agents load ONLY their sprint spec file — never the full PRD

**Sprint File Structure:** `spec.md` + `progress.json` + `INVARIANTS.md` + `sprints/NN-title.md` per sprint. Each sprint spec declares file boundaries (`files_to_create`, `files_to_modify`, `files_read_only`, `shared_contracts`). Full schema: `~/.claude/skills/plan/SKILL.md`.

## Build Candidate

A **Build Candidate** is a tagged commit declaring "this specification is complete enough to build from" — the formal gate between planning and execution. Tag format: `build-candidate/<prd-name>`.

**When to tag:** After PRD, sprint specs, progress.json, and INVARIANTS.md are written and reviewed. `/plan` tags it; `/plan-build-test` verifies it exists before execution.

## Architecture Invariant Registry (INVARIANTS.md)

`INVARIANTS.md` at the project root defines every cross-cutting concept with machine-verifiable contracts. Enforced by `check-invariants.sh` PostToolUse hook.

**Format:**
```markdown
## [Concept Name]
- **Owner:** [bounded context that defines this concept]
- **Preconditions:** [what consumers must satisfy before using this]
- **Postconditions:** [what the owner guarantees after execution]
- **Invariants:** [what must always hold across all contexts]
- **Verify:** `shell command that exits 0 if invariant holds`
- **Fix:** [how to fix if violated]
```

**Cascading invariants:** Project-level applies everywhere. Component-level adds constraints for specific directories. Hook walks up from edited file to project root. Create during `/plan` phase — part of the Build Candidate.

**Orchestrator design:** Deterministic checklist — read progress.json → find next batch → spawn sprint-executors with ONLY their sprint spec → collect results → code review → merge → dev server verification → update progress.json → return. Full protocol: `~/.claude/agents/orchestrator.md`.

## PRD-Driven Task System

**Location:** `docs/tasks/<area>/<category>/YYYY-MM-DD_HHmm-descriptive-name.md`
**Categories:** `feature`, `bugfix`, `refactor`, `infrastructure`, `security`, `documentation`

**Correctness Discovery — Standard mode (2 questions):**
1. **Audience:** Who uses this output and what decision will they make?
2. **Verification:** How would you check if the output is correct?

**Correctness Discovery — PRD+Sprint mode (6 questions):** adds Failure Definition, Danger Definition, Uncertainty Policy, Risk Tolerance. Full framework: `~/.claude/skills/plan/correctness-discovery.md`.

## Agent Architecture

- **orchestrator** — Task management, sprint lifecycle, agent delegation. Full tool access. Uses opus.
- **sprint-executor** — Single sprint execution. Isolated worktree. Uses sonnet. Tools: Read, Write, Edit, Bash, Glob, Grep.
- **code-reviewer** — Read-only post-sprint review. Uses sonnet. Tools: Read, Grep, Glob.

Sprint agents use `isolation: worktree`. Independent sprints can run in parallel; orchestrator handles merging. `cleanup-worktrees.sh` Stop hook prunes stale worktrees and removes merged sprint branches.

## Context Rot Protocol

**Signs:** Responses become generic, rules forgotten, questions re-asked, fixed errors reappear.

**Action:** Save state (update checkboxes, fill Agent Notes), write pending insights to session-learnings, report: "Context degrading. Recommend new session."

**Prevention:** Orchestrator keeps context lean. Sprint agents receive ONLY their sprint spec. Never forward raw output between sprints. Order context by stability: system instructions, docs, session state, current task.

## Parallel Execution with Worktrees

DEPENDENT tasks: same files, same component tree, shared config, output feeds another — run sequentially.
INDEPENDENT tasks: different files/dirs, unrelated features, no shared deps — spawn all in a single message.

Spawn all batch agents in a single message. Each uses `isolation: worktree`. Worktree agents must NOT modify coordination files or install dependencies. Merge each branch sequentially. Conflicts: spawn opus agent. Build fails after merges: spawn sonnet agent to fix.

## Subagent Communication Protocol

- Every subagent prompt ends with: "Return a structured summary: [specify exact fields needed]"
- Never ask a subagent to "return everything" — specify exact data points
- Target 10-20 lines of actionable info per subagent result
- Chain subagents: extract only relevant fields from agent A to pass to agent B — never forward raw output
