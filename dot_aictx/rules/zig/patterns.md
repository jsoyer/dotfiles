---
paths:
  - "**/*.zig"
---
# Zig Patterns

> This file extends [common/coding-style.md](../common/coding-style.md) with Zig-specific content.

## Allocator Pattern

Pass allocators through the call chain — choose the right allocator for the job:

```zig
// Application entry point — choose allocator based on workload
pub fn main() !void {
    // Long-lived data: GPA with leak detection in debug
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    // Request-scoped data: arena (free everything at once)
    var arena = std.heap.ArenaAllocator.init(allocator);
    defer arena.deinit();
    const request_alloc = arena.allocator();

    try handle_request(request_alloc);
}
```

## Tagged Unions

Model state machines and variant types with exhaustive matching:

```zig
const Value = union(enum) {
    int: i64,
    float: f64,
    boolean: bool,
    string: []const u8,
    null_value,

    pub fn type_name(self: Value) []const u8 {
        return switch (self) {
            .int => "int",
            .float => "float",
            .boolean => "bool",
            .string => "string",
            .null_value => "null",
        };
    }
};
```

The compiler rejects non-exhaustive switches — no forgotten cases.

## Comptime Generics

Build type-safe, zero-overhead containers and algorithms:

```zig
fn SortedList(comptime T: type, comptime less_than: fn (T, T) bool) type {
    return struct {
        const Self = @This();
        items: std.ArrayList(T),

        pub fn init(allocator: std.mem.Allocator) Self {
            return .{ .items = std.ArrayList(T).init(allocator) };
        }

        pub fn insert(self: *Self, item: T) !void {
            const idx = blk: {
                for (self.items.items, 0..) |existing, i| {
                    if (less_than(item, existing)) break :blk i;
                }
                break :blk self.items.items.len;
            };
            try self.items.insert(idx, item);
        }
    };
}
```

## Sentinel-Terminated Slices

Use `[*:0]const u8` for C-compatible null-terminated strings; `[:0]const u8` for known-length:

```zig
// Passing to C APIs
extern fn puts(s: [*:0]const u8) c_int;

const greeting: [:0]const u8 = "Hello";
_ = puts(greeting.ptr);

// Converting Zig string literals (already sentinel-terminated)
const path = "/etc/hosts";  // type: *const [10:0]u8
```

## Interface via Tagged Unions or Comptime Dispatch

Zig has no interfaces — use comptime duck typing or tagged unions:

```zig
// Comptime duck typing (static dispatch, zero overhead)
fn write_all(writer: anytype, data: []const u8) !void {
    try writer.writeAll(data);
}

// Works with any type that has writeAll — checked at compile time
try write_all(std.io.getStdOut().writer(), "hello\n");
try write_all(buffer_writer, "hello\n");
```

## build.zig Structure

Organize build steps clearly:

```zig
pub fn build(b: *std.Build) void {
    const target = b.standardTargetOptions(.{});
    const optimize = b.standardOptimizeOption(.{});

    const lib = b.addStaticLibrary(.{
        .name = "mylib",
        .root_source_file = b.path("src/root.zig"),
        .target = target,
        .optimize = optimize,
    });
    b.installArtifact(lib);

    const unit_tests = b.addTest(.{
        .root_source_file = b.path("src/root.zig"),
        .target = target,
        .optimize = optimize,
    });
    const run_tests = b.addRunArtifact(unit_tests);
    const test_step = b.step("test", "Run unit tests");
    test_step.dependOn(&run_tests.step);
}
```

## References

See skill: `zig-patterns` for comprehensive patterns including C interop, async I/O, SIMD, and cross-compilation.
