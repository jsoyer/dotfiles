---
paths:
  - "**/*.hs"
---
# Haskell Patterns

> This file extends [common/coding-style.md](../common/coding-style.md) with Haskell-specific content.

## Typeclasses

Define behaviour via typeclasses; derive standard instances automatically:

```haskell
class Describable a where
  describe :: a -> Text

data Shape = Circle Double | Rectangle Double Double
  deriving (Show, Eq)

instance Describable Shape where
  describe (Circle r)      = "circle with radius " <> T.pack (show r)
  describe (Rectangle w h) = "rectangle " <> T.pack (show w) <> "x" <> T.pack (show h)
```

## Monads and the MTL Stack

Use the MTL style for composable effects:

```haskell
type AppM = ReaderT Config (ExceptT AppError IO)

runApp :: Config -> AppM a -> IO (Either AppError a)
runApp cfg action = runExceptT (runReaderT action cfg)

fetchUser :: UserId -> AppM User
fetchUser uid = do
  db <- asks configDb
  liftIO (DB.findUser db uid) >>= maybe (throwError NotFound) pure
```

## Newtype Deriving

Use `newtype` for type-safe wrappers; derive instances cheaply:

```haskell
newtype UserId = UserId { unUserId :: Int }
  deriving (Show, Eq, Ord, FromJSON, ToJSON)

newtype Email = Email { unEmail :: Text }
  deriving (Show, Eq, Hashable)
```

## Lens for Deep Updates

Use `lens` / `optics` for nested record updates without manual boilerplate:

```haskell
import Control.Lens

data User = User { _name :: Text, _address :: Address }
  deriving Show
makeLenses ''User

data Address = Address { _city :: Text }
  deriving Show
makeLenses ''Address

-- Deep update without lens: User { _address = ((_address u) { _city = "Paris" }) }
-- With lens:
moveToCity :: Text -> User -> User
moveToCity c = address . city .~ c
```

## Smart Constructors

Hide data constructors; expose validated smart constructors:

```haskell
module Domain.Email (Email, mkEmail, emailText) where

newtype Email = Email Text  -- constructor not exported

mkEmail :: Text -> Either Text Email
mkEmail t
  | T.isInfixOf "@" t = Right (Email t)
  | otherwise         = Left "invalid email"

emailText :: Email -> Text
emailText (Email t) = t
```

## References

See skill: `haskell-patterns` for comprehensive functional patterns.
