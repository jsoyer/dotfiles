#!/bin/bash
# Claude Code Statusline — Noxys Edition v4
# Auto palette (Catppuccin Mocha / Snazzy) · OAuth fallback · single git call
set -f

input=$(cat)

if [ -z "$input" ]; then
  printf "Claude"
  exit 0
fi

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Color Palette — auto-detect SSH vs local
#  Local/Desktop → Catppuccin Mocha
#  SSH           → Snazzy
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

RST=$'\033[0m'
BOLD=$'\033[1m'
DIM=$'\033[2m'
BLINK=$'\033[5m'

if [ -n "$SSH_TTY" ] || [ -n "$SSH_CONNECTION" ] || [ -n "$SSH_CLIENT" ]; then
  # ── Snazzy ───────────────────────────────────────────
  MAUVE=$'\033[38;2;255;106;193m'     # #ff6ac1
  RED=$'\033[38;2;255;85;85m'         # #ff5555
  PEACH=$'\033[38;2;255;159;67m'      # #ff9f43
  YELLOW=$'\033[38;2;243;249;157m'    # #f3f99d
  GREEN=$'\033[38;2;90;247;142m'      # #5af78e
  TEAL=$'\033[38;2;154;237;254m'      # #9aedfe
  SKY=$'\033[38;2;154;237;254m'       # #9aedfe
  SAPPHIRE=$'\033[38;2;87;199;255m'   # #57c7ff
  BLUE=$'\033[38;2;87;199;255m'       # #57c7ff
  LAVENDER=$'\033[38;2;255;106;193m'  # #ff6ac1
  PINK=$'\033[38;2;255;106;193m'      # #ff6ac1
  FLAMINGO=$'\033[38;2;255;159;67m'   # #ff9f43
  ROSEWATER=$'\033[38;2;239;239;239m' # #efefef
  TEXT=$'\033[38;2;239;239;239m'      # #efefef
  SUBTEXT=$'\033[38;2;184;184;184m'   # #b8b8b8
  OVERLAY=$'\033[38;2;120;120;120m'   # #787878
  SURFACE=$'\033[38;2;68;68;68m'      # #444444
else
  # ── Catppuccin Mocha ─────────────────────────────────
  MAUVE=$'\033[38;2;203;166;247m'     # #cba6f7
  RED=$'\033[38;2;243;139;168m'       # #f38ba8
  PEACH=$'\033[38;2;250;179;135m'     # #fab387
  YELLOW=$'\033[38;2;249;226;175m'    # #f9e2af
  GREEN=$'\033[38;2;166;227;161m'     # #a6e3a1
  TEAL=$'\033[38;2;148;226;213m'      # #94e2d5
  SKY=$'\033[38;2;137;220;235m'       # #89dceb
  SAPPHIRE=$'\033[38;2;116;199;236m'  # #74c7ec
  BLUE=$'\033[38;2;137;180;250m'      # #89b4fa
  LAVENDER=$'\033[38;2;180;190;254m'  # #b4befe
  PINK=$'\033[38;2;245;194;231m'      # #f5c2e7
  FLAMINGO=$'\033[38;2;242;205;205m'  # #f2cdcd
  ROSEWATER=$'\033[38;2;245;224;220m' # #f5e0dc
  TEXT=$'\033[38;2;205;214;244m'      # #cdd6f4
  SUBTEXT=$'\033[38;2;166;173;200m'   # #a6adc8
  OVERLAY=$'\033[38;2;108;112;134m'   # #6c7086
  SURFACE=$'\033[38;2;69;71;90m'      # #45475a
fi

SEP="  ${SURFACE}│${RST}  "

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  JSON extraction (single jq call)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

read_json() {
  echo "$input" | jq -r '[
    (.model.display_name // "Claude"),
    (.workspace.current_dir // ""),
    (.session_name // ""),
    (.agent.name // ""),
    (.output_style.name // ""),
    (.vim.mode // ""),
    (.worktree.name // ""),
    (.worktree.branch // ""),
    (.context_window.used_percentage // 0 | tostring | split(".")[0]),
    (.context_window.context_window_size // 200000),
    (.context_window.current_usage.input_tokens // 0),
    (.context_window.current_usage.cache_creation_input_tokens // 0),
    (.context_window.current_usage.cache_read_input_tokens // 0),
    (.cost.total_cost_usd // 0),
    (.cost.total_duration_ms // 0 | tostring | split(".")[0]),
    (.cost.total_api_duration_ms // 0 | tostring | split(".")[0]),
    (.cost.total_lines_added // 0),
    (.cost.total_lines_removed // 0),
    (.rate_limits.five_hour.used_percentage // ""),
    (.rate_limits.seven_day.used_percentage // ""),
    (.rate_limits.five_hour.resets_at // ""),
    (.cost.total_turns // 0)
  ] | @tsv'
}

IFS=$'\t' read -r MODEL DIR SESSION_NAME AGENT OUTPUT_STYLE VIM_MODE \
  WORKTREE WORKTREE_BRANCH PCT CTX_SIZE INPUT_TOKENS CACHE_CREATE CACHE_READ \
  COST DURATION_MS API_MS LINES_ADD LINES_DEL RATE_5H RATE_7D RESET_5H \
  TURNS \
  <<< "$(read_json)"

PCT=${PCT:-0};             CTX_SIZE=${CTX_SIZE:-200000}
INPUT_TOKENS=${INPUT_TOKENS:-0}
CACHE_CREATE=${CACHE_CREATE:-0}
CACHE_READ=${CACHE_READ:-0}
DURATION_MS=${DURATION_MS:-0};  API_MS=${API_MS:-0}
LINES_ADD=${LINES_ADD:-0};      LINES_DEL=${LINES_DEL:-0}
TURNS=${TURNS:-0}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Helpers
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

fmt_tokens() {
  local n=$1
  if   [ "$n" -ge 1000000 ]; then awk "BEGIN{printf \"%.1fM\",$n/1000000}"
  elif [ "$n" -ge 1000 ];    then awk "BEGIN{printf \"%.0fk\",$n/1000}"
  else printf "%d" "$n"; fi
}

pct_color() {
  local v=${1%.*}
  if   [ "$v" -ge 90 ]; then printf '%s' "$RED"
  elif [ "$v" -ge 70 ]; then printf '%s' "$PEACH"
  elif [ "$v" -ge 50 ]; then printf '%s' "$YELLOW"
  else                        printf '%s' "$GREEN"; fi
}

pct_emoji() {
  local v=${1%.*}
  if   [ "$v" -ge 90 ]; then printf '🔴'
  elif [ "$v" -ge 70 ]; then printf '🟠'
  elif [ "$v" -ge 50 ]; then printf '🟡'
  else                        printf '🟢'; fi
}

build_bar() {
  local pct=$1 width=${2:-10}
  [ "$pct" -lt 0 ]   2>/dev/null && pct=0
  [ "$pct" -gt 100 ] 2>/dev/null && pct=100
  local filled=$((pct * width / 100))
  local empty=$((width - filled))
  local bc
  bc=$(pct_color "$pct")
  local f="" e=""
  for ((i = 0; i < filled; i++)); do f+="●"; done
  for ((i = 0; i < empty;  i++)); do e+="○"; done
  printf "${bc}${f}${SURFACE}${e}${RST}"
}

iso_to_epoch() {
  local iso=$1
  local epoch
  # GNU date (Linux)
  epoch=$(date -d "$iso" +%s 2>/dev/null)
  if [ -n "$epoch" ]; then echo "$epoch"; return 0; fi
  # BSD date (macOS)
  local stripped="${iso%%.*}"; stripped="${stripped%%Z}"
  stripped="${stripped%%+*}"; stripped="${stripped%%-[0-9][0-9]:[0-9][0-9]}"
  if [[ "$iso" == *"Z"* ]] || [[ "$iso" == *"+00:00"* ]] || [[ "$iso" == *"-00:00"* ]]; then
    epoch=$(env TZ=UTC date -j -f "%Y-%m-%dT%H:%M:%S" "$stripped" +%s 2>/dev/null)
  else
    epoch=$(date -j -f "%Y-%m-%dT%H:%M:%S" "$stripped" +%s 2>/dev/null)
  fi
  if [ -n "$epoch" ]; then echo "$epoch"; return 0; fi
  return 1
}

time_until() {
  local ts=$1 now diff h m
  now=$(date +%s); diff=$((ts - now))
  [ "$diff" -le 0 ] && echo "now" && return
  h=$((diff / 3600)); m=$(( (diff % 3600) / 60 ))
  [ "$h" -gt 0 ] && echo "${h}h${m}m" || echo "${m}m"
}

fmt_duration() {
  local ms=$1
  [ "$ms" -le 0 ] && echo "0s" && return
  local s=$((ms / 1000)) h m
  h=$((s / 3600)); m=$(( (s % 3600) / 60 )); s=$((s % 60))
  if   [ "$h" -gt 0 ]; then echo "${h}h${m}m"
  elif [ "$m" -gt 0 ]; then echo "${m}m${s}s"
  else                       echo "${s}s"; fi
}

fmt_reset_time() {
  local iso=$1 style=$2
  [ -z "$iso" ] || [ "$iso" = "null" ] && return
  local epoch
  epoch=$(iso_to_epoch "$iso")
  [ -z "$epoch" ] && return
  case "$style" in
    time)
      date -d "@$epoch" +"%H:%M" 2>/dev/null || \
      date -j -r "$epoch" +"%l:%M%p" 2>/dev/null | sed 's/^ //; s/\.//g' | tr '[:upper:]' '[:lower:]'
      ;;
    datetime)
      date -d "@$epoch" +"%b %-d %H:%M" 2>/dev/null || \
      date -j -r "$epoch" +"%b %-d, %l:%M%p" 2>/dev/null | sed 's/  / /g; s/^ //; s/\.//g' | tr '[:upper:]' '[:lower:]'
      ;;
    *)
      date -d "@$epoch" +"%b %-d" 2>/dev/null || \
      date -j -r "$epoch" +"%b %-d" 2>/dev/null | tr '[:upper:]' '[:lower:]'
      ;;
  esac
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  OAuth token resolution (for rate limit fallback)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

get_oauth_token() {
  if [ -n "$CLAUDE_CODE_OAUTH_TOKEN" ]; then
    echo "$CLAUDE_CODE_OAUTH_TOKEN"; return 0
  fi
  if command -v security >/dev/null 2>&1; then
    local blob
    blob=$(security find-generic-password -s "Claude Code-credentials" -w 2>/dev/null)
    if [ -n "$blob" ]; then
      local t
      t=$(echo "$blob" | jq -r '.claudeAiOauth.accessToken // empty' 2>/dev/null)
      [ -n "$t" ] && [ "$t" != "null" ] && { echo "$t"; return 0; }
    fi
  fi
  local creds="${HOME}/.claude/.credentials.json"
  if [ -f "$creds" ]; then
    local t
    t=$(jq -r '.claudeAiOauth.accessToken // empty' "$creds" 2>/dev/null)
    [ -n "$t" ] && [ "$t" != "null" ] && { echo "$t"; return 0; }
  fi
  if command -v secret-tool >/dev/null 2>&1; then
    local blob
    blob=$(timeout 2 secret-tool lookup service "Claude Code-credentials" 2>/dev/null)
    if [ -n "$blob" ]; then
      local t
      t=$(echo "$blob" | jq -r '.claudeAiOauth.accessToken // empty' 2>/dev/null)
      [ -n "$t" ] && [ "$t" != "null" ] && { echo "$t"; return 0; }
    fi
  fi
  echo ""
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  OAuth usage API — async background refresh
#  Always returns instantly (stale cache or empty)
#  Triggers background curl when cache is expired
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

OAUTH_CACHE_DIR="/tmp/claude"
OAUTH_CACHE_FILE="${OAUTH_CACHE_DIR}/statusline-usage-cache.json"
OAUTH_CACHE_LOCK="${OAUTH_CACHE_DIR}/statusline-usage.lock"
OAUTH_CACHE_MAX_AGE=60

fetch_usage_data() {
  mkdir -p "$OAUTH_CACHE_DIR"
  local usage_data="" needs_refresh=true

  if [ -f "$OAUTH_CACHE_FILE" ]; then
    local mtime now age
    mtime=$(stat -c %Y "$OAUTH_CACHE_FILE" 2>/dev/null || stat -f %m "$OAUTH_CACHE_FILE" 2>/dev/null)
    now=$(date +%s); age=$((now - mtime))
    usage_data=$(cat "$OAUTH_CACHE_FILE" 2>/dev/null)
    [ "$age" -lt "$OAUTH_CACHE_MAX_AGE" ] && needs_refresh=false
  fi

  if $needs_refresh && [ ! -f "$OAUTH_CACHE_LOCK" ]; then
    touch "$OAUTH_CACHE_LOCK"
    (
      token=$(get_oauth_token)
      if [ -n "$token" ] && [ "$token" != "null" ]; then
        resp=$(curl -s --max-time 5 \
          -H "Accept: application/json" \
          -H "Content-Type: application/json" \
          -H "Authorization: Bearer $token" \
          -H "anthropic-beta: oauth-2025-04-20" \
          "https://api.anthropic.com/api/oauth/usage" 2>/dev/null)
        if [ -n "$resp" ] && echo "$resp" | jq -e '.five_hour' >/dev/null 2>&1; then
          echo "$resp" > "$OAUTH_CACHE_FILE"
        fi
      fi
      rm -f "$OAUTH_CACHE_LOCK"
    ) &
    disown
  fi

  echo "$usage_data"
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Computed values
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

REPO="${DIR##*/}"
DISPLAY="${SESSION_NAME:-$REPO}"
USED_TOKENS=$((INPUT_TOKENS + CACHE_CREATE + CACHE_READ))
REMAINING=$((CTX_SIZE - USED_TOKENS))
DURATION_STR=$(fmt_duration "$DURATION_MS")
NOW_TIME=$(date +"%H:%M")

# Git — single call: branch + staged + unstaged + last commit ts
BRANCH="$WORKTREE_BRANCH"
STAGED=0; UNSTAGED=0; LAST_COMMIT_TS=""

if [ -n "$DIR" ] && [ -d "$DIR" ]; then
  GIT_RAW=$(timeout 1 git -C "$DIR" status --porcelain -b 2>/dev/null)
  if [ -n "$GIT_RAW" ]; then
    [ -z "$BRANCH" ] && BRANCH=$(head -1 <<< "$GIT_RAW" | sed 's/^## //; s/\.\.\..*//')
    STAGED=$(grep -c '^[MADRC]' <<< "$GIT_RAW" || true)
    UNSTAGED=$(grep -c '^.[MADRC?]' <<< "$GIT_RAW" || true)
    LAST_COMMIT_TS=$(timeout 1 git -C "$DIR" log -1 --format="%ct" 2>/dev/null)
  fi
fi

# Cache ratio
CACHE_TOTAL=$((CACHE_READ + CACHE_CREATE)); CACHE_PCT=0
[ "$CACHE_TOTAL" -gt 0 ] && CACHE_PCT=$((CACHE_READ * 100 / CACHE_TOTAL))

# Health score
HEALTH=100
[ "$PCT" -ge 80 ] && HEALTH=$((HEALTH - 30))
[ "$PCT" -ge 60 ] && [ "$PCT" -lt 80 ] && HEALTH=$((HEALTH - 15))
[ "$PCT" -ge 40 ] && [ "$PCT" -lt 60 ] && HEALTH=$((HEALTH - 5))
if [ "$CACHE_TOTAL" -gt 1000 ]; then
  [ "$CACHE_PCT" -lt 20 ] && HEALTH=$((HEALTH - 20))
  [ "$CACHE_PCT" -ge 20 ] && [ "$CACHE_PCT" -lt 40 ] && HEALTH=$((HEALTH - 10))
fi
if [ -n "$RATE_5H" ]; then
  R5I=${RATE_5H%.*}
  [ "$R5I" -ge 80 ] && HEALTH=$((HEALTH - 20))
  [ "$R5I" -ge 50 ] && [ "$R5I" -lt 80 ] && HEALTH=$((HEALTH - 10))
fi

if   [ "$HEALTH" -ge 90 ]; then GRADE="S";  GC=$GREEN;    GRADE_EMOJI="🏆"
elif [ "$HEALTH" -ge 80 ]; then GRADE="A";  GC=$GREEN;    GRADE_EMOJI="✨"
elif [ "$HEALTH" -ge 70 ]; then GRADE="B+"; GC=$TEAL;     GRADE_EMOJI="👍"
elif [ "$HEALTH" -ge 60 ]; then GRADE="B";  GC=$SKY;      GRADE_EMOJI="👌"
elif [ "$HEALTH" -ge 50 ]; then GRADE="C";  GC=$YELLOW;   GRADE_EMOJI="⚡"
elif [ "$HEALTH" -ge 40 ]; then GRADE="D";  GC=$PEACH;    GRADE_EMOJI="⚠️"
else                             GRADE="F";  GC=$RED;      GRADE_EMOJI="🔥"; fi

# Thinking status
THINKING_ON=false
[ -f "$HOME/.claude/settings.json" ] && \
  [ "$(jq -r '.alwaysThinkingEnabled // false' "$HOME/.claude/settings.json" 2>/dev/null)" = "true" ] && \
  THINKING_ON=true

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  LINE 1 — Identity
#  🔮 Opus 4.6  │  📂 myrepo   main +2 ~1  │  ⏱ 12m  14:30  │  💬 8  │  🧠 on
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

L1="${MAUVE}🔮 ${BOLD}${MODEL}${RST}"

# Directory + git
L1+="${SEP}${BLUE}📂 ${BOLD}${DISPLAY}${RST}"
[ -n "$WORKTREE" ] && L1+="  ${TEAL}⑂ ${WORKTREE}${RST}"

if [ -n "$BRANCH" ]; then
  case "$BRANCH" in
    main|master|production|prod|release*)
      L1+="  ${RED}🛡️ ${BOLD}${BRANCH}${RST}" ;;
    *)
      L1+="  ${GREEN} ${BRANCH}${RST}" ;;
  esac
  [ "$STAGED"   -gt 0 ] && L1+=" ${GREEN}+${STAGED}${RST}"
  [ "$UNSTAGED" -gt 0 ] && L1+=" ${PEACH}~${UNSTAGED}${RST}"
fi

# Agent / Vim / Style (conditional)
[ -n "$AGENT" ] && L1+="${SEP}${PINK}🤖 ${AGENT}${RST}"
if [ -n "$VIM_MODE" ]; then
  case "$VIM_MODE" in
    NORMAL)  L1+="  ${SUBTEXT}[N]${RST}" ;;
    INSERT)  L1+="  ${GREEN}[I]${RST}" ;;
    VISUAL)  L1+="  ${MAUVE}[V]${RST}" ;;
    *)       L1+="  ${OVERLAY}[${VIM_MODE}]${RST}" ;;
  esac
fi
[ -n "$OUTPUT_STYLE" ] && [ "$OUTPUT_STYLE" != "default" ] && \
  L1+="  ${SUBTEXT}(${OUTPUT_STYLE})${RST}"

# Duration + clock
L1+="${SEP}${FLAMINGO}⏱  ${BOLD}${DURATION_STR}${RST}  ${OVERLAY}${NOW_TIME}${RST}"

# Turns
[ "$TURNS" -gt 0 ] && L1+="${SEP}${SAPPHIRE}💬 ${TURNS}${RST}"

# Thinking toggle
if $THINKING_ON; then
  L1+="${SEP}${MAUVE}🧠 on${RST}"
else
  L1+="${SEP}${OVERLAY}🧠 off${RST}"
fi

echo -e "$L1"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  LINE 2 — Context & Metrics
#  🟢 ●●●●○○○○○○○○ 42%  156k/1.0M  │  💰 $0.12  │  ✏️ +120 / -34  │  📦 87%  │  🏆 S
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CTX_BAR=$(build_bar "$PCT" 12)
CTX_CLR=$(pct_color "$PCT")
CTX_DOT=$(pct_emoji "$PCT")
USED_FMT=$(fmt_tokens "$USED_TOKENS")
TOTAL_FMT=$(fmt_tokens "$CTX_SIZE")

L2="${CTX_DOT} ${CTX_BAR}  ${CTX_CLR}${BOLD}${PCT}%${RST}  ${OVERLAY}${USED_FMT}/${TOTAL_FMT}${RST}"

# Context alert — pick the single most urgent one
CTX_ALERT=""
if [ "$DURATION_MS" -gt 120000 ] && [ "$PCT" -gt 10 ] && [ "$USED_TOKENS" -gt 0 ]; then
  TPM=$(awk "BEGIN{printf \"%.0f\",$USED_TOKENS/($DURATION_MS/60000)}")
  if [ -n "$TPM" ] && [ "$TPM" -gt 0 ]; then
    MINS=$(awk "BEGIN{printf \"%.0f\",$REMAINING/$TPM}")
  fi
fi

if [ "$PCT" -ge 80 ]; then
  if [ -n "$MINS" ] && [ "${MINS:-99}" -le 10 ]; then
    CTX_ALERT="  ${BLINK}${RED}⚡ /compact! ~${MINS}m${RST}"
  else
    CTX_ALERT="  ${BLINK}${RED}⚡ /compact!${RST}"
  fi
elif [ "$REMAINING" -lt 20000 ] && [ "$USED_TOKENS" -gt 0 ]; then
  RK=$((REMAINING / 1000))
  CTX_ALERT="  ${RED}⚠️  ~${RK}k left${RST}"
elif [ -n "$MINS" ] && [ "${MINS:-99}" -le 10 ]; then
  CTX_ALERT="  ${RED}🕐 full ~${MINS}m${RST}"
elif [ "$PCT" -ge 60 ]; then
  CTX_ALERT="  ${PEACH}💡 /compact${RST}"
elif [ "$REMAINING" -lt 50000 ] && [ "$USED_TOKENS" -gt 0 ]; then
  RK=$((REMAINING / 1000))
  CTX_ALERT="  ${YELLOW}~${RK}k left${RST}"
elif [ -n "$MINS" ] && [ "${MINS:-99}" -le 30 ]; then
  CTX_ALERT="  ${YELLOW}🕐 ~${MINS}m${RST}"
fi

L2+="$CTX_ALERT"

# Cost
L2+="${SEP}${ROSEWATER}💰 \$$(printf '%.4f' "$COST")${RST}"

# Lines changed
L2+="${SEP}${GREEN}✏️  +${LINES_ADD}${RST} ${OVERLAY}/${RST} ${RED}-${LINES_DEL}${RST}"

# Cache hit ratio
if   [ "$CACHE_PCT" -ge 70 ]; then CC=$GREEN
elif [ "$CACHE_PCT" -ge 30 ]; then CC=$YELLOW
else                                CC=$RED; fi
L2+="${SEP}${CC}📦 ${CACHE_PCT}%${RST}"

# Health grade
L2+="${SEP}${GC}${BOLD}${GRADE_EMOJI} ${GRADE}${RST}"

echo -e "$L2"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  LINE 3 — Rate limits (JSON primary, OAuth API fallback)
#  ⚡ current  ●●●○○○○○  30%  ⟳ 2h15m  │  📅 weekly  ●●○○○○○○  18%
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

HAS_RATES=false
L3=""

# ── Source 1: Claude Code JSON rate_limits ─────────────
if [ -n "$RATE_5H" ] || [ -n "$RATE_7D" ]; then

  if [ -n "$RATE_5H" ]; then
    HAS_RATES=true
    R5I=${RATE_5H%.*}
    L3+="${LAVENDER}⚡ current${RST}  $(build_bar "$R5I" 8)  $(pct_color "$R5I")${BOLD}${R5I}%${RST}"
    if [ -n "$RESET_5H" ] && [ "$R5I" -ge 40 ]; then
      L3+="  ${OVERLAY}⟳${RST} ${TEXT}$(time_until "$RESET_5H")${RST}"
    fi
  fi

  if [ -n "$RATE_7D" ]; then
    R7I=${RATE_7D%.*}
    if [ "$R7I" -ge 10 ]; then
      HAS_RATES=true
      [ -n "$L3" ] && L3+="${SEP}"
      L3+="${SKY}📅 weekly${RST}   $(build_bar "$R7I" 8)  $(pct_color "$R7I")${BOLD}${R7I}%${RST}"
    fi
  fi

# ── Source 2: OAuth API fallback (async, cached) ───────
else
  USAGE_DATA=$(fetch_usage_data)

  if [ -n "$USAGE_DATA" ] && echo "$USAGE_DATA" | jq -e '.five_hour' >/dev/null 2>&1; then

    FIVE_PCT=$(echo "$USAGE_DATA" | jq -r '.five_hour.utilization // 0' | awk '{printf "%.0f", $1}')
    FIVE_RESET_ISO=$(echo "$USAGE_DATA" | jq -r '.five_hour.resets_at // empty')
    FIVE_RESET=$(fmt_reset_time "$FIVE_RESET_ISO" "time")

    HAS_RATES=true
    L3+="${LAVENDER}⚡ current${RST}  $(build_bar "$FIVE_PCT" 8)  $(pct_color "$FIVE_PCT")${BOLD}$(printf '%3d' "$FIVE_PCT")%${RST}"
    [ -n "$FIVE_RESET" ] && L3+="  ${OVERLAY}⟳${RST} ${TEXT}${FIVE_RESET}${RST}"

    SEVEN_PCT=$(echo "$USAGE_DATA" | jq -r '.seven_day.utilization // 0' | awk '{printf "%.0f", $1}')
    SEVEN_RESET_ISO=$(echo "$USAGE_DATA" | jq -r '.seven_day.resets_at // empty')
    SEVEN_RESET=$(fmt_reset_time "$SEVEN_RESET_ISO" "datetime")

    L3+="${SEP}"
    L3+="${SKY}📅 weekly${RST}   $(build_bar "$SEVEN_PCT" 8)  $(pct_color "$SEVEN_PCT")${BOLD}$(printf '%3d' "$SEVEN_PCT")%${RST}"
    [ -n "$SEVEN_RESET" ] && L3+="  ${OVERLAY}⟳${RST} ${TEXT}${SEVEN_RESET}${RST}"

    EXTRA_ENABLED=$(echo "$USAGE_DATA" | jq -r '.extra_usage.is_enabled // false')
    if [ "$EXTRA_ENABLED" = "true" ]; then
      EXTRA_PCT=$(echo "$USAGE_DATA" | jq -r '.extra_usage.utilization // 0' | awk '{printf "%.0f", $1}')
      EXTRA_USED=$(echo "$USAGE_DATA" | jq -r '.extra_usage.used_credits // 0' | awk '{printf "%.2f", $1/100}')
      EXTRA_LIMIT=$(echo "$USAGE_DATA" | jq -r '.extra_usage.monthly_limit // 0' | awk '{printf "%.2f", $1/100}')

      L3+="\n${PINK}💳 extra${RST}    $(build_bar "$EXTRA_PCT" 8)  $(pct_color "$EXTRA_PCT")${BOLD}\$${EXTRA_USED}${RST}${OVERLAY} / \$${EXTRA_LIMIT}${RST}"
    fi
  fi
fi

# ── Uncommitted time ───────────────────────────────────
if [ -n "$LAST_COMMIT_TS" ] && [ "$LAST_COMMIT_TS" -gt 0 ]; then
  SINCE_H=$(( ($(date +%s) - LAST_COMMIT_TS) / 3600 ))
  if [ "$SINCE_H" -ge 2 ]; then
    HAS_RATES=true
    [ -n "$L3" ] && L3+="${SEP}"
    L3+="${RED}📝 ${SINCE_H}h sans commit${RST}"
  elif [ "$SINCE_H" -ge 1 ]; then
    HAS_RATES=true
    [ -n "$L3" ] && L3+="${SEP}"
    L3+="${PEACH}📝 1h sans commit${RST}"
  fi
fi

$HAS_RATES && echo -e "$L3"
