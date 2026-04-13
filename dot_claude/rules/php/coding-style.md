---
paths:
  - "**/*.php"
  - "**/*.phtml"
---
# PHP Coding Style

> This file extends [common/coding-style.md](../common/coding-style.md) with PHP-specific content.

## Standards

- Follow **PSR-12** (extended coding style) — enforced by **PHP-CS-Fixer** or **PHP_CodeSniffer**
- Use **PHPStan** (level 8+) or **Psalm** for static analysis — treat errors as CI failures
- PHP 8.2+ required for all new code; use 8.3+ for new projects

## Naming

- `camelCase` for methods and variables; `PascalCase` for classes and interfaces
- `SCREAMING_SNAKE_CASE` for constants
- Prefix interfaces with `Interface` or use no prefix (Laravel style) — pick one per project
- Boolean methods: `isActive()`, `hasPermission()`, `canSubmit()`

## Modern PHP (8.2+)

Use modern features — avoid PHP 5/7 patterns:

```php
// GOOD — readonly class (PHP 8.2)
readonly class Money {
    public function __construct(
        public readonly float $amount,
        public readonly string $currency,
    ) {}
}

// GOOD — enums (PHP 8.1)
enum OrderStatus: string {
    case Pending  = 'pending';
    case Paid     = 'paid';
    case Shipped  = 'shipped';
}

// GOOD — match expression
$label = match($status) {
    OrderStatus::Pending => 'Awaiting payment',
    OrderStatus::Paid    => 'Processing',
    OrderStatus::Shipped => 'On its way',
};
```

## Type Declarations

- Declare types on ALL function parameters, return types, and class properties
- Use union types for multiple possible types: `int|string`
- Use `?Type` for nullable; avoid `mixed` except at system boundaries

```php
// GOOD — fully typed
function findUser(string $id): ?User {
    return $this->repo->find($id);
}

// BAD — untyped
function findUser($id) { /* ... */ }
```

## Immutability

PHP lacks built-in immutability, but apply these patterns:
- Use `readonly` properties (PHP 8.1) and `readonly` classes (PHP 8.2)
- Return new instances from transformation methods — never mutate `$this`

```php
readonly class Temperature {
    public function __construct(public readonly float $celsius) {}

    public function toCelsius(): self { return $this; }
    public function toFahrenheit(): self { return new self($this->celsius * 9/5 + 32); }
}
```

## References

See skill: `php-patterns` for Laravel, Symfony, and repository patterns.
