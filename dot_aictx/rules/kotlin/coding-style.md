---
paths:
  - "**/*.kt"
  - "**/*.kts"
---
# Kotlin Coding Style

> This file extends [common/coding-style.md](../common/coding-style.md) with Kotlin-specific content.

## Formatting

- **ktfmt** (Google format) or **ktlint** — enforce in CI via Gradle plugin
- 4-space indent; no semicolons; trailing commas in multi-line expressions
- Max line length: 120 characters

## Naming

- `camelCase` for properties and functions; `PascalCase` for classes, objects, interfaces
- `SCREAMING_SNAKE_CASE` for compile-time constants (`const val`)
- Boolean properties: `isActive`, `hasPermission`, `canSubmit`
- Extension functions named after what they do: `String.toSlug()`, `List<T>.second()`

## Null Safety

Kotlin's type system eliminates most NullPointerExceptions — respect it:

```kotlin
// GOOD — nullable handled explicitly
fun findUser(id: String): User? = repo.findById(id)

val email = findUser(id)?.email ?: throw NotFoundException("User $id")

// BAD — suppresses null safety
val user = findUser(id)!!
```

## Immutability

- Use `val` by default; only `var` when mutation is required
- Use `data class` for value objects — they provide structural equality and `copy()`

```kotlin
// GOOD — immutable data class
data class Money(val amount: BigDecimal, val currency: String) {
    fun add(other: Money): Money {
        require(currency == other.currency) { "Currency mismatch" }
        return copy(amount = amount + other.amount)
    }
}
```

## Coroutines

Use coroutines for all async and concurrent work — avoid callbacks:

```kotlin
// GOOD — suspend function; caller controls the coroutine scope
suspend fun loadProfile(id: String): Profile {
    val user = userRepo.findById(id) ?: throw NotFoundException("User $id")
    return Profile(user)
}

// GOOD — structured concurrency with async/await
val (user, settings) = coroutineScope {
    val u = async { userRepo.findById(id) }
    val s = async { settingsRepo.find(id) }
    u.await() to s.await()
}
```

## Sealed Classes for State

```kotlin
sealed class Result<out T> {
    data class Success<T>(val value: T) : Result<T>()
    data class Failure(val error: Throwable) : Result<Nothing>()
}

val result: Result<Order> = orderService.place(request)
when (result) {
    is Result.Success -> respond(result.value)
    is Result.Failure -> respondError(result.error)
}
```

## References

See skill: `kotlin-patterns` for Spring Boot Kotlin, Ktor, and Arrow functional patterns.
