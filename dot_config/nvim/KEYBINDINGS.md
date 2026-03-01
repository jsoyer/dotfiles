# Manuel des Raccourcis Neovim

> Référence complète de tous les raccourcis de cette configuration

**Leader key :** `<Space>`

---

## Table des matières

1. [Mode d'insertion](#mode-dinsertion)
2. [Navigation](#navigation)
3. [Buffers](#buffers)
4. [Fenêtres & Splits](#fenêtres--splits)
5. [Fichiers & Sauvegarde](#fichiers--sauvegarde)
6. [Recherche (Telescope)](#recherche-telescope)
7. [Git](#git)
8. [LSP & Diagnostics](#lsp--diagnostics)
9. [Refactoring](#refactoring)
10. [Débogage (DAP)](#débogage-dap)
11. [Harpoon](#harpoon)
12. [Treesitter & Text Objects](#treesitter--text-objects)
13. [Surround](#surround)
14. [Mode visuel](#mode-visuel)
15. [Complétion](#complétion)
16. [AI & Code Tools](#ai--code-tools)
17. [Toggles](#toggles)
18. [Session](#session)
19. [UI & Notifications](#ui--notifications)
20. [Terminal](#terminal)
21. [Référence rapide](#référence-rapide)

---

## Mode d'insertion

| Raccourci | Action |
|-----------|--------|
| `jj` / `jk` | Quitter le mode insertion |
| `<C-e>` | Accepter suggestion Codeium |
| `<C-n>` / `<C-p>` | Suggestion suivante / précédente (Codeium) |
| `<C-x>` | Annuler suggestion Codeium |
| `,` `.` `!` `?` | Points de rupture undo |

---

## Navigation

| Raccourci | Action |
|-----------|--------|
| `<C-h/j/k/l>` | Naviguer entre les splits |
| `H` / `L` | Buffer précédent / suivant |
| `<Tab>` / `<S-Tab>` | Buffer suivant / précédent |
| `<leader>1`…`9` | Aller au buffer N |
| `E` | Fin de ligne (`$`) |
| `B` | Début de ligne (`^`) |
| `j` / `k` | Navigation wrap-aware |
| `n` / `N` | Résultat suivant/précédent (centré) |
| `<Esc>` / `<leader><space>` | Effacer la surbrillance de recherche |

### Navigation de saut rapide (Flash)

| Raccourci | Action |
|-----------|--------|
| `s` | Flash jump |
| `S` | Flash Treesitter |
| `r` | Remote flash (opérateur) |
| `R` | Treesitter search |
| `<C-s>` | Toggle Flash dans la recherche (commande) |

### Quickfix & Location list

| Raccourci | Action |
|-----------|--------|
| `[q` / `]q` | Quickfix précédent / suivant |
| `[l` / `]l` | Location list précédent / suivant |

---

## Buffers

| Raccourci | Action |
|-----------|--------|
| `<Tab>` / `<S-Tab>` | Buffer suivant / précédent ⭐ |
| `H` / `L` | Buffer précédent / suivant ⚡ |
| `<leader>bh` / `<leader>bl` | Buffer précédent / suivant |
| `<leader>bj` / `<leader>bk` | Premier / dernier buffer |
| `<leader>bd` / `<leader>bD` | Fermer / forcer fermer buffer |
| `<leader>ba` | Fermer tous sauf le courant |
| `<leader>bo` | Fermer les autres buffers |
| `<leader>bn` | Nouveau buffer |
| `<leader>x` / `<leader>X` | Fermer / forcer fermer buffer |
| `<leader>1`…`9` | Aller au buffer N |

---

## Fenêtres & Splits

| Raccourci | Action |
|-----------|--------|
| `<leader>-` / `<leader>\|` | Split horizontal / vertical |
| `<leader>sh` / `<leader>sv` | Split horizontal / vertical |
| `<leader>sx` | Fermer le split courant |
| `<leader>so` | Garder uniquement ce split |
| `<leader>s=` | Égaliser les splits |
| `<C-Up/Down>` | Redimensionner hauteur ±2 |
| `<C-Left/Right>` | Redimensionner largeur ±2 |
| `<C-W>,` / `<C-W>.` | Redimensionner largeur ±10 |

---

## Fichiers & Sauvegarde

| Raccourci | Action |
|-----------|--------|
| `<leader>w` / `<leader>W` | Sauvegarder / forcer sauvegarder |
| `<leader>fs` / `<leader>fS` | Sauvegarder / sauvegarder tout |
| `<leader>fn` | Nouveau fichier |
| `<leader>e` / `<leader>E` | Toggle / trouver dans l'explorateur |

---

## Recherche (Telescope)

| Raccourci | Action |
|-----------|--------|
| `<leader>sf` | Chercher fichiers |
| `<leader>?` | Fichiers récents |
| `<leader>sg` | Grep live |
| `<leader>sw` | Grep le mot sous curseur |
| `<leader>/` | Fuzzy find dans le buffer courant |
| `<leader>sb` | Chercher buffers ouverts |
| `<leader>sd` | Diagnostics |
| `<leader>st` | Chercher TODOs |
| `<leader>sn` | Notifications |
| `<leader>sS` | Git status |
| `<leader>sr` | Git worktrees |
| `<leader>sR` | Créer un git worktree |
| `<leader><Tab>` | Commandes |

### Dans Telescope (insert mode)

| Raccourci | Action |
|-----------|--------|
| `<C-j>` / `<C-k>` | Sélection suivante / précédente |

---

## Git

### Neogit & Fugitive

| Raccourci | Action |
|-----------|--------|
| `<leader>gs` | Neogit status |
| `<leader>gc` | Commit |
| `<leader>gp` | Pull |
| `<leader>gP` | Push |
| `<leader>gb` | Branches (Telescope) / Toggle blame inline |
| `<leader>gB` | Git blame (Fugitive) |

### Gitsigns (Hunks)

| Raccourci | Action |
|-----------|--------|
| `]c` / `[c` | Hunk suivant / précédent |
| `<leader>hs` / `<leader>ha` | Stager le hunk |
| `<leader>hr` | Reset le hunk |
| `<leader>hS` | Stager le buffer entier |
| `<leader>hu` | Annuler le stage |
| `<leader>hR` | Reset le buffer |
| `<leader>hp` | Prévisualiser le hunk |
| `<leader>hb` | Blame la ligne |
| `<leader>hd` / `<leader>hD` | Diff this / Diff with previous |
| `<leader>tB` | Toggle blame de ligne |
| `ih` (opérateur) | Text object : hunk git |

---

## LSP & Diagnostics

### Navigation

| Raccourci | Action |
|-----------|--------|
| `[d` / `]d` | Diagnostic précédent / suivant |
| `[e` / `]e` | Erreur précédente / suivante |

### Actions

| Raccourci | Action |
|-----------|--------|
| `<leader>ca` | Code actions |
| `<leader>rn` | Renommer (incremental) |
| `gR` | Références LSP |

### Goto Preview (fenêtres flottantes)

| Raccourci | Action |
|-----------|--------|
| `gpd` | Prévisualiser définition |
| `gpt` | Prévisualiser type |
| `gpi` | Prévisualiser implémentation |
| `gpr` | Prévisualiser références |
| `gP` | Fermer toutes les previews |

### Trouble (liste de diagnostics)

| Raccourci | Action |
|-----------|--------|
| `<leader>xx` | Toggle Trouble |
| `<leader>xw` | Diagnostics workspace |
| `<leader>xd` | Diagnostics document |
| `<leader>xl` | Location list |
| `<leader>xq` | Quickfix |

### TODOs

| Raccourci | Action |
|-----------|--------|
| `]t` / `[t` | TODO suivant / précédent |

---

## Refactoring

| Raccourci | Mode | Action |
|-----------|------|--------|
| `<leader>re` | Visual | Extraire fonction |
| `<leader>rf` | Visual | Extraire vers fichier |
| `<leader>rv` | Visual | Extraire variable |
| `<leader>ri` | Normal/Visual | Inliner variable |

---

## Débogage (DAP)

| Raccourci | Action |
|-----------|--------|
| `<leader>dt` | Toggle UI debug |
| `<leader>db` | Toggle breakpoint |
| `<leader>dc` | Continuer |
| `<leader>dr` | Reset UI |
| `<leader>dso` | Step over |
| `<leader>dsi` | Step into |
| `<leader>dsx` | Step out |

---

## Harpoon

| Raccourci | Action |
|-----------|--------|
| `<leader>m` | Marquer le fichier courant |
| `<leader>ht` | Toggle menu Harpoon |
| `<leader>sh` | Harpoon via Telescope |

---

## Treesitter & Text Objects

### Sélection incrémentale

| Raccourci | Action |
|-----------|--------|
| `<C-Space>` | Initier / étendre la sélection |
| `<C-s>` | Étendre au scope |
| `<C-Backspace>` | Réduire la sélection |

### Text Objects (`a` = outer, `i` = inner)

| Raccourci | Objet |
|-----------|-------|
| `af` / `if` | Fonction |
| `ac` / `ic` | Classe |
| `aa` / `ia` | Paramètre |
| `ai` / `ii` | Conditionnel |
| `al` / `il` | Boucle |
| `at` | Commentaire |

### Navigation Treesitter

| Raccourci | Action |
|-----------|--------|
| `]f` / `[f` | Fonction suivante / précédente |
| `]]` / `[[` | Classe suivante / précédente |
| `]F` / `[F` | Fin de fonction suivante / précédente |
| `][` / `[]` | Fin de classe suivante / précédente |

### Swap paramètres

| Raccourci | Action |
|-----------|--------|
| `<leader>a` | Swap avec le paramètre suivant |
| `<leader>A` | Swap avec le paramètre précédent |

---

## Surround (Mini.surround)

| Raccourci | Action |
|-----------|--------|
| `gsa` | Ajouter entourage |
| `gsd` | Supprimer entourage |
| `gsr` | Remplacer entourage |
| `gsf` / `gsF` | Trouver entourage (droite / gauche) |
| `gsh` | Surligner entourage |
| `gsn` | Mettre à jour n_lines |

---

## Mode visuel

| Raccourci | Action |
|-----------|--------|
| `<` / `>` | Indenter gauche / droite (garde la sélection) |
| `p` | Coller sans écraser le registre |
| `<A-j>` / `<A-k>` | Déplacer sélection bas / haut |

---

## Mode normal — édition

| Raccourci | Action |
|-----------|--------|
| `<C-a>` | Sélectionner tout |
| `J` | Joindre lignes (conserve la position du curseur) |
| `<A-j>` / `<A-k>` | Déplacer la ligne bas / haut |

---

## Complétion (nvim-cmp)

| Raccourci | Action |
|-----------|--------|
| `<C-Space>` | Déclencher la complétion |
| `<C-d>` / `<C-f>` | Scroll docs haut / bas |
| `<CR>` | Confirmer la sélection |

---

## AI & Code Tools

| Raccourci | Action |
|-----------|--------|
| `<leader>ai` | Génération IA (Ollama / Gen.nvim) |
| `<leader>cs` | CodeSnap → presse-papier (visual) |
| `<leader>cS` | CodeSnap → fichier (visual) |
| `<leader>cp` | Preview Markdown |
| `<leader>ge` | Ajouter `if err` (Go) |

---

## Toggles

| Raccourci | Action |
|-----------|--------|
| `<leader>ts` | Toggle orthographe |
| `<leader>tw` | Toggle retour à la ligne |
| `<leader>tr` | Toggle numéros relatifs |
| `<leader>tt` | Toggle transparence |
| `<leader>tW` | Toggle Twilight (mode focus) |
| `<leader>tc` | Toggle colorizer (hex colors) |
| `<leader>tB` | Toggle git blame inline |
| `TT` | Toggle transparence (alternatif) |

---

## Session

| Raccourci | Action |
|-----------|--------|
| `<leader>qs` | Restaurer la session |
| `<leader>ql` | Restaurer la dernière session |
| `<leader>qd` | Ne pas sauvegarder la session |

---

## UI & Notifications

| Raccourci | Action |
|-----------|--------|
| `<leader>un` | Fermer toutes les notifications |
| `<leader>sn` | Voir les notifications (Telescope) |
| `<leader>nn` | Fermer le message Noice |
| `<leader>nl` | Dernier message |
| `<leader>nh` | Historique des messages |

---

## Terminal

| Raccourci | Action |
|-----------|--------|
| `<Esc><Esc>` | Quitter le mode terminal |
| `<C-h/j/k/l>` | Naviguer vers un autre split depuis le terminal |

---

## Mode commande

| Raccourci | Action |
|-----------|--------|
| `<C-a>` | Aller au début de la ligne |
| `<C-e>` | Aller à la fin de la ligne |

---

## Référence rapide

### Workflow quotidien

```
<Tab> / <S-Tab>     Naviguer les buffers
<leader>sf          Ouvrir un fichier
<leader>sg          Chercher dans le code
<leader>w           Sauvegarder
<leader>x           Fermer le buffer
<leader>gs          Git status
<leader>ca          Code actions
```

### Splits

```
<leader>sv / sh     Créer split vertical / horizontal
<C-h/j/k/l>         Naviguer entre splits
<leader>sx          Fermer le split
<leader>s=          Égaliser les splits
```

### Git rapide

```
]c / [c             Hunk suivant / précédent
<leader>hs          Stager le hunk
<leader>hp          Prévisualiser le hunk
<leader>gs          Neogit status
```

### Débogage rapide

```
<leader>db          Toggle breakpoint
<leader>dc          Lancer / continuer
<leader>dt          Toggle UI
<leader>dso / dsi   Step over / into
```

---

**Dernière mise à jour :** 2026-03-01
**Base :** LazyVim avec raccourcis personnalisés
**Thème :** Catppuccin Mocha
