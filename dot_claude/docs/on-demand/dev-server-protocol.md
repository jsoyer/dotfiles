# Dev Server Smoke Test & Fix Loop Protocol

**Canonical definition. Referenced by:** `orchestrator.md` Step 8, `plan-build-test/SKILL.md` Step 5.2.

---

## Why Polling (Not Sleep)

Compilation time varies widely by environment — especially in proot-distro ARM64 where cold
starts can take 30-90 seconds. A fixed sleep either wastes time or races ahead before the
server is ready. Polling the log file for a known "ready" signal is reliable across all
environments. See `~/.claude/docs/on-demand/proot-distro-environment.md` for proot-specific
timing and environment notes.

---

## The Protocol

### 1. Free Ports

Run the `kill` command from Execution Config to stop any running server processes and free
the target port before starting.

### 2. Start the Server

Launch the dev server command from Execution Config in the background, redirecting stdout
and stderr to a temp log file so you can poll it without blocking:

```bash
[dev command] > /tmp/dev-server.log 2>&1 &
DEV_SERVER_PID=$!
```

### 3. Poll for Readiness (max 60 seconds)

Check every 3 seconds for one of these signals in the log file:
- `"Ready"` (Next.js App Router)
- `"started server on"` (Next.js Pages Router, some versions)
- `"compiled"` (webpack/Turbopack build complete)
- `"Local:"` (Vite, many other servers)

```bash
TIMEOUT=60
ELAPSED=0
while [ $ELAPSED -lt $TIMEOUT ]; do
  if grep -qE "Ready|started server on|compiled|Local:" /tmp/dev-server.log 2>/dev/null; then
    echo "Dev server ready after ${ELAPSED}s"
    break
  fi
  if ! kill -0 $DEV_SERVER_PID 2>/dev/null; then
    echo "Dev server process exited — check /tmp/dev-server.log"
    break
  fi
  sleep 3
  ELAPSED=$((ELAPSED + 3))
done
```

If the process exits early, read the error output immediately — it contains the root cause.

If 60 seconds elapse with no ready signal, attempt a `curl` fallback before treating it
as a failure (some servers emit different ready messages than the ones above).

### 4. Verify Representative Routes

**HTTP 200 is necessary but NOT sufficient. Verify actual page content.**

For each of 3-5 representative routes (chose routes that exercise the feature just built):

```bash
curl -sL -o /tmp/route-body.html -w "%{http_code}" http://localhost:[PORT]/[ROUTE]
```

Then inspect `/tmp/route-body.html` and verify ALL of the following:
- Response is HTTP 200 (or 3xx redirect to a 200)
- Body contains expected text content (headings, labels, key data)
- Body contains expected HTML structure (key components, navigation)
- Body does NOT contain error strings: `"Internal Server Error"`, `"500"`, stack traces,
  `"undefined"`, `"null"`, empty `<body>` tags
- Body is not in a loading-spinner-only state (incomplete SSR/hydration)

If Playwright MCP is available in context: use `browser_navigate` + `browser_snapshot` to
capture the accessibility tree and verify rendered components match expectations. This is
richer than curl for catching hydration and client-side rendering failures.

### 5. Fix-Retry Cycle (max 3 cycles, different fix each time)

If the server fails to start or a route check fails:

1. **Diagnose** — read the full error output from the log file
2. **Identify root cause** (not the symptom):
   - Port conflict → kill the conflicting process, retry
   - Missing dependency → install it, retry
   - Config error → fix the config, retry
   - System call error (e.g., `os.networkInterfaces()` in proot) → wrap in try/catch, retry
   - Symlink / native module issue → try removing `--turbopack` flag, retry
   - Build output broken → run build first, then serve, retry
3. **Fix** the root cause (a real code or config change — not just a re-run)
4. **Retry** — restart from step 1 (free ports → start → poll → verify)

Each of the 3 cycles MUST attempt a DIFFERENT fix. Retrying the same fix does not count.

**Turbopack fallback (proot-distro):** If the standard dev command includes `--turbopack`
and the server fails with a symlink or native module error, remove `--turbopack` and retry.
Turbopack has known issues in some ARM64 proot environments.

### 6. Kill the Server

After smoke test completes (pass or BLOCKED), kill the dev server:

```bash
kill $DEV_SERVER_PID 2>/dev/null
# Also run the Execution Config kill command to catch any lingering processes:
[kill command from Execution Config]
```

### 7. BLOCKED Condition

If the server still fails after 3 distinct fix attempts:
- Mark the sprint/task as **BLOCKED** — do NOT mark it complete
- Log the full error output in session learnings with category `[PROOT|ENV|CONFIG|LOGIC]`
- Report to caller with: what was tried, what failed, full error output
- **NEVER accept "environment limitation" as a reason to skip** — diagnose and fix or report BLOCKED

---

## Invariants (always true)

- `NEVER mark a sprint or task complete if the dev server won't start`
- `NEVER mark a sprint or task complete if routes return 200 but contain error content`
- Full E2E / Playwright testing is a SEPARATE phase — this protocol is a smoke test only
- The smoke test runs after each batch merge (orchestrator Step 8), NOT after the full pipeline
- The full content-verification pass runs in `plan-build-test` Phase 5 after ALL batches complete

---

## proot-Distro Notes

- Set `CHOKIDAR_USEPOLLING=true` and `WATCHPACK_POLLING=true` before starting (file watchers)
- Set `NODE_OPTIONS="--max-old-space-size=2048"` to avoid OOM on large builds
- Chromium is available at `/usr/bin/chromium` — Playwright E2E tests work normally
- Native module rebuilds may fail — try `node-linker=hoisted` in `.npmrc` if symlinks break
- Cold-start times: 30-90 seconds is normal; do not reduce the 60s timeout
