# End-to-End Example

This walkthrough shows the complete system in action for a real scenario: adding Google OAuth authentication to a Next.js app.

## The Request

```
YOU: "I need to implement login with Google OAuth in my Next.js app"
```

## Phase 1: Planning (/plan auto-invokes)

```
┌─────────────────────────────────────────────────────────────────────────┐
│ 1. Classifies as PRD+Sprint (multi-component, >1h work)                │
│                                                                         │
│ 2. Contract-First:                                                      │
│    "I understand you want: login via Google OAuth using NextAuth.js,    │
│     redirecting to /dashboard after login. Correct?"                    │
│                                                                         │
│ 3. Correctness Discovery (all 6 questions):                             │
│    Audience: End users                                                  │
│    Failure: Login that doesn't persist                                  │
│    Danger: Token leak                                                   │
│    Uncertainty: STOP (it's security)                                    │
│    Risk: Unauthorized access > refused login                            │
│    Verification: E2E test of complete login flow                        │
│                                                                         │
│ 4. PRD created at docs/tasks/auth/feature/2026-03-14_1400-oauth/       │
│    ├── spec.md (the PRD)                                                │
│    ├── progress.json                                                    │
│    └── sprints/                                                         │
│        ├── 01-setup-nextauth.md (Sprint 1)                              │
│        ├── 02-login-ui.md (Sprint 2 — parallel with 3)                  │
│        └── 03-route-protection.md (Sprint 3 — parallel with 2)          │
│                                                                         │
│ 5. Spec Self-Evaluator: 12/14, approved                                 │
│                                                                         │
│ 6. "PRD saved. Run /plan-build-test to execute."                        │
└─────────────────────────────────────────────────────────────────────────┘
```

The user reviews the PRD, confirms it's correct, and proceeds.

## Phase 2: Execution (/plan-build-test — autonomous)

```
YOU: "/plan-build-test"

┌─────────────────────────────────────────────────────────────────────────┐
│ Phase 0: Finds progress.json with 3 pending sprints                     │
│                                                                         │
│ Phase 3: Execution begins                                               │
│                                                                         │
│   Batch 1: Sprint 1 (sequential — dependency for 2 and 3)              │
│   ┌─────────────────────────────────────────────────────────┐           │
│   │ Orchestrator spawns sprint-executor in worktree          │           │
│   │ → Executor implements NextAuth setup with TDD            │           │
│   │ → Marks checkboxes, fills Agent Notes                    │           │
│   │ → Returns: PASS (build, lint, types, tests)              │           │
│   │ → Orchestrator verifies coherence, runs dev server       │           │
│   │ → Content verified: NextAuth API routes responding       │           │
│   └─────────────────────────────────────────────────────────┘           │
│                                                                         │
│   Batch 2: Sprints 2 + 3 (parallel — different files)                  │
│   ┌──────────────────────┐  ┌──────────────────────────┐               │
│   │ Sprint 2 (worktree)  │  │ Sprint 3 (worktree)      │               │
│   │ Login UI components  │  │ Route protection          │               │
│   │ (own branch)         │  │ middleware (own branch)   │               │
│   └──────────┬───────────┘  └────────────┬─────────────┘               │
│              │                            │                             │
│              ▼                            ▼                             │
│   Orchestrator merges both (sequential, lowest sprint first)            │
│   → No conflicts (different files)                                      │
│   → Code reviewer: PASS, 1 finding: "consider rate limiting callback"  │
│   → Dev server: content verified on all auth routes                     │
│                                                                         │
│ Phase 5: Live Verification                                              │
│   Build: PASS | Lint: PASS | Types: PASS | Tests: 15/15 PASS           │
│   Dev server: PASS (port 3000)                                          │
│   Content: /login shows login form, /dashboard requires auth            │
│   Route health: 12/12 routes returning 200                              │
│   Plan completeness: 3/3 sprints complete, all criteria met             │
│                                                                         │
│ Phase 6: Learning captured, error-registry updated                      │
└─────────────────────────────────────────────────────────────────────────┘
```

The user manually tests the feature — everything works.

## Phase 3: Shipping (/ship-test-ensure — autonomous through staging)

```
YOU: "/ship-test-ensure"

┌─────────────────────────────────────────────────────────────────────────┐
│ Phase 1: Create branch ship/20260314-1430-google-oauth                  │
│          Commit, push, create PR, wait for CI, merge                    │
│                                                                         │
│ Phase 2: Monitor staging deploy on GitHub Actions                       │
│          All workflows green                                            │
│                                                                         │
│ Phase 3: E2E on staging: 8/8 tests pass                                 │
│                                                                         │
│ Phase 4: ★ "Staging verified. Deploy to production?" ★                  │
│          YOU: "Deploy all"                                               │
│          Production deploy triggered, monitored, green                  │
│                                                                         │
│ Phase 5: Lighthouse on production                                       │
│          Performance: 100 | A11y: 100 | Best Practices: 100 | SEO: 100│
│                                                                         │
│ Phase 6: Final report + compound                                        │
│          Hardest decision: Rate limiting on OAuth callback               │
│          Rejected: Manual OAuth (NextAuth more secure)                   │
│          Least confident: Rate limit threshold                           │
│          → NextAuth pattern promoted to docs/solutions/auth/             │
└─────────────────────────────────────────────────────────────────────────┘
```

## What Happened Behind the Scenes

1. **Contract-First** prevented misunderstanding the requirement
2. **Correctness Discovery** identified security as the uncertainty policy (STOP, don't guess)
3. **File boundaries** in sprint specs enabled Sprint 2 and Sprint 3 to run in parallel
4. **Worktree isolation** gave each sprint its own branch and directory
5. **Anti-Goodhart verification** ensured tests validated real OAuth behavior
6. **Content verification** (not just HTTP 200) confirmed the login form rendered
7. **Code review** caught a rate limiting concern that planning missed
8. **Inter-batch learning** would have passed Sprint 1 insights to Sprint 2/3 if there were errors
9. **Mandatory user confirmation** before production deploy
10. **Compound step** captured learnings and promoted the NextAuth pattern

## User Touchpoints

The user only needed to:

1. Describe the feature (1 message)
2. Confirm the Contract-First mirror (1 message)
3. Review the PRD (1 read)
4. Say "/plan-build-test" (1 message)
5. Test manually (hands-on)
6. Say "/ship-test-ensure" (1 message)
7. Confirm production deploy (1 message)

Everything else was autonomous — planning, sprint decomposition, parallel execution, merging, verification, CI/CD, staging E2E, and learning capture.

---

Next: [Design Principles](14-design-principles.md)
