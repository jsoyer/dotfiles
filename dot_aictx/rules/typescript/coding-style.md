---
paths:
  - "**/*.ts"
  - "**/*.tsx"
  - "**/*.mts"
  - "**/*.cts"
---
# TypeScript Coding Style

> This file extends [common/coding-style.md](../common/coding-style.md) with TypeScript-specific content.

## Formatting

- **Prettier** for formatting — run before committing
- **ESLint** with `@typescript-eslint` for linting — treat warnings as errors in CI
- 2-space indent, single quotes, trailing commas (`"all"`)
- Max line length: 100 characters

## Type System

- **Never use `any`** — use `unknown` when the type is genuinely unknown and narrow it
- Prefer `interface` for object shapes (extensible); `type` for unions, intersections, mapped types
- Enable `strict: true` in `tsconfig.json` — no exceptions
- Use `satisfies` to validate a value matches a type without widening

```ts
// BAD — loses type info
const config: any = loadConfig();

// GOOD — unknown + narrowing
const config: unknown = loadConfig();
if (isConfig(config)) { /* narrowed here */ }

// GOOD — satisfies preserves the literal type
const palette = {
  red: [255, 0, 0],
  green: "#00ff00",
} satisfies Record<string, string | number[]>;
```

## Naming

- `camelCase` for variables, functions, methods
- `PascalCase` for classes, interfaces, types, enums, React components
- `SCREAMING_SNAKE_CASE` for module-level constants
- Prefix boolean variables with `is`, `has`, `can`, `should`
- Avoid abbreviations except universally known ones (`id`, `url`, `err`)

## Immutability

- Use `const` for all declarations unless reassignment is required
- Mark object properties `readonly` where mutation is not intended
- Use `as const` for literal tuples and enums

```ts
// GOOD — immutable config object
const HTTP_METHODS = ["GET", "POST", "PUT", "DELETE"] as const;
type HttpMethod = typeof HTTP_METHODS[number]; // "GET" | "POST" | "PUT" | "DELETE"

// GOOD — readonly properties
interface Config {
  readonly host: string;
  readonly port: number;
}
```

## File Organization

- One primary export per file; filename matches the export name
- Co-locate tests alongside source files (`foo.ts` / `foo.test.ts`)
- Barrel files (`index.ts`) only at module boundaries — never for deep re-exports

```text
src/
├── auth/
│   ├── auth.service.ts
│   ├── auth.service.test.ts
│   ├── auth.types.ts
│   └── index.ts          ← public API only
├── orders/
│   ├── order.model.ts
│   ├── order.repository.ts
│   └── index.ts
└── shared/
    └── errors.ts
```

## Error Handling

- Define typed error classes extending `Error`; set `name` in constructor
- Never `throw` raw strings or generic `new Error("something failed")`
- Use discriminated unions for operation results when exceptions are undesirable

```ts
class NotFoundError extends Error {
  readonly name = "NotFoundError";
  constructor(resource: string, id: string) {
    super(`${resource} with id '${id}' not found`);
  }
}
```

## References

See skill: `typescript-patterns` for comprehensive TypeScript idioms and patterns.
