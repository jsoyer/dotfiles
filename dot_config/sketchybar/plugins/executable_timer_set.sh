#!/usr/bin/env bash

# Called with duration in seconds as first argument
DURATION=$1
echo "$(($(date +%s) + DURATION))" > /tmp/sketchybar_timer_end
sketchybar --set timer popup.drawing=off
