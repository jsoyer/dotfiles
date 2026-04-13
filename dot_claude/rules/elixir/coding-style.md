---
paths:
  - "**/*.ex"
  - "**/*.exs"
---
# Elixir Coding Style

> This file extends [common/coding-style.md](../common/coding-style.md) with Elixir-specific content.

## Formatting

- **mix format** for enforcement — always run before committing (configured in `.formatter.exs`)
- 2-space indent
- Max line width: 98 characters (mix format default)
- **Credo** for linting: `mix credo --strict`

## Pipe Operator

Prefer pipelines for data transformations — one operation per line:

```elixir
# GOOD — clear data flow
def process_users(users) do
  users
  |> Enum.filter(&(&1.active))
  |> Enum.map(&normalize_email/1)
  |> Enum.sort_by(& &1.name)
end

# BAD — nested calls obscure order of operations
def process_users(users) do
  Enum.sort_by(Enum.map(Enum.filter(users, &(&1.active)), &normalize_email/1), & &1.name)
end
```

## Pattern Matching

Use pattern matching in function heads instead of conditionals:

```elixir
# GOOD — function clauses as dispatch
def handle_response({:ok, %{status: 200, body: body}}), do: {:ok, parse(body)}
def handle_response({:ok, %{status: 404}}), do: {:error, :not_found}
def handle_response({:ok, %{status: status}}), do: {:error, {:unexpected_status, status}}
def handle_response({:error, reason}), do: {:error, {:http_error, reason}}

# BAD — cond/case where function heads would be clearer
def handle_response(result) do
  case result do
    {:ok, %{status: 200, body: body}} -> {:ok, parse(body)}
    # ...
  end
end
```

## with Blocks

Use `with` for sequential operations that may fail, avoiding nested `case`:

```elixir
def create_account(params) do
  with {:ok, validated} <- validate(params),
       {:ok, user} <- Repo.insert(User.changeset(validated)),
       {:ok, _} <- send_welcome_email(user) do
    {:ok, user}
  else
    {:error, %Ecto.Changeset{} = cs} -> {:error, {:validation, cs}}
    {:error, :email_failed} -> {:ok, user}  # non-fatal
    error -> error
  end
end
```

## Documentation and Specs

Document all public functions with `@doc` and `@spec`:

```elixir
@doc """
Calculates the compound interest for a principal over time.

## Examples

    iex> Finance.compound_interest(1000, 0.05, 3)
    1157.625

"""
@spec compound_interest(number(), float(), pos_integer()) :: float()
def compound_interest(principal, rate, years) do
  principal * :math.pow(1 + rate, years)
end
```

## Immutability

All Elixir data is immutable — embrace it:

- Rebind variables explicitly rather than assuming mutation
- Use `Map.put/3`, `Map.update!/3`, `Keyword.put/3` for "updates" (returns new structure)
- Never rely on destructive updates — there are none

## References

See skill: `elixir-patterns` for comprehensive patterns including OTP, Phoenix, and Ecto.
