#!/usr/bin/env bash

source "$CONFIG_DIR/colors.sh"

sketchybar --add item mic right               \
           --set mic                          \
             icon="󰍬"                        \
             icon.color=$MOCHA_GREEN          \
             label.drawing=off               \
             update_freq=10                   \
             script="$PLUGIN_DIR/mic.sh"      \
           --subscribe mic volume_change
