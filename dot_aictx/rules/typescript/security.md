---
paths:
  - "**/*.ts"
  - "**/*.tsx"
---
# TypeScript Security

> This file extends [common/security.md](../common/security.md) with TypeScript-specific content.

## XSS Prevention

- Never inject unsanitized user input into the DOM — use `textContent` for plain text
- In React, all JSX string expressions are escaped automatically — preserve this behavior
- Sanitize HTML with **DOMPurify** when rendering user-supplied rich text is required
- Avoid string-based DOM APIs (`innerHTML`, `document.write`) entirely when user data is involved

```ts
// GOOD — safe plain text insertion
element.textContent = userInput;

// GOOD — sanitize with DOMPurify when HTML is required
import DOMPurify from "dompurify";
element.innerHTML = DOMPurify.sanitize(userInput);
```

## SQL Injection

- Always use parameterized queries — never template literals with user input in SQL
- With ORMs (Prisma, Drizzle) use typed query builders; avoid raw query escape hatches

```ts
// BAD — SQL injection
const rows = await db.query(`SELECT * FROM users WHERE email = '${email}'`);

// GOOD — parameterized (node-postgres)
const rows = await db.query("SELECT * FROM users WHERE email = $1", [email]);

// GOOD — Prisma typed query
const user = await prisma.user.findUnique({ where: { email } });
```

## Environment Secrets

- Read secrets from environment variables at startup — never hardcode
- Validate all required env vars are present on boot; fail fast with a clear message
- Never log secret values; mask them in error messages

```ts
// GOOD — validate at startup
function loadEnv() {
  const apiKey = process.env.PAYMENT_API_KEY;
  if (!apiKey) throw new Error("PAYMENT_API_KEY env var is required");
  return { apiKey };
}
```

## Input Validation with Zod

- Validate ALL external inputs (HTTP bodies, query params, env vars, file content) with Zod
- Reject early with HTTP 400 — never pass unvalidated data deeper into the system

```ts
import { z } from "zod";
const CreateUserBody = z.object({
  email: z.string().email().max(254),
  password: z.string().min(12).max(128),
});

app.post("/users", async (req, res) => {
  const body = CreateUserBody.safeParse(req.body);
  if (!body.success) return res.status(400).json({ error: body.error.flatten() });
  // body.data is now safe to use
});
```

## Dependency Security

- Run `pnpm audit` / `npm audit` regularly and in CI
- Use **socket.dev** or Renovate for continuous dependency monitoring
- Pin major versions; review changelogs before upgrading

## References

See skill: `security-review` for general security checklists.
See skill: `typescript-patterns` for validation and input sanitization patterns.
