
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

- **CONFIG:** Non-admin Mac Pro (`jsoyer-macOS`) cannot upgrade casks that write to `/Library` (obs virtualcam, logitune, logi-options+, xquartz, elgato-*). `brew cu` has no `--except`.
- **LOGIC:** Per-host file `dot_private/Brewfile_cu_skip_<hostname>` is applied by `breww` on bulk `cu`/`upgrade` only. Explicit `breww cu -a obs` still upgrades. Bare `cu -a` must never be emitted when a skip list is active (that would upgrade skipped casks).
- **Verify:** `python3 dot_local/bin/test_breww.py`
- **LOGIC:** Hostname-only skip file missed the Mac Pro (`uname` case / `cmupgrade` calls raw `brew upgrade`). Load `Brewfile_cu_skip_<hostname>` case-insensitive AND `Brewfile_cu_skip_<MACHINE_PROFILE>`. Wrap `brew` on mac-pro. Pin skipped casks so unwrapped upgrades skip them too.

## 2026-08-29 — Intel Homebrew Tier 3 brew bundle failures

- **ENV:** MacMiniIntel is macOS 15.7.9 x86_64. Homebrew 6.0 marks this Tier 3: no Sequoia Intel bottles, and `brew install`/`upgrade` refuse source builds unless `--build-from-source` is passed.
- **LOGIC:** `chezmoi update` → `brew bundle` does not pass that flag, so every unbottled formula (awscli, php, podman, oh-my-posh, …) and bottled formulae with an unbottled dep (gstreamer → orc, spice-gtk, podman-compose → podman) print `Installing/Upgrading X has failed!`.
- **FIX:** `dot_local/bin/executable_brewfile-filter-bottled` drops those `brew` lines before bundle and lists only pourable outdated formulae for `run_onchange_update-homebrew.sh`. Keep installed kegs; compile by hand with `brew install --build-from-source <name>` if needed.
- **Verify:** `python3 dot_local/bin/test_brewfile_filter_bottled.py`

