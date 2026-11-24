# Sprint 3: Câblage fleet (double envoi, pull, notify-test)

## Meta

- **PRD:** `../spec.md`
- **Sprint:** 3 of 4
- **Depends on:** Sprint 1
- **Batch:** 2 (parallel with Sprint 2 — aucun fichier modifiable en commun)
- **Model:** sonnet
- **Estimated effort:** M
- **Revue obligatoire :** Jérôme relit les diffs de `fleet-agent.sh` / `fleet-agent.ps1` **avant fusion** (l'agent est réinstallé root sur tout le parc par `run_onchange_install-fleet-agent` dès la fusion sur `main`).

## Objective

Brancher le master fleet en double envoi ntfy + Telegram (sujet `fleet`), ajouter
`fleet notify-test`, faire notifier le mode pull Unix et Windows sur Telegram, et
documenter le tout dans `docs/FLEET.md`.

## File Boundaries

### Creates (new files)

- (aucun)

### Modifies (can touch)

- `dot_local/share/fleet/lib/orchestrate.py` — `_make_notifier` multi-canal (`:781-790`), sous-commande `notify-test` (`:745-771`)
- `dot_local/share/fleet/agent/fleet-agent.sh` — `pull_notify` (`:1117-1143`) : Telegram en plus de ntfy
- `dot_local/share/fleet/agent/fleet-agent.ps1` — `Send-PullNotification` (`:997-1017`) : Telegram en plus de ntfy
- `dot_local/bin/executable_fleet` — transmettre `notify-test` (`:215`), aide (`:11`, `:75`)
- `dot_config/systemd/user/fleet-reminder.service` — description et commentaire d'environnement (`FLEET_TELEGRAM_*`)
- `docs/FLEET.md` — notifications Telegram, pull.conf, notify-test, rotation du jeton, liste des actions manuelles
- `scripts/test_fleet_orchestrate.py` — canaux construits, double envoi, notify-test
- `scripts/test_fleet_pull.py` — pull Telegram (faux curl), non-fuite du jeton
- `scripts/test_fleet_windows_contract.py` — contrat statique du pull Windows

### Read-Only (reference but do NOT modify)

- `dot_local/share/fleet/lib/notify.py` — `NtfyChannel`, `TelegramChannel`, `Notifier(channels)`, `resolve_telegram` (sprint 1)
- `dot_local/share/fleet/lib/inventory.py` — schéma `telegram:` (sprint 1)
- `dot_local/share/fleet/lib/schema.py` — masquage (sprint 1)
- `dot_local/share/fleet/fleet.yml` — bloc `telegram:` (sprint 1) ; `ntfy.gateway` reste jusqu'au sprint 4
- `dot_local/share/fleet/agent/fleet-bootstrap.ps1` — crée le dossier d'état qui contient `pull.conf` et le fichier jeton
- `.chezmoiscripts/03-configure/run_onchange_install-fleet-agent.sh.tmpl` — installation root (ne pas toucher)

### Shared Contracts (consume from prior sprints or PRD)

- `Notifier(channels)` ; `send(msg) -> bool` ; `flush() -> int` ; builders `summary_message`, `stale_message`, `not_back_message`, `refused_message`, `pull_message`, `reminder_message`.
- `fleet.yml` `telegram: {token_ref, chat_ref, thread_ref}` ; surcharges `FLEET_TELEGRAM_TOKEN`, `FLEET_TELEGRAM_CHAT_ID`, `FLEET_TELEGRAM_THREAD_ID`.
- `pull.conf` : `TELEGRAM_CHAT_ID` (`^-100[0-9]{5,}$`), `TELEGRAM_THREAD_ID` (`^[0-9]{1,10}$`, facultatif), `TELEGRAM_TOKEN_FILE` (1ʳᵉ ligne = `^[0-9]{6,}:[A-Za-z0-9_-]{30,}$`).
- Texte : `[<host>] fleet pull update\n<message>` en texte brut, `disable_notification=true` (priorité 2), `disable_web_page_preview=true`.
- Catalogue des événements F1-F7 (PRD §12) ; F2/F3/F4 testables par `fleet notify-test --event stale|not-back|refused`.

### Consumed Invariants (from INVARIANTS.md)

- Jeton jamais en argv — `python3 -m pytest -q scripts/test_fleet_pull.py`
- Validation stricte du jeton (pull) — motif ancré présent dans les deux agents
- Références op:// seulement — `fleet.yml` inchangé ici
- Verbes de l'agent (invariant racine `INVARIANTS.md`) — **aucun verbe ajouté** (`check update reboot-status reboot report`)

## Tasks

**Master (`orchestrate.py`)**

- [ ] Tests d'abord dans `scripts/test_fleet_orchestrate.py` (expéditeurs simulés, faux `op`).
- [ ] `_make_notifier` : construit `NtfyChannel` si `ntfy:` présent et `TelegramChannel` si `telegram:` présent (résolution via `notify.resolve_telegram`), files `st.root / "ntfy-queue"` et `st.root / "telegram-queue"` ; un canal invalide ⇒ message `fleet: telegram notifications disabled: <raison sans valeur>` et l'autre canal continue ; aucun canal ⇒ `None` (comportement actuel). Jamais construit pour `--dry-run` (aucun `op read`, existant).
- [ ] `notify-test [--event summary|stale|not-back|refused|pull|reminder]` (défaut `summary`) : construit le message avec le **vrai** builder et des données factices, préfixe `[TEST] ` au titre, envoie à chaque canal, affiche une ligne par canal `channel=<c> result=sent|queued|bad` ; code 1 si un canal n'a pas livré.
- [ ] Ne pas changer les phases : `ntfy.gateway` (`:327`) reste jusqu'au sprint 4.
- [ ] `dot_local/bin/executable_fleet` : ajouter `notify-test` à la liste transmise (`:215`) et à l'aide ; remplacer « ntfy » par « notification » dans les lignes d'aide `:11` et `:75`.
- [ ] `fleet-reminder.service` : description « reminder notification if no fleet up for 14 days … » ; commentaire : `FLEET_TELEGRAM_TOKEN` / `FLEET_TELEGRAM_CHAT_ID` / `FLEET_TELEGRAM_THREAD_ID` ou session 1Password dans `~/.config/fleet/env` (inchangé : `EnvironmentFile=-…`).

**Agent Unix (`fleet-agent.sh`)** — **revue Jérôme avant fusion**

- [ ] Tests d'abord dans `scripts/test_fleet_pull.py` (faux `curl` qui enregistre argv + stdin, comme l'existant).
- [ ] `pull_notify` : garder la branche ntfy telle quelle ; ajouter une branche Telegram indépendante lue par `conf_value` (jamais sourcé) : valider `TELEGRAM_CHAT_ID`, `TELEGRAM_THREAD_ID`, lire la 1ʳᵉ ligne de `TELEGRAM_TOKEN_FILE` et exiger le motif **ancré complet** `^[0-9]{6,}:[A-Za-z0-9_-]{30,}$` (ne pas réutiliser ni élargir la regex ntfy `^[A-Za-z0-9_.-]+$`) ; fichier jeton non régulier, illisible ou invalide ⇒ journal `pull notify: no valid telegram settings`, pas d'envoi.
- [ ] Envoi par `curl -K -` sur stdin : `url = "https://api.telegram.org/bot<token>/sendMessage"`, `data-urlencode = "chat_id=…"`, `message_thread_id`, `disable_notification=true`, `text` (même texte filtré `tr -d '"\\\r\n'` que l'existant) ; jamais en argv ; échec ⇒ `log auth.warning "pull notify: telegram delivery failed"` sans corps de réponse.
- [ ] POSIX / bash 3.2 conservé (le script tourne aussi sur macOS) ; `shellcheck`.
- [ ] Ne toucher à aucun verbe, à aucun chemin d'installation, à aucun appel sudo.

**Agent Windows (`fleet-agent.ps1`)** — **revue Jérôme avant fusion**

- [ ] Tests d'abord dans `scripts/test_fleet_windows_contract.py` (contrat statique, comme l'existant `:237-238`).
- [ ] `Send-PullNotification` : branche Telegram indépendante de ntfy : `Get-ConfValue` pour les trois clés, mêmes validations (motif ancré), `Invoke-RestMethod -Method Post -Uri ('https://api.telegram.org/bot' + $token + '/sendMessage') -Body @{ chat_id=…; message_thread_id=…; text=…; disable_notification='true' }` (TLS 1.2, `-TimeoutSec 15`, `-UseBasicParsing`) ; `catch` à message fixe `pull notify: telegram delivery failed` (ne jamais écrire `$_`, qui contient l'URI avec le jeton).
- [ ] PowerShell 5.1 ; PSScriptAnalyzer si disponible, sinon BLOCKED (noté).

**Documentation `docs/FLEET.md`**

- [ ] Section Notifications : deux canaux pendant la transition, bloc `telegram:` de `fleet.yml`, files `ntfy-queue/` et `telegram-queue/`, 429 / `retry_after`, repli « sujet introuvable », silencieux pour priorité ≤ 2.
- [ ] Mode pull (`:322-337`) : clés `TELEGRAM_*` de `pull.conf`, fichier jeton 0600 (Unix) / ACL du dossier d'état (Windows), procédure de pose manuelle.
- [ ] `fleet notify-test` dans la table des commandes.
- [ ] Rotation / révocation du jeton (PRD §10) et liste des actions manuelles (élément 1Password `Telegram`, `pull.conf` par hôte pull).

## Acceptance Criteria

- [ ] Avec `ntfy:` et `telegram:` configurés, une synthèse part sur les deux canaux ; Telegram en échec transitoire ⇒ message en `telegram-queue/`, ntfy livré quand même (test).
- [ ] `fleet notify-test --event refused` utilise `refused_message` et préfixe `[TEST]` ; code 1 si un canal ne livre pas.
- [ ] `--dry-run` n'appelle jamais `op` (test existant toujours vert).
- [ ] Pull Unix : Telegram et ntfy envoyés indépendamment ; jeton absent d'argv et des journaux ; jeton malformé ou avec caractère hors motif ⇒ pas d'envoi.
- [ ] Pull Windows : le contrat statique vérifie la validation ancrée, l'absence de `$_` dans le `catch` et le corps `chat_id`/`text`.
- [ ] Aucun verbe d'agent ajouté ; invariant racine « Verbes de l'agent » vert.
- [ ] `docs/FLEET.md` documente `notify-test`, les clés `pull.conf` et la rotation.

## Verification

- [ ] `uvx pytest scripts/test_fleet_*.py` (ou `python3 -m pytest -q scripts/test_fleet_*.py`)
- [ ] `bash -n dot_local/share/fleet/agent/fleet-agent.sh` + `shellcheck` (0 nouveau constat)
- [ ] `bash -n dot_local/bin/executable_fleet`
- [ ] Commandes `Verify` de `../INVARIANTS.md` : « Jeton jamais en argv », « Validation stricte du jeton (pull) » ; et de `INVARIANTS.md` racine : « Verbes de l'agent »
- [ ] Manuel (Jérôme — BLOCKED pour l'agent) : revue des diffs agents avant fusion ; `fleet notify-test` puis `--event stale|not-back|refused` ; un run pull réel Linux et Windows ; `fleet reminder` forcé

> **Note:** Dev server smoke test and content verification are handled by the orchestrator
> after merge — do not run in the sprint-executor. Sprint-executors do static verification only.

## Context

- Double envoi jusqu'au sprint 4 (décision Jérôme) : les deux canaux ont chacun leur
  file pour qu'une panne de l'un ne bloque jamais l'autre.
- Toutes les machines ont un accès Internet direct : chaque agent pull poste lui-même
  à `api.telegram.org` (pas de relais par le master).
- Le jeton est dans le **chemin** de l'URL Telegram : toute exception, en Python
  comme en PowerShell, peut le contenir ⇒ messages d'erreur fixes uniquement.
- `notify.py` (sprint 1) garde un alias de compatibilité pour l'ancien constructeur ;
  ce sprint passe à `Notifier(channels)`.
- ACL Windows du dossier d'état (fichier jeton du mode pull) : c'est un stockage de
  secret ⇒ toute modification d'ACL existante, au-delà de documenter la pose manuelle,
  relève de « arrêter et demander ».
- Topic actuel : fleet publie sur `topic: fleet` (`orchestrate.py:787`), pas sur
  `chezmoi-fleet` (topic de `chezmoi-autoupdate`) ; le rappel (`fleet reminder`) passe
  par le même `Notifier` ⇒ bot d'envoi seul, sujet `fleet`.
- Aucun `getUpdates` / `setWebhook` (D15).
- Sudoers / ACL : ce sprint n'en modifie aucun. Si une tâche semble l'exiger ⇒
  arrêter et demander (politique du PRD). Idem pour tout changement du modèle de
  stockage du fichier jeton.

## Agent Notes (filled during execution)

- Assigned to:
- Started:
- Completed:
- Decisions made:
- Assumptions:
- Issues found:
