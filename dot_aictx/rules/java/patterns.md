---
paths:
  - "**/*.java"
---
# Java Patterns

> This file extends [common/coding-style.md](../common/coding-style.md) with Java-specific content.

## Builder Pattern

Use for classes with many optional parameters — avoid telescoping constructors:

```java
public final class Email {
    private final String to;
    private final String subject;
    private final String body;
    private final List<String> cc;

    private Email(Builder b) {
        this.to = b.to; this.subject = b.subject;
        this.body = b.body; this.cc = List.copyOf(b.cc);
    }

    public static final class Builder {
        private final String to;
        private String subject = "", body = "";
        private List<String> cc = List.of();

        public Builder(String to) { this.to = to; }
        public Builder subject(String s) { this.subject = s; return this; }
        public Builder body(String b) { this.body = b; return this; }
        public Email build() { return new Email(this); }
    }
}
// Usage: new Email.Builder("a@b.com").subject("Hi").build()
```

## Repository Pattern with Spring Data

```java
public interface OrderRepository extends JpaRepository<Order, UUID> {
    List<Order> findByCustomerIdAndStatus(UUID customerId, OrderStatus status);
    @Query("SELECT o FROM Order o WHERE o.total > :min")
    List<Order> findHighValue(@Param("min") BigDecimal min);
}
```

## Streams for Collections

Prefer stream pipelines over imperative loops for transformations:

```java
// GOOD — declarative transformation
List<String> activeEmails = users.stream()
    .filter(User::isActive)
    .map(User::getEmail)
    .sorted()
    .toList(); // Java 16+ immutable list
```

## Switch Expressions (Java 14+)

```java
// GOOD — exhaustive switch expression
String label = switch (status) {
    case PENDING  -> "Awaiting payment";
    case PAID     -> "Processing";
    case SHIPPED  -> "On its way";
    case DELIVERED -> "Delivered";
};
```

## Sealed Types for Algebraic Results

```java
sealed interface Result<T> permits Result.Success, Result.Failure {
    record Success<T>(T value) implements Result<T> {}
    record Failure<T>(String message) implements Result<T> {}
}

Result<Order> result = orderService.place(request);
if (result instanceof Result.Success<Order> s) {
    return ResponseEntity.ok(s.value());
} else if (result instanceof Result.Failure<Order> f) {
    return ResponseEntity.badRequest().body(f.message());
}
```

## References

See skill: `java-patterns` for Spring Boot, reactive streams, and concurrency patterns.
