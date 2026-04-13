---
paths:
  - "**/*.go"
  - "**/*_test.go"
---
# Go Testing

> This file extends [common/testing.md](../common/testing.md) with Go-specific content.

## Test Framework

- Standard library `testing` package for unit and integration tests
- **testify** (`assert` / `require`) for readable assertions — `require` halts the test on failure
- **gomock** or hand-rolled interfaces for mocking dependencies
- **httptest** (`net/http/httptest`) for HTTP handler tests without a live server

## Test Organization

```text
auth/
├── handler.go
├── handler_test.go     ← package auth_test (black-box) or package auth (white-box)
├── service.go
└── service_test.go
testdata/               ← fixtures read by tests (git-tracked)
    └── valid_config.json
```

Use `package foo_test` (external test package) for integration tests; `package foo` for unit tests needing unexported symbols.

## Table-Driven Tests

Go's idiomatic pattern — always prefer over repeated `t.Run` blocks:

```go
func TestDivide(t *testing.T) {
    cases := []struct {
        name    string
        a, b    float64
        want    float64
        wantErr bool
    }{
        {"simple", 10, 2, 5, false},
        {"zero divisor", 10, 0, 0, true},
    }
    for _, tc := range cases {
        t.Run(tc.name, func(t *testing.T) {
            got, err := Divide(tc.a, tc.b)
            if tc.wantErr {
                require.Error(t, err)
                return
            }
            require.NoError(t, err)
            assert.Equal(t, tc.want, got)
        })
    }
}
```

## HTTP Handler Tests

```go
func TestCreateUserHandler(t *testing.T) {
    svc := &mockUserService{}
    h := NewHandler(svc)

    body := strings.NewReader(`{"email":"a@b.com"}`)
    req := httptest.NewRequest(http.MethodPost, "/users", body)
    req.Header.Set("Content-Type", "application/json")
    rec := httptest.NewRecorder()

    h.ServeHTTP(rec, req)

    assert.Equal(t, http.StatusCreated, rec.Code)
}
```

## Subtests and Parallelism

Mark independent tests `t.Parallel()` to speed up test runs:

```go
func TestProcessOrder(t *testing.T) {
    t.Parallel()
    // ...
}
```

## Coverage

- Target 80%+ coverage on business logic
- Use `go test -cover ./...` for summary; `-coverprofile=c.out` for detail

```bash
go test -cover ./...
go test -coverprofile=c.out ./... && go tool cover -html=c.out
```

## References

See skill: `golang-testing` for database integration tests, test containers, and fuzz testing.
