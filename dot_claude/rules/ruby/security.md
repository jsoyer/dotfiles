---
paths:
  - "**/*.rb"
  - "app/**/*.rb"
  - "config/**/*.rb"
---
# Ruby Security

> This file extends [common/security.md](../common/security.md) with Ruby-specific content.

## Strong Parameters

Always use strong parameters in Rails controllers to prevent mass assignment:

```ruby
# GOOD — whitelist permitted attributes
def user_params
  params.require(:user).permit(:name, :email, :role)
end

# BAD — never use params.permit! or User.new(params[:user])
def user_params_bad
  params[:user]  # mass assignment vulnerability
end
```

## SQL Injection Prevention

Use ActiveRecord parameterized queries — never interpolate user input into SQL:

```ruby
# BAD — SQL injection
User.where("name = '#{params[:name]}'")

# GOOD — parameterized query
User.where(name: params[:name])
User.where("name = ?", params[:name])
User.where("name = :name", name: params[:name])
```

## CSRF Protection

Ensure CSRF protection is enabled (Rails default) and never disable it for non-API endpoints:

```ruby
# application_controller.rb
class ApplicationController < ActionController::Base
  protect_from_forgery with: :exception  # default — keep it
end

# API controllers using token auth may skip CSRF:
class Api::BaseController < ActionController::API
  # ActionController::API does not include CSRF protection by default
end
```

## Secrets Management

Use Rails credentials or environment variables — never hardcode secrets:

```ruby
# GOOD — Rails encrypted credentials
payment_key = Rails.application.credentials.payment_api_key!

# GOOD — environment variable with early validation
STRIPE_KEY = ENV.fetch("STRIPE_SECRET_KEY") { raise "STRIPE_SECRET_KEY not set" }
```

## Input Sanitization

Sanitize HTML output; use `html_escape` or Rails' automatic escaping in views:

```ruby
# In views, Rails auto-escapes by default:
<%= user.bio %>           # safe — escaped
<%= raw user.bio %>       # DANGEROUS — only for trusted HTML
<%= sanitize user.bio %>  # safe — strips unsafe tags
```

## References

See skill: `security-review` for full Rails security checklist and Brakeman usage.
