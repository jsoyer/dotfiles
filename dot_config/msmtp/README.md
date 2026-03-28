# msmtp Configuration

SMTP relay for sending emails. Routes mail through Gmail's SMTP server.

## Files

- `private_config.tmpl` — SMTP configuration (password via 1Password CLI)

## Details

- **Tool**: msmtp
- **Platform**: Linux, macOS
- **Purpose**: Send emails via Gmail SMTP
- **Theme**: N/A (backend tool)

## Configuration

- **Host**: smtp.gmail.com (port 587, TLS)
- **From**: Configured email address from templates
- **Password**: Fetched at runtime via `op read` (1Password)
- **Logs**: `$XDG_STATE_HOME/msmtp/msmtp.log`

## Usage

```bash
# Via neomutt (automatic)
msmtp < message.txt   # Direct mail send
```

## Dependencies

- 1Password CLI (`op`) for password lookup
- neomutt (email client)
- Gmail account with app password if 2FA enabled
