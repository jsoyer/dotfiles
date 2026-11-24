# Sprint 1: Émetteurs communs (agent-alert, transport fleet, egress)

## Meta

- **PRD:** `../spec.md`
- **Sprint:** 1 of 4
- **Depends on:** None (sprint 0 manuel requis seulement pour les essais réels)
- **Batch:** 1 (sequential)
- **Model:** sonnet
- **Estimated effort:** L

## Objective

Rendre les deux émetteurs partagés capables d'envoyer sur Telegram, dans le bon
sujet, sans fuite de jeton, en gardant ntfy pour le double envoi : `agent-alert`
(bash, Linux + macOS) et le transport de `dot_local/share/fleet/lib/notify.py`
(Python 3.9 stdlib) ; plus un script de vérification de sortie Internet.

## File Boundaries

### Creates (new files)

- `scripts/telegram_egress_check.py` — vérification de sortie vers api.telegram.org, hôte par hôte
- `scripts/test_telegram_egress_check.py` — tests avec runner SSH simulé

### Modifies (can touch)

- `dot_local/bin/executable_agent-alert` — multi-backend, `--category`, sujets, portabilité bash 3.2, filtre de jetons
- `scripts/test_agent_alert.py` — nouveaux cas (multi-backend, catégories, macOS stat, non-fuite)
- `.chezmoiignore.tmpl` — déployer `agent-alert` sur macOS (reste ignoré sur Windows)
- `.chezmoiscripts/02-install/run_once_12-disable-macos-agent-stacks.sh.tmpl` — retirer `agent-alert` de la liste de suppression
- `dot_local/share/fleet/lib/notify.py` — canaux `NtfyChannel` / `TelegramChannel`, `Notifier` multi-canal
- `dot_local/share/fleet/lib/schema.py` — motif de masquage du jeton Telegram
- `dot_local/share/fleet/lib/inventory.py` — validation du bloc `telegram:`
- `dot_local/share/fleet/fleet.yml` — ajout du bloc `telegram:` (références op:// seulement)
- `scripts/test_fleet_report.py` — tests du transport Telegram et du masquage
- `scripts/test_fleet_inventory.py` — tests du schéma `telegram:`

### Read-Only (reference but do NOT modify)

- `dot_local/share/fleet/lib/orchestrate.py` — construction actuelle du `Notifier` (`_make_notifier` `:781-790`) : l'API publique doit rester compatible jusqu'au sprint 3
- `dot_local/share/fleet/lib/state.py` — `make_private_dir`, `write_private`, `utcnow`
- `scripts/test_t3_paseo.py` — `SandboxCase`, `LOGGER` utilisés par `test_agent_alert.py`
- `scripts/test_orca_headless.py` — exige encore `Authorization: Bearer`, `ORCA_ALERT_TOKEN`, `/etc/orca-alert.conf` dans `agent-alert` : ne rien casser
- `dot_local/bin/executable_orca-setup`, `dot_local/bin/executable_paseo-setup` — installent la copie root `/usr/local/bin/agent-alert`

### Shared Contracts (consume from prior sprints or PRD)

- Catégories : `fleet`, `agents`, `chezmoi`, `media` ; défaut `agents`.
- CLI : `agent-alert [--category C] [--title T] [--priority low|default|high] [--tags a,b] [--strict] "message"` ; `--configure [--system]` ; `--test [--category C]`. Codes 0 / 1 (strict ou test : un backend au moins a échoué) / 2 usage.
- Sortie `--test` : une ligne par backend `backend=<b> config=<fichier> category=<c> chat=…<4 derniers chiffres> thread=<id|general> result=ok|fail` (sur stderr), jamais le jeton.
- Clés : `ALERT_BACKEND` (liste à virgules de `ntfy`, `telegram`, `none`), `ALERT_TELEGRAM_BOT_TOKEN`, `ALERT_TELEGRAM_CHAT_ID`, `ALERT_TELEGRAM_THREAD_FLEET|AGENTS|CHEZMOI|MEDIA`, `ALERT_TELEGRAM_THREAD_ID` (défaut), `ALERT_NTFY_URL`, `ALERT_NTFY_TOKEN` (+ hérités `ORCA_ALERT_URL/TOKEN`).
- Texte Telegram : `[<host>] <titre>\n<message>`, `[URGENT] ` devant le titre si `--priority high`, ≤ 3900 caractères, texte brut (pas de `parse_mode`), `disable_web_page_preview=true`, `disable_notification=true` si `--priority low`.
- Motif de jeton : `[0-9]{6,}:[A-Za-z0-9_-]{30,}` ; dans une URL `bot[0-9]{6,}:[A-Za-z0-9_-]{30,}`.
- `chat_id` valide : `^-100[0-9]{5,}$` ; `thread_id` : `^[0-9]{1,10}$`.
- Fleet : builders de messages inchangés ; `TelegramChannel(token, chat_id, thread_id, queue_dir, sender=None, clock=…)`, `NtfyChannel(url, topic, token, queue_dir, sender=None, clock=…)`, interface `send(msg) -> bool`, `flush() -> int` ; `Notifier(channels)` diffuse à tous et retourne `True` si tous ont livré. Expéditeur Telegram injectable `sender(url: str, form: Dict[str, str]) -> Dict[str, Any]`.
- `fleet.yml` : `telegram: {token_ref: "op://Private/Telegram/bot-token", chat_ref: "op://Private/Telegram/chat-id", thread_ref: "op://Private/Telegram/thread-fleet"}` ; surcharges `FLEET_TELEGRAM_TOKEN`, `FLEET_TELEGRAM_CHAT_ID`, `FLEET_TELEGRAM_THREAD_ID`.

### Consumed Invariants (from INVARIANTS.md)

- Catégories — `grep` des 4 noms dans `agent-alert` et `notify.py`
- Jeton jamais en argv — `python3 scripts/test_agent_alert.py`
- Masquage jeton Telegram — motif présent dans `schema.py`
- Références op:// seulement — bloc `telegram:` de `fleet.yml`
- Portabilité bash 3.2 — aucun bash4-isme dans `agent-alert`

## Tasks

**agent-alert** (`dot_local/bin/executable_agent-alert`, état actuel : un backend, `stat -c %a` `:58`, Telegram sans sujet `:89-98`)

- [ ] Test d'abord (RED) dans `scripts/test_agent_alert.py` pour chaque point ci-dessous ; puis implémentation.
- [ ] `stat` portable : `stat -c %a` puis repli `stat -f %Lp` (BSD) ; si les deux échouent, traiter comme non sûr (comportement actuel). Test : faux `stat` BSD dans le bac à sable ⇒ config 0600 lue.
- [ ] `ALERT_BACKEND` en liste à virgules ; chaque backend envoyé indépendamment ; défaut inchangé (ntfy si une URL, sinon none ; telegram si jeton + chat et pas de backend). `none` combiné à un autre ⇒ ignoré. Backend inconnu dans la liste ⇒ avertissement, les autres partent.
- [ ] `--category` (validée contre la liste, sinon code 2) ; sujet = `ALERT_TELEGRAM_THREAD_<CAT>` (majuscules via `tr`, pas `${x^^}`), sinon `ALERT_TELEGRAM_THREAD_ID`, sinon sujet général. Valeur de sujet invalide ⇒ ignorée avec avertissement (sujet général).
- [ ] **Q5 confirmée par Jérôme le 2026-11-24 (D14), à implémenter** : lire en repli `TG_CHAT_ID` et `TG_THREAD_<CAT>` quand la clé `ALERT_TELEGRAM_*` correspondante est absente (jamais prioritaires), mêmes validations ; test dédié. Sans confirmation : ne pas implémenter, le noter dans les Agent Notes. Pas d'utilitaire `tg-notify` séparé.
- [ ] Envoi seul (D15) : aucun appel `getUpdates` / `setWebhook` ; le jeton utilisé est celui du bot d'envoi seul (`op://Private/Telegram/bot-token`).
- [ ] `send_telegram` : `message_thread_id`, `disable_notification`, `disable_web_page_preview`, préfixe `[URGENT] ` ; jeton seulement dans la config curl sur stdin (existant). Repli « sujet introuvable » : si la réponse est un 400 dont le corps contient `thread`, renvoyer une fois sans `message_thread_id` avec le préfixe `[sujet <cat> introuvable] ` (utiliser `curl -sS -w '%{http_code}' -o <fichier 0600>` au lieu de `-f` pour lire le corps ; ne jamais afficher ce corps brut).
- [ ] Filtre de jetons sur le message et le titre avant envoi (Telegram **et** ntfy) : remplacer `[0-9]{6,}:[A-Za-z0-9_-]{30,}` et `tk_[A-Za-z0-9_-]{6,}` par `[MASKED]` (sed -E, portable).
- [ ] `--strict` / `--test` : code 1 si au moins un backend a échoué ; `--test` imprime une ligne par backend au format du contrat (chat masqué sauf 4 derniers chiffres).
- [ ] `--configure` : choix `telegram` demande aussi les 4 identifiants de sujet (vides permis) ; **conserve** les clés ntfy existantes du fichier cible et met alors `ALERT_BACKEND="ntfy,telegram"` ; valide le jeton avec le motif complet et `chat_id` avec `^-100[0-9]{5,}$` ; `umask 077`, `.bak` conservé (existant).
- [ ] Passe bash 3.2 : pas de `declare -A`, `mapfile`, `readarray`, `${x,,}`, `${x^^}`, `&>>`, `|&` ; tableaux vides via `${a[@]+"${a[@]}"}`. Ajouter un test statique qui échoue si un de ces motifs apparaît.
- [ ] Mettre à jour l'en-tête d'aide (usage, clés, catégories) en anglais comme l'existant.

**Déploiement macOS**

- [ ] `.chezmoiignore.tmpl:270` : retirer `.local/bin/agent-alert` du bloc `ne .chezmoi.os "linux"` et l'ajouter à un bloc `eq .chezmoi.os "windows"` (ou équivalent) pour qu'il reste ignoré sur Windows.
- [ ] `run_once_12-disable-macos-agent-stacks.sh.tmpl:41` : retirer `"${HOME}/.local/bin/agent-alert"` de la liste. Effet connu et accepté : le contenu change ⇒ le script repasse **une fois** sur chaque Mac ; il est idempotent (rm si présent, `launchctl bootout` toléré). Le noter dans le message de commit.
- [ ] Vérifier `chezmoi execute-template` (ou `chezmoi cat` avec données mac) si disponible ; sinon BLOCKED et le noter.

**fleet `notify.py`** (état actuel : `Notifier(url, topic, token, queue_dir, sender, clock)` ntfy seul, `:206-309`)

- [ ] Tests d'abord dans `scripts/test_fleet_report.py` (là où vivent les tests `notify`), expéditeur simulé, aucun réseau.
- [ ] Extraire l'existant en `NtfyChannel` (comportement et file `ntfy-queue/` inchangés) ; garder un alias de compatibilité pour que `orchestrate.py:787` (`notify.Notifier(url, topic, token, queue_dir)`) fonctionne sans modification jusqu'au sprint 3.
- [ ] `TelegramChannel` : URL `https://api.telegram.org/bot<token>/sendMessage` construite au moment de l'envoi (jamais stockée dans la file ni dans un attribut journalisé), formulaire `chat_id`, `message_thread_id` (si défini), `text` = `title + "\n" + body` tronqué à 3900, `disable_notification` = `"true"` si `priority <= 2`, `disable_web_page_preview` = `"true"`, préfixe `[URGENT] ` si `priority >= 5`. Pas de redirection (`_NoRedirect`), timeout 10 s.
- [ ] Classement : réseau, 5xx, 401, 403, 404, 408 ⇒ `retry` ; 429 ⇒ `retry` + écrire `telegram-queue/.retry-after` (epoch now + `parameters.retry_after`, borné à 3600) ; tant que ce délai court, `send` met en file sans appeler l'expéditeur ; 400 dont `description` contient `thread` ⇒ un renvoi sans `message_thread_id`, préfixé `[sujet fleet introuvable] `, puis `bad` si nouvel échec ; autre 400 ⇒ `bad` (`.bad`).
- [ ] Aucune exception ne remonte avec l'URL : n'utiliser que `exc.code` et la classe ; tests qui vérifient que le jeton n'apparaît dans aucun fichier de la file, ni dans `repr`/`str` des erreurs relevées par `Notifier`.
- [ ] File `telegram-queue/` 0700, fichiers 0600 (`fstate.make_private_dir` / `write_private`), `flock` comme `ntfy-queue/`.
- [ ] `Notifier(channels)` : envoie à chaque canal ; un canal en échec n'empêche pas l'autre ; `True` seulement si tous livrent ; `flush()` vide chaque file.
- [ ] `resolve_telegram(cfg, env, runner)` : `FLEET_TELEGRAM_TOKEN/CHAT_ID/THREAD_ID` sinon `op read` des trois références ; valide jeton (motif), chat (`^-100[0-9]{5,}$`), sujet (`^[0-9]{1,10}$`, facultatif) ; invalide ⇒ `None` + raison sans valeur.

**fleet `schema.py`, `inventory.py`, `fleet.yml`**

- [ ] `schema.py:61-62`, `:108` : ajouter `_TELEGRAM_TOKEN = re.compile(r"(?<![0-9])[0-9]{6,}:[A-Za-z0-9_-]{30,}")` (couvre aussi `bot<token>` dans une URL) appliqué dans `mask_secrets` ; tests : jeton nu, dans une URL, dans du JSON ; un horodatage `12:34:56` ou `2026-11-24T17:57:00` n'est **pas** masqué.
- [ ] `inventory.py:270-296` : valider `telegram` (mapping ; `token_ref`, `chat_ref` requis, `thread_ref` facultatif ; tous `op://`) ; `ntfy` reste accepté ; tests dans `test_fleet_inventory.py`.
- [ ] `fleet.yml` : ajouter la ligne `telegram: {token_ref: "op://Private/Telegram/bot-token", chat_ref: "op://Private/Telegram/chat-id", thread_ref: "op://Private/Telegram/thread-fleet"}` sous le bloc `ntfy`, avec un commentaire d'une ligne.

**Egress**

- [ ] `scripts/telegram_egress_check.py` (Python 3.9 stdlib) : charge `fleet.yml` via `dot_local/share/fleet/lib/inventory.py` (import en lecture), retient les hôtes avec `ssh_user` et un `kind` à agent (`chezmoi-linux`, `chezmoi-macos`, `omv`, `pikvm`, `guardian`, `windows`, `proxmox`), lance `ssh -o BatchMode=yes -o ConnectTimeout=5 <ssh_user>@<tailnet_name> <probe>` (probe Unix `curl -s -o /dev/null -w '%{http_code}' --max-time 10 https://api.telegram.org/`, Windows `curl.exe` idem) **avec la config SSH de l'opérateur, pas la clé fleet**, aucun jeton ; options `--host`, `--dry-run` ; tableau `host  result(ok|fail|unreachable)  http_code` ; code 1 si un hôte `fail`.
- [ ] `scripts/test_telegram_egress_check.py` : runner injecté (aucun ssh réel) : ok (`302`/`200`), fail (`000`), unreachable (code ssh 255), `--dry-run` n'exécute rien, aucun `op`/jeton dans argv.

## Acceptance Criteria

- [ ] `ALERT_BACKEND=ntfy,telegram` envoie deux requêtes ; si ntfy échoue, Telegram part quand même (test faux curl).
- [ ] `--category chezmoi` avec `ALERT_TELEGRAM_THREAD_CHEZMOI=7` ⇒ `message_thread_id=7` dans la config curl ; `--category bogus` ⇒ code 2.
- [ ] Config 0600 lue avec un `stat` de type BSD ; config 0644 à jeton ignorée (les deux en test).
- [ ] Aucun jeton (`TG_TOKEN`, `NTFY_TOKEN`) dans argv curl, stdout, stderr (tests existants + nouveaux).
- [ ] Le test statique bash 3.2 passe sur `agent-alert`.
- [ ] `agent-alert` n'est plus ignoré sur macOS ni supprimé par `run_once_12`, et reste ignoré sur Windows.
- [ ] Fleet : 429 ⇒ file + `.retry-after` respecté ; 400 thread ⇒ repli puis `.bad` ; 401 ⇒ file conservée ; succès ⇒ file vide (tests).
- [ ] Aucun fichier de `telegram-queue/` ne contient le jeton, l'URL ou `chat_id` (test).
- [ ] `mask_secrets` masque un jeton Telegram nu et dans une URL, sans masquer un horodatage.
- [ ] `fleet.yml` avec le bloc `telegram:` passe la validation ; une valeur non `op://` est rejetée.
- [ ] `orchestrate.py` inchangé et `uvx pytest scripts/test_fleet_*.py` vert (compatibilité de l'API `Notifier`).
- [ ] `scripts/test_telegram_egress_check.py` vert sans réseau.

## Verification

- [ ] `python3 scripts/test_agent_alert.py`
- [ ] `python3 scripts/test_orca_headless.py` (inchangé, doit rester vert)
- [ ] `uvx pytest scripts/test_fleet_*.py` (ou `python3 -m pytest -q scripts/test_fleet_*.py`)
- [ ] `python3 -m pytest -q scripts/test_telegram_egress_check.py`
- [ ] `bash -n dot_local/bin/executable_agent-alert` et `shellcheck dot_local/bin/executable_agent-alert` (0 nouveau constat)
- [ ] Commandes `Verify` de `../INVARIANTS.md` : « Catégories », « Masquage jeton Telegram », « Références op:// seulement », « Portabilité bash 3.2 » passent
- [ ] Manuel (Jérôme, après fusion, BLOCKED pour l'agent) : `agent-alert --test --category agents` sur un Linux et un Mac ; `python3 scripts/telegram_egress_check.py` sur le parc ; relancer `orca-setup` / `paseo-setup` sur les hôtes agents pour rafraîchir la copie root `/usr/local/bin/agent-alert`, puis `sudo agent-alert --configure --system` (ntfy conservé ⇒ double envoi)

> **Note:** Dev server smoke test and content verification are handled by the orchestrator
> after merge — do not run in the sprint-executor. Sprint-executors do static verification only.

## Context

- Décisions (PRD §9) : supergroupe unique à sujets ; envoi direct ; double envoi
  jusqu'au sprint 4 ; texte brut ; priorité basse ⇒ silencieux ; repli « sujet
  introuvable » plutôt que perte ; un canal = une file.
- API : `POST https://api.telegram.org/bot<token>/sendMessage` ; 429 renvoie
  `{"ok":false,"error_code":429,"parameters":{"retry_after":N}}` ; 400 renvoie
  `{"ok":false,"error_code":400,"description":"Bad Request: message thread not found"}`.
- Le danger principal est la fuite du jeton : il est dans le **chemin** de l'URL.
  `urllib.error.HTTPError` garde l'URL dans `exc.url`/`exc.filename` : ne jamais
  journaliser `exc`, `repr(exc)` ni `exc.url`.
- `agent-alert` n'échoue jamais son appelant sans `--strict` (garder ce contrat).
- `chezmoi-autoupdate` (sprint 2) appellera `agent-alert --category chezmoi --priority high --title "chezmoi-autoupdate error" "<résumé>"`.
- Portabilité : stock macOS = bash 3.2, Python 3.9 ; fleet = stdlib.
- Politique d'incertitude : signaler et continuer (Agent Notes), **sauf** secrets,
  sudoers, commande imposée, ACL Tailscale ⇒ arrêter et demander. `--configure`
  écrit un fichier à jeton : ne pas changer son modèle de permissions (0600, umask
  077) sans demander.

## Agent Notes (filled during execution)

- Assigned to:
- Started:
- Completed:
- Decisions made:
- Assumptions:
- Issues found:
