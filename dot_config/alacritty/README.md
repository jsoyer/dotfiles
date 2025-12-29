# 🚀 Configuration Alacritty

Configuration personnalisée d'Alacritty basée sur Ghostty et WezTerm.

## 🎨 Thème

**Catppuccin Mocha** - Un thème sombre et apaisant avec des couleurs pastel.

## 🔤 Police

- **Famille:** JetBrainsMono Nerd Font
- **Taille:** 12px
- **Styles:** Regular, Bold, Italic, Bold Italic

## 🐚 Shell

Par défaut, Nushell (nu) est configuré comme shell.

```toml
[terminal.shell]
program = "/opt/homebrew/bin/nu"
```

**Note:** La configuration utilise `terminal.shell` (nouvelle syntaxe) au lieu de `shell` (dépréciée).

## ✨ Apparence

### 🪟 Fenêtre
- **Padding:** 12px de chaque côté (équilibré)
- **Décorations:** Buttonless (sans boutons)
- **Opacité:** 0.9 (90%)
- **Blur:** Activé (effet de flou sur macOS)

### 💫 Curseur
- **Forme:** Block (bloc)
- **Clignotement:** Désactivé

## ⚙️ Fonctionnalités

### 📋 Sélection
- **Copy on select:** Activé - Le texte sélectionné est automatiquement copié dans le presse-papiers

### 📜 Scrollback
- **Historique:** 10 000 lignes

### 💻 Terminal
- **TERM:** xterm-256color

## ⌨️ Raccourcis clavier

### 📋 Copier/Coller
- `Ctrl+Shift+C` - Copier
- `Ctrl+Shift+V` - Coller

### 🔍 Recherche
- `Ctrl+Shift+F` - Recherche en avant

### 🔠 Taille de police
- `Ctrl+=` - Augmenter la taille
- `Ctrl+-` - Diminuer la taille
- `Ctrl+0` - Réinitialiser la taille

### 🧭 Navigation
- `Shift+PageUp` - Défiler vers le haut
- `Shift+PageDown` - Défiler vers le bas

### 🪟 Fenêtre
- `Ctrl+Shift+N` - Nouvelle fenêtre

## 🖱️ Souris

- **Clic droit:** Coller depuis la sélection
- **Masquage:** Le curseur n'est pas masqué lors de la frappe

## 🎨 Palette de couleurs Catppuccin Mocha

### 🌈 Couleurs normales
- ⬛ Noir: `#45475a`
- 🔴 Rouge: `#f38ba8`
- 🟢 Vert: `#a6e3a1`
- 🟡 Jaune: `#f9e2af`
- 🔵 Bleu: `#89b4fa`
- 🟣 Magenta: `#f5c2e7`
- 🩵 Cyan: `#94e2d5`
- ⬜ Blanc: `#bac2de`

### ✨ Couleurs vives
- ⬛ Noir: `#585b70`
- 🔴 Rouge: `#f38ba8`
- 🟢 Vert: `#a6e3a1`
- 🟡 Jaune: `#f9e2af`
- 🔵 Bleu: `#89b4fa`
- 🟣 Magenta: `#f5c2e7`
- 🩵 Cyan: `#94e2d5`
- ⬜ Blanc: `#a6adc8`

### 🎯 Couleurs primaires
- 🌑 Arrière-plan: `#1e1e2e`
- 📄 Texte: `#cdd6f4`

## 🛠️ Personnalisation

Pour modifier la configuration, éditez le fichier:
```bash
~/.config/alacritty/alacritty.toml
```

### 🔄 Changer de shell

Pour Fish:
```toml
[terminal.shell]
program = "/opt/homebrew/bin/fish"
```

Pour Zsh:
```toml
[terminal.shell]
program = "/bin/zsh"
```

### 👁️ Changer l'opacité

```toml
[window]
opacity = 1.0  # Complètement opaque
# ou
opacity = 0.8  # Plus transparent
```

### 📏 Changer la taille de police

```toml
[font]
size = 14.0  # Plus grande
# ou
size = 10.0  # Plus petite
```

## 📦 Installation

1. Installer Alacritty:
```bash
brew install --cask alacritty
```

2. Installer la police JetBrains Mono Nerd Font:
```bash
brew tap homebrew/cask-fonts
brew install --cask font-jetbrains-mono-nerd-font
```

3. La configuration est déjà en place dans `~/.config/alacritty/alacritty.toml`

## 📚 Ressources

- 📖 [Documentation Alacritty](https://alacritty.org/)
- 🎨 [Catppuccin](https://github.com/catppuccin/catppuccin)
- 🔤 [JetBrains Mono](https://www.jetbrains.com/lp/mono/)
- 🐚 [Nushell](https://www.nushell.sh/)
