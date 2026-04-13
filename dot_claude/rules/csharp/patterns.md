---
paths:
  - "**/*.cs"
---
# C# Patterns

> This file extends [common/coding-style.md](../common/coding-style.md) with C#-specific content.

## Repository Pattern with EF Core

```csharp
public interface IOrderRepository {
    Task<Order?> FindByIdAsync(Guid id, CancellationToken ct = default);
    Task<IReadOnlyList<Order>> FindByCustomerAsync(Guid customerId, CancellationToken ct = default);
    Task<Order> SaveAsync(Order order, CancellationToken ct = default);
}

class EfOrderRepository(AppDbContext db) : IOrderRepository {
    public Task<Order?> FindByIdAsync(Guid id, CancellationToken ct) =>
        db.Orders.FirstOrDefaultAsync(o => o.Id == id, ct);

    public async Task<Order> SaveAsync(Order order, CancellationToken ct) {
        db.Orders.Update(order);
        await db.SaveChangesAsync(ct);
        return order;
    }
}
```

## CQRS with MediatR

Separate reads from writes using command/query objects:

```csharp
// Command
record PlaceOrderCommand(Guid CustomerId, IReadOnlyList<OrderLine> Lines)
    : IRequest<OrderId>;

class PlaceOrderHandler(IOrderRepository repo) : IRequestHandler<PlaceOrderCommand, OrderId> {
    public async Task<OrderId> Handle(PlaceOrderCommand cmd, CancellationToken ct) {
        var order = Order.Create(cmd.CustomerId, cmd.Lines);
        await repo.SaveAsync(order, ct);
        return order.Id;
    }
}
```

## Options Pattern for Configuration

```csharp
public class EmailOptions {
    public const string Section = "Email";
    public string SmtpHost { get; init; } = "";
    public int Port { get; init; } = 587;
}

// In Program.cs
builder.Services.Configure<EmailOptions>(
    builder.Configuration.GetSection(EmailOptions.Section));

// Inject with IOptions<T>
class EmailService(IOptions<EmailOptions> opts) {
    private readonly EmailOptions _opts = opts.Value;
}
```

## Result Pattern with OneOf / Error Union

```csharp
using OneOf;

record NotFound(string Resource);
record ValidationFailed(IReadOnlyList<string> Errors);

OneOf<Order, NotFound, ValidationFailed> PlaceOrder(CreateOrderRequest req) {
    if (!req.IsValid(out var errors)) return new ValidationFailed(errors);
    var order = _repo.Save(Order.From(req));
    return order ?? (OneOf<Order, NotFound, ValidationFailed>)new NotFound("Order");
}
```

## Global Exception Middleware

```csharp
app.UseExceptionHandler(builder => builder.Run(async ctx => {
    var ex = ctx.Features.Get<IExceptionHandlerFeature>()?.Error;
    var (status, message) = ex switch {
        NotFoundException => (404, ex.Message),
        ValidationException => (422, ex.Message),
        _ => (500, "An unexpected error occurred")
    };
    ctx.Response.StatusCode = status;
    await ctx.Response.WriteAsJsonAsync(new { error = message });
}));
```

## References

See skill: `csharp-patterns` for Minimal API, Blazor, and background service patterns.
