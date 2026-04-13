---
paths:
  - "**/*.go"
---
# Go Security

> This file extends [common/security.md](../common/security.md) with Go-specific content.

## SQL Injection

- Always use parameterized queries with `database/sql` or a query builder
- Never format user data into SQL strings with `fmt.Sprintf`

```go
// BAD — SQL injection
query := fmt.Sprintf("SELECT * FROM users WHERE email = '%s'", email)
db.QueryContext(ctx, query)

// GOOD — parameterized
db.QueryContext(ctx, "SELECT * FROM users WHERE email = $1", email)

// GOOD — sqlc-generated typed queries (preferred for larger projects)
user, err := q.GetUserByEmail(ctx, email)
```

## Environment Secrets

- Read secrets from environment variables; validate at startup
- Never log secret values — redact them explicitly

```go
func mustEnv(key string) string {
    v := os.Getenv(key)
    if v == "" {
        log.Fatalf("required env var %s is not set", key)
    }
    return v
}

apiKey := mustEnv("PAYMENT_API_KEY")
```

## Input Validation

- Validate and sanitize all inputs at HTTP handler boundaries
- Use `net/http` `MaxBytesReader` to limit request body size and prevent DoS

```go
http.MaxBytesReader(w, r.Body, 1_048_576) // 1 MiB limit

var req CreateUserRequest
if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
    http.Error(w, "invalid request body", http.StatusBadRequest)
    return
}
if err := req.Validate(); err != nil {
    http.Error(w, err.Error(), http.StatusUnprocessableEntity)
    return
}
```

## Cryptography

- Use `crypto/rand` for all random values — never `math/rand` for security purposes
- Use `golang.org/x/crypto/bcrypt` for password hashing (cost >= 12)
- Use `crypto/tls` with `MinVersion: tls.VersionTLS12` for TLS configuration

```go
import "crypto/rand"
token := make([]byte, 32)
if _, err := rand.Read(token); err != nil {
    return fmt.Errorf("generate token: %w", err)
}
encoded := base64.URLEncoding.EncodeToString(token)
```

## HTTP Security Headers

Set security headers in middleware for all responses:

```go
func securityHeaders(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        w.Header().Set("X-Content-Type-Options", "nosniff")
        w.Header().Set("X-Frame-Options", "DENY")
        w.Header().Set("Strict-Transport-Security", "max-age=63072000")
        next.ServeHTTP(w, r)
    })
}
```

## Dependency Security

- Run `govulncheck ./...` regularly and in CI
- Use `go mod verify` to detect tampered module cache

## References

See skill: `security-review` for general security checklists.
