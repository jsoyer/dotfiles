---
paths:
  - "**/*.dart"
  - "**/pubspec.yaml"
---
# Dart Coding Style

> This file extends [common/coding-style.md](../common/coding-style.md) with Dart-specific content.

## Formatting

- **dart format** for enforcement — run before committing
- **dart analyze** for lints — address all warnings
- 2-space indent; max line width 80 characters

```bash
dart format .
dart analyze
```

## Null Safety

Always prefer non-nullable types; assert nullability at boundaries:

```dart
// GOOD — non-nullable, clear contract
String greet(String name) => 'Hello, $name!';

// GOOD — nullable only where genuinely optional
String? findUser(int id) => _cache[id];

// Use null-aware operators, not explicit null checks
final display = user?.displayName ?? 'Anonymous';
```

## Cascade Notation

Use cascades (`..`) for fluent object mutation:

```dart
final paint = Paint()
  ..color = Colors.blue
  ..strokeWidth = 2.0
  ..style = PaintingStyle.stroke;
```

## Extension Methods

Extend existing types without subclassing:

```dart
extension StringExtensions on String {
  bool get isValidEmail => contains('@') && contains('.');
  String toTitleCase() =>
      split(' ').map((w) => w[0].toUpperCase() + w.substring(1)).join(' ');
}

// Usage
'hello world'.toTitleCase(); // 'Hello World'
'user@example.com'.isValidEmail; // true
```

## Naming

- `lowerCamelCase` for variables, functions, parameters
- `UpperCamelCase` for classes, enums, typedefs
- `lowercase_with_underscores` for library and file names
- Private members prefixed with `_`

## References

See skill: `dart-patterns` for Flutter widgets, BLoC, and Riverpod patterns.
