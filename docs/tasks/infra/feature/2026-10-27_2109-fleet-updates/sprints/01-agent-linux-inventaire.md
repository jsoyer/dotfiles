# Sprint 1: Agent Linux + inventaire

## Meta

- **PRD:** `../spec.md`
- **Sprint:** 1 of 5
- **Depends on:** None
- **Batch:** 1 (sequential)
- **Model:** sonnet
- **Estimated effort:** L

## Objective

Livrer `fleet-agent` (Unix) sûr — 5 verbes en liste blanche, appelé via une clé SSH
à commande imposée — déployé par chezmoi, avec `sysup` extrait en exécutable,
l'inventaire `fleet.yml`, et un `fleet` minimal (`ping`, `check`) côté master.

## File Boundaries

### Creates (new files)

- `dot_local/bin/executable_sysup` — `sysup` extrait de `aliases.sh` (bash 3.2)
- `dot_local/share/fleet/agent/fleet-agent.sh` — agent Unix (POSIX sh / bash 3.2)
- `dot_local/share/fleet/fleet.yml` — inventaire (hôtes, sites, kinds, groupes, canary, critical_services, délais)
- `dot_local/share/fleet/lib/inventory.py` — lecture `tailscale status --json` + `fleet.yml` (Python 3.9, stdlib)
- `dot_local/bin/executable_fleet` — wrapper master, verbes `ping` et `check` uniquement dans ce sprint
- `.chezmoiscripts/03-configure/run_onchange_install-fleet-agent.sh.tmpl` — installe l'agent root 0755 dans `/usr/local/libexec/fleet-agent`, la clé à commande imposée dans `authorized_keys`
- `scripts/test_fleet_agent.py` — tests : liste blanche, schéma JSON, verrou, vérifications préalables
- `scripts/test_fleet_inventory.py` — tests : inventaire, groupes, validation `kind`/`site`

### Modifies (can touch)

- `dot_shell_common/aliases.sh` — `sysup()` réduite à `command sysup "$@"`
- `dot_config/private_fish/config.fish.tmpl` — fonction fish `sysup` réduite à un appel du script
- `dot_config/nushell/config.nu` — `def sysup` réduite à un appel du script
- `.chezmoiscripts/03-configure/run_always_install-sudoers-sysup.sh.tmpl` — ajouter les seules commandes exactes requises par l'agent (`systemctl reboot` pour le verbe `reboot`) ; ne rien élargir d'autre

### Read-Only (reference but do NOT modify)

- `dot_config/systemd/user/chezmoi-autoupdate.service` — modèle d'unité
- `.chezmoiscripts/03-configure/run_onchange_generate-ssh-config.sh.tmpl` — conventions de script chezmoi
- `scripts/test_chezmoi_consistency.py` — style des tests Python du repo

### Shared Contracts (consume from prior sprints or PRD)

- Verbes : `check`, `update`, `reboot-status`, `reboot`, `report`
- Sortie JSON v1 (voir Context) et codes de sortie 0/1/2/3
- Valeurs `kind` : `chezmoi-linux`, `chezmoi-macos`, `omv`, `pikvm`, `homeassistant`, `opnsense`, `proxmox`, `windows`, `guardian`
- Valeurs `site` : `dijon`, `nice`, `garage`, `cloud`, `mobile`

### Consumed Invariants (from INVARIANTS.md)

- Verbes de l'agent — liste identique partout
- Vocabulaire des statuts
- Valeurs `kind` / `site`
- Aucun secret en sortie

## Tasks

- [ ] Créer une VM de test jetable sur `multibox` (clone d'un modèle Debian ou Fedora) ; contrôle de cohérence `pveversion` sur `multibox` (décidé hôte Proxmox, §14), noté dans Agent Notes — BLOCKED: requires live infra / user action (multibox VM + pveversion; not touched)
- [x] Extraire `sysup` en `dot_local/bin/executable_sysup` (comportement identique, flag `--reboot` conservé pour l'usage manuel ; **l'agent ne le passe jamais**) ; réduire les fonctions bash/zsh, fish, nushell à un appel
- [x] Rendre `sysup` strictement non interactif : `DEBIAN_FRONTEND=noninteractive`, `NEEDRESTART_MODE=l`, `-o Dpkg::Options::=--force-confdef -o Dpkg::Options::=--force-confold` ; vérifier brew (`HOMEBREW_NO_*` / brew.env)
- [x] Écrire `fleet-agent.sh` : lit `SSH_ORIGINAL_COMMAND`, liste blanche des 5 verbes, aucun argument libre ; refus ⇒ code 1 + journalisation
- [x] Verrou (`flock`, ou `mkdir` atomique sur macOS) ⇒ `busy` code 3 — mkdir atomique sur Linux et macOS (voir Agent Notes)
- [x] Journalisation de chaque appel/refus : journald (`logger -t fleet-agent`) sur Linux, `/var/log/fleet-agent.log` sur macOS
- [x] `update` détaché : `systemd-run --user --unit=fleet-update-<job>` (Linux, sans sudo ; `loginctl enable-linger` posé par le script d'installation), `nohup` + fichier d'état (macOS) ; renvoie `started` + `job` ; `report` renvoie l'état du dernier job lu sur disque
- [x] Vérifications préalables : `disk_low`, `on_battery`, `metered_network`, `update_in_progress` ⇒ `skipped` avec raison
- [x] Santé avant/après : unités systemd en échec, conteneurs Docker `unhealthy`/arrêtés, disque, `critical_services` ⇒ `degraded`
- [x] Liste `changes` (dnf/apt/pacman/brew) et `config_conflicts` (`.dpkg-dist`, `.rpmnew`, `.pacnew`)
- [x] `reboot-status` (needs-restarting / `/var/run/reboot-required` / noyau installé ≠ en cours) et `reboot` (ne fait rien si non requis)
- [x] Sudoers (kinds chezmoi-linux, proxmox, guardian — liste fermée §10) : ajouter la seule commande exacte `/usr/bin/systemctl reboot` (aucun joker, pas de `systemd-run` en sudo) ; **Stop (§15) et revue par Jérôme** avant d'appliquer — implemented, awaiting review (§15), NOT applied; `visudo -cf` OK sur la règle rendue
- [x] Script chezmoi d'installation : `sudo install -o root -g root -m 0755` de `~/.local/share/fleet/agent/fleet-agent.sh` vers `/usr/local/libexec/fleet-agent`, `loginctl enable-linger`, clé `restrict,command="/usr/local/libexec/fleet-agent"` pour chaque master (clés publiques depuis 1Password « Fleet ») — implémenté, jamais exécuté pour de vrai (testé avec sudo/op simulés)
- [x] `fleet.yml` initial avec tous les hôtes du tailnet (alias propres, site, kind, groupes, `canary`, `critical_services`, délais par kind)
- [x] `fleet ping` et `fleet check` (séquentiels suffisent dans ce sprint) ; `StrictHostKeyChecking yes` — testés avec ssh/tailscale simulés uniquement
- [x] Tests Python + `shellcheck`

## Acceptance Criteria

- [x] Verbe inconnu ou argument supplémentaire ⇒ code 1, rien exécuté, ligne de journal présente — test_fleet_agent.py::Whitelist
- [x] Tentative de shell interactif avec la clé master ⇒ refusée — simulé : SSH_ORIGINAL_COMMAND absent/vide ⇒ code 1 (Whitelist.test_interactive_shell_attempt_has_no_command) ; la clé réelle `restrict,command=` n'a pas été testée sur un hôte
- [x] Sortie de chaque verbe = une ligne JSON conforme au schéma v1 (validée par test) — test_fleet_agent.py::SchemaV1
- [x] Deuxième appel concurrent ⇒ `busy` (code 3) — LockAndDetach (dont 4 appels simultanés ⇒ 1 seul démarre)
- [ ] Sur la VM de test : tuer la session SSH pendant `update` n'interrompt pas la MAJ ; `report` retourne ensuite l'état final — BLOCKED: requires live infra / user action (simulé localement : LockAndDetach.test_ssh_killed_during_update_does_not_stop_the_job ; pas de VM)
- [ ] Aucune MAJ n'attend de saisie (test sur la VM avec un conffile modifié : conflit listé dans `config_conflicts`) — BLOCKED: requires live infra / user action (conffile réel sur VM ; simulé : HealthAndConflicts.test_config_conflicts_are_listed + drapeaux apt non interactifs vérifiés statiquement)
- [ ] Service critique arrêté après MAJ (simulé sur la VM) ⇒ `degraded` — BLOCKED: requires live infra / user action (VM ; simulé : HealthAndConflicts.test_critical_service_down_after_update_is_degraded)
- [ ] `sysup` lancé à la main se comporte comme avant sur Fedora (zsh, bash, fish) — BLOCKED: requires live infra / user action (zsh/bash/fish sur Fedora non exécutés : lancer `sysup` lancerait une vraie MAJ ; syntaxe bash/zsh/fish vérifiée)
- [ ] `fleet check` réel : VM de test puis 3 machines Linux (Fedora, Debian, Arch) — BLOCKED: requires live infra / user action
- [ ] Agent installé root 0755 dans `/usr/local/libexec/fleet-agent`, non modifiable par l'utilisateur SSH — BLOCKED: requires live infra / user action (installation non faite ici ; `install -o root -g root -m 0755` vérifié dans le script rendu et testé avec sudo simulé)
- [ ] Sudoers : seule `systemctl reboot` ajoutée, `visudo -cf` OK, `sudo -l` ne montre aucun joker nouveau — BLOCKED: requires live infra / user action (`visudo -cf` OK ; `sudo -l` non exécuté ; règle NON appliquée, revue §15 en attente — voir Agent Notes : 2 lignes de plus que le texte du sprint)
- [x] `fleet ping` = commande du wrapper (pas un verbe agent) ; `offline` vs `unreachable` distingués (§12) — FleetWrapper tests (offline/unreachable distingués, aucune commande sur la clé agent)

## Verification

- [x] `shellcheck dot_local/share/fleet/agent/fleet-agent.sh dot_local/bin/executable_sysup dot_local/bin/executable_fleet` → exit 0
- [x] `python3 -m pytest scripts/test_fleet_agent.py scripts/test_fleet_inventory.py` → 130 passed (avec test_chezmoi_consistency.py)
- [x] `chezmoi execute-template < .chezmoiscripts/03-configure/run_onchange_install-fleet-agent.sh.tmpl | bash -n` → rendu + `bash -n` OK (avec `--source .`)
- [x] `visudo -cf` sur la règle sudoers générée → parsed OK

## Context

**Pourquoi :** une seule commande pour mettre à jour le tailnet. Sécurité : la clé
des masters (diabolo, penelope) ne peut lancer que `fleet-agent` ; un master
compromis ne peut que déclencher des MAJ / redémarrages, pas obtenir un shell.
Tailscale SSH est exclu (Tailworm, oct. 2026) : on utilise OpenSSH classique sur le tailnet.

**Compte :** l'utilisateur courant (pas d'utilisateur `fleet`) ; `sysup` réutilise
sa règle sudoers NOPASSWD existante.

**`sysup` actuel :** fonction dans `dot_shell_common/aliases.sh:437-544` (bash/zsh),
copies dans `config.fish.tmpl:591` et `config.nu:1227`. Seul flag : `--reboot`.
Linux : apt/dnf/pacman/rpm-ostree selon `MACHINE_PROFILE`, flatpak, brew,
update-omz, update-ai, mise, herdr. macOS : brew, mas, update-ai, mise, herdr.

**Contraintes :** bash 3.2 et Python 3.9 (macOS d'origine) — pas de tableaux vides
non protégés, pas de syntaxe PEP 604.

**Schéma JSON v1 :**
```json
{"schema":1,"host":"omv-nice","verb":"update",
 "status":"started|running|updated|up-to-date|degraded|failed|busy|skipped|unsupported",
 "reason":null,"packages":12,
 "changes":[{"name":"openssl","from":"3.0.13","to":"3.0.15"}],
 "health_before":{"failed_units":[],"unhealthy_containers":[],"disk_free_pct":{"/":41}},
 "health_after":{"failed_units":[],"unhealthy_containers":[],"disk_free_pct":{"/":39}},
 "preflight":{"ok":true,"blocked_by":null},
 "config_conflicts":[],"job":null,
 "reboot_required":true,"reboot_since":null,"os":"Debian 12.7","kernel":"6.1.0-26-amd64",
 "major_available":null,"started":"ISO8601","ended":"ISO8601","log_tail":"≤ 20 lignes, secrets masqués"}
```
Codes : 0 succès, 1 refusé, 2 échec MAJ, 3 busy.

**Vérifications préalables :** `disk_low` (`/` < 10 % ou `/boot` < 20 %), `on_battery`,
`metered_network`, `update_in_progress` (gestionnaire de paquets verrouillé).

## Agent Notes (filled during execution)

- Assigned to: sprint-executor (sonnet), worktree agent-ae91cd9b4c87ea267, branche feat/fleet-sprint1-agent (créée depuis feat/fleet-plan @ 332b9324 : le worktree d'origine pointait sur un autre commit, `git reset --hard` soumis à validation donc nouvelle branche)
- Started: 2026-10-30
- Completed: 2026-10-30 (tâches locales) ; tâches « infra live » laissées ouvertes
- Decisions made:
  - `sysup` : script autonome ; les helpers (update-ai, update-omz, mise, herdr, reboot hint) sont DUPLIQUÉS dans le script car `aliases.sh` ne peut pas être sourcé hors shell interactif. `update-ai`/`update-omz` restent dans aliases.sh (utilisés seuls). `_sysup_reboot_hint` supprimé d'aliases.sh et fish (plus utilisé). Code de sortie : non nul si l'étape gestionnaire de paquets échoue (l'agent s'en sert) ; l'ancienne fonction retournait le statut de la dernière commande. `MACHINE_PROFILE` absent en exécution détachée ⇒ déduit de /etc/os-release. PATH complété (~/.local/bin, linuxbrew).
  - Non interactif apt : `-o Dpkg::Options::=--force-confdef/--force-confold` ajoutés à la ligne `dist-upgrade` ET exportation de `DEBIAN_FRONTEND`/`NEEDRESTART_MODE`. Comme sudo efface l'environnement et que sudoers est à correspondance EXACTE des arguments, le sudoers a dû changer en conséquence : (a) la ligne `apt-get dist-upgrade -y` est remplacée par la même commande + les deux options (échappées `\:` `\=` requis par sudoers), (b) `Defaults:user env_keep += "DEBIAN_FRONTEND NEEDRESTART_MODE"`. Aucun droit de commande supplémentaire, mais c'est 2 changements au-delà de « seulement `systemctl reboot` » : À REVOIR par Jérôme (§15). Brew : HOMEBREW_NO_ASK/NONINTERACTIVE exportés par sysup.
  - Verrou : `mkdir` atomique partout (pas `flock`) car le verrou doit être transmis au job détaché ; pid + fichier `handoff` ; verrou orphelin (pid mort) repris. Seuls `update` et `reboot` verrouillent ; `check`/`reboot-status`/`report` restent lisibles pendant une MAJ (`check` ⇒ `running`).
  - Détachement : Linux `systemd-run --user --collect --unit=fleet-update-<job> --setenv=...` ; si systemd-run absent ou macOS : `nohup`. Le point d'entrée du job est sélectionné par la variable d'environnement `FLEET_AGENT_JOB_ID` (inaccessible au client SSH), jamais par SSH_ORIGINAL_COMMAND. Job tué sans état final ⇒ `report` = `failed` / `job_died`.
  - Sémantique de `check` (le spec ne la fixe pas) : 0 MAJ en attente ⇒ `up-to-date` ; sinon `skipped` avec reason `updates_pending` (ou la raison de préflight) et `packages`=N ; pas de gestionnaire connu ⇒ `unsupported` ; MAJ en cours ⇒ `running`. `reboot-status` ⇒ `up-to-date` + reason `reboot_required|no_reboot_required` (le champ `reboot_required` fait foi). `reboot` non requis ⇒ `skipped`/`no_reboot_required`, sinon `started`/`rebooting` puis `sudo -n /usr/bin/systemctl reboot` après délai de 3 s (détaché pour que la réponse parte).
  - `degraded` : nouvelle unité en échec, nouveau conteneur unhealthy/arrêté, service critique inactif, `/` < 10 % libre. `critical_services` est lu côté cible dans `~/.config/fleet-agent/critical-services` (aucun argument libre possible) ; le déploiement de ce fichier depuis fleet.yml n'est pas fait (voir Issues).
  - L'identité de la clé appelante n'est pas disponible dans l'agent (sshd ne l'expose pas avec une commande imposée sans PermitUserEnvironment) : on journalise l'IP cliente (SSH_CONNECTION) ; la ligne sshd « Accepted publickey ... SHA256 » du journal identifie la clé.
  - Script d'installation : le contenu de l'agent est intégré (include + sha256 dans un commentaire) plutôt que lu depuis ~/.local/share/fleet/agent/ : sans préfixe `after_`, le script peut tourner avant le dépôt du fichier. Clés publiques lues par `op read op://Private/Fleet/public-key-<master>` (noms de champs choisis ici : à créer dans 1Password) ; seules `ssh-ed25519 <blob>` bien formées sont acceptées, commentaire remplacé par `fleet-master-<master>` ; clé illisible ⇒ ligne existante conservée ; master retiré de la liste ⇒ ligne supprimée ; le script sort toujours en 0.
  - `fleet ping` : ouvre SSH avec `PreferredAuthentications=none` (clé d'hôte vérifiée en StrictHostKeyChecking=yes, authentification volontairement non tentée) pour ne jamais déclencher l'agent (un `ssh host true` serait un refus journalisé + ntfy 5). « Permission denied » = SSH ouvert ⇒ ok.
  - `fleet.yml` : 37 hôtes (iOS exclus). Sites et `ssh_user` majoritairement INFÉRÉS : chaque ligne incertaine est précédée d'un commentaire `# UNCERTAIN`. bbh-network = chezmoi-linux, tag infra. Canary posé sur un hôte par kind à plusieurs hôtes.
  - inventory.py : sous-ensemble YAML restreint écrit à la main (Python 3.9, stdlib), documenté en tête de fichier ; vermin : compatible 3.7+.
- Assumptions:
  - 🟡 sites/ssh_user de fleet.yml (voir ci-dessus) ; 🟡 sudoers : les `\:` `\=` ne sont validés que par `visudo -cf` (syntaxe), pas par un vrai appel sudo ; 🟡 `op://Private/Fleet/public-key-<master>` ; 🟢 `needs-restarting -r` rc 1 = redémarrage requis ; 🟡 `nmcli -g connection.metered connection show --active` = « yes » pour réseau limité ; 🟢 sshd `restrict,command=` met la commande client dans SSH_ORIGINAL_COMMAND.
  - Tests Linux seulement pour l'agent (outils simulés par PATH) ; la branche macOS (pmset, brew, shutdown, nohup, fichier journal) n'est pas exécutée.
- Issues found:
  - Worktree de départ sur le mauvais commit (voir Assigned to).
  - Hors périmètre non modifié : `dot_local/bin/README.md` (documenter sysup/fleet), `.chezmoiignore.tmpl` (déploiement de `fleet`/`sysup` sur Windows non vérifié), docs/ALIASES.md.
  - Reste à faire (sprint suivant / action utilisateur) : créer l'item 1Password « Fleet » avec `public-key-diabolo` et `public-key-penelope` ; déployer `~/.config/fleet-agent/critical-services` depuis `critical_services` de fleet.yml ; revue §15 du sudoers puis `chezmoi apply` ; `_update_mise_if_present`/`_update_herdr_if_present` restent dans aliases.sh/fish/nu sans appelant (nettoyage possible, non fait : hors scope).
  - `bash --posix -n` sur aliases.sh refusé par l'environnement d'exécution ; `bash -n` et `zsh -n` OK (aliases.sh utilise `[[ ]]`, pas POSIX par nature). `nu-check` renvoyait « File not found » même sur l'original : vérifié par exécution d'un extrait `def --wrapped sysup`. config.fish rendu : `fish -n` OK.
