# Quick Start Guide

Quick start guide for your Neovim configuration.

## First Launch

1. **Launch Neovim**
   ```bash
   nvim
   ```

2. **Automatic installation**
   - Lazy.nvim will install all plugins automatically
   - Wait for all plugins to install
   - Restart Neovim after installation

3. **Check health**
   ```vim
   :checkhealth
   ```

## Essential Commands

### Plugin Management
```vim
:Lazy              " Open plugin manager
:Lazy sync         " Install/update plugins
:Lazy clean        " Remove unused plugins
:Lazy update       " Update all plugins
```

### LSP Management
```vim
:Mason             " Open LSP manager
:LspInfo           " Info about active LSP
:LspRestart        " Restart LSP
```

### Treesitter
```vim
:TSUpdate          " Update parsers
:TSInstallInfo     " View installed parsers
```

## Recommended Workflow

### 1. Open a project
```bash
cd ~/my-project
nvim .
```

### 2. Quick navigation
- `<leader>sf` - Search file
- `<leader>sg` - Search text
- `ff` - Toggle file explorer
- `<leader>sh` - Harpoon (favorite files)

### 3. Editing
- `gcc` - Comment/uncomment line
- `gc` (visual) - Comment selection
- Leader + `ca` - Code actions
- Leader + `rn` - Rename

### 4. Git workflow
- Leader + `gs` - Open Neogit
- Leader + `gc` - Commit
- Leader + `gp` - Pull
- Leader + `gP` - Push
- `]c` / `[c` - Navigate between hunks

### 5. Debugging
- Leader + `db` - Toggle breakpoint
- Leader + `dc` - Start/Continue debugging
- Leader + `dt` - Toggle DAP UI

## Main Plugins

### Editing
- **Telescope** - Fuzzy search (`<leader>sf`, `<leader>sg`)
- **Harpoon** - Quick navigation (`<leader>m`, `<leader>ht`)
- **nvim-tree** - File explorer (`ff`)
- **Flash** - Quick navigation (`s`)

### Git
- **Neogit** - Git interface (`<leader>gs`)
- **Gitsigns** - Git decorations
- **Diffview** - Diff views

### Code
- **LSP** - Autocompletion, diagnostics
- **Treesitter** - Syntax highlighting
- **nvim-cmp** - Completion
- **DAP** - Debugging

### AI
- **Codeium** - AI suggestions (`Ctrl-e` in insert)
- **Gen.nvim** - Local LLM (`<leader>ai`)

### UI
- **Lualine** - Status bar
- **Noice** - Enhanced UI
- **WhichKey** - Shortcut help

### Writing
- **Obsidian** - Notes
- **Zen Mode** - Focus mode (`<leader>z`)
- **Markdown Preview** - Preview

## Productivity Tips

### 1. Use WhichKey
Press `<leader>` and wait → WhichKey shows all available shortcuts

### 2. Fuzzy search
- `<leader>sf` - Files
- `<leader>sg` - Content (grep)
- `<leader>sb` - Open buffers
- `<leader>sd` - Diagnostics

### 3. Harpoon for quick navigation
1. `<leader>m` to mark an important file
2. `<leader>ht` to see your favorites
3. Navigate quickly between main files

### 4. Code actions
- `K` on a function/variable → Documentation
- `gd` → Go to definition
- `gr` → View references
- `<leader>ca` → Available code actions

### 5. Integrated Git
- `<leader>gs` → Neogit (full interface)
- `]c` → Next change
- `<leader>hp` → Preview change
- `<leader>hs` → Stage change

## Troubleshooting

### Plugins don't load
```vim
:Lazy sync
```
Then restart Neovim

### LSP not working
1. Check that the server is installed:
   ```vim
   :Mason
   ```
2. Check LSP status:
   ```vim
   :LspInfo
   ```
3. Restart LSP:
   ```vim
   :LspRestart
   ```

### Treesitter not coloring
```vim
:TSUpdate all
```

### Slow performance
1. Check loaded plugins:
   ```vim
   :Lazy profile
   ```
2. Disable unused plugins in `lua/plugins/`

## Resources

- **Neovim Documentation**: `:help`
- **LazyVim docs**: https://www.lazyvim.org
- **Keybindings**: See `KEYBINDINGS.md`
- **Plugins**: See `PLUGINS.md`

## Next Steps

1. **Customize the colorscheme**
   - Edit `lua/plugins/colorscheme.lua`

2. **Add languages**
   - Edit `lua/config/lazy.lua` to add LazyVim extras
   - Example: `{ import = "lazyvim.plugins.extras.lang.python" }`

3. **Create your own keymaps**
   - Edit `lua/config/keymaps.lua`

4. **Add plugins**
   - Create a file in `lua/plugins/`
   - Use the LazyVim structure

## Useful Commands

```vim
:Telescope keymaps              " View all shortcuts
:Telescope commands             " View all commands
:Telescope help_tags            " Search in help
:checkhealth                    " Check configuration
:Lazy                          " Plugin manager
:Mason                         " LSP/DAP/Linters manager
:LspInfo                       " LSP info
:TSInstallInfo                 " Treesitter info
```

Happy coding!
