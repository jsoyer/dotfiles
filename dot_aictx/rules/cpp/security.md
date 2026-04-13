---
paths:
  - "**/*.cpp"
  - "**/*.hpp"
  - "**/*.h"
---
# C++ Security

> This file extends [common/security.md](../common/security.md) with C++-specific content.

## Buffer Overflow Prevention

- Use `std::string`, `std::vector`, `std::array` — never raw C arrays with pointer arithmetic
- Never use `strcpy`, `strcat`, `gets`, `sprintf` — use their bounds-checked alternatives or `std::string`
- When bounds-checked access is needed, use `.at()` which throws on out-of-bounds

```cpp
// BAD — buffer overflow risk
char buf[64];
strcpy(buf, user_input); // undefined behavior if > 63 chars

// GOOD — automatic memory management
std::string result = user_input; // safe regardless of length

// GOOD — bounds-checked access
std::vector<int> v = {1, 2, 3};
int val = v.at(index); // throws std::out_of_range instead of UB
```

## Integer Overflow

- Use `std::numeric_limits<T>::max()` checks before arithmetic on untrusted values
- For cryptographic or security-sensitive sizes, use `size_t` and check against `SIZE_MAX`
- Enable `-fsanitize=undefined,integer` in debug builds to catch overflows early

```cpp
// GOOD — checked addition
size_t safe_add(size_t a, size_t b) {
    if (b > SIZE_MAX - a) throw std::overflow_error("size overflow");
    return a + b;
}
```

## Use-After-Free and Dangling Pointers

- Prefer smart pointers — they prevent manual lifetime errors
- Never return a reference or pointer to a local variable
- Use AddressSanitizer (`-fsanitize=address`) in CI to catch UAF and heap errors

```cpp
// BAD — dangling reference to local
const std::string& get_name() {
    std::string name = compute_name();
    return name; // UB — name destroyed on return
}

// GOOD — return by value
std::string get_name() { return compute_name(); }
```

## Input Validation

- Never trust external input sizes — validate before allocating
- Sanitize strings intended for OS commands; prefer `execv` family over `system()`
- Validate numeric ranges explicitly before use in security-sensitive calculations

## Compiler Hardening Flags

Enable for all production builds:

```cmake
target_compile_options(myapp PRIVATE
    -D_FORTIFY_SOURCE=2
    -fstack-protector-strong
    -Wformat -Wformat-security
)
target_link_options(myapp PRIVATE -Wl,-z,relro,-z,now)
```

## References

See skill: `security-review` for general security checklists.
See skill: `cpp-patterns` for safe concurrency and memory ownership patterns.
