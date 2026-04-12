# Development & Git Workflow

## Feature Implementation

0. **Research & Reuse** _(mandatory before any new implementation)_
   - GitHub code search first (`gh search repos`, `gh search code`)
   - Library docs second (Context7 or primary vendor docs)
   - Check package registries (npm, PyPI, crates.io) before writing utility code
   - Prefer adopting a proven approach over writing net-new code

1. **Plan First**
   - Use **planner** agent for complex features
   - Identify dependencies and risks
   - Break down into phases

2. **TDD Approach**
   - Write tests first (RED) → Implement (GREEN) → Refactor (IMPROVE)
   - Verify 80%+ coverage

3. **Code Review**
   - Use **code-reviewer** agent immediately after writing code
   - Address CRITICAL and HIGH issues

4. **Commit & Push**

## Commit Message Format

```
<type>: <description>

<optional body>
```

Types: feat, fix, refactor, docs, test, chore, perf, ci

## Pull Request Workflow

1. Analyze full commit history (not just latest commit)
2. Use `git diff [base-branch]...HEAD` to see all changes
3. Draft comprehensive PR summary
4. Include test plan with TODOs
5. Push with `-u` flag if new branch
