---
paths:
  - "**/*.lua"
---
# Lua Coding Style

> This file extends [common/coding-style.md](../common/coding-style.md) with Lua-specific content.

## Formatting

- **stylua** for enforcement — always run `stylua .` before committing
- 2-space indent (stylua default for Neovim ecosystem), 4-space for standalone projects
- Max line width: 120 characters
- Trailing commas in multi-line tables and function calls

## Locals by Default

Variables are global unless declared `local` — always use `local`:

```lua
-- GOOD — explicit local scope
local M = {}
local config = { timeout = 30 }

local function helper(x)
  return x * 2
end

-- BAD — implicit global pollutes _G
config = { timeout = 30 }
function helper(x) return x * 2 end
```

## Naming

Follow Lua community conventions:
- `snake_case` for functions, variables, modules
- `PascalCase` for class-like tables
- `SCREAMING_SNAKE_CASE` for module-level constants
- Module tables named `M` (Neovim plugin convention) or the module name

## String Handling

- Prefer single quotes for short strings; double quotes when string contains single quotes
- Use `string.format` for interpolation — never concatenate in hot loops
- Use `[[...]]` long strings for multiline or strings with special characters

```lua
-- GOOD
local msg = string.format("Hello, %s! You have %d messages.", name, count)
local sql = [[
  SELECT * FROM users
  WHERE active = 1
]]

-- BAD — concatenation in loop is O(n^2)
local result = ""
for _, v in ipairs(items) do
  result = result .. v  -- avoid
end
```

## Error Handling

Lua uses `nil, err` returns and `pcall`/`xpcall` for protected calls:

```lua
-- GOOD — nil + error string pattern
local function read_file(path)
  local f, err = io.open(path, "r")
  if not f then
    return nil, string.format("failed to open %s: %s", path, err)
  end
  local content = f:read("*a")
  f:close()
  return content
end

-- GOOD — pcall for third-party or untrusted code
local ok, result = pcall(json.decode, raw)
if not ok then
  return nil, "invalid JSON: " .. result
end
```

## LuaJIT / Lua 5.4 Compatibility

- Use `local var <const> = value` (Lua 5.4) for true constants when targeting 5.4+
- Avoid `goto` except for cleanup patterns in pre-5.4 code
- Prefer `ipairs` / `pairs` over manual index loops; use `table.move` for bulk copies
- LuaJIT: keep hot paths free of `table.insert`/`table.remove` in tight loops — use numeric indexing

## References

See skill: `lua-patterns` for comprehensive idioms, metatables, and coroutine patterns.
