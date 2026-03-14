# Neovim Configuration - Plugin Organization

This Neovim configuration uses LazyVim and organizes plugins in a modular structure.

## Structure

```
lua/plugins/
├── ai.lua          # AI assistants (Codeium, Gen.nvim)
├── cmp.lua         # Completion (nvim-cmp)
├── coding.lua      # Coding tools (DAP, autopairs, comment, codesnap)
├── colorscheme.lua # Themes (Catppuccin, Dracula)
├── editor.lua      # Editing tools (Harpoon, snacks_explorer, Trouble, Todo)
├── git.lua         # Git (Neogit, Gitsigns, Fugitive, Worktree, Diffview)
├── go.lua          # Go development
├── lsp.lua         # LSP configuration
├── telescope.lua   # Fuzzy search (Telescope)
├── treesitter.lua  # Syntax parsing
├── ui.lua          # Interface (Lualine, Noice, Notify, Indent guides)
└── writing.lua     # Writing (Obsidian, Markdown, Zen mode, Twilight)
```

## Plugin Categories

### AI (ai.lua)
- **opencode.nvim** - OpenCode CLI integration (`<leader>ao` toggle, `<C-a>` ask)
- **copilot.lua** - GitHub Copilot ghost-text completions (`<M-l>` accept)
- **avante.nvim** - Cursor-style AI diff panel (Claude, OpenAI, Gemini)
- **minuet-ai.nvim** - Multi-provider as-you-type completions (Ollama)
- **codecompanion.nvim** - Multi-provider AI chat, inline, agents + ACP

### Completion (cmp.lua)
- **nvim-cmp** - Completion engine

### Coding (coding.lua)
- **nvim-autopairs** - Auto-close pairs
- **Comment.nvim** - Smart commenting
- **nvim-dap** - Debug Adapter Protocol
- **codesnap** - Code screenshots

### Git (git.lua)
- **Neogit** - Magit-like Git interface
- **Gitsigns** - Git gutter decorations
- **Fugitive** - Git commands
- **git-worktree** (polarmutex) - Worktree management (`<leader>gwl` list, `<leader>gwc` create)
- **Diffview** - Enhanced diff views

### Editor (editor.lua)
- **Harpoon** - Quick file navigation
- **snacks_explorer** - File explorer (via lazyvim.json extra)
- **goto-preview** - LSP preview
- **Trouble** - Diagnostics list
- **todo-comments** - TODO highlighting
- **vim-surround** - Surround manipulation
- **nvim-transparent** - Transparency toggle

### Go (go.lua)
- **go.nvim** - Go tooling
- **nvim-dap-go** - Go debugging

### LSP (lsp.lua)
- **Mason** - LSP manager
- **nvim-lspconfig** - LSP configuration
- **Fidget** - LSP progress

### Telescope (telescope.lua)
- **Telescope** - Fuzzy finder
- **telescope-fzf-native** - FZF extension
- **telescope-symbols** - Symbol search

### Treesitter (treesitter.lua)
- **nvim-treesitter** - Syntax parsing
- **nvim-treesitter-textobjects** - Text objects

### UI (ui.lua)
- **Lualine** - Status bar
- **indent-blankline** - Indentation guides
- **nvim-notify** - Notifications
- **Noice** - Enhanced messages/cmdline UI
- **nvim-web-devicons** - Icons

### Writing (writing.lua)
- **Obsidian.nvim** - Obsidian integration
- **render-markdown** - Markdown rendering
- **markdown-preview** - Markdown preview
- **Twilight** - Dims inactive code

## Optimizations

- **Lazy-loading** - Most plugins load on demand
- **Event-based loading** - Loads on events (InsertEnter, LazyFile, etc.)
- **Command-based loading** - Loads on first command call
- **Keymap-based loading** - Loads on first keybinding use

## Customization

To add a plugin:

1. Choose the appropriate file in `lua/plugins/`
2. Add your LazyVim spec
3. Use appropriate lazy-loading

Example:
```lua
{
  "author/plugin-name",
  event = "LazyFile",  -- or cmd, keys, ft, etc.
  opts = {},
  config = function(_, opts)
    require("plugin-name").setup(opts)
  end,
}
```

## Installation

After changes, restart Neovim:
```
nvim
```

Lazy.nvim will automatically install new plugins.

## Formatting

All files are formatted with Stylua:
```bash
stylua .
```

Configuration in `stylua.toml`:
- Indentation: 2 spaces
- Width: 120 columns
- Double quotes
