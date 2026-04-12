# Quality: Evaluation, Self-Improvement & Session Learnings

## Verification Pattern

LLMs are non-deterministic. The most reliable pattern combines prose specification (intent, context, constraints) + executable tests (machine-verifiable contracts) + iteration loops (run, fail, fix, run).

**Adaptive retry budget:**
- `transient` failures (network, timeout, flaky test) → up to 5 retries
- `logic` failures (wrong approach, broken implementation) → max 2, then try different approach
- `environment` failures (proot limitation, missing binary) → 1 retry, then mark BLOCKED
- `config` failures (bad setting, wrong flag) → max 3 retries

Full evaluation checklists (Stack Evaluation, Diagnostic Loop, Spec Self-Evaluator): `~/.claude/docs/on-demand/evaluation-reference.md`.

## Code Intelligence

Prefer LSP over Grep/Glob/Read for code navigation. Key operations: `goToDefinition`, `findReferences`, `hover`, `documentSymbol`, `workspaceSymbol`, `goToImplementation`, `incomingCalls`, `outgoingCalls`. Before renaming or changing a function signature, use `findReferences` to find all call sites first. After writing or editing code, check LSP diagnostics and fix type errors or missing imports immediately.

## Session Learnings

Maintain a session learnings file as living memory that survives `/compact`. Path from project CLAUDE.md `session-learnings-path`; default: `docs/session-learnings.md`. Created proactively by `/plan-build-test` Phase 0.

**Update rules:** Append errors as they occur, patterns when they repeat, rules when mistakes happen, task status as work progresses. Use structured format with categories (ENV, LOGIC, CONFIG, etc.) — full schema in `/compound` skill Step 6.

**Promotion:** 2+ tasks → `docs/solutions/`. 2+ projects → `~/.claude/evolution/error-registry.json` + memory.

## Compact Recovery Protocol

Automated by PreCompact/PostCompact hooks. Manual fallback when hooks miss state:

1. Re-read the session learnings file (path from project CLAUDE.md)
2. Re-read project knowledge files (patterns, MEMORY.md)
3. Resume from the last completed phase — do NOT restart
4. If mid-deploy or mid-monitoring, re-check current status before continuing

## Per-Task Compound (every task — enforced by stop hook)

1. **Capture:** What worked? What didn't? What is the reusable insight?
2. **Document:** Create solution doc if reusable. Update session learnings.
3. **Update the system:** If a rule/pattern/doc needs changing, do it now — not "later."
4. **Verify:** "Would the system catch this automatically next time?" If no, compound is incomplete.
5. **Capture user corrections** as error-registry entries and model-performance data (richest signal).

## Per-Session Compound (end of session)

Run `/compound` — handles: compile, generate rules, promote to solutions, persist to memory, cross-project evolution (error-registry, model-performance, workflow-changelog, session postmortem). Full protocol: `~/.claude/skills/compound/SKILL.md`.

**Periodic:** Run `/workflow-audit` monthly or after 10+ sessions.

## Knowledge Promotion Chain

**Per-project:** session-learnings → `docs/solutions/` → ADRs → CLAUDE.md updates. Promote when a pattern proves useful across 2+ tasks.

**Cross-project:** session-learnings → `~/.claude/evolution/error-registry.json` → `~/.claude/evolution/model-performance.json` → `~/.claude/projects/-root/memory/` → CLAUDE.md / skills / agents / hooks.

Evolution data lives in `~/.claude/evolution/`. **Compound is BLOCKING** — the stop hook prevents session end without capturing learnings. Anti-patterns reference: `~/.claude/docs/on-demand/anti-patterns-full.md`.
