#!/usr/bin/env python3
"""OPNsense firmware updates through its API (kind ``opnsense``), plus the HTTP/secret
plumbing shared with api_homeassistant.py.

Why an API and not the agent: OPNsense is a FreeBSD appliance with no sysup and no
SSH forced command. The ``fleet`` API user holds a single privilege, "System:
Firmware". This module produces the SAME schema v1 JSON as the Unix agent and rebuilds
it through schema.parse_agent_output, so statuses, masking and bounds are identical.

Policy (spec section 10, accepted risk of API tokens held by the masters):
  * credentials are read from 1Password at run time (``op read``, injectable runner,
    FLEET_OP), kept in memory, sent in a header only (never a URL, never argv, never
    disk, never in an error text);
  * major OPNsense releases are NEVER applied (``upgrade_major_version`` present =>
    ``major_available`` flag, no update call); no config.xml copy is made;
  * the HTTP client refuses redirects, caps the response size, has timeouts, accepts
    only tailnet API hosts (https to a ``*.ts.net`` name, or a literal 100.64.0.0/10
    address, in which case plain http is allowed: WireGuard already encrypts it) and
    survives hostile or invalid JSON (=> ``failed``).

The firmware endpoints below are NAMED CONSTANTS because they must be verified on the
installed OPNsense version (live infrastructure, BLOCKED in sprint 3).

Stdlib only, Python 3.9 compatible. Every outside effect (HTTP opener, ``op``, ping,
Tailscale, notifier, sleep, clock) is injectable through ApiContext.
"""

import base64
import http.client
import ipaddress
import json
import os
import re
import socket
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

_LIB = os.path.dirname(os.path.abspath(__file__))
if _LIB not in sys.path:
    sys.path.insert(0, _LIB)

import inventory as inv  # noqa: E402
import notify  # noqa: E402
import schema  # noqa: E402
import state as fstate  # noqa: E402

# --- OPNsense firmware endpoints (to verify on the installed version: BLOCKED, live) ---
EP_FIRMWARE_CHECK = "/api/core/firmware/check"              # POST: refresh the update info
EP_FIRMWARE_STATUS = "/api/core/firmware/status"            # GET: what is pending
EP_FIRMWARE_UPDATE = "/api/core/firmware/update"            # POST: minor updates only
EP_FIRMWARE_UPGRADESTATUS = "/api/core/firmware/upgradestatus"  # GET: progress of the running job
EP_FIRMWARE_UPGRADE = "/api/core/firmware/upgrade"          # major release: NEVER called
EP_FORBIDDEN_PROBE = "/api/core/system/status"              # outside "System: Firmware": must be 403

MAX_RESPONSE = 1024 * 1024
HTTP_TIMEOUT = 30.0
RETURN_WAIT_MIN = 15          # max wait for a rebooting appliance to come back
DOWN_GRACE_MIN = 3            # how long to wait to SEE it go down after a reboot order
VERBS = ("check", "update")


class ApiError(Exception):
    """An API call failed. The message never carries a secret, a URL or response text."""

    def __init__(self, message: str, status: Optional[int] = None) -> None:
        super().__init__(message)
        self.status = status


# ---------------------------------------------------------------- URL policy / HTTP


TS_NET_NAME = re.compile(r"(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+ts\.net")
CGNAT = ipaddress.ip_network("100.64.0.0/10")


def is_tailnet_name(host: str) -> bool:
    return bool(TS_NET_NAME.fullmatch(host.lower().rstrip(".")))


def is_tailnet_ip(host: str) -> bool:
    try:
        addr = ipaddress.ip_address(host)
    except ValueError:
        return False
    return addr.version == 4 and addr in CGNAT


def is_tailnet_host(host: str) -> bool:
    return is_tailnet_name(host) or is_tailnet_ip(host)


def check_api_url(url: str, allow_hosts: Sequence[str] = ()) -> str:
    """The normalized base URL, or ValueError. The API host must be on the tailnet:
    https to a ``*.ts.net`` name, or a literal 100.64.0.0/10 IP (http or https). Nothing else.

    ``allow_hosts`` is a TEST-ONLY injection (loopback test servers); the production
    callers never pass it, so the production policy is not loosened.
    """
    parts = urllib.parse.urlsplit(url or "")
    host = (parts.hostname or "").lower()
    if parts.scheme not in ("https", "http") or not host:
        raise ValueError("API url must be https://<name>.ts.net or http(s)://<100.64.0.0/10 address>")
    if parts.username or parts.password or parts.query or parts.fragment or parts.path not in ("", "/"):
        raise ValueError("API url must be a bare base URL without credentials or path")
    if host in allow_hosts or is_tailnet_ip(host) or (parts.scheme == "https" and is_tailnet_name(host)):
        return url.rstrip("/")
    raise ValueError("API host must be on the tailnet (https *.ts.net, or a 100.64.0.0/10 address)")


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Never follow a redirect: the Authorization header must not leave the configured URL."""

    def redirect_request(self, *args: Any, **kwargs: Any) -> None:
        return None


def build_opener(cafile: Optional[str] = None) -> "urllib.request.OpenerDirector":
    context = ssl.create_default_context(cafile=cafile) if cafile else ssl.create_default_context()
    return urllib.request.build_opener(_NoRedirect, urllib.request.HTTPSHandler(context=context))


class ApiHttp:
    """Tiny JSON-over-HTTP client. Credentials live only in ``headers`` (memory)."""

    def __init__(
        self, base_url: str, headers: Dict[str, str], allow_hosts: Sequence[str] = (),
        opener: Optional[Any] = None, timeout: float = HTTP_TIMEOUT, cafile: Optional[str] = None,
    ) -> None:
        self.base = check_api_url(base_url, allow_hosts)
        self._headers = dict(headers)
        self.opener = opener or build_opener(cafile)
        self.timeout = timeout

    def request(
        self, method: str, path: str, body: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
    ) -> Tuple[int, Any]:
        """(HTTP status, parsed JSON or None). ApiError on network trouble, redirect or bad JSON."""
        if not path.startswith("/") or "://" in path or "@" in path:
            raise ApiError("invalid API path")
        data = json.dumps(body).encode("utf-8") if body is not None else None
        headers = dict(self._headers)
        headers["Accept"] = "application/json"
        if data is not None:
            headers["Content-Type"] = "application/json"
        elif method == "POST":
            data = b""
        req = urllib.request.Request(self.base + path, data=data, headers=headers, method=method)
        try:
            with self.opener.open(req, timeout=timeout or self.timeout) as resp:  # noqa: S310
                status, raw = resp.status, resp.read(MAX_RESPONSE + 1)
        except urllib.error.HTTPError as exc:
            status = exc.code
            try:
                raw = exc.read(MAX_RESPONSE + 1)
            except (OSError, http.client.HTTPException):
                raw = b""
            if 300 <= status < 400:
                raise ApiError("redirect refused", status)
        except (urllib.error.URLError, OSError, http.client.HTTPException, socket.timeout, ValueError) as exc:
            raise ApiError("network error: %s" % exc.__class__.__name__)
        if len(raw) > MAX_RESPONSE:
            raise ApiError("response too large", status)
        if not raw.strip():
            return status, None
        try:
            return status, json.loads(raw.decode("utf-8", "replace"))
        except (ValueError, RecursionError, MemoryError):
            if status >= 400:
                return status, None       # an error page is not JSON: the status is what matters
            raise ApiError("invalid JSON response", status)


def basic_header(key: str, secret: str) -> Dict[str, str]:
    token = base64.b64encode(("%s:%s" % (key, secret)).encode("utf-8")).decode("ascii")
    return {"Authorization": "Basic " + token}


def bearer_header(token: str) -> Dict[str, str]:
    return {"Authorization": "Bearer " + token}


# ---------------------------------------------------------------- context / secrets


def default_ping(host: str) -> bool:
    try:
        proc = subprocess.run(["ping", "-c", "1", host], stdin=subprocess.DEVNULL,
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=8)
    except (OSError, subprocess.SubprocessError):
        return False
    return proc.returncode == 0


def default_node_online(tailnet_name: str) -> bool:
    peers = inv.read_tailscale()
    return inv.peer_state(tailnet_name, peers)[0] == "online"


class ApiContext:
    """Everything an API run needs from the outside world, all injectable."""

    def __init__(
        self, master: str = "", env: Optional[Dict[str, str]] = None,
        op: Optional[Callable[[List[str]], str]] = None, allow_hosts: Sequence[str] = (),
        opener: Optional[Any] = None, sleep: Callable[[float], None] = time.sleep,
        now: Callable[[], datetime] = fstate.utcnow, ping: Optional[Callable[[str], bool]] = None,
        node_online: Optional[Callable[[str], bool]] = None,
        notifier: Optional[Callable[[Dict[str, Any]], None]] = None,
        tailnet_name: str = "", deadline_min: int = 30, poll_interval: float = 15.0,
    ) -> None:
        self.master, self.env = master, dict(os.environ) if env is None else env
        self.op = op or (lambda args: notify.default_op_runner(args, self.env))
        self.allow_hosts, self.opener = tuple(allow_hosts), opener
        self.sleep, self.now = sleep, now
        self.ping = ping or default_ping
        self.node_online = node_online or default_node_online
        self.notifier = notifier
        self.tailnet_name, self.deadline_min, self.poll_interval = tailnet_name, deadline_min, poll_interval

    def iso(self) -> str:
        return fstate.iso(self.now())

    def notify(self, msg: Dict[str, Any]) -> None:
        if self.notifier is not None:
            try:
                self.notifier(msg)
            except Exception:  # noqa: BLE001 (a notification problem never aborts the run)
                pass


def read_secret(ctx: ApiContext, ref: Any) -> str:
    """The secret behind an ``op://`` reference. The value is never logged or put in a message."""
    if not isinstance(ref, str) or not ref.startswith("op://"):
        raise ApiError("credential reference must be an op:// reference")
    try:
        value = ctx.op(["op", "read", ref]).strip()
    except (OSError, subprocess.SubprocessError):
        raise ApiError("cannot read the API credential from 1Password")
    if not value:
        raise ApiError("the API credential in 1Password is empty")
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in value):
        raise ApiError("the API credential in 1Password contains control characters")
    return value


def api_params(data: Dict[str, Any], alias: str, required: Sequence[str]) -> Dict[str, Any]:
    """fleet.yml ``api.<alias>`` mapping: url + op:// references. ApiError when unusable."""
    params = (data.get("api") or {}).get(alias)
    if not isinstance(params, dict):
        raise ApiError("no api parameters for this host in fleet.yml")
    for field in required:
        if not isinstance(params.get(field), str) or not params[field]:
            raise ApiError("api.%s: missing %s" % (alias, field))
    for field in required:
        if field.endswith("_ref") and not params[field].startswith("op://"):
            raise ApiError("api.%s.%s must be an op:// reference" % (alias, field))
    return params


def make_http(ctx: ApiContext, params: Dict[str, Any], headers: Dict[str, str]) -> ApiHttp:
    try:
        return ApiHttp(params["url"], headers, ctx.allow_hosts, ctx.opener, cafile=params.get("ca_file"))
    except ValueError as exc:
        raise ApiError(str(exc))


# ---------------------------------------------------------------- entries (schema v1)


def build_entry(
    alias: str, verb: str, ctx: ApiContext, status: str, reason: Optional[str] = None,
    packages: Optional[int] = None, changes: Optional[List[Dict[str, str]]] = None,
    major_available: Optional[str] = None, os_text: Optional[str] = None,
    reboot_required: Optional[bool] = None, started: Optional[str] = None,
    log_tail: str = "",
) -> Dict[str, Any]:
    """Same JSON as the agent, masked on the structure then rebuilt by schema (never trusted)."""
    now = ctx.iso()
    obj = {
        "schema": 1, "host": alias, "verb": verb, "status": status, "reason": reason,
        "packages": packages, "changes": changes or [], "reboot_required": reboot_required,
        "os": os_text, "major_available": major_available,
        "started": started or now, "ended": now, "log_tail": log_tail,
    }
    text = json.dumps(schema.mask_data(obj))
    entry, why = schema.parse_agent_output(text, alias, verb)
    return entry if entry is not None else schema.failed_entry(alias, verb, why or "invalid API result", now)


def failed(alias: str, verb: str, ctx: ApiContext, reason: str, started: Optional[str] = None) -> Dict[str, Any]:
    return build_entry(alias, verb, ctx, "failed", reason, started=started)


def wait_until(ctx: ApiContext, ready: Callable[[], bool], limit_min: float) -> bool:
    """Poll ``ready`` (exceptions = not ready) until true or ``limit_min`` minutes passed."""
    end = ctx.now().timestamp() + limit_min * 60
    # iteration guard besides the clock deadline: a stuck clock can never loop forever
    remaining = int(limit_min * 60 / max(ctx.poll_interval, 0.01)) + 2
    while remaining > 0:
        remaining -= 1
        try:
            if ready():
                return True
        except (ApiError, OSError):
            pass
        if ctx.now().timestamp() >= end:
            return False
        ctx.sleep(ctx.poll_interval)
    return False


# ---------------------------------------------------------------- OPNsense


def _as_int(value: Any) -> int:
    try:
        return max(0, int(str(value).strip()))
    except (TypeError, ValueError):
        return 0


def _pkg_changes(body: Dict[str, Any]) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    for key in ("upgrade_packages", "new_packages", "reinstall_packages"):
        items = body.get(key)
        if not isinstance(items, list):
            continue
        for item in items[:500]:
            if isinstance(item, dict) and isinstance(item.get("name"), str):
                out.append({"name": item["name"],
                            "from": str(item.get("old_version") or item.get("current_version") or ""),
                            "to": str(item.get("new_version") or "")})
    return out


def summarize_status(body: Any) -> Dict[str, Any]:
    """Pending minor updates / major release / reboot flag from a firmware status answer."""
    if not isinstance(body, dict):
        raise ApiError("unexpected firmware status answer")
    state = body.get("status")
    changes = _pkg_changes(body)
    updates = _as_int(body.get("updates")) or len(changes)
    major = body.get("upgrade_major_version")
    major = str(major).strip() if major not in (None, "", False, 0, "0") else None
    return {
        "state": state if isinstance(state, str) else "",
        "message": body.get("status_msg") if isinstance(body.get("status_msg"), str) else "",
        "minor": updates > 0,               # never report up-to-date while updates are pending
        "updates": updates, "changes": changes, "major": major,
        "reboot": str(body.get("needs_reboot", "0")).lower() in ("1", "true"),
        "version": str(body.get("product_version") or ""),
    }


def _firmware_status(http: ApiHttp, refresh: bool) -> Dict[str, Any]:
    if refresh:
        status, body = http.request("POST", EP_FIRMWARE_CHECK)
        if status != 200:
            raise ApiError("firmware check refused (HTTP %d)" % status, status)
    status, body = http.request("GET", EP_FIRMWARE_STATUS)
    if status != 200:
        raise ApiError("firmware status refused (HTTP %d)" % status, status)
    summary = summarize_status(body)
    if summary["state"] == "error":
        raise ApiError("firmware status error: %s" % schema.clean_text(summary["message"], 80))
    return summary


def _opnsense_http(alias: str, params: Dict[str, Any], ctx: ApiContext) -> ApiHttp:
    key = read_secret(ctx, params["key_ref"])
    secret = read_secret(ctx, params["secret_ref"])
    return make_http(ctx, params, basic_header(key, secret))


TERMINAL_JOB_STATES = ("done", "error", "reboot")


def _job_snapshot(http: ApiHttp) -> Optional[str]:
    """The log text of the job status BEFORE the update POST (a previous job's terminal answer)."""
    try:
        status, body = http.request("GET", EP_FIRMWARE_UPGRADESTATUS)
    except ApiError:
        return None
    if status != 200 or not isinstance(body, dict):
        return None
    return str(body.get("log"))


def _follow_upgrade(http: ApiHttp, ctx: ApiContext, limit_min: float,
                    baseline: Optional[str] = None) -> Tuple[str, bool]:
    """(final job state, saw_reboot). Network blips while services restart are tolerated.

    A terminal state is only believed once THIS job was seen running, or its log differs from
    the pre-POST snapshot: right after the POST the box may still answer with the terminal
    state of the previous job."""
    seen = {"state": "running", "reboot": False, "armed": False}

    def done() -> bool:
        status, body = http.request("GET", EP_FIRMWARE_UPGRADESTATUS)
        if status != 200 or not isinstance(body, dict):
            return False
        state = body.get("status")
        state = state if isinstance(state, str) else "running"
        if state not in TERMINAL_JOB_STATES:
            seen["armed"] = True
            seen["state"] = state
            return False
        if baseline is not None and str(body.get("log")) != baseline:
            seen["armed"] = True
        if not seen["armed"]:
            return False
        seen["state"] = state
        if state == "reboot":
            seen["reboot"] = True
        return True

    if not wait_until(ctx, done, limit_min):
        return "timeout", False
    return seen["state"], seen["reboot"]


def _wait_return(http: ApiHttp, ctx: ApiContext, limit_min: float) -> bool:
    """After a reboot order: see it go down (grace), then wait for ping + tailnet node + API."""
    def down() -> bool:
        if not ctx.ping(ctx.tailnet_name):
            return True
        try:
            return http.request("GET", EP_FIRMWARE_STATUS)[0] != 200
        except ApiError:
            return True

    wait_until(ctx, down, min(DOWN_GRACE_MIN, limit_min))      # never seen down: nothing to wait for

    def back() -> bool:
        return bool(ctx.ping(ctx.tailnet_name) and ctx.node_online(ctx.tailnet_name)
                    and http.request("GET", EP_FIRMWARE_STATUS)[0] == 200)

    return wait_until(ctx, back, limit_min)


def _check_entry(alias: str, summary: Dict[str, Any], ctx: ApiContext, started: str) -> Dict[str, Any]:
    if summary["minor"]:
        status, reason = "skipped", "updates_pending"
    else:
        status, reason = "up-to-date", ("major_available: not applied" if summary["major"] else None)
    return build_entry(alias, "check", ctx, status, reason, packages=summary["updates"],
                       major_available=summary["major"], os_text=("OPNsense " + summary["version"]).strip(),
                       reboot_required=summary["reboot"], started=started)


def _final_status(http: ApiHttp, ctx: ApiContext, end_ts: float) -> Optional[Dict[str, Any]]:
    """The firmware status after the update; the box may be half-up, so retry until ``end_ts``."""
    got: Dict[str, Any] = {}

    def fetch() -> bool:
        got["status"] = _firmware_status(http, refresh=True)
        return True

    remaining_min = max(0.0, (end_ts - ctx.now().timestamp()) / 60.0)
    return got.get("status") if wait_until(ctx, fetch, remaining_min) else None


def _update(alias: str, http: ApiHttp, ctx: ApiContext, started: str) -> Dict[str, Any]:
    end_ts = ctx.now().timestamp() + ctx.deadline_min * 60
    before = _firmware_status(http, refresh=True)
    if not before["minor"]:         # nothing minor: a major release is only reported, never applied
        return build_entry(
            alias, "update", ctx, "up-to-date", "major_available: not applied" if before["major"] else None,
            packages=0, major_available=before["major"], os_text=("OPNsense " + before["version"]).strip(),
            started=started)
    baseline = _job_snapshot(http)
    # minor updates only: EP_FIRMWARE_UPGRADE (major release) is never called
    status, body = http.request("POST", EP_FIRMWARE_UPDATE)
    if status != 200 or not isinstance(body, dict) or body.get("status") not in ("ok", None):
        return failed(alias, "update", ctx, "update refused (HTTP %d)" % status, started)
    state, rebooting = _follow_upgrade(http, ctx, min(ctx.deadline_min, 30), baseline)
    if state in ("error", "timeout"):
        return failed(alias, "update", ctx, "firmware job %s" % state, started)
    if rebooting and not _wait_return(http, ctx, RETURN_WAIT_MIN):
        ctx.notify(notify.not_back_message(ctx.master, alias))
        return failed(alias, "update", ctx, "did not come back within %d min" % RETURN_WAIT_MIN, started)
    after = _final_status(http, ctx, end_ts)
    packages = len(before["changes"]) or before["updates"]
    if after is None:
        ctx.notify(notify.not_back_message(ctx.master, alias))
        return build_entry(alias, "update", ctx, "degraded", "firmware status unavailable after the update",
                           packages=packages, changes=before["changes"], major_available=before["major"],
                           started=started)
    ok = not after["minor"]
    return build_entry(
        alias, "update", ctx, "updated" if ok else "degraded",
        None if ok else "updates still pending after the update", packages=packages,
        changes=before["changes"], major_available=after["major"] or before["major"],
        os_text=("OPNsense " + after["version"]).strip(), reboot_required=after["reboot"], started=started)


def run(verb: str, alias: str, data: Dict[str, Any], ctx: ApiContext) -> Dict[str, Any]:
    """check | update for one OPNsense host -> a schema v1 entry (never raises)."""
    started = ctx.iso()
    if verb not in VERBS:
        return build_entry(alias, verb, ctx, "unsupported", "no %s verb for an API host" % verb, started=started)
    try:
        params = api_params(data, alias, ("url", "key_ref", "secret_ref"))
        http = _opnsense_http(alias, params, ctx)
        if verb == "check":
            return _check_entry(alias, _firmware_status(http, refresh=True), ctx, started)
        return _update(alias, http, ctx, started)
    except ApiError as exc:
        return failed(alias, verb, ctx, str(exc), started)
    except Exception as exc:  # noqa: BLE001 (an API host must never abort the run)
        return failed(alias, verb, ctx, "internal error: %s" % exc.__class__.__name__, started)


def verify_privileges(alias: str, data: Dict[str, Any], ctx: ApiContext) -> Dict[str, Any]:
    """The ``fleet`` user must reach System: Firmware and NOTHING else.

    Expects 200 on the firmware status and 403 outside that privilege (EP_FORBIDDEN_PROBE);
    a 200 there means the user is too privileged. Live verification: BLOCKED (sprint 3).
    """
    try:
        params = api_params(data, alias, ("url", "key_ref", "secret_ref"))
        http = _opnsense_http(alias, params, ctx)
        allowed = http.request("GET", EP_FIRMWARE_STATUS)[0]
        probe = http.request("GET", EP_FORBIDDEN_PROBE)[0]
    except ApiError as exc:
        return {"ok": False, "reason": schema.clean_text(str(exc), 160)}
    except Exception as exc:  # noqa: BLE001 (never echo str(exc): it could carry a secret)
        return {"ok": False, "reason": "internal error: %s" % exc.__class__.__name__}
    if allowed != 200:
        return {"ok": False, "reason": "firmware status not reachable (HTTP %d)" % allowed}
    if probe != 403:
        return {"ok": False, "reason": "too privileged: %s answered HTTP %d, expected 403"
                % (EP_FORBIDDEN_PROBE, probe)}
    return {"ok": True, "reason": "limited to System: Firmware"}
