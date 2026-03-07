#!/usr/bin/env bash

ACTION="$1"
APP="$(cat /tmp/sketchybar_media_app 2>/dev/null || echo 'Music')"

case "$ACTION" in
  previous)
    osascript -e "tell application \"$APP\" to previous track" 2>/dev/null
    ;;
  playpause)
    osascript -e "tell application \"$APP\" to playpause" 2>/dev/null
    ;;
  next)
    osascript -e "tell application \"$APP\" to next track" 2>/dev/null
    ;;
esac

sketchybar --set media popup.drawing=off
