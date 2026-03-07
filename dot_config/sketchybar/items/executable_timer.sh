#!/usr/bin/env bash

source "$CONFIG_DIR/colors.sh"

TIMER_SET="$PLUGIN_DIR/timer_set.sh"

sketchybar \
  --add item timer left                           \
  --set timer                                     \
    icon="󱎫"                                     \
    icon.color=$MOCHA_SUBTEXT0                    \
    label=""                                      \
    label.font="SF Pro:Semibold:12.0"             \
    background.drawing=off                        \
    update_freq=1                                 \
    popup.align=left                              \
    script="$PLUGIN_DIR/timer.sh"                 \
    click_script="sketchybar --set timer popup.drawing=toggle" \
  --subscribe timer routine mouse.clicked         \
  \
  --add item timer.5 popup.timer                  \
  --set timer.5                                   \
    icon="󰔛" icon.color=$MOCHA_GREEN             \
    label="5 min" background.drawing=off          \
    click_script="$TIMER_SET 300"                 \
  \
  --add item timer.10 popup.timer                 \
  --set timer.10                                  \
    icon="󰔛" icon.color=$MOCHA_GREEN             \
    label="10 min" background.drawing=off         \
    click_script="$TIMER_SET 600"                 \
  \
  --add item timer.25 popup.timer                 \
  --set timer.25                                  \
    icon="󰔛" icon.color=$MOCHA_YELLOW            \
    label="25 min" background.drawing=off         \
    click_script="$TIMER_SET 1500"                \
  \
  --add item timer.50 popup.timer                 \
  --set timer.50                                  \
    icon="󰔛" icon.color=$MOCHA_YELLOW            \
    label="50 min" background.drawing=off         \
    click_script="$TIMER_SET 3000"                \
  \
  --add item timer.reset popup.timer              \
  --set timer.reset                               \
    icon="󰩺" icon.color=$MOCHA_RED               \
    label="Reset" background.drawing=off          \
    click_script="rm -f /tmp/sketchybar_timer_end; sketchybar --set timer label='' icon.color=$MOCHA_SUBTEXT0 popup.drawing=off"
