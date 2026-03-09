#!/usr/bin/env bash

MEM_USED=$(memory_pressure | grep "System-wide memory free percentage:" \
  | awk '{ sub(/%/,"", $5); printf("%02.0f\n", 100-$5) }')

sketchybar --set "$NAME" label="${MEM_USED}%"
