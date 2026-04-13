---
paths:
  - "**/*.java"
---
# Java Coding Style

> This file extends [common/coding-style.md](../common/coding-style.md) with Java-specific content.

## Formatting

- **Google Java Format** or **Spotless** — enforced via Maven/Gradle plugin in CI
- 2-space indent (Google style) or 4-space (Oracle/Sun style) — pick one, be consistent
- Organize imports: static imports first, then `java.*`, then third-party, then project
- Max line length: 100 characters

## Modern Java (17+)

Prefer modern language features over legacy patterns:

```java
// GOOD — record for immutable data
record Point(double x, double y) {}

// GOOD — sealed interface for algebraic types
sealed interface Shape permits Circle, Rectangle {}
record Circle(double radius) implements Shape {}
record Rectangle(double width, double height) implements Shape {}

// GOOD — pattern matching instanceof
if (shape instanceof Circle c) {
    return Math.PI * c.radius() * c.radius();
}
```

## Naming

- `camelCase` for methods and fields; `PascalCase` for classes and interfaces
- `SCREAMING_SNAKE_CASE` for constants (`static final`)
- Prefix boolean methods with `is`, `has`, `can`: `isActive()`, `hasPermission()`
- Interface names: noun (`Repository`) or adjective (`Comparable`) — never `IFoo`

## Immutability

- Declare fields `final` by default; only non-final when mutation is required
- Use `record` for simple value objects (Java 16+)
- Use `Collections.unmodifiableList()` or `List.copyOf()` when returning collections

```java
// GOOD — immutable value object via record
record Money(BigDecimal amount, Currency currency) {
    Money {
        Objects.requireNonNull(amount, "amount");
        if (amount.compareTo(BigDecimal.ZERO) < 0) throw new IllegalArgumentException("negative amount");
    }
}
```

## Optionals

Use `Optional<T>` for method return values that may be absent — never for fields or parameters:

```java
// GOOD — Optional return
Optional<User> findById(String id) { /* ... */ }

// GOOD — chaining
findById(id)
    .map(User::email)
    .orElseThrow(() -> new NotFoundException("user", id));

// BAD — Optional as parameter
void process(Optional<User> user) { /* avoid */ }
```

## File Organization

- One top-level class per file; filename matches the class name
- Package structure mirrors the domain: `com.example.orders.service`
- Keep packages cohesive: `model`, `service`, `repository`, `controller` under each domain

## References

See skill: `java-patterns` for streams, builders, and Spring Boot patterns.
