---
paths:
  - "**/*.ex"
  - "**/*.exs"
---
# Elixir Patterns

> This file extends [common/coding-style.md](../common/coding-style.md) with Elixir-specific content.

## GenServer

Standard GenServer structure with typed state:

```elixir
defmodule MyApp.Cache do
  use GenServer
  require Logger

  @type state :: %{entries: map(), ttl: pos_integer()}

  # Client API
  def start_link(opts \\ []) do
    GenServer.start_link(__MODULE__, opts, name: __MODULE__)
  end

  def get(key), do: GenServer.call(__MODULE__, {:get, key})
  def put(key, value), do: GenServer.cast(__MODULE__, {:put, key, value})

  # Server callbacks
  @impl true
  def init(opts) do
    {:ok, %{entries: %{}, ttl: Keyword.get(opts, :ttl, 60_000)}}
  end

  @impl true
  def handle_call({:get, key}, _from, state) do
    {:reply, Map.get(state.entries, key), state}
  end

  @impl true
  def handle_cast({:put, key, value}, state) do
    {:noreply, put_in(state, [:entries, key], value)}
  end
end
```

Always use `@impl true` to mark OTP callbacks — catches typos at compile time.

## Supervisor Trees

Define supervision strategy close to the supervised children:

```elixir
defmodule MyApp.Application do
  use Application

  @impl true
  def start(_type, _args) do
    children = [
      MyApp.Repo,
      {Phoenix.PubSub, name: MyApp.PubSub},
      MyAppWeb.Endpoint,
      {MyApp.Cache, ttl: 30_000},
    ]

    opts = [strategy: :one_for_one, name: MyApp.Supervisor]
    Supervisor.start_link(children, opts)
  end
end
```

## Phoenix Contexts

Contexts are the public API boundary — never reach into another context's schema:

```elixir
# lib/my_app/accounts.ex — the Accounts context
defmodule MyApp.Accounts do
  alias MyApp.Repo
  alias MyApp.Accounts.User

  def get_user!(id), do: Repo.get!(User, id)

  def create_user(attrs) do
    %User{}
    |> User.changeset(attrs)
    |> Repo.insert()
  end

  def update_user(%User{} = user, attrs) do
    user
    |> User.changeset(attrs)
    |> Repo.update()
  end
end
```

Controllers call context functions — never call `Repo` directly from a controller.

## Ecto Changesets

Validate data at the changeset level:

```elixir
defmodule MyApp.Accounts.User do
  use Ecto.Schema
  import Ecto.Changeset

  schema "users" do
    field :email, :string
    field :name, :string
    field :password, :string, virtual: true
    field :hashed_password, :string
    timestamps()
  end

  def changeset(user, attrs) do
    user
    |> cast(attrs, [:email, :name, :password])
    |> validate_required([:email, :name])
    |> validate_format(:email, ~r/^[^\s]+@[^\s]+\.[^\s]+$/)
    |> validate_length(:password, min: 8)
    |> unique_constraint(:email)
    |> hash_password()
  end

  defp hash_password(changeset) do
    case get_change(changeset, :password) do
      nil -> changeset
      password -> put_change(changeset, :hashed_password, Bcrypt.hash_pwd_salt(password))
    end
  end
end
```

## Behaviours

Define contracts between modules using `@behaviour` and `@callback`:

```elixir
defmodule MyApp.Notifier do
  @callback send(recipient :: String.t(), message :: String.t()) :: :ok | {:error, term()}

  def send(notifier_module, recipient, message) do
    notifier_module.send(recipient, message)
  end
end

defmodule MyApp.EmailNotifier do
  @behaviour MyApp.Notifier

  @impl MyApp.Notifier
  def send(recipient, message) do
    # send email...
    :ok
  end
end
```

## References

See skill: `elixir-patterns` for comprehensive OTP patterns, LiveView, Broadway pipelines, and distributed system patterns.
