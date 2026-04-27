# Web & UI Rules

Rules that only apply to projects with a web frontend or UI layer. Import from a
project's CLAUDE.md when the stack includes a browser-facing UI. Not auto-loaded
globally — the global CLAUDE.md keeps its core-workflow focus.

## Mobile First (mandatory order for UI work)

1. Mobile (< 640px)
2. Tablet (640-1024px)
3. Desktop (1024-1280px)
4. Wide (> 1280px)

## Security Checklist

Input sanitization (XSS). CSP headers. No sensitive data client-side. HTTPS.
Dependency audit. Rate limiting. CORS. No tokens in frontend code.

## Performance Targets

- **LCP** < 2s
- **CLS** < 0.1
- **FID/INP** < 200ms
- WebP images with lazy loading
- Font preload + swap
- JS bundle < 200KB gzipped
- SSG for content pages

## End-of-Task Browser Verification

Required for UI/API/server changes. Start dev server → Playwright navigate →
screenshot to `.artifacts/playwright/screenshots/YYYY-MM-DD_HHmm/` → check browser
AND server console → fix all errors → repeat. Both consoles must be clean before
claiming done.

Full protocol: `~/.claude/docs/on-demand/browser-verification.md`.
