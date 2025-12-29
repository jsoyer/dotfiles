# 🚀 Quickstart Guide

Guide de démarrage rapide pour votre configuration Neovim.

## 📥 Premier lancement

1. **Lancer Neovim**
   ```bash
   nvim
   ```

2. **Installation automatique**
   - Lazy.nvim installera tous les plugins automatiquement
   - Attendez que tous les plugins soient installés
   - Redémarrez Neovim après l'installation

3. **Vérifier la santé**
   ```vim
   :checkhealth
   ```

## 🔧 Commandes essentielles

### Gestion des plugins
```vim
:Lazy              " Ouvrir le gestionnaire de plugins
:Lazy sync         " Installer/mettre à jour les plugins
:Lazy clean        " Supprimer les plugins inutilisés
:Lazy update       " Mettre à jour tous les plugins
```

### Gestion LSP
```vim
:Mason             " Ouvrir le gestionnaire LSP
:LspInfo           " Info sur les LSP actifs
:LspRestart        " Redémarrer le LSP
```

### Treesitter
```vim
:TSUpdate          " Mettre à jour les parsers
:TSInstallInfo     " Voir les parsers installés
```

## 🎯 Workflow recommandé

### 1. Ouvrir un projet
```bash
cd ~/mon-projet
nvim .
```

### 2. Navigation rapide
- `<leader>sf` - Rechercher un fichier
- `<leader>sg` - Rechercher du texte
- `ff` - Toggle l'explorateur de fichiers
- `<leader>sh` - Harpoon (fichiers favoris)

### 3. Édition
- `gcc` - Commenter/décommenter une ligne
- `gc` (visual) - Commenter une sélection
- Leader + `ca` - Actions de code
- Leader + `rn` - Renommer

### 4. Git workflow
- Leader + `gs` - Ouvrir Neogit
- Leader + `gc` - Commit
- Leader + `gp` - Pull
- Leader + `gP` - Push
- `]c` / `[c` - Naviguer entre les hunks

### 5. Debugging
- Leader + `db` - Toggle breakpoint
- Leader + `dc` - Start/Continue debugging
- Leader + `dt` - Toggle DAP UI

## 📦 Plugins principaux

### Édition
- **Telescope** - Recherche fuzzy (`<leader>sf`, `<leader>sg`)
- **Harpoon** - Navigation rapide (`<leader>m`, `<leader>ht`)
- **nvim-tree** - Explorateur de fichiers (`ff`)
- **Flash** - Navigation rapide (`s`)

### Git
- **Neogit** - Interface Git (`<leader>gs`)
- **Gitsigns** - Décorations Git
- **Diffview** - Vues de diff

### Code
- **LSP** - Autocomplétion, diagnostics
- **Treesitter** - Syntax highlighting
- **nvim-cmp** - Complétion
- **DAP** - Debugging

### IA
- **Codeium** - Suggestions IA (`Ctrl-e` en insert)
- **Gen.nvim** - LLM local (`<leader>ai`)

### UI
- **Lualine** - Barre de statut
- **Noice** - UI améliorée
- **WhichKey** - Aide aux raccourcis

### Writing
- **Obsidian** - Notes
- **Zen Mode** - Mode focus (`<leader>z`)
- **Markdown Preview** - Prévisualisation

## ⚡ Tips de productivité

### 1. Utiliser WhichKey
Appuyez sur `<leader>` et attendez → WhichKey affiche tous les raccourcis disponibles

### 2. Recherche fuzzy
- `<leader>sf` - Fichiers
- `<leader>sg` - Contenu (grep)
- `<leader>sb` - Buffers ouverts
- `<leader>sd` - Diagnostics

### 3. Harpoon pour navigation rapide
1. `<leader>m` pour marquer un fichier important
2. `<leader>ht` pour voir vos favoris
3. Naviguez rapidement entre vos fichiers principaux

### 4. Code actions
- `K` sur une fonction/variable → Documentation
- `gd` → Aller à la définition
- `gr` → Voir les références
- `<leader>ca` → Actions de code disponibles

### 5. Git intégré
- `<leader>gs` → Neogit (interface complète)
- `]c` → Prochain changement
- `<leader>hp` → Prévisualiser le changement
- `<leader>hs` → Stage le changement

## 🐛 Dépannage

### Les plugins ne se chargent pas
```vim
:Lazy sync
```
Puis redémarrer Neovim

### LSP ne fonctionne pas
1. Vérifier que le serveur est installé :
   ```vim
   :Mason
   ```
2. Vérifier l'état du LSP :
   ```vim
   :LspInfo
   ```
3. Redémarrer le LSP :
   ```vim
   :LspRestart
   ```

### Treesitter ne colore pas
```vim
:TSUpdate all
```

### Performance lente
1. Vérifier les plugins chargés :
   ```vim
   :Lazy profile
   ```
2. Désactiver les plugins inutiles dans `lua/plugins/`

## 📚 Ressources

- **Documentation Neovim** : `:help`
- **LazyVim docs** : https://www.lazyvim.org
- **Keybindings** : Voir `KEYBINDINGS.md`
- **Plugins** : Voir `PLUGINS.md`

## 🎓 Prochaines étapes

1. **Personnaliser le colorscheme**
   - Éditer `lua/plugins/colorscheme.lua`

2. **Ajouter des langages**
   - Éditer `lua/config/lazy.lua` pour ajouter des extras LazyVim
   - Exemple : `{ import = "lazyvim.plugins.extras.lang.python" }`

3. **Créer vos propres keymaps**
   - Éditer `lua/config/keymaps.lua`

4. **Ajouter des plugins**
   - Créer un fichier dans `lua/plugins/`
   - Utiliser la structure LazyVim

## 💡 Commandes utiles

```vim
:Telescope keymaps              " Voir tous les raccourcis
:Telescope commands             " Voir toutes les commandes
:Telescope help_tags            " Chercher dans l'aide
:checkhealth                    " Vérifier la configuration
:Lazy                          " Gestionnaire de plugins
:Mason                         " Gestionnaire LSP/DAP/Linters
:LspInfo                       " Info LSP
:TSInstallInfo                 " Info Treesitter
```

Bon coding ! 🎉
