---
paths:
  - "**/*.hs"
  - "**/*.cabal"
---
# Haskell Coding Style

> This file extends [common/coding-style.md](../common/coding-style.md) with Haskell-specific content.

## Formatting

- **ormolu** or **fourmolu** for formatting — run before committing
- **HLint** for lints — address all suggestions or add explicit ignores
- 2-space indent; max line width 80-100 characters
- One module per file; module name matches file path

```bash
ormolu --mode inplace src/**/*.hs
hlint src/
```

## Type Signatures

Always provide explicit type signatures for top-level definitions:

```haskell
-- GOOD — explicit signature aids readability and catches errors early
wordsCount :: Text -> Int
wordsCount = length . T.words

-- BAD — relying on inference at top level
wordsCount t = length (T.words t)
```

## Do-Notation and Where Clauses

Use `do`-notation for sequential effects; extract helpers with `where`:

```haskell
loadConfig :: FilePath -> IO Config
loadConfig path = do
  content <- TIO.readFile path
  case Aeson.decode (TL.encodeUtf8 content) of
    Nothing  -> throwIO (ParseError path)
    Just cfg -> pure cfg

parseField :: Object -> Text -> Parser Int
parseField obj key = obj .: key
  where
    -- where clause for local helpers
```

## Naming

- `camelCase` for functions and variables
- `PascalCase` for types, constructors, type classes
- `_unused` prefix for intentionally unused bindings
- Avoid single-letter names except for well-known idioms (`f`, `g` for functions; `xs` for lists)

## Imports

Prefer explicit import lists to prevent namespace pollution:

```haskell
import Data.Map.Strict (Map)
import qualified Data.Map.Strict as Map
import Data.Text (Text)
import qualified Data.Text as T
```

## References

See skill: `haskell-patterns` for monads, typeclasses, and lens usage.
