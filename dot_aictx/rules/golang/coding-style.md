---
paths:
  - "**/*.go"
---
# Go Coding Style

> This file extends [common/coding-style.md](../common/coding-style.md) with Go-specific content.

## Formatting

- **gofmt** / **goimports** — mandatory, enforced by CI; no style debates
- **golangci-lint** with at minimum `errcheck`, `staticcheck`, `revive`, `gosec`
- Max line length: 120 characters (soft); let gofmt decide wrapping

## Naming

- `camelCase` for unexported identifiers; `PascalCase` for exported
- Acronyms are all-caps when exported: `ServeHTTP`, `UserID`, `ParseURL`
- Receiver names: 1-2 letter abbreviation of the type (`u` for `User`, `srv` for `Server`)
- Error variables: `ErrNotFound`, `ErrInvalidInput` (exported); `errTimeout` (unexported)
- Interface names: single-method interfaces end in `-er` (`Reader`, `Stringer`, `Closer`)

## Error Handling

- Always handle errors — never use `_` for an error return
- Wrap errors with context using `fmt.Errorf("operation: %w", err)`
- Use `errors.Is` / `errors.As` for checking wrapped errors
- Define sentinel errors with `errors.New` at package level

```go
// GOOD — wrapped error with context
func loadConfig(path string) (*Config, error) {
    data, err := os.ReadFile(path)
    if err != nil {
        return nil, fmt.Errorf("loadConfig: %w", err)
    }
    // ...
}

// GOOD — sentinel error check
if errors.Is(err, ErrNotFound) { /* handle */ }
```

## Package Design

- One package per directory; package name matches the directory name
- Avoid `util`, `common`, `helpers` packages — put code in domain packages
- Keep `internal/` for packages not meant for external import
- Prefer flat package hierarchies; deep nesting signals poor design

## Defer for Cleanup

Use `defer` immediately after acquiring a resource:

```go
f, err := os.Open(path)
if err != nil {
    return nil, fmt.Errorf("open: %w", err)
}
defer f.Close()
```

## Immutability

Go has no built-in immutability, but apply these patterns:
- Pass structs by value when they are small and should not be mutated
- Return copies from constructor functions; avoid exposing internal slices/maps
- Use unexported fields with getter methods to protect state

## References

See skill: `golang-patterns` for interfaces, channels, and concurrency idioms.
