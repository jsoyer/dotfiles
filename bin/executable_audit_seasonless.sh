#!/usr/bin/env bash
# Audit read-only : detecte les series importees a tort comme films par le bug
# "episode sans numero de saison" (E01 sans S01) de media_automation.py.
#
# N'ecrit rien, ne deplace rien. A lancer sur n'importe quel hote concerne.
set -uo pipefail

LOG="${1:-$HOME/bin/media_automation.cron.log}"
CONFIG="${2:-$HOME/bin/media_automation/media_automation.toml}"

echo "### Audit bug 'episode sans saison'"
echo "log    : $LOG"
echo "config : $CONFIG"
echo

if [[ ! -r "$LOG" ]]; then
  echo "!! log illisible — rien a auditer"
  exit 1
fi

# 1. Releases importees en MOVIE alors que le nom porte un motif d'episode.
#    C'est la signature exacte du bug : E01/EP01/Episode.01 sans SxxExx.
echo "== 1. Releases suspectes (importees en MOVIE avec un motif d'episode) =="
suspects=$(grep -a -oP "\[IMPORT:MOVIE\] \K[^ ]*" "$LOG" 2>/dev/null \
  | grep -a -viE "S[0-9]{1,2}E[0-9]{1,3}" \
  | grep -a -iE "[._-](E|EP|EPISODE)[._-]?[0-9]{1,3}[._-]" \
  | sed -E 's/[._-](E|EP|EPISODE)[._-]?[0-9]{1,3}([._-].*)?$//I' \
  | sort | uniq -c | sort -rn)

if [[ -z "$suspects" ]]; then
  echo "  aucune — cet hote n'est pas touche."
else
  echo "$suspects" | while read -r count title; do
    echo "  $count episodes : $title"
  done
fi
echo

# 2. Destinations concernees, avec le mapping de reparation issu du log.
echo "== 2. Mapping de reparation (source -> fichier film actuel) =="
if [[ -z "$suspects" ]]; then
  echo "  n/a"
else
  echo "$suspects" | awk '{ $1=""; sub(/^ /,""); print }' | while read -r title; do
    echo "  --- $title ---"
    grep -a -oP "OK: \K\Q${title}\E[^ ]* -> .*" "$LOG" | tail -40 | sed 's/^/    /'
  done
fi
echo

# 3. Signature complementaire cote disque : dossiers movies/ a versions multiples.
#    Un film legitime en a 2-3 (qualites/editions) ; le bug en produit des dizaines.
echo "== 3. Dossiers movies/ a versions multiples (>=4 = tres suspect) =="
movies_root=$(grep -a -oP '^\s*movies\s*=\s*"\K[^"]+' "$CONFIG" 2>/dev/null)
if [[ -z "$movies_root" || ! -d "$movies_root" ]]; then
  echo "  racine movies introuvable dans la config — etape ignoree"
else
  found=0
  for dir in "$movies_root"/*/; do
    [[ -d "$dir" ]] || continue
    # Le bug produit des suffixes numeriques " (2).mkv", " (3).mkv"...
    # Ne pas confondre avec le "(annee)" present dans tout nom de film.
    n=$(find "$dir" -type f -regextype posix-extended \
          -regex '.*/[^/]+\) \([0-9]{1,3}\)\.mkv$' 2>/dev/null | wc -l)
    if (( n >= 2 )); then
      flag=""; (( n >= 4 )) && flag="   <== SUSPECT"
      printf '  %3d versions : %s%s\n' "$n" "$(basename "$dir")" "$flag"
      found=1
    fi
  done
  (( found == 0 )) && echo "  aucun"
fi
echo
echo "### Fin de l'audit (aucune modification effectuee)"
