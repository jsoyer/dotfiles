---
paths:
  - "**/*.swift"
  - "**/*Tests.swift"
  - "**/*Test.swift"
---
# Swift Testing

> This file extends [common/testing.md](../common/testing.md) with Swift-specific content.

## Test Framework

- **Swift Testing** (Xcode 16+) for new code — `@Test`, `#expect`, `#require`
- **XCTest** for legacy code and UITest targets
- **swift-mock** or hand-written protocol mocks for dependency isolation
- No third-party assertion library needed — Swift Testing's macros are expressive

## Test Organization

```text
MyApp/
├── Sources/
│   └── Orders/
│       ├── OrderService.swift
│       └── OrderRepository.swift
└── Tests/
    └── OrdersTests/
        ├── OrderServiceTests.swift
        └── Mocks/
            └── MockOrderRepository.swift
```

## Swift Testing Pattern (Xcode 16+)

```swift
import Testing
@testable import Orders

@Suite("OrderService")
struct OrderServiceTests {
    let mockRepo = MockOrderRepository()
    var svc: OrderService { OrderService(repo: mockRepo) }

    @Test("returns nil when order not found")
    func orderNotFound() async throws {
        mockRepo.findByIDResult = nil
        let result = try await svc.getOrder(id: "x")
        #expect(result == nil)
    }

    @Test("throws when ID is empty", arguments: ["", " ", "\t"])
    func throwsOnInvalidID(id: String) async {
        await #expect(throws: ValidationError.self) {
            try await svc.getOrder(id: id)
        }
    }
}
```

## XCTest Pattern (Legacy / UITests)

```swift
import XCTest
@testable import Orders

final class OrderServiceTests: XCTestCase {
    func testReturnsNilWhenNotFound() async throws {
        let repo = MockOrderRepository()
        repo.findByIDResult = nil
        let svc = OrderService(repo: repo)
        let result = try await svc.getOrder(id: "missing")
        XCTAssertNil(result)
    }
}
```

## Mocking via Protocols

```swift
final class MockOrderRepository: OrderRepository {
    var findByIDResult: Order?
    var saveCalled = false

    func fetchOrder(id: String) async throws -> Order? { findByIDResult }
    func save(_ order: Order) async throws { saveCalled = true }
}
```

## Async Test Patterns

- Use `async throws` test functions — no XCTestExpectation needed for async code in Swift Testing
- Use `withCheckedThrowingContinuation` only when wrapping legacy callback APIs

## Coverage

- Enable code coverage in the test scheme: `Product > Scheme > Test > Options > Gather coverage`
- Target 80%+ coverage on business logic; exclude generated code and SwiftUI previews

## References

See skill: `swift-testing` for UI testing, snapshot testing, and performance test patterns.
