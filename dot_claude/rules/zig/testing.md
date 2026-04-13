---
paths:
  - "**/*.zig"
---
# Zig Testing

> This file extends [common/testing.md](../common/testing.md) with Zig-specific content.

## Test Framework

Zig has a **built-in test runner** — no external framework needed. Use `std.testing` for assertions. Tests live in the same `.zig` source files they test (`test` blocks are excluded from non-test builds).

## Test Blocks

```zig
const std = @import("std");
const expect = std.testing.expect;
const expectEqual = std.testing.expectEqual;
const expectError = std.testing.expectError;

pub fn add(a: i32, b: i32) i32 {
    return a + b;
}

test "add returns sum of two integers" {
    try expectEqual(@as(i32, 5), add(2, 3));
}

test "add handles negative numbers" {
    try expectEqual(@as(i32, -1), add(2, -3));
}
```

## std.testing Assertions

```zig
// Value equality
try std.testing.expectEqual(expected, actual);

// Error returned
try std.testing.expectError(error.InvalidInput, parse("bad"));

// String equality
try std.testing.expectEqualStrings("hello", result);

// Slice equality
try std.testing.expectEqualSlices(u8, &expected, actual);

// Boolean
try std.testing.expect(condition);
```

## Test Allocator

Use `std.testing.allocator` to detect memory leaks — it fails the test if any allocation is not freed:

```zig
test "parse allocates and frees correctly" {
    const allocator = std.testing.allocator;
    const tokens = try parse(allocator, "hello world");
    defer allocator.free(tokens);

    try std.testing.expectEqual(@as(usize, 2), tokens.len);
}
```

The test allocator is leak-detecting by default — any unreleased allocation causes a test failure.

## Organizing Tests

```zig
// src/parser.zig — tests inline with implementation
pub const Parser = struct {
    // ...
};

test "Parser.init" { ... }
test "Parser.next token" { ... }
test "Parser.handles EOF" { ... }

// Refer to tests in other files from root
// src/root.zig
test {
    _ = @import("parser.zig");
    _ = @import("lexer.zig");
    _ = @import("ast.zig");
}
```

Using `_ = @import(...)` in a test block pulls all `test` declarations from that file into the test binary.

## build.zig Test Step

Wire tests into the build system (see patterns.md for full `build.zig`):

```zig
const unit_tests = b.addTest(.{
    .root_source_file = b.path("src/root.zig"),
    .target = target,
    .optimize = optimize,
});
const run_tests = b.addRunArtifact(unit_tests);
const test_step = b.step("test", "Run unit tests");
test_step.dependOn(&run_tests.step);
```

## Test Commands

```bash
zig test src/main.zig               # Test a single file
zig build test                      # Run test step from build.zig
zig build test -- --test-filter "parse"  # Run tests matching pattern
zig test src/main.zig --test-filter "add"
```

## References

See skill: `zig-testing` for comprehensive patterns including property testing, fuzz testing with `std.testing.fuzz`, and integration test setup.
