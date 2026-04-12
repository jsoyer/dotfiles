# Workflow & Modes

## The Three Execution Modes

The system defines three modes, and the golden rule is: **switch modes freely within a single task**.

```
┌──────────────────────────────────────────────────────────┐
│                    EXECUTION MODES                       │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  QUICK FIX                                               │
│  When: Single file, <30 lines, no architectural impact   │
│  Process: Fix directly, run tests, micro-compound        │
│  Spec: Intent Doc (4 lines)                              │
│  ┌──────────────────────────────────────────────────┐    │
│  │ Task → Fix → Test → "Would the system catch      │    │
│  │                      this next time?"             │    │
│  └──────────────────────────────────────────────────┘    │
│                                                          │
│  STANDARD                                                │
│  When: Multi-file, clear scope, moderate complexity      │
│  Process: Contract-First → 2 Correctness Questions       │
│           → Minimal PRD → Implement → Verify → Compound  │
│  ┌──────────────────────────────────────────────────┐    │
│  │ Intent → Mirror → Receipt → PRD → Build → Test   │    │
│  │ → Compound                                        │    │
│  └──────────────────────────────────────────────────┘    │
│                                                          │
│  PRD + SPRINT                                            │
│  When: Large feature, multi-component, >1h agent work    │
│  Process: Contract-First → 6 Correctness Questions       │
│           → Full PRD → Sprint Decomposition → Compound   │
│  ┌──────────────────────────────────────────────────┐    │
│  │ Intent → Mirror → Receipt → Full PRD             │    │
│  │ → Sprint 1 → Sprint 2 → ... → Sprint N          │    │
│  │ → Verify → Compound                              │    │
│  └──────────────────────────────────────────────────┘    │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

Typical pattern within a large task: start in PRD+Sprint (plan), drop to Standard for normal sprints, drop to Quick Fix for trivial adjustments, return to Standard for the next piece.

**Why this matters:** Different tasks need different levels of ceremony. Using a full PRD for a CSS fix is bureaucracy. Using Quick Fix for a payment system is reckless. Mode fluency means matching the process to the complexity.

## Contract-First Pattern

Mandatory for Standard and PRD+Sprint modes. Before executing any multi-step task:

```
  Human                          Agent
    │                              │
    │  "I want feature X"          │
    ├─────────────────────────────►│
    │                              │  ┌─────────────────────┐
    │                              │  │ 1. INTENT           │
    │                              │  │    (user describes)  │
    │                              │  └─────────────────────┘
    │                              │
    │  "I understand you want:     │
    │   - Feature X                │
    │   - With constraint Y        │
    │   - Tradeoff: prefer Z"      │
    │◄─────────────────────────────┤
    │                              │  ┌─────────────────────┐
    │                              │  │ 2. MIRROR           │
    │                              │  │    (agent reflects)  │
    │                              │  └─────────────────────┘
    │                              │
    │  "Yes, but also add W"       │
    ├─────────────────────────────►│
    │                              │  ┌─────────────────────┐
    │                              │  │ 3. RECEIPT          │
    │                              │  │    (user confirms)   │
    │                              │  └─────────────────────┘
    │                              │
    │                              │  ┌─────────────────────┐
    │                              │  │ EXECUTION BEGINS    │
    │                              │  └─────────────────────┘
```

**Why this matters:** The biggest waste in AI engineering is not bad code — it's **building the wrong thing**. When an agent misinterprets a requirement and implements 500 lines in the wrong direction, all that work is thrown away. Contract-First prevents this by spending 2 minutes on alignment to save hours of rework.

## Correctness Discovery

Six questions must be answered before writing any PRD:

| # | Question | Purpose | Example |
|---|----------|---------|---------|
| 1 | **Audience:** Who uses this output? | Defines who you're building for | "End users on pricing page" |
| 2 | **Failure:** What makes it useless? | Defines the quality floor | "Showing outdated prices" |
| 3 | **Danger:** What makes it harmful? | Identifies risks beyond "useless" | "Showing prices lower than actual" |
| 4 | **Uncertainty:** What to do when uncertain? | Sets the safety level | Guess / Flag / Stop |
| 5 | **Risk:** What's worse — wrong answer or refusal? | Calibrates error tolerance | Security: block. UX: show something. |
| 6 | **Verification:** How to check correctness? | Forces completeness | "E2E test of complete login flow" |

In Standard mode, only questions 1 and 6 are asked. In PRD+Sprint mode, all 6 are mandatory.

## The Autonomous Pipeline

The preferred end-to-end workflow minimizes human touchpoints:

```
┌─────────┐    ┌──────────────────┐    ┌──────────────────────┐    ┌───────────┐
│  /plan   │───►│ User reviews PRD │───►│  /plan-build-test    │───►│ User tests│
│          │    │ and approves     │    │  (autonomous)        │    │ manually  │
└─────────┘    └──────────────────┘    └──────────────────────┘    └─────┬─────┘
                                                                         │
                ┌──────────────────────────────────────────────────────────┘
                │
                ▼
        ┌───────────────────┐    ┌──────────────────────┐    ┌──────────────┐
        │ /ship-test-ensure │───►│ MANDATORY: User       │───►│ Production   │
        │ (autonomous thru  │    │ confirms prod deploy  │    │ + Lighthouse │
        │  staging)         │    │ (non-negotiable gate) │    │ 100/100      │
        └───────────────────┘    └──────────────────────┘    └──────────────┘
```

**Design goal:** The user reviews the plan once, approves once, tests manually once, and confirms production deploy once. Everything else runs without interruption.

### Autonomous Checkpoints

| Checkpoint | Autonomous Action | Rationale |
|---|---|---|
| Execution plan | Auto-select "Run all autonomously" | PRD was already reviewed |
| Verification failures | Exhaust retry budget, then BLOCKED | User checks at end |
| Fresh context check | Auto-select "Continue here" | Advisory only |
| Deploy timeout (15min) | Wait 10 more minutes, then BLOCKED | Safe default |
| **Production deploy** | **ALWAYS ask user** | **Non-negotiable safety gate** |
| Lighthouse plateau | Accept current scores after max iterations | Performance, not correctness |
| **Rollback decision** | **ALWAYS ask user** | **Destructive action needs human judgment** |

## Skill Selection Decision Tree

```
"What do I need to do?"
│
├─ "Just plan, don't build yet"
│   └─ /plan
│
├─ "Build a feature / fix a bug / implement something"
│   ├─ Single file, < 30 lines, obvious fix?
│   │   └─ Quick Fix (no skill needed)
│   └─ Anything larger
│       └─ /plan-build-test
│
├─ "Ship what I've built to production"
│   └─ /ship-test-ensure
│
├─ "Full autonomous pipeline"
│   └─ /plan → review PRD → /plan-build-test → manual test → /ship-test-ensure
│
├─ "Wrap up / capture what I learned"
│   └─ /compound
│
├─ "I have pending task files from a previous session"
│   └─ /plan-build-test (Phase 0 detects and resumes)
│
└─ "Audit how the workflow is performing"
    └─ /workflow-audit
```

## Knowledge Promotion Chain

Knowledge flows upward in an ascending chain:

### Per-Project Promotion

```
session-learnings (ephemeral — lives during session)
    │
    ▼  Pattern proves useful in 2+ tasks
docs/solutions/ (project knowledge — persistent)
    │
    ▼  Affects architecture
ADRs (Architecture Decision Records — formal & durable)
    │
    ▼  Improves the workflow itself
CLAUDE.md updates (system-level changes)
```

### Cross-Project Promotion

```
session-learnings
    │
    ▼  Error occurs
~/.claude/evolution/error-registry.json (cross-project error patterns)
    │
    ▼  Model performance recorded
~/.claude/evolution/model-performance.json (success rate tracking)
    │
    ▼  Pattern confirmed in 2+ projects
~/.claude/projects/-root/memory/ (cross-project memory)
    │
    ▼  System file updated
~/.claude/evolution/workflow-changelog.md (evolution history)
```

The analogy is the immune system: an infection (bug) is fought locally (session-learnings), but if the same type appears repeatedly, the body develops permanent antibodies (CLAUDE.md update or hook).

---

Next: [Sprint System](06-sprint-system.md)
