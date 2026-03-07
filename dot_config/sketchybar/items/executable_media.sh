#!/usr/bin/env bash

source "$CONFIG_DIR/colors.sh"

sketchybar --add item media center      \
           --set media                  \
             icon="󰎆"                  \
             icon.color=$MOCHA_MAUVE    \
             icon.padding_left=8        \
             label.color=$MOCHA_MAUVE   \
             label.max_chars=30         \
             label.padding_right=8      \
             scroll_texts=on            \
             background.color=$ITEM_BG_COLOR \
             background.corner_radius=6 \
             background.height=26       \
             drawing=off                \
             script="$PLUGIN_DIR/media.sh" \
           --subscribe media media_change
