# 🐱 Configuration Kitty

Configuration personnalisée de Kitty basée sur Ghostty, WezTerm et Alacritty.

## 🎨 Thème

**Catppuccin Mocha** - Un thème sombre et apaisant avec des couleurs pastel.

## 🔤 Police

- **Famille:** JetBrainsMono Nerd Font
- **Taille:** 12px
- **Ligatures:** Activées

## 🐚 Shell

Par défaut, Nushell (nu) est configuré comme shell.

```conf
shell /opt/homebrew/bin/nu
```

**Note importante:** Assurez-vous que le PATH de Homebrew est configuré dans votre `env.nu` avant l'initialisation de Starship et autres outils.

## ✨ Apparence

### 🪟 Fenêtre
- **Padding:** 12px de chaque côté
- **Décorations:** Barre de titre masquée (titlebar-only)
- **Opacité:** 0.9 (90%)
- **Blur:** Activé avec intensité de 30

### 💫 Curseur
- **Forme:** Block (bloc)
- **Clignotement:** Désactivé

### 📑 Barre d'onglets
- **Position:** En haut
- **Style:** Powerline avec effet slanted
- **Affichage:** Toujours visible

## ⚙️ Fonctionnalités

### 📋 Sélection
- **Copy on select:** Activé - Le texte sélectionné est automatiquement copié dans le presse-papiers

### 📜 Scrollback
- **Historique:** 10 000 lignes
- **Multiplicateur de défilement:** 5x

### 💻 Terminal
- **TERM:** xterm-256color

### 🔔 Cloche
- **Audio:** Désactivée
- **Visuel:** Désactivée

## ⌨️ Raccourcis clavier

### 📋 Copier/Coller
- `Cmd+C` / `Ctrl+Shift+C` - Copier
- `Cmd+V` / `Ctrl+Shift+V` - Coller

### 🔍 Recherche
- `Cmd+F` / `Ctrl+Shift+F` - Recherche avec fzf

### 🔠 Taille de police
- `Cmd+=` / `Ctrl+=` - Augmenter la taille
- `Cmd+-` / `Ctrl+-` - Diminuer la taille
- `Cmd+0` / `Ctrl+0` - Réinitialiser la taille

### 🧭 Navigation
- `Shift+PageUp` - Défiler vers le haut
- `Shift+PageDown` - Défiler vers le bas
- `Cmd+Home` - Aller au début
- `Cmd+End` - Aller à la fin

### 🪟 Gestion des fenêtres
- `Cmd+N` / `Ctrl+Shift+N` - Nouvelle fenêtre
- `Cmd+W` / `Ctrl+Shift+W` - Fermer la fenêtre

### 📑 Gestion des onglets
- `Cmd+T` / `Ctrl+Shift+T` - Nouvel onglet
- `Cmd+W` / `Ctrl+Shift+X` - Fermer l'onglet
- `Cmd+]` / `Ctrl+Shift+]` - Onglet suivant
- `Cmd+[` / `Ctrl+Shift+[` - Onglet précédent
- `Cmd+Shift+]` - Déplacer l'onglet vers l'avant
- `Cmd+Shift+[` - Déplacer l'onglet vers l'arrière
- `Cmd+1` à `Cmd+9` - Aller à l'onglet 1-9

### 🔄 Configuration
- `Cmd+Shift+R` / `Ctrl+Shift+R` - Recharger la configuration

## 🖱️ Souris

- **Masquage:** Le curseur n'est jamais masqué
- **URLs:** Style souligné avec effet curly
- **Ouverture:** Cmd+clic pour ouvrir les liens

## 🎨 Palette de couleurs Catppuccin Mocha

### 🌈 Couleurs normales
- ⬛ Noir (0): `#45475a`
- 🔴 Rouge (1): `#f38ba8`
- 🟢 Vert (2): `#a6e3a1`
- 🟡 Jaune (3): `#f9e2af`
- 🔵 Bleu (4): `#89b4fa`
- 🟣 Magenta (5): `#f5c2e7`
- 🩵 Cyan (6): `#94e2d5`
- ⬜ Blanc (7): `#bac2de`

### ✨ Couleurs vives
- ⬛ Noir (8): `#585b70`
- 🔴 Rouge (9): `#f38ba8`
- 🟢 Vert (10): `#a6e3a1`
- 🟡 Jaune (11): `#f9e2af`
- 🔵 Bleu (12): `#89b4fa`
- 🟣 Magenta (13): `#f5c2e7`
- 🩵 Cyan (14): `#94e2d5`
- ⬜ Blanc (15): `#a6adc8`

### 🎯 Couleurs principales
- 🌑 Arrière-plan: `#1e1e2e`
- 📄 Texte: `#cdd6f4`
- 🖱️ Sélection (bg): `#f5e0dc`
- 🖱️ Sélection (fg): `#1e1e2e`
- 💫 Curseur: `#f5e0dc`

### 📑 Couleurs des onglets
- 🔵 Onglet actif (bg): `#89b4fa`
- ⬛ Onglet actif (fg): `#1e1e2e`
- 🌑 Onglet inactif (bg): `#313244`
- 📄 Onglet inactif (fg): `#cdd6f4`

## 🛠️ Personnalisation

Pour modifier la configuration, éditez le fichier:
```bash
~/.config/kitty/kitty.conf
```

### 🔄 Changer de shell

Pour Fish:
```conf
shell /opt/homebrew/bin/fish
```

Pour Zsh:
```conf
shell /bin/zsh
```

### 👁️ Changer l'opacité

```conf
background_opacity 1.0  # Complètement opaque
# ou
background_opacity 0.8  # Plus transparent
```

### 📏 Changer la taille de police

```conf
font_size 14.0  # Plus grande
# ou
font_size 10.0  # Plus petite
```

### 🎨 Changer le style de la barre d'onglets

```conf
tab_bar_style fade      # Style fade
# ou
tab_bar_style separator # Style séparateur
# ou
tab_bar_style hidden    # Masquer la barre
```

## 📦 Installation

1. Installer Kitty:
```bash
brew install --cask kitty
```

2. Installer la police JetBrains Mono Nerd Font:
```bash
brew tap homebrew/cask-fonts
brew install --cask font-jetbrains-mono-nerd-font
```

3. (Optionnel) Installer fzf pour la recherche:
```bash
brew install fzf
```

4. La configuration est déjà en place dans `~/.config/kitty/kitty.conf`

## 🚀 Fonctionnalités avancées de Kitty

### 🖼️ Support des images
Kitty supporte l'affichage d'images directement dans le terminal avec le protocole Kitty graphics.

### 🔗 Hints (détection de liens)
Kitty peut détecter et ouvrir automatiquement les URLs, chemins de fichiers, etc.

### 📐 Layouts
Kitty supporte plusieurs layouts pour organiser vos fenêtres (splits, stack, etc.)

### 🎯 Marks
Vous pouvez marquer du texte dans le terminal pour y revenir facilement.

## 🐚 Configuration Nushell

Si vous utilisez Nushell, assurez-vous que votre `env.nu` configure le PATH avant d'initialiser Starship:

```nu
# Dans ~/Library/Application Support/nushell/env.nu
$env.PATH = ($env.PATH | split row (char esep) | prepend '/opt/homebrew/bin')
```

Cela évite les erreurs "starship command not found" au démarrage.

## 📚 Ressources

- 📖 [Documentation Kitty](https://sw.kovidgoyal.net/kitty/)
- 🎨 [Catppuccin](https://github.com/catppuccin/catppuccin)
- 🔤 [JetBrains Mono](https://www.jetbrains.com/lp/mono/)
- 🐚 [Nushell](https://www.nushell.sh/)
- 🔍 [fzf](https://github.com/junegunn/fzf)

## 💡 Astuces

- Utilisez `Cmd+Shift+R` pour recharger la config sans redémarrer Kitty
- Les ligatures de la police sont activées pour un meilleur rendu du code
- La recherche avec fzf permet de naviguer rapidement dans le scrollback
- Kitty est GPU-accéléré pour des performances optimales
