# Sprint 2: chezmoi-autoupdate, config générée, media, docs env

## Meta

- **PRD:** `../spec.md`
- **Sprint:** 2 of 4
- **Depends on:** Sprint 1
- **Batch:** 2 (parallel with Sprint 3 — aucun fichier modifiable en commun)
- **Model:** sonnet
- **Estimated effort:** M

## Objective

Faire enfin arriver les erreurs de `chezmoi-autoupdate` planifié (sujet `chezmoi`,
1 message par signature d'erreur et par 24 h), supprimer la Phase E, fournir la
config utilisateur `~/.config/agent-alert.conf` générée depuis 1Password, router
`media_automation` vers le sujet `media`, et mettre à jour la documentation
d'environnement.

## File Boundaries

### Creates (new files)

- `scripts/test_chezmoi_autoupdate_alert.py` — tests de la Phase D (faux `agent-alert`, limiteur 24 h, absence de Phase E)

### Modifies (can touch)

- `dot_local/bin/executable_chezmoi-autoupdate` — Phase D via `agent-alert`, limiteur, Phase E supprimée, curl ntfy supprimés, en-tête
- `dot_local/bin/executable_dotfiles-generated-config` — nouvelle sorte `alert` (**secrets : seulement si Q1 validée**)
- `.chezmoiscripts/03-configure/run_onchange_generate-secrets.sh.tmpl` — appeler aussi `dotfiles-generated-config alert`
- `scripts/test_generated_config.py` — tests de la sorte `alert`
- `docs/GENERATED_CONFIG.md` — documenter la sorte `alert`
- `dot_config/systemd/user/chezmoi-autoupdate.service` — commentaire `EnvironmentFile` (plus lié aux notifications)
- `bin/executable_media_automation.py` — `thread_id` Telegram, journalisation sans exception brute
- `bin/test_media_automation.py` — tests sujet + non-fuite
- `dot_zsh/00-env.zsh.tmpl` — retirer la doc `CHEZMOI_NTFY_*` (`:257-260`), pointer vers `agent-alert`
- `dot_local/bin/executable_cminventory` — retirer l'indice ntfy (`:72-77`)
- `docs/RUNBOOK.md` — section notifications (`:479-516`, `:579`) : Telegram via `agent-alert`, plus de heartbeat
- `dot_config/systemd/README.md` — notifications de `chezmoi-autoupdate` (`:176-184`, `:267-272`)
- `dot_local/bin/README.md` — section chezmoi-autoupdate (`:353-357`), section Alerting (`:784-800`), rotation du jeton
- `README.md` — lignes `:495-496` (notifications, heartbeat)

### Read-Only (reference but do NOT modify)

- `dot_local/bin/executable_agent-alert` — contrat CLI (livré au sprint 1)
- `Library/private_LaunchAgents/com.jsoyer.chezmoi-autoupdate.plist.tmpl` — passe `HOME` et `PATH` (avec `~/.local/bin`) : suffisant pour que `agent-alert` lise `~/.config/agent-alert.conf`
- `.chezmoiscripts/03-configure/run_once_enable-chezmoi-autoupdate.ps1.tmpl` — Windows : hors périmètre (pas d'`agent-alert` sur Windows)
- `scripts/test_chezmoi_autoupdate_dirs.py` — modèle d'extraction de fonction bash pour tester
- `.chezmoiignore.tmpl` — confirmer que `agent-alert` est déployé sur macOS (sprint 1)

### Shared Contracts (consume from prior sprints or PRD)

- CLI `agent-alert [--category C] [--title T] [--priority low|default|high] [--strict] "message"` ; n'échoue jamais sans `--strict` ; catégorie `chezmoi`.
- Clés : `ALERT_BACKEND`, `ALERT_TELEGRAM_BOT_TOKEN`, `ALERT_TELEGRAM_CHAT_ID`, `ALERT_TELEGRAM_THREAD_FLEET|AGENTS|CHEZMOI|MEDIA`, `ALERT_NTFY_URL`, `ALERT_NTFY_TOKEN`.
- Élément 1Password `op://Private/Telegram` : champs `bot-token`, `chat-id`, `thread-fleet`, `thread-agents`, `thread-chezmoi`, `thread-media`.
- Motif de jeton `^[0-9]{6,}:[A-Za-z0-9_-]{30,}$` ; `chat_id` `^-100[0-9]{5,}$` ; sujet `^[0-9]{1,10}$`.

### Consumed Invariants (from INVARIANTS.md)

- Plus de battement de cœur — aucune « Phase E » dans `chezmoi-autoupdate`
- Portabilité bash 3.2 — `chezmoi-autoupdate` tourne aussi sur macOS
- Catégories — `chezmoi` et `media` utilisées telles quelles

## Tasks

**chezmoi-autoupdate** (Phase D `:381-423`, Phase E `:425-442`)

- [ ] Test d'abord : `scripts/test_chezmoi_autoupdate_alert.py` extrait la fonction de notification (même technique que `test_chezmoi_autoupdate_dirs.py`) et l'exécute avec un faux `agent-alert` dans `PATH` qui enregistre argv.
- [ ] Remplacer D2 (curl ntfy) par une fonction `notify_error` : si `command -v agent-alert`, appeler `agent-alert --category chezmoi --priority high --title "chezmoi-autoupdate error" -- "<résumé>"` ; sortie ajoutée à `LOG_FILE` ; jamais d'échec du script.
- [ ] Limiteur (D10) : signature = `sha256` du résumé **sans horodatages** (`shasum -a 256` sur macOS, `sha256sum` sinon) ; fichier `~/.cache/chezmoi-autoupdate/last-alert` (`<hash> <epoch>`, 0600) ; envoyer si hash différent ou si > 86400 s ; sur un run `ok` qui suit une erreur, supprimer le fichier (la prochaine erreur repart tout de suite).
- [ ] Garder D1 (notification bureau) tel quel ; supprimer les commentaires D3/D4 obsolètes et l'en-tête `CHEZMOI_NTFY_*` (`:10-11`, `:17-19`), documenter `agent-alert` à la place.
- [ ] Supprimer la Phase E entière (`:425-442`) et sa ligne d'en-tête.
- [ ] bash 3.2 : pas de bash4-isme ajouté ; `bash -n` ; `shellcheck`.
- [ ] `chezmoi-autoupdate.service` : réécrire le commentaire `EnvironmentFile` (le fichier reste facultatif, il ne sert plus aux notifications ; `agent-alert` lit `~/.config/agent-alert.conf`).

**Config générée** (D7) — **Q1 validée par Jérôme le 2026-11-24 (option A) : bloc à implémenter**

- [ ] Vérifier dans la PR / `../spec.md` §14 que Q1 est cochée ; sinon sauter ce bloc, le marquer BLOCKED (Q1) et documenter `agent-alert --configure` comme seule voie.
- [ ] `dotfiles-generated-config alert` : un seul `op item get Telegram --vault Private --format=json` (même parseur que `secret_values`, champs `bot-token`, `chat-id`, `thread-*`) ; valider jeton, chat, sujets (motifs ci-dessus) ; écrire `~/.config/agent-alert.conf` 0600 par `publish()` (atomique, ancien fichier conservé si échec), en-tête `# Generated from 1Password; refresh with: dotfiles-generated-config alert`.
- [ ] Transition : si le fichier actuel contient `ALERT_NTFY_URL` / `ALERT_NTFY_TOKEN` (ou s'ils sont présents dans `Shell Secrets` comme `CHEZMOI_NTFY_URL`+`CHEZMOI_NTFY_TOPIC`+`CHEZMOI_NTFY_TOKEN`), les reprendre et mettre `ALERT_BACKEND="ntfy,telegram"` ; sinon `ALERT_BACKEND="telegram"`. Un fichier existant **sans** l'en-tête « Generated » est sauvegardé en `.bak` avant remplacement.
- [ ] Ne jamais imprimer de valeur ; message final : `agent-alert config generated (telegram[, ntfy])`.
- [ ] `run_onchange_generate-secrets.sh.tmpl` : après `secrets`, appeler `alert` (même garde `op` connecté ; échec ⇒ message, pas d'arrêt).
- [ ] Tests dans `scripts/test_generated_config.py` : faux `op` ; fichier 0600 ; valeurs invalides ⇒ ancien fichier intact ; ntfy repris ; aucune valeur dans stdout/stderr.
- [ ] `docs/GENERATED_CONFIG.md` : sorte `alert`, champs 1Password, hôtes sans `op` ⇒ `agent-alert --configure`, root ⇒ `sudo agent-alert --configure --system`.

**media_automation** (`TelegramConfig` `:182-189`, `send_telegram_message` `:542-562`)

- [ ] Tests d'abord dans `bin/test_media_automation.py` (`urlopen` simulé).
- [ ] `TelegramConfig.thread_id: str | None` lu depuis `[telegram] thread_id` puis env `TELEGRAM_THREAD_ID` ; envoyé en `message_thread_id` s'il vérifie `^[0-9]{1,10}$` (sinon ignoré avec avertissement).
- [ ] Repli « sujet introuvable » (400 dont le corps contient `thread`) : renvoyer le morceau une fois sans `message_thread_id`, préfixé `[sujet media introuvable] `.
- [ ] Journalisation : `LOGGER.warning("Telegram notification failed: %s", type(exc).__name__)` (+ code HTTP si `HTTPError`) ; test qui vérifie que le jeton n'apparaît pas dans le journal quand `urlopen` lève une exception contenant l'URL.
- [ ] Ne pas toucher à `NtfyConfig` (double envoi jusqu'au sprint 4).

**Documentation**

- [ ] `dot_zsh/00-env.zsh.tmpl:257-262` : retirer `CHEZMOI_NTFY_*`, indiquer que les alertes passent par `agent-alert` (config `~/.config/agent-alert.conf`) ; garder `TELEGRAM_BOT_TOKEN/CHAT_ID` (autres outils).
- [ ] `executable_cminventory:72-77` : supprimer le bloc « Ntfy hint ».
- [ ] `docs/RUNBOOK.md`, `dot_config/systemd/README.md`, `dot_local/bin/README.md`, `README.md` : remplacer la doc ntfy/heartbeat de `chezmoi-autoupdate` par `agent-alert --category chezmoi` + limiteur ; dans `dot_local/bin/README.md` (Alerting) : multi-backend, catégories, contextes utilisateur/root, procédure de rotation du jeton (§10 du PRD). Laisser les mentions fleet de `README.md:539-540` au sprint 4.

## Acceptance Criteria

- [ ] Run en erreur ⇒ faux `agent-alert` appelé une fois avec `--category chezmoi --priority high` ; deuxième run, même erreur < 24 h ⇒ aucun appel ; erreur différente ⇒ appel ; run ok ⇒ `last-alert` supprimé.
- [ ] `grep -c 'Phase E' dot_local/bin/executable_chezmoi-autoupdate` = 0 et aucun `curl` vers ntfy dans ce fichier.
- [ ] Sans `agent-alert` dans `PATH`, le script finit avec le même code qu'avant (pas d'erreur ajoutée).
- [ ] (Si Q1) `dotfiles-generated-config alert` écrit un fichier 0600 valide ; une lecture `op` en échec laisse l'ancien fichier intact ; aucune valeur imprimée.
- [ ] `media_automation` envoie `message_thread_id` quand configuré ; aucun jeton dans le journal.
- [ ] Plus aucune mention `CHEZMOI_NTFY` dans `dot_zsh/00-env.zsh.tmpl`, `executable_cminventory`, `docs/RUNBOOK.md`, `dot_config/systemd/README.md`.

## Verification

- [ ] `python3 -m pytest -q scripts/test_chezmoi_autoupdate_alert.py`
- [ ] `python3 scripts/test_chezmoi_autoupdate_dirs.py`
- [ ] `python3 scripts/test_generated_config.py`
- [ ] `python3 -m pytest -q bin/test_media_automation.py`
- [ ] `bash -n dot_local/bin/executable_chezmoi-autoupdate` + `shellcheck` (0 nouveau constat)
- [ ] Commandes `Verify` de `../INVARIANTS.md` : « Plus de battement de cœur », « Portabilité bash 3.2 »
- [ ] Manuel (Jérôme, après fusion — BLOCKED pour l'agent) : provoquer une erreur sur `fedora-pve` (hôte sans écran, sans `op` ⇒ `agent-alert --configure` d'abord) et vérifier la réception dans le sujet `chezmoi` ; ajouter `thread_id` au TOML média (Q3) et vérifier M1.

> **Note:** Dev server smoke test and content verification are handled by the orchestrator
> after merge — do not run in the sprint-executor. Sprint-executors do static verification only.

## Context

- Cause racine du trou d'alerte : `CHEZMOI_NTFY_TOPIC` n'existe que dans
  `~/.zsh/secrets.zsh` ; ni l'unité systemd (`EnvironmentFile` que rien ne crée), ni
  la LaunchAgent (PATH/HOME/SSH_AUTH_SOCK), ni la tâche Windows ne la fournissent.
  `agent-alert` lit un fichier de config par `HOME` : ça marche sous systemd user et
  launchd.
- Contextes de config (PRD §11) : utilisateur = `~/.config/agent-alert.conf` (généré
  ou `--configure`) ; root = `/etc/agent-alert.conf` (`sudo agent-alert --configure --system`,
  jamais généré par chezmoi). `chezmoi-autoupdate` tourne en utilisateur.
- « Rater une alerte est pire qu'un doublon » mais « spam qui noie les alertes » est
  aussi un échec : d'où le limiteur par signature, pas par temps seul.
- Le générateur `dotfiles-generated-config` gère des secrets : même discipline que
  `generate_secrets` (`:175-212`) — une lecture `op`, validation, publication
  atomique, rien d'imprimé. Python 3.9 (`from __future__ import annotations` déjà là).
- `media_automation` exige Python ≥ 3.11 (`tomllib`) ; son TOML vit sur l'hôte média.
- Politique : signaler et continuer, **sauf** secrets (bloc « Config générée ») ⇒
  arrêter et demander si Q1 n'est pas validée ou si une question nouvelle sur les
  secrets apparaît.

## Agent Notes (filled during execution)

- Assigned to:
- Started:
- Completed:
- Decisions made:
- Assumptions:
- Issues found:
