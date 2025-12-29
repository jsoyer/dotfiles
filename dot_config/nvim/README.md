# 🚀 Ma configuration Neovim

Configuration Neovim moderne et optimisée basée sur LazyVim.

## ✨ Caractéristiques

- ⚡ **Rapide** : Lazy-loading intelligent, démarrage < 50ms
- 🎨 **Moderne** : UI améliorée avec Noice, Lualine, Telescope
- 🤖 **IA intégrée** : Codeium + Gen.nvim (Ollama)
- 🌿 **Git puissant** : Neogit, Gitsigns, Fugitive, Worktree
- 🐛 **Debugging** : Support DAP complet
- 📝 **Writing** : Obsidian, Markdown, Zen mode
- 🔧 **LSP** : Autocomplétion, diagnostics, formatting
- 🎯 **Navigation** : Harpoon, Flash, Telescope
- 🌳 **Treesitter** : Syntax highlighting avancé

## 📦 Stack technique

- **Package manager** : Lazy.nvim
- **Base** : LazyVim
- **LSP** : Mason + nvim-lspconfig
- **Complétion** : nvim-cmp + Codeium
- **Git** : Neogit + Gitsigns
- **Fuzzy finder** : Telescope
- **File explorer** : nvim-tree
- **Statusline** : Lualine
- **Debugging** : nvim-dap
- **AI** : Codeium + Gen.nvim

## 🗂️ Structure

```
~/.config/nvim/
├── init.lua                    # Point d'entrée
├── lua/
│   ├── config/                 # Configuration de base
│   │   ├── autocmds.lua       # Auto-commandes
│   │   ├── keymaps.lua        # Raccourcis clavier
│   │   ├── lazy.lua           # Configuration Lazy.nvim
│   │   └── options.lua        # Options Neovim
│   └── plugins/                # Plugins organisés par catégorie
│       ├── ai.lua             # IA (Codeium, Gen.nvim)
│       ├── cmp.lua            # Complétion
│       ├── coding.lua         # Outils de dev (DAP, autopairs)
│       ├── colorscheme.lua    # Thèmes
│       ├── editor.lua         # Outils d'édition
│       ├── extras.lua         # Plugins supplémentaires
│       ├── git.lua            # Intégration Git
│       ├── go.lua             # Développement Go
│       ├── lsp.lua            # Configuration LSP
│       ├── performance.lua    # Optimisations
│       ├── telescope.lua      # Recherche fuzzy
│       ├── treesitter.lua     # Parsing syntaxe
│       ├── ui.lua             # Interface utilisateur
│       └── writing.lua        # Markdown & Obsidian
├── KEYBINDINGS.md             # Cheatsheet des raccourcis
├── PLUGINS.md                 # Documentation des plugins
├── QUICKSTART.md              # Guide de démarrage rapide
└── stylua.toml                # Configuration du formateur
```

## 🚀 Installation

### Prérequis

```bash
# macOS
brew install neovim ripgrep fd lazygit
brew install --cask font-jetbrains-mono-nerd-font

# Optionnel : Pour Gen.nvim (IA local)
brew install ollama
ollama pull llama3
```

### Installation de la config

```bash
# Backup de l'ancienne config (si elle existe)
mv ~/.config/nvim ~/.config/nvim.backup

# Clone de cette config
git clone <votre-repo> ~/.config/nvim

# Premier lancement
nvim
```

Au premier lancement :
1. Lazy.nvim s'installe automatiquement
2. Tous les plugins sont installés
3. Redémarrer Neovim après installation

### Post-installation

```vim
:checkhealth           " Vérifier la configuration
:Mason                 " Installer les LSP servers
:TSUpdate              " Installer les parsers Treesitter
```

## ⚡ Démarrage rapide

### Raccourcis essentiels

| Action | Raccourci |
|--------|-----------|
| Rechercher fichier | `<leader>sf` |
| Rechercher texte | `<leader>sg` |
| Explorateur fichiers | `ff` |
| Git status | `<leader>gs` |
| Code action | `<leader>ca` |
| Toggle Harpoon | `<leader>ht` |
| Aide raccourcis | `<leader>` (puis attendre) |

**Leader key** = `<Space>`

Voir [KEYBINDINGS.md](KEYBINDINGS.md) pour la liste complète.

## 📚 Documentation

- **[QUICKSTART.md](QUICKSTART.md)** - Guide de démarrage rapide
- **[KEYBINDINGS.md](KEYBINDINGS.md)** - Tous les raccourcis clavier
- **[PLUGINS.md](PLUGINS.md)** - Documentation des plugins

## 🎨 Thèmes

Par défaut : **Catppuccin Mocha**

Changer de thème :
```lua
-- Dans lua/plugins/colorscheme.lua
opts = {
  colorscheme = "catppuccin",  -- ou "dracula"
}
```

## 🔧 Personnalisation

### Ajouter un plugin

Créer un fichier dans `lua/plugins/` :

```lua
-- lua/plugins/mon-plugin.lua
return {
  {
    "auteur/mon-plugin",
    event = "LazyFile",  -- Lazy loading
    opts = {},
    config = function(_, opts)
      require("mon-plugin").setup(opts)
    end,
  },
}
```

### Modifier les options

Éditer `lua/config/options.lua` :

```lua
vim.opt.tabstop = 4  -- Exemple
```

### Ajouter des raccourcis

Éditer `lua/config/keymaps.lua` :

```lua
vim.keymap.set("n", "<leader>x", ":MonCommande<CR>", { desc = "Ma commande" })
```

## 🐛 Dépannage

### Plugin ne se charge pas
```vim
:Lazy sync
:Lazy clean
```

### LSP ne fonctionne pas
```vim
:LspInfo      " Voir les LSP actifs
:LspRestart   " Redémarrer
:Mason        " Installer les serveurs
```

### Performance lente
```vim
:Lazy profile  " Voir les temps de chargement
```

### Réinitialiser la config
```bash
rm -rf ~/.local/share/nvim
rm -rf ~/.local/state/nvim
rm -rf ~/.cache/nvim
nvim  # Réinstaller
```

## 📊 Statistiques

- **Plugins** : 50+ plugins
- **Lignes de config** : ~1500 lignes
- **Temps de démarrage** : ~40-50ms
- **Languages supportés** : Go, Lua, Python, Rust, TypeScript, etc.

## 🎯 Workflows

### Développement

1. `nvim .` - Ouvrir le projet
2. `<leader>sf` - Trouver un fichier
3. `<leader>m` - Marquer les fichiers importants (Harpoon)
4. `<leader>ca` - Code actions
5. `<leader>gs` - Git status

### Writing (Markdown/Obsidian)

1. `nvim note.md`
2. `<leader>z` - Zen mode
3. `gf` - Suivre les liens Obsidian
4. `:MarkdownPreview` - Prévisualiser

### Debugging

1. `<leader>db` - Toggle breakpoint
2. `<leader>dc` - Start debugging
3. `<leader>dt` - Toggle DAP UI
4. `<leader>dso` - Step over

## 🤝 Contributeurs

- Configuration initiale : [Votre nom]
- Refonte complète : Assistant IA
- Base : [LazyVim](https://www.lazyvim.org)

## 📝 License

MIT License - Voir [LICENSE](LICENSE)

## 🙏 Remerciements

- [LazyVim](https://github.com/LazyVim/LazyVim) - Base de la config
- [folke](https://github.com/folke) - Créateur de nombreux plugins
- Tous les mainteneurs de plugins utilisés

## 🔗 Liens utiles

- [Neovim Docs](https://neovim.io/doc/)
- [LazyVim Docs](https://www.lazyvim.org)
- [Awesome Neovim](https://github.com/rockerBOO/awesome-neovim)

---

**Enjoy coding! 🎉**
