---
paths:
  - "**/*.cs"
  - "**/*Tests.cs"
  - "**/*Test.cs"
---
# C# Testing

> This file extends [common/testing.md](../common/testing.md) with C#-specific content.

## Test Framework

- **xUnit** for all tests — preferred over NUnit and MSTest for modern .NET
- **FluentAssertions** for readable, failure-descriptive assertions
- **Moq** or **NSubstitute** for mocking interfaces
- **Microsoft.AspNetCore.Mvc.Testing** (`WebApplicationFactory<T>`) for integration tests

## Test Organization

```text
MyApp/
├── src/
│   └── Orders/
│       └── OrderService.cs
└── tests/
    └── Orders.Tests/
        ├── OrderServiceTests.cs
        └── OrderControllerTests.cs
```

## Unit Test with Moq

```csharp
public class OrderServiceTests {
    private readonly Mock<IOrderRepository> _repo = new();
    private readonly OrderService _svc;

    public OrderServiceTests() => _svc = new OrderService(_repo.Object);

    [Fact]
    public async Task GetOrderAsync_ReturnsNull_WhenNotFound() {
        _repo.Setup(r => r.FindByIdAsync(It.IsAny<Guid>(), default))
             .ReturnsAsync((Order?)null);

        var result = await _svc.GetOrderAsync(Guid.NewGuid());

        result.Should().BeNull();
    }

    [Fact]
    public async Task GetOrderAsync_ThrowsArgumentException_WhenIdIsEmpty() {
        var act = () => _svc.GetOrderAsync(Guid.Empty);
        await act.Should().ThrowAsync<ArgumentException>();
    }
}
```

## Parameterized Tests

```csharp
[Theory]
[InlineData("alice@example.com", true)]
[InlineData("not-an-email", false)]
[InlineData("", false)]
public void IsValidEmail_ReturnsExpected(string email, bool expected) {
    EmailValidator.IsValid(email).Should().Be(expected);
}
```

## Integration Test with WebApplicationFactory

```csharp
public class OrderControllerTests : IClassFixture<WebApplicationFactory<Program>> {
    private readonly HttpClient _client;

    public OrderControllerTests(WebApplicationFactory<Program> factory)
        => _client = factory.CreateClient();

    [Fact]
    public async Task GetOrder_Returns404_WhenNotFound() {
        var response = await _client.GetAsync($"/orders/{Guid.NewGuid()}");
        response.StatusCode.Should().Be(HttpStatusCode.NotFound);
    }
}
```

## Coverage

- Use **coverlet** with `dotnet test --collect:"XPlat Code Coverage"`
- ReportGenerator for HTML reports; target 80%+ on business logic

```bash
dotnet test --collect:"XPlat Code Coverage"
reportgenerator -reports:"**/coverage.cobertura.xml" -targetdir:coverage-report
```

## References

See skill: `csharp-testing` for Testcontainers .NET, WireMock.Net, and Respawn database cleanup.
