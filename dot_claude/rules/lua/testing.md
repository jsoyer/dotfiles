---
paths:
  - "**/*.lua"
---
# Lua Testing

> This file extends [common/testing.md](../common/testing.md) with Lua-specific content.

## Test Framework

- **busted** for standalone Lua projects (`luarocks install busted`)
- **plenary.nvim** (`plenary.busted` / `plenary.test_harness`) for Neovim plugins
- Run Neovim tests headlessly: `nvim --headless -c "PlenaryBustedDirectory tests/ {minimal_init = 'tests/minimal_init.lua'}"`

## busted: describe/it Blocks

```lua
-- spec/calculator_spec.lua
local Calculator = require("calculator")

describe("Calculator", function()
  local calc

  before_each(function()
    calc = Calculator.new()
  end)

  describe("add", function()
    it("returns sum of two numbers", function()
      assert.equals(5, calc:add(2, 3))
    end)

    it("handles negative numbers", function()
      assert.equals(-1, calc:add(2, -3))
    end)
  end)

  describe("divide", function()
    it("returns nil and error on division by zero", function()
      local result, err = calc:divide(10, 0)
      assert.is_nil(result)
      assert.matches("division by zero", err)
    end)
  end)
end)
```

## Mocking with busted

busted provides `spy`, `stub`, and `mock` built in:

```lua
describe("notifier", function()
  it("calls send once per recipient", function()
    local mailer = require("mailer")
    local send_spy = spy.on(mailer, "send")

    local notifier = require("notifier")
    notifier.notify({ "a@example.com", "b@example.com" }, "hello")

    assert.spy(send_spy).was_called(2)
    assert.spy(send_spy).was_called_with("a@example.com", "hello")
  end)
end)
```

## Neovim Testing with plenary

```lua
-- tests/minimal_init.lua — bootstrap for headless test runs
vim.cmd("set rtp+=.")
vim.cmd("set rtp+=" .. vim.fn.stdpath("data") .. "/site/pack/vendor/start/plenary.nvim")
vim.cmd("runtime! plugin/plenary.vim")

-- tests/myplugin_spec.lua
local assert = require("luassert")

describe("myplugin", function()
  before_each(function()
    -- Reset plugin state between tests
    package.loaded["myplugin"] = nil
    package.loaded["myplugin.config"] = nil
  end)

  it("setup merges user options with defaults", function()
    local plugin = require("myplugin")
    plugin.setup({ timeout = 1000 })
    assert.equals(1000, plugin.options.timeout)
    assert.is_true(plugin.options.enabled)  -- default preserved
  end)
end)
```

## Test Commands

```bash
busted                          # Run all specs (auto-discovers spec/ and *_spec.lua)
busted spec/calculator_spec.lua # Single file
busted --output=TAP             # TAP format for CI
luacov && busted --coverage     # Coverage with luacov
```

## Coverage

- Use **luacov** for coverage: `busted --coverage` generates `luacov.stats.out`
- Generate report: `luacov` → reads `luacov.stats.out` → produces `luacov.report.out`
- Target 80%+ line coverage for business logic

## References

See skill: `lua-testing` for comprehensive patterns including async testing, Neovim buffer fixtures, and coverage reporting.
