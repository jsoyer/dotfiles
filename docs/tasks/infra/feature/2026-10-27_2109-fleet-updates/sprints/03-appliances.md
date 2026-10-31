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

- [x] **OMV** : `omv-upgrade` (pas `apt` direct), non interactif ; chemins absolus des commandes du fragment sudoers résolus par `command -v` au bootstrap
- [x] **PiKVM** : une seule fenêtre `rw` avec `trap` garantissant `ro` même en échec ; `pikvm-update` ; puis `cloudflared` (**binaire installé à la main**) : `cloudflared update`, redémarrage du service si la version change, ancienne version conservée et restaurée si le tunnel ne revient pas ; santé : `kvmd` actif + tunnel prêt (`/ready` des métriques locales) ; délai 20 min
- [x] **Proxmox (`multibox`)** : agent Unix, branche `proxmox` = `apt-get dist-upgrade` non interactif via `sysup` (dépôts Proxmox) ; `critical: true` ; `critical` (hors `fleet up` sans `--critical`) ; jamais de redémarrage automatique ; avertissement listant les VM avant confirmation
- [x] **OPNsense** (API, utilisateur `fleet`, droit unique « System: Firmware ») : `check` = `POST /api/core/firmware/check` + `GET /api/core/firmware/status` ; `update` = `POST /api/core/firmware/update` (pas de copie de `config.xml` sur le master : elle exigerait un droit au-delà de « System: Firmware » ; l'historique de configuration local d'OPNsense suffit, une MAJ firmware ne modifie pas la config) (mineures seulement), suivi `/api/core/firmware/upgradestatus`, attente du retour (ping + nœud tailnet + API) 15 min max ; **majeures OPNsense jamais appliquées** (`upgrade_major_version` ⇒ `major_available`) ; vérifier les endpoints exacts sur la version installée — implémenté et testé en simulation ; vérification sur l'infra réelle : BLOCKED (endpoints en constantes nommées)
- [x] **Home Assistant** (API, utilisateur dédié, jeton longue durée) : sauvegarde d'abord (échec ⇒ `skipped`), puis Core + add-ons + OS, **versions majeures incluses** ; la MAJ OS redémarre l'appareil : attente de l'API 15 min max, sinon ntfy priorité 5
- [x] `fleet bootstrap <host>` : installe agent, clé à commande imposée, `known_hosts` et le fragment sudoers du `kind` (liste fermée §10 : OMV `omv-upgrade` ; PiKVM `rw`, `ro`, `pikvm-update`, `cloudflared update`, `systemctl restart cloudflared` ; + `systemctl reboot`), validé par `visudo -cf` ; **Stop et revue par Jérôme** avant application (PiKVM : dans une fenêtre `rw`)
- [x] Jetons API lus depuis 1Password à l'exécution, jamais écrits sur disque ni affichés
- [x] Droits minimaux vérifiés : OPNsense, un appel hors « System: Firmware » (ex. `GET /api/core/system/status` hors privilège) ⇒ 403 ; HA, utilisateur dédié non propriétaire — implémenté et testé en simulation ; vérification sur l'infra réelle : BLOCKED (endpoints en constantes nommées)

## Acceptance Criteria

- [ ] `check` réel sur chaque type (OMV, PiKVM, OPNsense, HA, Proxmox) — BLOCKED (infra réelle) ; implémenté + test simulé
- [x] PiKVM revient en `ro` même si `pikvm-update` échoue (test simulé)
- [x] OPNsense : une montée majeure disponible est signalée (`major_available`) et non appliquée
- [x] HA : sauvegarde en échec (simulée) ⇒ aucune MAJ, statut `skipped` ; MAJ majeure HA appliquée après sauvegarde réussie
- [x] Utilisateurs API à droits minimaux (test 403 OPNsense, HA non propriétaire) — chemin de code + tests simulés ; vérification réelle BLOCKED (infra réelle)
- [x] `fleet up` sans `--critical` ne touche ni OPNsense ni `multibox`
- [x] Fragments sudoers OMV / PiKVM = liste fermée §10 exactement, `visudo -cf` OK
- [x] Aucun jeton dans `runs/`, journaux, notifications (`grep`)
- [ ] `update` réel sur un type à faible risque (OMV ou PiKVM) — BLOCKED (infra réelle) ; implémenté + test simulé

## Verification

- [x] `python3 -m pytest scripts/test_fleet_appliances.py`
- [x] `shellcheck dot_local/share/fleet/agent/fleet-agent.sh`

## Context

**OPNsense** route les VM du Proxmox (`multibox`, site de Dijon). Ses MAJ et celles
de `multibox` passent en dernier (`--critical`), OPNsense puis `multibox`.
Les masters ne sont pas derrière OPNsense.

**Risque accepté (2026-10-27) :** les jetons API OPNsense / HA détenus par les
masters échappent à la commande imposée. Atténuations : droits minimaux, jetons
dans 1Password (compte de service révocable), jamais en clair sur disque.

**Délais :** omv 30 min, pikvm 20 min, homeassistant 45 min, opnsense 30 min, proxmox 45 min.

## Agent Notes (filled during execution)

- Assigned to: sprint-executor (branch sprint/03-appliances, base 4db99a88)
- Started / Completed: 2026-10-31

### Decisions made
- **Proxmox VM list (no new verb):** the `proxmox` branch of `check` adds `vm: <id> <name> <status>` lines (best effort `qm list`, no sudo) to the existing `log_tail` field of the `check` JSON. `SshTransport.list_vms` calls `check`, parses `log_tail` (`orchestrate.vm_lines`) and the `--critical` warning lists the VMs. If `qm list` is not allowed for the SSH account (it usually needs root; the closed sudoers list has no `qm`) the list is empty and the warning falls back to the generic text. Verb whitelist unchanged.
- **API routing rule:** an API kind (`opnsense`, `homeassistant`) WITHOUT `ssh_user` goes through `lib/api_*.py`; with an `ssh_user` it keeps the agent path (existing tests/fakes unchanged). The orchestrator only builds an `ApiContext` and calls the `transport.api(alias, verb, ctx)` seam; all logic is in the new modules. API hosts have no reboot verb (`fleet reboot` skips them).
- **Shared plumbing lives in `api_opnsense.py`** (HTTP client, URL policy, `op` secrets, entry building through `schema.mask_data` + `schema.parse_agent_output`); `api_homeassistant.py` imports it (only 3 new lib files allowed by the boundary).
- **fleet.yml:** new top-level `api:` mapping (url + `op://` refs); no change to inventory.py (unknown top-level keys are ignored by the validator). The tailnet domain in the URLs is a placeholder (`example-tailnet.ts.net`, UNCERTAIN).
- **Agent kind detection** by shipped tool (`pveversion` / `omv-upgrade` / `pikvm-update`), `FLEET_AGENT_KIND` override is test-only (already dropped in an SSH context by the existing hardening).
- **Bootstrap confirmation flow:** default = dry run (scan host key, `command -v` on the target, render, `visudo -cf`, print everything, apply nothing). `--apply` shows the same output, then requires typing the host alias on a terminal (non-tty => declined, exit 1); an invalid fragment or missing master public key blocks apply. Files go to a remote `mktemp -d` via scp, then one `sh apply.sh` (sudo install for agent + fragment, re-validated by `visudo -cf` on the target, authorized_keys via temp+mv). The host key is pinned in known_hosts only after a successful apply. All ssh in bootstrap uses a scratch known_hosts holding the key shown to the operator.
- OPNsense: a minor update is applied only when `status != upgrade`; `upgrade_major_version` => `major_available` field, status `up-to-date`, `EP_FIRMWARE_UPGRADE` is a constant that is never called (tested). Waiting for return after a reboot: observe down (3 min grace) then ping + tailnet node + API, 15 min max; failure => `failed` + ntfy prio 5 (`notify.not_back_message`).
- HA: backup via `POST /api/hassio/backups/new/full`; no update call at all if it is not `ok`; order add-ons, Core, OS; connection loss during Core/OS update is tolerated and the API is polled until the new version is reported (15 min max).
- PiKVM: one `rw` window in a subshell with an EXIT trap running `ro` (also on rw failure and TERM/INT/HUP). `cloudflared update` exit 0 and 11 are accepted. Metrics URL defaults to `http://127.0.0.1:20241/ready` (UNCERTAIN, overridable).

### Assumptions
- 🟡 Supervisor endpoints under `/api/hassio/...` and the OPNsense firmware endpoints are correct for the installed versions (named constants; BLOCKED live).
- 🟡 `cloudflared` metrics listen on 127.0.0.1:20241.
- 🟡 PiKVM's SSH account is root or has the sudoers fragment; `ro`/`rw` live in PATH.

### Issues found / known limitations (flag for Jerome)
- **cloudflared rollback is only automatic when the agent account can write the binary (root on PiKVM).** With a non-root account the closed sudoers list (spec section 10) has no command to write `/usr/local/bin/cloudflared`; the agent keeps the old binary in its state dir (`cloudflared.old`) and reports `cloudflared_tunnel_down_restore_by_hand`. Adding a root restore command would be a dated section-14 decision (a user-writable source installed as root would be a privilege escalation).
- `fleet check` (bash wrapper) still prints `unsupported` for API hosts; `api_*.run("check")` exists and is tested but is not wired to a CLI verb (outside the file boundaries to do cleanly). `verify_privileges` is implemented and tested but also has no CLI verb.
- `qm list` as a non-root agent account usually fails: the VM list then falls back to the generic warning (decision recorded above; a sudoers `qm list` would be a section-14 decision).
- BLOCKED (live infra): real `check` on each type, real `update` on OMV/PiKVM, real 403 probe of OPNsense and HA non-owner check, endpoint verification.
- Chezmoi installer template embeds the agent sha, so `run_onchange_install-fleet-agent` will re-run on masters once (expected).
- `python3 -m pytest` invariants 5 and 7 need pytest; system python3 has none, they were run with `uvx pytest` instead.

### Boundary deviations
- None. Only declared files were created/modified (schema.py, notify.py, report.py, inventory.py untouched).

### Review fixes (fix/fleet-sprint3-review)
- **Superseded decision (OPNsense):** a minor update is now applied whenever `updates > 0` (even if a major is also available); `update` only POSTs `/api/core/firmware/update` (never `upgrade`) and the entry carries `major_available`. `up-to-date` is never reported while updates are pending. The follow of `upgradestatus` snapshots the status before the POST and trusts a terminal state only after the job was seen running or its log changed. A failing final status is retried within the deadline, then `degraded` + ntfy priority 5.
- **URL policy:** API hosts must be on the tailnet: https to a `*.ts.net` name, or a literal 100.64.0.0/10 IP (http or https). Every other host is refused (https to an arbitrary host is no longer accepted). `fleet.yml` placeholders already conform; only its comment changed.
- **Bootstrap:** remote `command -v` uses `PATH=REMOTE_PATH` only; each resolved path (and `--path` overrides, and `/usr/local/bin/cloudflared` on PiKVM) plus all parents must be root-owned and not group/other-writable (checked read-only on the target, strict parsing). The apply script stages agent and sudoers as root under dotted names (`.fleet-agent.new`), checks their sha256 against the locally computed values, runs `visudo -cf` on the root-owned copy, and only renames at the very end. grep exit >1 aborts. `sudo -n` throughout (first bootstrap needs root or NOPASSWD sudo). A different already-pinned host key is refused. The prompt and dry run show fingerprint, agent sha256 and the apply script. Remote temp dir must match `^/(var/)?tmp/[A-Za-z0-9._-]+$`. DECISION kept: `Defaults:<user> !requiretty` and the omv-upgrade `env_keep` (commented in code).
- **Agent:** cloudflared rollback copies to `$cf.new` then `mv -f` (no ETXTBSY); `cloudflared.old` is refreshed only when the tunnel was ready before the update; empty `systemctl` path aborts with exit 44 before any `as_root`.
- **Orchestrator:** Proxmox VM lines are filtered with `^vm: [0-9]{1,6} [A-Za-z0-9._-]{1,63} [a-z]{1,16}$`, capped at 50, and cleaned again in the warning.
- **Tests whose expectation changed:** `UrlPolicyTest.test_accepts_https_anywhere...` (encoded the insecure https-anywhere rule; replaced by tailnet-only tests); the PiKVM happy-path order now includes the pre-update `curl` health probe, and the tunnel-down rollback test now lets the first probe succeed (`STUB_CURL_OK_FIRST`), both because of the A3 rule; `bootstrap.apply_script` gained the two sha arguments.
- **Decision for Jerome:** literal tailnet IPs also accept https (certificate would need `ca_file`); say if you want https restricted to `*.ts.net` names only.
