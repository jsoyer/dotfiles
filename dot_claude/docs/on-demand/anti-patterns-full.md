# Anti-Patterns: Full Reference

Expanded version of the quick reference in CLAUDE.md. Each anti-pattern includes description, real examples, detection signals, and fixes.

---

## Specification Anti-Patterns

### 1. Kitchen Sink

**What:** Everything crammed into one massive spec. 50+ acceptance criteria. Touches every part of the system.
**Signal:** PRD is >3 pages. Sprint decomposition has >8 sprints. Multiple unrelated features bundled.
**Fix:** Split into independent PRDs. Each PRD should have one clear "What & Why." If you can't state the goal in one sentence, it's too big.
**Example:** "Redesign the dashboard AND add billing AND migrate the database" → Three separate PRDs.

### 2. Aspirational

**What:** Requirements stated as wishes, not behaviors. "Make it better." "Improve performance." "Clean up."
**Signal:** No numbers, no metrics, no definition of done. Can't write a test for it.
**Fix:** Apply the Vague Requirements Translator (see `~/.claude/docs/vague-requirements-translator.md`). Every requirement must have a binary pass/fail test.
**Example:** "Make the page faster" → "Reduce LCP from 3.2s to under 2.0s on mobile (Lighthouse)."

### 3. Solution Spec

**What:** Prescribing HOW to implement instead of WHAT to achieve. Over-specifies implementation details.
**Signal:** PRD mentions specific functions, variable names, or implementation steps rather than outcomes.
**Fix:** Separate functional requirements (what) from technical constraints (how). The "what" goes in acceptance criteria; the "how" goes in technical constraints (and only when there's a genuine reason to constrain implementation).
**Example:** "Use a React context with useReducer to manage state" → "Form state persists across page navigation within the wizard flow."

### 4. Assumption

**What:** References tacit knowledge without providing it. "Follow our patterns." "Use the standard approach."
**Signal:** PRD references conventions, patterns, or standards without linking to them or describing them.
**Fix:** Every reference must include the actual content or a link to it. If the pattern isn't documented, document it first (in `docs/solutions/`).
**Example:** "Follow our auth pattern" → "Follow the auth pattern documented in `docs/solutions/patterns/auth-flow.md` (specifically: JWT in httpOnly cookie, refresh via /api/auth/refresh)."

### 5. No-Boundary

**What:** Goals without non-goals. Scope without limits. Everything is in scope.
**Signal:** Non-goals section is empty or says "N/A." No mention of what the task will NOT do.
**Fix:** Non-goals must be at least as detailed as goals. For every goal, there's a natural boundary — state it. Include: files not to touch, features not to add, refactors not to do.
**Example:** "Add user settings page" without non-goals → Add: "Will NOT include: notification preferences (separate PRD), profile picture upload (Phase 2), admin settings (different role)."

---

## Workflow Anti-Patterns

### 6. Mode Rigidity

**What:** Always using the same mode regardless of task complexity. Full PRD for a one-liner. Quick Fix for a multi-component feature.
**Signal:** Every task gets the same treatment. No mode switching within tasks.
**Fix:** Classify before starting. Switch modes freely during execution. A PRD task might have Quick Fix sub-tasks.

### 7. Review Complacency

**What:** Less rigorous review as volume increases. First sprint gets careful review; sprint 5 gets rubber-stamped.
**Signal:** Code review findings decrease as project progresses (unlikely if quality is constant). Tests become less thorough.
**Fix:** Review rigor scales with risk, not inverse with volume. High-risk areas (auth, data, billing) always get full review regardless of how many sprints came before.

### 8. False Sense of Control

**What:** Believing templates and checklists guarantee quality. Filling in the template without thinking about the content.
**Signal:** PRD sections are filled with boilerplate. Acceptance criteria are vague. Verification steps are "run tests."
**Fix:** Templates are prompts for thought, not forms to fill. The Spec Self-Evaluator catches this — if it scores <11, the spec needs real work, not more words.

### 9. Spec-as-Bureaucracy

**What:** Full PRD ceremony for a trivial task. 30 minutes of planning for a 2-minute fix.
**Signal:** Task classification doesn't match effort. Quick Fix tasks have full PRDs. Session-learnings entries for obvious fixes.
**Fix:** Match ceremony to complexity. Quick Fix = Intent Doc (4 lines). Standard = Minimal PRD. Only PRD+Sprint for genuinely large tasks.

### 10. No Feedback Loops

**What:** Not tracking what goes wrong. Same mistakes repeated across sessions. No learning from failures.
**Signal:** Session-learnings file doesn't exist or isn't updated. No solution docs created. Same errors appear in multiple tasks.
**Fix:** The Compound step is mandatory for exactly this reason. Every task produces learnings. Repeated patterns get promoted to solutions. Solutions get promoted to rules.
