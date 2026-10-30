#!/usr/bin/env python3
"""Validation of the agents' JSON v1 output, and secret masking.

Agent output is UNTRUSTED. Everything the master renders, stores or notifies is
first rebuilt here from the validated fields: unknown keys are dropped, strings
are stripped of control characters, capped and masked. A single invalid byte of
structure makes the host ``failed``. The result is never interpolated into a
shell command anywhere in fleet.

Status vocabulary (spec section 12):
  agent  : "started" "running" "updated" "up-to-date" "degraded" "failed"
           "busy" "skipped" "unsupported"
  master : "offline" "unreachable" "timeout" "held"   (never accepted from an agent)

Stdlib only, Python 3.9 compatible.
"""

import json
import re
from typing import Any, Dict, List, Optional, Tuple

AGENT_STATUSES = (
    "started", "running", "updated", "up-to-date", "degraded", "failed",
    "busy", "skipped", "unsupported",
)
MASTER_STATUSES = ("offline", "unreachable", "timeout", "held")
ALL_STATUSES = AGENT_STATUSES + MASTER_STATUSES
VERBS = ("check", "update", "reboot-status", "reboot", "report")
FINAL_STATUSES = (
    "updated", "up-to-date", "degraded", "failed", "busy", "skipped", "unsupported",
)

MAX_TEXT = 65536
MAX_CHANGES = 2000
MAX_PACKAGES = 100000
SAFE_JOB = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,63}")
_CTRL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f-\x9f]")
# zero-width, bidi controls, line/paragraph separators, BOM
_INVISIBLE = re.compile("[\u200b-\u200f\u2028-\u202e\u2060-\u206f\ufeff]")
_ANSI = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")

# ------------------------------------------------------------------ masking

_PEM = re.compile(
    r"(?:-----)?BEGIN [A-Z ]*PRIVATE KEY(?:-----)?.*?"
    r"(?:(?:-----)?END [A-Z ]*PRIVATE KEY(?:-----)?|\Z)",
    re.DOTALL,
)
_URL_PASSWORD = re.compile(r"(?<![A-Za-z0-9+.-])([A-Za-z][A-Za-z0-9+.-]*://[^\s:/@]+:)\S+@")
# scheme://TOKEN@host (no colon): a plain lowercase login (git, root, jerome) is kept
_URL_USERINFO = re.compile(r"(?<![A-Za-z0-9+.-])([A-Za-z][A-Za-z0-9+.-]*://)([^\s:/@]+)@")
_PLAIN_LOGIN = re.compile(r"[a-z][a-z-]{0,15}")
# no left boundary: NTFY_tk_xxx and xtk_xxx are masked too
_NTFY_TOKEN = re.compile(r"tk_[A-Za-z0-9_-]{6,}")
_JWT = re.compile(r"eyJ[A-Za-z0-9_-]{6,}(?:\.[A-Za-z0-9_-]*)*")
_BEARER = re.compile(r"(?i)\b(bearer|basic)\s+[A-Za-z0-9._~+/=-]{8,}")
# The lookbehind anchors the key at a word start: each token is scanned once (linear time).
_KEYVAL = re.compile(
    r"(?i)(?<![A-Za-z0-9_.-])"
    r"([A-Za-z0-9_.-]*(?:password|passwd|passphrase|secret|token|api[_-]?key)[A-Za-z0-9_.-]*[\"']?)"
    r"(\s*[=:]\s*)(\"[^\"\n]*\"?|'[^'\n]*'?|\S+)"
)
MASK = "[MASKED]"


def _mask_keyval(match: "re.Match[str]") -> str:
    """Mask the whole value: a quoted string (even unterminated, to end of line) or a bare word.

    Choice: surrounding quotes are kept ("[MASKED]") so masked JSON-ish text stays parseable;
    only the content between them is replaced, so no secret character survives.
    """
    value = match.group(3)
    quote = value[0] if value[0] in "\"'" else ""
    closing = quote if quote and len(value) > 1 and value[-1] == quote else ""
    return match.group(1) + match.group(2) + quote + MASK + closing


def _mask_userinfo(match: "re.Match[str]") -> str:
    user = match.group(2)
    if _PLAIN_LOGIN.fullmatch(user):
        return match.group(0)
    return match.group(1) + MASK + "@"


def mask_secrets(text: str) -> str:
    """Hide private keys (even truncated), URL passwords, ntfy tokens, JWTs, key=value secrets."""
    out = _PEM.sub("[MASKED PRIVATE KEY]", text)
    out = _URL_PASSWORD.sub(lambda m: m.group(1) + MASK + "@", out)
    out = _URL_USERINFO.sub(_mask_userinfo, out)
    out = _JWT.sub(MASK, out)
    out = _NTFY_TOKEN.sub(MASK, out)
    out = _BEARER.sub(lambda m: m.group(1) + " " + MASK, out)
    out = _KEYVAL.sub(_mask_keyval, out)
    return out


def mask_data(value: Any) -> Any:
    """Copy of a JSON-like structure with every string masked (never regex serialized JSON)."""
    if isinstance(value, str):
        return mask_secrets(value)
    if isinstance(value, dict):
        return {(mask_secrets(k) if isinstance(k, str) else k): mask_data(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [mask_data(v) for v in value]
    return value


def clean_text(value: str, limit: int = 200, multiline: bool = False) -> str:
    """Printable, masked, bounded text (terminal-safe).

    Control, bidi and separator characters are removed BEFORE masking so they cannot
    be used to split a secret; lone surrogates are replaced so the text always encodes.
    """
    text = str(value).encode("utf-8", "replace").decode("utf-8", "replace")
    text = _ANSI.sub("", text).replace("\r", "")
    text = _INVISIBLE.sub("", text)
    if not multiline:
        text = text.replace("\n", " ").replace("\t", " ")
    text = _CTRL.sub("", text)
    if multiline:
        text = text.replace("\t", " ")
    return mask_secrets(text)[:limit]


# --------------------------------------------------------------- validation


class _Invalid(Exception):
    pass


def _opt_str(obj: Dict[str, Any], key: str, limit: int = 200) -> Optional[str]:
    val = obj.get(key)
    if val is None:
        return None
    if not isinstance(val, str):
        raise _Invalid("%s must be a string or null" % key)
    return clean_text(val, limit)


def _opt_bool(obj: Dict[str, Any], key: str) -> Optional[bool]:
    val = obj.get(key)
    if val is None:
        return None
    if not isinstance(val, bool):
        raise _Invalid("%s must be a boolean or null" % key)
    return val


def _str_list(val: Any, key: str, limit: int = 200) -> List[str]:
    if val is None:
        return []
    if not isinstance(val, list) or len(val) > MAX_CHANGES or not all(isinstance(v, str) for v in val):
        raise _Invalid("%s must be a list of strings" % key)
    return [clean_text(v, limit) for v in val]


def _health(val: Any, key: str) -> Optional[Dict[str, Any]]:
    if val is None:
        return None
    if not isinstance(val, dict):
        raise _Invalid("%s must be an object" % key)
    disk = val.get("disk_free_pct") or {}
    if not isinstance(disk, dict) or not all(
        type(v) is int and 0 <= v <= 100 for v in disk.values()
    ):
        raise _Invalid("%s.disk_free_pct invalid" % key)
    out = {
        "failed_units": _str_list(val.get("failed_units"), key + ".failed_units"),
        "unhealthy_containers": _str_list(val.get("unhealthy_containers"), key + ".unhealthy_containers"),
        "disk_free_pct": {clean_text(k, 80): v for k, v in disk.items()},
    }
    if "critical_services_down" in val:
        out["critical_services_down"] = _str_list(val["critical_services_down"], key + ".critical_services_down")
    return out


def _changes(val: Any) -> List[Dict[str, str]]:
    if val is None:
        return []
    if not isinstance(val, list) or len(val) > MAX_CHANGES:
        raise _Invalid("changes must be a list")
    out: List[Dict[str, str]] = []
    for item in val:
        if not isinstance(item, dict) or not isinstance(item.get("name"), str):
            raise _Invalid("changes item invalid")
        entry = {"name": clean_text(item["name"], 120)}
        for key in ("from", "to"):
            v = item.get(key)
            if v is not None and not isinstance(v, str):
                raise _Invalid("changes item invalid")
            entry[key] = clean_text(v, 80) if v is not None else ""
        out.append(entry)
    return out


def _build(obj: Dict[str, Any], alias: str, verb: str) -> Dict[str, Any]:
    version = obj.get("schema")
    if type(version) is not int or version != 1:
        raise _Invalid("unsupported schema")
    status = obj.get("status")
    if status not in AGENT_STATUSES:
        raise _Invalid("status %r not an agent status" % (status if isinstance(status, str) else "?"))
    said_verb = obj.get("verb", verb)
    if said_verb not in VERBS or said_verb != verb:
        raise _Invalid("verb does not match the request")
    packages = obj.get("packages")
    if packages is not None and (type(packages) is not int or not 0 <= packages <= MAX_PACKAGES):
        raise _Invalid("packages must be an integer between 0 and %d, or null" % MAX_PACKAGES)
    job = obj.get("job")
    if job not in (None, ""):
        if not isinstance(job, str) or not SAFE_JOB.fullmatch(job):
            raise _Invalid("job id invalid")
    else:
        job = None
    preflight = obj.get("preflight")
    pf = None
    if preflight is not None:
        if not isinstance(preflight, dict) or not isinstance(preflight.get("ok", True), bool):
            raise _Invalid("preflight invalid")
        blocked = preflight.get("blocked_by")
        if blocked is not None and not isinstance(blocked, str):
            raise _Invalid("preflight invalid")
        pf = {"ok": preflight.get("ok", True), "blocked_by": clean_text(blocked, 40) if blocked else None}
    tail = obj.get("log_tail")
    if tail is not None and not isinstance(tail, str):
        raise _Invalid("log_tail must be a string")
    tail_lines = clean_text(tail or "", 4000, multiline=True).splitlines()[-20:]
    return {
        "schema": 1,
        "host": alias,
        "verb": said_verb,
        "status": status,
        "reason": _opt_str(obj, "reason"),
        "packages": packages,
        "changes": _changes(obj.get("changes")),
        "health_before": _health(obj.get("health_before"), "health_before"),
        "health_after": _health(obj.get("health_after"), "health_after"),
        "preflight": pf,
        "config_conflicts": _str_list(obj.get("config_conflicts"), "config_conflicts"),
        "job": job,
        "reboot_required": _opt_bool(obj, "reboot_required"),
        "reboot_since": _opt_str(obj, "reboot_since", 40),
        "os": _opt_str(obj, "os", 80),
        "kernel": _opt_str(obj, "kernel", 80),
        "major_available": _opt_str(obj, "major_available", 80),
        "started": _opt_str(obj, "started", 40),
        "ended": _opt_str(obj, "ended", 40),
        "log_tail": "\n".join(tail_lines),
    }


def parse_agent_output(text: str, alias: str, verb: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """(clean entry, None) or (None, problem). ``alias`` replaces the agent's ``host``."""
    if len(text) > MAX_TEXT:
        return None, "agent output too large"
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if len(lines) != 1:
        return None, "agent output is not exactly one JSON line"
    if not lines[0].lstrip().startswith("{"):
        return None, "agent output is not a JSON object"
    try:
        obj = json.loads(lines[0])
    except (ValueError, RecursionError, MemoryError, TypeError):
        return None, "agent output is not JSON"
    if not isinstance(obj, dict):
        return None, "agent output is not a JSON object"
    try:
        return _build(obj, alias, verb), None
    except _Invalid as exc:
        return None, "invalid agent output: %s" % exc


def failed_entry(alias: str, verb: str, reason: str, now_iso: str) -> Dict[str, Any]:
    """A master-made ``failed`` entry (invalid agent output, refused call...)."""
    return {
        "schema": 1, "host": alias, "verb": verb, "status": "failed",
        "reason": clean_text(reason), "started": now_iso, "ended": now_iso,
    }


def master_entry(
    alias: str, verb: str, status: str, reason: str, last_seen: Optional[str],
    started: str, ended: str,
) -> Dict[str, Any]:
    """Entry for a status only the master can decide: offline unreachable timeout held."""
    if status not in MASTER_STATUSES:
        raise ValueError("not a master status: %s" % status)
    return {
        "schema": 1, "host": alias, "verb": verb, "status": status,
        "reason": clean_text(reason), "last_seen": last_seen,
        "started": started, "ended": ended,
    }
