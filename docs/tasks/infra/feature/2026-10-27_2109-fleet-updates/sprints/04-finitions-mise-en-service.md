# Sprint 4: Finitions et mise en service (Linux + appliances)

## Meta

- **PRD:** `../spec.md`
- **Sprint:** 4 of 5
- **Depends on:** Sprint 3
- **Batch:** 4 (sequential)
- **Model:** sonnet
- **Estimated effort:** M

## Objective

Rendre le v1 utilisable au quotidien sur les cibles prioritaires (Linux +
appliances) : documentation, alias, ACL Tailscale rédigée, premiers runs réels complets.

## File Boundaries

### Creates (new files)

- `docs/FLEET.md` — installation, prérequis, commandes, sélecteurs, statuts, révocation d'une clé, procédure manuelle
- `docs/tasks/infra/feature/2026-10-27_2109-fleet-updates/tailscale-acl.hujson` — extrait d'ACL proposé (non appliqué)

### Modifies (can touch)

- `dot_shell_common/aliases.sh` — alias `fup='fleet up'`
- `docs/ALIASES.md` — documenter `fup` et `fleet`
- `docs/CHEZMOISCRIPTS.md` — documenter `run_onchange_install-fleet-agent`
- `dot_local/share/fleet/fleet.yml` — corrections issues des runs réels

### Read-Only (reference but do NOT modify)

- `dot_local/bin/executable_fleet`
- `dot_local/share/fleet/agent/fleet-agent.sh`

### Shared Contracts (consume from prior sprints or PRD)

- Toutes les commandes `fleet` et leurs options

### Consumed Invariants (from INVARIANTS.md)

- Verbes de l'agent

## Tasks

- [ ] Écrire `docs/FLEET.md` (prérequis par type, liste des actions manuelles : coffre 1Password « Fleet », compte de service, topic + jeton ntfy, utilisateur API OPNsense, jetons HA)
- [ ] Alias `fup` (zsh + bash via `aliases.sh`)
- [ ] Rédiger l'ACL : `tag:fleet-master` (diabolo, penelope) seul autorisé sur le port 22 des cibles ; Jérôme l'applique lui-même
- [ ] Premier `fleet up` complet réel (Linux + appliances, hors `--critical`) ; relire le rapport avec Jérôme
- [ ] `fleet up --critical` réel : OPNsense puis `multibox`, avec confirmation
- [ ] Corriger `fleet.yml` selon les constats

## Acceptance Criteria

- [ ] `docs/FLEET.md` couvre chaque commande et chaque prérequis
- [ ] `fup` disponible dans zsh et bash
- [ ] ACL rédigée et remise, non appliquée par l'agent
- [ ] Un run complet réel sans `failed` inexpliqué ; chaque `skipped`/`degraded` a une raison
- [ ] `--critical` réel réussi avec retour d'OPNsense et de `multibox`

## Verification

- [ ] `shellcheck dot_shell_common/aliases.sh`
- [ ] Rapport du run réel archivé dans `.artifacts/reports/`

## Context

Priorité des cibles : Linux et appliances d'abord ; le v1 est considéré utile à
la fin de ce sprint. Les postes de travail (Windows, macOS) viennent au sprint 5.

Risques acceptés (2026-10-27) : port 22 ouvert à tout le tailnet jusqu'à
l'application de l'ACL ; jetons API hors commande imposée.

## Agent Notes (filled during execution)

- Assigned to:
- Started:
- Completed:
- Decisions made:
- Assumptions:
- Issues found:
