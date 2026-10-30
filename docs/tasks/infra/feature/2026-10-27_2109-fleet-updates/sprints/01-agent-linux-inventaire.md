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

- [ ] Créer une VM de test jetable sur `multibox` (clone d'un modèle Debian ou Fedora) ; contrôle de cohérence `pveversion` sur `multibox` (décidé hôte Proxmox, §14), noté dans Agent Notes
- [ ] Extraire `sysup` en `dot_local/bin/executable_sysup` (comportement identique, flag `--reboot` conservé pour l'usage manuel ; **l'agent ne le passe jamais**) ; réduire les fonctions bash/zsh, fish, nushell à un appel
- [ ] Rendre `sysup` strictement non interactif : `DEBIAN_FRONTEND=noninteractive`, `NEEDRESTART_MODE=l`, `-o Dpkg::Options::=--force-confdef -o Dpkg::Options::=--force-confold` ; vérifier brew (`HOMEBREW_NO_*` / brew.env)
- [ ] Écrire `fleet-agent.sh` : lit `SSH_ORIGINAL_COMMAND`, liste blanche des 5 verbes, aucun argument libre ; refus ⇒ code 1 + journalisation
- [ ] Verrou (`flock`, ou `mkdir` atomique sur macOS) ⇒ `busy` code 3
- [ ] Journalisation de chaque appel/refus : journald (`logger -t fleet-agent`) sur Linux, `/var/log/fleet-agent.log` sur macOS
- [ ] `update` détaché : `systemd-run --user --unit=fleet-update-<job>` (Linux, sans sudo ; `loginctl enable-linger` posé par le script d'installation), `nohup` + fichier d'état (macOS) ; renvoie `started` + `job` ; `report` renvoie l'état du dernier job lu sur disque
- [ ] Vérifications préalables : `disk_low`, `on_battery`, `metered_network`, `update_in_progress` ⇒ `skipped` avec raison
- [ ] Santé avant/après : unités systemd en échec, conteneurs Docker `unhealthy`/arrêtés, disque, `critical_services` ⇒ `degraded`
- [ ] Liste `changes` (dnf/apt/pacman/brew) et `config_conflicts` (`.dpkg-dist`, `.rpmnew`, `.pacnew`)
- [ ] `reboot-status` (needs-restarting / `/var/run/reboot-required` / noyau installé ≠ en cours) et `reboot` (ne fait rien si non requis)
- [ ] Sudoers (kinds chezmoi-linux, proxmox, guardian — liste fermée §10) : ajouter la seule commande exacte `/usr/bin/systemctl reboot` (aucun joker, pas de `systemd-run` en sudo) ; **Stop (§15) et revue par Jérôme** avant d'appliquer
- [ ] Script chezmoi d'installation : `sudo install -o root -g root -m 0755` de `~/.local/share/fleet/agent/fleet-agent.sh` vers `/usr/local/libexec/fleet-agent`, `loginctl enable-linger`, clé `restrict,command="/usr/local/libexec/fleet-agent"` pour chaque master (clés publiques depuis 1Password « Fleet »)
- [ ] `fleet.yml` initial avec tous les hôtes du tailnet (alias propres, site, kind, groupes, `canary`, `critical_services`, délais par kind)
- [ ] `fleet ping` et `fleet check` (séquentiels suffisent dans ce sprint) ; `StrictHostKeyChecking yes`
- [ ] Tests Python + `shellcheck`

## Acceptance Criteria

- [ ] Verbe inconnu ou argument supplémentaire ⇒ code 1, rien exécuté, ligne de journal présente
- [ ] Tentative de shell interactif avec la clé master ⇒ refusée
- [ ] Sortie de chaque verbe = une ligne JSON conforme au schéma v1 (validée par test)
- [ ] Deuxième appel concurrent ⇒ `busy` (code 3)
- [ ] Sur la VM de test : tuer la session SSH pendant `update` n'interrompt pas la MAJ ; `report` retourne ensuite l'état final
- [ ] Aucune MAJ n'attend de saisie (test sur la VM avec un conffile modifié : conflit listé dans `config_conflicts`)
- [ ] Service critique arrêté après MAJ (simulé sur la VM) ⇒ `degraded`
- [ ] `sysup` lancé à la main se comporte comme avant sur Fedora (zsh, bash, fish)
- [ ] `fleet check` réel : VM de test puis 3 machines Linux (Fedora, Debian, Arch)
- [ ] Agent installé root 0755 dans `/usr/local/libexec/fleet-agent`, non modifiable par l'utilisateur SSH
- [ ] Sudoers : seule `systemctl reboot` ajoutée, `visudo -cf` OK, `sudo -l` ne montre aucun joker nouveau
- [ ] `fleet ping` = commande du wrapper (pas un verbe agent) ; `offline` vs `unreachable` distingués (§12)

## Verification

- [ ] `shellcheck dot_local/share/fleet/agent/fleet-agent.sh dot_local/bin/executable_sysup dot_local/bin/executable_fleet`
- [ ] `python3 -m pytest scripts/test_fleet_agent.py scripts/test_fleet_inventory.py`
- [ ] `chezmoi execute-template < .chezmoiscripts/03-configure/run_onchange_install-fleet-agent.sh.tmpl | bash -n`
- [ ] `visudo -cf` sur la règle sudoers générée

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

- Assigned to:
- Started:
- Completed:
- Decisions made:
- Assumptions:
- Issues found:
