---
paths:
  - "**/*.cpp"
  - "**/*.hpp"
  - "**/*.h"
---
# C++ Patterns

> This file extends [common/coding-style.md](../common/coding-style.md) with C++-specific content.

## RAII Resource Wrapper

Encapsulate any resource (file, socket, lock) in a class with RAII semantics:

```cpp
template<typename T, auto Deleter>
class UniqueHandle {
    T handle_;
public:
    explicit UniqueHandle(T h) : handle_(h) {}
    ~UniqueHandle() { if (handle_) Deleter(handle_); }
    UniqueHandle(const UniqueHandle&) = delete;
    UniqueHandle(UniqueHandle&& o) noexcept : handle_(o.handle_) { o.handle_ = {}; }
    T get() const { return handle_; }
};
// Usage: UniqueHandle<FILE*, fclose> f(std::fopen("x.txt", "r"));
```

## Concepts for Template Constraints (C++20)

Replace `std::enable_if` with readable concepts:

```cpp
template<typename T>
concept Numeric = std::integral<T> || std::floating_point<T>;

template<Numeric T>
T clamp(T value, T lo, T hi) {
    return std::max(lo, std::min(hi, value));
}
```

## Type-Safe IDs with Strong Typedefs

```cpp
template<typename Tag>
class StrongId {
    std::string value_;
public:
    explicit StrongId(std::string v) : value_(std::move(v)) {}
    const std::string& value() const { return value_; }
    bool operator==(const StrongId&) const = default;
};

using UserId  = StrongId<struct UserTag>;
using OrderId = StrongId<struct OrderTag>;
// UserId and OrderId are distinct types — can't be accidentally swapped
```

## Visitor Pattern with std::variant

Prefer `std::visit` + `std::variant` over virtual dispatch for closed type sets:

```cpp
using Shape = std::variant<Circle, Rectangle, Triangle>;

double area(const Shape& s) {
    return std::visit([](const auto& shape) {
        return shape.area(); // resolved at compile time
    }, s);
}
```

## Factory Function over Constructor

Return `std::optional` or `std::expected` from factories for validation:

```cpp
class Email {
    std::string address_;
    explicit Email(std::string a) : address_(std::move(a)) {}
public:
    static std::optional<Email> parse(std::string_view s) {
        if (s.find('@') == std::string_view::npos) return std::nullopt;
        return Email{std::string(s)};
    }
    const std::string& value() const { return address_; }
};
```

## References

See skill: `cpp-patterns` for move semantics, coroutines (C++20), and concurrency with `std::jthread`.
