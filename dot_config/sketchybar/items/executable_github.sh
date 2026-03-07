#!/usr/bin/env bash

source "$CONFIG_DIR/colors.sh"

sketchybar --add item github right                \
           --set github                           \
             icon="󰊤"                            \
             icon.color=$MOCHA_SUBTEXT0           \
             label=""                             \
             update_freq=300                      \
             script="$PLUGIN_DIR/github.sh"       \
             click_script="open 'https://github.com/notifications'" \
           --subscribe github                     \
             system_woke
