---
paths:
  - "**/*.cpp"
  - "**/*.cxx"
  - "**/*.cc"
  - "**/*.hpp"
  - "**/*.h"
---
# C++ Coding Style

> This file extends [common/coding-style.md](../common/coding-style.md) with C++-specific content.

## Formatting

- **clang-format** with Google or LLVM style — enforced via pre-commit and CI
- 2-space indent (Google) or 4-space (LLVM) — pick one project-wide
- Max line length: 100 characters

## Modern C++ (C++20+)

Prefer modern idioms — avoid raw C patterns:

```cpp
// GOOD — range-based for with const ref
for (const auto& user : users) { process(user); }

// GOOD — structured bindings
auto [status, message] = validate(input);

// GOOD — std::span instead of pointer+length
void process(std::span<const std::byte> data);
```

## Naming

- `snake_case` for functions, variables, member variables, namespaces
- `PascalCase` for classes, structs, enums, concepts
- `kConstantName` or `SCREAMING_SNAKE_CASE` for constants
- Member variables: `name_` with trailing underscore (Google style)

## Memory Safety

Avoid raw owning pointers:
- Use `std::unique_ptr<T>` for exclusive ownership
- Use `std::shared_ptr<T>` only when shared ownership is required
- Pass by reference or raw non-owning pointer for non-owning access
- Use `std::vector`, `std::string`, `std::array` — never raw `new[]`/`delete[]`

```cpp
// GOOD — ownership expressed in types
auto cache = std::make_unique<ImageCache>(max_size);
void render(const ImageCache& cache); // borrows, does not own

// BAD — raw owning pointer
ImageCache* cache = new ImageCache(max_size);
```

## Error Handling

- Prefer exceptions for exceptional conditions in application code
- Use `std::expected<T, E>` (C++23) or `std::optional<T>` for expected-failure operations
- Never use `errno` or return codes in new C++ code unless interoperating with C

```cpp
// C++23 — expected for operations that commonly fail
std::expected<Config, std::string> load_config(std::string_view path);

auto cfg = load_config("app.toml");
if (!cfg) { log_error(cfg.error()); return 1; }
```

## RAII Everywhere

Every resource acquisition must have a corresponding release via a destructor:

```cpp
class FileHandle {
public:
    explicit FileHandle(std::string_view path)
        : fp_(std::fopen(path.data(), "r")) {
        if (!fp_) throw std::system_error(errno, std::generic_category());
    }
    ~FileHandle() { if (fp_) std::fclose(fp_); }
    // delete copy; allow move
    FileHandle(const FileHandle&) = delete;
    FileHandle& operator=(const FileHandle&) = delete;
    FILE* get() const { return fp_; }
private:
    FILE* fp_;
};
```

## References

See skill: `cpp-patterns` for templates, concepts, and concurrency idioms.
