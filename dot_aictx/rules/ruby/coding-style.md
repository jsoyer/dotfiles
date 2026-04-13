---
paths:
  - "**/*.rb"
  - "**/Gemfile"
  - "**/Rakefile"
---
# Ruby Coding Style

> This file extends [common/coding-style.md](../common/coding-style.md) with Ruby-specific content.

## Formatting

- **RuboCop** for linting and style enforcement — run before committing
- 2-space indent; max line length 120 characters
- Frozen string literals enabled at file top

```ruby
# frozen_string_literal: true

# .rubocop.yml
AllCops:
  NewCops: enable
  TargetRubyVersion: 3.2
```

## Blocks and Procs

Use `{}` for single-line blocks; `do...end` for multi-line:

```ruby
# GOOD — single-line with {}
active_users = users.select { |u| u.active? }

# GOOD — multi-line with do...end
results = records.map do |record|
  transformed = transform(record)
  validate!(transformed)
  transformed
end
```

## Symbols and Frozen Strings

Prefer symbols for hash keys; freeze string constants:

```ruby
# GOOD — symbol keys
user = { name: "Alice", role: :admin }

# GOOD — frozen constant
ROLES = %i[admin editor viewer].freeze
```

## Naming

- `snake_case` for methods and variables
- `PascalCase` for classes and modules
- `SCREAMING_SNAKE_CASE` for constants
- `?` suffix for predicate methods; `!` suffix for bang methods

## Method Length

Keep methods short (< 10 lines). Extract private methods for clarity:

```ruby
def process_order(order)
  validate_order!(order)
  charge_payment(order)
  fulfill_order(order)
end

private

def validate_order!(order)
  raise InvalidOrder unless order.items.any?
end
```

## References

See skill: `ruby-patterns` for Rails concerns, service objects, and ActiveRecord patterns.
