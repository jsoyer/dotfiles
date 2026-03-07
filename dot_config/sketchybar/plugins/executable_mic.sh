#!/usr/bin/env bash

source "$CONFIG_DIR/colors.sh"

MUTED=$(osascript -e 'input muted of (get volume settings)' 2>/dev/null)

if [ "$MUTED" = "true" ]; then
  sketchybar --set "$NAME" icon="󰍭" icon.color=$MOCHA_RED
else
  sketchybar --set "$NAME" icon="󰍬" icon.color=$MOCHA_GREEN
fi
