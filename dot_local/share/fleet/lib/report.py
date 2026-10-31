#!/usr/bin/env python3
"""Run reports: terminal, Markdown, JSON; run directory; logs and changes lookups.

Every string that leaves this module (screen, file) has been through
schema masking again, so an unmasked value coming from any caller cannot reach
runs/ or the terminal. JSON is masked on the data structure (strings only) BEFORE
json.dumps: a regex over serialized JSON would corrupt it. Reports read back from
disk may come from the other master (rsync): malformed entries are skipped. Stdlib only, Python 3.9 compatible.
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import schema
import state as fstate

OK_STATUSES = ("updated", "up-to-date")
BAD_STATUSES = ("failed", "degraded", "unreachable", "timeout")
SAFE_HOST = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*")
MAX_RAW_LOG = 262144   # bytes kept per raw host log (write and read)
_MD_SPECIAL = re.compile(r"([\\`*_\[\]<>!|])")


def valid_entries(entries: Any) -> List[Dict[str, Any]]:
    """Entries that are objects with a host and a status, from untrusted-shaped data."""
    if not isinstance(entries, list):
        return []
    return [e for e in entries if isinstance(e, dict) and isinstance(e.get("host"), str)
            and isinstance(e.get("status"), str)]


def md_escape(text: Any) -> str:
    """Neutralize Markdown/HTML syntax in agent-provided text (masking happens before)."""
    return _MD_SPECIAL.sub(r"\\\1", str(text))


def counts(entries: List[Dict[str, Any]]) -> Dict[str, int]:
    out: Dict[str, int] = {}
    entries = valid_entries(entries)
    for e in entries:
        out[e["status"]] = out.get(e["status"], 0) + 1
    out["reboot"] = sum(1 for e in entries if e.get("reboot_required") is True)
    return out


def summary_line(entries: List[Dict[str, Any]]) -> str:
    c = counts(entries)
    ok = sum(c.get(s, 0) for s in OK_STATUSES)
    bad = sum(c.get(s, 0) for s in BAD_STATUSES)
    parts = ["%d ✅" % ok, "%d ❌" % bad]
    for label in ("reboot", "offline", "held", "skipped", "busy", "unsupported"):
        if c.get(label):
            parts.append("%d %s" % (c[label], label))
    return " · ".join(parts)


def build_report(
    run_id: str, master: str, selector: str, started: str, ended: str,
    entries: List[Dict[str, Any]],
) -> Dict[str, Any]:
    return {
        "schema": 1, "run_id": run_id, "master": master,
        "selector": schema.clean_text(selector, 300),
        "started": started, "ended": ended, "hosts": entries,
    }


def _detail(e: Dict[str, Any]) -> str:
    bits = []
    if e.get("packages") is not None:
        bits.append("packages=%s" % e["packages"])
    if e.get("reboot_required"):
        bits.append("reboot required")
    if e.get("last_seen"):
        bits.append("last seen %s" % e["last_seen"])
    if e.get("reason"):
        bits.append(str(e["reason"]))
    return schema.clean_text("; ".join(bits), 300)


def _meta(data: Optional[Dict[str, Any]], alias: str) -> str:
    host = ((data or {}).get("hosts") or {}).get(alias) or {}
    return "%s/%s" % (host.get("kind", "?"), host.get("site", "?"))


def _hosts_of(rep: Dict[str, Any]) -> List[Dict[str, Any]]:
    return valid_entries(rep.get("hosts"))


def render_terminal(rep: Dict[str, Any], data: Optional[Dict[str, Any]] = None) -> str:
    lines = ["fleet %s  run %s  selector: %s" % (
        schema.clean_text(rep.get("master", "?"), 60), schema.clean_text(rep.get("run_id", "?"), 60),
        schema.clean_text(rep.get("selector") or "(all)", 300))]
    for e in _hosts_of(rep):
        lines.append("%-22s %-12s %s" % (schema.clean_text(e["host"], 80), schema.clean_text(e["status"], 20),
                                         _detail(e)))
    lines.append(summary_line(_hosts_of(rep)))
    return "\n".join(lines) + "\n"


def render_markdown(rep: Dict[str, Any], data: Optional[Dict[str, Any]] = None) -> str:
    lines = [
        "# fleet run %s" % md_escape(schema.clean_text(rep.get("run_id", "?"), 60)), "",
        "- master: %s" % md_escape(schema.clean_text(rep.get("master", "?"), 60)),
        "- selector: %s" % md_escape(schema.clean_text(rep.get("selector") or "(all)", 300)),
        "- started: %s" % md_escape(schema.clean_text(rep.get("started"), 40)),
        "- ended: %s" % md_escape(schema.clean_text(rep.get("ended"), 40)),
        "- summary: %s" % summary_line(_hosts_of(rep)), "",
        "| host | kind/site | status | detail |", "| --- | --- | --- | --- |",
    ]
    for e in _hosts_of(rep):
        lines.append("| %s | %s | %s | %s |" % (
            md_escape(schema.clean_text(e["host"], 80)), md_escape(schema.clean_text(_meta(data, e["host"]), 80)),
            md_escape(schema.clean_text(e["status"], 20)), md_escape(_detail(e))))
    return "\n".join(lines) + "\n"


def clean_log(text: Any) -> str:
    """Raw host log, safe to store or show: control/ANSI stripped, THEN masked, byte-bounded."""
    out = schema.clean_text(str(text)[: MAX_RAW_LOG * 2], MAX_RAW_LOG, multiline=True)
    return out.encode("utf-8")[:MAX_RAW_LOG].decode("utf-8", "ignore")


def write_run(
    st: "fstate.State", rep: Dict[str, Any], raw: Dict[str, Dict[str, Any]],
    log_lines: List[str], data: Optional[Dict[str, Any]] = None,
) -> Path:
    """Write runs/<run>/{report.json,report.md,run.log,raw/<host>.json|log}, all masked, 0600."""
    run = st.run_dir(rep["run_id"])
    fstate.make_private_dir(run)
    fstate.make_private_dir(run / "raw")
    fstate.write_private(run / "report.json", json.dumps(schema.mask_data(rep), indent=1, sort_keys=True) + "\n")
    fstate.write_private(run / "report.md", render_markdown(rep, data))
    fstate.write_private(run / "run.log", schema.mask_secrets("\n".join(log_lines)) + "\n")
    for alias, item in raw.items():
        if not SAFE_HOST.fullmatch(alias):
            continue
        fstate.write_private(run / "raw" / (alias + ".json"),
                             json.dumps(schema.mask_data(item.get("json")), indent=1, sort_keys=True) + "\n")
        fstate.write_private(run / "raw" / (alias + ".log"), clean_log(item.get("log") or "") + "\n")
    return run


def stale_hosts(
    last_success: Dict[str, str], now: datetime, days: int = 30,
) -> List[Tuple[str, str, int]]:
    """(host, last success ISO, age in days) for hosts whose last success is > ``days`` old."""
    out = []
    for host, when in sorted(last_success.items()):
        moment = fstate.parse_iso(when)
        if moment is None:
            continue
        age = (now - moment).days
        if age > days:
            out.append((host, when, age))
    return out


def read_report(st: "fstate.State", run_id: str) -> Optional[Dict[str, Any]]:
    try:
        data = json.loads((st.run_dir(run_id) / "report.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def latest_run(st: "fstate.State") -> Optional[Tuple[str, Dict[str, Any]]]:
    """Most recent run across masters (own runs plus the rsync'd ones)."""
    for run_id in reversed(st.list_runs()):
        rep = read_report(st, run_id)
        if rep is not None:
            return run_id, rep
    return None


def _check_host(alias: str) -> None:
    if not SAFE_HOST.fullmatch(alias):
        raise ValueError("invalid host name")


def host_logs(st: "fstate.State", alias: str, run_id: Optional[str] = None) -> str:
    _check_host(alias)
    ids = [run_id] if run_id else list(reversed(st.list_runs()))
    for rid in ids:
        path = st.run_dir(rid) / "raw" / (alias + ".log")   # run_dir validates the id
        try:
            if path.is_file():
                with path.open("rb") as fh:
                    raw = fh.read(MAX_RAW_LOG + 1)
                return clean_log(raw.decode("utf-8", errors="replace"))
        except OSError:
            continue
    return ""


def host_changes(st: "fstate.State", alias: str, since: Optional[datetime]) -> str:
    _check_host(alias)
    out: List[str] = []
    for rid in reversed(st.list_runs()):
        moment = fstate.run_id_time(rid)
        if since is not None and moment is not None and moment < since:
            continue
        path = st.run_dir(rid) / "raw" / (alias + ".json")
        try:
            item = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        changes = item.get("changes") if isinstance(item, dict) else None
        for ch in changes if isinstance(changes, list) else []:
            if not isinstance(ch, dict) or not isinstance(ch.get("name"), str):
                continue
            out.append("%s  %s  %s -> %s" % (
                rid, schema.clean_text(ch["name"], 120), schema.clean_text(ch.get("from") or "?", 80),
                schema.clean_text(ch.get("to") or "?", 80)))
    return "\n".join(out) + ("\n" if out else "")


def list_runs_text(st: "fstate.State", limit: int = 20) -> str:
    lines = []
    for rid in reversed(st.list_runs()[-limit:]):
        rep = read_report(st, rid)
        lines.append("%s  %s" % (rid, summary_line(rep.get("hosts")) if rep else "(unreadable)"))
    return "\n".join(lines) + ("\n" if lines else "")

