---
paths:
  - "**/*.java"
---
# Java Security

> This file extends [common/security.md](../common/security.md) with Java-specific content.

## SQL Injection

- Always use `PreparedStatement` or Spring Data / JPA named parameters
- Never concatenate user input into JPQL/SQL strings

```java
// BAD — SQL injection
String sql = "SELECT * FROM users WHERE email = '" + email + "'";
stmt.executeQuery(sql);

// GOOD — PreparedStatement
PreparedStatement ps = conn.prepareStatement("SELECT * FROM users WHERE email = ?");
ps.setString(1, email);

// GOOD — Spring Data named parameter
@Query("SELECT u FROM User u WHERE u.email = :email")
Optional<User> findByEmail(@Param("email") String email);
```

## Password Storage

- Use **BCrypt** (cost factor >= 12) via Spring Security's `BCryptPasswordEncoder`
- Never store plain-text or MD5/SHA-1 hashed passwords

```java
PasswordEncoder encoder = new BCryptPasswordEncoder(12);
String hash = encoder.encode(rawPassword);
boolean matches = encoder.matches(rawPassword, hash);
```

## Environment Secrets

- Use Spring's `@Value("${MY_SECRET}")` with `.env` / Vault / Kubernetes secrets — never hardcode
- Validate required properties at startup with `@ConfigurationPropertiesBinding`

## Input Validation with Bean Validation

```java
public record CreateUserRequest(
    @Email @NotBlank String email,
    @Size(min = 12, max = 128) String password,
    @NotNull @Positive Integer age
) {}

// In controller — @Valid triggers validation, BindingResult captures errors
@PostMapping("/users")
ResponseEntity<?> create(@Valid @RequestBody CreateUserRequest req) { /* ... */ }
```

## Serialization Safety

- Never deserialize untrusted data with Java's native `ObjectInputStream`
- Use JSON (Jackson/Gson) with explicit type mapping; disable polymorphic type handling unless needed
- Set `DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES = false` to avoid information leaks

## Dependency Security

- Use **OWASP Dependency-Check** Maven/Gradle plugin in CI
- Keep Spring Boot and Spring Security on latest patch releases

## References

See skill: `security-review` for general security checklists.
See skill: `java-patterns` for Spring Security configuration.
