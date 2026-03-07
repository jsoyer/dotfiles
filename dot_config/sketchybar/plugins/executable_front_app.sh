#!/bin/sh

if [ "$SENDER" = "front_app_switched" ]; then
  sketchybar --set $NAME label="$INFO" icon.background.image="app.$INFO" \
             --set $NAME icon.background.image.scale=0.8 \
                         icon.background.image.scale=0.8
fi
