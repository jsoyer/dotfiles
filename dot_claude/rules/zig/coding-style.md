---
paths:
  - "**/*.zig"
---
# Zig Coding Style

> This file extends [common/coding-style.md](../common/coding-style.md) with Zig-specific content.

## Formatting

- **zig fmt** for enforcement — always run `zig fmt src/` before committing
- 4-space indent (zig fmt enforced)
- Max line width: 100 characters
- No trailing whitespace; blank line between top-level declarations

## Naming Conventions

```zig
// snake_case: functions, variables, fields, namespaces
fn compute_checksum(data: []const u8) u32 { ... }
const max_retries = 3;

// PascalCase: types, structs, enums, unions, error sets
const ConnectionState = enum { idle, connecting, connected };
const ParseError = error{ InvalidInput, UnexpectedEof };

// SCREAMING_SNAKE_CASE: comptime constants acting as config
const MAX_BUFFER_SIZE = 4096;
```

## Explicit Allocators — No Hidden Allocation

Every function that allocates must accept an `Allocator` parameter. Never allocate globally:

```zig
// GOOD — caller controls memory
pub fn parse(allocator: std.mem.Allocator, input: []const u8) ![]Token {
    var tokens = std.ArrayList(Token).init(allocator);
    errdefer tokens.deinit();
    // ... fill tokens ...
    return tokens.toOwnedSlice();
}

// BAD — hidden global allocation
var global_arena = std.heap.ArenaAllocator.init(std.heap.page_allocator);
pub fn parse(input: []const u8) ![]Token { ... }
```

## Error Unions and Error Handling

Use `!T` return types; propagate with `try`; handle with `catch`:

```zig
pub fn read_config(path: []const u8) !Config {
    const file = try std.fs.cwd().openFile(path, .{});
    defer file.close();
    const content = try file.readToEndAlloc(allocator, 1_048_576);
    defer allocator.free(content);
    return try std.json.parseFromSlice(Config, allocator, content, .{});
}

// Handling specific errors
const result = read_config("config.json") catch |err| switch (err) {
    error.FileNotFound => return default_config,
    else => return err,
};
```

## No Hidden Control Flow

Zig is explicit — no operator overloading, no implicit casts, no exceptions:

- Use `defer` for cleanup (runs at scope exit, even on error)
- Use `errdefer` for cleanup only on error paths
- Integer overflow is safety-checked in debug; use `+%`, `-%` for wrapping arithmetic

```zig
pub fn process(allocator: std.mem.Allocator, data: []const u8) !Result {
    const buf = try allocator.alloc(u8, data.len * 2);
    errdefer allocator.free(buf);  // free only if we return an error
    defer allocator.free(buf);     // always free on normal return
    // ...
}
```

## Comptime

Use `comptime` for zero-cost generics and compile-time computation:

```zig
// Generic container via comptime type parameter
fn Stack(comptime T: type) type {
    return struct {
        items: []T,
        len: usize,

        pub fn push(self: *@This(), item: T) void { ... }
        pub fn pop(self: *@This()) ?T { ... }
    };
}

const IntStack = Stack(i32);
```

## References

See skill: `zig-patterns` for comprehensive idioms including allocators, tagged unions, comptime generics, and C interop.
