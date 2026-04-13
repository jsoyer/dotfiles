---
paths:
  - "**/*.swift"
---
# Swift Coding Style

> This file extends [common/coding-style.md](../common/coding-style.md) with Swift-specific content.

## Formatting

- **swift-format** (official) for formatting — integrate into Xcode build phase or pre-commit hook
- **SwiftLint** for linting — use default rules plus `force_cast`, `force_try`, `implicitly_unwrapped_optional`
- 4-space indent; trailing commas in multi-line collections

## Naming

- `camelCase` for properties, methods, local variables; `PascalCase` for types, protocols, enums
- Method names should read as sentences: `tableView(_:cellForRowAt:)`, `fetchUser(withID:)`
- Boolean properties: `isLoading`, `hasError`, `canSubmit`
- Avoid type name repetition in method names: `users.removeUser(u)` → `users.remove(u)`

## Value Types by Default

Prefer `struct` over `class` — use `class` only when identity, inheritance, or Obj-C interop is needed:

```swift
// GOOD — value semantics, no aliasing bugs
struct Money {
    let amount: Decimal
    let currency: Currency
}

// BAD — reference semantics where value semantics suffice
class Money { var amount: Decimal; var currency: Currency; ... }
```

## Optionals

- Avoid force-unwrap `!` — prefer `guard let`, `if let`, or optional chaining
- Implicitly unwrapped optionals (`Type!`) only for `@IBOutlet` and `@IBAction`

```swift
// GOOD — guard let for early exit
guard let user = findUser(id: id) else {
    return .failure(AppError.notFound)
}

// GOOD — optional chaining
let city = user.address?.city ?? "Unknown"
```

## Error Handling

- Use Swift's `throws` / `try` / `catch` for recoverable errors
- Define typed errors with `enum` conforming to `LocalizedError`
- Use `Result<T, E>` when async propagation is needed without `async throws`

```swift
enum AuthError: LocalizedError {
    case invalidCredentials
    case tokenExpired
    var errorDescription: String? {
        switch self {
        case .invalidCredentials: return "Invalid email or password"
        case .tokenExpired: return "Session expired, please log in again"
        }
    }
}
```

## Concurrency (Swift 5.5+)

- Use `async`/`await` — avoid completion handlers and Combine for new code
- Mark types that cross actor boundaries as `Sendable`
- Use `@MainActor` for UI updates; isolate background work in actors

```swift
@MainActor
func loadProfile() async {
    isLoading = true
    defer { isLoading = false }
    profile = try? await userService.fetchProfile(id: userId)
}
```

## References

See skill: `swift-patterns` for Combine, SwiftUI, and dependency injection patterns.
