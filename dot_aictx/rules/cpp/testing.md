---
paths:
  - "**/*.cpp"
  - "**/*.hpp"
  - "**/*_test.cpp"
  - "**/*Test.cpp"
---
# C++ Testing

> This file extends [common/testing.md](../common/testing.md) with C++-specific content.

## Test Framework

- **Google Test** (GTest) + **Google Mock** (GMock) — most widely adopted
- **Catch2** as an alternative with expressive BDD-style macros
- **Google Benchmark** for micro-benchmarks
- Run with AddressSanitizer and UndefinedBehaviorSanitizer in CI

## Test Organization

```text
src/
├── orders/
│   ├── order_service.cpp
│   └── order_service.hpp
tests/
├── orders/
│   └── order_service_test.cpp
└── mocks/
    └── mock_order_repository.hpp
CMakeLists.txt
```

## GTest Unit Test Pattern

```cpp
#include <gtest/gtest.h>
#include "orders/order_service.hpp"
#include "mocks/mock_order_repository.hpp"

class OrderServiceTest : public ::testing::Test {
protected:
    MockOrderRepository mock_repo_;
    OrderService svc_{&mock_repo_};
};

TEST_F(OrderServiceTest, ReturnsNulloptWhenNotFound) {
    EXPECT_CALL(mock_repo_, FindById(testing::_))
        .WillOnce(testing::Return(std::nullopt));

    auto result = svc_.GetOrder("unknown");
    EXPECT_FALSE(result.has_value());
}

TEST_F(OrderServiceTest, ThrowsOnEmptyId) {
    EXPECT_THROW(svc_.GetOrder(""), std::invalid_argument);
}
```

## GMock Interface and Mock

```cpp
// Interface in production code
class OrderRepository {
public:
    virtual ~OrderRepository() = default;
    virtual std::optional<Order> FindById(std::string_view id) const = 0;
};

// Mock in test directory
class MockOrderRepository : public OrderRepository {
public:
    MOCK_METHOD(std::optional<Order>, FindById, (std::string_view id), (const, override));
};
```

## Parameterized Tests

```cpp
class ValidateEmailTest : public testing::TestWithParam<std::pair<std::string, bool>> {};

TEST_P(ValidateEmailTest, ChecksFormat) {
    auto [email, expected] = GetParam();
    EXPECT_EQ(expected, IsValidEmail(email));
}

INSTANTIATE_TEST_SUITE_P(EmailCases, ValidateEmailTest, testing::Values(
    std::make_pair("a@b.com", true),
    std::make_pair("not-email", false),
    std::make_pair("", false)
));
```

## Catch2 Style (alternative)

```cpp
#include <catch2/catch_test_macros.hpp>

TEST_CASE("OrderService", "[orders]") {
    SECTION("returns nullopt when order not found") {
        // ...
        REQUIRE(!result.has_value());
    }
}
```

## References

See skill: `cpp-testing` for property-based testing with RapidCheck and benchmark patterns.
