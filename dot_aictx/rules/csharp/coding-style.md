---
paths:
  - "**/*.cs"
  - "**/*.csx"
---
# C# Coding Style

> This file extends [common/coding-style.md](../common/coding-style.md) with C#-specific content.

## Formatting

- **dotnet-format** / **EditorConfig** — enforce via `dotnet format` in CI
- **StyleCop.Analyzers** or **Roslynator** for extended lint rules
- 4-space indent; `{` on same line as control structures (K&R style)

## Naming

- `PascalCase` for types, methods, properties, events, namespaces
- `camelCase` for local variables and parameters
- `_camelCase` with underscore prefix for private fields
- Prefix interfaces with `I`: `IUserRepository`, `ILogger<T>`
- Async methods end with `Async`: `GetUserAsync()`, `SaveOrderAsync()`

## Modern C# (C# 12+)

Use modern syntax to reduce boilerplate:

```csharp
// GOOD — primary constructor (C# 12)
class OrderService(IOrderRepository repo, ILogger<OrderService> logger) {
    public async Task<Order?> GetOrderAsync(Guid id) =>
        await repo.FindByIdAsync(id);
}

// GOOD — record for immutable value objects
record Money(decimal Amount, string Currency) {
    public Money Add(Money other) {
        if (Currency != other.Currency) throw new InvalidOperationException("Currency mismatch");
        return this with { Amount = Amount + other.Amount };
    }
}
```

## Null Safety

- Enable nullable reference types: `<Nullable>enable</Nullable>` in `.csproj`
- Use `?` for nullable types; handle with `??`, `?.`, or null checks
- Avoid `!` (null-forgiving operator) except in constructors when value is guaranteed

```csharp
// GOOD — nullable return type, explicit check
public async Task<User?> FindUserAsync(Guid id) { /* ... */ }

var user = await FindUserAsync(id)
    ?? throw new NotFoundException($"User {id} not found");
```

## Async/Await

- All I/O-bound methods must be `async Task<T>` — never `Task.Result` or `.Wait()`
- Pass `CancellationToken` through the call chain for all async operations
- Use `ConfigureAwait(false)` in library code to avoid deadlocks

```csharp
public async Task<IReadOnlyList<Order>> GetOrdersAsync(
    Guid userId, CancellationToken ct = default)
{
    return await _repo.FindByUserAsync(userId, ct).ConfigureAwait(false);
}
```

## Immutability

- Use `record` for value types; `init`-only properties for semi-mutable DTOs
- Use `IReadOnlyList<T>`, `IReadOnlyDictionary<K,V>` for exposed collections
- Use `with` expressions for non-destructive updates on records

## References

See skill: `csharp-patterns` for ASP.NET Core, EF Core, and MediatR patterns.
