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

- [x] Écrire `docs/FLEET.md` (prérequis par type, liste des actions manuelles : coffre 1Password « Fleet », compte de service, topic + jeton ntfy, utilisateur API OPNsense, jetons HA)
- [x] Alias `fup` (zsh + bash via `aliases.sh`)
- [x] Rédiger l'ACL : `tag:fleet-master` (diabolo, penelope) seul autorisé sur le port 22 des cibles ; Jérôme l'applique lui-même
- [ ] Premier `fleet up` complet réel (Linux + appliances, hors `--critical`) ; relire le rapport avec Jérôme — BLOCKED (infra réelle, requiert Jérôme)
- [ ] `fleet up --critical` réel : OPNsense puis `multibox`, avec confirmation — BLOCKED (infra réelle, requiert Jérôme)
- [ ] Corriger `fleet.yml` selon les constats — BLOCKED (infra réelle, requiert Jérôme) (dépend des runs réels)

## Acceptance Criteria

- [x] `docs/FLEET.md` couvre chaque commande et chaque prérequis
- [x] `fup` disponible dans zsh et bash
- [x] ACL rédigée et remise, non appliquée par l'agent
- [ ] Un run complet réel sans `failed` inexpliqué ; chaque `skipped`/`degraded` a une raison — BLOCKED (infra réelle, requiert Jérôme)
- [ ] `--critical` réel réussi avec retour d'OPNsense et de `multibox` — BLOCKED (infra réelle, requiert Jérôme)

## Verification

- [x] `shellcheck dot_shell_common/aliases.sh` (0 nouveau constat ; exit 1 dû aux 145 constats préexistants, identiques à la base 4276455f)
- [ ] Rapport du run réel archivé dans `.artifacts/reports/` — BLOCKED (infra réelle, requiert Jérôme)

## Context

Priorité des cibles : Linux et appliances d'abord ; le v1 est considéré utile à
la fin de ce sprint. Les postes de travail (Windows, macOS) viennent au sprint 5.

Risques acceptés (2026-10-27) : port 22 ouvert à tout le tailnet jusqu'à
l'application de l'ACL ; jetons API hors commande imposée.

## Agent Notes (filled during execution)

- Assigned to: sprint-executor (sonnet, worktree, branch `sprint/04-finitions`), orchestrator (opus) for review fixes and merge
- Started: 2026-10-31
- Completed: 2026-10-31 (local part); merge 8676a707 on feat/fleet-plan. Live items BLOCKED.
- Decisions made:
  - `docs/FLEET.md` (English, like the rest of docs/) derived from the code: wrapper verbs ping/check/help + forwarded up/reboot/report/logs/changes/hold/unhold/holds/reminder/bootstrap, every argparse option, 5 agent verbs, 13 statuses, 9 kinds, exit codes 1/2/3.
  - `alias fup='fleet up'` right after `sysup()` in `dot_shell_common/aliases.sh`, unguarded like sysup; sourced by `dot_zsh/10-aliases.zsh:8` and `dot_bash/10-aliases.bash:7`. Fish/nushell not covered (documented).
  - ACL draft: `tagOwners` (autogroup:admin) for tag:fleet-master and tag:fleet-target, one `acls` rule tag:fleet-master -> tag:fleet-target:22, `grants` alternative commented, 3 `tests`. Masters carry both tags (they update and sync each other over SSH). Tailscale SSH must stay OFF on targets (would bypass the forced command).
  - CHEZMOISCRIPTS.md documents run_onchange_install-fleet-agent and run_always_install-sudoers-sysup.
- Assumptions:
  - The 1Password reference is item "Fleet" in vault "Private" (`op://Private/Fleet/<field>`), not a vault named "Fleet" as the spec wording suggested; FLEET.md follows the code.
  - Master-to-master rsync refused by the forced command: inferred from code (lower confidence).
- Issues found:
  - Review (2 sonnet reviewers, PASS with minor fixes), all fixed in 6f4a14bb: ACL must say an allow-all rule has to be REPLACED (ACLs are additive, no deny); stronger tests (target->target deny); key revocation reordered emergency-first, overwrite-not-add the 1Password field, inline warning that deleting the scriptState bucket replays every run_once/run_onchange script; markdown table `|` breakage; unclear `fleet hold` sentence in the manual procedure.
  - `fleet ping`/`check` take plain aliases only (inventory `plan_rows` rejects unknown names), not selectors; `reboot` has `--dry-run` that the wrapper usage omits (documented).
  - Main checkout: the unknown formatter reflowed 16 fleet .py/test files again (uncommitted, not part of this sprint); verification ran on a `git archive` export of 8676a707.
  - BLOCKED (live infra, requires Jérôme): first real full `fleet up`, real `fleet up --critical` (OPNsense then multibox), fleet.yml corrections from the real runs, real-run report in `.artifacts/reports/`. ACL not applied (Jérôme applies it).
