---
paths:
  - "**/*.rb"
  - "spec/**/*.rb"
  - "**/Gemfile"
---
# Ruby Testing

> This file extends [common/testing.md](../common/testing.md) with Ruby-specific content.

## Test Frameworks

- **RSpec** — describe/context/it BDD-style tests
- **FactoryBot** — test data factories
- **shoulda-matchers** — one-liner ActiveRecord/controller matchers
- **VCR** — record and replay HTTP interactions

## RSpec Structure

```ruby
RSpec.describe CreateOrder do
  describe "#call" do
    context "when items are present" do
      let(:user)  { create(:user) }
      let(:items) { create_list(:item, 2) }
      subject(:result) { described_class.new(user: user, items: items).call }

      it "creates an order" do
        expect { result }.to change(Order, :count).by(1)
      end

      it "returns the new order" do
        expect(result).to be_an(Order)
      end
    end

    context "when items are empty" do
      it "raises InvalidOrder" do
        expect { described_class.new(user: build(:user), items: []).call }
          .to raise_error(InvalidOrder)
      end
    end
  end
end
```

## FactoryBot Factories

```ruby
# spec/factories/users.rb
FactoryBot.define do
  factory :user do
    name  { Faker::Name.name }
    email { Faker::Internet.unique.email }
    role  { :viewer }

    trait :admin do
      role { :admin }
    end
  end
end

# Usage
create(:user)           # persisted
build(:user, :admin)    # not persisted, admin role
```

## Shoulda Matchers

```ruby
RSpec.describe User, type: :model do
  it { is_expected.to validate_presence_of(:email) }
  it { is_expected.to validate_uniqueness_of(:email) }
  it { is_expected.to belong_to(:organisation) }
  it { is_expected.to have_many(:orders).dependent(:destroy) }
end
```

## VCR for HTTP

```ruby
RSpec.describe PaymentGateway do
  it "charges successfully", vcr: { cassette_name: "payment/success" } do
    result = described_class.charge(amount: 100, token: "tok_visa")
    expect(result).to be_success
  end
end
```

## Testing Commands

```bash
bundle exec rspec                    # All tests
bundle exec rspec spec/models/       # Models only
bundle exec rspec --format progress  # Compact output
bundle exec rspec --tag focus        # Run focused tests
```

## References

See skill: `ruby-testing` for system tests with Capybara, request specs, and parallel test setup.
