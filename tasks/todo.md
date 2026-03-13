# Plan: Ajouter .codex, .agents, .qwen, .kiro, .mistralcode, .vibe dans chezmoi

## Analyse

### ~/.codex/ — OpenAI Codex CLI
**A tracker (config):**
- `config.toml` — modele, personality, projects trust (template potentiel)

**A ignorer (etat/cache/runtime):**
- `auth.json` — tokens OAuth (secret)
- `history.jsonl` — historique commandes
- `models_cache.json` — cache modeles
- `state_5.sqlite` — DB locale
- `.codex-global-state.json` — etat Electron/workspace
- `.personality_migration` — flag migration
- `version.json` — version check cache
- `log/`, `sessions/`, `shell_snapshots/`, `sqlite/`, `tmp/`, `vendor_imports/` — runtime
- `skills/` — skills systeme (.system/)

### ~/.agents/ — Agent universel (multi-agent skills)
**A tracker:**
- `skills/find-skills/SKILL.md` — skill find-skills (vercel-labs)
- `skills/frontend-design/SKILL.md` + `LICENSE.txt` — skill frontend-design (anthropics)
- `.skill-lock.json` — lock des skills installees

### ~/.qwen/ — Qwen Code CLI
**A tracker:** rien de propre — les skills sont des **symlinks vers `~/.agents/skills/`**
- `skills/find-skills` -> `../../.agents/skills/find-skills`
- `skills/frontend-design` -> `../../.agents/skills/frontend-design`

**Consequence:** si `.agents/` est gere, `.qwen/skills/` se resout automatiquement.
Il faut juste recreer les symlinks.

### ~/.kiro/ — Kiro IDE (AWS, fork VS Code)
**A tracker (config):**
- `argv.json` — args VS Code (crash-reporter, hardware accel)

**A ignorer:**
- `extensions/extensions.json` — liste extensions (vide, runtime)
- `argv.json` contient un `crash-reporter-id` unique par machine -> template ou ignorer

**Decision:** `argv.json` contient un UUID unique -> probablement mieux de l'ignorer aussi.
Si on veut tracker les flags (`enable-crash-reporter`, `disable-hardware-acceleration`), il faut un template.

### ~/.mistralcode/ — Mistral Code CLI
**A tracker (config):**
- `config.json` — domaine console, models list
- `.mistralcoderc.json` — settings (disableIndexing)

**A ignorer (runtime):**
- `dev_data/` — autocomplete.jsonl, chat.jsonl, nextEdit.jsonl, quickEdit.jsonl, tokens_generated.jsonl
- `index/` — index local
- `sessions/` — autocompleteCache.sqlite, sessions.json

### ~/.vibe/ — Vibe CLI (Mistral devstral)
**A tracker (config):**
- `config.toml` — modele actif, providers, models, tools permissions, theme (catppuccin-mocha)
- `trusted_folders.toml` — dossiers trusted (template potentiel, varie par machine)
- `instructions.md` — instructions custom (vide pour l'instant)

**A ignorer (secrets):**
- `.env` — MISTRAL_API_KEY en clair! -> JAMAIS commiter, gerer via 1Password ou env var

**A ignorer (runtime):**
- `vibe.log` — logs
- `vibehistory` — historique commandes
- `update_cache.json` — cache version check
- `logs/` — session logs
- `session/` — sessions JSON
- `skills/` — symlinks vers `~/.agents/skills/` (meme pattern que .qwen)

## Plan d'implementation

### Etape 1: .codex — config.toml
- [ ] Creer `dot_codex/config.toml.tmpl` avec template pour `trust_level` par machine
- [ ] La section `[projects]` varie par machine -> template conditionnel
- [ ] Alternative: `config.toml` statique si la config est identique partout

### Etape 2: .mistralcode — configs
- [ ] Creer `dot_mistralcode/config.json` (statique — domaine + models)
- [ ] Creer `dot_mistralcode/dot_mistralcoderc.json` (statique — settings)

### Etape 3: .vibe — configs
- [ ] Creer `dot_vibe/config.toml` (statique — providers, models, tools, theme)
- [ ] Creer `dot_vibe/trusted_folders.toml.tmpl` (template — varie par machine)
- [ ] Creer `dot_vibe/instructions.md` (statique — instructions custom)
- [ ] NE PAS tracker `.env` (secret MISTRAL_API_KEY)
- [ ] Note: `session_logging.save_dir` dans config.toml contient un path absolu
  -> template `.tmpl` avec `{{ .chezmoi.homeDir }}/.vibe/logs/session`

### Etape 4: .agents — skills
- [ ] **Option A (recommande)**: `.chezmoiexternal.toml` pour pull les skills depuis GitHub
  ```toml
  [".agents/skills/find-skills"]
  type = "git-repo"
  url = "https://github.com/vercel-labs/skills.git"
  # extraire juste skills/find-skills/

  [".agents/skills/frontend-design"]
  type = "git-repo"
  url = "https://github.com/anthropics/skills.git"
  # extraire juste skills/frontend-design/
  ```
- [ ] **Option B**: copie statique des SKILL.md + LICENSE.txt
- [ ] Tracker `.skill-lock.json` en statique (reflette l'etat voulu)

### Etape 5: .qwen + .vibe — symlinks vers .agents
- [ ] Creer `dot_qwen/skills/` avec symlinks chezmoi:
  ```
  dot_qwen/skills/symlink_find-skills       -> contient "../../.agents/skills/find-skills"
  dot_qwen/skills/symlink_frontend-design   -> contient "../../.agents/skills/frontend-design"
  ```
- [ ] Creer `dot_vibe/skills/` avec memes symlinks:
  ```
  dot_vibe/skills/symlink_agent-browser     -> contient "../../.agents/skills/agent-browser"
  dot_vibe/skills/symlink_find-skills       -> contient "../../.agents/skills/find-skills"
  dot_vibe/skills/symlink_frontend-design   -> contient "../../.agents/skills/frontend-design"
  ```
- [ ] Note: `.vibe` a un skill supplementaire `agent-browser` -> verifier s'il existe dans `.agents/`

### Etape 6: .kiro — decision
- [ ] **Option A (recommande)**: ignorer entierement (UUID unique, config triviale)
- [ ] **Option B**: template `argv.json.tmpl` pour les flags sans le crash-reporter-id

### Etape 7: .chezmoiignore.tmpl — exclusions globales
- [ ] Ajouter les exclusions runtime:
  ```
  # .codex runtime
  .codex/auth.json
  .codex/history.jsonl
  .codex/models_cache.json
  .codex/state_5.sqlite
  .codex/.codex-global-state.json
  .codex/.personality_migration
  .codex/version.json
  .codex/log/**
  .codex/sessions/**
  .codex/shell_snapshots/**
  .codex/sqlite/**
  .codex/tmp/**
  .codex/vendor_imports/**
  .codex/skills/**

  # .mistralcode runtime
  .mistralcode/dev_data/**
  .mistralcode/index/**
  .mistralcode/sessions/**

  # .vibe runtime + secrets
  .vibe/.env
  .vibe/vibe.log
  .vibe/vibehistory
  .vibe/update_cache.json
  .vibe/logs/**
  .vibe/session/**
  .vibe/skills/**

  # .kiro (ignorer tout)
  .kiro/**
  ```

### Etape 8: Conditionnel Windows
- [ ] Ajouter dans `.chezmoiignore.tmpl`:
  ```
  {{- if eq .chezmoi.os "windows" }}
  .codex/**
  .agents/**
  .qwen/**
  .kiro/**
  .mistralcode/**
  .vibe/**
  {{- end }}
  ```

### Etape 9: Verification
- [ ] `chezmoi diff` pour verifier les fichiers trackes
- [ ] `chezmoi apply ~/.codex ~/.agents ~/.qwen ~/.mistralcode ~/.vibe` pour tester
- [ ] Verifier que les symlinks .qwen et .vibe fonctionnent
- [ ] Verifier que `.vibe/.env` (secret) n'est PAS inclus
- [ ] Verifier que les fichiers runtime ne sont pas inclus

## Decisions a prendre

1. **`.codex/config.toml`**: template ou statique?
   - Les `[projects]` trust levels varient par machine -> template recommande

2. **`.agents/skills`**: `.chezmoiexternal.toml` (auto-update) ou copie statique?
   - External = coherent avec le pattern oh-my-zsh/powerlevel10k
   - Statique = plus simple, pas de deps reseau

3. **`.kiro/`**: ignorer entierement ou template argv.json?
   - Ignorer semble le plus sense (config triviale, UUID unique)

4. **`.mistralcode/config.json`**: statique ou template?
   - Statique semble OK (meme domaine partout)

5. **`.vibe/config.toml`**: statique ou template?
   - Contient `save_dir` avec path absolu -> template recommande (`.chezmoi.homeDir`)
   - Le reste (providers, models, tools) est probablement identique partout

6. **`.vibe/.env`**: comment gerer la MISTRAL_API_KEY?
   - Option A: ne pas tracker, chaque machine la set manuellement
   - Option B: template avec 1Password (`op read`)
   - Option C: la ref depuis `~/.zsh/00-env.zsh` (deja gere?)

7. **Windows**: tout ignorer pour ces 6 dirs?

## Resume visuel

| Dir | Tracker | Methode | Ignorer |
|-----|---------|---------|---------|
| `.codex/` | `config.toml` | template `.tmpl` | auth, cache, sessions, DB, skills |
| `.agents/` | `skills/*`, `.skill-lock.json` | external ou statique | - |
| `.qwen/` | `skills/*` (symlinks) | `symlink_` chezmoi | - |
| `.kiro/` | rien | ignorer tout | argv.json (UUID), extensions |
| `.mistralcode/` | `config.json`, `.mistralcoderc.json` | statique | dev_data, index, sessions |
| `.vibe/` | `config.toml`, `trusted_folders.toml`, `instructions.md` | template (path abs) | .env (secret!), logs, sessions, skills (symlinks) |
