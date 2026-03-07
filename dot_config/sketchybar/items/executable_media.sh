#!/usr/bin/env bash

source "$CONFIG_DIR/colors.sh"

MEDIA_CONTROL="$PLUGIN_DIR/media_control.sh"

sketchybar \
  --add item media center                          \
  --set media                                      \
    icon.drawing=off                               \
    icon.background.drawing=on                     \
    icon.background.image="media.artwork"          \
    icon.background.image.scale=0.65               \
    icon.background.color=0x00000000               \
    icon.background.corner_radius=4                \
    icon.width=28                                  \
    label.color=$MOCHA_MAUVE                       \
    label.max_chars=35                             \
    label.padding_left=6                           \
    label.padding_right=8                          \
    scroll_texts=on                                \
    background.color=$ITEM_BG_COLOR                \
    background.corner_radius=6                     \
    background.height=26                           \
    popup.align=center                             \
    drawing=off                                    \
    script="$PLUGIN_DIR/media.sh"                  \
    click_script="sketchybar --set media popup.drawing=toggle" \
  --subscribe media media_change mouse.clicked     \
  \
  --add item media.prev popup.media               \
  --set media.prev                                \
    icon=""                                      \
    icon.font="Hack Nerd Font:Bold:16.0"          \
    icon.color=$MOCHA_SUBTEXT1                    \
    label.drawing=off                             \
    background.drawing=off                        \
    click_script="$MEDIA_CONTROL previous"        \
  \
  --add item media.playpause popup.media          \
  --set media.playpause                           \
    icon=""                                      \
    icon.font="Hack Nerd Font:Bold:18.0"          \
    icon.color=$MOCHA_MAUVE                       \
    label.drawing=off                             \
    background.drawing=off                        \
    click_script="$MEDIA_CONTROL playpause"       \
  \
  --add item media.next popup.media               \
  --set media.next                                \
    icon=""                                      \
    icon.font="Hack Nerd Font:Bold:16.0"          \
    icon.color=$MOCHA_SUBTEXT1                    \
    label.drawing=off                             \
    background.drawing=off                        \
    click_script="$MEDIA_CONTROL next"
