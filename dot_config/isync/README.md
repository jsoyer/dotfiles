# isync (mbsync) Configuration

Email synchronization client for IMAP mailboxes. Syncs Gmail to local Maildir for offline access.

## Files

- `private_mbsyncrc.tmpl` — Main configuration (password via 1Password CLI)

## Details

- **Tool**: isync / mbsync
- **Platform**: Linux, macOS
- **Purpose**: Sync Gmail IMAP to local Maildir
- **Theme**: N/A (backend tool)

## Configuration

- Syncs to `$XDG_DATA_HOME/mail/gmail/` (local Maildir storage)
- Gmail account credentials fetched at runtime via `op read` (1Password)
- Excludes: All Mail, Important, Spam folders
- TLS on port 993 (IMAPS)

## Usage

```bash
mbsync gmail          # Sync Gmail account
mbsync -a             # Sync all accounts
```

## Dependencies

- 1Password CLI (`op`) for password lookup
- neomutt (email client)
- notmuch (optional, for virtual folder indexing)
