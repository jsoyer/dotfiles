#!/usr/bin/env bash

source "$CONFIG_DIR/colors.sh"

sketchybar --add item cpu right     \
           --set cpu                \
             icon="󰍛"              \
             icon.color=$MOCHA_PEACH \
             update_freq=4          \
             script="$PLUGIN_DIR/cpu.sh"
