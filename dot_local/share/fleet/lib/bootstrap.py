#!/usr/bin/env python3
"""``fleet bootstrap <host>``: install the fleet agent on an OMV or PiKVM box, outside chezmoi.

What it installs on the target (spec sections 10 and 12):
  * /usr/local/libexec/fleet-agent  root:root 0755
  * authorized_keys lines  ``restrict,command="/usr/local/libexec/fleet-agent" ssh-ed25519 ...``
    (public keys of the masters, read from 1Password)
  * a sudoers fragment for the ``kind``: the CLOSED list of section 10, nothing else
        omv    omv-upgrade, systemctl reboot
        pikvm  rw, ro, pikvm-update, /usr/local/bin/cloudflared update,
               systemctl restart cloudflared, systemctl reboot
    Absolute paths are resolved with ``command -v`` ON THE TARGET, the fragment is
    validated with ``visudo -cf`` (here, and again on the target) and ``:`` ``=`` ``,``
    ``\\`` are escaped as sudoers requires.
  * the target's host key in this master's known_hosts (pinned, shown with its fingerprint).

Safety: the default mode is a DRY RUN that renders, validates and prints everything and
changes nothing. ``--apply`` renders and shows the same things, then requires an explicit
confirmation (typing the host alias on a terminal; no terminal => declined). On PiKVM the
whole application runs inside one ``rw`` window with a trap that restores ``ro``.

Privileges: the FIRST bootstrap needs root, or an account with NOPASSWD sudo, on the target
(the apply script uses ``sudo -n``: no password prompt, it fails fast without a tty). Afterwards
the account only has the closed list below.

Trust: absolute paths are resolved with PATH fixed to REMOTE_PATH (never the account's own
PATH) and each resolved path, plus every parent directory, must be owned by uid 0 and not
group/other-writable, otherwise nothing is rendered or applied. The apply script stages every
file as root under a dotted name, verifies it there (visudo -cf on the root-owned copy, sha256
of the agent and of the sudoers fragment) and only then renames; nothing live changes earlier.

Every outside effect (ssh, scp, ssh-keyscan, ssh-keygen, visudo, 1Password, the
confirmation) goes through an injectable seam: tests use fakes and never touch a host.

Stdlib only, Python 3.9 compatible.
"""

import argparse
import hashlib
import os
import re
import shlex
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

_LIB = os.path.dirname(os.path.abspath(__file__))
if _LIB not in sys.path:
    sys.path.insert(0, _LIB)

import inventory as inv  # noqa: E402
import notify  # noqa: E402
import orchestrate  # noqa: E402

AGENT_DEST = "/usr/local/libexec/fleet-agent"
SUDOERS_DEST = "/etc/sudoers.d/fleet-agent"
FORCED = 'restrict,command="%s"' % AGENT_DEST
OP_ITEM = "op://Private/Fleet"
CLOUDFLARED = "/usr/local/bin/cloudflared"
# Same search path as the agent itself, so both resolve to the same absolute path.
REMOTE_PATH = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

# kind -> closed list of root commands: (program, args). A program without "/" is
# resolved on the target; one with "/" is fixed by spec section 10.
CLOSED_LIST: Dict[str, List[Tuple[str, Tuple[str, ...]]]] = {
    "omv": [("omv-upgrade", ()), ("systemctl", ("reboot",))],
    "pikvm": [
        ("rw", ()), ("ro", ()), ("pikvm-update", ()),
        (CLOUDFLARED, ("update",)),
        ("systemctl", ("restart", "cloudflared")),
        ("systemctl", ("reboot",)),
    ],
}
# Non-interactive apt inside omv-upgrade (no extra command). The agent exports DEBIAN_FRONTEND
# and NEEDRESTART_MODE, but sudo resets the environment: this `env_keep` limited to the
# omv-upgrade command (together with `!requiretty` for the account) is what lets them through.
ENV_KEEP_FOR = {"omv": "omv-upgrade"}
AGENT_STAGE = "/usr/local/libexec/.fleet-agent.new"      # dotted name: never live
SUDOERS_STAGE = "/etc/sudoers.d/.fleet-agent.new"        # sudo ignores names containing a dot
SHA256 = re.compile(r"[0-9a-f]{64}")

ABS_PATH = re.compile(r"/[A-Za-z0-9_./+-]{1,200}")
PROGRAM = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,40}")
KEY_BLOB = re.compile(r"[A-Za-z0-9+/]+={0,2}")
HOSTKEY_LINE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]* ssh-ed25519 [A-Za-z0-9+/]+={0,2}")
REMOTE_TMP = re.compile(r"/(?:var/)?tmp/[A-Za-z0-9._-]{1,100}")
VERIFY_OK = re.compile(r"OK (/[A-Za-z0-9_./+-]{1,200}) (/[A-Za-z0-9_./+-]{1,200})")
VERIFY_BAD = re.compile(r"BAD (/[A-Za-z0-9_./+-]{1,200})")
# Run ON the target (read-only, no sudo). Arguments: <root uid> <trust anchor> <path>...
# (production: "0" and "/"; tests inject their own uid and a tmp anchor). For each path it
# prints `OK <requested> <canonical>` or `BAD <requested>`, where <canonical> is `readlink -f`.
# The canonical path must be an absolute regular file; it and EVERY ancestor up to the anchor
# must be owned by the root uid, not group/other-writable (stat %A: group w is char 6, other
# w char 9) and not a symlink; `stat -c` and `[ -L ]` do not follow links (lstat semantics).
VERIFY_SCRIPT = r'''U=$1; T=$2; shift 2
for p in "$@"; do
  r=$(readlink -f -- "$p" 2>/dev/null) || r=""
  case "$r" in /*) ;; *) echo "BAD $p"; continue ;; esac
  ok=1; d=$r
  { [ -f "$r" ] && [ ! -L "$r" ]; } || ok=0
  while :; do
    s=$(stat -c '%u %A' -- "$d" 2>/dev/null) || s=""
    case "$s" in "$U "*) ;; *) ok=0 ;; esac
    case "$s" in "$U "?????w*|"$U "????????w*) ok=0 ;; esac
    [ ! -L "$d" ] || ok=0
    [ "$d" = "$T" ] && break
    [ "$d" = / ] && break
    d=$(dirname -- "$d")
  done
  if [ "$ok" = 1 ]; then echo "OK $p $r"; else echo "BAD $p"; fi
done'''

Runner = Callable[[List[str], float], Tuple[int, str, str]]


class BootstrapError(Exception):
    """Something prevents bootstrapping; the message is safe to print."""


# ---------------------------------------------------------------- sudoers fragment


def sudoers_escape(text: str) -> str:
    """Backslash-escape the characters sudoers treats as syntax in a command line."""
    return re.sub(r"([,:=\\])", r"\\\1", text)


def programs_needed(kind: str) -> List[str]:
    seen: List[str] = []
    for program, _ in CLOSED_LIST[kind]:
        if "/" not in program and program not in seen:
            seen.append(program)
    return seen


def render_sudoers(kind: str, user: str, paths: Dict[str, str]) -> str:
    """The sudoers fragment for ``kind``: the closed list of section 10 and nothing more."""
    if kind not in CLOSED_LIST:
        raise BootstrapError("no sudoers list for kind %s" % kind)
    if not inv.SAFE_USER.fullmatch(user or ""):
        raise BootstrapError("unsafe user name")
    lines = [
        "# Generated by `fleet bootstrap` (spec fleet-updates, section 10). DO NOT EDIT BY HAND.",
        "# Closed list for kind %s: exact commands, no wildcard, no shell, no systemd-run." % kind,
        "Defaults:%s !requiretty" % user,
    ]
    keep = ENV_KEEP_FOR.get(kind)
    if keep:
        lines.append('Defaults!%s env_keep += "DEBIAN_FRONTEND NEEDRESTART_MODE"'
                     % sudoers_escape(_resolve(keep, paths)))
    for program, args in CLOSED_LIST[kind]:
        path = _resolve(program, paths)
        # A command without an argument list lets sudo accept ANY argument; the explicit
        # empty list `""` makes sudo refuse every argument (exact command only).
        argv = [sudoers_escape(a) for a in args] if args else ['""']
        command = " ".join([sudoers_escape(path)] + argv)
        lines.append("%s ALL=(root) NOPASSWD: %s" % (user, command))
    return "\n".join(lines) + "\n"


def _resolve(program: str, paths: Dict[str, str]) -> str:
    # `paths` holds the CANONICAL (readlink -f, verified) path of each command; a program with
    # a fixed path (cloudflared) is also looked up there by that path.
    path = paths.get(program, program if "/" in program else "")
    if not ABS_PATH.fullmatch(path or "") or ".." in path:
        raise BootstrapError("no absolute path for %s" % program)
    return path


def granted_commands(fragment: str) -> List[str]:
    """The ``NOPASSWD:`` command lines of a fragment, unescaped (used to prove it is the closed list)."""
    out = []
    for line in fragment.splitlines():
        if "NOPASSWD:" in line:
            out.append(re.sub(r"\\(.)", r"\1", line.split("NOPASSWD:", 1)[1].strip()))
    return out


def find_visudo(env: Dict[str, str]) -> Optional[str]:
    if env.get("FLEET_VISUDO"):
        return env["FLEET_VISUDO"]
    for cand in (shutil.which("visudo"), "/usr/sbin/visudo", "/usr/bin/visudo"):
        if cand and os.access(cand, os.X_OK):
            return cand
    return None


def validate_fragment(fragment: str, env: Dict[str, str], run: Runner, workdir: Path) -> Tuple[bool, str]:
    """(valid, message): `visudo -cf` on the rendered fragment written to a temp file."""
    visudo = find_visudo(env)
    if visudo is None:
        return False, "visudo not found: cannot validate"
    path = workdir / "fleet-sudoers"
    path.write_text(fragment, encoding="utf-8")
    os.chmod(str(path), 0o440)
    rc, out, err = run([visudo, "-cf", str(path)], 30)
    text = " ".join((out + " " + err).split())[:200]
    return rc == 0, text or "visudo exit %d" % rc


# ---------------------------------------------------------------- keys / host key


def authorized_lines(masters: Sequence[str], env: Dict[str, str],
                     op: Callable[[List[str]], str]) -> Tuple[List[str], List[str]]:
    """(authorized_keys lines, masters whose public key could not be read or is malformed)."""
    lines: List[str] = []
    missing: List[str] = []
    for master in masters:
        try:
            raw = op(["op", "read", "%s/public-key-%s" % (OP_ITEM, master)]).strip().split()
        except Exception:  # noqa: BLE001 (op missing/locked: reported, not fatal here)
            raw = []
        if len(raw) < 2 or raw[0] != "ssh-ed25519" or not KEY_BLOB.fullmatch(raw[1]):
            missing.append(master)
            continue
        lines.append("%s %s %s fleet-master-%s" % (FORCED, raw[0], raw[1], master))
    return lines, missing


def scan_host_key(run: Runner, env: Dict[str, str], name: str) -> str:
    """The target's ed25519 host key as a known_hosts line (ssh-keyscan, read-only)."""
    rc, out, _ = run([env.get("FLEET_SSH_KEYSCAN", "ssh-keyscan"), "-t", "ed25519", "-T", "10", name], 30)
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 3 and parts[1] == "ssh-ed25519":
            candidate = "%s %s %s" % (name, parts[1], parts[2])
            if HOSTKEY_LINE.fullmatch(candidate):
                return candidate
    raise BootstrapError("cannot read the ed25519 host key of %s (rc %d)" % (name, rc))


def fingerprint(run: Runner, env: Dict[str, str], line: str, workdir: Path) -> str:
    path = workdir / "hostkey.pub"
    path.write_text(line.split(" ", 1)[1] + "\n", encoding="utf-8")
    rc, out, _ = run([env.get("FLEET_SSH_KEYGEN", "ssh-keygen"), "-lf", str(path)], 15)
    return " ".join(out.split())[:120] if rc == 0 else "(fingerprint unavailable)"


# ---------------------------------------------------------------- remote side


def ssh_argv(env: Dict[str, str], known_hosts: Path, target: str, remote: str) -> List[str]:
    argv = [env.get("FLEET_SSH", "ssh"), "-o", "BatchMode=yes", "-o", "ConnectTimeout=10",
            "-o", "StrictHostKeyChecking=yes", "-o", "UserKnownHostsFile=%s" % known_hosts]
    if env.get("FLEET_SSH_IDENTITY"):
        argv += ["-i", env["FLEET_SSH_IDENTITY"], "-o", "IdentitiesOnly=yes"]
    return argv + ["-T", "--", target, remote]


def scp_argv(env: Dict[str, str], known_hosts: Path, sources: Sequence[str], target: str, dest: str) -> List[str]:
    argv = [env.get("FLEET_SCP", "scp"), "-q", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes",
            "-o", "UserKnownHostsFile=%s" % known_hosts]
    if env.get("FLEET_SSH_IDENTITY"):
        argv += ["-i", env["FLEET_SSH_IDENTITY"], "-o", "IdentitiesOnly=yes"]
    return argv + ["--"] + list(sources) + ["%s:%s/" % (target, dest)]


def resolve_remote_paths(run: Runner, env: Dict[str, str], known_hosts: Path, target: str,
                         names: Sequence[str], given: Dict[str, str]) -> Dict[str, str]:
    """`command -v` on the target for each program (read-only). Operator overrides win."""
    paths = dict(given)
    for name in names:
        if name in paths:
            continue
        if not PROGRAM.fullmatch(name):
            raise BootstrapError("unsafe program name")
        remote = "PATH='%s'; command -v %s" % (REMOTE_PATH, name)   # fixed PATH: never the account's own
        rc, out, _ = run(ssh_argv(env, known_hosts, target, remote), 30)
        found = out.strip().splitlines()[0].strip() if out.strip() else ""
        if rc != 0 or not ABS_PATH.fullmatch(found) or ".." in found:
            raise BootstrapError("%s not found on the target (command -v)" % name)
        paths[name] = found
    return paths


def _clean_path(path: str) -> bool:
    return bool(ABS_PATH.fullmatch(path)) and ".." not in path and "//" not in path


def verify_trusted(run: Runner, env: Dict[str, str], known_hosts: Path, target: str,
                   paths: Sequence[str]) -> Dict[str, str]:
    """{requested path: canonical path}. Refuses unless every canonical path (`readlink -f` on
    the target) is a regular file and it and all its ancestors are root-owned, not
    group/other-writable and not symlinks. The target's answer is untrusted: parsed strictly."""
    wanted = sorted(set(paths))
    for path in wanted:
        if not _clean_path(path):
            raise BootstrapError("unsafe path %r" % path[:60])
    remote = "sh -c %s fleet-verify 0 / %s" % (shlex.quote(VERIFY_SCRIPT), " ".join(shlex.quote(p) for p in wanted))
    rc, out, _ = run(ssh_argv(env, known_hosts, target, remote), 30)
    seen: Dict[str, str] = {}
    for line in out.splitlines():
        ok, bad = VERIFY_OK.fullmatch(line), VERIFY_BAD.fullmatch(line)
        match = ok or bad
        if not match or match.group(1) not in wanted or match.group(1) in seen:
            raise BootstrapError("unparseable answer while checking path ownership on the target")
        if ok and not _clean_path(ok.group(2)):
            raise BootstrapError("unusable canonical path returned for %s" % match.group(1))
        seen[match.group(1)] = ok.group(2) if ok else ""
    if rc != 0 or set(seen) != set(wanted):
        raise BootstrapError("cannot verify path ownership on the target (rc %d)" % rc)
    untrusted = [p for p in wanted if not seen[p]]
    if untrusted:
        raise BootstrapError("untrusted path on the target (not a root-owned regular file, or a symlink, "
                             "or group/other-writable somewhere in its parents): %s" % ", ".join(untrusted))
    return seen


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def apply_script(kind: str, masters: Sequence[str], paths: Dict[str, str], agent_sha: str,
                 sudoers_sha: str) -> str:
    """POSIX sh run ON the target. Stage + verify everything, rename at the very end (nothing
    live changes before). PiKVM: all inside one rw window, ro restored by trap."""
    for master in masters:
        if not re.fullmatch(r"[A-Za-z0-9_-]+", master):
            raise BootstrapError("unsafe master name")
    if not SHA256.fullmatch(agent_sha or "") or not SHA256.fullmatch(sudoers_sha or ""):
        raise BootstrapError("bad sha256")
    q = shlex.quote
    # first bootstrap needs root or NOPASSWD sudo: `sudo -n` fails fast, never waits for a password
    out = ["#!/bin/sh", "set -eu", 'D="$(cd "$(dirname "$0")" && pwd)"',
           'SUDO="sudo -n"; [ "$(id -u)" = 0 ] && SUDO=""']
    if kind == "pikvm":
        out += ["RW=%s" % q(paths["rw"]), "RO=%s" % q(paths["ro"]),
                'restore_ro() { rc=$?; trap - EXIT; if ! $SUDO "$RO"; then',
                '  echo "fleet-bootstrap: ERROR: ro failed, the filesystem may still be read-write" >&2',
                '  [ "$rc" -ne 0 ] || rc=1; fi; exit "$rc"; }',
                "trap restore_ro EXIT",
                # SIGKILL cannot be trapped; HUP/INT/TERM still run the EXIT trap (ro)
                "trap 'exit 1' HUP INT TERM", '$SUDO "$RW"']
    out += [
        "$SUDO install -d -o root -g root -m 0755 %s" % q(os.path.dirname(AGENT_DEST)),
        # --- stage as root under dotted names, verify the ROOT-OWNED copies
        '$SUDO install -o root -g root -m 0755 "$D/fleet-agent" %s' % q(AGENT_STAGE),
        'GOT=$($SUDO sha256sum %s | cut -d" " -f1)' % q(AGENT_STAGE),
        '[ "$GOT" = %s ] || { echo "fleet-bootstrap: agent sha256 mismatch" >&2; exit 1; }' % agent_sha,
        '$SUDO install -o root -g root -m 0440 "$D/fleet-sudoers" %s' % q(SUDOERS_STAGE),
        'GOT=$($SUDO sha256sum %s | cut -d" " -f1)' % q(SUDOERS_STAGE),
        '[ "$GOT" = %s ] || { echo "fleet-bootstrap: sudoers sha256 mismatch" >&2; exit 1; }' % sudoers_sha,
        '$SUDO %s -cf %s' % (q(paths["visudo"]), q(SUDOERS_STAGE)),
        'AK="$HOME/.ssh/authorized_keys"; mkdir -p "$HOME/.ssh"; chmod 700 "$HOME/.ssh"',
        '[ -f "$AK" ] || : > "$AK"',
        'cp "$AK" "$D/ak.new"',
    ]
    for master in masters:
        # grep exits 1 when nothing is left (fine); 2 or more is an error and must abort
        out.append("rc=0; grep -v -e ' fleet-master-%s$' \"$D/ak.new\" > \"$D/ak.tmp\" || rc=$?; "
                   "[ \"$rc\" -le 1 ] || { echo 'fleet-bootstrap: grep failed' >&2; exit 1; }; "
                   "mv \"$D/ak.tmp\" \"$D/ak.new\"" % master)
    out += ['cat "$D/authorized.lines" >> "$D/ak.new"',
            'cp "$D/ak.new" "$AK.fleet-new" && chmod 600 "$AK.fleet-new"',
            # --- commit: renames only, at the very end
            '$SUDO mv -f %s %s' % (q(AGENT_STAGE), q(AGENT_DEST)),
            '$SUDO mv -f %s %s' % (q(SUDOERS_STAGE), q(SUDOERS_DEST)),
            'mv -f "$AK.fleet-new" "$AK"',
            "echo fleet-bootstrap: done"]
    return "\n".join(out) + "\n"


def pin_known_host(path: Path, line: str, run: Runner, env: Dict[str, str], write: bool = True) -> bool:
    """Pin the verified host key in known_hosts (0600). True if added, False if already there.

    Refuses (BootstrapError "host key mismatch") when a DIFFERENT key is already pinned for the
    name (`ssh-keygen -F`). ``write=False`` only performs the check."""
    name, keytype, blob = line.split(" ")
    if path.exists():
        rc, out, _ = run([env.get("FLEET_SSH_KEYGEN", "ssh-keygen"), "-F", name, "-f", str(path)], 15)
        found = []
        for entry in out.splitlines():
            parts = entry.split()
            if rc == 0 and len(parts) >= 3 and not entry.startswith("#"):
                found.append((parts[-2], parts[-1]))
        if (keytype, blob) in found:
            return False
        if found:
            raise BootstrapError("host key mismatch: a different key is already pinned for %s in %s"
                                 % (name, path))
    if not write:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    with os.fdopen(fd, "a", encoding="utf-8") as handle:
        handle.write(("" if not existing or existing.endswith("\n") else "\n") + line + "\n")
    return True


# ---------------------------------------------------------------- confirmation / CLI


def tty_confirm(alias: str, detail: str = "") -> bool:
    """Explicit confirmation: type the host alias on a terminal. No terminal => declined.
    ``detail`` (host key fingerprint, agent sha256) is part of the prompt text."""
    if not sys.stdin.isatty():
        return False
    sys.stderr.write("Apply the changes above to %s?%s Type the host name to confirm: "
                     % (alias, (" " + detail) if detail else ""))
    sys.stderr.flush()
    return sys.stdin.readline().strip() == alias


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="fleet bootstrap")
    ap.add_argument("host")
    ap.add_argument("--user", required=True, help="account on the target: runs the agent, needs sudo to install")
    ap.add_argument("--apply", action="store_true", help="apply after review + confirmation (default: dry run)")
    ap.add_argument("--path", action="append", default=[], metavar="NAME=/abs/path",
                    help="use this absolute path instead of `command -v` on the target")
    return ap


def _given_paths(items: Sequence[str]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for item in items:
        name, _, path = item.partition("=")
        if not PROGRAM.fullmatch(name) or not ABS_PATH.fullmatch(path) or ".." in path:
            raise BootstrapError("bad --path %r (expected NAME=/absolute/path)" % item[:40])
        out[name] = path
    return out


def _show(out: Any, title: str, body: str) -> None:
    out.write("--- %s\n%s\n" % (title, body.rstrip("\n")))


def main(
    argv: Sequence[str], env: Optional[Dict[str, str]] = None, run: Optional[Runner] = None,
    confirm: Optional[Callable[[str], bool]] = None, op: Optional[Callable[[List[str]], str]] = None,
    out: Any = None, err: Any = None, agent_path: Optional[str] = None,
) -> int:
    env = dict(os.environ) if env is None else env
    out, err = out or sys.stdout, err or sys.stderr
    try:
        args = build_parser().parse_args(list(argv))
    except SystemExit as exc:
        return int(exc.code or 0) if isinstance(exc.code, int) else 2
    run = run or (lambda cmd, timeout: orchestrate.run_capped(cmd, timeout, env=env))
    op = op or (lambda a: notify.default_op_runner(a, env))
    confirm = confirm or tty_confirm
    workdir = Path(tempfile.mkdtemp(prefix="fleet-bootstrap-"))
    try:
        return _bootstrap(args, env, run, confirm, op, out, err, workdir, agent_path)
    except BootstrapError as exc:
        err.write("fleet bootstrap: %s\n" % exc)
        return 2
    finally:
        shutil.rmtree(str(workdir), ignore_errors=True)


def _bootstrap(args: argparse.Namespace, env: Dict[str, str], run: Runner,
               confirm: Callable[[str], bool], op: Callable[[List[str]], str], out: Any, err: Any,
               workdir: Path, agent_path: Optional[str]) -> int:
    fleet_dir = env.get("FLEET_DIR") or os.path.join(
        env.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share"), "fleet")
    try:
        data = inv.load_inventory(env.get("FLEET_YML") or os.path.join(fleet_dir, "fleet.yml"))
    except inv.InventoryError as exc:
        raise BootstrapError(str(exc))
    if args.host not in data["hosts"]:
        raise BootstrapError("unknown host")
    host = data["hosts"][args.host]
    kind, name = host["kind"], host["tailnet_name"]
    if kind not in CLOSED_LIST:
        raise BootstrapError("kind %s is not bootstrapped here (chezmoi installs the agent on Linux "
                             "kinds; opnsense and homeassistant have no agent, only an API)" % kind)
    if not inv.SAFE_USER.fullmatch(args.user):
        raise BootstrapError("unsafe --user")
    agent = Path(agent_path or os.path.join(fleet_dir, "agent", "fleet-agent.sh"))
    if not agent.is_file():
        raise BootstrapError("agent script not found: %s" % agent)
    target = "%s@%s" % (args.user, name)
    masters = list(data.get("masters") or [])

    host_key = scan_host_key(run, env, name)
    known = workdir / "known_hosts"       # scratch: only the key shown below is trusted for this run
    known.write_text(host_key + "\n", encoding="utf-8")
    kh = Path(env.get("FLEET_KNOWN_HOSTS") or os.path.expanduser("~/.ssh/known_hosts"))
    pin_known_host(kh, host_key, run, env, write=False)       # refuse early on a key mismatch
    paths = resolve_remote_paths(run, env, known, target, programs_needed(kind) + ["visudo"],
                                 _given_paths(args.path))
    to_check = [paths[n] for n in programs_needed(kind) + ["visudo"]]
    if kind == "pikvm":
        to_check += [paths["rw"], paths["ro"], CLOUDFLARED]
    canonical = verify_trusted(run, env, known, target, to_check)
    # From here on ONLY the canonical (checked) paths are used: fragment, display, apply script.
    paths = dict((n, canonical[p]) for n, p in paths.items() if p in canonical)
    if kind == "pikvm":
        paths[CLOUDFLARED] = canonical[CLOUDFLARED]
    fragment = render_sudoers(kind, args.user, paths)
    valid, vmsg = validate_fragment(fragment, env, run, workdir)
    keys, missing = authorized_lines(masters, env, op)
    agent_sha = sha256_hex(agent.read_bytes())
    script = apply_script(kind, masters, paths, agent_sha, sha256_hex(fragment.encode("utf-8")))
    fp = fingerprint(run, env, host_key, workdir)

    _show(out, "host", "%s (%s, %s) -> %s" % (args.host, kind, host["site"], target))
    _show(out, "host key to pin (check the fingerprint)", "%s\n%s" % (host_key, fp))
    _show(out, "sudoers fragment -> %s" % SUDOERS_DEST, fragment)
    _show(out, "visudo -cf", ("OK: " if valid else "INVALID: ") + vmsg)
    _show(out, "authorized_keys lines (forced command)", "\n".join(keys) or "(none)")
    _show(out, "agent sha256 (verified on the target before it goes live)", agent_sha)
    _show(out, "apply script (runs on the target)", script)
    if kind == "pikvm":
        _show(out, "PiKVM", "everything is applied inside ONE rw window; ro is restored by a trap")
    if missing:
        out.write("WARNING: no usable public key in 1Password for: %s\n" % ", ".join(missing))
    if not args.apply:
        out.write("DRY RUN: nothing was applied. Review the above, then re-run with --apply.\n")
        return 0 if valid else 1
    if not valid:
        raise BootstrapError("the sudoers fragment is invalid: nothing applied")
    if missing:
        raise BootstrapError("missing master public keys: nothing applied")
    detail = "host key %s; agent sha256 %s." % (fp, agent_sha)
    if not (confirm(args.host, detail) if confirm is tty_confirm else confirm(args.host)):
        err.write("fleet bootstrap: not confirmed, nothing applied\n")
        return 1
    return _apply(args, env, run, out, err, workdir, agent, script, fragment, keys, known,
                  target, host_key, kh)


def _apply(args: argparse.Namespace, env: Dict[str, str], run: Runner, out: Any, err: Any, workdir: Path,
           agent: Path, script: str, fragment: str,
           keys: List[str], known: Path, target: str, host_key: str, kh: Path) -> int:
    (workdir / "authorized.lines").write_text("\n".join(keys) + "\n", encoding="utf-8")
    (workdir / "apply.sh").write_text(script, encoding="utf-8")
    shutil.copyfile(str(agent), str(workdir / "fleet-agent"))
    rc, tmp_out, _ = run(ssh_argv(env, known, target, "mktemp -d"), 30)
    remote = tmp_out.strip().splitlines()[0].strip() if tmp_out.strip() else ""
    if (rc != 0 or not REMOTE_TMP.fullmatch(remote) or ".." in remote
            or not remote.rsplit("/", 1)[1].strip(".")):
        err.write("fleet bootstrap: cannot create a temp dir on the target\n")
        return 2
    files = [str(workdir / n) for n in ("fleet-agent", "fleet-sudoers", "authorized.lines", "apply.sh")]
    rc, _, serr = run(scp_argv(env, known, files, target, remote), 120)
    if rc != 0:
        err.write("fleet bootstrap: copy failed (%s)\n" % " ".join(serr.split())[:120])
        return 2
    rc, rout, serr = run(ssh_argv(env, known, target, "sh %s/apply.sh; rc=$?; rm -rf %s; exit $rc"
                                  % (shlex.quote(remote), shlex.quote(remote))), 300)
    if rc != 0:
        err.write("fleet bootstrap: apply failed on the target (exit %d): %s\n"
                  % (rc, " ".join((rout + " " + serr).split())[-160:]))
        return 2
    added = pin_known_host(kh, host_key, run, env)
    out.write("applied on %s%s. Set ssh_user: %s in fleet.yml, then run `fleet check %s`.\n"
              % (args.host, ("; host key pinned in %s" % kh) if added else "", args.user, args.host))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
