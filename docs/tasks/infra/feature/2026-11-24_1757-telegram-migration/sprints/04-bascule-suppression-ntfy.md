# Sprint 4: Bascule — suppression de ntfy

## Meta

- **PRD:** `../spec.md`
- **Sprint:** 4 of 4
- **Depends on:** Sprint 2, Sprint 3 **et la grille de bascule ci-dessous complète**
- **Batch:** 3 (sequential)
- **Model:** sonnet
- **Estimated effort:** L (beaucoup de fichiers, surtout des suppressions)

## Gate (bloquant, rempli par Jérôme — l'agent ne démarre pas sinon)

Après 1-2 semaines de double envoi. « Complète » = chaque ligne porte une date de
réception **sur Telegram, dans le bon sujet**. F2/F3/F4 peuvent être validés par
`fleet notify-test --event stale|not-back|refused` (vrai builder, vrai canal).

| Id | Événement | Sujet | Reçu le |
| --- | --- | --- | --- |
| F1 | Synthèse de run fleet | fleet | |
| F2 | Hôte > 30 j sans MAJ | fleet | |
| F3 | Hôte redémarré non revenu | fleet | |
| F4 | Commande refusée par un agent | fleet | |
| F5 | MAJ autonome pull Linux/macOS | fleet | |
| F6 | MAJ autonome pull Windows | fleet | |
| F7 | Rappel 14 j | fleet | |
| A1 | Santé / MAJ stacks agents (`agent-alert`) | agents | |
| C1 | Erreur `chezmoi-autoupdate` (hôte sans écran) | chezmoi | |
| M1 | Rapport `media_automation` | media | |
| T1 | `agent-alert --test` sur un Mac | selon catégorie | |

Si une ligne reste vide : **ne pas démarrer** ; ouvrir une question à Jérôme (rater
une alerte est pire qu'un doublon).

Cette porte (D16 a) ne demande **pas** que les topics ntfy soient silencieux : pendant
le double envoi ils reçoivent encore les messages des dotfiles. Le silence des topics
est la porte de l'arrêt du serveur (D16 b, `../spec.md` §20), après ce sprint.

**Revue Jérôme avant fusion (bloquant) :** diff de `dot_local/bin/executable_orca-setup`
(migration de la config root `/etc/orca-alert.conf` → `/etc/agent-alert.conf`,
root:root 0600 conservé) et de `scripts/test_orca_headless.py` (changement d'attente
établie).

## Objective

Retirer toute trace de ntfy du dépôt (code, clés, tests, CLI, docs), ne garder que
les exceptions listées, mettre à jour les invariants, et remettre à Jérôme la liste
de démantèlement hors dépôt.

## File Boundaries

### Creates (new files)

- (aucun)

### Modifies (can touch)

- `dot_local/bin/executable_agent-alert` — retirer le backend ntfy, les clés `ALERT_NTFY_*`, l'héritage `ORCA_ALERT_*` et `/etc/orca-alert.conf` ; garder `telegram` et `none`
- `scripts/test_agent_alert.py` — retirer les cas ntfy, garder/étendre les équivalents Telegram ; `ALERT_BACKEND=ntfy` ⇒ avertissement « backend removed », pas d'envoi
- `scripts/test_orca_headless.py` — `:163-172` exige ntfy (Bearer, `ORCA_ALERT_TOKEN`, `/etc/orca-alert.conf`) : remplacer par l'équivalent Telegram (**changement d'attente établie : à signaler**)
- `dot_local/bin/executable_orca-setup` — migration ntfy `:806-842` : supprimer la copie des valeurs ntfy, gabarit Telegram seul
- `dot_local/bin/executable_orca-uninstall` — commentaire `:71`
- `dot_local/bin/executable_paseo-setup` — commentaire `:21`
- `dot_local/bin/executable_orca-health` — commentaire `:81`
- `dot_local/bin/executable_t3-health` — commentaire `:15`
- `dot_local/bin/executable_t3-setup` — commentaire `:24`
- `dot_local/bin/executable_agents-update` — commentaire `:40`
- `dot_local/bin/executable_chezmoi-autoupdate` — vérifier qu'il ne reste rien (nettoyé au sprint 2)
- `dot_local/bin/executable_cminventory` — vérifier qu'il ne reste rien (nettoyé au sprint 2)
- `dot_local/bin/executable_dotfiles-generated-config` — retirer `CHEZMOI_NTFY_*` de `SECRET_FIELDS` (`:26-28`) et la reprise ntfy de la sorte `alert`
- `scripts/test_generated_config.py` — adapter (plus de ntfy)
- `dot_zsh/00-env.zsh.tmpl` — vérifier qu'il ne reste rien
- `bin/executable_media_automation.py` — supprimer `NtfyConfig`, `send_ntfy_message`, `decouper_pour_ntfy`, `NTFY_TAILLE_MAX`, `_entete_transmissible` si inutilisé, branche ntfy de `notifier()`
- `bin/test_media_automation.py` — retirer les 41 réfs ntfy, garder la couverture Telegram
- `dot_local/share/fleet/lib/notify.py` — supprimer `NtfyChannel`, `encode_header`, l'alias de compatibilité, `FLEET_NTFY_TOKEN` ; docstring Telegram
- `dot_local/share/fleet/lib/orchestrate.py` — plus de canal ntfy ; supprimer `ntfy.gateway` et la phase 3 (`:327`, `:341`) ; docstring `:4`
- `dot_local/share/fleet/lib/inventory.py` — supprimer le schéma `ntfy` (`:281-296`) ; un bloc `ntfy:` restant ⇒ erreur explicite « ntfy removed, use telegram »
- `dot_local/share/fleet/lib/schema.py` — renommer `_NTFY_TOKEN` en `_LEGACY_TK_TOKEN`, commentaires sans « ntfy » (motif conservé, D13)
- `dot_local/share/fleet/lib/api_homeassistant.py` — docstring `:6` (« notification priorité 5 »)
- `dot_local/share/fleet/fleet.yml` — supprimer la ligne `ntfy:` et ses commentaires (`:22-25`) ; `bbh-network` (`:145`) : commentaire mis à jour + `tags: [infra]` (D11)
- `dot_local/share/fleet/agent/fleet-agent.sh` — supprimer la branche ntfy de `pull_notify` (`NTFY_URL/TOPIC/TOKEN_FILE`)
- `dot_local/share/fleet/agent/fleet-agent.ps1` — supprimer la branche ntfy de `Send-PullNotification`
- `dot_local/bin/executable_fleet` — vérifier l'aide
- `dot_config/systemd/user/fleet-reminder.service` — vérifier (plus de `FLEET_NTFY_TOKEN`)
- `scripts/test_fleet_report.py` — retirer les tests ntfy (garder ceux du motif `tk_` sous un nom neutre)
- `scripts/test_fleet_orchestrate.py` — fixture `:58` sans `ntfy` ; tests de phases sans passerelle
- `scripts/test_fleet_pull.py` — retirer les cas `NTFY_*`
- `scripts/test_fleet_appliances.py` — retirer les réfs ntfy
- `scripts/test_fleet_windows_contract.py` — `:237-238` vers le contrat Telegram
- `scripts/test_fleet_inventory.py` — `ntfy:` rejeté, `bbh-network` en phase 2
- `dot_config/mise/config.toml.tmpl` — retirer `"aqua:binwiederhier/ntfy"` (`:152`)
- `.chezmoiscripts/03-configure/run_onchange_after_purge-brew-mise-duplicates.sh.tmpl` — retirer la paire `ntfy:ntfy` (`:40`) ; `run_onchange` ⇒ relancé une fois partout, idempotent (le noter)
- `dot_private/Brewfile_JeromeSacMiniM6` — retirer `brew "ntfy"` (`:206`, overlay d'hôte modifiable)
- `docs/PACKAGE_BASELINE_2026-11-14.json` — mettre à jour le hash et le nombre de lignes de `Brewfile_JeromeSacMiniM6` dans le même commit
- `dot_private/Brewfile_blacklist` — ajouter `ntfy` (empêche `breww dump` de le réécrire depuis les Mac qui l'ont encore)
- `README.md` — `:495-496` (si restant), `:539-540` (fleet)
- `docs/FLEET.md` — retirer ntfy (`:4,34,112,123-124,136,322-337,360-368,394,418-423,472`)
- `docs/RUNBOOK.md` — retirer la section ntfy restante (dont `:500-506`, utilisateurs/ACL du serveur ntfy)
- `dot_config/systemd/README.md` — vérifier
- `dot_local/bin/README.md` — Alerting : Telegram seul (`:784-800`, `:1123`)
- `INVARIANTS.md` — « Aucun secret en sortie » : `file ntfy` → `files de notification` ; ajouter le motif Telegram au `Verify`

### Read-Only (reference but do NOT modify)

- `dot_private/Brewfile_personal` — **FIGÉ** (hash `compatibility-shared` vérifié par `scripts/test_package_layers.py:79-88`) : ne jamais modifier, même s'il contient `brew "ntfy"` (`:216`)
- `tools/aictx/src/trim.rs` — chaîne `"## ntfy Setup"` (titre à tronquer) : exception permanente
- `docs/tasks/` et `docs/session-learnings.md` — historique, exceptions permanentes
- `dot_local/bin/executable_breww` — vérifier comment `Brewfile_blacklist` est appliqué (Q4)
- `docs/PACKAGE_LAYERS.md` — règles des manifestes figés et des overlays

### Shared Contracts (consume from prior sprints or PRD)

- `agent-alert` : `ALERT_BACKEND` ∈ {`telegram`, `none`} ; reste du contrat CLI inchangé.
- Fleet : `Notifier(channels)` avec le seul `TelegramChannel`.
- Exceptions permanentes à la recherche ntfy : `docs/tasks/**`, `docs/session-learnings.md`, `tools/aictx/src/trim.rs`, `dot_private/Brewfile_personal`, `dot_private/Brewfile_blacklist`.

### Consumed Invariants (from INVARIANTS.md)

- Fin de ntfy — `git grep -i ntfy` avec les exclusions ⇒ aucune ligne
- Masquage jeton Telegram, Jeton jamais en argv, Validation stricte du jeton (pull) — toujours verts
- Invariants racine (`INVARIANTS.md`) — verts après mise à jour

## Tasks

- [ ] Vérifier la grille de bascule (section Gate) ; sinon arrêter.
- [ ] Pour chaque test ntfy supprimé : confirmer qu'un test Telegram équivalent existe (sinon l'écrire d'abord) ; lister les correspondances dans les Agent Notes. Aucun test passant n'est supprimé sans remplaçant.
- [ ] `agent-alert` : supprimer ntfy et l'héritage `ORCA_ALERT_*` / `/etc/orca-alert.conf` ; `ALERT_BACKEND` contenant `ntfy` ⇒ avertissement `backend ntfy removed`, les autres backends partent ; `--configure` : choix `telegram` ou `none` ; filtre `tk_` gardé (défense en profondeur, sans le mot ntfy).
- [ ] `orca-setup` : la migration `/etc/orca-alert.conf` ne copie plus de clés ntfy ; le fichier hérité n'est plus lu ; message d'aide `sudo agent-alert --configure --system`.
- [ ] Commentaires des stacks agents (`orca-health`, `t3-health`, `t3-setup`, `paseo-setup`, `agents-update`, `orca-uninstall`) : « Telegram » au lieu de « ntfy or Telegram ».
- [ ] `dotfiles-generated-config` : retirer `CHEZMOI_NTFY_*` et la reprise ntfy de `alert` (`ALERT_BACKEND="telegram"`) ; tests.
- [ ] `media_automation` : supprimer ntfy ; une section `[ntfy]` restante dans un TOML ⇒ avertissement journalisé, pas d'erreur.
- [ ] Fleet : supprimer ntfy de `notify.py`, `orchestrate.py`, `inventory.py`, `fleet.yml`, agents ; supprimer `gateway`/phase 3 ; `bbh-network` `tags: [infra]` (phase 2, en série) ; renommer le motif `tk_` ; tests adaptés.
- [ ] Paquets : mise, script de purge, overlay `Brewfile_JeromeSacMiniM6` + hash de référence, `Brewfile_blacklist` ; **ne pas toucher** `Brewfile_personal`. Lire `breww` pour répondre à Q4 et l'écrire dans les Agent Notes.
- [ ] Docs : README, FLEET, RUNBOOK, READMEs systemd et bin.
- [ ] `INVARIANTS.md` racine : reformuler « Aucun secret en sortie » et ajouter `[0-9]{6,}:[A-Za-z0-9_-]{30,}` à son `Verify`.
- [ ] `git grep -i ntfy -- ':!docs/tasks' ':!docs/session-learnings.md' ':!tools/aictx/src/trim.rs' ':!dot_private/Brewfile_personal' ':!dot_private/Brewfile_blacklist'` ⇒ aucune ligne.
- [ ] Remettre à Jérôme la liste de démantèlement hors dépôt (ci-dessous) dans le message de fin.

**Démantèlement manuel (Jérôme, hors dépôt)**

- [ ] Après fusion et un cycle `chezmoi-autoupdate` : relancer `orca-setup` / `paseo-setup` sur les hôtes agents (copie root `/usr/local/bin/agent-alert`), puis `sudo agent-alert --configure --system` (Telegram seul).
- [ ] Hôtes pull : retirer `NTFY_*` de `pull.conf` et supprimer le fichier jeton ntfy.
- [ ] Dépendances externes (`../spec.md` §20) : Watchtower, Diun, Vigil, CI `unifi-network-server`, émetteurs `infra-*` / `proxmox` / `pyload` / `fork-keeper` migrés vers Telegram.
- [ ] TOML `media_automation` : retirer `[ntfy]`.
- [ ] 1Password : supprimer `op://Private/Fleet/ntfy-token` et les champs `CHEZMOI_NTFY_*` de « Shell Secrets ».
- [ ] Serveur (**en dernier**, D16 b : tous les topics ntfy silencieux ≥ 3 jours) : arrêter et supprimer le conteneur `ntfy` (`~/docker/prod/ntfy`) sur `bbh-network`, ses volumes, l'entrée DNS / reverse proxy `ntfy.bbhome.wf`, l'éventuelle route Cloudflare.
- [ ] Postes : `brew uninstall ntfy` sur les Mac qui l'ont, `mise uninstall aqua:binwiederhier/ntfy` là où il est installé ; application ntfy du téléphone.

## Acceptance Criteria

- [ ] La recherche `git grep -i ntfy` avec les 5 exclusions ne renvoie rien.
- [ ] `ALERT_BACKEND=ntfy,telegram` ⇒ avertissement + envoi Telegram (test).
- [ ] `fleet.yml` avec `ntfy:` est rejeté avec un message explicite (test) ; le `fleet.yml` du dépôt valide.
- [ ] `bbh-network` est planifié en phase 2 (test).
- [ ] `scripts/test_package_layers.py` vert (manifestes figés intacts, hash de l'overlay à jour).
- [ ] Toutes les suites concernées vertes ; chaque test ntfy supprimé a son équivalent Telegram listé.
- [ ] Invariants du PRD et racine verts.

## Verification

- [ ] `python3 scripts/test_agent_alert.py` et `python3 scripts/test_orca_headless.py`
- [ ] `uvx pytest scripts/test_fleet_*.py`
- [ ] `python3 scripts/test_generated_config.py`, `python3 -m pytest -q bin/test_media_automation.py`
- [ ] `python3 -m pytest -q scripts/test_chezmoi_autoupdate_alert.py`
- [ ] `python3 scripts/test_package_layers.py`
- [ ] `bash -n` + `shellcheck` sur chaque script bash modifié (0 nouveau constat)
- [ ] Toutes les commandes `Verify` de `../INVARIANTS.md` et de `INVARIANTS.md` racine
- [ ] Manuel (Jérôme) : `agent-alert --test --category <c>` pour les 4 catégories et `fleet notify-test` après fusion ; démantèlement ci-dessus

> **Note:** Dev server smoke test and content verification are handled by the orchestrator
> after merge — do not run in the sprint-executor. Sprint-executors do static verification only.

## Context

- Retirer une ligne de Brewfile ou de mise ne désinstalle rien : la désinstallation
  est manuelle (liste ci-dessus).
- `Brewfile_personal` et `Brewfile_pro` sont des entrées de compatibilité figées par
  hash ; les overlays d'hôte (`Brewfile_<host>`) sont modifiables mais leur hash de
  référence dans `docs/PACKAGE_BASELINE_2026-11-14.json` se met à jour dans le même commit.
- Les scripts `run_onchange` modifiés (purge mise/brew) repassent une fois sur chaque
  machine : vérifier qu'ils sont idempotents avant de les modifier.
- Le motif `tk_…` reste masqué (anciens jetons dans l'historique fleet).
- Politique : signaler et continuer, **sauf** secrets, sudoers, commande imposée, ACL
  Tailscale, et la migration de config root de `orca-setup` ⇒ arrêter et demander. Un changement d'attente de test établie
  (`test_orca_headless.py`) est signalé à Jérôme dans le rapport.

## Agent Notes (filled during execution)

- Assigned to:
- Started:
- Completed:
- Decisions made:
- Assumptions:
- Issues found:
