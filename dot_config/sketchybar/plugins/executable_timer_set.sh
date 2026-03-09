#!/usr/bin/env bash

# Called with duration in seconds as first argument
DURATION=$1
[[ "$DURATION" =~ ^[0-9]+$ ]] || { echo "Error: invalid duration '${DURATION}'" >&2; exit 1; }
echo "$(($(date +%s) + DURATION))" > /tmp/sketchybar_timer_end
sketchybar --set timer popup.drawing=off
