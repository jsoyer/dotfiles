---
paths:
  - "**/*.pl"
  - "**/*.pm"
---
# Perl Patterns

> This file extends [common/coding-style.md](../common/coding-style.md) with Perl-specific content.

## Repository Pattern with Moo

```perl
package My::App::Repository::User;
use Moo;
use DBI;

has dbh => (is => 'ro', required => 1);

sub find_by_id {
    my ($self, $id) = @_;
    my $row = $self->dbh->selectrow_hashref(
        'SELECT * FROM users WHERE id = ?', undef, $id,
    );
    return $row ? My::App::User->new(%$row) : undef;
}

sub save {
    my ($self, $user) = @_;
    $self->dbh->do(
        'INSERT INTO users (id, email) VALUES (?, ?) ON CONFLICT (id) DO UPDATE SET email = ?',
        undef, $user->id, $user->email, $user->email,
    );
    return $user;
}
```

## Dispatch Tables

Use hashrefs of coderefs instead of long if/elsif chains:

```perl
my %handler_for = (
    create => \&handle_create,
    update => \&handle_update,
    delete => \&handle_delete,
);

my $action = $request->param('action');
my $handler = $handler_for{$action}
    or die "Unknown action: $action\n";
$handler->($request, $response);
```

## Chained Method Calls (Fluent Interface)

Return `$self` from setters to allow chaining:

```perl
package My::App::QueryBuilder;
use Moo;

has _table  => (is => 'rw');
has _where  => (is => 'rw', default => sub { [] });
has _limit  => (is => 'rw', default => 100);

sub from  { my ($s, $t) = @_; $s->_table($t); $s }
sub where { my ($s, $c) = @_; push @{$s->_where}, $c; $s }
sub limit { my ($s, $n) = @_; $s->_limit($n); $s }

# My::App::QueryBuilder->new->from('users')->where('active = 1')->limit(10)->build;
```

## Regular Expression Best Practices

```perl
# GOOD — named captures, extended mode for clarity
if ($line =~ m{
    (?<year>  \d{4}) -
    (?<month> \d{2}) -
    (?<day>   \d{2})
}x) {
    my ($y, $m, $d) = @+{qw(year month day)};
}

# GOOD — compile regex outside loops
my $email_re = qr/\A[\w.+-]+\@[\w-]+\.[a-z]{2,}\z/i;
for my $address (@addresses) {
    warn "invalid: $address" unless $address =~ $email_re;
}
```

## Moose Roles for Mixins

```perl
package My::Role::Timestamps;
use Moose::Role;
use Types::Standard qw(Str);

has created_at => (is => 'ro', isa => Str, default => sub { scalar localtime });
has updated_at => (is => 'rw', isa => Str);

before 'save' => sub { $_[0]->updated_at(scalar localtime) };
```

## References

See skill: `perl-patterns` for DBI advanced patterns, Plack middleware, and Moo/Moose type constraints.
