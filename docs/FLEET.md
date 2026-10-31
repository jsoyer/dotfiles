# Fleet Updates (`fleet`)

Update every machine of the tailnet from one command, by phases, with a canary,
holds, reports and ntfy notifications. Source of truth: the code in
`dot_local/bin/executable_fleet` (wrapper), `dot_local/share/fleet/lib/*.py`
(orchestrator, bootstrap, API clients), `dot_local/share/fleet/agent/fleet-agent.sh`
(agent) and `dot_local/share/fleet/fleet.yml` (inventory). Spec and sprint notes:
`docs/tasks/infra/feature/2026-10-27_2109-fleet-updates/`.

Status of this document: v1 covers Linux hosts and appliances (OMV, PiKVM, Proxmox,
OPNsense, Home Assistant, guardians). macOS and Windows agents are **Sprint 5**: those
hosts are in `fleet.yml` but have no `ssh_user`, so they report `unsupported`.

## Architecture in one minute

- Two **masters** (`diabolo`, `penelope`) run the orchestrator. Any other machine is a
  **console**: it hands the command over to a master by SSH (the master of the
  targets' site first, then the other one).
- Each target runs a **forced-command agent** (`/usr/local/libexec/fleet-agent`,
  `root:root 0755`). The masters' SSH key is restricted: `restrict,command="..."`.
  The agent accepts exactly five verbs (see below), nothing else.
- Hosts without an agent (OPNsense, Home Assistant) are driven through their HTTP API
  by the master (tailnet only, credentials read from 1Password at run time).
- `fleet.yml` lists the hosts; it is validated on every run (a bad value rejects the
  whole file).

## Prerequisites

Everywhere: Tailscale up, `python3` (3.9+ is enough, stdlib only), `ssh`, `bash`.
On masters additionally: `tailscale` CLI, `rsync` (state sync to the other master),
1Password CLI `op` (ntfy token, API credentials, public keys).

| Kind | Agent install | Prerequisites on the host |
|------|---------------|---------------------------|
| `chezmoi-linux` | chezmoi (`run_onchange_install-fleet-agent`) | passwordless sudo for the `sysup` commands (`/etc/sudoers.d/sysup`, `run_always_install-sudoers-sysup`), `~/.local/bin/sysup`, `op` signed in at apply time so the master keys are written |
| `proxmox` (`multibox`) | chezmoi, same as above | same; agent detects `pveversion`; `critical: true` |
| `guardian` | chezmoi, same as above | same; updated only if the rest of its site is healthy |
| `omv` | `fleet bootstrap HOST --user U --apply` | first bootstrap needs root or NOPASSWD sudo; `omv-upgrade` present |
| `pikvm` | `fleet bootstrap HOST --user U --apply` | root or NOPASSWD sudo for the first bootstrap; `rw`, `ro`, `pikvm-update`; cloudflared at `/usr/local/bin/cloudflared` (optional) |
| `opnsense` | none (API only) | dedicated API user (see checklist), `critical: true` |
| `homeassistant` | none (API only) | dedicated non-owner user + long-lived token |
| `chezmoi-macos` | Sprint 5 | not supported yet (`unsupported`) |
| `windows` | Sprint 5 | not supported yet (`unsupported`) |

Allowed `site` values: `dijon nice garage cloud mobile`. `critical` must be `true` if
and only if the kind is `opnsense` or `proxmox` (the validator enforces it).

## Installation

1. `chezmoi apply` on every master and Linux target. It installs `fleet`
   (`~/.local/bin/fleet`), the library (`~/.local/share/fleet/`), the user timer
   `fleet-reminder.timer` (`dot_config/systemd/user/`) and, on Linux with sudo,
   the agent (see below). The `fup` alias (`fup='fleet up'`) comes with the shell
   config.
2. Create the 1Password item (see the checklist) so the install script can write the
   masters' public keys into `~/.ssh/authorized_keys` of every Linux target.
3. For OMV and PiKVM, bootstrap by hand (dry run first):

   ```bash
   fleet bootstrap omv-dijon --user admin            # dry run: renders and validates only
   fleet bootstrap omv-dijon --user admin --apply    # shows everything, asks to type the host alias
   ```

   Then set `ssh_user:` for that host in `fleet.yml` and run `fleet check omv-dijon`.
4. Generate a dedicated ed25519 key per master, store the **public** halves in
   1Password and point `FLEET_SSH_IDENTITY` at the private key on the master if the
   default ssh config/agent does not pick it.

### What the chezmoi script does (Linux)

`.chezmoiscripts/03-configure/run_onchange_install-fleet-agent.sh.tmpl`: installs the
agent root-owned, enables lingering, and rewrites the `fleet-master-*` lines of
`~/.ssh/authorized_keys`. See `docs/CHEZMOISCRIPTS.md`. It never fails `chezmoi apply`
(exit 0 everywhere) but is **not retried** after a deferral (see limitations).

## Commands

```
fleet ping   [host[,host]...]
fleet check  [host[,host]...]
fleet up     [HOST ...] [-l SELECTOR] [--dry-run] [--critical] [--no-canary]
fleet reboot --pending [HOST ...] [-l SELECTOR] [--critical] [--dry-run]
fleet report [--last | --run ID]
fleet logs   [HOST ...] [-l SELECTOR] [--run ID]
fleet changes HOST [--since DATE]
fleet hold   HOST ... --reason TEXT --until DATE
fleet unhold HOST ...
fleet holds
fleet reminder
fleet bootstrap HOST --user U [--apply] [--path NAME=/abs/path]
fleet help | -h | --help
```

A host argument that is unknown is an error (exit 2), never "everything".
Targets are handled one after the other for `ping`/`check`.

| Command | What it does |
|---------|--------------|
| `ping [hosts]` | Local to the wrapper, not an agent verb. Tailscale state, then an SSH connection is opened **without authenticating** (host key verified), so the agent is never invoked. Prints `offline`, `unreachable` or `ok`. Exit 1 if any host is unreachable. Takes plain aliases (comma lists), **not** selectors. |
| `check [hosts]` | Calls the agent verb `check` (read-only: pending packages, health, reboot state). Prints `packages=N reboot=yes/no (reason)`. Hosts without `ssh_user` print `unsupported`. Exit 1 on `failed`, `degraded`, `unreachable`. Plain aliases only. |
| `up` | Update by phases (below). No target = the whole fleet minus the other master. |
| `reboot --pending` | Restarts only hosts reporting a pending reboot, **one at a time, one confirmation each**. `--pending` is mandatory (without it: exit 2). Waits 15 min (30 for critical hosts) for the host to come back. Skips the current master (restart it by hand), critical hosts without `--critical`, and API hosts. |
| `report` | No option: lists the last 20 runs. `--last`: renders the latest run. `--run ID`: renders a given run. |
| `logs [hosts]` | Raw log of a host from the latest run that has one (or `--run ID`). A target is required. |
| `changes HOST` | Package changes of a host across runs; `--since YYYY-MM-DD|ISO8601`. |
| `hold HOST... --reason R --until D` | Skip these hosts (status `held`) until the date. Both options mandatory; date is `YYYY-MM-DD` or ISO8601. Synced to the other master; a failed sync prints a warning and exits 1. |
| `unhold HOST...` | Lift a hold. |
| `holds` | List active holds. |
| `reminder` | ntfy reminder if no `fleet up` ran for 14 days (reads history only, opens no connection). Masters only. Run daily by `fleet-reminder.timer`. |
| `bootstrap HOST` | Install the agent on an `omv` or `pikvm` host outside chezmoi. See below. |

### `up` details

- Options: `-l/--label SELECTOR` (repeatable), positional `HOST...` (same syntax as
  selectors), `--dry-run` (prints the plan: no lock, no `op read`, no connection),
  `--critical` (also update critical hosts, with a warning + confirmation each),
  `--no-canary` (do not run canaries first and do not block on a failed canary).
- Phases: **1** `chezmoi-linux chezmoi-macos omv pikvm windows` in parallel (global
  cap `parallel.total` = 10, per site `parallel.per_site` = 4); **2** Home Assistant,
  guardians and hosts tagged `infra`/`site-router`, serially; **3** the ntfy gateway
  (`ntfy.gateway`, `bbh-network`) alone. Then **critical** hosts (OPNsense first, then
  the hypervisor) only with `--critical` and a typed `y`; the **current master** is
  always last, updated locally.
- Canary: hosts with `canary: true` run first inside a stage. If a canary ends
  `failed`, `degraded` or `timeout`, the other hosts of the same kind are `skipped`
  ("canary failed for kind ...").
- A guardian is skipped (`site degraded`) unless at least one other non-guardian host
  of its site is reachable.
- Updates are detached on the target; the master polls with the `report` verb until
  the per-kind timeout (`timeouts:` in `fleet.yml`, host override `timeout_min`).
- Exit codes: 0 all good, 1 if any host is `failed`/`degraded`/`unreachable`/`timeout`,
  2 usage/selector/inventory error, 3 another run in progress (a lock per master).
- Notifications: one summary per run (ntfy priority 2, or 4 if something failed),
  a "refused" alert when an agent refused a call (5), "stale" when a host has had no
  success for more than 30 days (4).

### Console vs master

On a machine that is not a master, `up`, `reboot`, `report`, `logs`, `changes`, holds
and `reminder` are re-run on a master with `ssh -t` (the master of the first target's
site per `master_priority`, e.g. `nice` -> `penelope`; otherwise `diabolo`, failing
over to the other). `--dry-run` on a console prints the plan locally. If no master
answers: `fleet: no master reachable`, exit 1. `ping` and `check` run from wherever
you are.

### `bootstrap` details

`fleet bootstrap HOST --user U [--apply] [--path NAME=/abs/path]`

- `--user` (required): the account on the target that runs the agent.
- `--apply`: apply after review and an explicit confirmation (type the host alias on a
  terminal; no terminal = declined). Default is a **dry run**.
- `--path NAME=/abs/path` (repeatable): use this absolute path for a program instead of
  `command -v` on the target.
- Only `omv` and `pikvm` kinds. Pins the target ed25519 host key (fingerprint shown),
  resolves tool paths with a fixed `PATH`, requires every resolved path and parent to
  be root-owned and not group/other-writable, renders and `visudo -cf`-validates the
  sudoers fragment, then stages and verifies sha256 on the target before renaming.
  Installs `/usr/local/libexec/fleet-agent`, `/etc/sudoers.d/fleet-agent`, the
  `authorized_keys` lines. PiKVM: applied inside one `rw` window, `ro` restored by a trap.
- Closed sudo lists: `omv`: `omv-upgrade`, `systemctl reboot`. `pikvm`: `rw`, `ro`,
  `pikvm-update`, `/usr/local/bin/cloudflared update`,
  `systemctl restart cloudflared`, `systemctl reboot`.
- Refuses when a public key is missing from 1Password, or the fragment is invalid.

## Selectors

Used by `-l` and by positional hosts of `up`, `reboot`, `logs`, `hold`, `unhold`.

| Syntax | Meaning |
|--------|---------|
| `alias` | One host |
| `site=<site>` | `dijon nice garage cloud mobile` |
| `kind=<kind>` | `chezmoi-linux chezmoi-macos omv pikvm homeassistant opnsense proxmox windows guardian` |
| `tag:<tag>` | A tag of `fleet.yml` (`infra`, `site-router`) |
| `@<group>` | A group of `fleet.yml` (`masters nas homeassistant guardians macs`) |
| `a,b` or several tokens | Union |
| `!x` | Exclusion, applied after the union |

An unknown term is an error even inside a union; a selector matching nothing is an
error (exit 2) and never falls back to the whole fleet. `!x` alone is also an error:
write `site=dijon,!x`. Example: `fleet up -l 'kind=omv,!omv-garage' --dry-run`.

## Statuses

Decided by an agent: `started` (detached update launched, job id returned), `running`
(an update is in progress), `updated` (packages were upgraded), `up-to-date` (nothing
pending), `degraded` (updated but health got worse: new failed unit, new unhealthy
container, critical service down, `/` under 10 percent free; also an API host whose
final check failed), `failed` (update or check failed, invalid or refused agent
answer), `busy` (another update holds the lock, agent exit 3), `skipped` (deliberately
not done: canary failed for the kind, guardian site degraded, no reboot pending, critical without
`--critical`, declined confirmation), `unsupported` (no package manager, or no agent
for this kind yet).

Decided by the master only: `offline` (Tailscale says the peer is down, no connection
tried), `unreachable` (peer online but SSH fails, no answer, or not in `tailscale
status`), `timeout` (job not finished within the kind timeout, or the host did not come
back after a reboot), `held` (active hold).

Counted OK: `updated`, `up-to-date`. Counted bad (exit 1): `failed`, `degraded`,
`unreachable`, `timeout`.

## Agent

The agent is reached only through the forced command. Verbs (exactly one, no argument;
anything else exits 1 with `fleet-agent: refused` and is logged):

| Verb | Effect |
|------|--------|
| `check` | Read-only: pending packages, health, conflicts, reboot state. Proxmox: includes `vm:` lines when `qm list` is allowed. |
| `update` | Starts a detached update (`systemd-run --user`, `nohup` fallback) and returns `started` + job id. Kind-specific branches: OMV (`omv-upgrade`), PiKVM (`rw` window, `pikvm-update`, cloudflared with rollback), generic (`sysup`). |
| `reboot-status` | Is a reboot required (needs-restarting, `reboot-required`, newer kernel). |
| `reboot` | Reboots only if required (exact sudoers command). |
| `report` | Final or current state of the last update job, from disk. |

Output: one JSON line (schema v1). Exit codes: 0 success, 1 refused, 2 update failed,
3 busy. Critical services are read on the target from
`~/.config/fleet-agent/critical-services` (one unit name per line; `fleet.yml`
`critical_services` is **not** deployed there yet).

## Where things live

| What | Where |
|------|-------|
| Wrapper / library / inventory | `~/.local/bin/fleet`, `~/.local/share/fleet/` (`FLEET_DIR`, `FLEET_YML`) |
| Master state | `~/.local/state/fleet/` (`FLEET_STATE_DIR`, `XDG_STATE_HOME`), 0600/0700: `runs/<id>/{report.json,report.md,run.log,raw/}`, `history-<master>.jsonl` (31 days), `last-success-<master>.json` (never purged), `holds-<master>.json`, `ntfy-queue/` |
| Run id | `YYYYMMDDTHHMMZ-<master>` |
| Agent on target | `/usr/local/libexec/fleet-agent`; state `~/.local/state/fleet-agent/` (jobs, lock, `cloudflared.old`); logs in journald (`fleet-agent` tag), `/var/log/fleet-agent.log` on macOS |
| Sudoers | `/etc/sudoers.d/sysup` (chezmoi, Linux), `/etc/sudoers.d/fleet-agent` (bootstrap, OMV/PiKVM) |
| Timer | `~/.config/systemd/user/fleet-reminder.{service,timer}`; optional env file `~/.config/fleet/env` |

Each master writes only its own `*-<master>` files and syncs them to the other by
rsync (`FLEET_SYNC=0` disables); the other master's copies are merged at read time.

Environment variables: `FLEET_DIR`, `FLEET_YML`, `FLEET_PYTHON`, `FLEET_SSH`,
`FLEET_SSH_IDENTITY`, `FLEET_STATE_DIR`, `FLEET_MASTER`, `FLEET_HOSTNAME`,
`FLEET_SYNC`, `FLEET_RSYNC`, `FLEET_LOCAL_AGENT`, `FLEET_OP`, `FLEET_NTFY_TOKEN`
(overrides the 1Password reference), `FLEET_VISUDO`, `FLEET_KNOWN_HOSTS`.

## Notifications (ntfy)

Configured in `fleet.yml` (`ntfy: {url, topic, token_ref, gateway}`). The token is
read at run time from `FLEET_NTFY_TOKEN` or `op read <token_ref>`, sent only in the
`Authorization` header and only over https (or loopback). Messages are masked, at most
20 lines, never a raw log. Undelivered messages are queued under `ntfy-queue/` and
resent in order. Events: run summary, host stale over 30 days, reboot not back,
command refused by an agent, 14-day reminder (`fleet reminder`).
`--dry-run` never reads the token.

## Key revocation

Public keys come from the 1Password item (`op://Private/Fleet/public-key-<master>`);
the key marker is the comment `fleet-master-<master>` on each `authorized_keys` line.

1. Compromised master key: generate a new key pair on the master, replace the field
   `public-key-<master>` in 1Password.
2. Re-apply on every target: Linux `chezmoi state delete-bucket --bucket=scriptState
   && chezmoi apply` (the install script is `run_onchange`; touching the agent or
   forcing it rewrites the lines), OMV/PiKVM `fleet bootstrap HOST --user U --apply`
   (it drops the old `fleet-master-<master>` line first).
3. Retiring a master completely: remove it from `MASTERS` in the install script (and
   `masters:` in `fleet.yml`); the next run deletes its line from `authorized_keys`.
4. Emergency without waiting: on each target delete the line ending in
   ` fleet-master-<master>` from `~/.ssh/authorized_keys`.
5. Also revoke the ntfy token, API keys and Home Assistant tokens if the master was
   compromised: the masters hold them (accepted risk).

## Manual procedure (fleet unavailable)

On each host, as the normal user: `sysup` (Linux/macOS; `sysup --reboot` on Fedora
desktop/server stages the dnf upgrade offline). OMV: `sudo omv-upgrade`. PiKVM:
`rw; pikvm-update; ro` and, if installed, update cloudflared and restart it, checking
the tunnel. OPNsense: System > Firmware in the web UI (minor updates; check the
release notes before a major). Home Assistant: Settings > System > Updates (take a
backup first, update Core, then OS). Proxmox: `sysup` (apt `dist-upgrade`) after
checking running VMs. Then check `needs-restarting -r` / `/var/run/reboot-required` and
reboot when convenient. Record it with `fleet hold` on skipped hosts if needed.

## Manual actions for Jerome

Nothing below has been done by the code.

- [ ] 1Password: create the item **`Fleet` in the vault `Private`** (the code reads
      `op://Private/Fleet/...`; not a vault named Fleet). Fields:
      `public-key-diabolo`, `public-key-penelope` (ssh-ed25519 public keys),
      `ntfy-token`, `opnsense-api-key`, `opnsense-api-secret`,
      `ha-dijon-token`, `ha-nice-token`, `ha-garage-token`.
- [ ] 1Password service account (or desktop integration) usable by `op` on both masters,
      non-interactively (timer and `fleet up`).
- [ ] Generate the two master ed25519 key pairs and set `FLEET_SSH_IDENTITY` on the masters.
- [ ] ntfy: confirm the server address of `bbh-network` and replace the placeholder
      `ntfy.url` (`https://ntfy.sh`), create the topic `fleet` and an access token.
- [ ] OPNsense: create user `fleet` with the single privilege **System: Firmware**,
      generate an API key/secret.
- [ ] Home Assistant (x3): dedicated non-owner user + long-lived token.
- [ ] Replace the placeholder `*.example-tailnet.ts.net` API URLs in `fleet.yml`
      (`api:` section) with the real tailnet names.
- [ ] Review and apply the Tailscale ACL draft
      `docs/tasks/infra/feature/2026-10-27_2109-fleet-updates/tailscale-acl.hujson`.
- [ ] Review the sudoers fragments before applying them: the `fleet-agent` reboot line
      in `run_always_install-sudoers-sysup.sh.tmpl` (applied by the next `chezmoi apply`),
      and the fragments `fleet bootstrap` prints for OMV/PiKVM.
- [ ] Deploy the critical-services list: create `~/.config/fleet-agent/critical-services`
      on each target (nothing deploys it from `fleet.yml` yet; PiKVM wants `kvmd`, `cloudflared`).
- [ ] Bootstrap OMV (x3) and PiKVM, then set their `ssh_user` in `fleet.yml`.
- [ ] Enable the reminder timer: `systemctl --user enable --now fleet-reminder.timer`
      (and `~/.config/fleet/env` if the token is not read through `op`).
- [ ] First live runs: `fleet ping`, `fleet check <canary>`, `fleet up --dry-run`,
      then `fleet up -l <canary>`.

## Known limitations / open decisions

- `fleet check` prints `unsupported` for API hosts (OPNsense, Home Assistant): the
  wrapper only calls the SSH agent; the API `check` and privilege verification exist in
  `lib/api_*.py` but have no CLI verb. `fleet up` does handle them.
- API URLs in `fleet.yml` are placeholders (`example-tailnet.ts.net`) and must be replaced.
- API URL policy: `https://<name>.ts.net`, or a literal tailnet IP in
  `100.64.0.0/10` (http or https). Anything else is refused. No redirects.
- Sudoers fragments are **not applied**; they await Jerome's review. Commands without
  arguments are rendered with an explicit `""` argument so sudo refuses any argument;
  the fragment grants the canonical (`readlink -f`) path.
- cloudflared rollback is automatic only when the agent runs as root (PiKVM default):
  the closed sudo list has no command to write `/usr/local/bin`. Otherwise
  "restore by hand" with the copy in `~/.local/state/fleet-agent/cloudflared.old`.
- `qm list` as a non-root user usually fails, so the Proxmox `--critical` warning is
  the generic "VM list unavailable: assume every VM/service behind it is interrupted".
  A real list needs an agent verb (not planned) or stays generic.
- Master-to-master `rsync` needs a dedicated key (the agent's forced command refuses
  rsync); until then the sync fails and is logged, retried by the next run.
- `ntfy.url` is a placeholder; the reminder timer is not enabled by default.
- OPNsense: pending updates are treated as `minor` even when the box is in the
  `upgrade` state, to be confirmed on the real box (firmware endpoints are named
  constants). Major releases are never applied. Home Assistant Core failure is
  reported `failed` (not `degraded`) and blocks the OS update.
- `run_onchange_install-fleet-agent` is not retried after a deferred `exit 0` (sudo
  needs a password, `op` missing...). Replay with
  `chezmoi state delete-bucket --bucket=scriptState && chezmoi apply` (replays other
  one-shot scripts too).
- Masking limits: `basic`/`bearer` prose can be over-masked, `user@host` with dotted
  users is over-masked, and the ntfy queue is unbounded.
- Port 22 is open to the whole tailnet until the ACL is applied (accepted risk,
  2026-10-27); API tokens live on the masters, outside the forced command (accepted risk).
- Sprint 5 pending: macOS and Windows agents.
- Correction to older notes: the 1Password item is `Fleet` in vault `Private`
  (not a vault named Fleet).
