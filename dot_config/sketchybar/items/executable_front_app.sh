#!/usr/bin/env bash

source "$CONFIG_DIR/colors.sh"

sketchybar --add item front_app left              \
           --set front_app                        \
             display=active                       \
             icon.drawing=off                     \
             icon.background.drawing=on           \
             icon.background.image.scale=0.65     \
             icon.background.corner_radius=4      \
             icon.width=24                        \
             label.font="SF Pro:Semibold:13.0"    \
             label.color=$LABEL_COLOR             \
             label.padding_left=6                 \
             label.padding_right=8                \
             background.drawing=off               \
             script="$PLUGIN_DIR/front_app.sh"    \
           --subscribe front_app front_app_switched
