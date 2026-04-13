---
paths:
  - "**/*.php"
---
# PHP Patterns

> This file extends [common/coding-style.md](../common/coding-style.md) with PHP-specific content.

## Repository Pattern

```php
interface UserRepository {
    public function findById(string $id): ?User;
    /** @return list<User> */
    public function findAll(): array;
    public function save(User $user): User;
    public function delete(string $id): void;
}

final class EloquentUserRepository implements UserRepository {
    public function findById(string $id): ?User {
        return UserModel::find($id)?->toDomain();
    }
    public function save(User $user): User {
        $model = UserModel::updateOrCreate(['id' => $user->id], $user->toArray());
        return $model->toDomain();
    }
}
```

## Value Objects

```php
readonly class Email {
    public function __construct(public readonly string $value) {
        if (!filter_var($value, FILTER_VALIDATE_EMAIL)) {
            throw new \InvalidArgumentException("Invalid email: $value");
        }
    }
    public function __toString(): string { return $this->value; }
}
```

## Service Layer with Dependency Injection

```php
final class OrderService {
    public function __construct(
        private readonly OrderRepository $orders,
        private readonly PaymentGateway $payments,
        private readonly LoggerInterface $logger,
    ) {}

    public function place(CreateOrderRequest $request): Order {
        $order = Order::create($request->customerId, $request->lines);
        $this->payments->charge($order->total());
        $saved = $this->orders->save($order);
        $this->logger->info('Order placed', ['order_id' => $saved->id]);
        return $saved;
    }
}
```

## Pipeline Pattern for Request Processing

Inspired by Laravel's middleware pipeline:

```php
$result = array_reduce(
    array_reverse($middleware),
    fn ($carry, $fn) => fn ($input) => $fn($input, $carry),
    fn ($input) => $handler->handle($input),
)($request);
```

## Named Arguments for Clarity

```php
// GOOD — named arguments make intent obvious with many params
$user = new User(
    name:  'Alice',
    email: 'alice@example.com',
    role:  Role::Admin,
);
```

## References

See skill: `php-patterns` for Laravel Eloquent, Symfony DI, and event-driven patterns.
