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

- [x] Phases (sélection dérivée de `fleet.yml`) : 1 = `chezmoi-linux`, `chezmoi-macos`, `omv`, `pikvm`, `windows` non critiques (parallèle) ; 2 = `homeassistant`, `guardian`, tags `infra`/`site-router` (série) ; 3 = `bbh-network` seul ; `critical` = OPNsense puis `multibox` (`--critical` + confirmation) — orchestrate.plan(); test_phases_derived_from_fleet_yml, test_phase_follows_edited_inventory_not_hardcoded, test_real_inventory_phases
- [x] Parallélisme (par master) : 10 au total, 4 maximum par site ; délais d'`update` par `kind` — ThreadPool 10 + 4/site semaphores, timeouts via inventory.timeout_for; test_caps_total_10_and_site_4, test_default_timeouts_per_kind
- [x] Témoins (`canary: true`) d'abord en phase 1 ; témoin `failed`/`degraded` ⇒ autres hôtes du `kind` `skipped (canary failed)` ; `--no-canary` — test_canary_runs_first_in_phase_one, test_failed_canary_skips_others_of_the_kind, test_no_canary_flag_forces
- [x] Guardians : mis à jour seulement si un autre hôte du même site (hors guardians) est en ligne, sinon `skipped (site dégradé)` — test_guardian_skipped_when_no_other_host_of_site_online, test_guardian_updated_when_site_healthy
- [x] Master courant traité en dernier, en local, sans redémarrage — test_current_master_local_last_and_never_rebooted
- [x] Hôtes hors site : diabolo prioritaire, penelope en secours ; console → master du site, bascule si injoignable — choose_masters + console delegation; test_console_delegates_to_site_master_with_failover, test_console_dijon_and_off_site_prefer_diabolo (simulated)
- [x] Suivi des jobs détachés (`started` → interrogation `report` → état final) — test_started_then_report_polled_until_final, test_ssh_cut_during_job_is_tolerated, test_detached_jobs_tracked_independently_in_parallel
- [x] Validation de schéma de chaque sortie d'agent (`schema.py`) avant tout rendu ; invalide ⇒ `failed`, jamais interpolée dans un shell — schema.parse_agent_output; test_invalid_agent_output_is_failed, SchemaTest.test_invalid_fixtures_are_rejected; SshTransport runs arg lists only (test_verb_is_passed_as_a_single_argument_never_through_a_shell)
- [x] Statuts master : `offline` (Tailscale `Online: false`, `LastSeen`), `unreachable` (Tailscale en ligne, SSH en échec ≤ 10 s), `timeout`, `held` — test_offline_carries_last_seen_and_run_continues, test_unreachable_when_online_but_ssh_fails, test_timeout_when_job_never_finishes, test_held_host_is_not_contacted_and_visible
- [x] Sélecteur `-l` : alias, `site=`, `kind=`, `tag:`, `@groupe`, `,` union, `!` exclusion ; vide ⇒ exit 2 ; `--dry-run` — test_fleet_selector.py (8 tests); CliTest.test_empty_selector_exit_2_and_no_connection; test_dry_run_lists_targets_without_connecting
- [x] Gel : `fleet hold <host> --reason --until`, `unhold`, `holds` ⇒ statut `held` ; expiration automatique — StateTest hold tests; CliTest.test_report_logs_changes_holds_commands, test_expired_hold_is_ignored
- [x] `fleet reboot --pending` : confirmation machine par machine — RebootTest.test_confirmation_per_machine_and_return_check, test_declined_reboot_not_sent, test_not_back_notifies_priority_5
- [x] Avertissement `--critical` listant les VM coupées avant confirmation — test_critical_confirmation_and_vm_warning (simulated; no agent verb lists VMs, real list unavailable - see Issues)
- [x] Rapports : terminal, `runs/<run>/report.md`, `report.json`, `run.log`, `raw/<host>.log|json` ; `fleet report [--last]`, `fleet logs <host> [--run <id>]`, `fleet changes <host> [--since]` — ReportTest.test_run_directory_layout_and_secret_free, test_report_last_logs_and_changes; CliTest.test_report_logs_changes_holds_commands
- [x] Historique : `history-<master>.jsonl` (un fichier par master), rsync vers l'autre master, fusion à la lecture (dédoublonnage `(run_id, host)`) ; `holds-<master>.json` et `last-success-<master>.json` synchronisés de la même façon (§11) — StateTest.test_history_merge_dedups_run_id_host, test_last_success_merge_keeps_latest; SshTransport.sync tested with a fake rsync (SyncTest); real rsync between masters BLOCKED (requires live infra)
- [x] Rétention 1 mois (`runs/` et historique) — StateTest.test_retention_purges_history_and_runs_but_never_last_success
- [x] ntfy (serveur sur `bbh-network`, topic `fleet`, jeton depuis 1Password) : 6 types d'événements et priorités (voir Context), formats d'état et charge utile de §12 ; file d'attente si ntfy indisponible — NotifyTest.test_six_event_types_priorities_and_tags, test_queue_when_down_then_flushed_in_order_after_recovery; real delivery BLOCKED (requires live infra)
- [x] Alerte « > 30 j sans MAJ » calculée à chaque run depuis `last-success-*` fusionnés (non purgés) — StateTest.test_stale_alert_survives_history_purge_40_days; OutcomeTest.test_stale_alert_from_last_success_after_history_purge
- [x] Timer de rappel (systemd user, quotidien) : ntfy priorité 3 si aucun `fleet up` depuis 14 j ; n'ouvre aucune connexion — ReminderTest (3 tests), CliTest.test_reminder_makes_no_connection; units verified with systemd-analyze; timer NOT enabled/started (requires live infra to fire)
- [x] Masquage des secrets dans tous les rapports, journaux, notifications ; fichiers temporaires 0600 — MaskTest, NotifyTest.test_body_never_has_log_tail_or_secret, OutcomeTest.test_history_and_last_success_written_and_secrets_masked; state/temp files 0600 asserted

## Acceptance Criteria

- [x] Ordre des phases respecté (test unitaire avec agents simulés) — test_phase_order_respected (simulated agents)
- [x] Jamais plus de 4 hôtes simultanés par site ni 10 au total (test) — test_caps_total_10_and_site_4 (peak total <= 10, per site == 4); orchestrate suite looped 20x, 20/20 green
- [x] Hôte injoignable ⇒ `offline` avec date de dernière connexion, le run continue — test_offline_carries_last_seen_and_run_continues
- [x] `fleet up -l site=inexistant` ⇒ exit 2, aucune connexion — test_empty_selector_exit_2_and_no_connection (connect seam count 0) + WrapperTest.test_empty_selector_exits_2_without_any_connection (ssh tripwire untouched)
- [x] Témoin en échec ⇒ les autres hôtes du `kind` sautés — test_failed_canary_skips_others_of_the_kind
- [x] Guardian d'un site sans autre hôte en ligne ⇒ `skipped` — test_guardian_skipped_when_no_other_host_of_site_online
- [x] Hôte gelé ⇒ `held`, visible dans le rapport — test_held_host_is_not_contacted_and_visible (report.md contains held)
- [x] Sortie d'agent invalide (fixture) ⇒ `failed` (test) — test_invalid_agent_output_is_failed (4 fixtures)
- [x] Hôte sans MAJ depuis 40 j, historique purgé à 31 j ⇒ alerte quand même (test) — StateTest.test_stale_alert_survives_history_purge_40_days + OutcomeTest.test_stale_alert_from_last_success_after_history_purge
- [x] `grep -rE` des motifs de secrets sur `runs/` ⇒ vide — ReportTest.test_run_directory_layout_and_secret_free + OutcomeTest secret scan of the whole state dir (regex = INVARIANTS Verify); INVARIANTS secret Verify exit 0 on real home
- [x] ntfy coupé pendant un run ⇒ messages renvoyés au rétablissement — test_ntfy_down_during_run_is_resent_afterwards, NotifyTest.test_queue_when_down_then_flushed_in_order_after_recovery (simulated sender)
- [ ] Premier run réel : `fleet up -l site=garage` — BLOCKED (requires live infra): real `fleet up -l site=garage` needs SSH/Tailscale to the garage hosts, sudoers change of sprint 1 applied, agent installed and a real ntfy; nothing was run against real hosts. Dry-run on the real inventory verified (WrapperTest.test_dry_run_on_real_inventory_lists_phases_without_connection).

## Verification

- [x] `python3 -m pytest scripts/test_fleet_selector.py scripts/test_fleet_orchestrate.py scripts/test_fleet_report.py` (le schéma est testé dans `test_fleet_report.py`) — `uvx pytest -q scripts/test_fleet_*.py scripts/test_chezmoi_consistency.py` => 270 passed (exit 0); selector 8, report 37, orchestrate 61 passed
- [x] `shellcheck dot_local/bin/executable_fleet` — `uvx --from shellcheck-py shellcheck dot_local/bin/executable_fleet` => exit 0, no finding
- [x] `systemd-analyze --user verify dot_config/systemd/user/fleet-reminder.*` — verify of the chezmoi-source units fails only with 'Command /home/<user>/.local/bin/fleet is not executable: No such file' (binary not deployed in this checkout); with %h pointed at a tmp dir holding an executable fleet, `systemd-analyze --user verify` => exit 0

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

- Assigned to: sprint-executor (sonnet)
- Started: 2026-10-30 (worktree branch sprint/02-orchestrateur, base 5f5f5ba4)
- Completed: 2026-10-31
- Decisions made:
  - Every outside effect is an injectable seam (transport: peers/probe/call/local_call/list_vms/sync/run_on_master; Notifier sender; `op` runner via FLEET_OP). Tests use fakes or fake ssh/rsync/agent scripts in tmp dirs; nothing touched a real host, ntfy, Tailscale or 1Password.
  - Agent output is rebuilt field by field by schema.py (unknown keys dropped, host replaced by the master's alias, master-only statuses rejected from agents, job id regex, strings masked/capped). SshTransport only accepts the 5 whitelisted verbs and passes argument lists (no shell). stdout 64 KiB / stderr 4 KiB caps kill the process group.
  - Canary rule applies per kind across phases (failed/degraded/timeout canary => other hosts of the kind skipped); canaries run first inside each phase.
  - Implicit `fleet up` (no -l) excludes the OTHER master (each master treats itself); an explicit selector may include it.
  - `critical` hosts: skipped unless --critical; with it, a VM warning then a y/N confirmation (non-tty => declined).
  - Detached job tracking tolerates SSH cuts while polling `report`; only the per-kind deadline ends it (timeout).
  - Added keys to fleet.yml: `ntfy.gateway` (phase-3 host, instead of hard-coding bbh-network) and `master_priority: {nice: penelope}` (console master choice); inventory.py validates masters/ntfy/parallel/master_priority. `reminder` subcommand added (needed by the timer).
  - Reboot runs write a report but no history (so they do not reset the 14-day reminder).
- Assumptions:
  - 🟡 ntfy.url stays the placeholder `https://ntfy.sh` already in fleet.yml; real bbh-network address unknown.
  - 🟡 Master-to-master rsync reuses the same ssh options/key as agent calls; since that key is command-restricted to the agent, a dedicated transport/key will probably be needed (not testable offline).
  - 🟡 Timer reads optional `~/.config/fleet/env` (FLEET_NTFY_TOKEN) as EnvironmentFile; `op read` needs a 1Password session which a user timer may not have.
  - 🟢 `fleet.yml` `tags` (not Tailscale tags) drive `tag:` selection and the infra/site-router phase rule.
- Issues found:
  - `--critical` warning cannot list the real VMs: the closed agent whitelist has no verb for `qm list`. The warning lists them only if the transport provides them (fake in tests); default says "VM list unavailable". Needs a user decision (new verb vs. accepting the generic warning).
  - HA OS "rebooted but not back" (prio 5) after a HA update is sprint 3; only `fleet reboot --pending` return check and the notification builder exist here. Pull-mode message exists as a builder only (no producer yet).
  - Timer is installed as files only; enabling it is not done by this sprint (no chezmoi script touched; out of file boundaries).
  - lib/orchestrate.py is ~850 lines (above the 800 guideline) after the auto-formatter; splitting transport out would be a follow-up.
  - Python 3.9 could not be run locally (no interpreter, downloads disabled); 3.9 compatibility checked by grep (no PEP 604 / match / builtin generics) and stdlib-only imports.
- Boundary deviations: none (scripts/test_chezmoi_consistency.py needed no registration).
- Review fixes (2026-10-31, code-review findings; tests in test_fleet_report.py `Review*`, test_fleet_orchestrate.py `Review*`/`SshTransportTest`, test_fleet_selector.py `SelectorReviewTest`):
  - 1 masking corrupted JSON: fixed, report/raw JSON masked on the structure (`schema.mask_data`) before `json.dumps` (`test_report_json_and_raw_roundtrip_as_valid_json_with_secrets_masked`, `test_mask_data_...`).
  - 2 RecursionError on hostile JSON: fixed, catches ValueError/RecursionError/MemoryError/TypeError and rejects non-`{` lines (`test_hostile_nesting_is_rejected_not_a_crash`).
  - 3 masking coverage: fixed, key=value (prefix/suffix names, quoted), embedded `tk_`, URL userinfo token (plain login kept), control/bidi/surrogate stripped before masking, linear-time anchors (`test_key_value_secrets_of_every_shape_are_masked`, `test_ntfy_token_masked_when_embedded`, `test_url_userinfo_...`, `test_control_chars_stripped_before_masking_...`, `test_surrogates_and_line_separators_are_cleaned`, `test_masking_is_linear_on_big_inputs`).
  - 4 notify: fixed, permanent 4xx -> `*.bad` quarantine, transient (network/5xx/401/403/408/429/HTTPException) kept, corrupt queue files quarantined, https required with a token except loopback (Notifier raises, `_make_notifier` disables notifications with a warning), orchestrator `_notify` swallows+logs exceptions (`ReviewNotifyTest.*`, `test_a_notifier_exception_never_aborts_the_run`, `test_http_ntfy_url_with_a_token_gives_no_notifier_and_a_warning`).
  - 5 hold/unhold sync result: fixed, stderr WARNING + exit 1, hold still recorded (`test_hold_with_failed_sync_warns_on_stderr_exits_1_but_records_the_hold`, `test_unhold_with_failed_sync_...`).
  - 6 directory modes: fixed, every created level 0700 (`make_private_dir`) (`test_modes_of_every_state_file_and_directory`, `test_every_file_and_directory_left_by_a_run_is_private`).
  - 7 run lock: fixed, `State.try_lock` (flock on run.lock, non-blocking), "fleet: another run in progress", exit 3, for `up` and `reboot` (`test_second_run_is_refused_with_exit_3_...`, `test_two_concurrent_runs_exactly_one_wins_20_times`).
  - 8 dry-run and `op read`: fixed, notifier built only after the dry-run branch and the lock; `default_op_runner` now honours the passed env (`test_dry_run_never_calls_op_read`, `test_positive_control_building_the_notifier_does_call_op`).
  - 9 stderr over cap: fixed, drained and truncated (" [truncated]"), only stdout overflow or timeout kills (`test_stderr_over_cap_does_not_kill_the_call`, `test_stdout_flood_is_byte_capped_and_the_process_killed`, `test_timeout_kills_a_silent_process`).
  - 10 ssh option injection: fixed, `--` before every ssh/rsync target (Python and bash wrapper; `ssh -G -- host` verified), `_target` re-validates name/user, regexes use fullmatch (`$` accepted a trailing newline) (`test_argument_after_double_dash_and_leading_dash_refused`, `ReviewInventoryNamesTest.*`).
  - 11 strict fields: fixed, verb must equal the request (the agent already rewrites it to `report` for polls), `schema` exact int 1, disk_free_pct int 0..100, packages <= 100000 (`test_verb_must_match_the_requested_verb`, `test_strict_field_types_and_ranges`).
  - 12 report robustness: fixed, malformed entries skipped in host_changes/list_runs_text/render, run id validated (no `..`, fullmatch), Markdown specials escaped (`ReviewReportTest.*`).
  - 13 reboot: fixed, valid `failed`/`busy`/`skipped`/`unsupported` reply returned at once; `reboot --dry-run` prints reboot targets (also from a console); `silent` removed; a critical current master now goes through the critical stage (still needs --critical, updated locally, last) (`test_a_valid_failed_reply_to_reboot_is_returned_at_once`, `test_reboot_dry_run_prints_reboot_targets_not_the_update_plan`, `test_console_reboot_dry_run_...`, `test_a_critical_master_still_needs_the_critical_flag`).
  - 14 test quality: fixed, (a) 50 ms delays + negative control `test_caps_negative_control_...`, (b) `test_canary_finishes_before_...` + `..._negative_control_without_canary_they_overlap`, (c) `test_phases_2_and_3_are_strictly_serial` + `test_phase_1_negative_control_runs_in_parallel`, (d) `test_stale_alert_survives_the_real_31_day_purge` + `test_no_stale_alert_for_a_recently_updated_host`, (e) `test_no_secret_anywhere_in_the_state_dir_even_with_ntfy_down`, (f) finite generators + short timeout + marker proving the kill.
  - 15 `up --dry-run -l site=garage` on the real fleet.yml: correct, no change. garage has exactly omv-garage and ha-garage; omv-garage is kind omv (phase 1 by kind) but carries tag `site-router`, which sends it to phase 2 (serial) like ha-garage (kind homeassistant, tag infra) (`test_real_inventory_garage_plan_contains_every_garage_host`).
  - 16 self-review: fixed, selector: unknown/empty `tag:` is now an error even in a union, `!x` alone stays an error and is documented (`SelectorReviewTest.*`); wrapper: `--` before ssh targets, otherwise already safe (`set -u` with `${1+"$@"}`, `exec`, no eval; shellcheck clean); fleet-reminder.service: EnvironmentFile already had the `-` prefix and no secret, added NoNewPrivileges=yes, PrivateTmp=yes and ConditionPathExists on the fleet binary (systemd-analyze verify clean).
  - Deferred: none. Not done: the orchestrator tests were written before the fixes but only the report/schema/notify ones were run red individually; the orchestrate ones were checked against the pre-fix orchestrate.py afterwards (14 failed there, 0 after).
- Review round 3 (branch fix/fleet-review3; tests in test_fleet_report.py `Review3Test`):
  1. notify redirects: fixed, `_NoRedirect` opener refuses every redirect; 3xx classified permanent (`.bad`) (`test_redirect_is_refused_and_authorization_never_follows_it` with local 302 server, `test_classify_3xx_is_permanent`).
  2. Secret-named keys: fixed, `mask_data` replaces non-empty scalar values of keys matching password/passwd/passphrase/secret/token/api-key (substring, case-insensitive, invisible chars ignored) with `[MASKED]` (`test_mask_data_masks_values_of_secret_keys`, `test_raw_json_masks_secret_keys`).
  3. Raw logs: fixed, `report.clean_log` (clean_text multiline, 256 KiB cap) on write and on read in `host_logs` (`test_raw_log_ansi_split_secret_is_masked_on_write_and_read`, `test_raw_log_is_bounded`).
  4. ReDoS: fixed, `_URL_PASSWORD`/`_URL_USERINFO` bounded, `_PEM` `[A-Z ]{0,40}` (`test_redos_inputs_are_fast`).
  5. ValueError / InvalidURL permanent, OverflowError in `valid_message` (`test_invalid_header_and_invalid_url_are_permanent`, `test_newline_in_title_with_real_sender_is_quarantined`, `test_valid_message_rejects_infinite_priority`, `test_infinity_priority_in_queue_file_is_quarantined`).
  6. `host: status` lines: fixed, `mask_secrets(keyval=False)` for the body and queue record; free-text reason/detail stay masked per field (`test_host_status_line_keeps_status_when_host_looks_secret`).
  7. Rendered report: whole-document mask removed (every field already goes through `clean_text`) (`test_rendered_report_masks_per_field_and_cell_ending_in_token_keeps_pipe`).
  8. `parse_agent_output` never raises; `_INVISIBLE` extended (`test_parse_agent_output_never_raises`, `test_soft_hyphen_and_tag_chars_cannot_split_a_keyword`).
  9. Queue: `fcntl.flock` on `<queue>/.lock` around flush/send, unlink guarded against FileNotFoundError (`test_concurrent_flushes_send_each_message_once`, 20 rounds).
  - Deferred (known limitations): `basic|bearer` prose over-masking; `jerome.soyer@host` over-masking; residual `token="ab"cd,ef` tail after a comma; unbounded queue size.
