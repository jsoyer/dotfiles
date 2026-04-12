# Design Principles

Ten recurring principles guide the entire system. Understanding them helps you extend the system correctly and diagnose problems when they occur.

## 1. Match Ceremony to Complexity

The amount of process should be proportional to the risk. Quick Fix for trivialities, Standard for moderate work, PRD+Sprint for complex features.

Using a full PRD for a CSS fix is bureaucracy. Using Quick Fix for a payment system is reckless.

## 2. Deterministic Enforcement Over Hopeful Suggestions

Hooks > instructions. Code that prevents > text that asks.

CLAUDE.md says "use pnpm not npm." The model might forget. But `block-dangerous.sh` physically blocks npm commands — the model cannot bypass it. For rules that must never be broken, use hooks. For guidelines, use CLAUDE.md.

## 3. Separate Concerns, Minimize Privilege

Each agent has only what it needs:
- **Reviewer** doesn't edit (reports, doesn't fix)
- **Executor** doesn't delegate (implements, doesn't manage)
- **Orchestrator** doesn't implement (manages, doesn't code)

This prevents role confusion and limits blast radius when something goes wrong.

## 4. Fresh Context Is Better Than Stale Context

Starting clean > dragging a long conversation. Save state to files, not to conversation history.

This is why:
- One orchestrator invocation = one batch
- Sprint agents get only their sprint spec
- Session learnings are file-based (survive context compression)
- Each major skill works best in a fresh context window

## 5. Knowledge Compounds — Capture It

Every task must improve the system. If an error happens twice, it must become a rule that prevents the third time.

The compound step is not optional — it's blocking. Without it, you have "engineering with AI assistance." With it, you have a system that gets better with every use.

## 6. Plan + Review = 80%, Work + Compound = 20%

The bottleneck is not implementation — it's knowing what to implement and verifying the result.

With AI agents, typing speed is irrelevant. What matters is:
- Understanding the requirement correctly (Plan)
- Verifying the output is correct (Review)
- Implementation and learning capture are the smaller portion

## 7. Scope Discipline

Stay in scope. Log adjacent problems instead of solving them. "Just one more thing" is the enemy of delivery.

If you find a bug in another area, log it. If you see code that could be improved, log it. Don't fix it now. Scope creep is how sprints go from 30 minutes to 3 hours.

## 8. Binary Verifiability

If you can't write a pass/fail test for a criterion, it's not a valid criterion.

"Make it fast" is not verifiable. "LCP < 2s" is. "Make it user-friendly" is not verifiable. "Core task in < 3 clicks" is.

## 9. Evidence Over Claims

"Tests pass" is not evidence. "Route /login returns 200 and response body contains login form with Google button" is evidence.

This principle drives:
- Content verification (not just HTTP 200)
- Mandatory completion checklist (cite specific evidence)
- Verification Integrity rules (never claim PASS without running the command)

## 10. The System Improves Itself

This is the meta-principle. The error-registry grows. Model assignments adapt. Hooks get added. Skills get refined. Each session leaves the system better than it found it.

Without this, you have a static set of tools. With this, you have a living system that evolves to match your needs.

---

Next: [Glossary](15-glossary.md)
