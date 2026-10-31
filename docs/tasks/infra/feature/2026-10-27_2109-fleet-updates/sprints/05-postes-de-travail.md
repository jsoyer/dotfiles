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

- [ ] **Valider d'abord** sur un vrai PC : winget et Scoop via une tâche planifiée dans le contexte de l'utilisateur (winget fonctionne mal sous SSH / SYSTEM) (BLOCKED: needs a real PC; design = update runs in scheduled task fleet-agent-update)
- [x] `fleet-bootstrap.ps1` : OpenSSH Server (capability + service auto) ; pare-feu port 22 limité à 100.64.0.0/10 ; `administrators_authorized_keys` avec commande imposée et ACL Administrators + SYSTEM uniquement ; source Event Log `fleet-agent` ; tâches planifiées (exécution détachée + pull) ; vérification de winget
- [x] `fleet-agent.ps1` : mêmes 5 verbes et même JSON ; MAJ dans l'ordre : Windows Update (API COM `Microsoft.Update.Session`), `winget upgrade --all`, Scoop (`scoop update`, `scoop update --all`, `--global` si présent), WSL (`wsl --update`, puis chaque distribution de `wsl -l -q` : `sysup` si présent sinon gestionnaire de paquets en root ; jamais `wsl --shutdown` si session active), Defender (`Update-MpSignature`) ; pas de Chocolatey
- [x] Vérifications préalables Windows : `on_battery`, `metered_network`, `user_active` ; délai 120 min
- [x] macOS : agent Unix validé (Remote Login, sudoers limité à `/sbin/shutdown -r now` pour le verbe `reboot` (§10, revue par Jérôme), `sysup`, vérification que les MAJ automatiques macOS sont actives ; macOS système jamais installé par l'agent sur Apple Silicon)
- [x] Mode pull : timer systemd (portables Linux), launchd (macOS), tâche planifiée (Windows) ; déclenche `update` si dernière MAJ > 7 jours, notifie ntfy priorité 2 ; jamais de redémarrage ; jamais sur `critical` ni guardians

## Acceptance Criteria

- [ ] PSScriptAnalyzer sans erreur (BLOCKED: pwsh absent; the executor's PowerShell container run was denied by the auto-mode permission check and was not retried; run on a Windows PC or with user approval)
- [x] Commande hors liste blanche sur Windows ⇒ refus + Event Log (verified statically, live Event Log BLOCKED)
- [ ] `check` + `update` réels sur un PC Windows et un Mac (BLOCKED: live Windows PC and Mac)
- [ ] Un poste rallumé après > 7 jours se met à jour et notifie seul (BLOCKED live; simulated by test_fleet_pull.py)
- [x] Aucun redémarrage déclenché en mode pull

## Verification

- [ ] `pwsh -c "Invoke-ScriptAnalyzer -Path dot_local/share/fleet/agent -Recurse"` (si pwsh disponible, sinon sur le PC Windows) (BLOCKED: pwsh absent)
- [x] `python3 -m pytest scripts/test_fleet_windows_contract.py`
- [ ] `plutil -lint` sur le plist généré (sur un Mac) (BLOCKED: no Mac; plistlib parse OK)

## Context

Windows et macOS sont des postes de travail, mis à jour ponctuellement et souvent
à la main ; le support est voulu mais secondaire. macOS : option A — MAJ système
par les MAJ automatiques natives, l'agent ne lance que `sysup` (brew, mas, outils IA)
et vérifie/signale. Apple Silicon exige le mot de passe du propriétaire du volume
pour installer macOS : non automatisé volontairement.

## Agent Notes (filled during execution)

- Assigned to: sprint-executor (sonnet, worktree, branch `sprint/05-postes`), 3 fix branches (`fix/fleet-sprint5-review`, `fix/fleet-sprint5-review2`, `fix/fleet-sprint5-lockfile`); orchestrator (opus) for reviews and merges
- Started: 2026-10-31
- Completed: 2026-10-31 (local part); merges 0304e8d7 and 59470356 on feat/fleet-plan. Live items BLOCKED.
- Decisions made:
  - Pull mode is a local-only entry, never a 6th SSH verb. Unix: `FLEET_AGENT_PULL=1` handled in `main()`, refused if `SSH_CONNECTION`/`SSH_ORIGINAL_COMMAND` set or arguments given; Windows: `-RunPull`/`-RunJob` switches the forced command never passes, also refused under SSH. Pull reaches only `update`; tests assert no reboot path.
  - Pull rules: opt-in marker `pull-enabled`; denied by `no-pull` marker, non-empty `critical-services`, kind guardian / name *guardian*, appliance kinds; update only if `last-success` > 7 days (strict digits, future = stale); `last-attempt` stamped before launch, 24 h backoff after a non-successful attempt; ntfy priority 2, token via curl config on stdin (https only, or exact http://127.0.0.1 / http://localhost); exit 0 on busy.
  - Pull job hard timeout: `systemd-run -p RuntimeMaxSec=7200` (Linux), `set -m` watchdog killing the whole process group (macOS bash 3.2); TERM trap writes `failed`/`timeout` (status `timeout` is master-only in schema.py).
  - launchd plist: AbandonProcessGroup, ProcessType Background, LowPriorityIO; user unit Nice=19, IOSchedulingClass=idle; headless Linux needs `loginctl enable-linger`.
  - Windows agent: 5 verbs, same JSON v1 (`ConvertTo-Json -Depth 8 -Compress`), update in scheduled task `fleet-agent-update` (interactive user, highest, 120 min, process tree killed with taskkill /T on timeout), order WU (COM) > winget (table parsed before `--all`, one change per package) > Scoop > WSL (`wsl --update` only with no running distro) > Defender; skipped when nobody is logged on. Restart: `/t 30` with message, exit code checked.
  - Security fixes requested by the coordinator's automated security review: (1) bootstrap agent dir: refuse pre-existing dir not owned by Administrators/SYSTEM or any reparse point (dir, ancestors, children), SetOwner(Administrators), inheritance off, Administrators+SYSTEM only, recursive; Assert-AclAdminOnly checks owner + reparse points. (2) firewall TCP 22 from 100.64.0.0/10 AND `-InterfaceAlias Tailscale` (fails without the adapter), stock OpenSSH rule disabled and sshd kept stopped until hardened; sshd_config hardened idempotently (timestamped backup, PasswordAuthentication no, KbdInteractiveAuthentication no, AllowUsers <SshUser>, directives before the first Match, `sshd -t` before restart, backup restored on failure). (3) the stale-lock takeover no longer uses a `Global\` named mutex (squattable by any local user, DoS): it uses `update.lock.takeover` inside the admin-only state dir opened with FileShare None, bounded retry, disposed in finally, UnauthorizedAccessException logged. Static tests cover all three.
  - Bootstrap requires `-SshUser`; TaskUser and SshUser must be direct local Administrators (SID comparison, ADSI fallback).
  - fleet.yml: comments only for the Windows/macOS workstations; no `ssh_user` set, so `fleet` does not contact them yet.
- Assumptions:
  - Windows OpenSSH sets `SSH_ORIGINAL_COMMAND`, honours `restrict`, and parses `\"` inside `command="..."` (reviewer confirmed for OpenSSH's parser; unverified on Win32-OpenSSH live).
  - `quser` parsing for user_active / no session is language-independent but fragile; winget table parser and sshd_config editor have static coverage only.
  - Domain-group admin membership is not resolved (direct SID membership only). `AllowUsers` locks out every other SSH account (documented).
- Issues found:
  - Review: 3 sonnet reviewers (Windows, pull mode, tests/docs) then 1 re-review; 2 HIGH (pre-created agent dir privilege escalation; launchd killing the detached update) and ~20 MEDIUM fixed over 2 rounds plus the coordinator's 3 security findings. Deferred: ntfy url `https://ntfy.sh` in fleet.yml (pre-existing since Sprint 2, reviewer flags a real public server as placeholder: user decision); domain-group admin resolution.
  - Verification on a git-archive export of 59470356: 560 tests pass, shellcheck 0 on fleet-agent.sh, bash -n 0, 8/8 invariants 0, plist renders empty on Linux (darwin gate) and parses with plistlib when the gate is forced, `systemd-analyze --user verify` only reports the not-installed /usr/local/libexec/fleet-agent.
  - BLOCKED (live infra / tooling): winget+Scoop scheduled-task validation on a real PC; real `check`+`update` on a Windows PC and a Mac; real pull after > 7 days; live Event Log refusal; PSScriptAnalyzer (pwsh absent here; the executor's container attempt was denied by the permission check and not retried); `plutil -lint` (no Mac).
  - Main checkout: the external formatter reflowed 23 .py files twice (AST-identical); stashed before each merge.
