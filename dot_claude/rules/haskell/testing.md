---
paths:
  - "**/*.hs"
  - "**/test/**"
---
# Haskell Testing

> This file extends [common/testing.md](../common/testing.md) with Haskell-specific content.

## Test Frameworks

- **HSpec** — BDD-style unit and integration tests
- **QuickCheck** — property-based testing
- **tasty** — test runner composing HSpec, QuickCheck, and golden tests
- **tasty-hunit** — HUnit-style assertions inside tasty

## HSpec Unit Tests

```haskell
import Test.Hspec

spec :: Spec
spec = do
  describe "mkEmail" $ do
    it "accepts a valid email" $
      mkEmail "user@example.com" `shouldBe` Right (Email "user@example.com")
    it "rejects an email without @" $
      mkEmail "notanemail" `shouldSatisfy` isLeft
```

## QuickCheck Properties

```haskell
import Test.QuickCheck

prop_reverseInvolution :: [Int] -> Bool
prop_reverseInvolution xs = reverse (reverse xs) == xs

prop_sortIdempotent :: [Int] -> Bool
prop_sortIdempotent xs = sort (sort xs) == sort xs

-- Run standalone
main :: IO ()
main = do
  quickCheck prop_reverseInvolution
  quickCheck prop_sortIdempotent
```

## Tasty Composition

```haskell
import Test.Tasty
import Test.Tasty.HUnit
import Test.Tasty.QuickCheck

main :: IO ()
main = defaultMain $ testGroup "MyLib"
  [ testCase "unit: parses config" $ do
      cfg <- loadConfig "test/fixtures/config.json"
      configPort cfg @?= 8080
  , testProperty "prop: sort idempotent" prop_sortIdempotent
  ]
```

## Testing Commands

```bash
cabal test               # Run all tests
stack test               # Run all tests (Stack)
cabal test --test-show-details always   # Verbose output
```

## References

See skill: `haskell-testing` for golden tests, hedgehog, and async testing patterns.
