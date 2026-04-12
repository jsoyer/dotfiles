# End-of-Task Browser Verification Protocol

Extension of the Anti-Premature Completion Protocol. Load this document when verifying any task that touched UI, API routes, or server-side code.

## When This Applies

- Frontend components, pages, or styles modified
- API routes created/modified (REST, GraphQL, tRPC, Next.js API handlers, server actions)
- Server-side logic (Next.js middleware, SSR, streaming, RSC)
- Database queries that flow to the UI
- Config changes that affect runtime behavior (next.config, middleware config, env vars)

## When This Does NOT Apply

- Pure documentation changes
- Test-only changes (but still run the tests)
- Standalone scripts with no UI/API surface
- Build tool/lint config that does not affect runtime output

## The Protocol

1. **Start the dev server** — use the project-specific command from the project's CLAUDE.md `## Execution Config` (typically `pnpm dev`). Wait until the server reports ready. Keep the server log visible — you will check it.

2. **Open Playwright** — Use `mcp__plugin_playwright_playwright__browser_navigate` to the first affected route. Playwright MCP interaction stays in the main agent, never delegated to a subagent.

3. **Take a screenshot** — `browser_take_screenshot` saved under `.artifacts/playwright/screenshots/YYYY-MM-DD_HHmm/<route>_<step>.png`.

4. **Check the browser console** — Call `browser_console_messages`. Classify every message:
   - **ERROR** → MUST fix. App is broken or about to break.
   - **WARN** → MUST fix unless genuinely third-party and unavoidable (document the exception in session-learnings).
   - **LOG / DEBUG / INFO** → Remove stray `console.log` / `console.debug` statements introduced by this task. Production code does not ship debug output.

5. **Check the server console** — Read the dev server output. Look for:
   - Compilation errors or warnings
   - Runtime exceptions, unhandled rejections, module-not-found
   - Hydration mismatches, React key warnings, invalid hook calls, effect cleanup warnings
   - API route 500s, ORM errors, server action failures
   - Middleware errors, edge runtime warnings

6. **Navigate every affected route** — Repeat steps 3-5 for each. Include at least one end-to-end user flow (click, submit, navigate) that exercises the feature.

7. **Fix every error found** — After any fix, loop back to step 1 (some changes require a dev server restart). Do NOT mark the task complete until both consoles are clean.

8. **Save final artifacts** — Final screenshots go to `.artifacts/playwright/screenshots/YYYY-MM-DD_HHmm/` with descriptive filenames (`<route>_final.png`). These serve as evidence for the Stop hook's completion check.

## Failure Modes (STOP and report, do not paper over)

- Dev server won't start → BLOCKED. Investigate the server log, do not claim completion.
- Playwright can't navigate (route 404/500) → routing is broken. Fix before continuing.
- Same errors keep reappearing after fixes → ROLLBACK per the Rollback & Recovery Protocol.
- Console has errors from code you didn't touch → investigate. If pre-existing, log in session-learnings and escalate to user. Do not suppress errors just to make your task look clean.

## Completion Evidence Required

- At least one screenshot in `.artifacts/playwright/screenshots/` from the current session
- A statement naming each route verified and confirming both consoles were clean
