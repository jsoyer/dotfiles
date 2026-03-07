#!/usr/bin/env bash

source "$CONFIG_DIR/colors.sh"

front_app=(
  label.font="SF Pro:Black:12.0"
  label.color=$LABEL_COLOR
  icon.color=$MOCHA_PEACH
  icon.background.drawing=on
  display=active
  script="$PLUGIN_DIR/front_app.sh"
  click_script="open -a 'Mission Control'"
)
sketchybar --add item front_app left         \
           --set front_app "${front_app[@]}" \
           --subscribe front_app front_app_switched
