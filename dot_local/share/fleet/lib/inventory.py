#!/usr/bin/env python3
"""Fleet inventory: read and validate fleet.yml, merge Tailscale peer state.

Runs on stock macOS Python 3.9: standard library only (no PyYAML, no PEP 604).

fleet.yml uses a RESTRICTED YAML SUBSET, parsed here by hand:

* block mappings nested by indentation (spaces only, any consistent step);
* keys: letters, digits, ``_ . -`` ;
* scalars: ``true``/``false``, ``null`` (or ``~``), integers, plain strings,
  single- or double-quoted strings (no escapes beyond the quote itself);
* flow sequences on ONE line: ``[a, b, c]`` (items are scalars);
* flow mappings on ONE line, flat: ``{k: v, k2: v2}``;
* comments: a line starting with ``#``, or `` #`` after a value. Do not put a
  trailing comment on ``kind:`` / ``site:`` lines (INVARIANTS.md greps them).

Not supported (rejected or ignored by design): block sequences (``- x``),
anchors/aliases, multi-line scalars, tags, documents (``---``).

Validation rules (spec section 12 / INVARIANTS.md): ``kind`` and ``site`` from
closed lists, ``critical: true`` if and only if kind is opnsense or proxmox,
groups reference existing aliases, one canary per kind at most, timeouts only
for known kinds.

CLI (used by dot_local/bin/executable_fleet):
    inventory.py validate [--file F]
    inventory.py plan [--file F] [alias ...]   TSV: alias kind site user tailnet state last_seen
    inventory.py agent-line                    stdin = agent output, prints TSV summary
"""

import json
import os
import re
import subprocess
import sys
from typing import Any, Dict, List, Optional, Tuple

KINDS = (
    "chezmoi-linux", "chezmoi-macos", "omv", "pikvm", "homeassistant",
    "opnsense", "proxmox", "windows", "guardian",
)
SITES = ("dijon", "nice", "garage", "cloud", "mobile")
CRITICAL_KINDS = ("opnsense", "proxmox")
AGENT_STATUSES = (
    "started", "running", "updated", "up-to-date", "degraded", "failed",
    "busy", "skipped", "unsupported",
)
DEFAULT_TIMEOUTS = {
    "chezmoi-linux": 30, "chezmoi-macos": 30, "omv": 30, "pikvm": 20,
    "homeassistant": 45, "windows": 120, "opnsense": 30, "proxmox": 45,
    "guardian": 30,
}
HOST_FIELDS = (
    "tailnet_name", "site", "kind", "critical", "ssh_user", "tags", "canary",
    "critical_services", "timeout_min",
)
REQUIRED_HOST_FIELDS = ("tailnet_name", "site", "kind", "critical")
SAFE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
SAFE_SERVICE = re.compile(r"^[A-Za-z0-9_.@:-]+$")
SAFE_USER = re.compile(r"^[a-z_][a-z0-9_.-]*$")


class InventoryError(Exception):
    """fleet.yml unreadable or invalid. The message lists every problem."""


# ---------------------------------------------------------------- YAML subset


def _strip_comment(text: str) -> str:
    """Remove a trailing ' #...' comment that is outside quotes."""
    quote = ""
    for i, ch in enumerate(text):
        if quote:
            if ch == quote:
                quote = ""
        elif ch in ("'", '"'):
            quote = ch
        elif ch == "#" and (i == 0 or text[i - 1] in " \t"):
            return text[:i]
    return text


def _scalar(token: str) -> Any:
    token = token.strip()
    if token == "" or token in ("null", "~"):
        return None
    if token == "true":
        return True
    if token == "false":
        return False
    if len(token) >= 2 and token[0] == token[-1] and token[0] in ("'", '"'):
        return token[1:-1]
    if re.fullmatch(r"-?\d+", token):
        return int(token)
    return token


def _split_flow(body: str) -> List[str]:
    parts: List[str] = []
    cur = ""
    quote = ""
    for ch in body:
        if quote:
            cur += ch
            if ch == quote:
                quote = ""
        elif ch in ("'", '"'):
            quote = ch
            cur += ch
        elif ch == ",":
            parts.append(cur)
            cur = ""
        else:
            cur += ch
    if cur.strip() != "" or parts:
        parts.append(cur)
    return [p for p in parts if p.strip() != ""]


def _value(token: str) -> Any:
    token = token.strip()
    if token.startswith("["):
        if not token.endswith("]"):
            raise ValueError("unterminated flow sequence")
        return [_scalar(p) for p in _split_flow(token[1:-1])]
    if token.startswith("{"):
        if not token.endswith("}"):
            raise ValueError("unterminated flow mapping")
        out: Dict[str, Any] = {}
        for part in _split_flow(token[1:-1]):
            if ":" not in part:
                raise ValueError("flow mapping item without ':'")
            k, v = part.split(":", 1)
            out[k.strip()] = _scalar(v)
        return out
    return _scalar(token)


_KEY_LINE = re.compile(r"^([A-Za-z0-9_.-]+):(?:\s+(.*))?$")


def parse_yaml_subset(text: str) -> Dict[str, Any]:
    """Parse the restricted subset documented in the module docstring."""
    root: Dict[str, Any] = {}
    stack: List[Tuple[int, Dict[str, Any]]] = [(-1, root)]
    for lineno, raw in enumerate(text.splitlines(), 1):
        if "\t" in raw[: len(raw) - len(raw.lstrip())]:
            raise ValueError("line %d: tabs are not allowed for indentation" % lineno)
        line = _strip_comment(raw).rstrip()
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        content = line.strip()
        if content.startswith("- ") or content == "-":
            raise ValueError("line %d: block sequences are not supported, use [a, b]" % lineno)
        match = _KEY_LINE.match(content)
        if not match:
            raise ValueError("line %d: cannot parse %r" % (lineno, content))
        key, rest = match.group(1), match.group(2)
        while stack and stack[-1][0] >= indent:
            stack.pop()
        if not stack:
            raise ValueError("line %d: bad indentation" % lineno)
        parent = stack[-1][1]
        if key in parent:
            raise ValueError("line %d: duplicate key %r" % (lineno, key))
        if rest is None or rest.strip() == "":
            child: Dict[str, Any] = {}
            parent[key] = child
            stack.append((indent, child))
        else:
            try:
                parent[key] = _value(rest)
            except ValueError as exc:
                raise ValueError("line %d: %s" % (lineno, exc))
    return root


# ---------------------------------------------------------------- validation


def validate(data: Dict[str, Any]) -> List[str]:
    """Return the list of problems (empty = valid)."""
    errors: List[str] = []
    hosts = data.get("hosts")
    if not isinstance(hosts, dict) or not hosts:
        return ["hosts: missing or empty"]
    tailnet_seen: Dict[str, str] = {}
    canary_by_kind: Dict[str, str] = {}
    for alias, host in hosts.items():
        where = "hosts.%s" % alias
        if not SAFE_NAME.match(str(alias)):
            errors.append("%s: invalid alias" % where)
        if not isinstance(host, dict):
            errors.append("%s: must be a mapping" % where)
            continue
        for field in host:
            if field not in HOST_FIELDS:
                errors.append("%s: unknown field %r" % (where, field))
        for field in REQUIRED_HOST_FIELDS:
            if field not in host:
                errors.append("%s: missing %s" % (where, field))
        kind, site = host.get("kind"), host.get("site")
        if kind is not None and kind not in KINDS:
            errors.append("%s: kind %r not in %s" % (where, kind, ", ".join(KINDS)))
        if site is not None and site not in SITES:
            errors.append("%s: site %r not in %s" % (where, site, ", ".join(SITES)))
        critical = host.get("critical")
        if "critical" in host and not isinstance(critical, bool):
            errors.append("%s: critical must be true or false" % where)
        elif kind in KINDS and isinstance(critical, bool):
            if critical != (kind in CRITICAL_KINDS):
                errors.append(
                    "%s: critical must be %s for kind %s"
                    % (where, "true" if kind in CRITICAL_KINDS else "false", kind)
                )
        name = host.get("tailnet_name")
        if name is not None:
            if not isinstance(name, str) or not SAFE_NAME.match(name):
                errors.append("%s: invalid tailnet_name" % where)
            elif name.lower() in tailnet_seen:
                errors.append("%s: tailnet_name also used by %s" % (where, tailnet_seen[name.lower()]))
            else:
                tailnet_seen[name.lower()] = str(alias)
        user = host.get("ssh_user")
        if user is not None and (not isinstance(user, str) or not SAFE_USER.match(user)):
            errors.append("%s: invalid ssh_user" % where)
        for listed in ("tags", "critical_services"):
            vals = host.get(listed)
            if vals is not None and (not isinstance(vals, list) or not all(isinstance(v, str) for v in vals)):
                errors.append("%s: %s must be a list of strings" % (where, listed))
        for svc in host.get("critical_services") or []:
            if isinstance(svc, str) and not SAFE_SERVICE.match(svc):
                errors.append("%s: unsafe service name %r" % (where, svc))
        if "canary" in host:
            if not isinstance(host["canary"], bool):
                errors.append("%s: canary must be true or false" % where)
            elif host["canary"] and kind in KINDS:
                if kind in canary_by_kind:
                    errors.append("%s: kind %s already has canary %s" % (where, kind, canary_by_kind[kind]))
                canary_by_kind[kind] = str(alias)
        tmo = host.get("timeout_min")
        if tmo is not None and (not isinstance(tmo, int) or isinstance(tmo, bool) or tmo <= 0):
            errors.append("%s: timeout_min must be a positive integer" % where)
    groups = data.get("groups") or {}
    if not isinstance(groups, dict):
        errors.append("groups: must be a mapping")
    else:
        for gname, members in groups.items():
            if not isinstance(members, list):
                errors.append("groups.%s: must be a list" % gname)
                continue
            for member in members:
                if member not in hosts:
                    errors.append("groups.%s: unknown host %r" % (gname, member))
    timeouts = data.get("timeouts") or {}
    if not isinstance(timeouts, dict):
        errors.append("timeouts: must be a mapping")
    else:
        for tkind, minutes in timeouts.items():
            if tkind not in KINDS:
                errors.append("timeouts.%s: unknown kind" % tkind)
            elif not isinstance(minutes, int) or isinstance(minutes, bool) or minutes <= 0:
                errors.append("timeouts.%s: must be a positive integer" % tkind)
    return errors


def load_inventory(path: str) -> Dict[str, Any]:
    """Read, parse and validate fleet.yml; raise InventoryError with all problems."""
    try:
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
    except OSError as exc:
        raise InventoryError("cannot read %s: %s" % (path, exc))
    try:
        data = parse_yaml_subset(text)
    except ValueError as exc:
        raise InventoryError("%s: %s" % (path, exc))
    problems = validate(data)
    if problems:
        raise InventoryError("%s invalid:\n  - %s" % (path, "\n  - ".join(problems)))
    return data


def timeout_for(data: Dict[str, Any], alias: str) -> int:
    """Update timeout in minutes: host override, else timeouts.<kind>, else default."""
    host = data["hosts"][alias]
    if host.get("timeout_min"):
        return int(host["timeout_min"])
    configured = (data.get("timeouts") or {}).get(host["kind"])
    return int(configured or DEFAULT_TIMEOUTS[host["kind"]])


def group_members(data: Dict[str, Any], group: str) -> List[str]:
    groups = data.get("groups") or {}
    if group not in groups:
        raise InventoryError("unknown group %r" % group)
    return list(groups[group])


# ---------------------------------------------------------------- Tailscale


def parse_tailscale(status: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Map lower-case DNS label -> {online, last_seen, os, tags} from `tailscale status --json`."""
    peers: Dict[str, Dict[str, Any]] = {}
    entries = list((status.get("Peer") or {}).values())
    if isinstance(status.get("Self"), dict):
        entries.append(status["Self"])
    for peer in entries:
        dns = str(peer.get("DNSName") or "").rstrip(".")
        label = dns.split(".")[0].lower() if dns else str(peer.get("HostName") or "").lower()
        if not label:
            continue
        last_seen = peer.get("LastSeen")
        if isinstance(last_seen, str) and last_seen.startswith("0001-"):
            last_seen = None
        peers[label] = {
            "online": bool(peer.get("Online")),
            "last_seen": last_seen,
            "os": peer.get("OS"),
            "tags": list(peer.get("Tags") or []),
        }
    return peers


def read_tailscale(runner: Optional[Any] = None) -> Optional[Dict[str, Dict[str, Any]]]:
    """Run `tailscale status --json`; None when Tailscale is unavailable."""
    try:
        if runner is not None:
            raw = runner()
        else:
            proc = subprocess.run(
                ["tailscale", "status", "--json"], capture_output=True, text=True, timeout=15
            )
            if proc.returncode != 0:
                return None
            raw = proc.stdout
        return parse_tailscale(json.loads(raw))
    except (OSError, ValueError, subprocess.SubprocessError):
        return None


def peer_state(tailnet_name: str, peers: Optional[Dict[str, Dict[str, Any]]]) -> Tuple[str, Optional[str]]:
    """('online'|'offline'|'absent'|'unknown', last_seen) for one host."""
    if peers is None:
        return "unknown", None
    peer = peers.get(tailnet_name.lower())
    if peer is None:
        return "absent", None
    if peer["online"]:
        return "online", peer["last_seen"]
    return "offline", peer["last_seen"]


# ---------------------------------------------------------------- agent output


def summarize_agent_output(text: str) -> Dict[str, Any]:
    """Validate one agent answer (untrusted) and reduce it to safe display fields.

    Anything that is not a schema-v1 object with a known status becomes
    ``failed``; control characters are stripped so the terminal is never driven
    by remote data.
    """
    lines = [ln for ln in text.splitlines() if ln.strip()]
    bad = {"status": "failed", "reason": "invalid agent output", "packages": None, "reboot_required": None}
    if len(lines) != 1:
        return bad
    try:
        data = json.loads(lines[0])
    except ValueError:
        return bad
    if not isinstance(data, dict) or data.get("schema") != 1 or data.get("status") not in AGENT_STATUSES:
        return bad
    reason = data.get("reason")
    packages = data.get("packages")
    reboot = data.get("reboot_required")
    return {
        "status": data["status"],
        "reason": re.sub(r"[^\x20-\x7e]", "?", str(reason))[:200] if reason else "",
        "packages": packages if isinstance(packages, int) and not isinstance(packages, bool) else None,
        "reboot_required": reboot if isinstance(reboot, bool) else None,
    }


# ---------------------------------------------------------------- CLI


def plan_rows(
    data: Dict[str, Any],
    aliases: List[str],
    peers: Optional[Dict[str, Dict[str, Any]]],
) -> List[List[str]]:
    hosts = data["hosts"]
    unknown = [a for a in aliases if a not in hosts]
    if unknown:
        raise InventoryError("unknown host(s): %s" % ", ".join(unknown))
    rows: List[List[str]] = []
    for alias in aliases or list(hosts):
        host = hosts[alias]
        state, last_seen = peer_state(host["tailnet_name"], peers)
        rows.append([
            alias, host["kind"], host["site"], host.get("ssh_user") or "-",
            host["tailnet_name"], state, last_seen or "-",
        ])
    return rows


def _default_file() -> str:
    base = os.environ.get("FLEET_DIR") or os.path.join(
        os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share"), "fleet"
    )
    return os.environ.get("FLEET_YML") or os.path.join(base, "fleet.yml")


def main(argv: List[str]) -> int:
    args = list(argv)
    path = _default_file()
    if "--file" in args:
        i = args.index("--file")
        path = args[i + 1]
        del args[i:i + 2]
    cmd = args[0] if args else ""
    rest = args[1:]
    if cmd == "agent-line":
        s = summarize_agent_output(sys.stdin.read())
        print("\t".join([
            s["status"], s["reason"],
            "" if s["packages"] is None else str(s["packages"]),
            "" if s["reboot_required"] is None else ("yes" if s["reboot_required"] else "no"),
        ]))
        return 0
    try:
        data = load_inventory(path)
        if cmd == "validate":
            print("ok: %d hosts" % len(data["hosts"]))
            return 0
        if cmd == "plan":
            wanted: List[str] = []
            for item in rest:
                wanted.extend(p for p in item.split(",") if p)
            if rest and not wanted:
                raise InventoryError("empty host selector")
            for row in plan_rows(data, wanted, read_tailscale()):
                print("\t".join(row))
            return 0
    except InventoryError as exc:
        sys.stderr.write("fleet: %s\n" % exc)
        return 2
    sys.stderr.write("usage: inventory.py validate|plan|agent-line [--file F] [alias ...]\n")
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
