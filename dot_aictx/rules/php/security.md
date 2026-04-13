---
paths:
  - "**/*.php"
---
# PHP Security

> This file extends [common/security.md](../common/security.md) with PHP-specific content.

## SQL Injection

- Always use PDO prepared statements or an ORM with parameter binding
- Never concatenate user input into SQL strings

```php
// BAD — SQL injection
$users = $db->query("SELECT * FROM users WHERE email = '$email'");

// GOOD — PDO prepared statement
$stmt = $db->prepare("SELECT * FROM users WHERE email = ?");
$stmt->execute([$email]);

// GOOD — Eloquent (Laravel)
$user = User::where('email', $email)->first();
```

## Output Escaping

- Use `htmlspecialchars($value, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8')` for all HTML output
- In Laravel Blade, `{{ $var }}` escapes automatically; `{!! $var !!}` does NOT — avoid unless sanitized
- Never echo raw user input into HTML, JS, CSS, or URL contexts

```php
// GOOD — escaped output
echo htmlspecialchars($userName, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');

// BAD — raw output
echo $userName;
```

## File Upload Security

- Validate MIME type server-side with `finfo_file()` — never trust the `$_FILES['type']` field
- Store uploaded files outside the web root or in object storage
- Generate random filenames — never use the original filename

```php
$finfo = new \finfo(FILEINFO_MIME_TYPE);
$mime  = $finfo->file($_FILES['upload']['tmp_name']);
if (!in_array($mime, ['image/jpeg', 'image/png'], true)) {
    throw new \InvalidArgumentException("Disallowed file type: $mime");
}
```

## Session Security

- Regenerate session ID after authentication: `session_regenerate_id(true)`
- Set `session.cookie_httponly = 1`, `session.cookie_secure = 1`, `session.cookie_samesite = Strict`
- Store session secrets in environment variables, not in the session itself

## Environment Secrets

- Use `$_ENV` or a `.env` library (vlucas/phpdotenv) — never hardcode secrets
- Validate required variables at bootstrap time and fail with a clear error

```php
$apiKey = $_ENV['PAYMENT_API_KEY']
    ?? throw new \RuntimeException('PAYMENT_API_KEY env var is required');
```

## References

See skill: `security-review` for general security checklists.
