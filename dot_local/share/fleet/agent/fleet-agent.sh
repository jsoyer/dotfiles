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
# Local-only entry (NOT a verb): FLEET_AGENT_PULL=1 with no SSH context runs the
# pull-mode catch-up (see run_pull). sshd gives the client no way to set an
# environment variable, SSH_ORIGINAL_COMMAND never reaches it, and main() refuses
# it if SSH_CONNECTION / SSH_ORIGINAL_COMMAND is set. It never reaches verb_reboot.
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
    [ "$_fa_var" = FLEET_AGENT_JOB_ID ] || [ "$_fa_var" = FLEET_AGENT_PULL ] || unset "$_fa_var"
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
CONF_DIR="${FLEET_AGENT_CONF_DIR:-${HOME:-/nonexistent}/.config/fleet-agent}"
PULL_DAYS="${FLEET_AGENT_PULL_DAYS:-7}"
case "$PULL_DAYS" in *[!0-9]*|"") PULL_DAYS=7 ;; esac
TAB="$(printf '\t')"

# Environment variables handed to the detached job (systemd --user units do not
# inherit the caller's environment).
PASSTHROUGH_VARS="PATH FLEET_AGENT_STATE_DIR FLEET_AGENT_LOCK_DIR FLEET_AGENT_SYSUP FLEET_AGENT_ETC_DIR FLEET_AGENT_CRITICAL_FILE FLEET_AGENT_REBOOT_FLAG FLEET_AGENT_MODULES_DIR FLEET_AGENT_POWER_DIR FLEET_AGENT_OS_RELEASE FLEET_AGENT_HOST FLEET_AGENT_PKGMGR FLEET_AGENT_KERNEL FLEET_AGENT_LOG_FILE FLEET_AGENT_REBOOT_DELAY FLEET_AGENT_TEST FLEET_AGENT_KIND FLEET_AGENT_CF_BIN FLEET_AGENT_CF_READY_URL FLEET_AGENT_CF_TRIES FLEET_AGENT_CF_SLEEP FLEET_AGENT_CONF_DIR FLEET_AGENT_PULL_DAYS FLEET_AGENT_PULL_JOB FLEET_AGENT_SWUPDATE_DOMAIN"

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

# macos_update_issues: one line per native macOS automatic-update setting that is
# explicitly switched off. Read-only (`defaults read`); macOS itself is updated by
# its own automatic updates, never by this agent (Apple Silicon needs the volume
# owner's password to install macOS, so the agent only checks and reports).
macos_update_issues() {
  local domain key val
  domain="${FLEET_AGENT_SWUPDATE_DOMAIN:-}"
  if [ -z "$domain" ]; then
    [ "$OS_KERNEL" = Darwin ] || return 0
    domain=/Library/Preferences/com.apple.SoftwareUpdate
  fi
  command -v defaults >/dev/null 2>&1 || return 0
  for key in AutomaticCheckEnabled AutomaticDownload CriticalUpdateInstall ConfigDataInstall AutomaticallyInstallMacOSUpdates; do
    val="$(defaults read "$domain" "$key" 2>/dev/null)" || continue
    if [ "$val" = 0 ]; then printf 'macos_auto_updates_off: %s\n' "$key"; fi
  done
}

config_conflicts_file() { # config_conflicts_file <out>
  {
    find "$ETC_DIR" -xdev -maxdepth 6 \( -name '*.dpkg-dist' -o -name '*.rpmnew' -o -name '*.pacnew' \) -print 2>/dev/null
    macos_update_issues
  } | sort | head -n 50 >"$1"
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

# ---------------------------------------------------------------- appliance branches

# agent_kind: omv | pikvm | proxmox | generic (anything sysup handles).
# Detected from the tool each appliance ships, so nothing needs configuring;
# FLEET_AGENT_KIND overrides it in tests only (dropped in an SSH context).
agent_kind() {
  if [ -n "${FLEET_AGENT_KIND:-}" ]; then printf '%s' "$FLEET_AGENT_KIND"; return; fi
  if command -v pveversion >/dev/null 2>&1; then printf proxmox
  elif command -v omv-upgrade >/dev/null 2>&1; then printf omv
  elif command -v pikvm-update >/dev/null 2>&1; then printf pikvm
  else printf generic
  fi
}

# canon_path <path>: `readlink -f` (symlinks resolved), empty when it cannot be resolved.
canon_path() {
  local r
  r="$(readlink -f -- "$1" 2>/dev/null)" || return 0
  case "$r" in /*) printf '%s\n' "$r" ;; esac
}

# tool_path <name>: the CANONICAL absolute path, the same one `fleet bootstrap` put in
# sudoers (sudo matches by path: a symlinked name such as /bin/systemctl would not match).
tool_path() {
  local p
  p="$(command -v "$1" 2>/dev/null)" || return 0
  case "$p" in /*) canon_path "$p" ;; esac
}

# as_root <abs path> [args]: exact sudoers commands only (never a shell, never a
# free-form argument). Already root (PiKVM logs in as root): run directly.
as_root() {
  if [ "$(id -u)" = 0 ]; then "$@"; else sudo -n "$@"; fi
}

# proxmox_vm_lines: "vm: <id> <name> <status>" per VM, best effort and without
# sudo (there is no agent verb to list VMs). Empty when `qm list` is not allowed;
# the master then falls back to a generic warning.
proxmox_vm_lines() {
  command -v qm >/dev/null 2>&1 || return 0
  qm list 2>/dev/null \
    | awk 'NR > 1 && $1 ~ /^[0-9]+$/ { printf "vm: %s %s %s\n", $1, $2, $3 }' | head -n 20
}

# OMV: `omv-upgrade` (never apt directly), non-interactive.
update_omv() {
  local bin
  bin="$(tool_path omv-upgrade)"
  if [ -z "$bin" ]; then echo "omv-upgrade not found"; return 127; fi
  DEBIAN_FRONTEND=noninteractive NEEDRESTART_MODE=a as_root "$bin"
}

# cloudflared_ready: the tunnel answers on the local metrics /ready endpoint.
cloudflared_ready() {
  local url="${FLEET_AGENT_CF_READY_URL:-http://127.0.0.1:20241/ready}"
  local tries="${FLEET_AGENT_CF_TRIES:-12}" pause="${FLEET_AGENT_CF_SLEEP:-5}" i=0
  case "$tries" in *[!0-9]*|"") tries=12 ;; esac
  case "$pause" in *[!0-9]*|"") pause=5 ;; esac
  command -v curl >/dev/null 2>&1 || return 1
  while [ "$i" -lt "$tries" ]; do
    curl -fsS --max-time 3 "$url" >/dev/null 2>&1 && return 0
    i=$((i + 1))
    [ "$i" -lt "$tries" ] && sleep "$pause"
  done
  return 1
}

# pikvm_cloudflared: manually installed binary. Keeps the old one (user-owned
# copy in the state dir); restarts the service only if the version changed;
# restores the old binary if the tunnel does not come back. Restoring needs write
# access to the binary: only when the account is root (PiKVM default) because the
# closed sudoers list (spec section 10) has no command to write /usr/local/bin.
pikvm_cloudflared() {
  local cf="${FLEET_AGENT_CF_BIN:-/usr/local/bin/cloudflared}" before after urc sc old cfc
  if [ ! -x "$cf" ]; then echo "cloudflared not installed: step skipped"; return 0; fi
  sc="$(tool_path systemctl)"
  # never call as_root with an empty program: `sudo -n restart cloudflared` is not what we mean
  if [ -z "$sc" ]; then echo "systemctl not found: cloudflared step aborted"; return 44; fi
  old="$STATE_DIR/cloudflared.old"
  before="$("$cf" --version 2>/dev/null | head -n 1)"
  mkdir -p "$STATE_DIR"
  # Refresh the rollback copy only from a HEALTHY tunnel: after a failed update the next run
  # must not overwrite the last known good binary with the broken one.
  if cloudflared_ready; then
    if ! cp -p "$cf" "$old"; then echo "cannot keep the old cloudflared"; return 42; fi
  elif [ -e "$old" ]; then
    echo "tunnel not ready before the update: last known good copy kept in $old"
  else
    echo "tunnel not ready before the update and no earlier copy: no rollback possible"
  fi
  cfc="$(canon_path "$cf")"
  if [ -z "$cfc" ]; then echo "cloudflared path cannot be resolved: step aborted"; return 42; fi
  as_root "$cfc" update; urc=$?
  case "$urc" in 0|11) ;; *) echo "cloudflared update failed (exit $urc)"; return 42 ;; esac
  after="$("$cf" --version 2>/dev/null | head -n 1)"
  if [ "$before" = "$after" ]; then echo "cloudflared unchanged: $after"; return 0; fi
  echo "cloudflared: $before -> $after"
  as_root "$sc" restart cloudflared
  if cloudflared_ready; then echo "cloudflared tunnel ready"; return 0; fi
  echo "cloudflared tunnel not ready after update"
  # copy next to the target then rename: cp onto the running binary fails with ETXTBSY
  if [ -e "$old" ] && [ -w "$cf" ] && [ -w "$(dirname "$cf")" ] && cp -p "$old" "$cf.new" && mv -f "$cf.new" "$cf"; then
    as_root "$sc" restart cloudflared
    if cloudflared_ready; then echo "old cloudflared restored: tunnel ready"; return 43; fi
  fi
  echo "old cloudflared kept in $old: restore by hand"
  return 44
}

# PiKVM: ONE rw window; `ro` is guaranteed by the EXIT trap, even on failure or
# a signal. Exit codes: 40 rw failed, 41 pikvm-update failed, 42 cloudflared
# update failed, 43 tunnel down (old binary restored), 44 tunnel down (restore by
# hand), 45 kvmd inactive.
update_pikvm() {
  local rw ro pk
  rw="$(tool_path rw)"; ro="$(tool_path ro)"; pk="$(tool_path pikvm-update)"
  if [ -z "$rw" ] || [ -z "$ro" ] || [ -z "$pk" ]; then echo "pikvm tools (rw, ro, pikvm-update) not found"; return 127; fi
  (
    trap 'as_root "$ro" || echo "WARNING: ro failed" >&2' EXIT
    # SIGKILL cannot be trapped, and INT may be ignored in background jobs: TERM and
    # EXIT still guarantee `ro` for every catchable termination.
    trap 'exit 143' TERM INT HUP
    as_root "$rw" || { echo "rw failed"; exit 40; }
    as_root "$pk" || { echo "pikvm-update failed"; exit 41; }
    pikvm_cloudflared || exit $?
    if command -v systemctl >/dev/null 2>&1 && ! systemctl is-active --quiet kvmd 2>/dev/null; then
      echo "kvmd is not active"; exit 45
    fi
    exit 0
  )
}

# run_update_tool <logfile>: the kind's updater, output to the log; returns its exit code.
run_update_tool() {
  case "$(agent_kind)" in
    omv) update_omv >"$1" 2>&1 </dev/null ;;
    pikvm) update_pikvm >"$1" 2>&1 </dev/null ;;
    *)
      # generic and proxmox (apt dist-upgrade through sysup, never --reboot)
      if [ -x "$SYSUP" ]; then
        "$SYSUP" >"$1" 2>&1 </dev/null
      else
        printf 'sysup not found or not executable: %s\n' "$SYSUP" >"$1"
        return 127
      fi ;;
  esac
}

# update_failure_reason <rc>
update_failure_reason() {
  case "$(agent_kind):$1" in
    pikvm:40) printf rw_failed ;;
    pikvm:41) printf pikvm_update_failed ;;
    pikvm:42) printf cloudflared_update_failed ;;
    pikvm:43) printf cloudflared_tunnel_down_restored ;;
    pikvm:44) printf cloudflared_tunnel_down_restore_by_hand ;;
    pikvm:45) printf kvmd_inactive ;;
    omv:*) printf 'omv_upgrade_exit_%s' "$1" ;;
    *) printf 'sysup_exit_%s' "$1" ;;
  esac
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
  if [ "$(agent_kind)" = proxmox ]; then V_log_tail="$(proxmox_vm_lines | mask_secrets)"; fi
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
  run_update_tool "$jobdir/sysup.log"
  rc=$?
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
    V_status="failed"; V_reason="$(update_failure_reason "$rc")"
  elif [ -n "$why" ]; then
    V_status="degraded"; V_reason="$why"
  elif [ "${V_packages:-0}" -gt 0 ]; then
    V_status="updated"
  else
    V_status="up-to-date"
  fi
  write_state "$jobdir"
  case "$V_status" in
    updated|up-to-date) date +%s >"$STATE_DIR/last-success" 2>/dev/null ;;
  esac
  log auth.notice "update job $job finished: $V_status"
  if [ "${FLEET_AGENT_PULL_JOB:-}" = 1 ]; then pull_notify; fi
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

# ---------------------------------------------------------------- pull mode

# Pull mode (laptops and workstations that are often off): a local timer / launchd
# agent runs this file with FLEET_AGENT_PULL=1. It is NOT a verb: it is not in the
# verb whitelist, it ignores SSH_ORIGINAL_COMMAND (main() refuses it when that is
# set) and it only ever reaches verb_update. Nothing here calls the restart verb:
# a pull run can never restart the machine.

# conf_value <KEY>: value of KEY=value in $CONF_DIR/pull.conf (never sourced).
conf_value() {
  [ -r "$CONF_DIR/pull.conf" ] || return 0
  sed -n "s/^$1=//p" "$CONF_DIR/pull.conf" | head -n 1 | tr -d '\r"'
}

# pull_denied_reason: empty when this host may pull. Opt-in by a marker file;
# guardians, critical hosts and appliances are refused.
pull_denied_reason() {
  if [ ! -f "$CONF_DIR/pull-enabled" ]; then printf not_enabled; return 0; fi
  if [ -e "$CONF_DIR/no-pull" ]; then printf pull_denied; return 0; fi
  case "$(agent_kind)" in
    omv|pikvm|proxmox) printf 'kind_%s' "$(agent_kind)"; return 0 ;;
  esac
  case "$(printf '%s' "$HOST" | tr '[:upper:]' '[:lower:]')" in
    *guardian*) printf guardian ;;
  esac
}

# pull_notify: ntfy priority 2. The token (file named in pull.conf) goes through a
# curl config on stdin: never in argv, never in a log. Failures are only logged.
pull_notify() {
  local url topic tokfile tok msg
  url="$(conf_value NTFY_URL)"; topic="$(conf_value NTFY_TOPIC)"; tokfile="$(conf_value NTFY_TOKEN_FILE)"
  if [ -z "$url" ] || [ -z "$topic" ]; then log auth.notice "pull notify: no ntfy settings"; return 0; fi
  printf '%s' "$url" | grep -Eq '^https?://[A-Za-z0-9._:/-]+$' || { log auth.warning "pull notify: bad ntfy url"; return 0; }
  printf '%s' "$topic" | grep -Eq '^[A-Za-z0-9_-]+$' || { log auth.warning "pull notify: bad ntfy topic"; return 0; }
  tok=""
  if [ -n "$tokfile" ] && [ -r "$tokfile" ]; then
    tok="$(head -n 1 "$tokfile" | tr -d '\r\n')"
    printf '%s' "$tok" | grep -Eq '^[A-Za-z0-9_.-]+$' || tok=""
    # A token only travels over https (or to loopback).
    case "$url" in https://*|http://127.0.0.1*|http://localhost*) ;; *) tok="" ;; esac
  fi
  msg="$HOST: pull-mode update $V_status"
  if [ -n "${V_packages:-}" ] && [ "$V_packages" != null ]; then msg="$msg ($V_packages packages)"; fi
  if [ "$V_reboot_required" = true ]; then msg="$msg; restart required, NOT done (pull mode never restarts)"; fi
  msg="$(printf '%s' "$msg" | tr -d '"\\\r\n')"
  {
    printf 'silent\nshow-error\nmax-time = 15\n'
    printf 'url = "%s/%s"\n' "${url%/}" "$topic"
    printf 'header = "Priority: 2"\nheader = "Title: fleet pull update"\n'
    if [ -n "$tok" ]; then printf 'header = "Authorization: Bearer %s"\n' "$tok"; fi
    printf 'data = "%s"\n' "$msg"
  } | curl -K - >/dev/null 2>&1 || log auth.warning "pull notify: delivery failed"
  return 0
}

# run_pull: update only if the last successful update is older than PULL_DAYS.
run_pull() {
  local why last age
  reset_fields
  mkdir -p "$STATE_DIR" 2>/dev/null || true
  why="$(pull_denied_reason)"
  if [ -n "$why" ]; then
    V_status="skipped"; V_reason="pull_$why"
    log auth.notice "pull skipped: $why"
    finish pull
  fi
  last="$(cat "$STATE_DIR/last-success" 2>/dev/null)"
  case "$last" in *[!0-9]*|"") last=0 ;; esac
  age=$(( $(date +%s) - last ))
  if [ "$last" -gt 0 ] && [ "$age" -lt $(( PULL_DAYS * 86400 )) ]; then
    V_status="skipped"; V_reason="recent_update"
    log auth.notice "pull skipped: last successful update ${age}s ago"
    finish pull
  fi
  log auth.notice "pull: last successful update older than ${PULL_DAYS} days, updating"
  FLEET_AGENT_PULL_JOB=1
  export FLEET_AGENT_PULL_JOB
  verb_update
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

  # Local-only pull entry: same pattern as the job entry above.
  if [ -n "${FLEET_AGENT_PULL:-}" ]; then
    if [ -n "${SSH_CONNECTION+x}${SSH_ORIGINAL_COMMAND+x}" ] || [ "$#" -ne 0 ] || [ "$FLEET_AGENT_PULL" != 1 ]; then
      refuse "pull entry reached through ssh or with arguments"
    fi
    run_pull
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
