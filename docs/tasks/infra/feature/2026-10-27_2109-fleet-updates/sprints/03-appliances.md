# Sprint 3: Appliances (PiKVM, OPNsense, Home Assistant, OMV, Proxmox)

## Meta

- **PRD:** `../spec.md`
- **Sprint:** 3 of 5
- **Depends on:** Sprint 2
- **Batch:** 3 (sequential)
- **Model:** sonnet
- **Estimated effort:** L

## Objective

Couvrir les cibles qui n'utilisent pas `sysup` : PiKVM (+ cloudflared), OMV,
hôte Proxmox via l'agent ; OPNsense et Home Assistant via leur API ; plus
`fleet bootstrap <host>` pour installer l'agent hors chezmoi.

## File Boundaries

### Creates (new files)

- `dot_local/share/fleet/lib/api_opnsense.py` — API firmware OPNsense
- `dot_local/share/fleet/lib/api_homeassistant.py` — API Home Assistant
- `dot_local/share/fleet/lib/bootstrap.py` — `fleet bootstrap <host>`
- `scripts/test_fleet_appliances.py`

### Modifies (can touch)

- `dot_local/share/fleet/agent/fleet-agent.sh` — branches `omv`, `pikvm`, `proxmox`
- `dot_local/share/fleet/lib/orchestrate.py` — routage des kinds API (`opnsense`, `homeassistant`)
- `dot_local/bin/executable_fleet` — verbe `bootstrap`
- `dot_local/share/fleet/fleet.yml` — paramètres API (URL tailnet, référence 1Password)

### Read-Only (reference but do NOT modify)

- `dot_local/share/fleet/lib/notify.py`
- `dot_local/share/fleet/lib/report.py`

### Shared Contracts (consume from prior sprints or PRD)

- Schéma JSON v1 : les modules API produisent le même JSON que l'agent

### Consumed Invariants (from INVARIANTS.md)

- Vocabulaire des statuts
- Aucun secret en sortie

## Tasks

- [ ] **OMV** : `omv-upgrade` (pas `apt` direct), non interactif ; chemins absolus des commandes du fragment sudoers résolus par `command -v` au bootstrap
- [ ] **PiKVM** : une seule fenêtre `rw` avec `trap` garantissant `ro` même en échec ; `pikvm-update` ; puis `cloudflared` (**binaire installé à la main**) : `cloudflared update`, redémarrage du service si la version change, ancienne version conservée et restaurée si le tunnel ne revient pas ; santé : `kvmd` actif + tunnel prêt (`/ready` des métriques locales) ; délai 20 min
- [ ] **Proxmox (`multibox`)** : agent Unix, branche `proxmox` = `apt-get dist-upgrade` non interactif via `sysup` (dépôts Proxmox) ; `critical: true` ; `critical` (hors `fleet up` sans `--critical`) ; jamais de redémarrage automatique ; avertissement listant les VM avant confirmation
- [ ] **OPNsense** (API, utilisateur `fleet`, droit unique « System: Firmware ») : `check` = `POST /api/core/firmware/check` + `GET /api/core/firmware/status` ; `update` = `POST /api/core/firmware/update` (pas de copie de `config.xml` sur le master : elle exigerait un droit au-delà de « System: Firmware » ; l'historique de configuration local d'OPNsense suffit, une MAJ firmware ne modifie pas la config) (mineures seulement), suivi `/api/core/firmware/upgradestatus`, attente du retour (ping + nœud tailnet + API) 15 min max ; **majeures OPNsense jamais appliquées** (`upgrade_major_version` ⇒ `major_available`) ; vérifier les endpoints exacts sur la version installée
- [ ] **Home Assistant** (API, utilisateur dédié, jeton longue durée) : sauvegarde d'abord (échec ⇒ `skipped`), puis Core + add-ons + OS, **versions majeures incluses** ; la MAJ OS redémarre l'appareil : attente de l'API 15 min max, sinon ntfy priorité 5
- [ ] `fleet bootstrap <host>` : installe agent, clé à commande imposée, `known_hosts` et le fragment sudoers du `kind` (liste fermée §10 : OMV `omv-upgrade` ; PiKVM `rw`, `ro`, `pikvm-update`, `cloudflared update`, `systemctl restart cloudflared` ; + `systemctl reboot`), validé par `visudo -cf` ; **Stop et revue par Jérôme** avant application (PiKVM : dans une fenêtre `rw`)
- [ ] Jetons API lus depuis 1Password à l'exécution, jamais écrits sur disque ni affichés
- [ ] Droits minimaux vérifiés : OPNsense, un appel hors « System: Firmware » (ex. `GET /api/core/system/status` hors privilège) ⇒ 403 ; HA, utilisateur dédié non propriétaire

## Acceptance Criteria

- [ ] `check` réel sur chaque type (OMV, PiKVM, OPNsense, HA, Proxmox)
- [ ] PiKVM revient en `ro` même si `pikvm-update` échoue (test simulé)
- [ ] OPNsense : une montée majeure disponible est signalée (`major_available`) et non appliquée
- [ ] HA : sauvegarde en échec (simulée) ⇒ aucune MAJ, statut `skipped` ; MAJ majeure HA appliquée après sauvegarde réussie
- [ ] Utilisateurs API à droits minimaux (test 403 OPNsense, HA non propriétaire)
- [ ] `fleet up` sans `--critical` ne touche ni OPNsense ni `multibox`
- [ ] Fragments sudoers OMV / PiKVM = liste fermée §10 exactement, `visudo -cf` OK
- [ ] Aucun jeton dans `runs/`, journaux, notifications (`grep`)
- [ ] `update` réel sur un type à faible risque (OMV ou PiKVM)

## Verification

- [ ] `python3 -m pytest scripts/test_fleet_appliances.py`
- [ ] `shellcheck dot_local/share/fleet/agent/fleet-agent.sh`

## Context

**OPNsense** route les VM du Proxmox (`multibox`, site de Dijon). Ses MAJ et celles
de `multibox` passent en dernier (`--critical`), OPNsense puis `multibox`.
Les masters ne sont pas derrière OPNsense.

**Risque accepté (2026-10-27) :** les jetons API OPNsense / HA détenus par les
masters échappent à la commande imposée. Atténuations : droits minimaux, jetons
dans 1Password (compte de service révocable), jamais en clair sur disque.

**Délais :** omv 30 min, pikvm 20 min, homeassistant 45 min, opnsense 30 min, proxmox 45 min.

## Agent Notes (filled during execution)

- Assigned to:
- Started:
- Completed:
- Decisions made:
- Assumptions:
- Issues found:
