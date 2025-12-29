# Neovim Configuration - Plugin Organization

Cette configuration Neovim utilise LazyVim et organise les plugins de manière modulaire.

## 📁 Structure

```
lua/plugins/
├── ai.lua          # Assistants IA (Codeium, Gen.nvim)
├── cmp.lua         # Complétion (nvim-cmp)
├── coding.lua      # Outils de code (DAP, autopairs, comment, codesnap)
├── colorscheme.lua # Thèmes (Catppuccin, Dracula)
├── editor.lua      # Outils d'édition (Harpoon, nvim-tree, Trouble, Todo)
├── git.lua         # Git (Neogit, Gitsigns, Fugitive, Worktree, Diffview)
├── go.lua          # Développement Go
├── lsp.lua         # Configuration LSP
├── telescope.lua   # Recherche fuzzy (Telescope)
├── treesitter.lua  # Parsing de syntaxe
├── ui.lua          # Interface (Lualine, Noice, Notify, Indent guides)
└── writing.lua     # Écriture (Obsidian, Markdown, Zen mode, Twilight)
```

## 🎯 Catégories de plugins

### AI (ai.lua)
- **Gen.nvim** : LLM local (Ollama/Llama)
- **Codeium** : Suggestions de code IA

### Complétion (cmp.lua)
- **nvim-cmp** : Moteur de complétion

### Coding (coding.lua)
- **nvim-autopairs** : Auto-fermeture des paires
- **Comment.nvim** : Commentaires intelligents
- **nvim-dap** : Débogage avec DAP
- **codesnap** : Captures d'écran de code

### Git (git.lua)
- **Neogit** : Interface Git Magit-like
- **Gitsigns** : Décorations Git dans la gouttière
- **Fugitive** : Commandes Git
- **git-worktree** : Gestion des worktrees
- **Diffview** : Vues de diff améliorées

### Editor (editor.lua)
- **Harpoon** : Navigation rapide entre fichiers
- **nvim-tree** : Explorateur de fichiers
- **goto-preview** : Prévisualisation LSP
- **Trouble** : Liste de diagnostics
- **todo-comments** : Mise en évidence des TODOs
- **vim-surround** : Manipulation de surrounds
- **nvim-transparent** : Toggle transparence

### Go (go.lua)
- **go.nvim** : Outils Go
- **nvim-dap-go** : Débogage Go

### LSP (lsp.lua)
- **Mason** : Gestionnaire LSP
- **nvim-lspconfig** : Configuration LSP
- **Fidget** : Progression LSP

### Telescope (telescope.lua)
- **Telescope** : Recherche fuzzy
- **telescope-fzf-native** : Extension FZF
- **telescope-symbols** : Symboles

### Treesitter (treesitter.lua)
- **nvim-treesitter** : Parsing de syntaxe
- **nvim-treesitter-textobjects** : Objets texte

### UI (ui.lua)
- **Lualine** : Barre de statut
- **indent-blankline** : Guides d'indentation
- **nvim-notify** : Notifications
- **Noice** : UI améliorée pour messages/cmdline
- **nvim-web-devicons** : Icônes

### Writing (writing.lua)
- **Obsidian.nvim** : Intégration Obsidian
- **render-markdown** : Rendu Markdown
- **markdown-preview** : Prévisualisation Markdown
- **vim-pencil** : Aide à l'écriture
- **zen-mode** : Mode focus
- **Twilight** : Assombrit le code inactif

## ⚡ Optimisations

- **Lazy-loading** : La plupart des plugins se chargent à la demande
- **Event-based loading** : Chargement basé sur les événements (InsertEnter, LazyFile, etc.)
- **Command-based loading** : Chargement au premier appel de commande
- **Keymap-based loading** : Chargement lors du premier appel de raccourci

## 🔧 Personnalisation

Pour ajouter un plugin :

1. Choisissez le fichier approprié dans `lua/plugins/`
2. Ajoutez votre spec LazyVim
3. Utilisez le lazy-loading approprié

Exemple :
```lua
{
  "author/plugin-name",
  event = "LazyFile",  -- ou cmd, keys, ft, etc.
  opts = {},
  config = function(_, opts)
    require("plugin-name").setup(opts)
  end,
}
```

## 📦 Installation

Après modification, relancez Neovim :
```
nvim
```

Lazy.nvim installera automatiquement les nouveaux plugins.

## 🎨 Formatage

Tous les fichiers sont formatés avec Stylua :
```bash
stylua .
```

Configuration dans `stylua.toml` :
- Indentation : 2 espaces
- Largeur : 120 colonnes
- Double quotes
