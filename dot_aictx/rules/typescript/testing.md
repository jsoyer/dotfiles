---
paths:
  - "**/*.ts"
  - "**/*.tsx"
  - "**/*.test.ts"
  - "**/*.spec.ts"
---
# TypeScript Testing

> This file extends [common/testing.md](../common/testing.md) with TypeScript-specific content.

## Test Framework

- **Vitest** for unit and integration tests (fast, native ESM, compatible with Jest API)
- **Playwright** for E2E tests
- **msw** (Mock Service Worker) for HTTP mocking — avoid mocking `fetch` directly
- `vi.fn()` / `vi.spyOn()` for mocking functions and modules

## Test Organization

```text
src/
├── auth/
│   ├── auth.service.ts
│   └── auth.service.test.ts   ← co-located unit tests
├── orders/
│   ├── order.repository.ts
│   └── order.repository.test.ts
tests/
└── e2e/
    └── checkout.spec.ts       ← Playwright E2E tests
```

## Unit Test Pattern

```ts
import { describe, it, expect, vi, beforeEach } from "vitest";
import { OrderService } from "./order.service";

describe("OrderService", () => {
  let service: OrderService;
  const mockRepo = { findById: vi.fn(), save: vi.fn() };

  beforeEach(() => {
    vi.clearAllMocks();
    service = new OrderService(mockRepo);
  });

  it("returns null when order does not exist", async () => {
    mockRepo.findById.mockResolvedValue(null);
    const result = await service.getOrder("unknown-id");
    expect(result).toBeNull();
  });
});
```

## HTTP Mocking with msw

```ts
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";

const server = setupServer(
  http.get("/api/users/:id", ({ params }) =>
    HttpResponse.json({ id: params.id, name: "Alice" })
  ),
);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
```

## Type-Safe Test Utilities

```ts
// Use satisfies to catch mistakes in test fixtures
const mockUser = {
  id: "user-1",
  email: "alice@example.com",
  role: "admin",
} satisfies User;
```

## Coverage

- Target 80%+ line coverage
- Use `vitest --coverage` with **v8** provider
- Exclude generated files, type-only files, and barrel `index.ts` files

```bash
vitest run --coverage
vitest run --coverage --coverage.thresholds.lines=80
```

## References

See skill: `typescript-testing` for mocking complex modules, testing async code, and Playwright patterns.
