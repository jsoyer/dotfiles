# Verification & Quality

## The 6 Verification Gates

Every agent must pass these blocking verification gates. A gate is NEVER skipped or silently marked as passed.

### Gate Application by Agent

```
Sprint-Executor:
  Gate 1 (Static Analysis) → Gate 5 (Plan Completeness Audit)

Orchestrator:
  Gate 1 (Coherence) → Gate 2 (Dev Server) → Gate 3 (Content) → Gate 5 (Plan Audit)

Plan-Build-Test Phase 5:
  Gate 1 → Gate 2 → Gate 3 → Gate 4 (Routes) → Gate 6 (E2E) → Gate 5 (Plan Audit)
```

### Gate Details

| Gate | What It Catches | What It Does NOT Catch |
|---|---|---|
| **1. Static Analysis** (build, lint, types, tests) | Syntax errors, type mismatches, test regressions | Runtime failures, rendering bugs |
| **2. Dev Server Startup** | Missing deps, config errors, port conflicts | Routes that 200 but show error content |
| **3. Content Verification** | 200 responses with error pages, empty renders, stale cache | N/A — ultimate check |
| **4. Route Health** | Missing pages, broken dynamic routes, locale errors | Content correctness (Gate 3 handles that) |
| **5. Plan Completeness Audit** | Partial completion claimed as full, forgotten tasks | N/A — final check |
| **6. E2E / Playwright** | Visual bugs, console errors, navigation failures | N/A — full user flow testing |

**Why sprint-executors skip Gates 2 and 3:** Sprint-executors work in isolated worktrees. Running a dev server per worktree would be redundant. The orchestrator runs Gates 2 and 3 after merging all sprints — testing the integrated code.

### Anti-Patterns (things that look like verification but aren't)

| Looks Like Verification | Why It's Not | Do This Instead |
|---|---|---|
| "All 128 tests pass" | Tests can pass while app is broken | Start dev server, curl routes, check content |
| "Build succeeded" | Build does not equal runtime correctness | Verify routes serve correct content |
| "HTTP 200 on all routes" | 200 can contain error pages | Check response body for expected content |
| "Dev server starts" | Starting ≠ serving correct content | Curl routes and inspect response bodies |

## Anti-Goodhart Verification

**Goodhart's Law:** "When a measure becomes a target, it ceases to be a good measure."

In AI testing: if you tell the agent "make all tests pass," it can make tests pass without verifying real behavior — weak assertions, removed checks, or tests that validate output without checking if it's correct.

Before marking any task complete, verify:

1. Do tests validate actual **BEHAVIOR** or just **OUTPUT**?
2. Did I add a test just to "make it pass" without verifying the real scenario?
3. Does E2E test the **USER flow** or just the **DEVELOPER flow**?
4. Are there scenarios the tests don't cover that acceptance criteria imply?
5. Could functional tests pass while security-relevant behaviors are missing?

**Why this matters:** "Vibe testing" — when AI-generated tests technically pass, inflate coverage metrics, and give false confidence — is one of the most dangerous failure modes of AI-assisted development.

## Anti-Premature Completion Protocol

This protocol exists because of repeated incidents where tasks were declared "complete" while the actual running application was broken.

### The Three Completion Lies (never do these)

1. **"All tests pass"** — Tests passing does NOT mean the feature works. Tests can pass while the app shows a visible bug, the dev server cache is corrupted, or runtime dependencies are missing.

2. **"Build complete"** — A build completing does NOT mean the app runs. You MUST start the dev server and verify actual routes return correct content.

3. **"All items done"** — Claiming completion without re-reading the original plan. Before declaring done: re-read the plan, enumerate every item, cite specific evidence for each.

### Mandatory Completion Checklist

Before saying "done":

```
1. Re-read the original plan/spec       (not from memory — actually read it)
2. Enumerate remaining items             (list every unchecked - [ ])
3. Cite evidence for each criterion      ("criterion X verified by [command]
                                           which returned [output]")
4. Start the dev server                  (verify key routes serve correct content)
5. If ANY item is incomplete             (complete it or report it — NEVER claim
                                           completion with unfinished items)
```

### When to STOP and Report Instead of Claiming Done

- Dev server won't start → **BLOCKED**, not "complete with known issue"
- Tests pass but you haven't visually verified → **NOT DONE**
- You checked off tasks but didn't re-read the plan → **NOT DONE**
- You can't cite specific evidence for a criterion → **NOT MET**

## Verification Integrity Rules

- NEVER claim a command "passed" without running it and seeing the output
- NEVER write "lint: PASS (0 issues)" without a preceding lint command execution
- NEVER mark E2E as "PASS" without a preceding E2E command execution
- If blocked (environment limitation, missing tool): mark as `BLOCKED`, never as `PASS`
- Session learnings verification sections must include actual exit codes

## Adaptive Retry Budget

Different failure types get different retry allowances:

| Failure Type | Max Retries | Rationale |
|---|---|---|
| `transient` (network, timeout, flaky test) | 5 | Usually resolves itself |
| `logic` (wrong approach, broken implementation) | 2, then different approach | Repeating bad approach wastes time |
| `environment` (proot limitation, missing binary) | 1, then mark BLOCKED | Can't fix the environment |
| `config` (bad setting, wrong flag) | 3 | Usually trial-and-error solvable |

## Scope Boundary Enforcement

If during implementation you discover:

- **Related bug in different area** — log in PRD under "Issues Found", do NOT fix
- **Opportunity to improve unrelated code** — log it, do NOT do it
- **Already-broken test** — log it, do NOT fix (unless in sprint scope)

Stay in scope. Resist "one more thing."

---

Next: [proot-distro Guide](12-proot-distro-guide.md)
