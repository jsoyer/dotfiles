#!/usr/bin/env bash

source "$CONFIG_DIR/colors.sh"

sketchybar --add item wifi right                  \
           --set wifi                             \
             icon="󰖩"                            \
             icon.color=$MOCHA_BLUE               \
             label.drawing=off                    \
             update_freq=30                       \
             script="$PLUGIN_DIR/wifi.sh"         \
             popup.align=right                    \
           --subscribe wifi wifi_change           \
                            system_woke           \
                            mouse.clicked         \
                            mouse.exited.global   \
           \
           --add item wifi.ssid popup.wifi        \
           --set wifi.ssid                        \
             icon="󰤨"                            \
             icon.color=$MOCHA_BLUE               \
             background.drawing=off               \
             label="---"                          \
           \
           --add item wifi.ip popup.wifi          \
           --set wifi.ip                          \
             icon="󰩟"                            \
             icon.color=$MOCHA_LAVENDER           \
             background.drawing=off               \
             label="---"
