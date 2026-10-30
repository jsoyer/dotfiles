#!/usr/bin/env python3
"""ntfy notifications with a durable queue.

Six event types (spec section 12): run summary (prio 2, or 4 when something
failed), stale host > 30 d (4), reboot not back (5), command refused by an agent
(5), pull-mode autonomous update (2), 14-day reminder (3).

The ntfy token is resolved at run time (env FLEET_NTFY_TOKEN, else 1Password
``op read <ref>``); it is only ever put in the Authorization header, never in the
queue, a report or a log. Messages are masked, bodies are at most 20 lines and
never carry a raw log_tail. A message that cannot be delivered is queued under
``ntfy-queue/`` (0600) and resent, in order, on the next successful contact.

Stdlib only, Python 3.9 compatible. The HTTP sender is injectable (tests never
touch a network).
"""

import base64
import json
import os
import subprocess
import threading
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

import report
import schema
import state as fstate

MAX_BODY_LINES = 20
REMINDER_DAYS = 14
BAD = ("failed", "unreachable", "timeout")


def message(title: str, priority: int, tags: List[str], body: str) -> Dict[str, Any]:
    lines = schema.mask_secrets(body).splitlines()[:MAX_BODY_LINES]
    return {
        "title": schema.clean_text(title, 200), "priority": int(priority),
        "tags": list(tags), "body": "\n".join(lines),
    }


def _line(e: Dict[str, Any]) -> str:
    reason = schema.clean_text(e.get("reason") or "", 80)
    return "%s: %s%s" % (e["host"], e["status"], (" (%s)" % reason) if reason else "")


def _capped(lines: List[str]) -> str:
    if len(lines) > MAX_BODY_LINES:
        extra = len(lines) - (MAX_BODY_LINES - 1)
        lines = lines[: MAX_BODY_LINES - 1] + ["... +%d more" % extra]
    return "\n".join(lines)


def summary_message(master: str, entries: List[Dict[str, Any]]) -> Dict[str, Any]:
    statuses = [e["status"] for e in entries]
    failed = any(s in BAD for s in statuses)
    degraded = "degraded" in statuses
    tags: List[str] = []
    if failed:
        tags.append("failed")
    if degraded:
        tags.append("degraded")
    if not tags:
        tags = ["ok"]
    prio = 4 if (failed or degraded) else 2
    interesting = [e for e in entries if e["status"] not in report.OK_STATUSES]
    ordered = interesting + [e for e in entries if e["status"] in report.OK_STATUSES]
    return message("fleet %s : %s" % (master, report.summary_line(entries)), prio, tags,
                   _capped([_line(e) for e in ordered]))


def stale_message(master: str, stale: Sequence[Tuple[str, str, int]]) -> Dict[str, Any]:
    lines = ["%s: no update for %d days (last %s)" % (h, age, when) for h, when, age in stale]
    return message("fleet %s : %d host(s) > 30 days without update" % (master, len(stale)),
                   4, ["degraded"], _capped(lines))


def not_back_message(master: str, host: str) -> Dict[str, Any]:
    return message("fleet %s : %s did not come back after reboot" % (master, host), 5,
                   ["reboot"], "%s: rebooted but not answering" % host)


def refused_message(master: str, host: str) -> Dict[str, Any]:
    return message("fleet %s : command refused by %s" % (master, host), 5, ["refused"],
                   "%s: the agent refused the call" % host)


def pull_message(master: str, host: str, detail: str) -> Dict[str, Any]:
    return message("fleet %s : autonomous update on %s" % (master, host), 2, ["pull"],
                   "%s: %s" % (host, schema.clean_text(detail, 160)))


def reminder_message(master: str, days: int) -> Dict[str, Any]:
    return message("fleet %s : no fleet up for %d days" % (master, days), 3, ["reminder"],
                   "Run `fleet up` (last run %d days ago or never)." % days)


# ------------------------------------------------------------------ transport


def encode_header(value: str) -> str:
    """HTTP headers are latin-1; anything else goes RFC 2047 (ntfy decodes it)."""
    try:
        value.encode("latin-1")
        return value
    except UnicodeEncodeError:
        return "=?UTF-8?B?%s?=" % base64.b64encode(value.encode("utf-8")).decode("ascii")


def http_sender(url: str, topic: str, headers: Dict[str, str], body: str) -> None:
    req = urllib.request.Request(
        url.rstrip("/") + "/" + topic, data=body.encode("utf-8"),
        headers={k: encode_header(v) for k, v in headers.items()}, method="POST")
    with urllib.request.urlopen(req, timeout=10) as resp:  # noqa: S310 (https URL from fleet.yml)
        resp.read(1024)


def default_op_runner(args: List[str]) -> str:
    cmd = [os.environ.get("FLEET_OP", "op")] + args[1:]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=20, stdin=subprocess.DEVNULL)
    if proc.returncode != 0:
        raise OSError("op read failed")
    return proc.stdout


def resolve_token(
    token_ref: Optional[str], env: Dict[str, str],
    runner: Optional[Callable[[List[str]], str]],
) -> Optional[str]:
    if env.get("FLEET_NTFY_TOKEN"):
        return env["FLEET_NTFY_TOKEN"]
    if not token_ref or runner is None:
        return None
    try:
        value = runner(["op", "read", token_ref]).strip()
    except (OSError, subprocess.SubprocessError):
        return None
    return value or None


class Notifier:
    def __init__(
        self, url: str, topic: str, token: Optional[str], queue_dir: Path,
        sender: Optional[Callable[[str, str, Dict[str, str], str], None]] = None,
        clock: Callable[[], datetime] = fstate.utcnow,
    ) -> None:
        self.url, self.topic, self.token = url, topic, token
        self.queue_dir = Path(queue_dir)
        self.sender = sender or http_sender
        self.clock = clock
        self._lock = threading.Lock()
        self._counter = 0

    def pending(self) -> List[Path]:
        if not self.queue_dir.is_dir():
            return []
        return sorted(p for p in self.queue_dir.iterdir() if p.suffix == ".json")

    def _headers(self, msg: Dict[str, Any]) -> Dict[str, str]:
        headers = {
            "Title": str(msg["title"]), "Priority": str(msg["priority"]),
            "Tags": ",".join(msg.get("tags") or []),
        }
        if self.token:
            headers["Authorization"] = "Bearer " + self.token
        return headers

    def _deliver(self, msg: Dict[str, Any]) -> bool:
        try:
            self.sender(self.url, self.topic, self._headers(msg), msg["body"])
        except (OSError, ValueError):
            return False
        return True

    def _enqueue(self, msg: Dict[str, Any]) -> None:
        self._counter += 1
        stamp = self.clock().strftime("%Y%m%dT%H%M%S%f")
        record = dict(msg)
        record["created"] = fstate.iso(self.clock())
        for key in ("title", "body"):
            record[key] = schema.mask_secrets(str(record[key]))
        fstate.make_private_dir(self.queue_dir)
        fstate.write_private(self.queue_dir / ("%s-%06d.json" % (stamp, self._counter)),
                             json.dumps(record, sort_keys=True) + "\n")

    def flush(self) -> int:
        """Resend queued messages in order; stop at the first failure. Returns sent count."""
        sent = 0
        with self._lock:
            return self._flush_locked(sent)

    def _flush_locked(self, sent: int) -> int:
        for path in self.pending():
            try:
                msg = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if not self._deliver(msg):
                break
            path.unlink()
            sent += 1
        return sent

    def send(self, msg: Dict[str, Any]) -> bool:
        """Deliver now (after the backlog) or queue. True if delivered immediately."""
        with self._lock:
            self._flush_locked(0)
            if self.pending():
                self._enqueue(msg)
                return False
            if self._deliver(msg):
                return True
            self._enqueue(msg)
            return False


def reminder_check(
    st: "fstate.State", notifier: Notifier, now: Optional[datetime] = None, days: int = REMINDER_DAYS,
) -> bool:
    """Reads merged history only; opens no connection to any fleet host."""
    moment = now or datetime.now(timezone.utc)
    last = st.last_run_started()
    age = (moment - last).days if last else None
    if age is not None and age < days:
        return False
    notifier.send(reminder_message(st.master, age if age is not None else days))
    return True
