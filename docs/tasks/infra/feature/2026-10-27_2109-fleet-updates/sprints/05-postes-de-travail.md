# Sprint 5: Postes de travail (Windows, macOS, WSL) + mode pull — priorité basse

## Meta

- **PRD:** `../spec.md`
- **Sprint:** 5 of 5
- **Depends on:** Sprint 4
- **Batch:** 5 (sequential)
- **Model:** sonnet
- **Estimated effort:** L

## Objective

Pouvoir mettre à jour ponctuellement les postes de travail (souvent mis à jour à
la main) et laisser les machines souvent éteintes se rattraper seules. Ce sprint
peut être reporté sans bloquer le v1.

## File Boundaries

### Creates (new files)

- `dot_local/share/fleet/agent/fleet-agent.ps1` — agent Windows (PowerShell 5.1)
- `dot_local/share/fleet/agent/fleet-bootstrap.ps1` — à lancer une fois en admin
- `Library/private_LaunchAgents/com.jsoyer.fleet-pull.plist.tmpl` — mode pull macOS
- `dot_config/systemd/user/fleet-pull.service`
- `dot_config/systemd/user/fleet-pull.timer`
- `scripts/test_fleet_windows_contract.py` — validation du JSON produit par l'agent PS (fixtures)

### Modifies (can touch)

- `dot_local/share/fleet/agent/fleet-agent.sh` — ajustements macOS (launchd, `/var/log/fleet-agent.log`, contrôle des MAJ automatiques natives)
- `dot_local/share/fleet/fleet.yml` — postes Windows / macOS
- `docs/FLEET.md` — section postes de travail

### Read-Only (reference but do NOT modify)

- `Library/private_LaunchAgents/com.jsoyer.chezmoi-autoupdate.plist.tmpl` — modèle launchd
- `.chezmoiscripts/03-configure/run_once_enable-chezmoi-autoupdate.ps1.tmpl` — modèle PowerShell chezmoi

### Shared Contracts (consume from prior sprints or PRD)

- Schéma JSON v1, verbes, codes de sortie (identiques à l'agent Unix)

### Consumed Invariants (from INVARIANTS.md)

- Verbes de l'agent — même liste que l'agent Unix
- Vocabulaire des statuts

## Tasks

- [ ] **Valider d'abord** sur un vrai PC : winget et Scoop via une tâche planifiée dans le contexte de l'utilisateur (winget fonctionne mal sous SSH / SYSTEM)
- [ ] `fleet-bootstrap.ps1` : OpenSSH Server (capability + service auto) ; pare-feu port 22 limité à 100.64.0.0/10 ; `administrators_authorized_keys` avec commande imposée et ACL Administrators + SYSTEM uniquement ; source Event Log `fleet-agent` ; tâches planifiées (exécution détachée + pull) ; vérification de winget
- [ ] `fleet-agent.ps1` : mêmes 5 verbes et même JSON ; MAJ dans l'ordre : Windows Update (API COM `Microsoft.Update.Session`), `winget upgrade --all`, Scoop (`scoop update`, `scoop update --all`, `--global` si présent), WSL (`wsl --update`, puis chaque distribution de `wsl -l -q` : `sysup` si présent sinon gestionnaire de paquets en root ; jamais `wsl --shutdown` si session active), Defender (`Update-MpSignature`) ; pas de Chocolatey
- [ ] Vérifications préalables Windows : `on_battery`, `metered_network`, `user_active` ; délai 120 min
- [ ] macOS : agent Unix validé (Remote Login, sudoers limité à `/sbin/shutdown -r now` pour le verbe `reboot` (§10, revue par Jérôme), `sysup`, vérification que les MAJ automatiques macOS sont actives ; macOS système jamais installé par l'agent sur Apple Silicon)
- [ ] Mode pull : timer systemd (portables Linux), launchd (macOS), tâche planifiée (Windows) ; déclenche `update` si dernière MAJ > 7 jours, notifie ntfy priorité 2 ; jamais de redémarrage ; jamais sur `critical` ni guardians

## Acceptance Criteria

- [ ] PSScriptAnalyzer sans erreur
- [ ] Commande hors liste blanche sur Windows ⇒ refus + Event Log
- [ ] `check` + `update` réels sur un PC Windows et un Mac
- [ ] Un poste rallumé après > 7 jours se met à jour et notifie seul
- [ ] Aucun redémarrage déclenché en mode pull

## Verification

- [ ] `pwsh -c "Invoke-ScriptAnalyzer -Path dot_local/share/fleet/agent -Recurse"` (si pwsh disponible, sinon sur le PC Windows)
- [ ] `python3 -m pytest scripts/test_fleet_windows_contract.py`
- [ ] `plutil -lint` sur le plist généré (sur un Mac)

## Context

Windows et macOS sont des postes de travail, mis à jour ponctuellement et souvent
à la main ; le support est voulu mais secondaire. macOS : option A — MAJ système
par les MAJ automatiques natives, l'agent ne lance que `sysup` (brew, mas, outils IA)
et vérifie/signale. Apple Silicon exige le mot de passe du propriétaire du volume
pour installer macOS : non automatisé volontairement.

## Agent Notes (filled during execution)

- Assigned to:
- Started:
- Completed:
- Decisions made:
- Assumptions:
- Issues found:
