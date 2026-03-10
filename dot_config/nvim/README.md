# Neovim Configuration

Modern Neovim configuration based on LazyVim.

## Features

- **Fast**: Intelligent lazy-loading, startup < 50ms
- **Multi-provider AI**: codecompanion.nvim (Claude, GPT, Gemini, Mistral, Ollama, + ACP agents)
- **Inline completion**: GitHub Copilot
- **Powerful Git**: Neogit, Gitsigns, Fugitive
- **Debugging**: Full DAP support
- **Writing**: Obsidian, Markdown, Zen mode
- **LSP**: Autocompletion, diagnostics, formatting
- **Navigation**: Harpoon, Flash, Telescope

## AI Stack

| Role | Plugin / Tool |
|------|--------------|
| Inline completions | `zbirenbaum/copilot.lua` (GitHub Copilot) |
| Chat + refactoring + agents | `olimorris/codecompanion.nvim` |

### codecompanion providers

**API (clé optionnelle via `secrets.zsh`) :**

| Provider | Env var | Modèles |
|----------|---------|---------|
| Anthropic Claude | `ANTHROPIC_API_KEY` | opus-4-6, sonnet-4-6, haiku-4-5 |
| OpenAI / Codex | `OPENAI_API_KEY` | gpt-4o, o3, o4-mini, codex-mini |
| Google Gemini | `GEMINI_API_KEY` | gemini-2.5-pro/flash |
| Mistral | `MISTRAL_API_KEY` | mistral-large, codestral |
| Ollama (local) | — | llama3, mistral, deepseek-coder, qwen2.5-coder |

**ACP agents (réutilisent l'auth du CLI, aucune clé supplémentaire) :**

| Agent | CLI requis |
|-------|-----------|
| `claude_code` | `claude` |
| `gemini_cli` | `gemini` |
| `opencode` | `opencode` |
| `mistral_vibe` | `mistral-vibe` |
| `codex` | `codex` |

Le provider par défaut est **automatiquement sélectionné** : premier dont la clé est présente dans l'environnement, sinon Ollama.

### Keymaps AI

| Keymap | Action |
|--------|--------|
| `<leader>aa` | Action palette |
| `<leader>ac` | Toggle chat panel |
| `<leader>an` | Nouveau chat |
| `<leader>ai` | Inline assistant |
| `<leader>ae` | Actions sur sélection |

Pour changer de provider dans un chat actif : `:CodeCompanion /model`

### Ajouter des clés API (optionnel)

Dans `~/.zsh/secrets.zsh` (gitignored, machine-local) :

```zsh
export ANTHROPIC_API_KEY="$(op read "op://Private/Anthropic API/credential" 2>/dev/null || true)"
export OPENAI_API_KEY="$(op read "op://Private/OpenAI API/credential" 2>/dev/null || true)"
export GEMINI_API_KEY="$(op read "op://Private/Gemini API/credential" 2>/dev/null || true)"
export MISTRAL_API_KEY="$(op read "op://Private/Mistral API/credential" 2>/dev/null || true)"
```

## Directory Structure

```
~/.config/nvim/
├── init.lua
├── lazyvim.json               # LazyVim extras
├── lua/
│   ├── config/
│   │   ├── autocmds.lua
│   │   ├── keymaps.lua
│   │   ├── lazy.lua
│   │   └── options.lua
│   └── plugins/
│       ├── core/              # cmp, colorscheme, lsp, telescope, treesitter
│       ├── dev/               # ai, coding, git
│       ├── lang/              # go, rust, python, typescript…
│       ├── tools/             # editor, extras, performance, writing
│       └── ui/                # ui
└── stylua.toml
```

## Installation

### Prerequisites

```bash
# macOS
brew install neovim ripgrep fd lazygit
brew install --cask font-jetbrains-mono-nerd-font

# Ollama (local AI, optionnel)
brew install ollama
ollama pull llama3
```

### Post-installation

```vim
:checkhealth
:Mason      " Install LSP servers
:TSUpdate   " Install Treesitter parsers
```

## Essential Keymaps

| Action | Shortcut |
|--------|----------|
| Search files | `<leader>sf` |
| Search text | `<leader>sg` |
| File explorer | `<leader>e` |
| Git status | `<leader>gs` |
| Code action | `<leader>ca` |
| AI actions | `<leader>aa` |
| AI chat | `<leader>ac` |
| Previous buffer | `H` |
| Next buffer | `L` |

**Leader key** = `<Space>`

## Troubleshooting

```vim
:Lazy sync       " Sync plugins
:LspInfo         " View active LSP
:Mason           " Install/update LSP servers
:Lazy profile    " View load times
:checkhealth codecompanion  " Check AI setup
```

## Links

- [LazyVim](https://www.lazyvim.org)
- [codecompanion.nvim](https://codecompanion.olimorris.dev)
- [Neovim Docs](https://neovim.io/doc/)
