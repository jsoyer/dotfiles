# The Constitution — CLAUDE.md

The `CLAUDE.md` is the most important file in the repository. It is loaded automatically at the start of every session and functions as the "operating system" of the agent. This document explains its key sections.

## Value Hierarchy

When two values conflict, which one wins? The system defines a clear priority:

```
Priority 1 ★★★★★  Security & Privacy
                   Auth integrity, data masking, secrets management — non-negotiable

Priority 2 ★★★★☆  Functional Correctness
                   Code that works correctly > code that looks elegant

Priority 3 ★★★☆☆  Robustness
                   For core components: defensive coding, error handling, validation

Priority 4 ★★☆☆☆  Iteration Speed
                   For UI, prototypes, non-core features: ship fast, iterate later

Priority 5 ★☆☆☆☆  Performance
                   Optimize only when measured data shows a bottleneck
```

**Why this matters:** AI agents frequently need to make decisions where two values conflict. "Should I add extra validation on this endpoint (robustness) or ship quickly (speed)?" If it's a payment endpoint, robustness wins (priority 3 > 4). If it's a UI prototype, speed wins (priority 4 > 5). Without this explicit hierarchy, the agent would make arbitrary choices.

## Autonomous Decision Authority

The system divides decisions into three categories:

| Agent CAN Decide Alone | Agent MUST Ask User | Agent NEVER Does |
|---|---|---|
| Variable/function naming | Schema/API changes | Expose sensitive data in logs |
| Choice between equivalent approaches | New dependency outside existing stack | Delete passing tests |
| Implementation order within a phase | Architectural pattern change | Deploy to production |
| CSS/styling decisions | Remove existing functionality | Modify auth/permission config |
| Test structure and naming | Security/privacy tradeoffs | Bypass rate limiting or validation |
| Refactoring within a single file | Scope significantly larger than expected (>2x) | Silently swallow errors |

**Why this table matters:** It solves the fundamental dilemma of AI agents — autonomy vs. safety. If the agent asks about everything, it's slow and annoying. If it decides everything on its own, it can cause damage. This table defines the exact boundary.

The "NEVER" column exists because certain actions are **never justified at any confidence level**. Even if the agent is 99% sure deleting a test is correct, it doesn't have permission.

## Tradeoff Resolution by Deliverable

What to optimize depends on what is being built:

| Deliverable | Optimize For | Acceptable to Sacrifice |
|---|---|---|
| API endpoint | Security, validation, idempotency | Development speed |
| UI component | UX, responsiveness, accessibility | Marginal performance |
| Data pipeline | Correctness, observability | Code elegance |
| Documentation | Clarity, accuracy | Completeness |
| Prototype/POC | Speed, core functionality | Tests, edge cases |

This prevents the agent from applying the same rigor to everything. A prototype does not need 100% test coverage. A payment endpoint cannot skip validation.

## Escalation Logic

The agent MUST stop and ask when:

1. The task is ambiguous and there are 2+ reasonable interpretations
2. The proposed solution conflicts with an existing ADR or pattern
3. Actual scope is significantly larger than expected (>2x)
4. An unrelated bug is discovered during implementation
5. The decision falls in the "MUST ask" column
6. No relevant documentation exists for the area being modified
7. A dependency or external service behaves unexpectedly

When escalating, the agent uses a standardized format:

```
[DECISION NEEDED]
Context: [brief].
Option A: [X].
Option B: [Y].
My recommendation: [A/B], because [reason].
Proceed?
```

This format forces the agent to synthesize the context, show it already analyzed options, and give a recommendation — saving the human's time.

## Confidence Levels

| Level | Meaning | Action |
|---|---|---|
| HIGH | Clear pattern in docs/solutions, existing tests confirm | Proceed autonomously |
| MEDIUM | Inferred from code but no explicit docs | Proceed but document assumption |
| LOW | Multiple valid interpretations, no precedent | STOP and ask user |

## Risk Categories

| Area | Catastrophic (rollback immediately) | Tolerable (fix forward) |
|---|---|---|
| Auth/Security | Any bypass, data leak, permission escalation | Error message copy, UI polish |
| Data/API | Data loss, schema break, contract violation | Response format, non-critical field |
| UI | Crash, blank page, broken critical flow | Pixel imperfection, animation glitch |
| Tests | Deleting passing tests, making tests lie | Flaky new test, missing edge case |
| Infrastructure | Broken deploy, env leak, service outage | Config optimization, log level |

## Development Rules

### TDD for Features (mandatory order)

```
1. Write unit tests first → 2. Implement code → 3. Integration tests → 4. E2E tests → 5. Run ALL tests
```

### TDD for Bug Fixes (different order)

```
1. REPRODUCE → 2. INVESTIGATE → 3. FIX → 4. VERIFY → 5. REGRESS
   Write failing    Find root       Target    Confirm     Add regression
   test             cause           root      test now    tests
                                    cause     passes
```

### Rollback & Recovery

When a fix makes things worse, **stop layering fixes on top of broken fixes**:

1. **Revert** to last known working state
2. **Reassess** with fresh eyes
3. **Try a different approach** — if same approach failed twice, it's wrong
4. **Escalate to user** after 2+ distinct failed approaches

### Post-Implementation Checklist

- All tests passing
- No unused components, imports, or dead code
- No console.logs or debug code
- No duplicated code
- Descriptive variable/function names
- Security check
- Performance check

---

Next: [Workflow & Modes](05-workflow-and-modes.md)
