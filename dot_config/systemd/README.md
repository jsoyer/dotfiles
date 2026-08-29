# Systemd User Services & Timers

Auto-update and daemon services managed by systemd (Linux only).

**Last Updated:** 2026-03-28
**Location:** `~/.config/systemd/user/`
**Status Command:** `systemctl --user list-timers`

---

## Services

### `chezmoi-autoupdate.service`

**Purpose:** Central daemon for automatic dotfile updates, auto-healing, and notifications.

**What It Does:**
1. Syncs from remote (`git pull --rebase`)
2. Applies configuration (`chezmoi apply`)
3. Auto-heals common issues (conflicts, stale caches, permissions)
4. Validates post-apply (shell/starship/tmux startup)
5. Auto-rollbacks if validation fails
6. Sends notifications (desktop, webhooks) on errors
7. Logs status to `~/.cache/chezmoi-autoupdate/`
8. Posts heartbeat to fleet monitoring system

**Runs on:**
- Linux desktop (fedora-desktop, ubuntu-desktop, arch-desktop, omarchy)
- Linux server (fedora-server, ubuntu-server, debian)
- Fedora Atomic (fedora-atomic)
- Toolbox containers (toolbox)
- **Not on:** RPi, Windows, macOS (uses launchd instead)

**Trigger:** `chezmoi-autoupdate.timer` (every 1 hour)

**Manual Execution:**
```bash
systemctl --user start chezmoi-autoupdate.service
# or
chezmoi-autoupdate
```

---

## Timers

### `chezmoi-autoupdate.timer`

**Purpose:** Scheduler for auto-update daemon (every 1 hour).

**Schedule:** `OnBootSec=5min OnUnitActiveSec=1h`
- Runs 5 minutes after system boot
- Repeats every 1 hour thereafter
- Randomized ±10 minutes to avoid thundering herd

**Status:**
```bash
systemctl --user status chezmoi-autoupdate.timer
systemctl --user list-timers chezmoi-autoupdate.timer
```

**View Next Run:**
```bash
systemctl --user list-timers --all | grep chezmoi
```

**Manual Trigger (bypass timer):**
```bash
systemctl --user start chezmoi-autoupdate.service
```

---

## Management Commands

### Enable/Disable

**Enable permanently** (runs on login):
```bash
systemctl --user enable chezmoi-autoupdate.timer
systemctl --user enable chezmoi-autoupdate.service
```

**Disable permanently:**
```bash
systemctl --user disable chezmoi-autoupdate.timer
systemctl --user disable chezmoi-autoupdate.service
```

**Temporarily stop** (until reboot):
```bash
systemctl --user stop chezmoi-autoupdate.timer
systemctl --user stop chezmoi-autoupdate.service
```

### Logging & Debugging

**View service logs** (last 50 lines, follow in real-time):
```bash
journalctl --user -u chezmoi-autoupdate -n 50 -f
```

**View timer logs:**
```bash
journalctl --user -u chezmoi-autoupdate.timer
```

**View full journal for today:**
```bash
journalctl --user -u chezmoi-autoupdate --since today
```

**View with timestamps:**
```bash
journalctl --user -u chezmoi-autoupdate -o short-iso
```

### Status

**Check if timer is active:**
```bash
systemctl --user is-active chezmoi-autoupdate.timer
```

**Check if enabled on login:**
```bash
systemctl --user is-enabled chezmoi-autoupdate.timer
```

**View next scheduled run:**
```bash
systemctl --user list-timers chezmoi-autoupdate.timer
```

**View detailed status:**
```bash
systemctl --user status chezmoi-autoupdate.service
systemctl --user status chezmoi-autoupdate.timer
```

---

## Auto-Update Output

### Status Cache

After each run, the service writes to `~/.cache/chezmoi-autoupdate/`:

| File | Content | Usage |
|------|---------|-------|
| `status.json` | Last run metadata (timestamp, duration, exit code) | `cmstatus` alias |
| `last-run.log` | Full execution output and errors | `cmlog` alias |
| `last-seen-commit` | Previous commit hash (for changelog) | `cmchangelog` alias |

**Query status:**
```bash
cmstatus                          # Pretty-print status JSON
cmlog                             # View last execution log
cmchangelog                       # Show updates since last check
```

---

## Monitoring & Alerts

### Desktop Notifications

On error, sends desktop notification via `notify-send`:
```bash
notify-send "Chezmoi Auto-Update" "Last update failed. See cmlog for details."
```

### Webhook Notifications

Errors also trigger webhooks (if configured in `secrets.zsh`):
- **ntfy.sh**: POST to topic (all outcomes for fleet tracking)
- **Telegram**: API sendMessage to chat
- **Discord**: Webhook POST to channel

**Configure in `~/.zsh/secrets.zsh`:**
```bash
export NTFY_TOPIC="chezmoi-fleet-myname"
export TELEGRAM_BOT_TOKEN="xxx"
export TELEGRAM_CHAT_ID="xxx"
export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..."
```

### Starship Integration

Custom module in starship prompt:
- **Red ✗** if last update failed
- **Silent** if healthy

---

## Troubleshooting

### Timer Not Running

**Check if enabled:**
```bash
systemctl --user is-enabled chezmoi-autoupdate.timer
# Should output: enabled
```

**Check if active:**
```bash
systemctl --user is-active chezmoi-autoupdate.timer
# Should output: active
```

**If inactive, start it:**
```bash
systemctl --user start chezmoi-autoupdate.timer
```

**View next run:**
```bash
systemctl --user list-timers chezmoi-autoupdate.timer
```

### Service Fails

**View error:**
```bash
journalctl --user -u chezmoi-autoupdate -n 20
```

**Common errors:**
- **"chezmoi: not found"** — chezmoi not in PATH
- **"git: not found"** — git not installed
- **"Permission denied"** — systemd timer running as wrong user

**Test manually:**
```bash
chezmoi-autoupdate --dry-run
# See what would happen without applying
```

### High CPU / Disk I/O

**Check if service is still running:**
```bash
systemctl --user status chezmoi-autoupdate.service
```

**If stuck, restart:**
```bash
systemctl --user restart chezmoi-autoupdate.service
```

**Check recent logs for hang point:**
```bash
journalctl --user -u chezmoi-autoupdate -n 100 | tail -20
```

### Notifications Not Showing

**Verify desktop notification works:**
```bash
notify-send "Test" "Desktop notification test"
```

**Check webhook variables:**
```bash
echo $DISCORD_WEBHOOK_URL
echo $TELEGRAM_BOT_TOKEN
```

**Test curl to ntfy.sh:**
```bash
curl -d "test" https://ntfy.sh/test-topic
```

---

## Performance

### Timer Jitter

Timers include randomization (±10 minutes) to avoid system load spikes when multiple machines update simultaneously.

**Set custom jitter:**
Edit service file and change `RandomizedDelaySec`:
```bash
systemctl --user edit chezmoi-autoupdate.timer
```

### Resource Limits

If chezmoi-autoupdate consumes too much resources, add limits to the service:

```bash
systemctl --user edit chezmoi-autoupdate.service
```

Add under `[Service]`:
```ini
MemoryLimit=256M
CPUQuota=50%
```

---

## Self-hosted Agent Units

These units are deployed by chezmoi but **never enabled automatically**. The
`run_onchange_reload-agent-units.sh.tmpl` script only runs `daemon-reload` when a
unit file changes — it never calls `enable` or `start`. Activation is always an
explicit command (`moshi-install`, `cursor-install`, `orca-setup`).
herdr's binary is installed automatically on every Unix host; only the
Linux update timer is enabled by `herdr-setup`.

| Unit | Purpose | Enabled by |
|------|---------|------------|
| `moshi-hook.service` | Moshi daemon (local socket + WebSocket bridge) | `moshi-setup` |
| `moshi-update.service` / `.timer` | Daily `update-moshi` | `moshi-setup` |
| `cursor-worker.service` | Cursor private worker (`cursor-agent worker start`) | `cursor-setup` |
| `cursor-update.service` / `.timer` | Daily `update-cursor-agent` | `cursor-setup` |
| `herdr-update.service` / `.timer` | `update-herdr` at 04:00 (handoff-aware) | `systemctl --user enable --now herdr-update.timer` |

herdr has **no long-running unit**: its server daemonizes itself outside systemd
and holds the live panes. Only the update timer is managed here, and it runs at
04:00 rather than `daily` (midnight) because the update hands the panes over to
a new server process — better when you are not typing into them.

Orca's units (`orca-serve.service`, `orca-update.{service,timer}`) live in
`/etc/systemd/system` — **system scope, not user** — because the AppImage sits in
`/opt/orca` and must boot without a session. They are generated by `orca-setup`,
not by chezmoi, which only writes inside `$HOME`.

### Restart hardening

Both long-running services use `StartLimitIntervalSec=0` (never end in `failed`)
combined with a **real exponential backoff** (`RestartSteps` + `RestartMaxDelaySec`,
systemd ≥ 254):

- `moshi-hook.service`: 2 s → 60 s
- `cursor-worker.service`: 10 s → 5 min

The backoff is not cosmetic. The previous `cursor-worker.service` had a flat
`RestartSec=10` with a broken `ExecStart`, and accumulated **262 847 failed
restarts** over seven weeks without any visible symptom. When diagnosing one of
these services, read the restart counter, not just `is-active`:

```bash
systemctl --user show -p NRestarts --value cursor-worker.service
agentsvc status          # flags a counter > 50 in red
```

### Common commands

```bash
agentsvc status                 # the three stacks at a glance
agentsvc logs moshi|orca|cursor # follow one journal
agentsvc restart moshi|cursor   # after a unit change
agentsvc reload                 # daemon-reload only
```

---

## Related Documentation

- [CLAUDE.md](../../CLAUDE.md#auto-update-system) — Auto-update overview
- [RUNBOOK.md](../../docs/RUNBOOK.md#auto-update-system-troubleshooting) — Troubleshooting guide
- [dot_local/bin/README.md](../../dot_local/bin/README.md#auto-update--health-monitoring) — Script reference
- [chezmoi systemd integration](https://www.chezmoi.io/) — Official docs

---

**Last Updated:** 2026-03-28
