# Migration des notifications ntfy → Telegram : PRD

> **Statut : PROPOSÉ** — Build Candidate `build-candidate/telegram-migration` posé sur
> `main` après squash merge de la PR de planification. Toute modification de
> périmètre passe ensuite par une décision datée en §14.

## 1. What & Why

**Problème :** les notifications du dépôt passent par ntfy (serveur auto-hébergé
`https://ntfy.bbhome.wf` sur `bbh-network`, plus `ntfy.sh` en repli dans plusieurs
scripts) par quatre chemins de code différents, chacun avec ses propres clés. Le
chemin le plus important ne fonctionne pas : les erreurs de `chezmoi-autoupdate`
lancé par timer ne sont jamais notifiées (la variable qui active l'envoi,
`CHEZMOI_NTFY_TOPIC`, n'existe que dans le shell interactif), donc une erreur sur
un hôte sans écran — hôte sans session graphique dont `chezmoi-autoupdate` ne tourne
que par timer systemd / LaunchAgent, donc sans `notify-send` visible (cas observé :
`fedora-pve`) — reste invisible. Maintenir un serveur
ntfy pour un seul destinataire coûte plus qu'utiliser Telegram, déjà présent dans
`agent-alert` et `media_automation`.

**Résultat attendu :** toutes les notifications arrivent dans **un** supergroupe
Telegram à sujets (forum), un sujet par catégorie (`fleet`, `agents`, `chezmoi`,
`media`), envoyées directement à `api.telegram.org` par chaque machine avec **un
seul bot d'envoi seul** partagé (D15). À la fin :
plus aucun code, clé, CLI ni serveur ntfy.

**Justification :** une seule application à surveiller sur le téléphone, sujets
séparés par domaine, aucun serveur à maintenir, et correction au passage du trou
d'alerte de `chezmoi-autoupdate`.

## 2. Correctness Contract

**Audience :** Jérôme seul, sur son téléphone. Décision prise sur chaque message :
intervenir ou non sur une machine (relancer, se connecter, ignorer).

**Failure Definition (inutile) :**
- une alerte n'arrive jamais (état actuel des erreurs `chezmoi-autoupdate` sur les
  hôtes sans écran) ;
- une alerte arrive dans le mauvais sujet au point d'être ignorée ;
- du bruit (même erreur répétée toutes les heures, battement de cœur de succès)
  noie les vraies alertes.

**Danger Definition (nuisible) :**
- le jeton du bot fuit : argv (visible par `ps`), journaux, `last-run.log`, file
  d'attente, rapports `fleet`, sortie d'erreur d'une exception `urllib` qui
  contient l'URL `…/bot<token>/…` ;
- une alerte part silencieusement vers un autre chat que le supergroupe ;
- une modification sudoers / commande imposée / ACL Tailscale passe sans revue
  (fusionner sur `main` déploie partout via `chezmoi-autoupdate`).

**Risk Tolerance :** rater une alerte est pire qu'un doublon. Pendant la
transition on envoie deux fois (ntfy + Telegram) ; en cas d'erreur Telegram
« sujet introuvable », on renvoie dans le sujet général avec un préfixe plutôt que
de perdre le message.

**Uncertainty Policy :** voir §15.

## 3. Context Loaded

Inventaire vérifié sur `origin/main` @ `b853dacd` (fichier:ligne).

**`agent-alert`** — `dot_local/bin/executable_agent-alert` (166 lignes, bash)
- Backends `ntfy|telegram|none`, un seul à la fois (`:18`, `:143-156`).
- Config : `$AGENT_ALERT_CONF`, `~/.config/agent-alert.conf`, `/etc/agent-alert.conf`,
  `/etc/orca-alert.conf` hérité (`:55-56`) ; fichier à jeton non 0600 ignoré (`:59-61`).
- **Bug macOS :** `stat -c %a` (`:58`) n'existe pas sous BSD → repli `777` → tout
  fichier à jeton est ignoré sur Mac.
- Secrets via `curl --config -` sur stdin (`:86`, `:97`) ; Telegram : `chat_id` +
  `text`, pas de `message_thread_id` (`:89-98`) ; corps tronqué à 3900 (`:92`, `:149`).
- `--configure [--system]` écrit un seul backend (`:101-132`), `--test` (`:135-136`),
  `--strict`.
- Déployé Linux seulement : `.chezmoiignore.tmpl:270` (bloc `ne linux`, donc aussi
  Windows) ; supprimé des Mac `mac-pro` par
  `.chezmoiscripts/02-install/run_once_12-disable-macos-agent-stacks.sh.tmpl:41`
  (`run_once` : le modifier le relance une fois sur chaque Mac).
- Appelants : `orca-health` (`executable_orca-health:81`), `agents-update` (`:40`),
  `t3-health` (`:15`), santé inline de `paseo-setup` (`:244-274`). Copie root
  `/usr/local/bin/agent-alert` installée par `orca-setup` (`:58`, `:324`) et
  `paseo-setup` (`:60`, `:262`) : **une copie, pas un lien** → elle ne suit pas
  `chezmoi apply`, il faut relancer `orca-setup`/`paseo-setup`.
- `orca-setup:813-842` migre l'ancien `/etc/orca-alert.conf` (ntfy) vers les
  nouvelles clés et écrit un gabarit commenté ntfy/telegram.
- Tests : `scripts/test_agent_alert.py` (faux `curl` qui enregistre argv + stdin,
  `TG_TOKEN`) ; `scripts/test_orca_headless.py:163-172` exige `Authorization: Bearer`,
  `ORCA_ALERT_TOKEN` et `/etc/orca-alert.conf` dans `agent-alert`. Lancés par CI
  (`.github/workflows/validate.yml:60-63`).

**`media_automation`** — `bin/executable_media_automation.py` (3639 lignes,
Python ≥ 3.11 : `tomllib`, `slots=True`)
- `TelegramConfig` (`:182-189`, sans sujet) + `NtfyConfig` (`:192-200`), lus depuis le
  TOML de l'hôte média (hors dépôt) avec repli env `TELEGRAM_BOT_TOKEN/CHAT_ID`,
  `NTFY_*` (`:418-439`).
- `send_telegram_message` (`:542-562`) : **journalise `exc` brut** (`:562`) → une
  exception contenant l'URL `…/bot<token>/…` fuirait dans le journal.
- `send_ntfy_message` (`:599-622`), dispatch unique `notifier()` (`:625-635`).
- Tests : `bin/test_media_automation.py` (41 réfs ntfy).

**`chezmoi-autoupdate`** — `dot_local/bin/executable_chezmoi-autoupdate` (458 lignes)
- Phase D (erreur) : notification bureau (`:386-400`) puis ntfy si
  `CHEZMOI_NTFY_TOPIC` (`:402-414`) ; Telegram retiré volontairement (`:416-420`).
- Phase E (battement de cœur de succès, ntfy priorité min) : `:425-442`.
- `CHEZMOI_NTFY_*` ne vivent que dans `~/.zsh/secrets.zsh` (shell) ; l'unité
  `dot_config/systemd/user/chezmoi-autoupdate.service` lit
  `EnvironmentFile=-%h/.config/chezmoi-autoupdate.env` que **rien ne crée** ; la
  LaunchAgent `Library/private_LaunchAgents/com.jsoyer.chezmoi-autoupdate.plist.tmpl`
  (mac-personal seulement) ne passe que `PATH/HOME/SSH_AUTH_SOCK` ; la tâche
  Windows `.chezmoiscripts/03-configure/run_once_enable-chezmoi-autoupdate.ps1.tmpl`
  lance `bash.exe -c ~/.local/bin/chezmoi-autoupdate` sans aucune variable.
  ⇒ **aucun envoi ntfy depuis un run planifié, sur aucune plateforme.**
- Documentation : `dot_zsh/00-env.zsh.tmpl:257-262`,
  `dot_local/bin/executable_dotfiles-generated-config:26-30` (`SECRET_FIELDS`),
  `docs/RUNBOOK.md:484-516` et `:579`, `dot_local/bin/executable_cminventory:72-77`
  (indice « Fleet status: https://ntfy.sh/… »), `dot_config/systemd/README.md:176-184`,
  `:267-272`, `dot_local/bin/README.md:353-357`, `README.md:495-496`.
- Génération des secrets : `.chezmoiscripts/03-configure/run_onchange_generate-secrets.sh.tmpl`
  (seulement si `op` présent et connecté) → `dotfiles-generated-config secrets`
  (`:175-212`, un seul `op item get "Shell Secrets"`, publication atomique 0600,
  ancien fichier conservé en cas d'échec). Tests : `scripts/test_generated_config.py`.

**fleet (master)** — `dot_local/share/fleet/`
- `lib/notify.py` (322 l.) : 6 types d'événements et priorités (`:4-6`, builders
  `:74-115`), jeton `FLEET_NTFY_TOKEN` ou `op read` (`:156-168`), https obligatoire
  avec jeton (`:171-177`), pas de redirection (`:130-137`), classement
  transitoire/permanent (`:180-190`, `TRANSIENT_HTTP = 401/403/408/429` `:48`),
  file durable `ntfy-queue/` 0600 avec `flock` et quarantaine `.bad` (`:206-309`),
  expéditeur injectable (`:209`).
- `lib/orchestrate.py` (976 l.) : `gateway` ntfy traité seul en phase 3 (`:327`, `:341`),
  `_notify` qui n'interrompt jamais un run (`:616-623`), appels (`:652-656`, `:700`),
  `_make_notifier` (`:781-790`), sous-commandes argparse (`:745-771`).
- `lib/inventory.py:270-296` : schéma `ntfy` (url, topic, `token_ref` op://, `gateway`).
- `lib/schema.py:61-62`, `:108` : masquage `tk_…` ; aucun motif de jeton Telegram.
- `fleet.yml:22-25` (`ntfy: {url: https://ntfy.bbhome.wf, topic: fleet, token_ref:
  op://Private/Fleet/ntfy-token, gateway: bbh-network}`), `:145` (bbh-network = passerelle ntfy).
- `dot_local/bin/executable_fleet:11`, `:75`, `:215-217` (verbes transmis à `orchestrate.py`).
- `dot_config/systemd/user/fleet-reminder.service` (rappel 14 j, `FLEET_NTFY_TOKEN`
  via `EnvironmentFile=-%h/.config/fleet/env`).
- `docs/FLEET.md:4,34,112,123-124,136,322-337,360-368,394,418-423,472`.
- Tests : `scripts/test_fleet_report.py`, `test_fleet_orchestrate.py` (fixture ntfy
  `:58`), `test_fleet_pull.py`, `test_fleet_appliances.py`,
  `test_fleet_windows_contract.py`, `test_fleet_inventory.py`.

**fleet (agents, mode pull)**
- `agent/fleet-agent.sh:1062-1066` (`conf_value`, `pull.conf` jamais sourcé),
  `:1117-1143` (`pull_notify` : `NTFY_URL/NTFY_TOPIC/NTFY_TOKEN_FILE`, jeton via
  `curl -K -`, regex de jeton `^[A-Za-z0-9_.-]+$` qui **refuse le `:`** d'un jeton Telegram).
- `agent/fleet-agent.ps1:981-1017` (`Get-ConfValue`, `Send-PullNotification`,
  `Invoke-RestMethod`, `catch` à message fixe).
- L'agent est installé root en `/usr/local/libexec/fleet-agent` par
  `.chezmoiscripts/03-configure/run_onchange_install-fleet-agent.sh.tmpl` : toute
  modification de `fleet-agent.sh` est redéployée sur tout le parc après fusion.

**Divers ntfy**
- `dot_config/mise/config.toml.tmpl:152` (`"aqua:binwiederhier/ntfy"`),
  `.chezmoiscripts/03-configure/run_onchange_after_purge-brew-mise-duplicates.sh.tmpl:40`
  (`ntfy:ntfy`, `run_onchange` → relancé une fois partout si modifié).
- `dot_private/Brewfile_personal:216` : **manifeste de compatibilité figé**
  (hash vérifié par `scripts/test_package_layers.py:79-88`, portée
  `compatibility-shared` dans `docs/PACKAGE_BASELINE_2026-11-14.json`) → **ne pas
  modifier**. `dot_private/Brewfile_JeromeSacMiniM6:206` : overlay d'hôte (portée
  `machine-or-policy`, modifiable ; mettre à jour son hash de référence dans
  `docs/PACKAGE_BASELINE_2026-11-14.json` dans le même commit).
  `dot_private/Brewfile_blacklist` : paquets que `breww dump` ne réécrit plus.
  Retirer une ligne ne désinstalle rien (`docs/PACKAGE_LAYERS.md:142-146`).
- `INVARIANTS.md` (racine) : entrée « Aucun secret en sortie » — invariant « aucun
  motif de clé privée ou jeton dans `runs/`, l'historique ou la file ntfy », Verify
  `grep -rqE 'BEGIN [A-Z ]*PRIVATE KEY|tk_[A-Za-z0-9]{20,}|eyJ…'` sur
  `~/.local/state/fleet` ; le sprint 4 y ajoute le motif Telegram. Entrée « Verbes de
  l'agent » — liste blanche exacte `check update reboot-status reboot report` dans
  `fleet-agent.sh`/`.ps1` : **inchangée** par ce PRD (aucun verbe ajouté).
- `dot_local/share/fleet/lib/api_homeassistant.py:6` (docstring).
- `tools/aictx/src/trim.rs:15` : chaîne `"## ntfy Setup"` d'une liste de titres à
  tronquer, pas un usage de ntfy → **laissée** (exception listée en §13).
- Historique non modifié : `docs/tasks/**`, `docs/session-learnings.md`.

**Topics ntfy existants (instantané du 2026-11-24, passation de la session `pi-2b`, Pi `bbh-network`) :** serveur
= conteneur `binwiederhier/ntfy`, port hôte 7171, public `https://ntfy.bbhome.wf`,
données `/home/pi/docker/prod/ntfy/data`, auth activée ; topics `watchtower-updates`,
`diun-updates`, `infra-dijon`, `infra-nice`, `chezmoi-fleet`, `proxmox`, `pyload`,
`fork-keeper`, `vigil-ops`, `vigil-dijon`, `vigil-nice` ; utilisateurs `vigil`
(écriture `vigil-*`), `jsoyer` (lecture). Pour un fait côté Pi, la session `pi-2b` est
joignable par SendMessage (par l'orchestrateur, pas par les agents de sprint).

**Écart topic fleet (vérifié dans le code) :** fleet — run **et** rappel — publie sur
`cfg.get("topic", "fleet")` (`orchestrate.py:787`), soit `topic: fleet` de
`fleet.yml:25`. `chezmoi-fleet` est la valeur de `CHEZMOI_NTFY_TOPIC` du RUNBOOK
(`docs/RUNBOOK.md:492`), donc le topic de `chezmoi-autoupdate`, pas de fleet : la
passation confond les deux. Le topic `fleet` n'apparaît pas dans la liste du serveur
⇒ soit il existe sans être listé, soit les messages fleet sont refusés aujourd'hui
(Q8). `fleet-reminder.service` lance `~/.local/bin/fleet reminder` avec
`EnvironmentFile=-%h/.config/fleet/env` (`FLEET_NTFY_TOKEN` ou session `op`) ⇒ passe
au canal Telegram (bot d'envoi seul, sujet `fleet`) au sprint 3.

**Émetteurs du dépôt pour les topics hors catégorie :** la recherche ne trouve
`infra-nice` que dans `bin/test_media_automation.py` (topic de test de
`media_automation`, dont le topic réel vient du TOML ou de `NTFY_TOPIC`) : **hypothèse**
— `infra-nice` est le topic réel de `media_automation` (à confirmer, Q7). Aucune
occurrence de `infra-dijon`, `proxmox` (comme topic), `pyload`, `fork-keeper` ;
`watchtower-updates`/`diun-updates` n'apparaissent que dans `docs/RUNBOOK.md:505-506`
(droits ntfy) : ces émetteurs sont hors dépôt (§20).

**Contraintes de portabilité** (règle consignée dans la mémoire projet de Claude, rappelée ici en entier) : scripts macOS sur bash 3.2 /
Python 3.9 d'origine (pas de `declare -A`, `${x,,}`, `mapfile`, `&>>`, tableau vide
sous `set -u` sans `${a[@]+…}`) ; fleet en stdlib Python 3.9 ; tests sans réseau.

## 4. Success Metrics

| Métrique | Actuel | Cible | Mesure |
| --- | --- | --- | --- |
| Types d'événements reçus sur Telegram, dans le bon sujet | 0 / 11 | 11 / 11 | grille de bascule (§12, catalogue des événements) recopiée et remplie dans `sprints/04-bascule-suppression-ntfy.md` |
| Erreurs `chezmoi-autoupdate` planifiées notifiées | 0 % | 100 % (1er message ≤ 1 run après l'erreur) | erreur provoquée sur un hôte sans écran |
| Messages identiques `chezmoi-autoupdate` par signature d'erreur | 1 / h (si actif) | ≤ 1 / 24 h | test unitaire du limiteur + journal |
| Jeton du bot dans argv, journaux, file, rapports | non mesuré | 0 occurrence | tests (faux `curl`, faux expéditeur) + grep du motif `[0-9]{6,}:[A-Za-z0-9_-]{30,}` |
| Fichiers suivis mentionnant ntfy hors exceptions §13 | 40 fichiers / 309 lignes | 0 | `git grep -i ntfy` avec les exclusions de §13 |
| Battements de cœur de succès envoyés | 0 (code mort) | 0, code supprimé | `grep -c 'Phase E'` = 0 |

## 5. User Stories

GIVEN un hôte sans écran (`fedora-pve`) dont `chezmoi update` échoue au run horaire
WHEN le timer systemd lance `chezmoi-autoupdate`
THEN un message arrive dans le sujet **chezmoi** avec l'hôte et le résumé d'erreur,
et la même erreur ne se répète pas avant 24 h.

GIVEN `fleet up` terminé avec un hôte `failed`
WHEN le master envoie la synthèse
THEN elle arrive dans le sujet **fleet** (avec son), et, pendant la transition,
aussi sur ntfy.

GIVEN un run `fleet up` sans échec
WHEN la synthèse (priorité 2) est envoyée
THEN elle arrive dans le sujet **fleet** en mode silencieux (`disable_notification`).

GIVEN `api.telegram.org` répond 429 avec `retry_after: 30`
WHEN fleet envoie une notification
THEN le message est mis en file `telegram-queue/` et n'est pas renvoyé avant 30 s.

GIVEN `orca-health` détecte une panne sur un hôte agents
WHEN il appelle `agent-alert`
THEN le message arrive dans le sujet **agents**.

GIVEN un Mac `mac-personal` avec `~/.config/agent-alert.conf` 0600
WHEN `agent-alert --test --category chezmoi` est lancé
THEN la config est lue (plus ignorée à cause de `stat -c`) et le message arrive.

GIVEN un sujet supprimé par erreur dans le groupe
WHEN un envoi reçoit `400 Bad Request: message thread not found`
THEN le message est renvoyé une fois dans le sujet général, préfixé
`[sujet <catégorie> introuvable]`.

## 6. Acceptance Criteria

- [ ] `agent-alert` accepte `ALERT_BACKEND=ntfy,telegram` et envoie aux deux ; un échec sur l'un n'empêche pas l'autre.
- [ ] `agent-alert --category fleet|agents|chezmoi|media` pose `message_thread_id` depuis `ALERT_TELEGRAM_THREAD_<CAT>` ; catégorie inconnue ⇒ code 2.
- [ ] `agent-alert` tourne sur bash 3.2 (aucun bash4-isme, `stat` BSD/GNU) et est déployé sur macOS ; toujours ignoré sur Windows.
- [ ] Le jeton Telegram n'apparaît jamais dans argv, stdout/stderr, journaux, files d'attente ou rapports (tests).
- [ ] `fleet` envoie via Telegram (file `telegram-queue/` 0600, 429 ⇒ transitoire avec `retry_after`, 400 ⇒ `.bad` après repli sujet général, texte brut ≤ 4096, priorité ≤ 2 ⇒ silencieux).
- [ ] `schema.mask_secrets` masque un jeton Telegram nu et dans une URL `…/bot<token>/…`.
- [ ] `fleet.yml` accepte un bloc `telegram:` (références `op://` uniquement) validé par `inventory.py`.
- [ ] `fleet notify-test [--event …]` envoie un message `[TEST]` par canal configuré avec le vrai constructeur de message.
- [ ] Mode pull Unix et Windows : notification Telegram depuis `pull.conf` (`TELEGRAM_CHAT_ID`, `TELEGRAM_THREAD_ID`, `TELEGRAM_TOKEN_FILE`), jeton jamais en argv.
- [ ] `chezmoi-autoupdate` : Phase D passe par `agent-alert --category chezmoi` (avec limiteur 24 h par signature) ; Phase E supprimée ; aucun `curl` ntfy restant.
- [ ] `~/.config/agent-alert.conf` généré 0600 depuis 1Password (si `op` connecté) par `dotfiles-generated-config alert`, ancien fichier conservé en cas d'échec.
- [ ] `media_automation` : `[telegram] thread_id` → `message_thread_id` ; plus d'exception brute journalisée.
- [ ] Script de vérification de sortie Internet (`scripts/telegram_egress_check.py`) écrit et testé sans réseau.
- [ ] `agent-alert` masque les motifs de jeton (`[0-9]{6,}:[A-Za-z0-9_-]{30,}`, `tk_…`) dans le titre et le message avant tout envoi (test).
- [ ] Bascule (sprint 4) faite seulement après la grille de bascule **complète** (définition : les 11 lignes du catalogue §12 ont chacune une date de réception sur Telegram dans le bon sujet, ou, pour F2/F3/F4, une date de `fleet notify-test --event …` reçu) ; ensuite `git grep -i ntfy` (exclusions §13) ne renvoie rien.
- [ ] Les suites de §16 (déterministe) passent toutes : `scripts/test_agent_alert.py`,
  `scripts/test_orca_headless.py`, `scripts/test_fleet_*.py`, `scripts/test_generated_config.py`,
  `bin/test_media_automation.py`, `scripts/test_chezmoi_autoupdate_dirs.py`,
  `scripts/test_chezmoi_autoupdate_alert.py`, `scripts/test_telegram_egress_check.py`,
  `scripts/test_package_layers.py` ; aucun test passant supprimé sans remplacement équivalent côté Telegram.

## 7. Non-Goals

- **Relais via le master fleet :** toutes les machines ont un accès Internet direct
  (décision Jérôme). Le script d'egress du sprint 1 sert seulement à repérer une
  exception, qui serait traitée hors de ce PRD.
- **Battement de cœur / dead-man switch :** Phase E supprimée, jamais remplacée.
  L'état du parc vient du rapport `fleet` ; un résumé quotidien optionnel reste
  hors périmètre (pas de besoin exprimé ferme).
- **Notifications `chezmoi-autoupdate` sur Windows :** la tâche planifiée lance
  `bash.exe` sans config ; les postes Windows sont couverts par le mode pull fleet.
  `agent-alert` reste ignoré sur Windows.
- **Bot interactif (commandes, boutons, réponses) :** envoi seul ; aucune lecture de
  mises à jour Telegram (`getUpdates`/webhook), donc aucune surface d'entrée.
- **Mise en forme HTML/MarkdownV2 :** texte brut, sans `parse_mode` ; évite les bugs
  d'échappement (un nom d'hôte avec `_` casserait MarkdownV2).
- **Migration des autres consommateurs Telegram** (`hivepilot-telegram`,
  `TELEGRAM_BOT_TOKEN/CHAT_ID` de `secrets.zsh`) : ils restent tels quels.
- **Émetteurs hors dépôt** (Watchtower, Diun, Vigil, CI `unifi-network-server`,
  `infra-dijon`/`infra-nice`/`proxmox`/`pyload`/`fork-keeper`) et **arrêt du serveur
  ntfy** : hors périmètre de ce PRD, suivis comme dépendances externes et portes de
  bascule en §20.
- **Bots interactifs Vigil** (4 bots, un par routeur, `getUpdates`, boutons de
  confirmation) : dépôt et session dédiés (`vigil-68`), voir §20.
- **Utilitaire `tg-notify` séparé :** `agent-alert` **est** l'utilitaire partagé
  (D14) ; pas de second outil.
- **Désinstallation automatique du binaire `ntfy` sur les Mac :** retirer une ligne
  de Brewfile ne désinstalle rien ; `brew uninstall ntfy` reste manuel.
- **Modification de `dot_private/Brewfile_personal` :** figé (hash de
  compatibilité) ; on passe par `Brewfile_blacklist` et l'overlay d'hôte.
- **Arrêt du serveur ntfy auto-hébergé :** hors dépôt, étape manuelle du sprint 4.

## 8. Technical Constraints

- **Stack :** bash (portable 3.2 pour tout ce qui tourne sur macOS : `agent-alert`,
  `chezmoi-autoupdate`, `fleet-agent.sh`) ; Python 3.9 stdlib pour fleet et
  `dotfiles-generated-config` (déjà `from __future__ import annotations`) ;
  Python ≥ 3.11 pour `media_automation` (inchangé) ; PowerShell 5.1 pour
  `fleet-agent.ps1`.
- **API Telegram :** `POST https://api.telegram.org/bot<token>/sendMessage`, corps
  form-encodé : `chat_id`, `message_thread_id` (si connu), `text` (≤ 4096 caractères,
  on coupe à 3900), `disable_notification`, `disable_web_page_preview=true`. Pas de
  `parse_mode`. Réponses : 200 ok ; 429 avec `parameters.retry_after` (s) ; 400
  permanent (dont « message thread not found », « chat not found ») ; 401/403/404
  = configuration (jeton révoqué, bot exclu) → transitoire : la file attend la
  correction, rien n'est perdu.
- **Secrets :** jamais en argv (`curl --config -` / `curl -K -` sur stdin, corps dans
  un fichier 0600) ; jamais imprimés ; fichiers de config 0600 ; l'URL `…/bot<token>/…`
  ne doit jamais apparaître dans un message d'erreur journalisé (journaliser la
  classe de l'exception et le code HTTP seulement).
- **Tests :** aucun accès réseau ; faux `curl` (existant dans
  `scripts/test_agent_alert.py`), expéditeur injecté (fleet), runner injecté (egress),
  `urlopen` simulé (media). Commandes : `python3 scripts/test_<x>.py` ou
  `uvx pytest scripts/test_fleet_*.py`.
- **Déploiement :** fusionner sur `main` = déploiement sur tout le parc à l'heure
  suivante (chezmoi-autoupdate), y compris la réinstallation root de l'agent fleet.
- **Ordre :** sprint 1 → (sprints 2 et 3 en parallèle) → transition double envoi
  1-2 semaines → sprint 4.

## 9. Architecture Decisions

| # | Décision | Coût de retour | Alternatives considérées | Raison |
| --- | --- | --- | --- | --- |
| D1 | Supergroupe forum unique, un sujet par catégorie `fleet`, `agents`, `chezmoi`, `media` (décision Jérôme) | Bas | Un chat par catégorie (4 bots/chats à gérer) ; un seul fil (bruit mélangé) | Un seul `chat_id`, tri par sujet, notifications réglables par sujet sur le téléphone |
| D2 | Envoi direct à `api.telegram.org` depuis chaque machine (décision Jérôme) | Moyen | Relais par le master fleet (point unique de panne, file à concevoir) | Toutes les machines ont un accès Internet ; vérifié par le script d'egress |
| D3 | Double envoi ntfy + Telegram pendant 1-2 semaines, coupure ntfy seulement quand chaque type d'événement a été vu sur Telegram (décision Jérôme) | Bas | Bascule sèche | Rater une alerte est pire qu'un doublon |
| D4 | `agent-alert` devient l'unique émetteur shell (Linux **et** macOS) ; `chezmoi-autoupdate` l'appelle au lieu de son propre `curl` | Moyen | Garder un `curl` Telegram dans `chezmoi-autoupdate` (deuxième implémentation des secrets) | Une seule implémentation testée de la gestion du jeton |
| D5 | Fleet : transport Telegram dans `notify.py`, une file par canal (`ntfy-queue/`, `telegram-queue/`), messages inchangés (`title`, `priority`, `tags`, `body`) | Moyen | File commune avec champ canal (un canal en panne bloquerait l'autre) | Canaux indépendants pendant le double envoi ; bascule = retirer un canal |
| D6 | Texte brut, pas de `parse_mode` | Bas | HTML ou MarkdownV2 | Aucun échappement ⇒ aucun 400 dû à un caractère |
| D7 | Source unique du routage : élément 1Password `op://Private/Telegram` (champs `bot-token`, `chat-id`, `thread-fleet`, `thread-agents`, `thread-chezmoi`, `thread-media`) ; `fleet.yml` ne porte que des références `op://` ; `~/.config/agent-alert.conf` est **généré** 0600 depuis ce même élément par `dotfiles-generated-config alert` quand `op` est connecté, sinon `agent-alert --configure` à la main | Moyen | `chat_id` en clair dans le dépôt (deux sources qui divergent ⇒ mauvais chat) ; variables d'environnement dans les unités (fichier `.env` que rien ne crée aujourd'hui) | Une seule source ⇒ pas de mauvais chat ; même mécanisme éprouvé que `secrets.zsh` (lecture unique, publication atomique, ancien fichier conservé). **Touche aux secrets : à valider explicitement par Jérôme (Q1)** |
| D8 | Priorité → `disable_notification` : fleet prio ≤ 2 et `agent-alert --priority low` ⇒ silencieux ; sinon sonore ; `high`/prio ≥ 5 préfixés `[URGENT]` | Bas | Priorités Telegram inexistantes | Garde l'intention des priorités ntfy |
| D9 | Repli « sujet introuvable » : un 400 dont la description contient `thread` est renvoyé **une fois** sans `message_thread_id`, préfixé `[sujet <cat> introuvable]` ; nouvel échec ⇒ `.bad` | Bas | `.bad` direct (alerte perdue) | Rater une alerte est pire |
| D10 | Phase E (battement de cœur) supprimée ; Phase D limitée à 1 message par signature d'erreur (hash du résumé) et par 24 h, état dans `~/.cache/chezmoi-autoupdate/last-alert` | Bas | Envoyer à chaque run horaire (bruit) | « Spam qui noie les vraies alertes » est un mode d'échec |
| D11 | Le concept `ntfy.gateway` disparaît au sprint 4 ; `bbh-network` reçoit le tag `infra` (phase 2, en série) | Bas | Garder une phase 3 vide | Plus de serveur de notification sur `bbh-network` ; la phase 2 reste prudente (en série) |
| D12 | Egress : `scripts/telegram_egress_check.py` lit `fleet.yml`, lance par SSH **interactif de l'opérateur** (pas la clé fleet à commande imposée) `curl -s -o /dev/null -w '%{http_code}' https://api.telegram.org/` sans jeton | Bas | Nouveau verbe d'agent (change le contrat de commande imposée et l'invariant des verbes) | Aucun secret, aucune modification sudoers/commande imposée |
| D14 | Clés canoniques des dotfiles : `ALERT_TELEGRAM_BOT_TOKEN`, `ALERT_TELEGRAM_CHAT_ID`, `ALERT_TELEGRAM_THREAD_<CATEGORY>` ; `agent-alert` est l'utilitaire « tg-notify » partagé ; alias `TG_CHAT_ID` / `TG_THREAD_<CATEGORY>` lus en repli seulement (**décision à confirmer par l'utilisateur, Q5**) | Bas | Schéma `TG_*` partout ; second utilitaire `tg-notify` | Garde le contrat existant d'`agent-alert` ; les alias permettent un fichier env commun avec les émetteurs hors dépôt |
| D15 | Un seul bot **d'envoi seul** (nom provisoire `bbhome_notify_bot`) pour tous les émetteurs des dotfiles ; aucun code du dépôt n'appelle `getUpdates` / `setWebhook` | Bas | Un bot par émetteur | Un jeton = un flux `getUpdates` (409 si partagé) : les 4 bots Vigil interactifs sont séparés, le bot d'envoi ne lit jamais rien |
| D16 | **Confirmée par Jérôme le 2026-11-24.** Deux portes distinctes : (a) sprint 4 (suppression du code ntfy des dotfiles) = grille Telegram complète ; (b) arrêt du serveur ntfy (manuel, §20) = sprint 4 fusionné **et** tous les topics ntfy silencieux ≥ 3 jours | Bas | Une seule porte « topics ntfy silencieux » | Pendant le double envoi les topics des dotfiles ne peuvent pas être silencieux ; le silence ne se constate qu'après le sprint 4 |
| D13 | Le masquage `tk_…` de `schema.py` reste (renommé `_LEGACY_TK_TOKEN`, commentaire sans « ntfy ») | Bas | Le supprimer avec ntfy | L'historique et les anciens journaux peuvent encore contenir d'anciens jetons |

## 10. Security Boundaries

- **Auth model :** un secret Telegram, le jeton du **bot d'envoi seul**
  (`op://Private/Telegram/bot-token`, un élément 1Password par bot ; les 4 bots Vigil
  ont leurs propres éléments, jamais lus par ce dépôt).
  Règles (sprint 0, manuel) : « Group Privacy » activé pour tous les bots ; **aucun bot
  admin du groupe** (sujets créés par Jérôme seul) ; après ajout au groupe, BotFather
  « Allow Groups » → off ; groupe privé sans lien d'invitation public. Lecture du
  jeton par `op read` ou par un `EnvironmentFile=-` hors dépôt (préfixe `-` comme
  `fleet-reminder.service`) ; jamais dans git, les journaux ni argv.
  **Pendant la transition (sprints 1-3, double envoi D3)** les secrets ntfy existants
  (`op://Private/Fleet/ntfy-token`, `CHEZMOI_NTFY_TOKEN`, `ALERT_NTFY_TOKEN`, fichier
  jeton ntfy de `pull.conf`) restent aussi présents sur les hôtes, avec les mêmes
  protections ; ils sont révoqués au démantèlement du sprint 4.
  Il permet d'écrire dans tout chat où le bot est membre ; le bot n'est membre que
  du supergroupe. Aucune lecture de messages entrants : aucun `getUpdates` /
  `setWebhook` dans le dépôt (invariant « Envoi seul »).
- **Trust boundaries :**
  - Le texte des messages vient de sorties de commandes (`chezmoi`, agents fleet,
    `media_automation`) : non fiable, possiblement porteur de secrets ⇒ masqué
    (`schema.mask_secrets` côté fleet ; filtre des motifs de jeton dans `agent-alert`)
    puis envoyé en texte brut (pas de `parse_mode`, donc aucune injection de mise en forme).
  - `pull.conf` et `agent-alert.conf` ne sont **jamais sourcés comme code** côté
    agent fleet (`conf_value` par `sed`) ; `agent-alert` source sa config (existant)
    mais refuse un fichier à jeton non 0600 (avec `stat` portable).
  - La copie root `/usr/local/bin/agent-alert` n'est installée que depuis la source
    de confiance (existant, `paseo-setup:248`).
  - Contrôle de sortie D12 (`scripts/telegram_egress_check.py`, sprint 1) : passe par
    le SSH de l'opérateur (`BatchMode=yes`), jamais par les clés fleet à commande
    imposée ; n'envoie aucun jeton (requête anonyme vers l'API, seul le code HTTP
    compte) ; aucun secret en argv ; sortie = hôte + verdict.
  - `fleet-agent.sh` est installé root et exécuté par commande imposée : le
    modifier ne change ni la liste des verbes ni le sudoers, mais il est redéployé
    root partout ⇒ **revue de Jérôme avant fusion** (sprint 3).
- **Data sensitivity :** jeton du bot = credential (et, jusqu'au sprint 4, jetons ntfy) ; `chat_id` et identifiants de sujet =
  peu sensibles mais gardés dans 1Password (source unique, D7). Protections : stdin
  pour curl, fichier corps 0600, `umask 077`, fichiers 0600, aucune exception brute
  journalisée quand l'URL porte le jeton, motif `[0-9]{6,}:[A-Za-z0-9_-]{30,}` masqué
  partout (fleet `schema.py`, `agent-alert`, tests de non-fuite).
- **Mauvais destinataire :** `chat_id` validé `^-100[0-9]{5,}$` (supergroupe) côté
  fleet et `agent-alert --configure`/générateur ; `--test` affiche
  `chat=<4 derniers chiffres>` et la catégorie, jamais le jeton.
- **Changements soumis à revue explicite :** génération de `agent-alert.conf` (D7,
  secrets), `pull.conf`/fichier jeton du mode pull, réinstallation root de l'agent,
  aucun changement sudoers ni ACL Tailscale prévu (s'il en apparaît un : arrêt) ;
  au sprint 4 (porte « revue Jérôme avant fusion », reprise dans le sprint 4), la migration `/etc/orca-alert.conf` → `/etc/agent-alert.conf` de
  `orca-setup` (fichier root:root 0600 conservé) et le changement d'attente de
  `scripts/test_orca_headless.py` passent en revue de Jérôme avant fusion.
- **Rotation / révocation (D2 met le jeton sur chaque hôte) :** hôte compromis ou
  jeton exposé ⇒ `/revoke` chez @BotFather (l'ancien jeton cesse immédiatement de
  fonctionner partout), nouveau jeton dans `op://Private/Telegram/bot-token`, puis
  `dotfiles-generated-config alert` sur les hôtes avec `op`, `agent-alert --configure`
  (`--system` pour root) ailleurs, et mise à jour des fichiers jeton du mode pull.
  Pendant l'intervalle les envois échouent en 401 ⇒ messages fleet gardés en file
  (transitoire), alertes shell en journal. Procédure écrite dans `docs/FLEET.md`
  (sprint 3) et `dot_local/bin/README.md` (sprint 2). Jusqu'au sprint 4, un jeton ntfy
  exposé suit la procédure existante : révocation dans le serveur ntfy
  (`docs/RUNBOOK.md`, section ntfy), nouveau jeton dans `op://Private/Fleet/ntfy-token`
  ou « Shell Secrets », régénération de la config.
- **Tenant isolation :** sans objet (un seul utilisateur).

## 11. Data Model

**Access Patterns :**
1. Chaque émetteur shell, à chaque envoi (≤ 4 / h / hôte en régime normal : santé
   des stacks agents + 1 run `chezmoi-autoupdate`), lit localement jeton + `chat_id`
   + sujet de **sa** catégorie dans le premier fichier lisible et sûr de cette liste,
   selon le contexte d'exécution :
   - **utilisateur** (unités systemd user `chezmoi-autoupdate`, `agents-update`,
     `t3-health` ; LaunchAgent macOS ; shell) : `~/.config/agent-alert.conf`, **généré**
     par `dotfiles-generated-config alert` (D7) ou écrit par `agent-alert --configure` ;
   - **root** (`orca-health`, santé `paseo`, via la copie `/usr/local/bin/agent-alert`) :
     `/etc/agent-alert.conf`, écrit **à la main** par `sudo agent-alert --configure --system`
     (le générateur ne touche jamais à `/etc` : pas de sudo dans `chezmoi apply`) ; la
     copie root est rafraîchie en relançant `orca-setup` / `paseo-setup` ;
   latence non critique (< 10 s).
2. Fleet, à chaque run (≤ 1 / jour, plus le rappel quotidien), lit jeton, chat et
   sujet `fleet` depuis 1Password (3 `op read`) ou l'environnement, puis vide sa file.
3. Agent fleet en mode pull (≤ 1 / jour / hôte, Unix et Windows) : lit `pull.conf`
   (`TELEGRAM_CHAT_ID`, `TELEGRAM_THREAD_ID`, `TELEGRAM_TOKEN_FILE`, jamais sourcé) puis
   la 1ʳᵉ ligne du fichier jeton 0600 ; fichiers posés à la main (procédure FLEET.md).
4. `chezmoi-autoupdate`, à chaque run horaire en erreur, lit le dernier hash d'erreur
   et son horodatage pour décider d'envoyer.
5. Jérôme, à la bascule, vérifie que chaque type d'événement a été reçu (grille de bascule = catalogue §12).

**Entités :**
- *Élément 1Password `Telegram`* (vault Private) : `bot-token`, `chat-id`,
  `thread-fleet`, `thread-agents`, `thread-chezmoi`, `thread-media`.
- *`agent-alert.conf`* (0600) — emplacements, dans l'ordre de recherche « premier
  fichier lisible et sûr » : `$AGENT_ALERT_CONF`, `~/.config/agent-alert.conf`
  (utilisateur), `/etc/agent-alert.conf` (root:root 0600, contexte root) ; l'ancien
  `/etc/orca-alert.conf` n'est lu que jusqu'au sprint 4. Clés : `ALERT_BACKEND`, `ALERT_TELEGRAM_BOT_TOKEN`,
  `ALERT_TELEGRAM_CHAT_ID`, `ALERT_TELEGRAM_THREAD_FLEET|AGENTS|CHEZMOI|MEDIA`,
  optionnel `ALERT_TELEGRAM_THREAD_ID` (défaut) ; pendant la transition aussi
  `ALERT_NTFY_URL`, `ALERT_NTFY_TOKEN`.
- *Bloc `fleet.yml` `telegram:`* : `token_ref`, `chat_ref`, `thread_ref` (tous `op://`).
- *Message fleet en file* (JSON 0600) : `title`, `priority`, `tags`, `body`, `created`
  (+ `category` facultatif) — jamais de jeton, d'URL ni de `chat_id`.
- *`telegram-queue/.retry-after`* : epoch avant lequel on ne renvoie pas.
- *`pull.conf`* (agent) : `TELEGRAM_CHAT_ID`, `TELEGRAM_THREAD_ID`, `TELEGRAM_TOKEN_FILE`.
- *`~/.cache/chezmoi-autoupdate/last-alert`* : `<sha256 du résumé> <epoch>`.

**Schema justification :** les accès 1, 3 et 4 sont des lectures locales de fichiers
plats (aucun réseau, aucun `op` au moment de l'alerte, donc l'alerte part même si
1Password est verrouillé) ; l'accès 2 garde le modèle existant de fleet (`op read` à
l'exécution, rien de secret sur disque côté master) ; la file par canal sert l'envoi
ordonné et le double envoi indépendant.

## 12. Shared Contracts

- **Catégories :** exactement `fleet`, `agents`, `chezmoi`, `media`. `agent-alert`
  sans `--category` ⇒ `agents` (compatibilité des appelants actuels).
- **CLI `agent-alert` :**
  `agent-alert [--category C] [--title T] [--priority low|default|high] [--tags a,b] [--strict] "message"`,
  message aussi sur stdin ; `--configure [--system]`, `--test [--category C]`.
  Codes : 0 envoyé (ou échec non strict), 1 échec avec `--strict`/`--test` (si **un**
  backend échoue), 2 usage. Sortie de `--test` : une ligne par backend
  `backend=<b> config=<fichier> category=<c> chat=…<4 derniers chiffres> thread=<id|general> result=ok|fail`.
- **Format du texte Telegram :** `[<host>] <titre>\n<message>` (`[URGENT] ` devant le
  titre si priorité haute), tronqué à 3900 caractères ; texte brut.
- **Clés de config `agent-alert` :** voir §11. `ALERT_BACKEND` : liste séparée par
  virgules de `ntfy`, `telegram`, `none` (sprint 4 : `telegram`, `none`).
- **Fleet `notify.py` :** builders inchangés (signature et dict) ; nouveau
  `TelegramChannel(token, chat_id, thread_id, queue_dir, sender=None, clock=…)` et
  `NtfyChannel` (l'existant) partageant l'interface `send(msg) -> bool`,
  `flush() -> int` ; `Notifier(channels: List[Channel])` diffuse à tous, retourne
  `True` si tous ont livré. Expéditeur Telegram injectable
  `sender(url: str, form: Dict[str, str]) -> Dict[str, Any]` (réponse JSON décodée).
- **`fleet.yml` :** `telegram: {token_ref: "op://Private/Telegram/bot-token", chat_ref: "op://Private/Telegram/chat-id", thread_ref: "op://Private/Telegram/thread-fleet"}` ;
  surcharges env `FLEET_TELEGRAM_TOKEN`, `FLEET_TELEGRAM_CHAT_ID`, `FLEET_TELEGRAM_THREAD_ID`.
- **Motif de jeton Telegram (masquage, validation) :** `[0-9]{6,}:[A-Za-z0-9_-]{30,}` ;
  dans une URL : `bot[0-9]{6,}:[A-Za-z0-9_-]{30,}`.
- **`pull.conf` :** `TELEGRAM_CHAT_ID` (`^-100[0-9]{5,}$`), `TELEGRAM_THREAD_ID`
  (`^[0-9]{1,10}$`, facultatif), `TELEGRAM_TOKEN_FILE` (chemin d'un fichier 0600 dont
  la 1ʳᵉ ligne vérifie le motif de jeton).
- **Catalogue des événements (grille de bascule) :**

| Id | Événement | Émetteur | Sujet | Silencieux |
| --- | --- | --- | --- | --- |
| F1 | Synthèse de run | fleet master | fleet | oui si prio 2 |
| F2 | Hôte > 30 j sans MAJ | fleet master | fleet | non |
| F3 | Hôte redémarré non revenu | fleet master | fleet | non |
| F4 | Commande refusée par un agent | fleet master | fleet | non |
| F5 | MAJ autonome mode pull (Linux/macOS) | `fleet-agent.sh` | fleet | oui |
| F6 | MAJ autonome mode pull (Windows) | `fleet-agent.ps1` | fleet | oui |
| F7 | Rappel 14 j | fleet master (timer) | fleet | non |
| A1 | Santé / MAJ des stacks agents | `agent-alert` (orca-health, t3-health, paseo-health, agents-update) | agents | oui si `--priority low`, sinon non (D8) |
| C1 | Erreur `chezmoi-autoupdate` | `agent-alert --category chezmoi` | chezmoi | non |
| M1 | Rapport `media_automation` | `media_automation` | media | non |
| T1 | `agent-alert --test` / `fleet notify-test` | tous | selon catégorie | — |

  F2, F3, F4 sont rares : `fleet notify-test --event stale|not-back|refused` passe par
  le vrai constructeur et le vrai canal, et compte pour la grille.

## 13. Architecture Invariant Registry

| Concept | Owner | Format/Values | Verify Command |
| --- | --- | --- | --- |
| Catégories | `agent-alert` | `fleet agents chezmoi media` | `grep` des 4 noms dans `agent-alert`, `notify.py`, générateur |
| Jeton jamais en argv | `agent-alert`, `fleet-agent.sh` | `curl --config -` / `-K -` | `scripts/test_agent_alert.py`, `scripts/test_fleet_pull.py` |
| Masquage jeton Telegram (fleet) | `lib/schema.py` | `[0-9]{6,}:[A-Za-z0-9_-]{30,}` | `grep` du motif dans `schema.py` |
| Masquage jeton dans le texte (shell) | `agent-alert` | même motif + `tk_…` → `[MASKED]` | `grep` du motif + `MASKED` dans `agent-alert` |
| Validation stricte du jeton (pull) | `fleet-agent.sh` / `.ps1` | 1ʳᵉ ligne = motif complet ancré `^[0-9]{6,}:[A-Za-z0-9_-]{30,}$`, sinon pas d'envoi | `grep` du motif ancré dans les deux agents |
| Références op:// seulement | `fleet.yml` / `inventory.py` | `token_ref`, `chat_ref`, `thread_ref` | `grep` dans `fleet.yml` |
| Portabilité bash 3.2 | `agent-alert`, `chezmoi-autoupdate` | aucun `declare -A`, `mapfile`, `${x,,}`, `stat -c` seul | `grep -E` |
| Plus de battement de cœur | `chezmoi-autoupdate` | pas de Phase E | `grep` |
| Envoi seul | dépôt | aucun `getUpdates` / `setWebhook` (hors doc tierce `dot_aictx/skills/openclaw-config`) | recherche dans le dépôt |
| Fin de ntfy | dépôt | 0 occurrence hors exceptions | `git grep -i ntfy` avec exclusions |

**Exceptions permanentes à « fin de ntfy » :** `docs/tasks/**` et
`docs/session-learnings.md` (historique), `tools/aictx/src/trim.rs` (chaîne de titre),
`dot_private/Brewfile_personal` (figé), `dot_private/Brewfile_blacklist` (y ajoute
`ntfy` justement pour qu'il ne revienne pas).

**Dependency direction :** `agent-alert` possède le contrat des catégories et des
clés ; `chezmoi-autoupdate`, les stacks agents et le générateur le consomment.
`schema.py` possède le motif de masquage ; `notify.py` et les tests le consomment.

## 14. Open Questions

- [x] **Q1 — VALIDÉE par Jérôme le 2026-11-24 (option A : génération depuis 1Password) — (bloquante pour la tâche « génération » du sprint 2, secrets) :** Jérôme
  valide D7 (génération de `~/.config/agent-alert.conf` depuis `op://Private/Telegram`
  par `dotfiles-generated-config alert`). Sans validation : le sprint 2 livre le reste
  et la config se fait par `agent-alert --configure`. — Jérôme, à la revue de la PR.
- [ ] **Q2 :** l'opérateur a-t-il un accès SSH interactif (hors clé fleet) à tous les
  hôtes de `fleet.yml` pour le script d'egress ? Hôtes sans accès : test manuel
  `agent-alert --test` sur place. — Jérôme.
- [ ] **Q3 :** chemin du TOML de `media_automation` sur l'hôte média (hors dépôt) —
  nécessaire seulement pour la mise en service manuelle. — Jérôme.
- [ ] **Q4 :** `Brewfile_blacklist` empêche-t-il aussi `brew bundle` d'installer `ntfy`
  depuis `Brewfile_personal`, ou seulement `breww dump` de le réécrire ? À vérifier
  dans `breww` au sprint 4 ; à défaut, documenter `brew uninstall ntfy` manuel.
- [x] **Q5 — CONFIRMÉE par Jérôme le 2026-11-24 (alias `TG_*` lus en repli) — (décision à confirmer par l'utilisateur) :** schéma de clés D14 —
  `ALERT_TELEGRAM_*` canonique, alias `TG_CHAT_ID` / `TG_THREAD_<CATEGORY>` lus en
  repli, pas d'utilitaire `tg-notify` séparé (un lien symbolique `tg-notify` →
  `agent-alert` seulement si Jérôme le demande). Sans réponse : canonique seul, sans
  alias. — Jérôme, à la revue de la PR.
- [ ] **Q6 (en attente, sprint 0) :** noms des 5 bots, user id, `chat_id`, identifiants
  des sujets. Les sprints 1-3 se codent et se testent avec des faux ; la config réelle
  et `agent-alert --test` par sujet sont une acceptation manuelle.
- [ ] **Q7 :** inventaire des émetteurs `infra-dijon`, `infra-nice`, `proxmox`,
  `pyload`, `fork-keeper` (machine, mécanisme) ; `infra-nice` = `media_automation` ?
- [ ] **Q8 :** le topic ntfy `fleet` existe-t-il sur le serveur (les messages fleet
  arrivent-ils) ? À demander à `pi-2b` ; n'affecte pas le code (cible Telegram = sujet
  `fleet`).
- [x] **Q9 — TRANCHÉE par Jérôme le 2026-11-24 : pas de sujet « Vigil – Ops ».** Deux
  sujets Vigil seulement (Dijon, Nice). Hors dépôt (§20).
- [ ] **Q10 :** shoutrrr (Watchtower) et Diun gèrent-ils `message_thread_id` ? Sinon
  sujet General. Hors dépôt (§20).
- [ ] **Q11 :** `parse_mode` : texte brut par défaut (§7) ; option par appel
  seulement si un besoin apparaît — non livrée ici.

## 15. Uncertainty Policy

- **Par défaut : signaler et continuer.** Noter l'hypothèse (et son niveau de
  confiance) dans les Agent Notes du sprint, choisir l'option la plus prudente,
  continuer.
- **Exception : arrêter et demander** pour tout ce qui touche aux secrets (jeton,
  génération de fichier de config à jeton, fichier jeton du mode pull), au sudoers,
  à la commande imposée / installation root de l'agent, aux ACL Tailscale.
- Doublon vs perte : préférer le doublon.
- Si « supprimer ntfy » contredit « ne pas supprimer un test passant » : remplacer le
  test par son équivalent Telegram dans le même commit, et le signaler.
- Si un fichier de §3 a changé depuis `b853dacd` : suivre le code, noter l'écart.

## 16. Verification

- **Déterministe :**
  - `python3 scripts/test_agent_alert.py`, `python3 scripts/test_orca_headless.py`
  - `uvx pytest scripts/test_fleet_*.py` (ou `python3 -m pytest -q …`)
  - `python3 scripts/test_generated_config.py`, `python3 -m pytest -q bin/test_media_automation.py`
  - `python3 scripts/test_chezmoi_autoupdate_dirs.py`, `python3 -m pytest -q scripts/test_chezmoi_autoupdate_alert.py`
  - `python3 -m pytest -q scripts/test_telegram_egress_check.py`
  - `bash -n` + `shellcheck` sur chaque script bash modifié (0 nouveau constat)
  - `python3 scripts/test_package_layers.py` (sprint 4 : Brewfiles)
  - les commandes `Verify` de `INVARIANTS.md` du dossier du PRD (`docs/tasks/infra/feature/2026-11-24_1757-telegram-migration/INVARIANTS.md`)
- **Manuel (Jérôme) :**
  - `agent-alert --test --category <c>` pour chaque catégorie, sur un Linux et un Mac ;
  - `fleet notify-test` et `fleet notify-test --event refused` ;
  - une erreur `chezmoi-autoupdate` provoquée sur `fedora-pve` ;
  - un run pull réel (Linux et Windows) ;
  - grille de bascule (catalogue §12, recopiée dans le sprint 4) remplie avant le sprint 4 ;
  - revue des diffs `fleet-agent.sh/.ps1` avant fusion du sprint 3 ;
  - une fois les IDs connus (Q6) : config réelle puis `agent-alert --test --category <c>`
    dans chacun des 4 sujets (acceptation manuelle, pas une tâche d'agent).

## 17. Sprint Decomposition

### Sprint 0 — prérequis manuels (Jérôme, non exécutable par un agent)

Ordre (passation `pi-2b`) : bots → groupe → sujets → verrouillage des bots → relevé
des IDs → envoi d'essai → Watchtower + Diun → fleet → Vigil → autres machines. État au
2026-11-24 : création des 5 bots en cours, IDs inconnus (Q6).

- [ ] Créer les 5 bots chez @BotFather : 1 bot d'envoi seul (nom provisoire `bbhome_notify_bot`) + 4 bots Vigil (dijon-master, dijon-slave, nice-master, nice-slave). « Group Privacy » activé pour chacun.
- [ ] Créer un groupe privé (supergroupe), sans lien d'invitation public ; activer les sujets (Topics) ; créer `fleet`, `agents`, `chezmoi`, `media` (et les sujets hors dépôt voulus, §20) — **sujets créés par Jérôme seul**.
- [ ] Ajouter les bots au groupe **sans droit admin** ; puis BotFather « Allow Groups » → off pour chaque bot.
- [ ] Relever user id, `chat_id` (`-100…`) et l'identifiant de chaque sujet (`message_thread_id`, visible dans le lien d'un message `t.me/c/<id>/<thread>/<msg>`).
- [ ] Un élément 1Password par bot ; celui du bot d'envoi seul = `op://Private/Telegram` : `bot-token`, `chat-id`, `thread-fleet`, `thread-agents`, `thread-chezmoi`, `thread-media`.
- [ ] Vérifier une fois à la main (jeton sur stdin, jamais en argv) qu'un message atteint le sujet `fleet`.

### Sprint Overview

| Sprint | Titre | Dépend de | Batch | Modèle | En parallèle avec |
| --- | --- | --- | --- | --- | --- |
| 1 | Émetteurs communs (agent-alert, transport fleet, egress) | — | 1 | sonnet | — |
| 2 | chezmoi-autoupdate, config générée, media, docs env | 1 | 2 | sonnet | 3 |
| 3 | Câblage fleet (double envoi, pull, notify-test) | 1 | 2 | sonnet | 2 |
| 4 | Bascule : suppression de ntfy | 2, 3 + grille | 3 | sonnet | — |

Fichiers : les sprints 2 et 3 n'ont aucun fichier modifiable en commun (vérifié par
`bash ~/.claude/hooks/scripts/validate-sprint-boundaries.sh docs/tasks/infra/feature/2026-11-24_1757-telegram-migration` (lancé depuis la racine du dépôt), script du
système de workflow de Jérôme : conflits par batch, fichiers existants, cycles).

### Sprint 1 : Émetteurs communs → `sprints/01-emetteurs-communs.md`

**Objective :** `agent-alert` multi-backend avec catégories → sujets, portable macOS
et déployé sur Mac ; transport Telegram de fleet (file, 429, repli sujet, masquage) ;
schéma `telegram:` dans `fleet.yml` ; script d'egress.
**Estimated effort :** L — **Dependencies :** sprint 0 (pour les essais manuels seulement).
**File Boundaries :** crée `scripts/telegram_egress_check.py`,
`scripts/test_telegram_egress_check.py` ; modifie `executable_agent-alert`,
`test_agent_alert.py`, `.chezmoiignore.tmpl`, `run_once_12-disable-macos-agent-stacks.sh.tmpl`,
`lib/notify.py`, `lib/schema.py`, `lib/inventory.py`, `fleet.yml`,
`test_fleet_report.py`, `test_fleet_inventory.py`.
**Acceptance :** voir le fichier du sprint.

### Sprint 2 : chezmoi-autoupdate, config, media, docs → `sprints/02-chezmoi-autoupdate-media-config.md`

**Objective :** erreurs `chezmoi-autoupdate` notifiées via `agent-alert --category chezmoi`
(limiteur 24 h), Phase E supprimée, `agent-alert.conf` généré depuis 1Password (si Q1
validée), sujet `media` pour `media_automation`, docs d'environnement à jour.
**Estimated effort :** M — **Dependencies :** sprint 1.
**File Boundaries :** crée `scripts/test_chezmoi_autoupdate_alert.py` ; modifie
`executable_chezmoi-autoupdate`, `executable_dotfiles-generated-config` (générateur
de secrets : nouvelle sorte `alert`, revue Q1),
`run_onchange_generate-secrets.sh.tmpl`, `test_generated_config.py`,
`docs/GENERATED_CONFIG.md`, `dot_config/systemd/user/chezmoi-autoupdate.service`,
`bin/executable_media_automation.py`, `bin/test_media_automation.py`,
`dot_zsh/00-env.zsh.tmpl`, `executable_cminventory`, `docs/RUNBOOK.md`,
`dot_config/systemd/README.md`, `dot_local/bin/README.md`, `README.md`.

### Sprint 3 : Câblage fleet → `sprints/03-cablage-fleet.md`

**Objective :** fleet master en double envoi ntfy + Telegram, `fleet notify-test`,
mode pull Unix/Windows vers Telegram, rappel et docs FLEET.
**Estimated effort :** M — **Dependencies :** sprint 1. **Revue de Jérôme avant fusion**
(agent redéployé root).
**File Boundaries :** modifie `lib/orchestrate.py`, `agent/fleet-agent.sh`,
`agent/fleet-agent.ps1`, `dot_local/bin/executable_fleet`,
`dot_config/systemd/user/fleet-reminder.service`, `docs/FLEET.md`,
`test_fleet_orchestrate.py`, `test_fleet_pull.py`, `test_fleet_windows_contract.py`.
**Contrainte :** la regex de jeton du mode pull devient le motif Telegram complet
**ancré** ; elle ne doit jamais être élargie à `:`+n'importe quoi (pas d'affaiblissement
de la validation).

### Sprint 4 : Bascule → `sprints/04-bascule-suppression-ntfy.md`

**Objective :** une fois la grille complète, supprimer tout ntfy (code, clés, tests,
CLI, docs), mettre à jour les invariants, liste de démantèlement manuelle.
**Estimated effort :** L — **Dependencies :** sprints 2, 3 et la grille de bascule
(remplie par Jérôme après 1-2 semaines de double envoi).
**File Boundaries :** voir `sprints/04-bascule-suppression-ntfy.md` (≈ 40 fichiers :
toutes les occurrences ntfy hors exceptions §13, plus `Brewfile_blacklist`,
l'overlay `Brewfile_JeromeSacMiniM6` et son hash dans
`docs/PACKAGE_BASELINE_2026-11-14.json`, `INVARIANTS.md` racine).

## 18. Execution Log

Suivi dans `progress.json`.

## 19. Learnings

À remplir après les sprints.

## 20. Dépendances externes (hors dépôt, portes de bascule)

Aucune n'est une tâche d'agent de ce PRD. Elles conditionnent seulement l'arrêt du
serveur ntfy (porte D16 b). Faits côté Pi : session `pi-2b`.

| Dépendance | Où | Action | Point à vérifier |
| --- | --- | --- | --- |
| Watchtower | Pi `~/docker/monitoring` | `WATCHTOWER_NOTIFICATION_URL` shoutrrr → `telegram://` (bot d'envoi seul) | prise en charge de `message_thread_id` par shoutrrr (Q10) |
| Diun | Pi, même `.env` que Watchtower (le conteneur diun porte aussi `WATCHTOWER_NOTIFICATION_URL`) | notifieur Telegram natif | prise en charge des sujets (Q10) |
| Vigil | dépôt propre, session dédiée `vigil-68` | restaurer le bot Telegram du commit `0ae7597`, un bot par routeur, boutons de confirmation de redémarrage TP-Link via `callback_query` en gardant les garanties de `src/confirm.py` (jeton à usage unique, `CONFIRM_TTL` 600 s, lié à l'action, `hmac.compare_digest`, anti-rejeu) | décision d'août « les boutons de confirmation ne transitent jamais par Internet » **révisée par Jérôme le 2026-11-24 : option 3b retenue** (bouton `callback_query` via Telegram, avec les garanties de `src/confirm.py` + contrôle user ID et chat ID du groupe). **Topologie (Jérôme, 2026-11-24, KISS) :** pas de sujet « Vigil – Ops » ; deux sujets « Vigil – Dijon » et « Vigil – Nice » ; seul le bot du **master** d'un site poste, le slave ne poste que si le master ne répond plus (« dijon-master ne répond plus ») ; chaque site surveille l'autre et poste dans le sujet du site tombé si master et slave sont muets ; tout message hors site va dans le sujet général du groupe |
| CI `unifi-network-server` | autre dépôt, `.github/workflows/notify.yml` (déjà Telegram via `BOT_TOKEN`) | passer au bot d'envoi seul et au bon sujet | — |
| `infra-dijon`, `infra-nice`, `proxmox`, `pyload`, `fork-keeper` | autres machines, à localiser (Q7) | migrer vers le bot d'envoi seul | `infra-nice` = `media_automation` ? (alors couvert par le sprint 2) |
| Serveur ntfy | Pi `~/docker/prod/ntfy` | arrêt **en dernier** : sprint 4 fusionné et tous les topics silencieux ≥ 3 jours (D16 b) ; puis volumes, DNS/proxy `ntfy.bbhome.wf` | silence constaté côté serveur |
