#!/usr/bin/env bash

source "$CONFIG_DIR/colors.sh"

TIMER_FILE="/tmp/sketchybar_timer_end"

case "$SENDER" in
  "mouse.clicked")
    sketchybar --set "$NAME" popup.drawing=toggle
    ;;
  *)
    if [ ! -f "$TIMER_FILE" ]; then
      sketchybar --set "$NAME" \
        label=""               \
        icon.color=$MOCHA_SUBTEXT0
      exit 0
    fi

    END_TIME=$(cat "$TIMER_FILE")
    REMAINING=$((END_TIME - $(date +%s)))

    if [ "$REMAINING" -le 0 ]; then
      rm -f "$TIMER_FILE"
      sketchybar --set "$NAME" \
        label="Done! 󰄬"       \
        icon.color=$MOCHA_GREEN
      osascript -e 'display notification "Timer done!" with title "Sketchybar" sound name "Glass"' 2>/dev/null
    else
      MINS=$((REMAINING / 60))
      SECS=$((REMAINING % 60))

      # Color shifts as time runs out
      if [ "$REMAINING" -lt 60 ]; then
        COLOR=$MOCHA_RED
      elif [ "$REMAINING" -lt 300 ]; then
        COLOR=$MOCHA_PEACH
      else
        COLOR=$MOCHA_YELLOW
      fi

      sketchybar --set "$NAME" \
        label="$(printf '%02d:%02d' "$MINS" "$SECS")" \
        icon.color="$COLOR"
    fi
    ;;
esac
