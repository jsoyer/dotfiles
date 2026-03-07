#!/usr/bin/env bash

source "$CONFIG_DIR/colors.sh"

update_status() {
  IP="$(ipconfig getifaddr en0 2>/dev/null)"
  if [ -n "$IP" ]; then
    SSID="$(networksetup -getairportnetwork en0 2>/dev/null | sed 's/Current Wi-Fi Network: //')"
    sketchybar --set wifi       \
      icon="󰖩"                 \
      icon.color=$MOCHA_BLUE
    sketchybar --set wifi.ssid label="$SSID"
    sketchybar --set wifi.ip   label="$IP"
  else
    sketchybar --set wifi       \
      icon="󰖪"                 \
      icon.color=$MOCHA_RED
    sketchybar --set wifi.ssid label="Not connected"
    sketchybar --set wifi.ip   label="No IP"
  fi
}

case "$SENDER" in
  "mouse.clicked")
    sketchybar --set wifi popup.drawing=toggle
    update_status
    ;;
  "mouse.exited.global")
    sketchybar --set wifi popup.drawing=off
    ;;
  *)
    update_status
    ;;
esac
