#!/usr/bin/env bash

source "$CONFIG_DIR/colors.sh"

sketchybar --add item ram right   \
           --set ram              \
             icon="󰍛"            \
             icon.color=$MOCHA_MAUVE \
             update_freq=30       \
             script="$PLUGIN_DIR/ram.sh"
