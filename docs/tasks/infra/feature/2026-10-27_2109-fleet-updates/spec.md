# fleet — mise à jour et reporting du tailnet : PRD

> **Statut : FIGÉ** — Build Candidate `build-candidate/fleet-updates` (2026-10-30).
> Toute modification de périmètre passe par une nouvelle décision datée en §14.

## 1. What & Why

**Problème :** ~35 machines pilotables (Linux, macOS, Windows, appliances, OPNsense)
réparties sur 3 sites (Dijon, Nice, Garage) + cloud + nomades. Chaque mise à jour
se fait machine par machine (`sysup` en local), sans vue d'ensemble : on ne sait
pas quelle machine est en retard, laquelle attend un redémarrage, laquelle a échoué.

**Résultat attendu :** une commande (`fleet up`, alias `fup`) lancée depuis
n'importe quelle console met à jour tout ce qui est en ligne, dans un ordre sûr,
et produit un rapport (terminal + fichiers + notification ntfy). Les machines
éteintes se rattrapent seules à leur rallumage (mode pull).

**Justification :** `sysup` + sudoers sans mot de passe existent déjà sur les
machines chezmoi ; il manque l'orchestration, le reporting et la couverture des
appliances/Windows. Le contexte Tailworm (oct. 2026) impose de ne pas s'appuyer
sur Tailscale SSH.

## 2. Correctness Contract

**Audience :** l'administrateur (Jérôme), seul utilisateur. Décisions prises sur
le rapport : redémarrer, intervenir sur un échec, rallumer une machine en retard.

**Failure Definition :** rapport faux ou absent (machine annoncée à jour alors
qu'elle a échoué), machines hors ligne silencieusement ignorées, run qui bloque
sur une machine injoignable.

**Danger Definition :**
- Couper un site : redémarrage non désiré d'OPNsense, de l'hôte Proxmox
  (`multibox`), de `bbh-network` ou d'un guardian pendant une bascule 5G.
- Montée de version majeure non voulue (OPNsense, HA, macOS).
- Un master compromis qui obtient root sur tout le parc.
- Fuite de secrets (clés, jetons API) dans les logs, rapports ou notifications.

**Risk Tolerance :** une abstention est préférable à une action risquée. En cas
de doute sur l'état d'une machine critique : ne rien faire et signaler.

**Uncertainty Policy :** voir §15.

## 3. Context Loaded

- `.chezmoiscripts/03-configure/run_always_install-sudoers-sysup.sh.tmpl` :
  sudoers étroit pour `sysup` (dnf/apt/pacman/flatpak exacts), Linux uniquement.
- `sysup` : **fonction shell** (`dot_shell_common/aliases.sh:437-544`, plus
  copies fish `config.fish.tmpl:591` et nushell `config.nu:1227`), pas un
  exécutable. Seul flag : `--reboot`. Linux : apt/dnf/pacman/rpm-ostree non
  interactifs, flatpak, brew, update-omz, update-ai, mise, herdr. macOS : brew,
  mas, update-ai, mise, herdr — **pas de `softwareupdate`**. Une commande SSH
  imposée ne peut pas appeler une fonction : il faut l'extraire en script (§14).
- `dot_config/systemd/user/chezmoi-autoupdate.{service,timer}` +
  `Library/private_LaunchAgents/com.jsoyer.chezmoi-autoupdate.plist.tmpl` :
  modèle timer systemd / launchd à reproduire pour le mode pull.
- `.chezmoiscripts/03-configure/run_onchange_generate-ssh-config.sh.tmpl` :
  config SSH depuis 1Password sur macOS.
- Tests du repo : scripts Python `test_*.py` (`scripts/`, `dot_local/bin/`), pas de bats.
- Mémoire : scripts doivent tourner sur bash 3.2 / Python 3.9 (macOS d'origine).
- Tailnet (`tailscale status`, 2026-10-27) : 23 Linux, 5 macOS, 7 Windows,
  1 FreeBSD (OPNsense), 4 iOS. Aucun nœud n'a Tailscale SSH activé.
- Tailworm (25/10/2026) : flaws non corrigées dans Tailscale SSH (forward de
  socket unix en root) — recommandation : désactiver Tailscale SSH.
- Apple Silicon : l'installation d'une mise à jour macOS exige l'autorisation
  d'un « volume owner » (mot de passe ou MDM) → non automatisable proprement.

## 4. Success Metrics

| Métrique | Actuel | Cible | Mesure |
| --- | --- | --- | --- |
| Commandes pour mettre à jour le parc | ~30 sessions SSH | 1 (`fleet up`) | usage |
| Machines en ligne couvertes | 0 % | 100 % des types supportés | rapport : aucun `unsupported` |
| Machines > 30 j sans MAJ réussie | inconnu | 0 non signalée | `last-success-*.json` (non purgé) + alerte ntfy au run suivant |
| Durée d'un run (phase 1, parc en ligne, hors `windows`) | n/a | < 20 min (durée typique ; les délais par `kind` de §12 sont des plafonds par hôte, pas la durée attendue) | horodatage rapport |
| Faux « up-to-date » | n/a | 0 | comparaison `check` après `update` |

## 5. User Stories

GIVEN diabolo et penelope en ligne
WHEN je tape `fleet up` sur n'importe quelle console
THEN toutes les cibles en ligne de la phase 1-3 sont mises à jour, et je reçois
un tableau récapitulatif + une notification ntfy.

GIVEN (sprint 5, reportable) un PC Windows éteint depuis 3 semaines
WHEN il redémarre
THEN sa tâche planifiée lance `fleet-agent update` et publie le résultat sur ntfy.

GIVEN une mise à jour OPNsense disponible
WHEN je lance `fleet up`
THEN OPNsense n'est pas touché ; le rapport indique « mineure disponible » et
`fleet up --critical` est requis (avec confirmation).

GIVEN la ligne principale de Dijon coupée (diabolo, omv-dijon, ha-dijon hors ligne)
WHEN un run lancé depuis penelope atteint bbh-dij-guardian
THEN le guardian est sauté avec le statut `skipped (site dégradé, guardian = seul accès)`.

GIVEN diabolo injoignable
WHEN je tape `fleet up` depuis une console à Dijon
THEN la commande bascule sur penelope.

GIVEN un run déjà en cours sur une cible depuis penelope
WHEN diabolo tente la même cible
THEN l'agent répond `busy` et le rapport l'indique, sans double exécution.

## 6. Acceptance Criteria

- [ ] `fleet up` met à jour en parallèle les cibles phase 1 et respecte l'ordre des phases 2, 3.
- [ ] OPNsense et `multibox` ne sont jamais touchés sans `--critical` + confirmation.
- [ ] Aucun redémarrage automatique (exception : MAJ HA OS, suivie jusqu'au retour de l'API) ; `fleet reboot --pending` demande confirmation par machine.
- [ ] HA : sauvegarde réussie **avant** toute MAJ Core / add-on / OS ; échec de sauvegarde ⇒ `skipped`.
- [ ] Les clés `fleet-master-<master>` ne permettent que les 5 verbes : toute autre commande est refusée et journalisée.
- [ ] Chaque cible renvoie un JSON conforme au contrat §12, validé par schéma côté master ; une sortie invalide = statut `failed`.
- [ ] Machine hors ligne → `offline` avec date de dernière connexion ; en ligne mais SSH en échec → `unreachable` (§12) ; le run continue.
- [ ] Rapport terminal + `report.md` + `report.json` + lignes `history-<master>.jsonl` à chaque run.
- [ ] Notifications ntfy conformes au tableau §12 (synthèse, échec/retard, hôte redémarré non revenu, commande refusée, pull, rappel 14 j).
- [ ] Ciblage `-l` conforme au §12 sur `check`, `up`, `reboot`, `logs` ; sélecteur vide ⇒ erreur, jamais tout le parc ; `--dry-run` liste les cibles.
- [ ] Chaque appel d'agent et chaque refus est journalisé sur la cible (§12) ; `fleet logs <host>` affiche la sortie du dernier run.
- [ ] ntfy indisponible → notifications mises en file et renvoyées.
- [ ] Guardian dont le site n'a aucun autre hôte en ligne → `skipped`.
- [ ] `--critical` affiche un avertissement listant les VM coupées par le redémarrage avant de demander confirmation.
- [ ] Mode pull opérationnel sur Linux (systemd), macOS (launchd), Windows (tâche planifiée) — **sprint 5, reportable** : ce critère ne bloque pas la recette du v1 Linux + appliances (fin du sprint 4).
- [ ] Aucun secret dans les rapports, logs ou notifications (vérifié par grep).
- [ ] Scripts Unix compatibles bash 3.2 / POSIX ; Python compatible 3.9.
- [ ] Santé relevée avant/après ; dégradation ⇒ `degraded` + ntfy priorité 4.
- [ ] Vérifications préalables (§12) : condition bloquante ⇒ `skipped` avec raison, aucune MAJ tentée.
- [ ] `fleet hold` / `unhold` / `holds` ; hôte gelé ⇒ `held` ; expiration automatique.
- [ ] Paquets modifiés listés par hôte ; `fleet changes <host>` les affiche.
- [ ] Témoin en échec ⇒ les autres hôtes du même `kind` sont `skipped (canary failed)`.
- [ ] Une coupure SSH pendant `update` (simulée en tuant la session) n'interrompt pas la MAJ ; le master récupère l'état final.
- [ ] Aucune MAJ ne peut attendre une saisie ; fichiers de config en conflit listés dans le rapport.
- [ ] Le master se met à jour en dernier, en local, sans redémarrer.
- [ ] Jamais plus de 4 hôtes simultanés par site ni 10 au total ; délai par `kind` respecté.
- [ ] Rappel ntfy si aucun `fleet up` depuis 14 jours ; le timer n'ouvre aucune connexion.

## 7. Non-Goals

- **Mise à jour des conteneurs Docker / stacks compose** : déjà assurée par
  Watchtower + Diun sur les hôtes Docker de prod ; `fleet` se limite à vérifier
  la santé des conteneurs avant/après (une MAJ du paquet Docker les redémarre).
- **`fleet up --only <paquet>`** : imposerait un argument libre à l'agent et
  affaiblirait la liste blanche ; le mode `--security` (v1.1) couvre le besoin.
- **Actions depuis ntfy** (boutons « redémarrer ») : ferait du téléphone et de
  ntfy une télécommande root.
- **Gestion de configuration** (déployer des fichiers, installer des paquets
  arbitraires) : c'est le rôle de chezmoi ; `fleet` ne fait que des mises à jour.
- **Tailscale SSH** : exclu (Tailworm, et pas de serveur sous Windows / macOS GUI).
- **Ansible / Salt / Puppet** : exclus — master omnipotent, fragile sur Windows
  et appliances ; `sysup` fait déjà le travail.
- **Installation automatique des mises à jour système macOS** : impossible sans
  mot de passe sur Apple Silicon ; on s'appuie sur les MAJ automatiques natives
  et on se contente de vérifier.
- **Montées de version majeures** (OPNsense, macOS) : signalées, jamais appliquées.
  Exception : Home Assistant (Core et OS), majeures incluses après sauvegarde.
- **Redémarrages automatiques** : toujours manuels, confirmés — seule exception :
  la MAJ HA OS, qui redémarre l'appareil d'elle-même.
- **Aucune MAJ planifiée depuis les masters** : `fleet` est lancé à la demande.
  Seuls tournent : le mode pull sur les cibles, et le timer de rappel d'oubli sur
  les masters (lecture d'historique uniquement, §12).
- **iOS / iPadOS** : non pilotables, exclus de l'inventaire.
- **Relais de site** : aucune machine hors tailnet aujourd'hui ; les guardians
  restent de simples cibles (lignes 5G de secours).
- **Modification de l'ACL Tailscale par `fleet`** : l'ACL est rédigée par Claude et
  appliquée par Jérôme une fois le plan figé ; `fleet` ne la modifie jamais.
- **Tableau de bord web** : le rapport Markdown/JSON + ntfy suffit pour l'instant.

## 8. Technical Constraints

- **Stack :** POSIX `sh`/bash 3.2 (agent Unix, wrapper `fleet`), PowerShell 5.1
  (agent Windows), Python 3.9 stdlib (rendu du rapport, inventaire), `jq`,
  `flock`, `rsync`, OpenSSH, CLI `op` (1Password), `curl` (ntfy, API).
- **Déploiement :** chezmoi (fichiers, `run_onchange_`), `fleet bootstrap <host>`
  pour les machines hors chezmoi (OMV, PiKVM, Windows).
- **Aucune nouvelle dépendance lourde** (pas d'Ansible, pas de module PS tiers).
- **Performance :** parallélisme 10 au total et 4 par site, timeout SSH de
  connexion 10 s, délai d'`update` par `kind` (§12).

## 9. Architecture Decisions

| Décision | Coût d'inversion | Alternatives | Justification |
| --- | --- | --- | --- |
| Agent script + clé SSH à commande imposée | Moyen | Ansible, Salt, pyinfra, bash+parallel-ssh | Master compromis ≠ shell root via SSH (il peut seulement déclencher les 5 verbes, dont redémarrer) ; réutilise `sysup` ; pas de Python requis sur les cibles. **Exception assumée :** les jetons API OPNsense / HA détenus par les masters échappent à la commande imposée (voir §10) |
| OpenSSH classique sur le tailnet | Faible | Tailscale SSH | Tailworm ; pas de support Windows / macOS GUI |
| Masters actif/actif diabolo (Dijon) + penelope (Nice) | Faible | guardians masters, bbh-network | Lignes principales, toujours allumés ; guardians sur 5G de secours |
| Verrou côté agent (`flock` / mutex) | Faible | coordination entre masters | Aucun état partagé requis entre masters |
| OPNsense & Home Assistant via API | Faible | agent installé sur l'appliance | Appliances non modifiables ; droits API limités = commande imposée |
| Push + pull | Moyen | push seul | 7/7 Windows et 3/5 Mac souvent hors ligne |
| ntfy auto-hébergé sur bbh-network | Faible | ntfy.sh + jeton | État du parc ne quitte pas le tailnet |
| macOS : MAJ natives auto + vérification | Faible | mot de passe dans 1Password | Pas de mot de passe de session exposé aux masters |

## 10. Security Boundaries

- **Auth model :** une paire de clés ed25519 par master (`fleet-master-diabolo`,
  `fleet-master-penelope`), privée dans 1Password « Fleet », récupérée via un
  compte de service. Côté cible : `authorized_keys` avec
  `restrict,command="/usr/local/libexec/fleet-agent"`. Windows :
  `administrators_authorized_keys` équivalent. Révocation : retirer une ligne.
- **Trust boundaries :**
  - `SSH_ORIGINAL_COMMAND` est non fiable → liste blanche stricte de 5 verbes,
    aucun argument libre, refus journalisé.
  - Sortie JSON des agents non fiable côté master → validée par schéma avant
    rendu ; pas d'interpolation dans un shell.
  - Le **fichier** `fleet-agent` appartient à root, mode 0755, non modifiable par l'utilisateur SSH ; le **processus** s'exécute sous le compte SSH (voir « Agent non root »).
  - `known_hosts` figé au bootstrap, `StrictHostKeyChecking yes`.
  - Réseau : port 22 joignable depuis tout le tailnet tant que l'ACL n'est pas posée (risque accepté le 2026-10-27, cf. §14).
  - **Confirmation de redémarrage côté master uniquement (risque résiduel) :** le
    verbe `reboot` ne peut pas vérifier qu'un humain a confirmé ; un master
    compromis peut donc redémarrer toute cible où un redémarrage est requis.
    Atténuations : `reboot` sans effet si aucun redémarrage n'est requis, chaque
    appel journalisé sur la cible avec la clé appelante, ntfy priorité 5 sur tout
    refus. Les cibles `critical` restent exposées à ce risque — accepté avec la
    commande imposée (2026-10-30).
  - **Agent non root :** le processus `fleet-agent` s'exécute sous le compte SSH ;
    sur les cibles Unix, il n'obtient root que via des commandes **exactes** du
    sudoers (chemins absolus résolus à l'installation, sans joker ni `systemd-run`
    en sudo). Liste fermée par `kind` :
    | `kind` | Commandes root autorisées | Déployé par |
    | --- | --- | --- |
    | chezmoi-linux, proxmox, guardian | celles de `sysup` (dnf/apt-get/pacman/rpm-ostree/flatpak, existant) + `systemctl reboot` | chezmoi (sprint 1) |
    | omv | `omv-upgrade` + `systemctl reboot` | `fleet bootstrap` (sprint 3) |
    | pikvm | `rw`, `ro`, `pikvm-update`, `/usr/local/bin/cloudflared update`, `systemctl restart cloudflared`, `systemctl reboot` | `fleet bootstrap` (sprint 3) |
    | chezmoi-macos | `sysup` n'en utilise aucune ; seul ajout : `/sbin/shutdown -r now` (verbe `reboot`) | chezmoi (sprint 5) |
    | windows | pas de sudo : la clé est dans `administrators_authorized_keys`, la session SSH est donc administrateur ; l'agent n'exécute que la liste fixe du §12 « Windows » (tâche planifiée) | `fleet-bootstrap.ps1` (sprint 5) |
    | homeassistant, opnsense | aucun agent ni SSH : droits = ceux de l'utilisateur API (ci-dessous) | sprint 3 |
    Toute autre commande root sur une cible Unix ⇒ décision datée en §14 et revue par Jérôme.
  - **Jetons API (OPNsense, HA) : hors commande imposée.** Un master compromis
    peut, via l'API OPNsense « System: Firmware », lancer des MAJ, redémarrer, et
    potentiellement installer des plugins ; via HA, déclencher des MAJ. Atténuations :
    utilisateurs dédiés aux droits minimaux, jetons dans 1Password (compte de service
    révocable), jamais sur disque en clair, rotation documentée. Risque accepté le 2026-10-27 (§14).
- **Data sensitivity :** clés SSH, jeton ntfy, clé API OPNsense (droit unique
  « System: Firmware »), jetons HA (utilisateur dédié). Jamais écrits dans les
  rapports/logs ; fichiers temporaires en 0600 ; masquage dans les erreurs.
- **Tenant isolation :** n/a (mono-utilisateur). Les machines `bbh-*` sont dans le périmètre.

## 11. Data Model

**Access patterns :**
1. Fin de run : le master écrit un rapport par run (lecture humaine immédiate).
2. `fleet report --last` : lecture du dernier run.
3. Alerte retard : pour chaque hôte, date du dernier `updated`/`up-to-date` (à chaque `fleet up`).
4. Synchronisation : chaque master n'écrit que **son** fichier
   (`history-<master>.jsonl`, `runs/*-<master>/`) et le pousse en rsync chez l'autre ;
   aucun fichier n'est jamais écrit par les deux. `fleet report` fusionne à la lecture
   (concaténation + dédoublonnage `(run_id, host)`) ; `--last` = run le plus récent
   tous masters confondus.

**Entités :**
- `fleet.yml` (config, versionnée) :
  - `hosts.<alias>: {tailnet_name, site, kind, critical, ssh_user, tags?, canary?, critical_services?, timeout_min?}`
    (la phase est **dérivée**, jamais saisie — §12) ;
  - `groups.<nom>: [<alias>, ...]` (alias existants uniquement, validé) ;
  - `timeouts.<kind>: <minutes>` (défauts §12) ;
  - `masters: [diabolo, penelope]`, `ntfy: {url, topic, token_ref}`, `parallel: {total: 10, per_site: 4}`.
- `~/.local/state/fleet/runs/<ISO8601>-<master>/` : `report.json`, `report.md`, `run.log`, `raw/<host>.json|log` (purgés après 31 j).
- `~/.local/state/fleet/history-<master>.jsonl` : une ligne par (run, hôte), append-only, un fichier par master (lignes > 31 j purgées).
- `~/.local/state/fleet/last-success-<master>.json` : par hôte, date du dernier
  `updated`/`up-to-date` ; **jamais purgé** (alimente l'alerte > 30 j malgré la rétention).
- `~/.local/state/fleet/holds-<master>.json` : gels posés depuis ce master.
- `~/.local/state/fleet/ntfy-queue/` : messages en attente.

Fichiers `*-<master>` : écrits par leur seul master, poussés en rsync chez l'autre,
fusionnés à la lecture (historique : dédoublonnage `(run_id, host)` ; last-success :
date la plus récente ; holds : union, `unhold` écrit une levée datée qui l'emporte
sur un gel antérieur).

**Justification :** fichiers plats suffisants pour ~40 hôtes ; JSONL append-only
→ fusion entre masters par concaténation + dédoublonnage `(run_id, host)`.

## 12. Shared Contracts

**Verbes de l'agent :** `check`, `update`, `reboot-status`, `reboot`, `report`.
`reboot` ne fait rien si aucun redémarrage n'est requis ; il n'est appelé que par
`fleet reboot --pending`, après confirmation humaine par machine côté master.

`ping` n'est **pas** un verbe de l'agent : `fleet ping` est une commande du wrapper
(Tailscale + ouverture SSH ≤ 10 s, puis `check` n'est pas appelé).

**Installation de l'agent :** source chezmoi `dot_local/share/fleet/agent/fleet-agent.sh`
→ `~/.local/share/fleet/agent/fleet-agent.sh` (chezmoi) → copié par
`run_onchange_install-fleet-agent.sh.tmpl` via `sudo install -o root -g root -m 0755`
vers **`/usr/local/libexec/fleet-agent`**, seul chemin référencé par `command=`.
`sysup` extrait : `dot_local/bin/executable_sysup` → `~/.local/bin/sysup`, appelé
par l'agent par chemin absolu, **sans `--reboot`** (le redémarrage passe uniquement
par le verbe `reboot`).

**Définitions testables :**
- **En ligne :** `Online: true` dans `tailscale status --json` **et** connexion SSH établie en ≤ 10 s.
- **`offline` :** `Online: false` dans Tailscale (date `LastSeen` reportée). Aucune connexion tentée.
- **`unreachable` :** `Online: true` mais SSH en échec (délai 10 s, refus, clé d'hôte non conforme).
- **`timeout` :** job détaché non terminé dans le délai du `kind`.
- **`critical` :** uniquement le champ `critical: true` de `fleet.yml` (source unique).
  Le validateur l'impose pour `kind ∈ {opnsense, proxmox}` et le refuse ailleurs.
  Les guardians et `bbh-network` ne sont **pas** `critical` : ce sont des hôtes
  **sensibles** (phases 2-3, en série), soumis à la règle Stop de §15 en cas de doute.
- **Version majeure / mineure (par source) :**
  | Source | Majeure | Traitement |
  | --- | --- | --- |
  | OPNsense | changement de série `AA.M` (ex. 26.1 → 26.7), indiqué par l'API firmware (`upgrade_major_version`) | signalée dans `major_available`, jamais appliquée |
  | Home Assistant Core / OS | changement de l'année `AAAA.M` (Core) ou du premier nombre (OS) | **appliquée** après sauvegarde (décision 2026-10-27) |
  | macOS | nouvelle version majeure (`softwareupdate --list`) | signalée, jamais appliquée (MAJ natives) |
  | Distributions Linux | montée de version de la distribution (ex. Debian 12 → 13, Fedora N → N+1) | hors périmètre : `sysup` ne la déclenche jamais ; `major_available` reste `null` (détection EOL en v1.1) |
  | apt / dnf / pacman / brew / winget / Scoop | n/a | toutes les MAJ de paquets proposées par la source sont appliquées |
- **Proxmox (`multibox`) :** agent Unix, branche `proxmox` = `apt-get dist-upgrade`
  non interactif (dépôts Proxmox configurés), via `sysup` ; jamais de redémarrage
  automatique ; redémarrage via `fleet reboot --pending --critical` après
  l'avertissement listant les VM en cours (`qm list`).
- **Site sain (guardians) :** un guardian sort toujours en 5G et a un accès LAN ;
  c'est l'accès de secours du site. Il n'est mis à jour que si le site est sain :
  **au moins un autre hôte du même `site` (hors guardians) est en ligne** au
  moment du run. Sinon ⇒ `skipped (site dégradé, guardian = seul accès)`.
  Évalué par le master, sans configuration par appareil.

**Phases (dérivées de `fleet.yml`, jamais codées en dur) :**
| Phase | Sélection | Mode |
| --- | --- | --- |
| 1 | `kind ∈ {chezmoi-linux, chezmoi-macos, omv, pikvm, windows}`, non `critical`, sans tag `infra` / `site-router`, hors `bbh-network` | parallèle (10) |
| 2 | `kind ∈ {homeassistant, guardian}` ou tag `infra` / `site-router` | série |
| 3 | `bbh-network` (porte ntfy) | seul |
| critical | `critical: true` (`OPNsense-amd64`, puis `multibox`) | série, `--critical` + confirmation |
Le master courant est retiré de sa phase et traité après la dernière phase exécutée.

**Sortie JSON (une ligne, stdout) :**
```json
{
  "schema": 1,
  "host": "omv-nice",
  "verb": "update",
  "status": "started|running|updated|up-to-date|degraded|failed|busy|skipped|unsupported",
  "reason": "string|null",
  "packages": 12,
  "changes": [{"name": "openssl", "from": "3.0.13", "to": "3.0.15"}],
  "health_before": {"failed_units": [], "unhealthy_containers": [], "disk_free_pct": {"/": 41, "/boot": 62}},
  "health_after":  {"failed_units": [], "unhealthy_containers": [], "disk_free_pct": {"/": 39, "/boot": 55}, "critical_services_down": []},
  "preflight": {"ok": true, "blocked_by": null},
  "config_conflicts": ["/etc/ssh/sshd_config.dpkg-dist"],
  "job": "string|null",
  "reboot_required": true,
  "reboot_since": "2026-10-27T21:00:00Z|null",
  "os": "Debian 12.7",
  "kernel": "6.1.0-26-amd64",
  "major_available": "string|null",
  "started": "ISO8601", "ended": "ISO8601",
  "log_tail": "≤ 20 lignes, secrets masqués"
}
```
Statuts calculés par le master uniquement : `offline`, `unreachable`, `timeout`, `held`.
`health_before` porte aussi `critical_services_down` (liste, vide par défaut).
Entrée produite par le master pour ces statuts :
`{"schema": 1, "host", "verb", "status", "reason", "last_seen": "ISO8601|null", "started", "ended"}`
(`last_seen` = `LastSeen` Tailscale lu au moment du run, conservé via l'historique).

**Exécution détachée (v1, obligatoire) :** `update` ne s'exécute jamais dans la
session SSH. L'agent lance la MAJ détachée (Linux : `systemd-run --user --unit=fleet-update-<run>`,
avec `loginctl enable-linger` posé à l'installation, aucun sudo requis pour le lancement ;
macOS : `nohup` + fichier d'état ; Windows : tâche planifiée immédiate ; PiKVM :
`systemd-run`), renvoie `{"status":"started","job":"<id>"}` puis le master interroge
`report` jusqu'à l'état final. Une coupure SSH (MAJ de Tailscale ou d'OpenSSH)
n'interrompt donc pas la MAJ. Le verbe `report` accepte l'id du dernier job
uniquement (lu sur disque côté cible, aucun argument libre).

**MAJ non interactives (v1, obligatoire) :** Debian/Ubuntu/OMV :
`DEBIAN_FRONTEND=noninteractive`, `NEEDRESTART_MODE=l`,
`-o Dpkg::Options::=--force-confdef -o Dpkg::Options::=--force-confold` ; les
fichiers `.dpkg-dist` / `.rpmnew` / `.pacnew` créés sont listés dans le rapport
(`config_conflicts`). Aucune MAJ ne doit pouvoir attendre une saisie.

**Master comme cible :** un master se traite lui-même **en dernier, en local**,
sans redémarrage ; l'autre master n'est pas concerné dans le même run.

**Parallélisme et délais :** **par master**, 10 hôtes simultanés au total et **4 maximum par site** (deux runs concurrents depuis deux masters ne se coordonnent pas : le verrou agent évite les doublons, le plafond n'est pas global).
Délai d'`update` par `kind` dans `fleet.yml` (défauts : chezmoi-linux 30 min,
chezmoi-macos 30 min, omv 30 min, pikvm 20 min, homeassistant 45 min,
windows 120 min, opnsense 30 min, proxmox 45 min). Dépassement ⇒ `timeout`.

**Rappel d'oubli :** un timer sur chaque master (systemd user, quotidien) lit
l'historique fusionné ; si aucun `fleet up` depuis 14 jours ⇒ ntfy priorité 3
« aucun fleet up depuis N jours ». Il ne lance aucune MAJ ni aucune connexion.

**Services critiques par hôte :** `fleet.yml` : `critical_services: [...]`
(ex. PiKVM : `kvmd`, `cloudflared`). Ajoutés à `health_before/after` : un service
critique inactif après MAJ ⇒ `degraded` + ntfy priorité 4.

**PiKVM :** dans une seule fenêtre `rw` (retour `ro` garanti par `trap`, même en
échec) : `pikvm-update`, puis `cloudflared` (**binaire installé à la main**, non
couvert par pacman) : `cloudflared update`, redémarrage du service si la version
a changé ; ancienne version conservée pour retour arrière si le tunnel ne revient pas. Santé : `kvmd` actif, tunnel `cloudflared` prêt
(endpoint `/ready` des métriques locales).

**Windows :** l'agent met à jour, dans l'ordre : Windows Update (API COM),
`winget upgrade --all` (sources winget + msstore), **Scoop** (`scoop update` puis
`scoop update --all`, et `--global` si des apps globales existent), **WSL**
(`wsl --update`, puis chaque distribution de `wsl -l -q` : `sysup` si présent,
sinon le gestionnaire de paquets de la distribution en root ; jamais de
`wsl --shutdown` si une session utilisateur est active), signatures Defender
(`Update-MpSignature`). `changes` agrège toutes les sources. Pas de Chocolatey.

**Santé et vérifications préalables (v1) :**
- `degraded` = MAJ appliquée mais `health_after` pire que `health_before`
  (nouvelle unité systemd en échec, nouveau conteneur `unhealthy`/arrêté,
  disque < 10 %). Notification ntfy priorité 4.
- `preflight.blocked_by` ∈ `disk_low` (`/` < 10 % ou `/boot` < 20 %),
  `on_battery`, `metered_network`, `user_active` (Windows : session active
  interactive), `update_in_progress` (gestionnaire de paquets verrouillé).
  Bloqué ⇒ `skipped` avec la raison, aucune MAJ tentée.
- `changes` : liste complète des paquets modifiés, conservée dans
  `runs/<run>/raw/<host>.json` (rétention 1 mois) ; `fleet changes <host> [--since <date>]`.

**Gel (`fleet hold`) :** `fleet hold <host> --reason "..." --until <date>`,
`fleet unhold <host>`, `fleet holds`. État côté master dans
`~/.local/state/fleet/holds-<master>.json` (un fichier par master, fusion à la
lecture, §11). Hôte gelé ⇒ `held`, visible dans le rapport ; expiration automatique.

**Alerte > 30 j :** calculée à chaque `fleet up` depuis `last-success-*.json`
fusionnés (non purgés) ; ntfy priorité 4.

**Machine témoin (canary) :** `fleet.yml` : `canary: true` sur un hôte par `kind`
(ex. `fedora-rawhide`). En phase 1, les témoins passent d'abord ; un témoin
`failed`/`degraded` ⇒ les autres hôtes de son `kind` passent `skipped (canary failed)`.
`--no-canary` pour forcer.

**Codes de sortie de l'agent :** 0 succès, 1 commande refusée, 2 échec de MAJ, 3 busy.

**Valeurs `kind` (fleet.yml) :** `chezmoi-linux`, `chezmoi-macos`, `omv`, `pikvm`,
`homeassistant`, `opnsense`, `proxmox`, `windows`, `guardian`.

**Valeurs `site` :** `dijon`, `nice`, `garage`, `cloud`, `mobile`.

**Sélecteur de cibles (`-l`, commun à `check`, `up`, `reboot`, `logs`) :**
| Syntaxe | Sélectionne |
| --- | --- |
| `omv-nice` / `omv-nice,ha-nice` (argument positionnel) | machine(s) par alias |
| `site=<site>` | un site |
| `kind=<kind>` | un type |
| `tag:<tag>` | un tag Tailscale |
| `@<groupe>` | un groupe de `fleet.yml` (`groups: {nas: [..]}`) |
| `a,b` | union ; `!x` exclusion (appliquée après l'union) |
`--dry-run` affiche les cibles retenues sans rien lancer. Un sélecteur qui ne
correspond à rien ⇒ erreur (code 2), jamais « tout le parc ». Les garde-fous
s'appliquent même en ciblage unitaire (`--critical`, site dégradé des guardians).

**Journaux :**
| Où | Contenu | Emplacement |
| --- | --- | --- |
| Cible | chaque appel (verbe, clé appelante, résultat), chaque refus | Linux : journald `-t fleet-agent` ; macOS : `/var/log/fleet-agent.log` ; Windows : Event Log source `fleet-agent` ; OPNsense/HA : journaux natifs |
| Master | déroulé du run + sortie complète par hôte | `runs/<run>/run.log`, `runs/<run>/raw/<host>.log` (rétention 1 mois) |
Consultation : `fleet logs <host>` (dernier run), `fleet logs --run <id>`.
Secrets masqués dans tous les journaux.

**Notifications ntfy (topic `fleet`) :**
| Événement | Priorité ntfy |
| --- | --- |
| Run terminé sans échec (synthèse) | 2 (basse) |
| Run avec échec, hôte `degraded`, témoin en échec, ou hôte > 30 j sans MAJ | 4 (haute) |
| Hôte redémarré non revenu (HA OS après MAJ, OPNsense, multibox) | 5 (urgente) |
| Commande refusée par un agent | 5 (urgente) |
| Mode pull : MAJ autonome effectuée | 2 (basse) |
| Rappel : aucun `fleet up` depuis 14 j | 3 (normale) |

Soit 6 types d'événements. Charge utile ntfy : `Title` = `fleet <master> : <résumé>`
(ex. `fleet diabolo : 24 ✅ · 1 ❌ · 3 reboot`), `Priority` selon le tableau,
`Tags` ∈ `ok`, `failed`, `degraded`, `reboot`, `refused`, `pull`, `reminder` ;
corps texte ≤ 20 lignes (hôtes et statuts), jamais de `log_tail` brut ni de secret.
- `ntfy-queue/<horodatage>-<n>.json` : `{"title", "priority", "tags", "body", "created"}`, 0600, renvoyé puis supprimé dans l'ordre.

**Formats d'état (master) :**
- `history-<master>.jsonl` : `{"run_id", "master", "host", "status", "reason", "packages", "reboot_required", "last_seen", "started", "ended"}` par ligne.
- `last-success-<master>.json` : `{"<host>": "ISO8601"}`.
- `holds-<master>.json` : `[{"host", "reason", "until", "set_at", "lifted_at": "ISO8601|null"}]`.
- `report.json` : `{"schema": 1, "run_id", "master", "selector", "started", "ended", "hosts": [<sortie agent v1 ou statut master>]}`.
- `run_id` : `<ISO8601 UTC compact>-<master>` (ex. `20261030T2100Z-diabolo`).

## 13. Architecture Invariant Registry

| Concept | Owner | Format | Verify |
| --- | --- | --- | --- |
| Verbes agent | fleet-agent | `check\|update\|reboot-status\|reboot\|report` | `grep` des verbes dans agent Unix + PS = liste identique (INVARIANTS) |
| Statuts | fleet-agent | liste §12 | `python3 -m pytest scripts/test_fleet_agent.py scripts/test_fleet_report.py` |
| `kind` / `site` | fleet.yml | valeurs §12 | validateur de `fleet.yml` |
| Pas de secret en sortie | fleet | regex jeton/clé | `grep -rE` sur `runs/` = vide |
| Sélecteur vide ≠ tout le parc | fleet | code 2 | test unitaire `fleet up -l site=inexistant` ⇒ exit 2 |

## 14. Open Questions

- [x] **Extraire `sysup` en exécutable** `dot_local/bin/executable_sysup` (bash 3.2),
  fonctions bash/zsh/fish/nushell réduites à un appel — validé (2026-10-27), sprint 1.
- [x] **Compte SSH sur les cibles :** l'utilisateur courant, clé à commande imposée
  dans son `authorized_keys` ; réutilise le sudoers de `sysup` — validé (2026-10-27).
- [x] **Run planifié côté masters :** aucun. `fleet` uniquement à la demande + mode
  pull sur les cibles — validé (2026-10-27).
- [x] **Home Assistant :** Core + add-ons + OS mis à jour (sauvegarde avant).
  **Exception à « aucun redémarrage automatique »** : la MAJ HA OS redémarre
  l'appareil ; `fleet` attend son retour (API qui répond, délai max 15 min) —
  validé (2026-10-27). Versions majeures HA (Core et OS) **incluses** — validé (2026-10-27).
- [x] **Rétention des rapports :** 1 mois (`runs/` et lignes d'historique > 31 j purgées) — validé (2026-10-27).
- [x] **Hôte Proxmox = `multibox`** (indiqué par Jérôme, 2026-10-27) — décidé ;
  contrôle de cohérence `pveversion` au sprint 1 (garde-fou, pas une question ouverte).
- [x] **Lancement détaché sans élargir le sudoers** : `systemd-run --user` + linger ;
  sudoers par `kind` limité à la liste fermée de §10 — décidé (2026-10-30), revue au sprint 1 (chezmoi) et au sprint 3 (OMV, PiKVM).
- [x] **OPNsense sans copie de `config.xml` sur le master** : l'utilisateur API garde le
  droit unique « System: Firmware » ; l'historique de configuration local suffit — décidé (2026-10-30).
- [x] **Plafond de parallélisme par master** (pas global entre masters) — décidé (2026-10-30).
- [x] **Stockage par master** : `history-`, `holds-`, `last-success-<master>` ;
  `last-success` jamais purgé — décidé (2026-10-30).
- [x] **Taille des sprints 1 et 2** (effort L) : conservés en 5 sprints ; l'exécuteur
  suit l'ordre des tâches avec un point de contrôle (tests verts) à mi-sprint — décidé (2026-10-30).
- [x] **Orchestrateur** : scripts maison retenus face à la variante Ansible + `fleet-agent` — validé (2026-10-30).
- [x] **cloudflared sur PiKVM** : binaire installé à la main ⇒ `cloudflared update` — validé (2026-10-30).
- [x] **Windows** : Scoop + WSL (moteur et distributions), pas de Chocolatey — validé (2026-10-30).
- [x] **Priorité des cibles** : Linux + appliances d'abord ; Windows/macOS en dernier (sprint 5, reportable) — validé (2026-10-30).
- [x] **ACL Tailscale** (`tag:fleet-master`) : rédigée au sprint 4 puis appliquée
  par Jérôme ; d'ici là, le risque « port 22 ouvert au tailnet » ci-dessous couvre
  les sprints 1-4 — validé (2026-10-27), calendrier précisé (2026-10-30).
- [x] **Port 22 joignable depuis tout le tailnet** en attendant l'ACL : risque accepté (Jérôme, 2026-10-27).
- [x] **Jetons API OPNsense / HA hors commande imposée** : risque §10 accepté (Jérôme, 2026-10-27).
- [x] **Guardians** : toujours en 5G + accès LAN ; mis à jour seulement si un autre
  hôte du site est en ligne (§12) — validé (2026-10-27).
- [x] **Hôtes hors site** : diabolo prioritaire, penelope en secours — validé (2026-10-27).
- [x] **Fenêtre `--critical`** : aucune restriction horaire (déclenchement manuel) ;
  avertissement listant l'impact avant confirmation — validé (2026-10-27).
- [x] **Futur guardian du Garage** : même rôle que les autres guardians — validé (2026-10-27).

## 15. Uncertainty Policy

- Machine `critical` ou sensible (guardian, `bbh-network`) dont l'état est douteux
  (vérification préalable ou santé illisible, site sain indéterminable) **avant
  toute action** : **Stop** — ne rien faire, statut `skipped`, raison explicite. Un état
  clair n'empêche pas leur MAJ dans leur phase.
- Machine standard : **Flag** — tenter, rapporter `failed` avec `log_tail`.
- Sortie d'agent invalide (tout hôte) : `failed` (§6), et aucune action suivante
  sur cet hôte dans le run (ni `reboot`, ni nouvel `update`).
- Implémentation : **Flag** pour les détails de format ; **Stop** pour tout ce qui touche clés, sudoers, ACL.
- Conflit sécurité ↔ couverture : préférer la sécurité (machine non couverte plutôt que droits élargis).

## 16. Verification

- **Déterministe :** `shellcheck` (agent, wrapper), PSScriptAnalyzer (agent Windows),
  tests Python `test_fleet_*.py` (schéma JSON, rendu, inventaire, fusion d'historique),
  tests de la liste blanche (commande interdite → code 1).
- **Réel :** `fleet ping` / `fleet check` sur un échantillon par `kind` ;
  `fleet up -l site=garage` comme premier run réel ; grep de secrets sur `runs/`.
- **Manuel :** relecture du rapport ; réception ntfy ; tentative de shell avec
  la clé master (doit échouer).

## 17. Sprint Decomposition

> Fichiers `sprints/NN-*.md`, `progress.json` et `INVARIANTS.md` générés
> (2026-10-30). Les fiches de sprint font foi pour les limites de fichiers.
> Sprints 1 et 2 : effort L, point de contrôle (tests verts) à mi-sprint.

| Sprint | Titre | Dépend de | Batch | Modèle | Parallèle avec |
| --- | --- | --- | --- | --- | --- |
| 1 | Agent Unix + inventaire | — | 1 | sonnet | — |
| 2 | Orchestrateur + reporting + ntfy | 1 | 2 | sonnet | — |
| 3 | Appliances (OMV, PiKVM, HA, OPNsense, Proxmox) | 2 | 3 | sonnet | — |
| 4 | Finitions + mise en service Linux/appliances | 3 | 4 | sonnet | — |
| 5 | Postes de travail (Windows, macOS, WSL) + mode pull — priorité basse | 4 | 5 | sonnet | — |

**Priorité des cibles :** Linux et appliances (PiKVM, OPNsense, HA, OMV,
Proxmox) d'abord — le v1 est utile dès la fin du sprint 4. Windows et macOS sont
des postes de travail mis à jour ponctuellement, souvent à la main : support
voulu mais en dernier (sprint 5), reportable.

### Sprint 1 : Agent Unix + inventaire
**Objectif :** un agent Unix sûr, déployé par chezmoi, interrogeable par les masters.
- Fichiers : `dot_local/share/fleet/agent/fleet-agent.sh`, `dot_local/share/fleet/fleet.yml`,
  `.chezmoiscripts/03-configure/run_onchange_install-fleet-agent.sh.tmpl`,
  `dot_local/bin/executable_fleet` (verbes `ping`, `check`), tests.
- Critères : liste blanche testée (verbe inconnu ⇒ code 1, journalisé) ; JSON
  conforme ; verrou ; `authorized_keys` déployé avec
  `restrict,command=` (tentative de shell ⇒ refus) ; agent root 0755 ;
  `sysup` extrait en exécutable (l'agent ne passe jamais `--reboot`) ; sudoers
  étendu à la seule commande `systemctl reboot` (`visudo -cf`) ; linger activé ; journalisation côté cible (journald / fichier
  macOS) de chaque appel et refus ; `groups` dans `fleet.yml` ; `fleet check` réel
  sur la VM de test puis 3 machines Linux (Fedora, Debian, Arch) ; **santé avant/après** (unités systemd, conteneurs
  Docker, disque) ; **vérifications préalables** (disque, batterie, réseau
  limité, MAJ en cours) ; **liste `changes`** (dnf/apt/pacman/brew) ;
  **exécution détachée** (`systemd-run` / `nohup`) + suivi par `report` ;
  **MAJ non interactives** vérifiées dans `sysup` (variables Debian, conffiles,
  `needrestart`) ; **VM de test jetable** sur `multibox` (clonée d'un modèle),
  cible de tous les tests réels avant le parc — test de coupure SSH en plein `update`.

### Sprint 2 : Orchestrateur + reporting
**Objectif :** `fleet up` complet avec phases, bascule de master, rapport et ntfy.
- Critères : phases conformes au tableau §12 ; guardian d'un site dégradé ⇒
  `skipped` ; hôtes hors site traités par diabolo (penelope en secours) ;
  `offline` / `unreachable` sans blocage ; validation de schéma côté master
  (sortie invalide ⇒ `failed`) ; rapport 3 formats ; masquage des secrets
  testé + fichiers temporaires 0600 + grep de secrets vide sur `runs/` ;
  sélecteur `-l` + `--dry-run` (tests unitaires de résolution) ; `run.log` +
  `raw/<host>.log` + `fleet logs` ; 6 types de notifications ntfy ; file ntfy ;
  statut `degraded` ; `fleet hold/unhold/holds` (synchronisé entre masters) ;
  `fleet changes` ; témoins (`canary`) en tête de phase 1 avec arrêt par `kind` ;
  suivi des jobs détachés ; master traité en dernier en local ; limite 4/site et
  10 au total ; délais par `kind` ; timer de rappel d'oubli (14 j) ;
  historique, holds et last-success par master + fusion à la lecture ; console →
  master avec bascule ; alerte « > 30 j sans MAJ » calculée à chaque run depuis
  `last-success` (aucune MAJ planifiée).

### Sprint 3 : Appliances
**Objectif :** OMV, PiKVM (+ `cloudflared`, fenêtre `rw`/`ro`), HA (API + sauvegarde), OPNsense (API firmware), Proxmox, `fleet bootstrap`.
- Critères : `check` réel par type ; `--critical` exige confirmation ; majeures
  OPNsense jamais appliquées (HA : majeures appliquées, §12) ; HA : sauvegarde
  en échec ⇒ `skipped`, aucune MAJ ; utilisateurs API à droits minimaux vérifiés
  (OPNsense : appel hors « System: Firmware » refusé ; HA : utilisateur non
  propriétaire) ; `fleet reboot --pending` confirme machine par machine ;
  jetons API jamais écrits sur disque ni en sortie.

### Sprint 4 : Finitions et mise en service (Linux + appliances)
**Objectif :** rendre le v1 utilisable au quotidien sur les cibles prioritaires.
- Critères : `docs/FLEET.md` (installation, prérequis, commandes, procédure de
  révocation d'une clé) ; alias `fup` (zsh + bash) ; ACL Tailscale rédigée
  (`tag:fleet-master`) et remise à Jérôme ; premier `fleet up` complet réel sur
  Linux + appliances (hors `--critical`), rapport relu ; `fleet up --critical`
  réel sur OPNsense puis `multibox` avec confirmation.

### Sprint 5 : Postes de travail (Windows, macOS, WSL) + mode pull — priorité basse
**Objectif :** pouvoir mettre à jour ponctuellement les postes de travail ; ce
sprint peut être reporté sans bloquer le v1 (les postes sont souvent mis à jour à la main).
- **Windows :** `fleet-agent.ps1` (Windows Update COM + winget + Scoop + **WSL** +
  Defender), `fleet-bootstrap.ps1` à lancer une fois en admin sur chaque PC :
  OpenSSH Server (capability + service auto), règle pare-feu port 22 limitée à
  100.64.0.0/10, `administrators_authorized_keys` avec commande imposée **et ACL
  correctes** (Administrators + SYSTEM uniquement, sinon sshd ignore le fichier),
  source Event Log, tâches planifiées (exécution détachée + mode pull),
  vérification de winget. **Risque à valider en premier :** winget fonctionne mal
  hors session interactive (SSH, SYSTEM) ; l'exécution passe par une tâche
  planifiée dans le contexte de l'utilisateur (Scoop est aussi par utilisateur).
- **macOS :** validation de l'agent Unix sur Mac (launchd, `/var/log/fleet-agent.log`,
  `sysup`, vérification des MAJ automatiques natives).
- **Mode pull :** systemd (portables Linux), launchd (macOS), tâche planifiée (Windows).
- Critères : PSScriptAnalyzer propre ; Event Log ; vérifications préalables
  (`on_battery`, `metered_network`, `user_active`) ; délai Windows 120 min ;
  `check` + `update` réels sur un PC et un Mac ; un poste rallumé se met à jour et
  notifie seul ; jamais de redémarrage en mode pull.

## 17bis. Feuille de route

| Priorité | Version | Fonctions | Où |
| --- | --- | --- | --- |
| **Haute** | **v1 (ce PRD)** | santé avant/après + `degraded` ; vérifications préalables ; `fleet hold` ; journal des paquets modifiés (`fleet changes`) ; machines témoins | sprints 1, 2, 4 |
| **Moyenne** | v1.1 (PRD suivant) | snapshot Proxmox avant MAJ d'une VM + `fleet rollback <vm>` (API de `multibox`) ; cache de paquets par site sur le LAN (apt/dnf), utilisé aussi par les guardians pour épargner la 5G ; Wake-on-LAN des postes éteints (réveil + extinction après run) ; mode `--security` (correctifs de sécurité seuls, CVE listées) ; détection OS en fin de support et noyau installé ≠ noyau en cours | PRD dédié |
| **Plus tard** | v2 | firmware (`fwupd`, EEPROM RPi, BIOS) en signalement seul ; `fleet rotate-keys` (clés masters, jetons API) ; tableau de bord statique servi par `bbh-network` ; procédure de secours sans master (runbook) ; contrôle de version agent ↔ master | backlog |

Hors feuille de route : MAJ des conteneurs (Watchtower + Diun), `--only <paquet>`,
actions depuis ntfy (voir §7).

## 18. Execution Log

_(rempli à l'exécution)_

## 19. Learnings

_(rempli après les sprints)_
