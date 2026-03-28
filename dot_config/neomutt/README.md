# NeoMutt Configuration

Terminal-based email client with Vim keybindings and modern features.

## Files

- `neomuttrc.tmpl` — Main configuration
- `accounts/gmail.muttrc.tmpl` — Gmail account setup
- `colors/catppuccin-mocha.muttrc` — Color theme (Catppuccin Mocha)
- `mailcap` — MIME type handlers (HTML, attachments)

## Details

- **Tool**: NeoMutt
- **Platform**: Linux, macOS
- **Purpose**: Terminal mail client (IMAP/SMTP)
- **Theme**: Catppuccin Mocha

## Features

- Vim-style keybindings (hjkl, gg/G navigation)
- Notmuch integration for virtual folders (Unread, Today, Week, Flagged)
- Sidebar with mailbox stats
- Thread-based sorting
- HTML email auto-viewing
- Markdown/text editor (nvim)

## Key Bindings

- `Ctrl-b/f` — Previous/next in sidebar
- `Ctrl-o` — Open sidebar folder
- `Space` — Collapse/expand thread
- `Tab` — Sync mailbox
- `X` — Search with Notmuch
- `\\` — Create virtual folder from query

## Usage

```bash
neomutt                    # Start client
neomutt -f imap://gmail/   # Open folder
```

## Dependencies

- mbsync (isync) for IMAP sync
- msmtp for SMTP sending
- notmuch for virtual folders
- nvim for compose editor
