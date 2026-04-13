---
paths:
  - "**/*.rb"
  - "app/**/*.rb"
---
# Ruby Patterns

> This file extends [common/coding-style.md](../common/coding-style.md) with Ruby-specific content.

## Service Objects

Encapsulate business logic in plain Ruby objects:

```ruby
# app/services/create_order.rb
class CreateOrder
  def initialize(user:, items:)
    @user  = user
    @items = items
  end

  def call
    order = Order.create!(user: @user, items: @items)
    OrderMailer.confirmation(order).deliver_later
    order
  rescue ActiveRecord::RecordInvalid => e
    Result.failure(e.message)
  end
end

# Usage
CreateOrder.new(user: current_user, items: cart.items).call
```

## Rails Concerns

Extract shared model/controller behaviour into concerns:

```ruby
# app/models/concerns/auditable.rb
module Auditable
  extend ActiveSupport::Concern

  included do
    before_create :set_created_by
    before_update :set_updated_by
  end

  private

  def set_created_by = self.created_by_id = Current.user&.id
  def set_updated_by = self.updated_by_id = Current.user&.id
end

class Order < ApplicationRecord
  include Auditable
end
```

## ActiveRecord Scopes

Prefer named scopes over raw where clauses in application code:

```ruby
class Order < ApplicationRecord
  scope :active,    -> { where(status: :active) }
  scope :recent,    -> { order(created_at: :desc) }
  scope :for_user,  ->(user) { where(user: user) }

  # Chainable
  # Order.active.recent.for_user(current_user)
end
```

## Decorator Pattern (Draper)

Decorate models with presentation logic; keep models clean:

```ruby
class UserDecorator < Draper::Decorator
  delegate_all

  def full_name = "#{object.first_name} #{object.last_name}"
  def avatar_url = object.avatar.attached? ? object.avatar_url : "/default_avatar.png"
end
```

## References

See skill: `ruby-patterns` for comprehensive Rails patterns, background jobs, and API design.
