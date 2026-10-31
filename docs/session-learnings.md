
## Compact Checkpoint — 2026-04-13T16:18:20Z

- **CWD:** /home/jeromesoyer/Documents/Github/jsoyer/dotfiles
- **Action:** Re-read this file after compaction. Resume from last completed phase.


## Compact Checkpoint — 2026-04-14T05:49:38Z

- **CWD:** /home/jeromesoyer/Documents/Github/jsoyer/dotfiles
- **Action:** Re-read this file after compaction. Resume from last completed phase.


## Compact Checkpoint — 2026-04-14T15:33:18Z

- **CWD:** /home/jeromesoyer/Documents/Github/jsoyer/dotfiles
- **Action:** Re-read this file after compaction. Resume from last completed phase.

## 2026-08-24 — Mac Pro cask upgrade skip

- **CONFIG:** Non-admin Mac Pro (`jsoyer-macOS`) cannot upgrade casks that write to `/Library` (obs virtualcam, claude, logitune, logi-options+, xquartz, elgato-*). `brew cu` has no `--except`.
- **LOGIC:** Per-host file `dot_private/Brewfile_cu_skip_<hostname>` is applied by `breww` on bulk `cu`/`upgrade` only. Explicit `breww cu -a obs` still upgrades. Bare `cu -a` must never be emitted when a skip list is active (that would upgrade skipped casks).
- **Verify:** `python3 dot_local/bin/test_breww.py`
- **LOGIC:** Hostname-only skip file missed the Mac Pro (`uname` case / `cmupgrade` calls raw `brew upgrade`). Load `Brewfile_cu_skip_<hostname>` case-insensitive AND `Brewfile_cu_skip_<MACHINE_PROFILE>`. Wrap `brew` on mac-pro. Pin skipped casks so unwrapped upgrades skip them too.

## 2026-08-29 — Intel Homebrew Tier 3 brew bundle failures

- **ENV:** MacMiniIntel is macOS 15.7.9 x86_64. Homebrew 6.0 marks this Tier 3: no Sequoia Intel bottles, and `brew install`/`upgrade` refuse source builds unless `--build-from-source` is passed.
- **LOGIC:** `chezmoi update` → `brew bundle` does not pass that flag, so every unbottled formula (awscli, php, podman, oh-my-posh, …) and bottled formulae with an unbottled dep (gstreamer → orc, spice-gtk, podman-compose → podman) print `Installing/Upgrading X has failed!`.
- **FIX:** `dot_local/bin/executable_brewfile-filter-bottled` drops those `brew` lines before bundle and lists only pourable outdated formulae for `run_onchange_update-homebrew.sh`. Keep installed kegs; compile by hand with `brew install --build-from-source <name>` if needed.
- **Verify:** `python3 dot_local/bin/test_brewfile_filter_bottled.py`

## 2026-08-29 — sidneys/homebrew aborts brew update

- **ENV:** Homebrew 6 treats `depends_on macos: :sierra` as a hard error (no replacement). `sidneys/homebrew` still has that DSL plus invalid `appcast` casks.
- **LOGIC:** The tap was in `Brewfile_blacklist` but never untapped. `brew update` (after a tap refresh, when it enumerates casks) exits 1, and `update-homebrew.sh` `set -e` failed chezmoi apply. No sidneys casks were installed.
- **FIX:** `brew-untap-blacklisted` untaps blacklist taps (including `updatest/tap,` with a trailing comma). `update-homebrew.sh` runs that first and continues if `brew update` / cask upgrade still fail.
- **Verify:** `python3 dot_local/bin/test_brew_untap_blacklisted.py`

## 2026-08-30 — macOS orca-update is the stablyai GUI cask

- **CONFIG:** `orca-update` was dropped on Darwin when agent stacks went Linux-only (`update-orca` AppImage). The GUI cask `stablyai/orca/orca` is still installed on personal Macs.
- **LOGIC:** Restore a Darwin-only `orca-update` in aliases.sh / fish / nushell that taps `stablyai/orca` and upgrades that fully-qualified cask. Unqualified `orca` is plotly/orca. Keep the Linux alias as `update-orca`. Do not define the function in functions.sh (zsh alias/function parse error).
- **Verify:** `python3 scripts/test_omp_herdr_scope.py`

## 2026-08-30 — Orca GUI cask on every Mac

- **CONFIG:** Headless Orca stays Linux-only. The macOS GUI (`stablyai/orca/orca`) belongs on every Mac, including mac-pro.
- **LOGIC:** Add the fully-qualified cask + tap to `Brewfile_personal` and `Brewfile_pro`. Never `cask "orca"` (plotly). Remove it from `run_once_09` purge lists so that script cannot uninstall it on re-run. `orca-update` on Darwin upgrades this cask.
- **Verify:** `python3 scripts/test_omp_herdr_scope.py`

## 2026-08-30 — Orca AppImage crash-loop without libfuse.so.2

- **ENV:** looping (RPi) `orca-serve` hit 70+ restarts: `dlopen(): error loading libfuse.so.2`. Debian/Raspberry Pi OS provide fuse3 only.
- **LOGIC:** systemd unit + drop-in set `APPIMAGE_EXTRACT_AND_RUN=1` (no FUSE). `orca-setup` installs `libfuse2`/`libfuse2t64` when missing. Cap restarts (`StartLimitBurst=8` / 120s). `Aptfile_rpi` lists `libfuse2`.
- **Verify:** `python3 scripts/test_orca_headless.py`

## 2026-08-30 — Orca AppImage needs GTK/ATK on Pi Lite

- **ENV:** After FUSE, looping failed with `libatk-1.0.so.0: cannot open shared object file` (Electron inside the AppImage).
- **LOGIC:** `libgtk-3-0` pulls ATK. Also nss/gbm/asound/atk-bridge/xss. `orca-setup` installs them; `Aptfile_rpi` lists them.
- **Verify:** `python3 scripts/test_orca_headless.py`

## 2026-08-30 — Orca serve SIGSEGV without Xvfb

- **ENV:** After GTK libs, looping logged `Xvfb not found` then `Missing X server or $DISPLAY` then SIGSEGV.
- **LOGIC:** Install `xvfb`. systemd `ExecStart=/usr/bin/xvfb-run --auto-servernum <AppImage> serve …`.
- **Verify:** `python3 scripts/test_orca_headless.py`

## 2026-08-30 — orca-setup set -u aborted on $DISPLAY in unit heredoc

- **ENV:** diabolo: `/home/pi/.local/bin/orca-setup: line 319: DISPLAY: unbound variable` after xvfb installed. Service stayed inactive.
- **LOGIC:** The systemd unit is `<<EOF` (unquoted) so bash expanded `$DISPLAY` in a comment. `set -u` killed the script before enable --now. Do not put `$DISPLAY` in that heredoc.
- **Verify:** `python3 scripts/test_orca_headless.py`

## 2026-08-30 — Orca ignores serve --port until the json profile exists

- **ENV:** diabolo: service active/enabled but `Port 6768 : not listening`. Orca reads `~/.config/orca/mobile-ws-fallback-port.json` and ignores `--port`.
- **LOGIC:** `orca-setup` now mkdir + writes `{"port":6768}` as the service user BEFORE start, waits up to 40s, rewrites+restarts if needed. `update-orca` mkdir -p instead of skipping when the profile dir is missing.
- **Verify:** `python3 scripts/test_orca_headless.py`


## 2026-10-30 — fleet-updates batch 1 (Sprint 1) complete, local scope
- Status: Sprint 1 complete locally (merged on feat/fleet-plan up to 5f5f5ba4); batches 2-5 not_started. Live-infra acceptance items BLOCKED (multibox VM, real fleet check, sudo -l); sudoers diff awaiting user review (§15).
- [ENV] shellcheck/pytest not installed: use `uvx --from shellcheck-py shellcheck` and `uvx pytest`.
- [LOGIC] Concurrency tests must be run repeatedly: a single run hid a stale-lock takeover race (fixed with a second mkdir mutex).
- [CONFIG] Sudoers command args need `:` and `=` escaped.
- [ENV] Worktree sprint-executors may start on an unrelated commit: first step `git checkout -b <new> <base-branch>`.
- [SECURITY] Remote output read by `fleet` must be byte-capped on stdout AND stderr; log_tail masking must handle URL passwords with `/`/`@` and truncated PEM bodies.

## 2026-10-31 — fleet-updates batch 2 (Sprint 2) complete, simulated
- Status: Sprint 2 complete and merged on feat/fleet-plan (HEAD 4db99a88); 355 tests pass, shellcheck 0, systemd-analyze verify 0. First real `fleet up -l site=garage` BLOCKED (live infra, sudoers review §15, real ntfy URL). Batches 3-5 not_started.
- [ENV] Something outside git (unknown formatter) rewrites fleet Python files in the main checkout after merges (format-only). Check `git status` right before each merge; verify on a `git archive` export. Rewrites parked in stash@{0}-{4}; source not yet found.
- [CONFIG] Read-limit hook stops code-reviewer agents after 4 files: give each reviewer at most 4 files.
- [SECURITY] Mask secrets on the data structure (keys too), never on serialized output. Cover quoted, escaped and glued values, ANSI-split secrets and ReDoS.
- [LOGIC] Worktree agents can't commit into the shared checkout: merge their fix branches.

## 2026-10-31 — fleet-updates batch 3 (Sprint 3) complete, simulated
- Status: Sprint 3 merged on feat/fleet-plan (HEAD 4276455f); 476 tests pass, shellcheck 0, visudo -cf OK on OMV/PiKVM fragments, 8/8 invariants 0. BLOCKED (live infra): real check per type, real update on OMV/PiKVM, OPNsense 403 probe, HA non-owner check, exact OPNsense endpoints. Sudoers fragments still await user review. Batches 4-5 not_started.
- [SECURITY] Sudoers lines for no-arg commands need an explicit `""` (otherwise any args allowed). Grant the canonical `readlink -f` path that was verified (lstat every ancestor: root-owned, no g/o write, no symlink component); the agent must call that same canonical path.
- [SECURITY] Root installs from a user-owned temp dir: stage as root (`.name.new`), visudo + sha256 there, then `mv` into place.
- [ENV] PreToolUse hook blocks Bash commands containing the shutdown/reboot string even inside heredoc text: reword.
- [LOGIC] A sprint branch still checked out in a finished worktree can't be checked out by the next executor: branch off it for each fix round.
- [ENV] Formatter rewrites again: stash@{0} (pre-sprint3-merge) and stash@{1} (pre-sprint3) hold AST-identical rewrites.
- Open decisions (user): cloudflared auto-rollback only as root (§14 widening?); `qm list` non-root ⇒ generic VM warning; allow https to literal 100.64/10 IPs or `*.ts.net` only; OPNsense minor detection in state `upgrade`; HA Core failure `failed` vs `degraded`; no CLI verb for API-host check/verify_privileges; placeholder `api:` URLs; env_keep + !requiretty on omv-upgrade.

## 2026-10-31 — fleet-updates batch 4 (Sprint 4) complete, local part
- Status: Sprint 4 merged on feat/fleet-plan (merge 8676a707, HEAD 699b6dee): docs/FLEET.md, `fup` alias (zsh+bash), ALIASES/CHEZMOISCRIPTS docs, drafted tailscale-acl.hujson (NOT applied). 476 tests pass, 8/8 invariants 0, shellcheck aliases.sh 145 pre-existing findings (none new). BLOCKED (live infra + user): real `fleet up`, real `--critical` (OPNsense, multibox), fleet.yml fixes, report in .artifacts/reports/. Batch 5 not_started.
- [CONFIG] 1Password mismatch: spec says vault "Fleet", code reads `op://Private/Fleet/<field>`; FLEET.md follows code. User to decide.
- [SECURITY] Tailscale ACLs are additive: an existing `* -> *:*` rule must be replaced or port 22 stays open; Tailscale SSH must stay off on targets (bypasses forced command).
- [ENV] Formatter rewrote 16 fleet .py/test files again (uncommitted, cosmetic). Leftover unmerged branch `worktree-agent-a2fe06e0e08a7989c` (unrelated start commit) not force-deleted.

## 2026-10-31 — fleet-updates batch 5 (Sprint 5) complete, simulated — ALL BATCHES DONE
- Status: Sprint 5 (Windows/macOS/WSL + pull mode) merged on feat/fleet-plan (merges 0304e8d7, 59470356; docs cc81e877). 560 tests pass, shellcheck 0, 8/8 invariants 0. BLOCKED (live infra/tooling): winget/Scoop via scheduled task, real check/update on PC+Mac, real >7d pull, Event Log refusal, plutil -lint (no Mac), PSScriptAnalyzer (no pwsh; container run denied by permissions — user decision).
- [SECURITY] Windows: never lock with `Global\`/`Local\` named mutexes (squattable by any local user); use a FileShare None lock file in the admin-only state dir. Verify agent dir owner = Administrators and refuse reparse points.
- [SECURITY] Windows sshd bootstrap: firewall rule scoped to the Tailscale adapter + 100.64/10; PasswordAuthentication no + AllowUsers, backup and `sshd -t` before restart.
- [LOGIC] launchd kills the job's process group on exit: detached work needs `AbandonProcessGroup`; watchdogs kill the group, not `pkill -P`.
- [ENV] Formatter also rewrites dot_aictx/skills/*.py and freshly merged tests: AST-compare every modified .py vs HEAD and stash before each merge. New stashes: "pre-lockfile-merge", "pre-sprint5-merge".
- [ENV] zsh doesn't word-split `$F`: run multi-path git commands via `bash -c`.
- [PROCESS] A subagent's permission denial is surfaced to the user, never retried by the orchestrator.
- Open (user): fleet.yml ntfy.url = https://ntfy.sh (public third party — token would leave the tailnet); macOS sudoers draft not applied; per-Mac manual install + ssh_user; per-PC fleet-bootstrap.ps1 as admin (AllowUsers locks out other SSH accounts); Linux pull mode opt-in (marker, pull.conf, systemctl --user enable, linger). Leftover locked worktree .claude/worktrees/agent-aebecc6d33a56cf69 (merged branch).
