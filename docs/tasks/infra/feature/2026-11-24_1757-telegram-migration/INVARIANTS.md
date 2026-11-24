# INVARIANTS — telegram-migration

Contrats transverses du PRD `spec.md` (§12, §13). Chaque `Verify` sort en 0 si
l'invariant tient. Chemins relatifs à la racine du dépôt dotfiles. La plupart
échouent aujourd'hui : la ligne « cible » indique le sprint après lequel la
commande doit passer et rester verte.

## Catégories
- **Owner:** `dot_local/bin/executable_agent-alert` (contrat des catégories et des clés)
- **Preconditions:** tout émetteur passe une catégorie ou accepte le défaut `agents`.
- **Postconditions:** catégorie inconnue ⇒ code 2, rien envoyé ; catégorie connue ⇒ sujet `ALERT_TELEGRAM_THREAD_<CAT>` ou sujet General si absent.
- **Invariants:** exactement `fleet`, `agents`, `chezmoi`, `media`, identiques dans `agent-alert` et le générateur de config (`dotfiles-generated-config`).
- **Verify:** `for f in dot_local/bin/executable_agent-alert dot_local/bin/executable_dotfiles-generated-config dot_local/share/fleet/lib/notify.py; do for c in fleet agents chezmoi media; do grep -qw "$c" $f || exit 1; done; done`
- **Fix:** réaligner la liste sur §12 dans l'émetteur et le générateur.
- **Cible:** échoue avant sprint 2 (`agent-alert` au sprint 1, générateur au sprint 2).

## Jeton jamais en argv
- **Owner:** `dot_local/bin/executable_agent-alert`, `dot_local/share/fleet/agent/fleet-agent.sh`
- **Preconditions:** jeton lu depuis un fichier 0600 ou l'environnement, jamais passé en option.
- **Postconditions:** `curl` reçoit l'URL contenant le jeton par `--config -` / `-K -` (stdin) ; le jeton n'apparaît ni dans `ps`, ni dans les journaux, ni dans la sortie de `--test`.
- **Invariants:** aucun appel `curl` avec `api[.]telegram[.]org/bot` en argument direct.
- **Verify:** `python3 scripts/test_agent_alert.py && uvx pytest -q scripts/test_fleet_pull.py`
- **Fix:** repasser l'URL par `curl --config -` ; faire tourner le jeton s'il a été exposé (§10).
- **Cible:** échoue avant sprint 3 (`agent-alert` au sprint 1, agent pull au sprint 3).

## Masquage jeton Telegram (fleet)
- **Owner:** `dot_local/share/fleet/lib/schema.py`
- **Preconditions:** toute sortie (rapport, historique, `log_tail`, file de notification, exception) passe par le masquage avant écriture.
- **Postconditions:** motif `[0-9]{6,}:[A-Za-z0-9_-]{30,}` remplacé ; les erreurs HTTP du canal Telegram ne contiennent jamais l'URL brute.
- **Invariants:** le motif Telegram et l'ancien motif `tk_…` (renommé `_LEGACY_TK_TOKEN` au sprint 4) sont masqués.
- **Verify:** `grep -qF '[0-9]{6,}:[A-Za-z0-9_-]{30,}' dot_local/share/fleet/lib/schema.py && uvx pytest -q scripts/test_fleet_report.py`
- **Fix:** ajouter le motif au masquage, purger `~/.local/state/fleet` des lignes concernées, faire tourner le jeton.
- **Cible:** échoue avant sprint 1.

## Masquage jeton dans le texte (shell)
- **Owner:** `dot_local/bin/executable_agent-alert`
- **Preconditions:** le texte du message vient d'appelants non maîtrisés (sorties de santé, journaux).
- **Postconditions:** tout motif de jeton Telegram ou `tk_…` dans le titre ou le message est remplacé par `[MASKED]` avant envoi.
- **Invariants:** `agent-alert` ne relaie jamais un jeton, même reçu en entrée.
- **Verify:** `f=dot_local/bin/executable_agent-alert; grep -qF '[0-9]{6,}:[A-Za-z0-9_-]{30,}' $f && grep -q MASKED $f`
- **Fix:** rétablir le filtre `sed` avant la construction du texte.
- **Cible:** échoue avant sprint 1.

## Pas d'envoi vers un mauvais chat
- **Owner:** `dot_local/bin/executable_agent-alert`
- **Preconditions:** `TELEGRAM_CHAT_ID` lu depuis la config 0600 générée depuis `op://Private/Telegram/chat-id`.
- **Postconditions:** chat_id hors motif ⇒ backend ignoré avec avertissement, rien envoyé.
- **Invariants:** chat_id = `^-100[0-9]{5,}$` (supergroupe) ; thread_id = `^[0-9]{1,10}$` ou absent.
- **Verify:** `f=dot_local/bin/executable_agent-alert; grep -qF -- '-100[0-9]{5,}' $f && grep -qF '[0-9]{1,10}' $f`
- **Fix:** rétablir la validation des identifiants avant tout envoi.
- **Cible:** échoue avant sprint 1.

## Validation stricte du jeton (pull)
- **Owner:** `dot_local/share/fleet/agent/fleet-agent.sh` et `dot_local/share/fleet/agent/fleet-agent.ps1`
- **Preconditions:** `TELEGRAM_TOKEN_FILE` dans `pull.conf` pointe vers un fichier 0600.
- **Postconditions:** 1ʳᵉ ligne hors motif complet ancré ⇒ aucun envoi, avertissement journalisé (sans la valeur).
- **Invariants:** l'ancienne regex permissive `^[A-Za-z0-9_.-]+$` n'est pas simplement élargie avec `:` ; le motif est ancré des deux côtés.
- **Verify:** `for f in dot_local/share/fleet/agent/fleet-agent.sh dot_local/share/fleet/agent/fleet-agent.ps1; do grep -qF '^[0-9]{6,}:[A-Za-z0-9_-]{30,}$' $f || exit 1; done`
- **Fix:** remettre le motif ancré complet dans les deux agents (revue de Jérôme : code qui tourne en root).
- **Cible:** échoue avant sprint 3.

## Références op:// seulement
- **Owner:** `dot_local/share/fleet/fleet.yml` (validé par `dot_local/share/fleet/lib/inventory.py`)
- **Preconditions:** les secrets Telegram vivent dans l'élément 1Password `op://Private/Telegram`.
- **Postconditions:** `fleet.yml` ne contient que des références (`token_ref`, `chat_ref`, `thread_ref`) ; une valeur en clair est rejetée par `inventory.py`.
- **Invariants:** aucun jeton ni chat_id en clair dans le dépôt.
- **Verify:** `f=dot_local/share/fleet/fleet.yml; grep -q 'op://Private/Telegram/bot-token' $f && ! git grep -qE '[0-9]{6,}:[A-Za-z0-9_-]{30,}' -- ':!docs/tasks'`
- **Fix:** remplacer la valeur par une référence `op://`, faire tourner le secret exposé (§10).
- **Cible:** échoue avant sprint 1.

## Portabilité bash 3.2
- **Owner:** `dot_local/bin/executable_agent-alert`, `dot_local/bin/executable_chezmoi-autoupdate`
- **Preconditions:** ces scripts tournent sur le bash 3.2 et le `stat` BSD d'un Mac neuf.
- **Postconditions:** droits lus avec `stat -f %Lp` en repli de `stat -c %a`, sans repli implicite à 777.
- **Invariants:** aucun `declare -A`, `mapfile`, `readarray`, `${x,,}`, `${x^^}`, `&>>`, `|&` ; `stat -c` jamais seul.
- **Verify:** `for f in dot_local/bin/executable_agent-alert dot_local/bin/executable_chezmoi-autoupdate; do ! grep -qE 'declare -A|mapfile|readarray|[$][{][A-Za-z_]+(,,|\^\^)[}]|&>>|[|]&' $f || exit 1; ! grep -q 'stat -c' $f || grep -q 'stat -f' $f || exit 1; done`
- **Fix:** réécrire la construction en bash 3.2 ; ajouter le repli `stat -f %Lp`.
- **Cible:** échoue avant sprint 1 (`stat -c` seul dans `agent-alert`).

## Plus de battement de cœur
- **Owner:** `dot_local/bin/executable_chezmoi-autoupdate`
- **Preconditions:** aucune.
- **Postconditions:** un run réussi n'envoie rien ; seuls les échecs partent (catégorie `chezmoi`, au plus 4 par heure).
- **Invariants:** pas de Phase E ni de « heartbeat ».
- **Verify:** `! grep -qiE 'Phase E|heartbeat' dot_local/bin/executable_chezmoi-autoupdate`
- **Fix:** supprimer le bloc de battement de cœur.
- **Cible:** échoue avant sprint 2.

## Envoi seul (aucune lecture Telegram)
- **Owner:** dépôt dotfiles (tous les émetteurs Telegram)
- **Preconditions:** les émetteurs utilisent le bot d'envoi seul (D15) ; les bots interactifs Vigil vivent hors dépôt.
- **Postconditions:** aucun flux `getUpdates` concurrent (pas de 409) ; aucune surface d'entrée Telegram.
- **Invariants:** aucun appel `getUpdates` ni `setWebhook` dans le code du dépôt (doc tierce `dot_aictx/skills/openclaw-config` exclue).
- **Verify:** `! git grep -qE 'getUpdates|setWebhook' -- ':!docs/tasks' ':!dot_aictx/skills/openclaw-config'`
- **Fix:** retirer l'appel ; un besoin interactif relève d'un bot séparé hors dépôt.
- **Cible:** passe dès aujourd'hui ; doit rester vert à chaque sprint.

## Fin de ntfy
- **Owner:** dépôt dotfiles
- **Preconditions:** grille de bascule complète (§12, sprint 4).
- **Postconditions:** aucun code, clé, test, CLI ni doc ntfy hors exceptions permanentes.
- **Invariants:** exceptions : `docs/tasks/**`, `docs/session-learnings.md`, `tools/aictx/src/trim.rs`, `dot_private/Brewfile_personal` (figé), `dot_private/Brewfile_blacklist`.
- **Verify:** `! git grep -i -q ntfy -- ':!docs/tasks' ':!docs/session-learnings.md' ':!tools/aictx/src/trim.rs' ':!dot_private/Brewfile_personal' ':!dot_private/Brewfile_blacklist'`
- **Fix:** supprimer l'occurrence ou, si elle est légitime, l'ajouter aux exceptions par décision datée dans `spec.md`.
- **Cible:** échoue avant sprint 4.
