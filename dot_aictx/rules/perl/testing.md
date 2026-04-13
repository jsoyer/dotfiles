---
paths:
  - "**/*.pl"
  - "**/*.pm"
  - "**/*.t"
---
# Perl Testing

> This file extends [common/testing.md](../common/testing.md) with Perl-specific content.

## Test Framework

- **Test2::V0** for all tests — modern, expressive, replaces `Test::More`
- **Test::Moo** for Moo class testing
- **Test::MockObject** or **Test::MockModule** for mocking
- Tests live in `t/` directory; each file is a TAP producer

## Test Organization

```text
lib/
└── My/App/
    ├── User.pm
    └── OrderService.pm
t/
├── unit/
│   ├── user.t
│   └── order_service.t
└── integration/
    └── api.t
```

## Test2::V0 Pattern

```perl
use Test2::V0;
use My::App::OrderService;

my $mock_repo = mock 'My::App::Repository::Order' => (
    override => [
        find_by_id => sub { undef },
    ],
);

subtest 'get_order returns undef when not found' => sub {
    my $repo = My::App::Repository::Order->new(dbh => mock_dbh());
    my $svc  = My::App::OrderService->new(repo => $repo);
    is $svc->get_order('missing-id'), undef, 'returns undef';
};

subtest 'get_order throws on empty id' => sub {
    my $svc = My::App::OrderService->new(repo => mock_repo());
    ok dies { $svc->get_order('') }, 'dies on empty id';
    like $@, qr/id is required/i, 'error message mentions id';
};

done_testing;
```

## Table-Driven Tests

```perl
use Test2::V0;

my @cases = (
    ['alice@example.com', 1, 'valid email'],
    ['not-an-email',      0, 'missing at sign'],
    ['',                  0, 'empty string'],
);

for my $case (@cases) {
    my ($email, $expected, $label) = @$case;
    is EmailValidator::is_valid($email), $expected, $label;
}

done_testing;
```

## Mocking with Test::MockObject

```perl
use Test::MockObject;

my $mock_ua = Test::MockObject->new;
$mock_ua->mock('get', sub {
    my ($self, $url) = @_;
    return HTTP::Response->new(200, 'OK', [], '{"id":"1"}');
});
```

## Running Tests

```bash
prove -lv t/           # run all tests verbose
prove -lv t/unit/      # unit tests only
cover -test            # run tests with Devel::Cover coverage report
```

## Coverage

- Use **Devel::Cover** for coverage analysis; target 80%+ on library code
- Exclude auto-generated code and POD sections

```bash
cover -test -ignore_re='t/' && cover -report html
```

## References

See skill: `perl-testing` for mock DBI, Plack test, and property-based testing with Test::LectroTest.
