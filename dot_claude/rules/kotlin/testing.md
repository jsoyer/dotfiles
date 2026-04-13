---
paths:
  - "**/*.kt"
  - "**/*Test.kt"
  - "**/*Tests.kt"
---
# Kotlin Testing

> This file extends [common/testing.md](../common/testing.md) with Kotlin-specific content.

## Test Framework

- **JUnit 5** with **kotlin-test** for assertions
- **MockK** for mocking Kotlin classes and coroutines — preferred over Mockito for Kotlin
- **Kotest** as an alternative test framework with richer spec styles
- **kotlinx-coroutines-test** for testing suspend functions and Flow

## Test Organization

```text
src/
├── main/kotlin/com/example/orders/
│   └── OrderService.kt
└── test/kotlin/com/example/orders/
    ├── OrderServiceTest.kt
    └── fixtures/
        └── OrderFixtures.kt
```

## Unit Test with MockK

```kotlin
import io.mockk.*
import kotlin.test.*

class OrderServiceTest {
    private val repo = mockk<OrderRepository>()
    private val svc = OrderService(repo)

    @Test
    fun `returns null when order not found`() = runTest {
        coEvery { repo.findById(any()) } returns null
        assertNull(svc.getOrder(OrderId("x")))
        coVerify(exactly = 1) { repo.findById(any()) }
    }

    @Test
    fun `throws on invalid order id`() = runTest {
        assertFailsWith<ValidationException> {
            svc.getOrder(OrderId(""))
        }
    }
}
```

## Testing Coroutine Flow

```kotlin
import kotlinx.coroutines.test.runTest
import app.cash.turbine.test

@Test
fun `emits orders on change`() = runTest {
    orderService.watchOrders(userId).test {
        val first = awaitItem()
        assertNotNull(first)
        cancelAndIgnoreRemainingEvents()
    }
}
```

Use **Turbine** (`app.cash.turbine`) for Flow testing — avoids manual coroutine management.

## Parameterized Tests

```kotlin
@ParameterizedTest
@CsvSource("alice@example.com, true", "bad-email, false", "'', false")
fun `validates email correctly`(email: String, expected: Boolean) {
    assertEquals(expected, EmailValidator.isValid(email))
}
```

## Kotest Style (alternative)

```kotlin
class OrderServiceSpec : FunSpec({
    val repo = mockk<OrderRepository>()
    val svc = OrderService(repo)

    test("returns null when order not found") {
        coEvery { repo.findById(any()) } returns null
        svc.getOrder(OrderId("x")) shouldBe null
    }
})
```

## Coverage

- JaCoCo via Kotlin Gradle plugin; target 80%+ on business logic
- Exclude generated files, sealed class boilerplate

## References

See skill: `kotlin-testing` for Spring Boot test slices, Testcontainers, and WireMock in Kotlin.
