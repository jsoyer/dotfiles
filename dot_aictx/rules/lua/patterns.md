---
paths:
  - "**/*.lua"
---
# Lua Patterns

> This file extends [common/coding-style.md](../common/coding-style.md) with Lua-specific content.

## Module Pattern

Use a local table `M` returned at end — the standard Lua module idiom:

```lua
local M = {}

local TIMEOUT = 5000  -- private constant

local function validate(input)  -- private helper
  return type(input) == "string" and #input > 0
end

function M.process(input)
  if not validate(input) then
    return nil, "invalid input"
  end
  return input:upper()
end

return M
```

## OOP via Metatables

```lua
local Animal = {}
Animal.__index = Animal

function Animal.new(name, sound)
  return setmetatable({ name = name, sound = sound }, Animal)
end

function Animal:speak()
  return string.format("%s says %s", self.name, self.sound)
end

-- Inheritance
local Dog = setmetatable({}, { __index = Animal })
Dog.__index = Dog

function Dog.new(name)
  local self = Animal.new(name, "woof")
  return setmetatable(self, Dog)
end

function Dog:fetch(item)
  return string.format("%s fetches the %s!", self.name, item)
end
```

## Coroutines

Use coroutines for cooperative multitasking and generators:

```lua
-- Generator pattern
local function range(from, to, step)
  step = step or 1
  return coroutine.wrap(function()
    for i = from, to, step do
      coroutine.yield(i)
    end
  end)
end

for n in range(1, 10, 2) do
  print(n)  -- 1, 3, 5, 7, 9
end
```

## Neovim Plugin Patterns

Standard structure for a Neovim plugin written in Lua:

```lua
-- lua/myplugin/init.lua
local M = {}
local config = require("myplugin.config")
local core = require("myplugin.core")

M.defaults = {
  enabled = true,
  timeout = 500,
}

function M.setup(opts)
  -- Merge user opts over defaults (never mutate defaults)
  M.options = vim.tbl_deep_extend("force", M.defaults, opts or {})
  config.apply(M.options)
  core.initialize()
end

return M
```

Use `vim.tbl_deep_extend("force", defaults, opts)` — never mutate the defaults table. Register autocommands and keymaps inside `setup()` so they only activate when the plugin is explicitly loaded.

## Lazy Evaluation with Closures

```lua
-- Memoize expensive computations
local function memoize(fn)
  local cache = {}
  return function(key)
    if cache[key] == nil then
      cache[key] = fn(key)
    end
    return cache[key]
  end
end

local expensive = memoize(function(n)
  -- simulate expensive work
  return n * n
end)
```

## References

See skill: `lua-patterns` for comprehensive patterns including metatables, coroutines, FFI (LuaJIT), and Neovim API usage.
