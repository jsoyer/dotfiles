---
paths:
  - "**/*.swift"
---
# Swift Patterns

> This file extends [common/coding-style.md](../common/coding-style.md) with Swift-specific content.

## Protocol-Oriented Design

Define protocols at the consumer; conform concretions to them:

```swift
protocol UserRepository {
    func fetchUser(id: String) async throws -> User
    func save(_ user: User) async throws
}

final class UserService {
    private let repo: any UserRepository

    init(repo: any UserRepository) { self.repo = repo }

    func getProfile(id: String) async throws -> Profile {
        let user = try await repo.fetchUser(id: id)
        return Profile(user: user)
    }
}
```

## Result Type for Synchronous Operations

```swift
func parse(json: String) -> Result<User, DecodingError> {
    guard let data = json.data(using: .utf8) else {
        return .failure(DecodingError.dataCorrupted(.init(codingPath: [], debugDescription: "Invalid UTF-8")))
    }
    do {
        return .success(try JSONDecoder().decode(User.self, from: data))
    } catch let e as DecodingError {
        return .failure(e)
    }
}
```

## Builder Pattern via Closures (SwiftUI-style)

Use trailing closure configuration for complex initializers:

```swift
struct AlertConfig {
    var title: String
    var message: String
    var primaryAction: String = "OK"
    var destructive: Bool = false
}

extension AlertConfig {
    static func make(title: String, configure: (inout AlertConfig) -> Void) -> AlertConfig {
        var config = AlertConfig(title: title, message: "")
        configure(&config)
        return config
    }
}
// Usage: AlertConfig.make(title: "Delete?") { $0.destructive = true; $0.message = "Cannot undo" }
```

## Dependency Injection with Actors

Use actors for thread-safe service instances:

```swift
actor ImageCache {
    private var store: [URL: UIImage] = [:]

    func image(for url: URL) -> UIImage? { store[url] }
    func insert(_ image: UIImage, for url: URL) { store[url] = image }
}
```

## Opaque and Existential Types

Prefer `some Protocol` (opaque) over `any Protocol` (existential) when the concrete type is fixed:

```swift
// GOOD — opaque; concrete type known at compile time
func makeView() -> some View { Text("Hello") }

// GOOD — existential; type varies at runtime
let services: [any Service] = [ServiceA(), ServiceB()]
```

## References

See skill: `swift-patterns` for Combine, SwiftData, and Coordinator navigation patterns.
