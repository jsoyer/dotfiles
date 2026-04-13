---
paths:
  - "**/*.ts"
  - "**/*.tsx"
---
# TypeScript Patterns

> This file extends [common/coding-style.md](../common/coding-style.md) with TypeScript-specific content.

## Discriminated Unions

Model state variants as a tagged union — make illegal states unrepresentable:

```ts
type Result<T, E = Error> =
  | { ok: true; value: T }
  | { ok: false; error: E };

function divide(a: number, b: number): Result<number, string> {
  if (b === 0) return { ok: false, error: "division by zero" };
  return { ok: true, value: a / b };
}

const result = divide(10, 2);
if (result.ok) {
  console.log(result.value); // narrowed to number
}
```

## Branded / Opaque Types

Prevent mixing structurally identical primitives:

```ts
type UserId = string & { readonly _brand: "UserId" };
type OrderId = string & { readonly _brand: "OrderId" };

const toUserId = (id: string): UserId => id as UserId;
// toUserId("abc") !== ("abc" as OrderId) — different brands
```

## Repository Pattern

```ts
interface UserRepository {
  findById(id: UserId): Promise<User | null>;
  findAll(): Promise<User[]>;
  save(user: User): Promise<User>;
  delete(id: UserId): Promise<void>;
}

class PgUserRepository implements UserRepository {
  constructor(private readonly db: Db) {}
  async findById(id: UserId) {
    return this.db.query<User>("SELECT * FROM users WHERE id = $1", [id]);
  }
  // ...
}
```

## Zod for Runtime Validation

Parse external data at system boundaries; types derived from schemas:

```ts
import { z } from "zod";

const UserSchema = z.object({
  id: z.string().uuid(),
  email: z.string().email(),
  role: z.enum(["admin", "member"]),
});

type User = z.infer<typeof UserSchema>;

const user = UserSchema.parse(apiResponse); // throws on invalid input
```

## Dependency Injection with Interfaces

Inject dependencies rather than importing concretions:

```ts
interface Logger { info(msg: string): void; error(msg: string): void; }

class OrderService {
  constructor(
    private readonly repo: OrderRepository,
    private readonly logger: Logger,
  ) {}
}
```

## Option / Maybe Pattern

Avoid `null` checks scattered throughout code:

```ts
function findUser(id: UserId): User | undefined { /* ... */ }

const user = findUser(id);
if (user === undefined) {
  return { ok: false, error: new NotFoundError("User", id) };
}
// user is narrowed to User here
```

## References

See skill: `typescript-patterns` for advanced generics, conditional types, and template literal types.
