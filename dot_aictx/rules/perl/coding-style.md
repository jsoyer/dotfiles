---
paths:
  - "**/*.pl"
  - "**/*.pm"
  - "**/*.t"
---
# Perl Coding Style

> This file extends [common/coding-style.md](../common/coding-style.md) with Perl-specific content.

## Mandatory Pragmas

Every file must start with:

```perl
use strict;
use warnings;
use utf8;
use open ':std', ':encoding(UTF-8)';
```

For modern Perl (5.36+), use `use v5.36;` which implies `strict`, `warnings`, and `utf8`.

## Formatting

- **perltidy** for consistent formatting — commit a `.perltidyrc`
- **Perl::Critic** (level 3+) for lint — treat fatal policies as CI failures
- 4-space indent; do not use tabs

## Naming

- `snake_case` for variables, functions, methods, modules within a namespace
- `PascalCase` for package (class) names: `My::App::UserService`
- `ALL_CAPS` for constants declared with `use constant` or `Readonly`
- Sigils communicate type: `$scalar`, `@array`, `%hash`, `&code`

## Object-Oriented Code

Use **Moo** (lighter) or **Moose** (full-featured) for all OOP — never bless hashref manually:

```perl
package My::App::User;
use Moo;
use Types::Standard qw(Str Int Bool);

has id    => (is => 'ro', isa => Str, required => 1);
has email => (is => 'ro', isa => Str, required => 1);
has active => (is => 'ro', isa => Bool, default => 1);

# Immutable by default with 'ro'; use 'rw' only when mutation is needed
```

## Error Handling

- Use `die` with an object for structured errors — not a bare string
- Catch with `eval { }` and inspect `$@` — or use **Try::Tiny** / **Feature::Compat::Try**

```perl
use Try::Tiny;

try {
    my $user = load_user($id);
} catch {
    if (ref $_ && $_->isa('My::Error::NotFound')) {
        warn "User $id not found";
    } else {
        die $_;  # re-throw unexpected errors
    }
};
```

## Subroutine Signatures (Perl 5.20+)

```perl
use feature 'signatures';
no warnings 'experimental::signatures';

sub greet ($name, $greeting = 'Hello') {
    return "$greeting, $name!";
}
```

## References

See skill: `perl-patterns` for Moose, DBI, and Dancer2/Mojolicious web patterns.
