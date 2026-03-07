#!/usr/bin/env bash

source "$CONFIG_DIR/colors.sh"

STATE="$(echo "$INFO" | jq -r '.state')"
APP="$(echo "$INFO" | jq -r '.app // empty')"

# Store current app for media_control.sh
[ -n "$APP" ] && echo "$APP" > /tmp/sketchybar_media_app

if [ "$STATE" = "playing" ]; then
  TITLE="$(echo "$INFO" | jq -r '.title // ""')"
  ARTIST="$(echo "$INFO" | jq -r '.artist // ""')"

  if [ -n "$ARTIST" ]; then
    MEDIA="$TITLE  $ARTIST"
  else
    MEDIA="$TITLE"
  fi

  sketchybar --set "$NAME" \
    label="$MEDIA" \
    icon.background.image="media.artwork" \
    icon.background.image.scale=0.65 \
    drawing=on

  # Update play/pause icon in popup
  sketchybar --set media.playpause icon=""
else
  sketchybar --set "$NAME" drawing=off

  # Update play/pause icon in popup
  sketchybar --set media.playpause icon=""
fi
