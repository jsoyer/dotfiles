#!/usr/bin/env python3
"""Run reports: terminal, Markdown, JSON; run directory; logs and changes lookups.

Every string that leaves this module (screen, file) has been through
schema.mask_secrets again, so an unmasked value coming from any caller cannot
reach runs/ or the terminal. Stdlib only, Python 3.9 compatible.
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
SAFE_HOST = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")


def counts(entries: List[Dict[str, Any]]) -> Dict[str, int]:
    out: Dict[str, int] = {}
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


def render_terminal(rep: Dict[str, Any], data: Optional[Dict[str, Any]] = None) -> str:
    lines = ["fleet %s  run %s  selector: %s" % (rep["master"], rep["run_id"], rep.get("selector") or "(all)")]
    for e in rep["hosts"]:
        lines.append("%-22s %-12s %s" % (e["host"], e["status"], _detail(e)))
    lines.append(summary_line(rep["hosts"]))
    return schema.mask_secrets("\n".join(lines)) + "\n"


def render_markdown(rep: Dict[str, Any], data: Optional[Dict[str, Any]] = None) -> str:
    lines = [
        "# fleet run %s" % rep["run_id"], "",
        "- master: %s" % rep["master"],
        "- selector: %s" % (rep.get("selector") or "(all)"),
        "- started: %s" % rep.get("started"), "- ended: %s" % rep.get("ended"),
        "- summary: %s" % summary_line(rep["hosts"]), "",
        "| host | kind/site | status | detail |", "| --- | --- | --- | --- |",
    ]
    for e in rep["hosts"]:
        lines.append("| %s | %s | %s | %s |" % (
            e["host"], _meta(data, e["host"]), e["status"], _detail(e).replace("|", "/")))
    return schema.mask_secrets("\n".join(lines)) + "\n"


def write_run(
    st: "fstate.State", rep: Dict[str, Any], raw: Dict[str, Dict[str, Any]],
    log_lines: List[str], data: Optional[Dict[str, Any]] = None,
) -> Path:
    """Write runs/<run>/{report.json,report.md,run.log,raw/<host>.json|log}, all masked, 0600."""
    run = st.run_dir(rep["run_id"])
    fstate.make_private_dir(run)
    fstate.make_private_dir(run / "raw")
    fstate.write_private(run / "report.json",
                         schema.mask_secrets(json.dumps(rep, indent=1, sort_keys=True)) + "\n")
    fstate.write_private(run / "report.md", render_markdown(rep, data))
    fstate.write_private(run / "run.log", schema.mask_secrets("\n".join(log_lines)) + "\n")
    for alias, item in raw.items():
        if not SAFE_HOST.match(alias):
            continue
        fstate.write_private(run / "raw" / (alias + ".json"),
                             schema.mask_secrets(json.dumps(item.get("json"), indent=1, sort_keys=True)) + "\n")
        fstate.write_private(run / "raw" / (alias + ".log"), schema.mask_secrets(item.get("log") or "") + "\n")
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
    if not SAFE_HOST.match(alias):
        raise ValueError("invalid host name")


def host_logs(st: "fstate.State", alias: str, run_id: Optional[str] = None) -> str:
    _check_host(alias)
    ids = [run_id] if run_id else list(reversed(st.list_runs()))
    for rid in ids:
        path = st.run_dir(rid) / "raw" / (alias + ".log")
        if path.is_file():
            return schema.mask_secrets(path.read_text(encoding="utf-8"))
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
        for ch in (item or {}).get("changes") or []:
            out.append("%s  %s  %s -> %s" % (rid, ch.get("name"), ch.get("from") or "?", ch.get("to") or "?"))
    return schema.mask_secrets("\n".join(out)) + ("\n" if out else "")


def list_runs_text(st: "fstate.State", limit: int = 20) -> str:
    lines = []
    for rid in reversed(st.list_runs()[-limit:]):
        rep = read_report(st, rid)
        lines.append("%s  %s" % (rid, summary_line(rep["hosts"]) if rep else "(unreadable)"))
    return "\n".join(lines) + ("\n" if lines else "")

