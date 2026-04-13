---
paths:
  - "**/*.kt"
  - "**/*.kts"
---
# Kotlin Patterns

> This file extends [common/coding-style.md](../common/coding-style.md) with Kotlin-specific content.

## Repository Pattern

```kotlin
interface UserRepository {
    suspend fun findById(id: UserId): User?
    suspend fun findAll(): List<User>
    suspend fun save(user: User): User
    suspend fun delete(id: UserId)
}

class ExposedUserRepository(private val db: Database) : UserRepository {
    override suspend fun findById(id: UserId): User? = withContext(Dispatchers.IO) {
        UsersTable.selectAll().where { UsersTable.id eq id.value }.singleOrNull()?.toUser()
    }
    // ...
}
```

## Extension Functions for Readability

```kotlin
// Domain-specific extension on a type you don't own
fun String.toSlug(): String = lowercase()
    .replace(Regex("[^a-z0-9]+"), "-")
    .trim('-')

// Extension on collections
fun <T> List<T>.second(): T {
    if (size < 2) throw NoSuchElementException("List has fewer than 2 elements")
    return this[1]
}
```

## DSL-Style Builders

Kotlin's lambda-with-receiver enables expressive builders:

```kotlin
class EmailBuilder {
    var to: String = ""
    var subject: String = ""
    var body: String = ""
}

fun email(block: EmailBuilder.() -> Unit): Email {
    val b = EmailBuilder().apply(block)
    return Email(to = b.to, subject = b.subject, body = b.body)
}

// Usage:
val msg = email {
    to = "alice@example.com"
    subject = "Hello"
    body = "How are you?"
}
```

## Scope Functions

Use scope functions purposefully — not interchangeably:

| Function | Use when | Returns |
|----------|----------|---------|
| `let`    | null-safe chain, local variable rename | lambda result |
| `run`    | object config + compute result | lambda result |
| `apply`  | object initialization / mutation | receiver |
| `also`   | side effects (logging, validation) | receiver |
| `with`   | operations on a non-null receiver | lambda result |

```kotlin
val user = userRepo.findById(id)
    ?.also { logger.debug("Found user: ${it.id}") }
    ?: throw NotFoundException("User $id")
```

## Coroutine Flow for Streams

```kotlin
fun watchOrders(userId: UserId): Flow<List<Order>> = flow {
    while (true) {
        emit(orderRepo.findByUser(userId))
        delay(5.seconds)
    }
}.flowOn(Dispatchers.IO)
```

## References

See skill: `kotlin-patterns` for Arrow, Ktor routing, and Spring Kotlin DSL patterns.
