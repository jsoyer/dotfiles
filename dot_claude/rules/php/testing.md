---
paths:
  - "**/*.php"
  - "**/*Test.php"
  - "**/*Spec.php"
---
# PHP Testing

> This file extends [common/testing.md](../common/testing.md) with PHP-specific content.

## Test Framework

- **PHPUnit 11+** for unit and integration tests
- **Mockery** or PHPUnit's built-in `createMock()` for test doubles
- **Pest PHP** as an expressive alternative to PHPUnit (same engine, better DX)
- **Laravel's testing helpers** for HTTP, database, queue, and mail assertions

## Test Organization

```text
tests/
├── Unit/
│   └── Orders/
│       ├── OrderServiceTest.php
│       └── OrderTest.php
├── Feature/
│   └── Orders/
│       └── PlaceOrderTest.php
└── TestCase.php
```

## PHPUnit Unit Test

```php
use PHPUnit\Framework\TestCase;
use PHPUnit\Framework\Attributes\Test;

final class OrderServiceTest extends TestCase {
    private OrderRepository $repo;
    private OrderService $svc;

    protected function setUp(): void {
        $this->repo = $this->createMock(OrderRepository::class);
        $this->svc  = new OrderService($this->repo);
    }

    #[Test]
    public function returns_null_when_order_not_found(): void {
        $this->repo->method('findById')->willReturn(null);
        $this->assertNull($this->svc->getOrder('unknown-id'));
    }

    #[Test]
    public function throws_on_empty_id(): void {
        $this->expectException(\InvalidArgumentException::class);
        $this->svc->getOrder('');
    }
}
```

## Pest Style (alternative)

```php
it('returns null when order not found', function () {
    $repo = Mockery::mock(OrderRepository::class);
    $repo->shouldReceive('findById')->andReturn(null);
    $svc = new OrderService($repo);
    expect($svc->getOrder('x'))->toBeNull();
});
```

## Data Providers (Parameterized Tests)

```php
use PHPUnit\Framework\Attributes\DataProvider;

#[DataProvider('emailProvider')]
public function test_validates_email(string $email, bool $expected): void {
    $this->assertSame($expected, EmailValidator::isValid($email));
}

public static function emailProvider(): array {
    return [
        'valid email'   => ['alice@example.com', true],
        'missing at'    => ['notanemail', false],
        'empty string'  => ['', false],
    ];
}
```

## Coverage

- Target 80%+ with Xdebug or PCOV: `./vendor/bin/phpunit --coverage-html coverage/`
- Enforce minimum coverage in CI: `--coverage-clover=coverage.xml --min-coverage=80`

## References

See skill: `php-testing` for Laravel HTTP tests, database factories, and API testing patterns.
