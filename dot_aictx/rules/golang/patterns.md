---
paths:
  - "**/*.go"
---
# Go Patterns

> This file extends [common/coding-style.md](../common/coding-style.md) with Go-specific content.

## Interface-Based Dependency Injection

Define small interfaces at the consumer, not the producer:

```go
// Defined in the package that USES it — not in the storage package
type UserStore interface {
    FindByID(ctx context.Context, id string) (*User, error)
    Save(ctx context.Context, u *User) error
}

type UserService struct {
    store  UserStore
    logger *slog.Logger
}

func NewUserService(store UserStore, logger *slog.Logger) *UserService {
    return &UserService{store: store, logger: logger}
}
```

## Functional Options

Preferred over constructor parameter explosion or config structs when options are optional:

```go
type ServerOption func(*Server)

func WithTimeout(d time.Duration) ServerOption {
    return func(s *Server) { s.timeout = d }
}
func WithMaxConns(n int) ServerOption {
    return func(s *Server) { s.maxConns = n }
}

func NewServer(addr string, opts ...ServerOption) *Server {
    s := &Server{addr: addr, timeout: 30 * time.Second, maxConns: 100}
    for _, opt := range opts {
        opt(s)
    }
    return s
}
```

## Context Propagation

Pass `context.Context` as the **first parameter** to every function that does I/O:

```go
func (s *UserService) GetUser(ctx context.Context, id string) (*User, error) {
    return s.store.FindByID(ctx, id)
}
```

Never store contexts in structs — they are request-scoped.

## Channel Patterns

Use channels for signaling; use mutexes for shared state:

```go
// Fan-out: distribute work across N workers
jobs := make(chan Job, len(items))
for _, item := range items {
    jobs <- Job{item: item}
}
close(jobs)

var wg sync.WaitGroup
for range runtime.NumCPU() {
    wg.Add(1)
    go func() {
        defer wg.Done()
        for job := range jobs {
            process(ctx, job)
        }
    }()
}
wg.Wait()
```

## Table-Driven Design

Prefer returning data over procedural branching:

```go
var statusText = map[int]string{
    200: "OK",
    404: "Not Found",
    500: "Internal Server Error",
}

func StatusText(code int) string {
    if text, ok := statusText[code]; ok {
        return text
    }
    return "Unknown"
}
```

## References

See skill: `golang-patterns` for HTTP middleware, database patterns, and concurrency.
