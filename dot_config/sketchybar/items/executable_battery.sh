#!/usr/bin/env bash

source "$CONFIG_DIR/colors.sh"

sketchybar --add item battery right               \
           --set battery                          \
             update_freq=120                      \
             script="$PLUGIN_DIR/battery.sh"      \
             popup.align=right                    \
           --subscribe battery                    \
             system_woke                          \
             power_source_change                  \
             mouse.clicked                        \
             mouse.exited.global                  \
           \
           --add item battery.time popup.battery  \
           --set battery.time                     \
             icon="󱑂"                            \
             icon.color=$MOCHA_LAVENDER           \
             label="Calculating..."               \
             background.drawing=off
