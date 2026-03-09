#!/usr/bin/env bash

source "$CONFIG_DIR/colors.sh"

if [ "$1" = "$FOCUSED_WORKSPACE" ]; then
  sketchybar --set "$NAME" \
    background.color=$WS_ACTIVE_BG         \
    background.border_width=2              \
    background.border_color=$WS_ACTIVE_BORDER \
    icon.color=$WS_ACTIVE_ICON             \
    icon.shadow.drawing=on                 \
    label.shadow.drawing=on
else
  sketchybar --set "$NAME" \
    background.color=$WS_INACTIVE_BG       \
    background.border_width=0              \
    background.border_color=$TRANSPARENT   \
    icon.color=$WS_INACTIVE_ICON           \
    icon.shadow.drawing=off                \
    label.shadow.drawing=off
fi
