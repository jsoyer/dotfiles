
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

