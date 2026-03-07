#!/usr/bin/env bash

source "$CONFIG_DIR/colors.sh"

PERCENTAGE="$(pmset -g batt | grep -Eo "\d+%" | cut -d% -f1)"
CHARGING="$(pmset -g batt | grep 'AC Power')"

if [ "$PERCENTAGE" = "" ]; then
  exit 0
fi

case "${PERCENTAGE}" in
  9[0-9]|100) ICON=""  ; COLOR=$MOCHA_GREEN  ;;
  [6-8][0-9]) ICON=""  ; COLOR=$MOCHA_GREEN  ;;
  [3-5][0-9]) ICON=""  ; COLOR=$MOCHA_YELLOW ;;
  [1-2][0-9]) ICON=""  ; COLOR=$MOCHA_PEACH  ;;
  *)          ICON=""  ; COLOR=$MOCHA_RED    ;;
esac

if [[ "$CHARGING" != "" ]]; then
  ICON=""
  COLOR=$MOCHA_TEAL
fi

sketchybar --set "$NAME" icon="$ICON" icon.color="$COLOR" label="${PERCENTAGE}%"
