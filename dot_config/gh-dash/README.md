# gh-dash Configuration

GitHub Dashboard TUI for viewing PRs, issues, and notifications in the terminal.

## Files

- `config.yml` — Dashboard layout, filters, keybindings, and theme

## Details

- **Tool**: gh-dash (GitHub CLI plugin)
- **Platform**: Linux, macOS
- **Purpose**: GitHub dashboard UI (PRs, issues, notifications)
- **Theme**: Snazzy theme (custom colors)

## Configuration

### Sections

- **PRs**: My PRs, Needs My Review, Involved
- **Issues**: My Issues, Assigned, Involved
- **Notifications**: All, Created, Participating, Mentioned, Review Requested, Assigned, Subscribed, Team Mentioned

### Keybindings

- `g` → lazygit (code review)
- `C` → OpenCode code-reviewer (PR review with AI)

### Layout

- PRs/Issues: repo (20px), author (15px), lines (15px), timestamps (5px)
- Notifications: reason-based filtering
- Compact table with separators
- 20-item default limits

### Theme

- **Text**: Primary (#F7F1FF), Secondary (#5AD4E6), Warning/Success colors
- **Border**: Mauve (#948AE3), Success green (#7BD88F)
- **Background**: Subtle selection (#535155)

## Usage

```bash
gh dash                 # Open dashboard
# Hotkeys visible in TUI
```

## Dependencies

- GitHub CLI (`gh`)
- gh-dash plugin
- lazygit (optional, for code review)
- OpenCode (optional, for AI review)
