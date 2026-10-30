#!/usr/bin/env python3
"""Master-side state under ~/.local/state/fleet (override: FLEET_STATE_DIR).

Layout (spec section 11):
  runs/<run_id>/            report.json report.md run.log raw/<host>.json|log
  history-<master>.jsonl    one line per (run, host), append-only, purged at 31 d
  last-success-<master>.json  {"host": ISO}, NEVER purged (feeds the > 30 d alert)
  holds-<master>.json       [{"host","reason","until","set_at","lifted_at"}]

Each master writes only its own ``*-<master>`` files and ``runs/*-<master>/``;
the other master's copies arrive by rsync and are merged at read time.
Everything is 0600 (directories 0700). Stdlib only, Python 3.9 compatible.
"""

import json
import os
import re
import shutil
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

RETENTION_DAYS = 31
SAFE_MASTER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
RUN_ID = re.compile(r"^\d{8}T\d{4}Z-[A-Za-z0-9][A-Za-z0-9_.-]*$")
HISTORY_FIELDS = (
    "run_id", "master", "host", "status", "reason", "packages", "reboot_required",
    "last_seen", "started", "ended",
)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def iso(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_iso(text: Optional[str]) -> Optional[datetime]:
    """ISO8601 ('Z' or offset) or a bare date (end of that day, UTC); None if unreadable."""
    if not isinstance(text, str) or not text:
        return None
    value = text.strip()
    try:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            return datetime.strptime(value, "%Y-%m-%d").replace(
                hour=23, minute=59, second=59, tzinfo=timezone.utc)
        value = re.sub(r"\.\d+", "", value)
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def run_id_time(run_id: str) -> Optional[datetime]:
    match = re.match(r"^(\d{8}T\d{4})Z-", run_id)
    if not match:
        return None
    return datetime.strptime(match.group(1), "%Y%m%dT%H%M").replace(tzinfo=timezone.utc)


def default_root(env: Optional[Dict[str, str]] = None) -> Path:
    env = os.environ if env is None else env
    if env.get("FLEET_STATE_DIR"):
        return Path(env["FLEET_STATE_DIR"])
    base = env.get("XDG_STATE_HOME") or os.path.join(os.path.expanduser("~"), ".local", "state")
    return Path(base) / "fleet"


def write_private(path: Path, text: str) -> None:
    """Atomic write, mode 0600, parent 0700 (temp file is created 0600 by mkstemp)."""
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, tmp = tempfile.mkstemp(prefix=".tmp-", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
        os.chmod(tmp, 0o600)
        os.replace(tmp, str(path))
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def make_private_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(str(path), 0o700)


def _read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


class State:
    def __init__(self, root: Path, master: str, now: Callable[[], datetime] = utcnow) -> None:
        if not SAFE_MASTER.match(master):
            raise ValueError("invalid master name")
        self.root = Path(root)
        self.master = master
        self.now = now
        make_private_dir(self.root)

    # ---------------------------------------------------------- paths
    def run_dir(self, run_id: str) -> Path:
        if not RUN_ID.match(run_id):
            raise ValueError("invalid run id")
        return self.root / "runs" / run_id

    def _own(self, prefix: str, suffix: str) -> Path:
        return self.root / ("%s-%s.%s" % (prefix, self.master, suffix))

    # ---------------------------------------------------------- history
    def append_history(self, run_id: str, entry: Dict[str, Any]) -> None:
        record = {"run_id": run_id, "master": self.master}
        for key in HISTORY_FIELDS[2:]:
            record[key] = entry.get(key)
        path = self._own("history", "jsonl")
        existing = path.read_text(encoding="utf-8") if path.exists() else ""
        write_private(path, existing + json.dumps(record, sort_keys=True) + "\n")

    def history(self) -> List[Dict[str, Any]]:
        seen = set()
        out: List[Dict[str, Any]] = []
        for path in sorted(self.root.glob("history-*.jsonl")):
            try:
                lines = path.read_text(encoding="utf-8").splitlines()
            except OSError:
                continue
            for text in lines:
                try:
                    rec = json.loads(text)
                except ValueError:
                    continue
                if not isinstance(rec, dict):
                    continue
                key = (rec.get("run_id"), rec.get("host"))
                if key in seen:
                    continue
                seen.add(key)
                out.append(rec)
        return out

    def last_run_started(self) -> Optional[datetime]:
        best = None
        for rec in self.history():
            moment = run_id_time(str(rec.get("run_id", ""))) or parse_iso(rec.get("started"))
            if moment and (best is None or moment > best):
                best = moment
        return best

    # ---------------------------------------------------------- last success
    def set_last_success(self, host: str, when_iso: str) -> None:
        path = self._own("last-success", "json")
        data = _read_json(path, {})
        if not isinstance(data, dict):
            data = {}
        data[host] = when_iso
        write_private(path, json.dumps(data, sort_keys=True, indent=1) + "\n")

    def last_success(self) -> Dict[str, str]:
        merged: Dict[str, str] = {}
        for path in sorted(self.root.glob("last-success-*.json")):
            data = _read_json(path, {})
            if not isinstance(data, dict):
                continue
            for host, when in data.items():
                new, old = parse_iso(when), parse_iso(merged.get(host))
                if new and (old is None or new > old):
                    merged[host] = when
        return merged

    # ---------------------------------------------------------- holds
    def _own_holds(self) -> List[Dict[str, Any]]:
        data = _read_json(self._own("holds", "json"), [])
        return data if isinstance(data, list) else []

    def _write_holds(self, holds: List[Dict[str, Any]]) -> None:
        write_private(self._own("holds", "json"), json.dumps(holds, indent=1) + "\n")

    def add_hold(self, host: str, reason: str, until: str) -> None:
        if parse_iso(until) is None:
            raise ValueError("unreadable --until date: %r" % until)
        holds = self._own_holds()
        holds.append({"host": host, "reason": reason, "until": until,
                      "set_at": iso(self.now()), "lifted_at": None})
        self._write_holds(holds)

    def lift_hold(self, host: str) -> None:
        """Dated lift record: it beats any earlier hold, on either master."""
        stamp = iso(self.now())
        holds = self._own_holds()
        holds.append({"host": host, "reason": "unhold", "until": None,
                      "set_at": stamp, "lifted_at": stamp})
        self._write_holds(holds)

    def all_holds(self) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for path in sorted(self.root.glob("holds-*.json")):
            data = _read_json(path, [])
            if isinstance(data, list):
                out.extend(h for h in data if isinstance(h, dict) and h.get("host"))
        return out

    def active_holds(self, now: Optional[datetime] = None) -> Dict[str, Dict[str, Any]]:
        """host -> hold, after union, lifts and automatic expiry."""
        moment = now or self.now()
        records = self.all_holds()
        lifts: Dict[str, datetime] = {}
        for rec in records:
            lifted = parse_iso(rec.get("lifted_at"))
            if lifted and (rec["host"] not in lifts or lifted > lifts[rec["host"]]):
                lifts[rec["host"]] = lifted
        active: Dict[str, Dict[str, Any]] = {}
        for rec in records:
            if rec.get("lifted_at"):
                continue
            until, set_at = parse_iso(rec.get("until")), parse_iso(rec.get("set_at"))
            if until is None or set_at is None or until < moment:
                continue
            lifted = lifts.get(rec["host"])
            if lifted is not None and lifted >= set_at:
                continue
            current = active.get(rec["host"])
            if current is None or parse_iso(current["set_at"]) < set_at:
                active[rec["host"]] = rec
        return active

    # ---------------------------------------------------------- retention
    def purge(self, now: Optional[datetime] = None, days: int = RETENTION_DAYS) -> None:
        """Drop history lines and run directories older than ``days``.

        Only this master's own files are rewritten. last-success is never touched.
        """
        limit = (now or self.now()) - timedelta(days=days)
        path = self._own("history", "jsonl")
        if path.exists():
            keep = []
            for text in path.read_text(encoding="utf-8").splitlines():
                try:
                    rec = json.loads(text)
                except ValueError:
                    continue
                moment = run_id_time(str(rec.get("run_id", ""))) or parse_iso(rec.get("started"))
                if moment is None or moment >= limit:
                    keep.append(text)
            write_private(path, "".join(t + "\n" for t in keep))
        runs = self.root / "runs"
        if runs.is_dir():
            for child in runs.iterdir():
                moment = run_id_time(child.name)
                if moment is not None and moment < limit and child.is_dir():
                    shutil.rmtree(str(child), ignore_errors=True)

    def list_runs(self) -> List[str]:
        runs = self.root / "runs"
        if not runs.is_dir():
            return []
        names = [c.name for c in runs.iterdir() if c.is_dir() and RUN_ID.match(c.name)]
        return sorted(names, key=lambda n: (run_id_time(n) or datetime.min.replace(tzinfo=timezone.utc), n))
