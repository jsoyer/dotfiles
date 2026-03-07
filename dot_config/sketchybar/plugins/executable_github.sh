#!/usr/bin/env bash

source "$CONFIG_DIR/colors.sh"

COUNT=$(gh api notifications 2>/dev/null | jq 'length' 2>/dev/null)

if [ -z "$COUNT" ] || [ "$COUNT" = "null" ]; then
  sketchybar --set "$NAME" label="" icon.color=$MOCHA_SUBTEXT0
  exit 0
fi

if [ "$COUNT" -gt 0 ]; then
  sketchybar --set "$NAME" label="$COUNT" icon.color=$MOCHA_RED
else
  sketchybar --set "$NAME" label="" icon.color=$MOCHA_SUBTEXT0
fi
