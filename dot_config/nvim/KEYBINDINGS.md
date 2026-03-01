# Neovim Keybindings Documentation

> Comprehensive guide to all custom keybindings in this Neovim configuration

**Leader key:** `Space`

## 📑 Table of Contents

1. [Mode Switching](#mode-switching)
2. [Buffer Navigation](#buffer-navigation)
3. [Window/Split Management](#windowsplit-management)
4. [File Operations](#file-operations)
5. [Text Editing](#text-editing)
6. [Search & Navigation](#search--navigation)
7. [Visual Mode](#visual-mode)
8. [Terminal Mode](#terminal-mode)
9. [Diagnostics & Quickfix](#diagnostics--quickfix)
10. [Toggle Options](#toggle-options)
11. [Language Specific](#language-specific)

---

## Mode Switching

### Exit Insert Mode
```vim
jj          " Exit insert mode (double j)
jk          " Exit insert mode (alternative)
```

### Exit Terminal Mode
```vim
<Esc><Esc>  " Exit terminal mode
```

---

## Buffer Navigation

### Next/Previous Buffer (Multiple Options)

**Recommended - Tab-like navigation:**
```vim
Tab         " Next buffer ⭐ EASIEST
Shift+Tab   " Previous buffer ⭐ EASIEST
```

**Alternative - Home row:**
```vim
H           " Previous buffer ⚡ FAST
L           " Next buffer ⚡ FAST
```

**Alternative - Explicit:**
```vim
<leader>bh  " Previous buffer (b=buffer, h=left)
<leader>bl  " Next buffer (b=buffer, l=right)
```

**Alternative - Browser-style:**
```vim
<C-Tab>     " Next buffer (may not work in all terminals)
<C-S-Tab>   " Previous buffer (may not work in all terminals)
```

### Jump to Buffer
```vim
<leader>bj  " First buffer (b=buffer, j=jump start)
<leader>bk  " Last buffer (b=buffer, k=jump end)
<leader>1   " Go to buffer 1
<leader>2   " Go to buffer 2
...
<leader>9   " Go to buffer 9
```

### Buffer Management
```vim
<leader>x   " Close current buffer ⭐ RECOMMENDED
<leader>X   " Force close buffer (ignore unsaved changes)
<leader>bd  " Delete buffer (alternative)
<leader>bD  " Force delete buffer (alternative)
<leader>bn  " New buffer
<leader>bo  " Close all other buffers (keep current only)
<leader>ba  " Delete all buffers except current (alternative)
```

---

## Window/Split Management

### Create Splits (Multiple Options)

**Recommended - Mnemonics:**
```vim
<leader>sv  " Split vertical ⭐ (s=split, v=vertical)
<leader>sh  " Split horizontal ⭐ (s=split, h=horizontal)
```

**Alternative - Visual:**
```vim
<leader>|   " Split vertical (visual: vertical bar)
<leader>-   " Split horizontal (visual: horizontal line)
```

**Alternative - Traditional Vim:**
```vim
<C-w>v      " Split vertical (Vim standard enhanced)
<C-w>s      " Split horizontal (Vim standard enhanced)
```

### Navigate Between Splits
```vim
<C-h>       " Go to left split ⭐ STANDARD
<C-j>       " Go to down split ⭐ STANDARD
<C-k>       " Go to up split ⭐ STANDARD
<C-l>       " Go to right split ⭐ STANDARD
```

**Terminal mode (same keys):**
```vim
<C-h>       " Go to left split (from terminal)
<C-j>       " Go to down split (from terminal)
<C-k>       " Go to up split (from terminal)
<C-l>       " Go to right split (from terminal)
```

### Resize Splits
```vim
<C-Up>      " Increase height by 2
<C-Down>    " Decrease height by 2
<C-Left>    " Decrease width by 2
<C-Right>   " Increase width by 2
<C-w>,      " Decrease width by 10
<C-w>.      " Increase width by 10
<leader>s=  " Equalize split sizes
```

### Close Splits
```vim
<leader>sx  " Close current split (s=split, x=close)
<leader>so  " Close all other splits (s=split, o=only)
<C-w>x      " Close split (alternative)
```

---

## File Operations

### Save
```vim
<leader>w   " Save current file
<leader>W   " Force save (override readonly)
<leader>fs  " Save file (alternative)
<leader>fS  " Save all files
```

### New File
```vim
<leader>fn  " New file in new buffer
```

---

## Text Editing

### Line Movement
```vim
<A-j>       " Move current line down (Alt+j)
<A-k>       " Move current line up (Alt+k)
```

**Visual mode:**
```vim
<A-j>       " Move selected lines down
<A-k>       " Move selected lines up
```

### Navigation Shortcuts
```vim
E           " End of line (instead of $)
B           " Beginning of line (instead of ^)
```

### Join Lines
```vim
J           " Join lines (cursor stays in place)
```

### Indenting (Visual mode)
```vim
<           " Indent left (stays in visual mode)
>           " Indent right (stays in visual mode)
```

### Better Paste (Visual mode)
```vim
p           " Paste without yanking replaced text
```

### Word Wrap Navigation
```vim
j           " Move down (wrap-aware)
k           " Move up (wrap-aware)
```

### Select All
```vim
<C-a>       " Select entire file
```

### Undo Breakpoints
```vim
,           " Create undo breakpoint (insert mode)
.           " Create undo breakpoint (insert mode)
!           " Create undo breakpoint (insert mode)
?           " Create undo breakpoint (insert mode)
```

---

## Search & Navigation

### Search
```vim
n           " Next search result (centered)
N           " Previous search result (centered)
```

### Clear Search Highlight
```vim
<Esc>       " Clear search highlight
<leader><space>  " Clear search highlight (alternative)
```

---

## Visual Mode

### Indenting
```vim
<           " Indent left (stays in visual mode)
>           " Indent right (stays in visual mode)
```

### Line Navigation
```vim
E           " End of line
B           " Beginning of line
```

### Move Selection
```vim
<A-j>       " Move selection down
<A-k>       " Move selection up
```

### Paste
```vim
p           " Paste without yanking replaced text
```

---

## Terminal Mode

### Exit Terminal
```vim
<Esc><Esc>  " Exit terminal mode to normal mode
```

### Navigate to Other Windows
```vim
<C-h>       " Go to left window
<C-j>       " Go to lower window
<C-k>       " Go to upper window
<C-l>       " Go to right window
```

---

## Diagnostics & Quickfix

### Diagnostics Navigation
```vim
[d          " Previous diagnostic
]d          " Next diagnostic
[e          " Previous error
]e          " Next error
```

### Quickfix List
```vim
[q          " Previous quickfix item
]q          " Next quickfix item
```

### Location List
```vim
[l          " Previous location item
]l          " Next location item
```

---

## Toggle Options

### Toggle Settings
```vim
<leader>ts  " Toggle spell check
<leader>tw  " Toggle line wrap
<leader>tr  " Toggle relative line numbers
<leader>tt  " Toggle transparency
<leader>tW  " Toggle Twilight (focus mode)
```

---

## Language Specific

### Go
```vim
<leader>ge  " Add if err boilerplate (Go)
```

---

## Command Mode Navigation

### Cursor Movement
```vim
<C-a>       " Jump to start of line (command mode)
<C-e>       " Jump to end of line (command mode)
```

---

## Disabled Keybindings

### Space in Normal/Visual Mode
```vim
<Space>     " Disabled (used as leader key)
```

---

## Quick Reference by Use Case

### Most Common Operations

**Daily workflow:**
```vim
Tab/S-Tab       " Navigate buffers (EASIEST)
<leader>sv/sh   " Create splits (MNEMONICS)
<C-h/j/k/l>     " Navigate splits (STANDARD)
<leader>x       " Close buffer
<leader>w       " Save file
```

**Editing:**
```vim
<A-j/k>         " Move lines up/down
E / B           " End/Beginning of line
<leader><space> " Clear search highlight
```

**Buffer management:**
```vim
Tab/S-Tab       " Next/Previous buffer
<leader>x       " Close buffer
<leader>bo      " Close other buffers
<leader>1-9     " Jump to buffer N
```

**Split management:**
```vim
<leader>sv/sh   " Create vertical/horizontal split
<C-h/j/k/l>     " Navigate between splits
<leader>sx      " Close current split
<leader>s=      " Equalize split sizes
```

---

## Philosophy Behind Multiple Bindings

This configuration provides **multiple ways** to achieve the same goal:

### Buffer Navigation
- **Tab/Shift+Tab**: Intuitive (like browser tabs)
- **H/L**: Fast (home row positioning)
- **\<leader\>bh/bl**: Explicit (self-documenting)

### Split Creation
- **\<leader\>sv/sh**: Mnemonic (easy to remember)
- **\<leader\>|-**: Visual (matches split direction)
- **\<C-w\>v/s**: Traditional (Vim muscle memory)

**Use what feels natural to you!** All options are kept for maximum flexibility.

---

## Tips & Tricks

### 1. Buffer Navigation
The **Tab/Shift+Tab** bindings are the most intuitive for most users coming from modern editors.

### 2. Split Workflow
Recommended workflow:
1. Create split: `<leader>sv` or `<leader>sh`
2. Navigate: `<C-h/j/k/l>`
3. Resize if needed: `<C-arrows>`
4. Close when done: `<leader>sx`

### 3. Quick Buffer Jumping
Use `<leader>1-9` to jump directly to a buffer by number (visible in status line).

### 4. Focus on Current Buffer
Use `<leader>bo` to close all other buffers and focus on the current one.

### 5. Line Movement
`<A-j>` and `<A-k>` work in both normal and visual mode, making it easy to reorganize code.

### 6. Centered Search
Search results (`n`/`N`) automatically center on screen for better visibility.

### 7. Terminal Integration
Terminal mode has the same `<C-h/j/k/l>` navigation, making split management consistent.

---

## LazyVim Default Keybindings

This configuration is based on **LazyVim**, which includes many additional keybindings. For a complete reference:

- [LazyVim Default Keymaps](https://github.com/LazyVim/LazyVim/blob/main/lua/lazyvim/config/keymaps.lua)
- Press `<leader>?` in Neovim to see all keybindings (via which-key)

---

## Theme Consistency

This Neovim configuration uses **Catppuccin Mocha** theme, matching:
- ✅ Tmux
- ✅ Starship
- ✅ FZF
- ✅ Bat
- ✅ Eza
- ✅ Ghostty

---

**Last updated:** 2025-12-26
**Configuration:** LazyVim with custom keybindings
**Theme:** Catppuccin Mocha
