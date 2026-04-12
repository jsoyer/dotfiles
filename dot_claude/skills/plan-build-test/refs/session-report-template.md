## Build Complete

### Work Summary
- Task files processed: N
- Total items completed: M
- Items failed/skipped: X
- Parallel batches executed: B

### Parallelism Report
- Tasks run in parallel: N (across B batches via worktrees)
- Tasks run sequentially: M
- Merge conflicts encountered: X (resolved: Y)

### Model Usage
- haiku: N tasks (first-try success: X/N)
- sonnet: M tasks (first-try success: X/M)
- opus: X tasks (first-try success: X/X)

### Error Categories
- [CATEGORY]: N occurrences → [brief summary]

### Metrics
- Total retries: N
- Verification gates that caught bugs: [list]
- Phase 5 duration: Ns
- Retry budget by category: transient=N, logic=N, environment=N, config=N

### Files Modified
- `path/to/file.ts` (+N/-M lines)

### Verification Results (Phase 5 — Live Verification)
- Build: PASS/FAIL (exit code)
- Lint: PASS/FAIL (file count, issue count)
- Types: PASS/FAIL (exit code)
- Tests: PASS/FAIL (N passing, M failing)
- Dev Server: PASS/FAIL (port, startup method)
- Content Verification: PASS/FAIL (routes checked, content found)
- Route Health: PASS/FAIL (N/M routes returning 200)
- Playwright E2E: PASS/FAIL (N tests, M screenshots, X console errors)
- Regression Scan: PASS/FAIL

### Evolution Updates
- Error registry entries added/updated: N
- Model performance data points recorded: N
- Session postmortem written: yes/no

### Task Files
- `path/to/task/spec.md` — COMPLETED (via progress.json)

### Next Step
Run `/ship-test-ensure` when ready to deploy.
