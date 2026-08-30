
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

