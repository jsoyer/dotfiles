#!/usr/bin/env bash

# Lightweight poll — only updates the focused workspace so new windows appear
# immediately without waiting for a workspace switch.
CONFIG_DIR="$HOME/.config/sketchybar"

FOCUSED=$(aerospace list-workspaces --focused 2>/dev/null | tr -d '[:space:]')
[ -z "$FOCUSED" ] && exit 0

apps=$(aerospace list-windows --workspace "$FOCUSED" 2>/dev/null \
  | awk -F'|' '{gsub(/^ *| *$/, "", $2); print $2}')

if [ "${apps}" != "" ]; then
  icon_strip=" "
  while read -r app; do
    icon_strip+=" $($CONFIG_DIR/plugins/icon_map_fn.sh "$app")"
  done <<<"${apps}"
else
  icon_strip=""
fi

sketchybar --set space."$FOCUSED" label="$icon_strip"
