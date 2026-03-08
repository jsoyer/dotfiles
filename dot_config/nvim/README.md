# My Neovim Configuration

Modern and optimized Neovim configuration based on LazyVim.

## Features

- **Fast**: Intelligent lazy-loading, startup < 50ms
- **Modern**: Enhanced UI with Noice, Lualine, Telescope
- **Integrated AI**: Codeium + Gen.nvim (Ollama)
- **Powerful Git**: Neogit, Gitsigns, Fugitive, Worktree
- **Debugging**: Full DAP support
- **Writing**: Obsidian, Markdown, Zen mode
- **LSP**: Autocompletion, diagnostics, formatting
- **Navigation**: Harpoon, Flash, Telescope
- **Treesitter**: Advanced syntax highlighting

## Technical Stack

- **Package manager**: Lazy.nvim
- **Base**: LazyVim
- **LSP**: Mason + nvim-lspconfig
- **Completion**: nvim-cmp + Codeium
- **Git**: Neogit + Gitsigns
- **Fuzzy finder**: Telescope
- **File explorer**: nvim-tree
- **Statusline**: Lualine
- **Debugging**: nvim-dap
- **AI**: Codeium + Gen.nvim

## Directory Structure

```
~/.config/nvim/
├── init.lua                    # Entry point
├── lua/
│   ├── config/                 # Base configuration
│   │   ├── autocmds.lua       # Auto-commands
│   │   ├── keymaps.lua        # Keyboard shortcuts
│   │   ├── lazy.lua           # Lazy.nvim configuration
│   │   └── options.lua        # Neovim options
│   └── plugins/                # Plugins organized by category
│       ├── ai.lua             # AI (Codeium, Gen.nvim)
│       ├── cmp.lua            # Completion
│       ├── coding.lua         # Dev tools (DAP, autopairs)
│       ├── colorscheme.lua    # Themes
│       ├── editor.lua         # Editing tools
│       ├── extras.lua         # Extra plugins
│       ├── git.lua            # Git integration
│       ├── go.lua             # Go development
│       ├── lsp.lua            # LSP configuration
│       ├── performance.lua    # Optimizations
│       ├── telescope.lua      # Fuzzy search
│       ├── treesitter.lua     # Syntax parsing
│       ├── ui.lua             # User interface
│       └── writing.lua        # Markdown & Obsidian
├── KEYBINDINGS.md             # Keyboard shortcuts cheatsheet
├── PLUGINS.md                 # Plugin documentation
├── QUICKSTART.md              # Quick start guide
└── stylua.toml                # Formatter configuration
```

## Installation

### Prerequisites

```bash
# macOS
brew install neovim ripgrep fd lazygit
brew install --cask font-jetbrains-mono-nerd-font

# Optional: For Gen.nvim (local AI)
brew install ollama
ollama pull llama3
```

### Configuration Installation

```bash
# Backup old config (if it exists)
mv ~/.config/nvim ~/.config/nvim.backup

# Clone this config
git clone <your-repo> ~/.config/nvim

# First launch
nvim
```

On first launch:
1. Lazy.nvim installs automatically
2. All plugins are installed
3. Restart Neovim after installation

### Post-installation

```vim
:checkhealth           " Check configuration
:Mason                 " Install LSP servers
:TSUpdate              " Install Treesitter parsers
```

## Quick Start

### Essential shortcuts

| Action | Shortcut |
|--------|----------|
| Search files | `<leader>sf` |
| Search text | `<leader>sg` |
| File explorer | `ff` |
| Git status | `<leader>gs` |
| Code action | `<leader>ca` |
| Toggle Harpoon | `<leader>ht` |
| Help shortcuts | `<leader>` (then wait) |

**Leader key** = `<Space>`

See [KEYBINDINGS.md](KEYBINDINGS.md) for the complete list.

## Documentation

- **[QUICKSTART.md](QUICKSTART.md)** - Quick start guide
- **[KEYBINDINGS.md](KEYBINDINGS.md)** - All keyboard shortcuts
- **[PLUGINS.md](PLUGINS.md)** - Plugin documentation

## Themes

Default: **Catppuccin Mocha**

Change theme:
```lua
-- In lua/plugins/colorscheme.lua
opts = {
  colorscheme = "catppuccin",  -- or "dracula"
}
```

## Customization

### Add a plugin

Create a file in `lua/plugins/`:

```lua
-- lua/plugins/my-plugin.lua
return {
  {
    "author/my-plugin",
    event = "LazyFile",  -- Lazy loading
    opts = {},
    config = function(_, opts)
      require("my-plugin").setup(opts)
    end,
  },
}
```

### Modify options

Edit `lua/config/options.lua`:

```lua
vim.opt.tabstop = 4  -- Example
```

### Add shortcuts

Edit `lua/config/keymaps.lua`:

```lua
vim.keymap.set("n", "<leader>x", ":MyCommand<CR>", { desc = "My command" })
```

## Troubleshooting

### Plugin not loading
```vim
:Lazy sync
:Lazy clean
```

### LSP not working
```vim
:LspInfo      " View active LSP
:LspRestart   " Restart
:Mason        " Install servers
```

### Slow performance
```vim
:Lazy profile  " View load times
```

### Reset configuration
```bash
rm -rf ~/.local/share/nvim
rm -rf ~/.local/state/nvim
rm -rf ~/.cache/nvim
nvim  # Reinstall
```

## Statistics

- **Plugins**: 50+ plugins
- **Config lines**: ~1500 lines
- **Startup time**: ~40-50ms
- **Supported languages**: Go, Lua, Python, Rust, TypeScript, etc.

## Workflows

### Development

1. `nvim .` - Open project
2. `<leader>sf` - Find file
3. `<leader>m` - Mark important files (Harpoon)
4. `<leader>ca` - Code actions
5. `<leader>gs` - Git status

### Writing (Markdown/Obsidian)

1. `nvim note.md`
2. `<leader>z` - Zen mode
3. `gf` - Follow Obsidian links
4. `:MarkdownPreview` - Preview

### Debugging

1. `<leader>db` - Toggle breakpoint
2. `<leader>dc` - Start debugging
3. `<leader>dt` - Toggle DAP UI
4. `<leader>dso` - Step over

## Contributors

- Initial configuration: [Your name]
- Complete refactor: AI Assistant
- Base: [LazyVim](https://www.lazyvim.org)

## License

MIT License - See [LICENSE](LICENSE)

## Acknowledgments

- [LazyVim](https://github.com/LazyVim/LazyVim) - Configuration base
- [folke](https://github.com/folke) - Creator of many plugins
- All plugin maintainers used

## Useful Links

- [Neovim Docs](https://neovim.io/doc/)
- [LazyVim Docs](https://www.lazyvim.org)
- [Awesome Neovim](https://github.com/rockerBOO/awesome-neovim)

---

**Enjoy coding!**
