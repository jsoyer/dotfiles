#!/usr/bin/env bash
# fleet-agent — Unix agent of the fleet-updates system (Linux, macOS).
#
# Installed root:root 0755 as /usr/local/libexec/fleet-agent by
# .chezmoiscripts/03-configure/run_onchange_install-fleet-agent.sh.tmpl and
# referenced ONLY by the forced command of the masters' authorized_keys line:
#
#   restrict,command="/usr/local/libexec/fleet-agent" ssh-ed25519 AAAA... fleet-master-<master>
#
# sshd puts what the master asked for in SSH_ORIGINAL_COMMAND. It is UNTRUSTED:
# only one of five verbs, alone, is accepted. Anything else (unknown verb, extra
# argument, empty = interactive shell attempt) exits 1, logs the refusal and
# runs nothing.
#
#   check          read-only: pending updates, health, reboot state
#   update         start a DETACHED update (systemd-run --user / nohup); returns
#                  status "started" + job id at once, an SSH cut cannot stop it
#   reboot-status  is a reboot required (needs-restarting / reboot-required /
#                  newer kernel installed)
#   reboot         reboot only if required (sudo exact command, see sudoers)
#   report         final (or current) state of the last update job, read from disk
#
# Output: exactly one JSON line, schema v1 (docs/tasks/.../spec.md section 12).
# Exit codes: 0 success, 1 refused, 2 update failed, 3 busy.
#
# The process runs as the SSH account; root only comes from exact sudoers
# commands. This file never takes free-form arguments.
#
# Test hooks: FLEET_AGENT_* environment variables (state dir, lock dir, sysup
# path, etc dir, ...) override defaults, but ONLY when FLEET_AGENT_TEST=1. In the
# forced-command path (SSH_ORIGINAL_COMMAND or SSH_CONNECTION set) without that
# flag they are all unset at startup, so an inherited variable can never swap an
# executed binary or a decision input (defence in depth: sshd with `restrict`
# and no PermitUserEnvironment already gives the client no way to set them).
#
# Must run on stock macOS bash 3.2: no associative arrays, no mapfile, no
# ${var,,}, empty arrays guarded.

set -u
umask 077

# Production hardening: drop every FLEET_AGENT_* override in an SSH context
# unless the explicit test flag is on. FLEET_AGENT_JOB_ID is kept here so main()
# can refuse it explicitly (and log it) instead of silently ignoring it.
if [ "${FLEET_AGENT_TEST:-}" != 1 ] && [ -n "${SSH_ORIGINAL_COMMAND+x}${SSH_CONNECTION+x}" ]; then
  for _fa_var in $(env | sed -n 's/^\(FLEET_AGENT_[A-Za-z0-9_]*\)=.*/\1/p'); do
    [ "$_fa_var" = FLEET_AGENT_JOB_ID ] || unset "$_fa_var"
  done
  unset _fa_var
fi
CLIENT_IP="${SSH_CONNECTION:-none}"
CLIENT_IP="${CLIENT_IP%% *}"

# Appended (never prepended): a detached/minimal environment still finds tools.
PATH="${PATH:-/usr/bin:/bin}:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:${HOME:-/nonexistent}/.local/bin:/home/linuxbrew/.linuxbrew/bin:/opt/homebrew/bin"
export PATH

AGENT_PATH="$0"
case "$AGENT_PATH" in
  /*) ;;
  *) AGENT_PATH="$(cd "$(dirname "$AGENT_PATH")" 2>/dev/null && pwd)/$(basename "$AGENT_PATH")" ;;
esac

OS_KERNEL="$(uname -s)"
STATE_DIR="${FLEET_AGENT_STATE_DIR:-${XDG_STATE_HOME:-${HOME:-/tmp}/.local/state}/fleet-agent}"
LOCK_BASE="${FLEET_AGENT_LOCK_DIR:-$STATE_DIR}"
LOCKDIR="$LOCK_BASE/update.lock"
JOBS_DIR="$STATE_DIR/jobs"
SYSUP="${FLEET_AGENT_SYSUP:-${HOME:-/nonexistent}/.local/bin/sysup}"
ETC_DIR="${FLEET_AGENT_ETC_DIR:-/etc}"
CRITICAL_FILE="${FLEET_AGENT_CRITICAL_FILE:-${HOME:-/nonexistent}/.config/fleet-agent/critical-services}"
REBOOT_FLAG="${FLEET_AGENT_REBOOT_FLAG:-/var/run/reboot-required}"
MODULES_DIR="${FLEET_AGENT_MODULES_DIR:-/usr/lib/modules}"
POWER_DIR="${FLEET_AGENT_POWER_DIR:-/sys/class/power_supply}"
OS_RELEASE="${FLEET_AGENT_OS_RELEASE:-/etc/os-release}"
HOST="${FLEET_AGENT_HOST:-$(hostname -s 2>/dev/null || uname -n)}"
REBOOT_DELAY="${FLEET_AGENT_REBOOT_DELAY:-3}"
case "$REBOOT_DELAY" in *[!0-9]*|"") REBOOT_DELAY=3 ;; esac
TAB="$(printf '\t')"

# Environment variables handed to the detached job (systemd --user units do not
# inherit the caller's environment).
PASSTHROUGH_VARS="PATH FLEET_AGENT_STATE_DIR FLEET_AGENT_LOCK_DIR FLEET_AGENT_SYSUP FLEET_AGENT_ETC_DIR FLEET_AGENT_CRITICAL_FILE FLEET_AGENT_REBOOT_FLAG FLEET_AGENT_MODULES_DIR FLEET_AGENT_POWER_DIR FLEET_AGENT_OS_RELEASE FLEET_AGENT_HOST FLEET_AGENT_PKGMGR FLEET_AGENT_KERNEL FLEET_AGENT_LOG_FILE FLEET_AGENT_REBOOT_DELAY FLEET_AGENT_TEST"

# ---------------------------------------------------------------- utilities

now() { date -u +%Y-%m-%dT%H:%M:%SZ; }

# One printable line, bounded: untrusted text goes through this before logging.
sanitize_line() {
  printf '%s' "$1" | LC_ALL=C tr -cd '[:print:]' | cut -c1-200
}

log_file_target() {
  if [ -n "${FLEET_AGENT_LOG_FILE:-}" ]; then
    printf '%s' "$FLEET_AGENT_LOG_FILE"
  elif [ "$OS_KERNEL" = Darwin ]; then
    printf '%s' /var/log/fleet-agent.log
  fi
}

# log <priority> <message>: journald via logger on Linux, a log file on macOS.
log() {
  local prio="$1" msg target
  msg="$(sanitize_line "$2")"
  target="$(log_file_target)"
  if [ -n "$target" ]; then
    printf '%s fleet-agent[%s]: %s\n' "$(now)" "$$" "$msg" >>"$target" 2>/dev/null && return 0
    mkdir -p "$STATE_DIR" 2>/dev/null
    printf '%s fleet-agent[%s]: %s\n' "$(now)" "$$" "$msg" >>"$STATE_DIR/agent.log" 2>/dev/null
    return 0
  fi
  if command -v logger >/dev/null 2>&1; then
    logger -t fleet-agent -p "$prio" -- "$msg" 2>/dev/null && return 0
  fi
  mkdir -p "$STATE_DIR" 2>/dev/null
  printf '%s fleet-agent[%s]: %s\n' "$(now)" "$$" "$msg" >>"$STATE_DIR/agent.log" 2>/dev/null
  return 0
}

# json_str <text>: JSON string literal (quotes included), control chars dropped.
json_str() {
  printf '%s' "$1" \
    | LC_ALL=C tr -d '\000-\010\013-\037\177' \
    | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g' -e "s/$TAB/\\\\t/g" \
    | awk 'BEGIN { ORS = ""; printf "\"" } { if (NR > 1) printf "\\n"; printf "%s", $0 } END { printf "\"" }'
}

# json_str_or_null <text>: null when empty.
json_str_or_null() {
  if [ -z "$1" ]; then printf 'null'; else json_str "$1"; fi
}

# list_json <file>: one JSON string per line of the file, as an array.
list_json() {
  local line first=1
  printf '['
  if [ -s "$1" ]; then
    while IFS= read -r line; do
      [ -n "$line" ] || continue
      if [ "$first" = 1 ]; then first=0; else printf ','; fi
      json_str "$line"
    done <"$1"
  fi
  printf ']'
}

# mask_secrets: stdin -> stdout, ANSI stripped and secrets masked (log_tail).
# 1. awk state machine: a whole PEM private key block (BEGIN..END, any number of
#    lines) collapses to one marker; an END without BEGIN (tail cut the block)
#    masks the marker and long base64-only lines.
# 2. sed: token / JWT / AWS key id / URL credentials.
# 3. awk: whole lines carrying a password-like assignment or flag.
mask_secrets() {
  local esc
  esc="$(printf '\033')"
  sed -E "s/${esc}\\[[0-9;?]*[A-Za-z]//g" \
    | awk '
        # Two passes (buffered): a tail cut mid-key can start with key body lines
        # BEFORE the END marker, so once any key marker exists in the text every
        # base64-looking line (8+ chars) is masked, wherever it is.
        { line[NR] = $0 }
        /-----(BEGIN|END) [A-Z ]*PRIVATE KEY-----/ { haskey = 1 }
        END {
          for (i = 1; i <= NR; i++) {
            l = line[i]
            if (l ~ /-----BEGIN [A-Z ]*PRIVATE KEY-----/) {
              print "[MASKED PRIVATE KEY]"
              if (l !~ /-----END [A-Z ]*PRIVATE KEY-----/) inkey = 1
              continue
            }
            if (inkey) { if (l ~ /-----END [A-Z ]*PRIVATE KEY-----/) inkey = 0; continue }
            if (l ~ /-----END [A-Z ]*PRIVATE KEY-----/) { print "[MASKED PRIVATE KEY]"; continue }
            if (haskey && l ~ /^[A-Za-z0-9+\/=]{8,}$/) { print "[MASKED]"; continue }
            if (l ~ /^[A-Za-z0-9+\/=]{40,}$/) { print "[MASKED]"; continue }
            print l
          }
        }
      ' \
    | sed -E \
        -e 's/tk_[A-Za-z0-9]{20,}/[MASKED]/g' \
        -e 's/eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_.-]*/[MASKED]/g' \
        -e 's/AKIA[0-9A-Z]{16}/[MASKED]/g' \
        -e 's#([A-Za-z][A-Za-z0-9+.-]*://[^/:@ ]+):[^ ]*@#\1:[MASKED]@#g' \
    | awk '{
        l = tolower($0)
        if (l ~ /(password|passwd|passphrase|token|secret|api[_-]?key|authorization|credential)[a-z_]*[ ]*[=:]/) print "[MASKED LINE]"
        else if (l ~ /--?(password|passwd|passphrase|token|secret)[ =]+[^ ]/) print "[MASKED LINE]"
        else print $0
      }'
}

tail_of() { # tail_of <file>: last 20 lines, masked
  if [ -s "$1" ]; then tail -n 20 "$1" | mask_secrets; fi
}

# ---------------------------------------------------------------- fields (V_*)

reset_fields() {
  V_status="failed"; V_reason=""; V_packages="null"; V_changes="[]"
  V_health_before='{"failed_units":[],"unhealthy_containers":[],"disk_free_pct":{},"critical_services_down":[]}'
  V_health_after='{"failed_units":[],"unhealthy_containers":[],"disk_free_pct":{},"critical_services_down":[]}'
  V_pf_ok="true"; V_pf_blocked=""; V_conflicts="[]"; V_job=""
  V_reboot_required="false"; V_reboot_since=""
  V_os=""; V_kernel=""; V_started="$(now)"; V_ended=""; V_log_tail=""
}

os_description() {
  if [ "$OS_KERNEL" = Darwin ]; then
    printf '%s %s' "$(sw_vers -productName 2>/dev/null || echo macOS)" "$(sw_vers -productVersion 2>/dev/null || true)"
  elif [ -r "$OS_RELEASE" ]; then
    # shellcheck disable=SC1090
    ( . "$OS_RELEASE" 2>/dev/null; printf '%s %s' "${NAME:-Linux}" "${VERSION_ID:-}" )
  else
    printf '%s' "$OS_KERNEL"
  fi
}

kernel_release() { printf '%s' "${FLEET_AGENT_KERNEL:-$(uname -r)}"; }

# emit <verb>: one JSON line from the V_* fields.
emit() {
  local verb="$1"
  [ -n "$V_ended" ] || V_ended="$(now)"
  [ -n "$V_os" ] || V_os="$(os_description)"
  [ -n "$V_kernel" ] || V_kernel="$(kernel_release)"
  printf '{"schema":1,"host":%s,"verb":%s,"status":%s,"reason":%s,"packages":%s,"changes":%s,"health_before":%s,"health_after":%s,"preflight":{"ok":%s,"blocked_by":%s},"config_conflicts":%s,"job":%s,"reboot_required":%s,"reboot_since":%s,"os":%s,"kernel":%s,"major_available":null,"started":%s,"ended":%s,"log_tail":%s}\n' \
    "$(json_str "$HOST")" "$(json_str "$verb")" "$(json_str "$V_status")" \
    "$(json_str_or_null "$V_reason")" "$V_packages" "$V_changes" \
    "$V_health_before" "$V_health_after" \
    "$V_pf_ok" "$(json_str_or_null "$V_pf_blocked")" \
    "$V_conflicts" "$(json_str_or_null "$V_job")" \
    "$V_reboot_required" "$(json_str_or_null "$V_reboot_since")" \
    "$(json_str "$V_os")" "$(json_str "$V_kernel")" \
    "$(json_str "$V_started")" "$(json_str "$V_ended")" "$(json_str "$V_log_tail")"
}

exit_code_for() {
  case "$1" in
    failed) return 2 ;;
    busy) return 3 ;;
    *) return 0 ;;
  esac
}

finish() { # finish <verb>: print and exit with the status-derived code
  emit "$1"
  exit_code_for "$V_status"
  exit $?
}

# ---------------------------------------------------------------- refusal

refuse() { # refuse <what>
  log auth.warning "REFUSED: $1 client=${CLIENT_IP}"
  echo "fleet-agent: refused" >&2
  exit 1
}

# ---------------------------------------------------------------- lock

# Atomic mkdir lock holding the owner pid. It is handed over to the detached
# job (handoff marker) and released by it.
LOCK_OWNED=0

# lock_dir_alive <dir>: is the holder of that lock directory still live?
lock_dir_alive() {
  local dir="$1" pid
  [ -d "$dir" ] || return 1
  pid="$(cat "$dir/pid" 2>/dev/null)"
  if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then return 0; fi
  # Parent exited, job not started yet: a fresh handoff still holds the lock.
  if [ -f "$dir/handoff" ] && [ -z "$(find "$dir/handoff" -mmin +2 2>/dev/null)" ]; then return 0; fi
  # Lock dir just created, pid not written yet.
  if [ -z "$pid" ] && [ -z "$(find "$dir" -maxdepth 0 -mmin +2 2>/dev/null)" ]; then return 0; fi
  return 1
}

lock_holder_alive() { lock_dir_alive "$LOCKDIR"; }

lock_claim() {
  printf '%s\n' "$$" >"$LOCKDIR/pid"
  LOCK_OWNED=1
}

# lock_acquire: atomic mkdir. A stale lock is taken over only while holding a
# second mkdir mutex ($LOCKDIR.takeover), so exactly one caller re-checks the
# holder, removes the stale lock and recreates it. Nobody else can create
# $LOCKDIR while the stale one exists, and only the takeover holder removes it,
# so a live lock is never moved or deleted. Losers report busy. A takeover mutex
# left by a crashed caller is ignored after 2 minutes. run_job additionally
# verifies ownership.
lock_acquire() {
  local mutex="$LOCKDIR.takeover" rc=1
  mkdir -p "$LOCK_BASE" 2>/dev/null
  if mkdir "$LOCKDIR" 2>/dev/null; then lock_claim; return 0; fi
  lock_holder_alive && return 1
  if ! mkdir "$mutex" 2>/dev/null; then
    [ -n "$(find "$mutex" -maxdepth 0 -mmin +2 2>/dev/null)" ] || return 1
    rm -rf "$mutex"
    mkdir "$mutex" 2>/dev/null || return 1
  fi
  if ! lock_holder_alive; then
    rm -rf "$LOCKDIR"
    if mkdir "$LOCKDIR" 2>/dev/null; then lock_claim; rc=0; fi
  fi
  rmdir "$mutex" 2>/dev/null
  return "$rc"
}

# lock_release: only remove a lock that still carries our pid.
lock_release() {
  if [ "$LOCK_OWNED" = 1 ]; then
    if [ "$(cat "$LOCKDIR/pid" 2>/dev/null)" = "$$" ]; then rm -rf "$LOCKDIR"; fi
    LOCK_OWNED=0
  fi
}

# ---------------------------------------------------------------- probes

# disk_free_pct <path>: integer percent free of the filesystem holding <path>.
disk_free_pct() {
  df -Pk "$1" 2>/dev/null | awk 'NR == 2 { gsub("%", "", $5); print 100 - $5 }'
}

# boot_is_separate: true when /boot is its own mount point.
boot_is_separate() {
  [ "$(df -Pk /boot 2>/dev/null | awk 'NR == 2 { print $6 }')" = "/boot" ]
}

on_battery() {
  local d t s
  if [ "$OS_KERNEL" = Darwin ]; then
    pmset -g batt 2>/dev/null | grep -q "Battery Power"
    return $?
  fi
  for d in "$POWER_DIR"/*; do
    [ -d "$d" ] || continue
    t="$(cat "$d/type" 2>/dev/null)"
    [ "$t" = Battery ] || continue
    s="$(cat "$d/status" 2>/dev/null)"
    [ "$s" = Discharging ] && return 0
  done
  return 1
}

metered_network() {
  command -v nmcli >/dev/null 2>&1 || return 1
  nmcli -g connection.metered connection show --active 2>/dev/null | grep -qx "yes"
}

# update_in_progress: a package manager is already running.
update_in_progress() {
  if [ "$OS_KERNEL" = Darwin ]; then
    pgrep -x "brew|softwareupdate|mas" >/dev/null 2>&1
  else
    pgrep -x "apt|apt-get|dpkg|dnf|dnf5|yum|rpm|pacman|rpm-ostree|packagekitd-upgrade" >/dev/null 2>&1
  fi
}

# preflight: sets V_pf_ok / V_pf_blocked.
preflight() {
  local root_free boot_free
  V_pf_ok="true"; V_pf_blocked=""
  root_free="$(disk_free_pct /)"
  if [ -n "$root_free" ] && [ "$root_free" -lt 10 ]; then V_pf_blocked="disk_low"; fi
  if [ -z "$V_pf_blocked" ] && boot_is_separate; then
    boot_free="$(disk_free_pct /boot)"
    if [ -n "$boot_free" ] && [ "$boot_free" -lt 20 ]; then V_pf_blocked="disk_low"; fi
  fi
  if [ -z "$V_pf_blocked" ] && on_battery; then V_pf_blocked="on_battery"; fi
  if [ -z "$V_pf_blocked" ] && metered_network; then V_pf_blocked="metered_network"; fi
  if [ -z "$V_pf_blocked" ] && update_in_progress; then V_pf_blocked="update_in_progress"; fi
  if [ -n "$V_pf_blocked" ]; then V_pf_ok="false"; fi
}

critical_services() {
  [ -r "$CRITICAL_FILE" ] || return 0
  grep -E '^[A-Za-z0-9_.@:-]+$' "$CRITICAL_FILE" 2>/dev/null
}

# collect_health <dir>: writes failed, unhealthy, critdown, disk files in <dir>.
collect_health() {
  local dir="$1" svc
  mkdir -p "$dir"
  : >"$dir/failed"; : >"$dir/unhealthy"; : >"$dir/critdown"; : >"$dir/disk"
  if command -v systemctl >/dev/null 2>&1 && [ "$OS_KERNEL" = Linux ]; then
    systemctl --failed --no-legend --plain --no-pager 2>/dev/null \
      | awk 'NF { print $1 }' | grep '\.' | sort -u >"$dir/failed"
  fi
  if command -v docker >/dev/null 2>&1; then
    docker ps -a --format '{{.Names}}|{{.Status}}' 2>/dev/null \
      | awk -F'|' '$2 ~ /\(unhealthy\)/ || $2 ~ /^Exited/ || $2 ~ /^Dead/ { print $1 }' \
      | sort -u >"$dir/unhealthy"
  fi
  { printf '/ %s\n' "$(disk_free_pct /)"
    if boot_is_separate; then printf '/boot %s\n' "$(disk_free_pct /boot)"; fi
  } | awk 'NF == 2 && $2 ~ /^[0-9]+$/' >"$dir/disk"
  if command -v systemctl >/dev/null 2>&1 && [ "$OS_KERNEL" = Linux ]; then
    critical_services | while IFS= read -r svc; do
      systemctl is-active --quiet "$svc" 2>/dev/null || printf '%s\n' "$svc"
    done >"$dir/critdown"
  fi
}

# health_json <dir>
health_json() {
  local dir="$1" first=1
  printf '{"failed_units":%s,"unhealthy_containers":%s,"disk_free_pct":{' "$(list_json "$dir/failed")" "$(list_json "$dir/unhealthy")"
  while read -r path pct; do
    [ -n "$path" ] || continue
    if [ "$first" = 1 ]; then first=0; else printf ','; fi
    printf '%s:%s' "$(json_str "$path")" "$pct"
  done <"$dir/disk"
  printf '},"critical_services_down":%s}' "$(list_json "$dir/critdown")"
}

# new_entries <before> <after>: lines of <after> missing from <before>.
new_entries() {
  if [ -s "$1" ]; then grep -vxF -f "$1" "$2"; else cat "$2"; fi
}

# degraded_reason <before_dir> <after_dir>: prints why health got worse (empty = fine).
degraded_reason() {
  local b="$1" a="$2" out="" n free
  n="$(new_entries "$b/failed" "$a/failed" | tr '\n' ' ')"
  [ -z "$n" ] || out="$out new failed units: $n;"
  n="$(new_entries "$b/unhealthy" "$a/unhealthy" | tr '\n' ' ')"
  [ -z "$n" ] || out="$out new unhealthy/stopped containers: $n;"
  n="$(tr '\n' ' ' <"$a/critdown")"
  [ -z "$n" ] || out="$out critical services down: $n;"
  free="$(awk '$1 == "/" { print $2 }' "$a/disk")"
  if [ -n "$free" ] && [ "$free" -lt 10 ]; then out="$out disk / below 10% free;"; fi
  printf '%s' "$out" | sed -e 's/^ //'
}

config_conflicts_file() { # config_conflicts_file <out>
  find "$ETC_DIR" -xdev -maxdepth 6 \( -name '*.dpkg-dist' -o -name '*.rpmnew' -o -name '*.pacnew' \) -print 2>/dev/null \
    | sort | head -n 50 >"$1"
}

# ---------------------------------------------------------------- packages

pkg_manager() {
  if [ -n "${FLEET_AGENT_PKGMGR:-}" ]; then printf '%s' "$FLEET_AGENT_PKGMGR"; return; fi
  if [ "$OS_KERNEL" = Darwin ]; then
    if command -v brew >/dev/null 2>&1; then printf brew; else printf none; fi
  elif command -v rpm-ostree >/dev/null 2>&1 && [ -e /run/ostree-booted ]; then printf ostree
  elif command -v dnf >/dev/null 2>&1; then printf dnf
  elif command -v apt-get >/dev/null 2>&1; then printf apt
  elif command -v pacman >/dev/null 2>&1; then printf pacman
  else printf none
  fi
}

# pending_count: prints the number of packages with an update available.
# Return codes: 0 ok, 1 the check itself failed (do NOT treat as up-to-date),
# 3 no package manager (unsupported).
pending_count() {
  local out rc
  case "$(pkg_manager)" in
    dnf)
      out="$(dnf -q check-update 2>/dev/null)"; rc=$?
      case "$rc" in
        0|100) printf '%s\n' "$out" \
                 | awk '/^Obsoleting/ { exit } NF == 3 && $1 ~ /\./ { n++ } END { print n + 0 }' ;;
        *) return 1 ;;
      esac ;;
    apt)
      out="$(apt-get -s -o Debug::NoLocking=1 dist-upgrade 2>/dev/null)"; rc=$?
      [ "$rc" = 0 ] || return 1
      printf '%s\n' "$out" | grep -c '^Inst ' || true ;;
    pacman)
      if command -v checkupdates >/dev/null 2>&1; then
        out="$(checkupdates 2>/dev/null)"; rc=$?
        # checkupdates: 0 updates available, 2 none, 1 error.
        case "$rc" in
          0) printf '%s\n' "$out" | grep -c . || true ;;
          2) printf '0\n' ;;
          *) return 1 ;;
        esac
      else
        out="$(pacman -Qu 2>/dev/null)"; rc=$?
        # pacman -Qu: 0 updates, 1 none or error (stdout empty either way).
        case "$rc" in
          0) printf '%s\n' "$out" | grep -c . || true ;;
          1) printf '0\n' ;;
          *) return 1 ;;
        esac
      fi ;;
    brew)
      out="$(brew outdated -q 2>/dev/null)"; rc=$?
      [ "$rc" = 0 ] || return 1
      printf '%s\n' "$out" | grep -c . || true ;;
    *) return 3 ;;
  esac
}

# pkg_snapshot <out>: sorted "name version" lines of installed packages.
pkg_snapshot() {
  case "$(pkg_manager)" in
    dnf|ostree) rpm -qa --qf '%{NAME} %{VERSION}-%{RELEASE}\n' 2>/dev/null ;;
    apt) dpkg-query -W -f='${Package} ${Version}\n' 2>/dev/null ;;
    pacman) pacman -Q 2>/dev/null ;;
    brew) brew list --versions 2>/dev/null | awk 'NF >= 2 { print $1, $NF }' ;;
    *) ;;
  esac | sort -u >"$1"
}

# changes_from <pre> <post> <out_json_file> <out_count_file>
changes_from() {
  local pre="$1" post="$2" out="$3" cnt="$4" only_pre only_post
  only_pre="$(mktemp "${TMPDIR:-/tmp}/fleet-agent.XXXXXX")"
  only_post="$(mktemp "${TMPDIR:-/tmp}/fleet-agent.XXXXXX")"
  comm -23 "$pre" "$post" >"$only_pre"
  comm -13 "$pre" "$post" >"$only_post"
  awk '
    function esc(s) { gsub(/\\/, "\\\\", s); gsub(/"/, "\\\"", s); return s }
    function item(n, f, t) {
      return "{\"name\":\"" esc(n) "\",\"from\":" (f == "" ? "null" : "\"" esc(f) "\"") ",\"to\":" (t == "" ? "null" : "\"" esc(t) "\"") "}"
    }
    FILENAME == ARGV[1] { if (!($1 in from)) { from[$1] = $2; order[++n] = $1 }; next }
    { to[$1] = $2; if (!($1 in from)) order[++n] = $1 }
    END {
      printf "["
      for (i = 1; i <= n && i <= 200; i++) {
        k = order[i]
        printf "%s%s", (i > 1 ? "," : ""), item(k, from[k], to[k])
      }
      printf "]"
    }' "$only_pre" "$only_post" >"$out"
  cat "$only_pre" "$only_post" | awk '{ print $1 }' | sort -u | grep -c . >"$cnt"
  rm -f "$only_pre" "$only_post"
}

# ---------------------------------------------------------------- reboot state

reboot_required() {
  local rc running newest
  [ "$OS_KERNEL" = Linux ] || return 1
  [ -e "$REBOOT_FLAG" ] && return 0
  if command -v needs-restarting >/dev/null 2>&1; then
    needs-restarting -r >/dev/null 2>&1; rc=$?
    [ "$rc" = 1 ] && return 0
  elif command -v dnf >/dev/null 2>&1; then
    dnf needs-restarting -r >/dev/null 2>&1; rc=$?
    [ "$rc" = 1 ] && return 0
  fi
  # Installed kernel newer than the running one (not meaningful in containers).
  if [ ! -e /run/.containerenv ] && [ ! -e /.dockerenv ] && [ -d "$MODULES_DIR" ]; then
    running="$(kernel_release)"
    # shellcheck disable=SC2012
    newest="$(ls "$MODULES_DIR" 2>/dev/null | sort -V | tail -n 1)"
    if [ -n "$newest" ] && [ "$newest" != "$running" ] \
       && [ "$(printf '%s\n%s\n' "$running" "$newest" | sort -V | tail -n 1)" = "$newest" ]; then
      return 0
    fi
  fi
  return 1
}

# refresh_reboot_fields: sets V_reboot_required / V_reboot_since (+ state file).
refresh_reboot_fields() {
  local f="$STATE_DIR/reboot-since"
  mkdir -p "$STATE_DIR"
  if reboot_required; then
    V_reboot_required="true"
    [ -s "$f" ] || now >"$f"
    V_reboot_since="$(cat "$f" 2>/dev/null)"
  else
    V_reboot_required="false"; V_reboot_since=""
    rm -f "$f"
  fi
}

# ---------------------------------------------------------------- verbs

verb_check() {
  local hdir pending prc
  reset_fields
  V_job=""
  if lock_holder_alive; then
    V_status="running"; V_reason="update_in_progress"
    V_job="$(cat "$STATE_DIR/last-job" 2>/dev/null)"
  fi
  hdir="$(mktemp -d "${TMPDIR:-/tmp}/fleet-agent.XXXXXX")"
  collect_health "$hdir"
  V_health_before="$(health_json "$hdir")"
  V_health_after="$V_health_before"
  rm -rf "$hdir"
  preflight
  mkdir -p "$STATE_DIR"
  config_conflicts_file "$STATE_DIR/.conflicts.$$"
  V_conflicts="$(list_json "$STATE_DIR/.conflicts.$$")"
  rm -f "$STATE_DIR/.conflicts.$$"
  refresh_reboot_fields
  if [ "$V_status" != running ]; then
    pending="$(pending_count)"; prc=$?
    if [ "$prc" = 3 ]; then
      V_status="unsupported"; V_reason="no_package_manager"
    elif [ "$prc" != 0 ] || ! printf '%s' "$pending" | grep -Eq '^[0-9]+$'; then
      # The check itself broke (repo error, lock, network): never "up-to-date".
      V_status="failed"; V_reason="check_failed"; V_packages="null"
    else
      V_packages="$pending"
      if [ "$pending" -eq 0 ]; then
        V_status="up-to-date"
      else
        V_status="skipped"
        if [ -n "$V_pf_blocked" ]; then V_reason="$V_pf_blocked"; else V_reason="updates_pending"; fi
      fi
    fi
  fi
  finish check
}

verb_reboot_status() {
  reset_fields
  refresh_reboot_fields
  if lock_holder_alive; then
    V_status="running"; V_reason="update_in_progress"
    V_job="$(cat "$STATE_DIR/last-job" 2>/dev/null)"
  else
    V_status="up-to-date"
    if [ "$V_reboot_required" = true ]; then V_reason="reboot_required"; else V_reason="no_reboot_required"; fi
  fi
  finish reboot-status
}

verb_reboot() {
  reset_fields
  if ! lock_acquire; then
    V_status="busy"; V_reason="update_in_progress"
    finish reboot
  fi
  trap lock_release EXIT
  refresh_reboot_fields
  if [ "$V_reboot_required" != true ]; then
    V_status="skipped"; V_reason="no_reboot_required"
    finish reboot
  fi
  log auth.notice "reboot requested and required: rebooting in ${REBOOT_DELAY}s"
  V_status="started"; V_reason="rebooting"
  # Delayed and detached so this answer reaches the master before the host goes
  # down. The sudoers rule allows exactly `/usr/bin/systemctl reboot`
  # (`/sbin/shutdown -r now` on macOS), nothing else.
  if [ "$OS_KERNEL" = Darwin ]; then
    nohup sh -c 'sleep '"$REBOOT_DELAY"'; sudo -n /sbin/shutdown -r now' >/dev/null 2>&1 &
  else
    nohup sh -c 'sleep '"$REBOOT_DELAY"'; sudo -n /usr/bin/systemctl reboot' >/dev/null 2>&1 &
  fi
  finish reboot
}

new_job_id() { printf '%s-%s' "$(date -u +%Y%m%dT%H%M%SZ)" "$$"; }

valid_job_id() { printf '%s' "$1" | grep -Eq '^[0-9]{8}T[0-9]{6}Z-[0-9]+$'; }

# write_state <jobdir>: atomically store the current V_* fields as state.json.
write_state() {
  emit update >"$1/state.json.tmp" && mv -f "$1/state.json.tmp" "$1/state.json"
}

launch_detached() { # launch_detached <job> <jobdir>
  local job="$1" jobdir="$2" var
  local sargs=()
  if [ "$OS_KERNEL" = Linux ] && command -v systemd-run >/dev/null 2>&1; then
    for var in $PASSTHROUGH_VARS; do
      if [ -n "${!var+x}" ]; then sargs+=("--setenv=$var=${!var}"); fi
    done
    env -u SSH_CONNECTION -u SSH_ORIGINAL_COMMAND \
      systemd-run --user --quiet --collect --unit="fleet-update-$job" \
      --setenv="FLEET_AGENT_JOB_ID=$job" ${sargs[@]+"${sargs[@]}"} \
      -- bash "$AGENT_PATH" >"$jobdir/launcher.log" 2>&1
    return $?
  fi
  env -u SSH_CONNECTION -u SSH_ORIGINAL_COMMAND FLEET_AGENT_JOB_ID="$job" nohup bash "$AGENT_PATH" >"$jobdir/launcher.log" 2>&1 </dev/null &
  return 0
}

verb_update() {
  local job jobdir hdir
  reset_fields
  if ! lock_acquire; then
    V_status="busy"; V_reason="update_in_progress"
    V_job="$(cat "$STATE_DIR/last-job" 2>/dev/null)"
    finish update
  fi
  trap lock_release EXIT
  preflight
  if [ "$V_pf_ok" != true ]; then
    V_status="skipped"; V_reason="$V_pf_blocked"
    finish update
  fi
  job="$(new_job_id)"
  jobdir="$JOBS_DIR/$job"
  mkdir -p "$jobdir"
  find "$JOBS_DIR" -mindepth 1 -maxdepth 1 -mtime +31 -exec rm -rf {} + 2>/dev/null
  collect_health "$jobdir/hb"
  V_health_before="$(health_json "$jobdir/hb")"
  V_health_after="$V_health_before"
  V_job="$job"
  V_status="started"
  refresh_reboot_fields
  printf '%s\n' "$V_started" >"$jobdir/started"
  write_state "$jobdir"
  printf '%s\n' "$job" >"$STATE_DIR/last-job"
  if ! launch_detached "$job" "$jobdir"; then
    V_status="failed"; V_reason="launch_failed"
    V_log_tail="$(tail_of "$jobdir/launcher.log")"
    write_state "$jobdir"
    finish update
  fi
  # The detached job now owns the lock; do not release it on exit. The lock
  # names the job so the job can verify it still owns it (lock_lost otherwise).
  printf '%s\n' "$job" >"$LOCKDIR/job"
  : >"$LOCKDIR/handoff"
  LOCK_OWNED=0
  trap - EXIT
  finish update
}

# Detached job entry: reached only through FLEET_AGENT_JOB_ID, which the SSH
# client cannot set. Runs sysup, builds the final state.
run_job() {
  local job="$FLEET_AGENT_JOB_ID" jobdir rc pre post cnt hdir why
  valid_job_id "$job" || { log auth.warning "job runner: invalid job id"; exit 1; }
  jobdir="$JOBS_DIR/$job"
  [ -d "$jobdir" ] || { log auth.warning "job runner: unknown job"; exit 1; }
  reset_fields
  V_job="$job"
  V_started="$(cat "$jobdir/started" 2>/dev/null || now)"
  # Ownership check: the lock must be the one verb_update handed to THIS job. If
  # a stale-lock takeover replaced it, abort without touching the other lock.
  if [ -d "$LOCKDIR" ] && [ "$(cat "$LOCKDIR/job" 2>/dev/null)" = "$job" ]; then
    printf '%s\n' "$$" >"$LOCKDIR/pid"
    rm -f "$LOCKDIR/handoff"
    LOCK_OWNED=1
  else
    V_status="failed"; V_reason="lock_lost"; V_ended="$(now)"
    write_state "$jobdir"
    log auth.warning "update job $job aborted: lock_lost"
    exit 2
  fi
  trap lock_release EXIT
  V_health_before="$(health_json "$jobdir/hb")"
  V_health_after="$V_health_before"
  V_status="running"
  write_state "$jobdir"
  log auth.notice "update job $job started"

  pre="$jobdir/pkgs.pre"; post="$jobdir/pkgs.post"
  pkg_snapshot "$pre"
  if [ -x "$SYSUP" ]; then
    "$SYSUP" >"$jobdir/sysup.log" 2>&1 </dev/null
    rc=$?
  else
    printf 'sysup not found or not executable: %s\n' "$SYSUP" >"$jobdir/sysup.log"
    rc=127
  fi
  pkg_snapshot "$post"
  cnt="$jobdir/count"
  changes_from "$pre" "$post" "$jobdir/changes.json" "$cnt"
  V_changes="$(cat "$jobdir/changes.json")"
  V_packages="$(cat "$cnt")"

  hdir="$jobdir/ha"
  collect_health "$hdir"
  V_health_after="$(health_json "$hdir")"
  config_conflicts_file "$jobdir/conflicts"
  V_conflicts="$(list_json "$jobdir/conflicts")"
  refresh_reboot_fields
  V_log_tail="$(tail_of "$jobdir/sysup.log")"
  V_ended="$(now)"

  why="$(degraded_reason "$jobdir/hb" "$hdir")"
  if [ "$rc" -ne 0 ]; then
    V_status="failed"; V_reason="sysup_exit_$rc"
  elif [ -n "$why" ]; then
    V_status="degraded"; V_reason="$why"
  elif [ "${V_packages:-0}" -gt 0 ]; then
    V_status="updated"
  else
    V_status="up-to-date"
  fi
  write_state "$jobdir"
  log auth.notice "update job $job finished: $V_status"
  exit_code_for "$V_status"
  exit $?
}

verb_report() {
  local job jobdir state status
  reset_fields
  job="$(cat "$STATE_DIR/last-job" 2>/dev/null)"
  if [ -z "$job" ] || ! valid_job_id "$job" || [ ! -s "$JOBS_DIR/$job/state.json" ]; then
    V_status="skipped"; V_reason="no_job"
    finish report
  fi
  jobdir="$JOBS_DIR/$job"
  state="$jobdir/state.json"
  status="$(sed -n 's/.*"status":"\([a-z-]*\)".*/\1/p' "$state" | head -n 1)"
  case "$status" in
    started|running)
      if ! lock_holder_alive; then
        # The job died without writing a final state (killed, host rebooted).
        V_job="$job"; V_status="failed"; V_reason="job_died"
        V_started="$(cat "$jobdir/started" 2>/dev/null || now)"
        V_log_tail="$(tail_of "$jobdir/sysup.log")"
        write_state "$jobdir"
        sed -e 's/"verb":"update"/"verb":"report"/' "$state"
        exit 2
      fi ;;
  esac
  sed -e 's/"verb":"update"/"verb":"report"/' "$state"
  case "$(sed -n 's/.*"status":"\([a-z-]*\)".*/\1/p' "$state" | head -n 1)" in
    failed) exit 2 ;;
  esac
  exit 0
}

# ---------------------------------------------------------------- main

main() {
  local verb
  # Internal entry of the detached job (see launch_detached); not reachable from
  # SSH_ORIGINAL_COMMAND.
  if [ -n "${FLEET_AGENT_JOB_ID:-}" ]; then
    # launch_detached clears SSH_CONNECTION / SSH_ORIGINAL_COMMAND for the job, so
    # seeing either here means the call came through sshd: refuse.
    if [ -n "${SSH_CONNECTION+x}${SSH_ORIGINAL_COMMAND+x}" ]; then
      refuse "internal job entry reached through ssh"
    fi
    run_job
  fi

  verb="${SSH_ORIGINAL_COMMAND-}"
  if [ "$#" -ne 0 ]; then
    refuse "unexpected arguments"
  fi
  case "$verb" in
    check|update|reboot-status|reboot|report) ;;
    "") refuse "no command (interactive shell attempt)" ;;
    *) refuse "verb not allowed: $verb" ;;
  esac
  log auth.notice "call verb=$verb client=${CLIENT_IP}"

  mkdir -p "$STATE_DIR" 2>/dev/null || true

  case "$verb" in
    check) verb_check ;;
    update) verb_update ;;
    reboot-status) verb_reboot_status ;;
    reboot) verb_reboot ;;
    report) verb_report ;;
  esac
}

main "$@"
