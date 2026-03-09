#!/usr/bin/env bash

CORE_COUNT=$(sysctl -n machdep.cpu.thread_count)
MY_UID=$(id -u)
CPU_INFO=$(ps -eo pcpu,uid)
CPU_SYS=$(echo "$CPU_INFO"  | awk -v uid="$MY_UID" -v c="$CORE_COUNT" '$2 != uid {sum+=$1} END {printf "%.4f", sum/(100.0*c)}')
CPU_USER=$(echo "$CPU_INFO" | awk -v uid="$MY_UID" -v c="$CORE_COUNT" '$2 == uid {sum+=$1} END {printf "%.4f", sum/(100.0*c)}')
CPU_PERCENT="$(echo "$CPU_SYS $CPU_USER" | awk '{printf "%.0f\n", ($1 + $2)*100}')"

sketchybar --set "$NAME" label="${CPU_PERCENT}%"
