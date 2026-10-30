# INVARIANTS — fleet

Contrats transverses du PRD `spec.md` (§12, §13). Chaque `Verify` sort en 0 si
l'invariant tient ; il est neutre (0) tant que le fichier concerné n'existe pas.
Chemins relatifs à la racine du dépôt dotfiles.

## Verbes de l'agent
- **Owner:** `dot_local/share/fleet/agent/fleet-agent.sh` (et `fleet-agent.ps1`)
- **Preconditions:** l'appelant passe par la clé `fleet-master-<master>` à commande imposée ; `SSH_ORIGINAL_COMMAND` = un verbe seul.
- **Postconditions:** verbe inconnu ou argument supplémentaire ⇒ code 1, rien exécuté, refus journalisé.
- **Invariants:** liste exacte `check update reboot-status reboot report`, identique dans les agents Unix et Windows ; `ping` n'est jamais un verbe agent.
- **Verify:** `for f in dot_local/share/fleet/agent/fleet-agent.sh dot_local/share/fleet/agent/fleet-agent.ps1; do test ! -f $f && continue; for v in check update reboot-status reboot report; do grep -q "$v" $f || exit 1; done; ! grep -qiE "^[[:space:]]*'?ping'?\)" $f || exit 1; done`
- **Fix:** réaligner la liste blanche sur §12 dans les deux agents.

## Vocabulaire des statuts
- **Owner:** contrat JSON v1 (§12), validé par `dot_local/share/fleet/lib/schema.py`
- **Preconditions:** toute sortie d'agent ou de module API passe par `schema.py` avant rendu.
- **Postconditions:** sortie invalide ⇒ `failed`.
- **Invariants:** agent : `started running updated up-to-date degraded failed busy skipped unsupported` ; master seul : `offline unreachable timeout held`.
- **Verify:** `f=dot_local/share/fleet/lib/schema.py; test ! -f $f || for s in started running updated up-to-date degraded failed busy skipped unsupported offline unreachable timeout held; do grep -q "\"$s\"" $f || exit 1; done`
- **Fix:** corriger `schema.py` et les producteurs pour revenir à la liste §12.

## Valeurs kind / site
- **Owner:** `dot_local/share/fleet/fleet.yml` (validé par `lib/inventory.py`)
- **Preconditions:** chaque hôte déclare `site`, `kind`, `critical`.
- **Postconditions:** valeur hors liste ⇒ `fleet.yml` rejeté, aucun run.
- **Invariants:** `kind ∈ {chezmoi-linux, chezmoi-macos, omv, pikvm, homeassistant, opnsense, proxmox, windows, guardian}` ; `site ∈ {dijon, nice, garage, cloud, mobile}` ; `critical: true` ⇔ `kind ∈ {opnsense, proxmox}`.
- **Verify:** `f=dot_local/share/fleet/fleet.yml; test ! -f $f || ! grep -E '^[[:space:]]+kind:' $f | grep -vqE 'kind:[[:space:]]*(chezmoi-linux|chezmoi-macos|omv|pikvm|homeassistant|opnsense|proxmox|windows|guardian)[[:space:]]*$'`
- **Verify (site):** `f=dot_local/share/fleet/fleet.yml; test ! -f $f || ! grep -E '^[[:space:]]+site:' $f | grep -vqE 'site:[[:space:]]*(dijon|nice|garage|cloud|mobile)[[:space:]]*$'`
- **Verify (critical):** `f=scripts/test_fleet_inventory.py; test ! -f $f || python3 -m pytest -q $f`
- **Fix:** corriger l'hôte dans `fleet.yml` ou ajouter la valeur à §12 par décision datée.

## Aucun secret en sortie
- **Owner:** `fleet` (wrapper + `lib/`)
- **Preconditions:** jetons lus depuis 1Password à l'exécution, jamais sur disque en clair.
- **Postconditions:** rapports, journaux, notifications, `log_tail` masqués.
- **Invariants:** aucun motif de clé privée ou jeton dans `runs/`, l'historique ou la file ntfy.
- **Verify:** `d=$HOME/.local/state/fleet; test ! -d $d || ! grep -rqE 'BEGIN [A-Z ]*PRIVATE KEY|tk_[A-Za-z0-9]{20,}|eyJ[A-Za-z0-9_-]{20,}\.' $d`
- **Fix:** ajouter le motif au masquage, purger les fichiers concernés, faire tourner le secret exposé.

## Sélecteur vide ≠ tout le parc
- **Owner:** `dot_local/share/fleet/lib/selector.py`
- **Preconditions:** `-l` fourni par l'utilisateur.
- **Postconditions:** aucune cible ⇒ code 2, aucune connexion ouverte.
- **Invariants:** un sélecteur ne s'élargit jamais implicitement à tout le parc ; les garde-fous (`--critical`, site sain) s'appliquent même en ciblage unitaire.
- **Verify:** `f=scripts/test_fleet_selector.py; test ! -f $f || python3 -m pytest -q $f`
- **Fix:** corriger la résolution dans `selector.py` ; ne jamais retomber sur « tous les hôtes ».

## Agent installé non modifiable
- **Owner:** `.chezmoiscripts/03-configure/run_onchange_install-fleet-agent.sh.tmpl`
- **Preconditions:** sudo disponible (gate `can-sudo`).
- **Postconditions:** `/usr/local/libexec/fleet-agent` root:root 0755 ; seul chemin référencé par `command=`.
- **Invariants:** aucune `authorized_keys` fleet sans `restrict,command="/usr/local/libexec/fleet-agent"`.
- **Verify:** `f=.chezmoiscripts/03-configure/run_onchange_install-fleet-agent.sh.tmpl; test ! -f $f || grep -q 'restrict,command="/usr/local/libexec/fleet-agent"' $f`
- **Fix:** rétablir l'option `restrict,command=` et le chemin d'installation.
