#!/usr/bin/env bash

source "$CONFIG_DIR/colors.sh"

sketchybar --add item calendar right     \
           --set calendar                \
             icon=""                    \
             icon.color=$MOCHA_LAVENDER  \
             label.color=$MOCHA_SUBTEXT1 \
             update_freq=30              \
             script="$PLUGIN_DIR/clock.sh"
