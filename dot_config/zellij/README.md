# 🔷 Configuration Zellij

Configuration personnalisée de Zellij - Un multiplexeur de terminal moderne écrit en Rust.

## 🎨 Thème

**Catppuccin Mocha** - Un thème sombre et apaisant avec des couleurs pastel.

## 🐚 Shell

Par défaut, Nushell (nu) est configuré comme shell.

```kdl
default_shell "nu"
```

## ✨ Apparence

### 🪟 Interface
- **UI simplifiée:** Activée (sans glyphes de flèches)
- **Frames des panes:** Désactivés
- **Nom de session:** Visible dans les frames

### 🔔 Tips au démarrage
- **Tips:** Désactivés (`session_serialization false`)
- Plus de messages de bienvenue ou d'astuces au lancement

## ⚙️ Fonctionnalités

### 📋 Copier/Coller
- **Commande de copie:** `pbcopy` (macOS)
- **Copy on select:** Activé par défaut

### 📜 Scrollback
- **Buffer:** 10 000 lignes (par défaut)

### 🎯 Comportement
- **Force close:** `detach` - Se détache au lieu de quitter
- **Editor:** Défini par `$EDITOR` ou `$VISUAL`

## ⌨️ Raccourcis clavier

### 🔑 Modes principaux
Zellij utilise des modes modaux (comme Vim). Voici les raccourcis pour changer de mode:

- `Ctrl+G` - Mode verrouillé (locked)
- `Ctrl+A` - Mode pane
- `Ctrl+N` - Mode resize
- `Ctrl+S` - Mode scroll
- `Ctrl+T` - Mode tab
- `Ctrl+X` - Mode session
- `Ctrl+B` - Mode tmux

### 📐 Mode Pane (Ctrl+A)
- `h/j/k/l` ou flèches - Déplacer le focus
- `n` - Nouveau pane
- `d` - Nouveau pane en bas
- `r` - Nouveau pane à droite
- `x` - Fermer le pane
- `z` - Toggle fullscreen
- `f` - Toggle frames
- `w` - Toggle floating panes
- `e` - Toggle embed/floating
- `R` - Renommer le pane
- `S` - Prochain swap layout

### 📑 Mode Tab (Ctrl+T)
- `n` - Nouvel onglet
- `x` - Fermer l'onglet
- `h/l` ou flèches - Naviguer entre onglets
- `r` - Renommer l'onglet
- `s` - Toggle sync tab
- `b` - Break pane (déplacer vers nouvel onglet)
- `[` - Break pane à gauche
- `]` - Break pane à droite
- `1-9` - Aller à l'onglet 1-9
- `a` - Toggle onglet précédent

### 📏 Mode Resize (Ctrl+N)
- `h/j/k/l` ou flèches - Redimensionner
- `H/J/K/L` - Redimensionner (décroître)
- `=` ou `+` - Augmenter
- `-` - Diminuer

### 📜 Mode Scroll (Ctrl+S)
- `j/k` ou flèches - Défiler ligne par ligne
- `Ctrl+F` / `PageDown` - Page suivante
- `Ctrl+B` / `PageUp` - Page précédente
- `d` - Demi-page bas
- `u` - Demi-page haut
- `G` - Aller à la fin
- `s` - Mode recherche
- `e` - Éditer le scrollback

### 🔍 Mode Search (Ctrl+/)
- `n` - Résultat suivant
- `p` - Résultat précédent
- `c` - Toggle case sensitivity
- `w` - Toggle whole word
- `o` - Toggle wrap

### 🎮 Mode Session (Ctrl+X)
- `d` - Se détacher de la session
- `w` - Gestionnaire de sessions

### 🔗 Mode Tmux (Ctrl+B)
Compatible avec les raccourcis tmux classiques:
- `[` - Mode scroll
- `"` - Split horizontal
- `%` - Split vertical
- `z` - Toggle fullscreen
- `c` - Nouvel onglet
- `n/p` - Onglet suivant/précédent
- `x` - Fermer pane
- `d` - Se détacher

### ⚡ Raccourcis globaux (tous modes sauf locked)
- `Alt+N` - Nouveau pane
- `Alt+H/L` ou `Alt+Left/Right` - Naviguer focus ou tab
- `Alt+J/K` ou `Alt+Up/Down` - Naviguer focus
- `Alt+=` ou `Alt++` - Augmenter taille
- `Alt+-` - Diminuer taille
- `Alt+[` - Layout précédent
- `Alt+]` - Layout suivant
- `Alt+R` - Renommer tab

## 🎨 Thèmes disponibles

Votre configuration inclut:
- **Catppuccin Mocha** (actif) - `~/.config/zellij/themes/catppuccin.kdl`
- **Dracula** - `~/.config/zellij/themes/dracula.kdl`

Pour changer de thème, modifiez la ligne dans `config.kdl`:
```kdl
theme "catppuccin-mocha"
// ou
theme "dracula"
```

## 🔌 Plugins

### Plugins par défaut
- `tab-bar` - Barre d'onglets
- `status-bar` - Barre de status
- `strider` - Navigateur de fichiers
- `compact-bar` - Barre compacte

### Plugins personnalisés disponibles
- `zjstatus` - Barre de status hautement personnalisable
- `zellij-sessionizer` - Navigation rapide entre sessions

**Note:** Les plugins WASM doivent être téléchargés et placés dans `~/.config/zellij/plugins/`

## 📁 Layouts

Layouts disponibles dans `~/.config/zellij/layouts/`:
- `default.kdl` - Layout par défaut
- `datetime.kdl` - Layout avec date/heure

## 🛠️ Personnalisation

### 📂 Structure des fichiers
```
~/.config/zellij/
├── config.kdl              # Configuration principale
├── layouts/
│   ├── default.kdl
│   └── datetime.kdl
├── themes/
│   ├── catppuccin.kdl
│   └── dracula.kdl
└── plugins/
    ├── zellij-sessionizer.wasm
    └── zellij-datetime.wasm
```

### 🔄 Changer de shell

Pour Fish:
```kdl
default_shell "fish"
```

Pour Zsh:
```kdl
default_shell "zsh"
```

### 🎨 Activer/Désactiver les frames

```kdl
pane_frames true   # Avec frames
# ou
pane_frames false  # Sans frames
```

### 📊 Activer les tips

Si vous souhaitez réactiver les tips:
```kdl
session_serialization true
```

## 📦 Installation

1. Installer Zellij:
```bash
brew install zellij
```

2. La configuration est déjà en place dans `~/.config/zellij/`

## 🚀 Utilisation

### Démarrer Zellij
```bash
zellij
```

### Sessions nommées
```bash
zellij -s ma-session          # Créer/attacher session
zellij attach ma-session      # Attacher à session existante
zellij list-sessions          # Lister les sessions
zellij delete-session ma-session  # Supprimer session
```

### Layouts
```bash
zellij --layout default       # Utiliser un layout
zellij --layout datetime      # Layout avec datetime
```

### Se détacher
Dans Zellij: `Ctrl+X` puis `d`

## 🎯 Workflows recommandés

### Navigation rapide
1. `Ctrl+T` + `1-9` pour switcher entre onglets
2. `Alt+H/L` pour naviguer entre panes/tabs
3. `Ctrl+A` + `z` pour fullscreen un pane

### Organisation
1. `Ctrl+T` + `n` pour créer des onglets thématiques
2. `Ctrl+A` + `d/r` pour splitter horizontalement/verticalement
3. `Ctrl+A` + `S` pour changer de layout

### Productivité
1. `Ctrl+T` + `s` pour synchroniser les commandes sur tous les panes
2. `Ctrl+S` pour consulter l'historique
3. `Ctrl+X` + `w` pour switcher entre projets

## 📚 Ressources

- 📖 [Documentation Zellij](https://zellij.dev/)
- 🎨 [Catppuccin](https://github.com/catppuccin/catppuccin)
- 🐚 [Nushell](https://www.nushell.sh/)
- 🔌 [zjstatus](https://github.com/dj95/zjstatus)
- 🔌 [zellij-sessionizer](https://github.com/laperlej/zellij-sessionizer)

## 💡 Astuces

- Les keybindings sont entièrement personnalisés avec `clear-defaults=true`
- Mode tmux disponible pour une transition facile depuis tmux
- Les raccourcis Alt fonctionnent dans tous les modes (sauf locked)
- `Ctrl+G` pour verrouiller l'interface et utiliser les raccourcis natifs
- Les sessions persistent après fermeture du terminal (avec `detach`)
