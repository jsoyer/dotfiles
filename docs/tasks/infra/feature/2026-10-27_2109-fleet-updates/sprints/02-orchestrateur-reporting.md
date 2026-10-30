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
