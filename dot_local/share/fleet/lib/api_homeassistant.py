#!/usr/bin/env python3
"""Home Assistant updates through its API (kind ``homeassistant``).

Order: a FULL BACKUP first (any failure => ``skipped``, nothing is updated at all), then
add-ons, Core and finally the OS. Major versions ARE included. The OS update reboots the
device: the API must be back within 15 minutes, otherwise an ntfy priority-5 notification
is sent (notify.not_back_message) and the host is ``failed``.

Authentication: a long-lived token of a dedicated NON-owner user, read from 1Password at
run time, sent as ``Authorization: Bearer`` only (HTTP layer shared with api_opnsense:
no redirects, capped responses, timeouts, https or tailnet only, hostile JSON => failed).

The Supervisor endpoints (proxied under /api/hassio/) are NAMED CONSTANTS: they must be
verified on the installed Home Assistant version (live infrastructure, BLOCKED in sprint 3).

Stdlib only, Python 3.9 compatible.
"""

import os
import re
import sys
from typing import Any, Callable, Dict, List, Optional, Tuple

_LIB = os.path.dirname(os.path.abspath(__file__))
if _LIB not in sys.path:
    sys.path.insert(0, _LIB)

import api_opnsense as api  # noqa: E402  (shared HTTP / secret / entry plumbing)
import notify  # noqa: E402
import schema  # noqa: E402

# --- Supervisor endpoints through the Core proxy (to verify live: BLOCKED) ---
EP_CORE_INFO = "/api/hassio/core/info"
EP_OS_INFO = "/api/hassio/os/info"
EP_ADDONS = "/api/hassio/addons"
EP_BACKUP_FULL = "/api/hassio/backups/new/full"
EP_CORE_UPDATE = "/api/hassio/core/update"
EP_OS_UPDATE = "/api/hassio/os/update"
EP_ADDON_UPDATE = "/api/hassio/addons/%s/update"
EP_OWNER_ONLY_PROBE = "/api/hassio/auth/list"     # reserved to the owner/admin: must NOT be 200

SAFE_SLUG = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}")
BACKUP_TIMEOUT = 900.0
RETURN_WAIT_MIN = 15
RESTARTING_STATUSES = (502, 503, 504)
VERBS = ("check", "update")


class Pending(object):
    __slots__ = ("kind", "slug", "name", "old", "new")

    def __init__(self, kind: str, slug: str, name: str, old: str, new: str) -> None:
        self.kind, self.slug, self.name, self.old, self.new = kind, slug, name, old, new

    def change(self) -> Dict[str, str]:
        return {"name": self.name, "from": self.old, "to": self.new}


def _data(body: Any) -> Dict[str, Any]:
    """Supervisor wraps answers in {"result": "ok", "data": {...}}; tolerate a bare object."""
    if not isinstance(body, dict):
        raise api.ApiError("unexpected answer")
    inner = body.get("data")
    return inner if isinstance(inner, dict) else body


def _get(http: api.ApiHttp, path: str) -> Dict[str, Any]:
    status, body = http.request("GET", path)
    if status != 200:
        raise api.ApiError("%s refused (HTTP %d)" % (path, status), status)
    return _data(body)


def _pending(item: Dict[str, Any], kind: str, slug: str, name: str) -> Optional[Pending]:
    if item.get("update_available") is not True:
        return None
    return Pending(kind, slug, name, str(item.get("version") or ""), str(item.get("version_latest") or ""))


def collect(http: api.ApiHttp) -> Tuple[List[Pending], str]:
    """Pending updates, add-ons first, then Core, then OS (the order they are applied in)."""
    out: List[Pending] = []
    addons = _get(http, EP_ADDONS).get("addons")
    for addon in addons if isinstance(addons, list) else []:
        if not isinstance(addon, dict):
            continue
        slug = addon.get("slug")
        if not isinstance(slug, str) or not SAFE_SLUG.fullmatch(slug):
            continue
        found = _pending(addon, "addon", slug, str(addon.get("name") or slug))
        if found:
            out.append(found)
    core = _pending(_get(http, EP_CORE_INFO), "core", "core", "Home Assistant Core")
    if core:
        out.append(core)
    os_info = _get(http, EP_OS_INFO)
    os_found = _pending(os_info, "os", "os", "Home Assistant OS")
    if os_found:
        out.append(os_found)
    return out, str(os_info.get("version") or "")


def _check(alias: str, http: api.ApiHttp, ctx: api.ApiContext, started: str) -> Dict[str, Any]:
    pending, os_version = collect(http)
    status, reason = ("skipped", "updates_pending") if pending else ("up-to-date", None)
    return api.build_entry(alias, "check", ctx, status, reason, packages=len(pending),
                           changes=[p.change() for p in pending],
                           os_text=("Home Assistant OS " + os_version).strip(), started=started)


def make_backup(http: api.ApiHttp, ctx: api.ApiContext) -> bool:
    """A full backup that the Supervisor reports as ok. Anything else is a failure."""
    name = "fleet-" + ctx.now().strftime("%Y%m%d-%H%M")
    try:
        status, body = http.request("POST", EP_BACKUP_FULL, {"name": name}, timeout=BACKUP_TIMEOUT)
    except api.ApiError:
        return False
    return status == 200 and isinstance(body, dict) and body.get("result", "ok") == "ok"


def _version_is(http: api.ApiHttp, path: str, target: str) -> Callable[[], bool]:
    def ready() -> bool:
        info = _get(http, path)
        # up to date: the new version is running, or nothing is pending any more (flag false/absent)
        return str(info.get("version")) == target or info.get("update_available") is not True
    return ready


def _apply(alias: str, http: api.ApiHttp, ctx: api.ApiContext, item: Pending) -> Optional[str]:
    """None on success, otherwise a short reason. Core/OS restarts cut the connection: tolerated."""
    path = EP_ADDON_UPDATE % item.slug if item.kind == "addon" else (
        EP_CORE_UPDATE if item.kind == "core" else EP_OS_UPDATE)
    restarts = item.kind in ("core", "os")
    try:
        status, _ = http.request("POST", path, {} if item.kind == "addon" else None, timeout=600.0)
        # 502/503/504: Home Assistant is restarting under us; the version wait below decides
        if status != 200 and not (restarts and status in RESTARTING_STATUSES):
            return "%s update refused (HTTP %d)" % (item.name, status)
    except api.ApiError as exc:
        if not (restarts and exc.status is None):
            return "%s update failed: %s" % (item.name, exc)
    if not restarts:
        return None
    probe = EP_CORE_INFO if item.kind == "core" else EP_OS_INFO
    if api.wait_until(ctx, _version_is(http, probe, item.new), RETURN_WAIT_MIN):
        return None
    if item.kind == "os":
        ctx.notify(notify.not_back_message(ctx.master, alias))
    return "api_not_back: %s not answering with the new version after %d min" % (item.name, RETURN_WAIT_MIN)


def _update(alias: str, http: api.ApiHttp, ctx: api.ApiContext, started: str) -> Dict[str, Any]:
    pending, os_version = collect(http)
    if not pending:
        return api.build_entry(alias, "update", ctx, "up-to-date", packages=0,
                               os_text=("Home Assistant OS " + os_version).strip(), started=started)
    if not make_backup(http, ctx):      # no backup, no update: nothing is touched
        return api.build_entry(alias, "update", ctx, "skipped", "backup_failed: no update applied",
                               packages=len(pending), started=started)
    problems: List[str] = []
    core_failed = False
    for item in pending:                # add-ons, Core, then the OS (which reboots) last
        why = _apply(alias, http, ctx, item)
        if why:
            problems.append(why)
            if item.kind == "os" and why.startswith("api_not_back"):
                break
            if item.kind == "core":     # a broken Core must never be followed by the OS update (reboot)
                skipped = [p.name for p in pending if p.kind == "os"]
                if skipped:
                    problems.append("%s update skipped: Core update failed" % skipped[0])
                core_failed = True
                break
    changes = [p.change() for p in pending]
    if core_failed or any(p.startswith("api_not_back") for p in problems):
        reason = "; ".join(problems) if core_failed else problems[-1]
        return api.build_entry(alias, "update", ctx, "failed", schema.clean_text(reason, 160),
                               packages=len(pending), changes=changes, started=started)
    try:
        left, os_version = collect(http)
    except api.ApiError:
        left = []
        problems.append("final check failed")
    ok = not problems and not left
    return api.build_entry(
        alias, "update", ctx, "updated" if ok else "degraded",
        None if ok else "; ".join(problems) or "updates still pending", packages=len(pending),
        changes=changes, os_text=("Home Assistant OS " + os_version).strip(), started=started)


def _http(alias: str, data: Dict[str, Any], ctx: api.ApiContext) -> api.ApiHttp:
    params = api.api_params(data, alias, ("url", "token_ref"))
    return api.make_http(ctx, params, api.bearer_header(api.read_secret(ctx, params["token_ref"])))


def run(verb: str, alias: str, data: Dict[str, Any], ctx: api.ApiContext) -> Dict[str, Any]:
    """check | update for one Home Assistant host -> a schema v1 entry (never raises)."""
    started = ctx.iso()
    if verb not in VERBS:
        return api.build_entry(alias, verb, ctx, "unsupported", "no %s verb for an API host" % verb,
                               started=started)
    try:
        http = _http(alias, data, ctx)
        return (_check if verb == "check" else _update)(alias, http, ctx, started)
    except api.ApiError as exc:
        return api.failed(alias, verb, ctx, schema.clean_text(str(exc), 160), started)
    except Exception as exc:  # noqa: BLE001
        return api.failed(alias, verb, ctx, "internal error: %s" % exc.__class__.__name__, started)


def verify_privileges(alias: str, data: Dict[str, Any], ctx: api.ApiContext) -> Dict[str, Any]:
    """The dedicated user must work for updates but NOT for owner-only endpoints.

    Live verification: BLOCKED (sprint 3). EP_OWNER_ONLY_PROBE is to confirm on the installed version.
    """
    try:
        http = _http(alias, data, ctx)
        allowed = http.request("GET", EP_CORE_INFO)[0]
        probe = http.request("GET", EP_OWNER_ONLY_PROBE)[0]
    except api.ApiError as exc:
        return {"ok": False, "reason": schema.clean_text(str(exc), 160)}
    except Exception as exc:  # noqa: BLE001 (never echo str(exc): it could carry a secret)
        return {"ok": False, "reason": "internal error: %s" % exc.__class__.__name__}
    if allowed != 200:
        return {"ok": False, "reason": "update endpoints not reachable (HTTP %d)" % allowed}
    if probe == 200:
        return {"ok": False, "reason": "too privileged: owner-only endpoint answered HTTP 200"}
    return {"ok": True, "reason": "non-owner user"}
