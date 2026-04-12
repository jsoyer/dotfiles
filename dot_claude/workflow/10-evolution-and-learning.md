# Evolution & Learning

## Why Evolution Exists

Without cross-project learning, each project starts from scratch. The same mistakes are repeated, the same workarounds are rediscovered, and model assignments are never optimized. The evolution system makes the workflow **get better over time across all projects**.

```
┌─────────────────────────────────────────────────────────────────┐
│                    EVOLUTION DATA FLOW                          │
│                                                                 │
│  Project A                    Project B                         │
│  ┌──────────┐                 ┌──────────┐                      │
│  │ Session  │                 │ Session  │                      │
│  │ learnings│                 │ learnings│                      │
│  └────┬─────┘                 └────┬─────┘                      │
│       │                            │                            │
│       ▼                            ▼                            │
│  ┌─────────────────────────────────────────┐                    │
│  │      ~/.claude/evolution/               │                    │
│  │                                         │                    │
│  │  error-registry.json                    │ ◄── Error patterns │
│  │  model-performance.json                 │ ◄── Model metrics  │
│  │  workflow-changelog.md                  │ ◄── System changes │
│  │  session-postmortems/                   │ ◄── Session data   │
│  └────────────┬────────────────────────────┘                    │
│               │                                                 │
│               ▼                                                 │
│  ┌─────────────────────────┐                                    │
│  │  /workflow-audit        │ ◄── Monthly analysis               │
│  │  (analyzes all data)    │                                    │
│  └────────────┬────────────┘                                    │
│               │                                                 │
│               ▼                                                 │
│  System improvements:                                           │
│  - Model upgrades/downgrades                                    │
│  - New hooks for recurring errors                               │
│  - Updated CLAUDE.md rules                                      │
│  - Skill/agent improvements                                     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Error Registry (error-registry.json)

A JSON database mapping error patterns to root causes, fixes, and projects where they occurred:

```json
{
  "pattern": "error message or symptom regex",
  "category": "ENV|LOGIC|CONFIG|DEPENDENCY|SECURITY|TEST|DEPLOY|PROOT|MERGE|PERFORMANCE",
  "root_cause": "why it happens",
  "fix": "how to fix it",
  "auto_preventable": false,
  "prevention": "hook/rule that prevents it",
  "approaches_that_failed": [
    { "approach": "what was tried", "why_bad": "why it didn't work" }
  ],
  "projects_seen": ["project-a", "project-b"],
  "occurrences": 3
}
```

The `approaches_that_failed` field is **negative learning** — recording what NOT to do is as valuable as recording what to do. When the same error appears in a future project, the agent knows both the fix AND which approaches to avoid.

### Error Categories

| Category | Examples |
|---|---|
| `ENV` | Missing env var, wrong Node version, proot limitation |
| `LOGIC` | Wrong algorithm, off-by-one, race condition |
| `CONFIG` | Bad setting, wrong flag, missing config file |
| `DEPENDENCY` | Version mismatch, missing package, native module failure |
| `SECURITY` | Auth bypass, data leak, XSS vulnerability |
| `TEST` | Flaky test, wrong assertion, missing coverage |
| `DEPLOY` | Failed deploy, wrong environment, broken pipeline |
| `PROOT` | ARM64 limitation, broken symlink, memory issue |
| `MERGE` | Conflict resolution error, file boundary violation |
| `PERFORMANCE` | Slow query, large bundle, memory leak |

## Model Performance (model-performance.json)

Tracks success rates per model per task type, enabling data-driven model selection:

```json
{
  "sonnet": {
    "implementation": { "attempts": 25, "first_try_success": 20, "required_upgrade": 2 },
    "bug_fix": { "attempts": 12, "first_try_success": 7, "required_upgrade": 3 }
  }
}
```

### Adaptation Rules (minimum 10 data points)

- Success rate **< 70%** → propose upgrade (e.g., sonnet → opus)
- Success rate **> 90%** → propose downgrade (e.g., sonnet → haiku, save cost)
- Changes require user approval
- Logged in workflow-changelog.md

### Current Model Assignment Matrix

| Task Type | Model |
|---|---|
| File scanning, discovery | haiku |
| Simple fixes (lint, typos, CSS) | haiku |
| Session learnings compilation | haiku |
| Standard implementation | sonnet |
| Bug fix implementation | sonnet |
| Test writing | sonnet |
| Verification & regression scan | sonnet |
| Sprint orchestration | opus |
| Complex multi-file refactoring | opus |
| Architectural decisions | opus |
| Merge conflicts (>3 files) | opus |

## Workflow Changelog (workflow-changelog.md)

Every system change is logged with date, what changed, why, and the source:

```markdown
## 2026-03-14
- **Changed:** Added rate limiting check to OAuth callback
  - **Why:** Code reviewer flagged potential abuse vector
  - **Source:** Sprint 03-route-protection code review
```

This provides:
- **Provenance:** Why was this rule added?
- **Regression tracking:** Was a change reverted?
- **Velocity monitoring:** Is the system learning (changes happening) or stagnating?

## Session Postmortems

Structured post-session analysis stored in `evolution/session-postmortems/`:

```markdown
# Session Postmortem: 2026-03-14 OAuth Implementation

## Metrics
- Total retries: 4
- Phases that caught bugs: [Phase 5.3 route health, Phase 5.5 plan audit]
- Model performance: sonnet 8/10 first-try success

## What Worked
- File boundaries prevented parallel sprint conflicts
- Inter-batch learning caught a pattern from Sprint 1

## What Didn't
- Rate limiting concern was caught late (code review, not planning)

## System Improvements Made
- Added rate limiting to correctness discovery checklist
```

## Session Learnings

Session learnings are a file-based memory that survives `/compact` (context compression). They use structured categories:

```markdown
## Errors
- [ENV] Missing NEXT_PUBLIC_API_URL → added to .env.example
- [LOGIC] Off-by-one in pagination → fixed with Math.ceil

## Rules Generated
- Always check .env.example when adding new env vars (category: CONFIG)

## Model Performance
- sonnet: 8/10 tasks first-try success

## Metrics
- Total retries: 4
- Phases that caught bugs: [Gate 3, Gate 5]
```

### Promotion Path

```
session-learnings (ephemeral — this session)
    │
    ▼  Pattern in 2+ tasks
docs/solutions/ (project knowledge)
    │
    ▼  Appears in 2+ projects
~/.claude/evolution/ (cross-project)
    │
    ▼  Proven effective
CLAUDE.md / hooks / skills (system-level)
```

## The Compound Step

The compound step is what transforms experience into system improvement:

1. **Capture:** What worked? What didn't? Reusable insight?
2. **Document:** Create solution doc if reusable. Update session learnings.
3. **Update the system:** If a rule/pattern needs changing, do it now.
4. **Verify:** "Would the system catch this automatically next time?" If no, compound is incomplete.
5. **Capture user corrections** as error-registry entries and model-performance data.

The Three Compound Questions:
1. "What was the hardest decision made here?"
2. "What alternatives were rejected, and why?"
3. "What are we least confident about?"

---

Next: [Verification & Quality](11-verification-and-quality.md)
