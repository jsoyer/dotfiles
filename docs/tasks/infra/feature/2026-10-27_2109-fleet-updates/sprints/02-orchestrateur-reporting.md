# Sprint 2: Orchestrateur + reporting + ntfy

## Meta

- **PRD:** `../spec.md`
- **Sprint:** 2 of 5
- **Depends on:** Sprint 1
- **Batch:** 2 (sequential)
- **Model:** sonnet
- **Estimated effort:** L

## Objective

Faire de `fleet` un orchestrateur complet : `fleet up` par phases, parallélisme
borné, ciblage `-l`, bascule entre masters, rapports, journaux, historique,
notifications ntfy, gel, témoins et rappel d'oubli.

## File Boundaries

### Creates (new files)

- `dot_local/share/fleet/lib/orchestrate.py` — phases, parallélisme, suivi des jobs détachés, délais
- `dot_local/share/fleet/lib/selector.py` — résolution de `-l`
- `dot_local/share/fleet/lib/report.py` — rendu terminal / Markdown / JSON, fusion d'historique
- `dot_local/share/fleet/lib/notify.py` — ntfy + file d'attente
- `dot_local/share/fleet/lib/state.py` — `holds-<master>.json`, `history-<master>.jsonl`, `last-success-<master>.json` (jamais purgé), rétention 1 mois
- `dot_local/share/fleet/lib/schema.py` — validation du JSON v1 des agents (stdlib)
- `dot_config/systemd/user/fleet-reminder.service`
- `dot_config/systemd/user/fleet-reminder.timer`
- `scripts/test_fleet_selector.py`
- `scripts/test_fleet_orchestrate.py`
- `scripts/test_fleet_report.py`

### Modifies (can touch)

- `dot_local/bin/executable_fleet` — ajouter `up`, `reboot`, `report`, `logs`, `changes`, `hold`, `unhold`, `holds`, `--dry-run`, `--critical`, `--no-canary`
- `dot_local/share/fleet/fleet.yml` — ajouter `masters`, `ntfy`, `parallel`
- `dot_local/share/fleet/lib/inventory.py` — exposer l'état en ligne (Tailscale + SSH ≤ 10 s)

### Read-Only (reference but do NOT modify)

- `dot_local/share/fleet/agent/fleet-agent.sh` — contrat de sortie
- `dot_config/systemd/user/chezmoi-autoupdate.timer` — modèle de timer

### Shared Contracts (consume from prior sprints or PRD)

- Schéma JSON v1 de l'agent, codes de sortie
- Statuts calculés par le master : `offline`, `unreachable`, `timeout`, `held`

### Consumed Invariants (from INVARIANTS.md)

- Vocabulaire des statuts
- Aucun secret en sortie
- Sélecteur vide ≠ tout le parc

## Tasks

- [ ] Phases (sélection dérivée de `fleet.yml`) : 1 = `chezmoi-linux`, `chezmoi-macos`, `omv`, `pikvm`, `windows` non critiques (parallèle) ; 2 = `homeassistant`, `guardian`, tags `infra`/`site-router` (série) ; 3 = `bbh-network` seul ; `critical` = OPNsense puis `multibox` (`--critical` + confirmation)
- [ ] Parallélisme (par master) : 10 au total, 4 maximum par site ; délais d'`update` par `kind`
- [ ] Témoins (`canary: true`) d'abord en phase 1 ; témoin `failed`/`degraded` ⇒ autres hôtes du `kind` `skipped (canary failed)` ; `--no-canary`
- [ ] Guardians : mis à jour seulement si un autre hôte du même site (hors guardians) est en ligne, sinon `skipped (site dégradé)`
- [ ] Master courant traité en dernier, en local, sans redémarrage
- [ ] Hôtes hors site : diabolo prioritaire, penelope en secours ; console → master du site, bascule si injoignable
- [ ] Suivi des jobs détachés (`started` → interrogation `report` → état final)
- [ ] Validation de schéma de chaque sortie d'agent (`schema.py`) avant tout rendu ; invalide ⇒ `failed`, jamais interpolée dans un shell
- [ ] Statuts master : `offline` (Tailscale `Online: false`, `LastSeen`), `unreachable` (Tailscale en ligne, SSH en échec ≤ 10 s), `timeout`, `held`
- [ ] Sélecteur `-l` : alias, `site=`, `kind=`, `tag:`, `@groupe`, `,` union, `!` exclusion ; vide ⇒ exit 2 ; `--dry-run`
- [ ] Gel : `fleet hold <host> --reason --until`, `unhold`, `holds` ⇒ statut `held` ; expiration automatique
- [ ] `fleet reboot --pending` : confirmation machine par machine
- [ ] Avertissement `--critical` listant les VM coupées avant confirmation
- [ ] Rapports : terminal, `runs/<run>/report.md`, `report.json`, `run.log`, `raw/<host>.log|json` ; `fleet report [--last]`, `fleet logs <host> [--run <id>]`, `fleet changes <host> [--since]`
- [ ] Historique : `history-<master>.jsonl` (un fichier par master), rsync vers l'autre master, fusion à la lecture (dédoublonnage `(run_id, host)`) ; `holds-<master>.json` et `last-success-<master>.json` synchronisés de la même façon (§11)
- [ ] Rétention 1 mois (`runs/` et historique)
- [ ] ntfy (serveur sur `bbh-network`, topic `fleet`, jeton depuis 1Password) : 6 types d'événements et priorités (voir Context), formats d'état et charge utile de §12 ; file d'attente si ntfy indisponible
- [ ] Alerte « > 30 j sans MAJ » calculée à chaque run depuis `last-success-*` fusionnés (non purgés)
- [ ] Timer de rappel (systemd user, quotidien) : ntfy priorité 3 si aucun `fleet up` depuis 14 j ; n'ouvre aucune connexion
- [ ] Masquage des secrets dans tous les rapports, journaux, notifications ; fichiers temporaires 0600

## Acceptance Criteria

- [ ] Ordre des phases respecté (test unitaire avec agents simulés)
- [ ] Jamais plus de 4 hôtes simultanés par site ni 10 au total (test)
- [ ] Hôte injoignable ⇒ `offline` avec date de dernière connexion, le run continue
- [ ] `fleet up -l site=inexistant` ⇒ exit 2, aucune connexion
- [ ] Témoin en échec ⇒ les autres hôtes du `kind` sautés
- [ ] Guardian d'un site sans autre hôte en ligne ⇒ `skipped`
- [ ] Hôte gelé ⇒ `held`, visible dans le rapport
- [ ] Sortie d'agent invalide (fixture) ⇒ `failed` (test)
- [ ] Hôte sans MAJ depuis 40 j, historique purgé à 31 j ⇒ alerte quand même (test)
- [ ] `grep -rE` des motifs de secrets sur `runs/` ⇒ vide
- [ ] ntfy coupé pendant un run ⇒ messages renvoyés au rétablissement
- [ ] Premier run réel : `fleet up -l site=garage`

## Verification

- [ ] `python3 -m pytest scripts/test_fleet_selector.py scripts/test_fleet_orchestrate.py scripts/test_fleet_report.py` (le schéma est testé dans `test_fleet_report.py`)
- [ ] `shellcheck dot_local/bin/executable_fleet`
- [ ] `systemd-analyze --user verify dot_config/systemd/user/fleet-reminder.*`

## Context

**Masters :** diabolo (Dijon, prioritaire Dijon + Garage + hors site) et penelope
(Nice). Actif/actif ; le verrou côté agent évite les doublons. Consoles : toute
machine où tu tapes `fleet`, qui se connecte à un master.

**Notifications ntfy :**
| Événement | Priorité |
| --- | --- |
| Run sans échec (synthèse « 24 ✅ · 0 ❌ · 3 reboot · 9 offline ») | 2 |
| Échec, `degraded`, témoin en échec, hôte > 30 j sans MAJ | 4 |
| Hôte redémarré non revenu (HA OS après MAJ, OPNsense, multibox) | 5 |
| Commande refusée par un agent | 5 |
| Mode pull : MAJ autonome | 2 |
| Rappel : aucun `fleet up` depuis 14 j | 3 |

**Aucune MAJ planifiée :** `fleet` est lancé à la main ; seul le timer de rappel tourne (lecture d'historique, aucune connexion).

**Aucun redémarrage automatique**, sauf la MAJ HA OS (sprint 3).

## Agent Notes (filled during execution)

- Assigned to:
- Started:
- Completed:
- Decisions made:
- Assumptions:
- Issues found:
