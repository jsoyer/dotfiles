#!/usr/bin/env python3
"""fleet orchestrator: `up` by phases, `reboot --pending`, reports, holds, reminder.

Master-side only. Every outside effect (Tailscale, SSH, rsync, ntfy, 1Password)
goes through an injectable seam so the whole thing is exercised with fakes:
the ``transport`` object (peers/probe/call/local_call/list_vms/sync/run_on_master)
and the ``Notifier`` sender. The default ``SshTransport`` only ever runs argument
lists (no shell), only ever sends one of the five whitelisted agent verbs, and
caps what it reads back on stdout AND stderr.

Agent output is untrusted: it goes through schema.parse_agent_output before any
use; invalid means ``failed``.

Stdlib only, Python 3.9 compatible. CLI entry: ``orchestrate.py <command> ...``
(called by dot_local/bin/executable_fleet).
"""

import argparse
import os
import shlex
import signal
import socket
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, NamedTuple, Optional, Sequence, Tuple

_LIB = os.path.dirname(os.path.abspath(__file__))
if _LIB not in sys.path:
    sys.path.insert(0, _LIB)

import inventory as inv  # noqa: E402
import notify  # noqa: E402
import report  # noqa: E402
import schema  # noqa: E402
import selector  # noqa: E402
import state as fstate  # noqa: E402

OUT_CAP = 65536   # bytes of agent stdout kept
ERR_CAP = 4096    # bytes of ssh stderr kept
CALL_TIMEOUT = 60  # seconds for one agent call (updates are detached, calls are short)
PHASE1_KINDS = ("chezmoi-linux", "chezmoi-macos", "omv", "pikvm", "windows")
PHASE2_KINDS = ("homeassistant", "guardian")
PHASE2_TAGS = ("infra", "site-router")
CANARY_BLOCKING = ("failed", "degraded", "timeout")
YES = ("y", "yes", "o", "oui")


# ---------------------------------------------------------------- transport


def run_capped(
    argv: Sequence[str], timeout: float, env: Optional[Dict[str, str]] = None,
    out_cap: int = OUT_CAP, err_cap: int = ERR_CAP,
) -> Tuple[int, str, str]:
    """Run an argument list (no shell), keep at most out_cap / err_cap bytes of each stream.

    A stdout flood or the timeout kills the whole process group (a flooding host
    cannot fill memory or disk). Excess stderr is only drained and discarded (the
    returned text ends with a truncation marker): chatty ssh warnings must not turn
    a good answer into a failure. Returns (rc, stdout, stderr).
    """
    proc = subprocess.Popen(
        list(argv), stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        env=env, start_new_session=True)

    def kill() -> None:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except (OSError, ProcessLookupError):
            pass

    store: Dict[str, bytes] = {}
    truncated: set = set()

    def pump(name: str, stream: Any, cap: int, fatal: bool) -> None:
        data = stream.read(cap)
        store[name] = data
        if len(data) >= cap and stream.read(1):
            if fatal:
                kill()
                return
            truncated.add(name)
            while stream.read(65536):
                pass

    threads = [threading.Thread(target=pump, args=("out", proc.stdout, out_cap, True)),
               threading.Thread(target=pump, args=("err", proc.stderr, err_cap, False))]
    timer = threading.Timer(timeout, kill)
    timer.start()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    rc = proc.wait()
    timer.cancel()
    kill()  # reap background children that outlived the shell
    proc.stdout.close()
    proc.stderr.close()
    err_text = store.get("err", b"").decode("utf-8", "replace") + (" [truncated]" if "err" in truncated else "")
    return rc, store.get("out", b"").decode("utf-8", "replace"), err_text


class SshTransport:
    """Real transport. Never instantiated by tests except against fake ssh/agent scripts."""

    def __init__(self, data: Dict[str, Any], env: Dict[str, str]) -> None:
        self.data = data
        self.env = env
        self.ssh = env.get("FLEET_SSH", "ssh")
        opts = ["-o", "BatchMode=yes", "-o", "ConnectTimeout=10", "-o", "StrictHostKeyChecking=yes",
                "-o", "ServerAliveInterval=5", "-o", "ServerAliveCountMax=3"]
        if env.get("FLEET_SSH_IDENTITY"):
            opts += ["-i", env["FLEET_SSH_IDENTITY"], "-o", "IdentitiesOnly=yes"]
        self.opts = opts

    def _target(self, alias: str) -> str:
        """user@host. Never starts with '-' (would be read as an ssh option): validated here too."""
        host = self.data["hosts"][alias]
        name, user = host["tailnet_name"], host.get("ssh_user")
        if not isinstance(name, str) or not inv.SAFE_NAME.fullmatch(name):
            raise ValueError("unsafe ssh host name")
        if user is not None and (not isinstance(user, str) or not inv.SAFE_USER.fullmatch(user)):
            raise ValueError("unsafe ssh user")
        return "%s@%s" % (user, name) if user else name

    def peers(self) -> Optional[Dict[str, Dict[str, Any]]]:
        return inv.read_tailscale()

    def probe(self, alias: str) -> bool:
        """SSH opens within 10 s (authentication deliberately not attempted: no agent call)."""
        argv = [self.ssh] + self.opts + [
            "-o", "PreferredAuthentications=none", "-o", "PubkeyAuthentication=no",
            "-o", "NumberOfPasswordPrompts=0", "--", self._target(alias), "true"]
        try:
            _, out, err = run_capped(argv, 15)
        except OSError:
            return False
        return "Permission denied" in (out + err)

    def call(self, alias: str, verb: str, timeout: float = CALL_TIMEOUT) -> Tuple[int, str, str]:
        if verb not in schema.VERBS:
            raise ValueError("not an agent verb: %r" % (verb,))
        argv = [self.ssh] + self.opts + ["-T", "--", self._target(alias), verb]
        try:
            return run_capped(argv, timeout)
        except OSError as exc:
            return 255, "", "cannot run ssh: %s" % exc.__class__.__name__

    def local_call(self, alias: str, verb: str, timeout: float = CALL_TIMEOUT) -> Tuple[int, str, str]:
        """The master updates itself through the installed agent, same verbs, no ssh."""
        if verb not in schema.VERBS:
            raise ValueError("not an agent verb: %r" % (verb,))
        agent = self.env.get("FLEET_LOCAL_AGENT", "/usr/local/libexec/fleet-agent")
        child_env = dict(os.environ)
        child_env["SSH_ORIGINAL_COMMAND"] = verb
        try:
            return run_capped([agent], timeout, env=child_env)
        except OSError as exc:
            return 255, "", "cannot run local agent: %s" % exc.__class__.__name__

    def list_vms(self, alias: str) -> Optional[List[str]]:
        return None  # no agent verb lists VMs (closed whitelist): the warning says so

    def sync(self, master: str, peers: List[str]) -> bool:
        """rsync this master's own files to each peer master (best effort)."""
        if self.env.get("FLEET_SYNC", "1") == "0":
            return True
        root = fstate.default_root(self.env)
        rsync = self.env.get("FLEET_RSYNC", "rsync")
        ok = True
        for peer in peers:
            if peer not in self.data["hosts"]:
                continue
            filters = [
                "--include=history-%s.jsonl" % master, "--include=last-success-%s.json" % master,
                "--include=holds-%s.json" % master, "--include=runs/",
                "--include=runs/*-%s/" % master, "--include=runs/*-%s/***" % master, "--exclude=*"]
            try:
                argv = [rsync, "-a", "-e", " ".join(shlex.quote(p) for p in [self.ssh] + self.opts)] + filters + [
                    "--", str(root) + "/", self._target(peer) + ":.local/state/fleet/"]
                rc, _, _ = run_capped(argv, 120)
            except (OSError, ValueError):
                rc = 255
            ok = ok and rc == 0
        return ok

    def run_on_master(self, master: str, argv: List[str]) -> Optional[int]:
        """Run `fleet <argv>` on a master with the console's terminal. None = master unreachable."""
        if not self.probe(master):
            return None
        remote = "fleet " + " ".join(shlex.quote(a) for a in argv)
        proc = subprocess.run([self.ssh] + self.opts + ["-t", "--", self._target(master), remote])
        return None if proc.returncode == 255 else proc.returncode


# ---------------------------------------------------------------- selection helpers


def implicit_targets(data: Dict[str, Any], master: Optional[str]) -> List[str]:
    """No -l: the whole fleet, minus the OTHER master (each master treats itself)."""
    others = set(data.get("masters") or []) - set([master] if master else [])
    if master is None:
        others = set()
    return [a for a in data["hosts"] if a not in others]


def choose_masters(data: Dict[str, Any], targets: Sequence[str]) -> List[str]:
    """Masters a console should try, best first: the master of the first target's site, then the rest."""
    masters = list(data.get("masters") or [])
    preferred = None
    if targets and targets[0] in data["hosts"]:
        preferred = (data.get("master_priority") or {}).get(data["hosts"][targets[0]]["site"])
    if preferred in masters:
        masters.remove(preferred)
        masters.insert(0, preferred)
    return masters


# ---------------------------------------------------------------- orchestrator


class Options:
    def __init__(
        self, critical: bool = False, no_canary: bool = False, dry_run: bool = False,
        confirm: Optional[Callable[[str], bool]] = None,
        say: Optional[Callable[[str], None]] = None,
        sleep: Callable[[float], None] = time.sleep, poll_interval: float = 15.0,
        reboot_wait_min: int = 15,
    ) -> None:
        self.critical, self.no_canary, self.dry_run = critical, no_canary, dry_run
        self.confirm = confirm
        self.say = say or (lambda text: None)
        self.sleep, self.poll_interval, self.reboot_wait_min = sleep, poll_interval, reboot_wait_min


class Plan(NamedTuple):
    phases: List[List[str]]
    critical: List[str]
    last: Optional[str]


class Orchestrator:
    def __init__(
        self, data: Dict[str, Any], st: "fstate.State", master: str, transport: Any,
        notifier: Optional["notify.Notifier"], options: Optional[Options] = None,
        now: Callable[[], datetime] = fstate.utcnow,
    ) -> None:
        self.data, self.st, self.master = data, st, master
        self.transport, self.notifier = transport, notifier
        self.opt = options or Options()
        self.now = now
        self.hosts = data["hosts"]
        par = data.get("parallel") or {}
        self.total = int(par.get("total") or 10)
        self.per_site = int(par.get("per_site") or 4)
        self._lock = threading.Lock()
        self._reset()

    def _reset(self) -> None:
        self.results: Dict[str, Dict[str, Any]] = {}
        self.raw: Dict[str, Dict[str, Any]] = {}
        self.log_lines: List[str] = []
        self.canary_failed: set = set()
        self.refused: List[str] = []
        self._site_cache: Dict[str, bool] = {}
        self.peers: Optional[Dict[str, Dict[str, Any]]] = None
        self.holds: Dict[str, Dict[str, Any]] = {}

    # ------------------------------------------------------------ small helpers
    def _iso(self) -> str:
        return fstate.iso(self.now())

    def _log(self, text: str) -> None:
        with self._lock:
            self.log_lines.append("%s %s" % (self._iso(), schema.clean_text(text, 400)))

    def _skip(self, alias: str, verb: str, reason: str, t0: str) -> Dict[str, Any]:
        return {"schema": 1, "host": alias, "verb": verb, "status": "skipped",
                "reason": schema.clean_text(reason), "started": t0, "ended": self._iso()}

    def _master_entry(self, alias: str, verb: str, status: str, reason: str, t0: str,
                      last_seen: Optional[str] = None) -> Dict[str, Any]:
        return schema.master_entry(alias, verb, status, reason, last_seen, t0, self._iso())

    def _last_seen(self, alias: str) -> Optional[str]:
        return inv.peer_state(self.hosts[alias]["tailnet_name"], self.peers)[1]

    # ------------------------------------------------------------ planning
    def plan(self, aliases: Sequence[str]) -> Plan:
        gateway = (self.data.get("ntfy") or {}).get("gateway")
        p1: List[str] = []
        p2: List[str] = []
        p3: List[str] = []
        crit: List[str] = []
        last = None
        wanted = set(aliases)
        for alias, host in self.hosts.items():
            if alias not in wanted:
                continue
            if host.get("critical"):          # even the current master: --critical is never bypassed
                crit.append(alias)
            elif alias == self.master:
                last = alias
            elif alias == gateway:
                p3.append(alias)
            elif host["kind"] in PHASE2_KINDS or set(host.get("tags") or []) & set(PHASE2_TAGS):
                p2.append(alias)
            elif host["kind"] in PHASE1_KINDS:
                p1.append(alias)
            else:
                p2.append(alias)
        # critical order: OPNsense first, then the hypervisor (multibox)
        # (a critical current master goes last of all and is updated locally)
        crit.sort(key=lambda a: (1 if a == self.master else 0, 0 if self.hosts[a]["kind"] == "opnsense" else 1))
        return Plan([p1, p2, p3], crit, last)

    def describe_plan(self, plan: Plan) -> str:
        names = ("phase 1 (parallel)", "phase 2 (serial)", "phase 3 (alone)")
        lines = ["%s: %s" % (n, ", ".join(p)) for n, p in zip(names, plan.phases) if p]
        if plan.critical:
            lines.append("critical (needs --critical + confirmation): %s" % ", ".join(plan.critical))
        if plan.last:
            lines.append("current master, last and local: %s" % plan.last)
        return "\n".join(lines) + "\n"

    def describe_reboot(self, aliases: Sequence[str]) -> str:
        ask: List[str] = []
        skip: List[str] = []
        for alias in aliases:
            if alias == self.master:
                skip.append("%s (current master: restart it by hand)" % alias)
            elif self.hosts[alias].get("critical") and not self.opt.critical:
                skip.append("%s (critical: needs --critical)" % alias)
            else:
                ask.append(alias)
        lines = ["reboot (one at a time, each confirmed; only hosts reporting a pending reboot): %s"
                 % (", ".join(ask) if ask else "none")]
        if skip:
            lines.append("skipped: " + "; ".join(skip))
        return "\n".join(lines) + "\n"

    # ------------------------------------------------------------ gates
    def _site_healthy(self, site: str) -> bool:
        """>= 1 other (non-guardian) host of the site is online: Tailscale AND ssh <= 10 s."""
        with self._lock:
            if site in self._site_cache:
                return self._site_cache[site]
        healthy = False
        for alias, host in self.hosts.items():
            if host["site"] != site or host["kind"] == "guardian" or not host.get("ssh_user"):
                continue
            state, _ = inv.online_state(host["tailnet_name"], self.peers, lambda a=alias: self.transport.probe(a))
            if state == "online":
                healthy = True
                break
        with self._lock:
            self._site_cache[site] = healthy
        return healthy

    def _gate(self, alias: str, verb: str, t0: str, local: bool) -> Optional[Dict[str, Any]]:
        host = self.hosts[alias]
        hold = self.holds.get(alias)
        if hold:
            return self._master_entry(
                alias, verb, "held", "held: %s (until %s)" % (hold.get("reason"), hold.get("until")), t0)
        if verb == "update" and not self.opt.no_canary and host["kind"] in self.canary_failed \
                and not host.get("canary"):
            return self._skip(alias, verb, "canary failed for kind %s" % host["kind"], t0)
        if host["kind"] == "guardian" and not self._site_healthy(host["site"]):
            return self._skip(alias, verb, "site degraded: guardian is the only access", t0)
        if not local:
            state, seen = inv.peer_state(host["tailnet_name"], self.peers)
            if state == "offline":
                return self._master_entry(alias, verb, "offline", "tailscale offline", t0, seen)
            if state == "absent":
                return self._master_entry(alias, verb, "unreachable", "not in tailscale status", t0)
            if not host.get("ssh_user"):
                return {"schema": 1, "host": alias, "verb": verb, "status": "unsupported",
                        "reason": "no agent for kind %s yet" % host["kind"], "started": t0, "ended": self._iso()}
        return None

    # ------------------------------------------------------------ one agent answer
    def _call(self, alias: str, verb: str, local: bool, raw: List[str]) -> Tuple[Optional[Dict[str, Any]], str, Dict[str, Any]]:
        """-> (entry or None, kind, fallback). kind: ok | refused | none | invalid."""
        fn = self.transport.local_call if local else self.transport.call
        try:
            rc, out, err = fn(alias, verb)
        except (OSError, ValueError) as exc:
            rc, out, err = 255, "", exc.__class__.__name__
        errline = schema.clean_text((err or "").strip().splitlines()[0] if (err or "").strip() else "", 120)
        raw.append("== %s rc=%s %s" % (verb, rc, errline))
        if not (out or "").strip():
            kind = "refused" if errline.startswith("fleet-agent: refused") else "none"
            return None, kind, {"rc": rc, "err": errline}
        ent, why = schema.parse_agent_output(out, alias, verb)
        if ent is None:
            raw.append(schema.clean_text(why or "", 200))
            return None, "invalid", {"why": why or "invalid agent output", "rc": rc, "err": errline}
        if ent.get("log_tail"):
            raw.append(ent["log_tail"])
        return ent, "ok", {"rc": rc, "err": errline}

    def _no_answer(self, alias: str, verb: str, kind: str, info: Dict[str, Any], t0: str) -> Dict[str, Any]:
        if kind == "refused":
            with self._lock:
                self.refused.append(alias)
            return schema.failed_entry(alias, verb, "agent refused the call (%s)" % info["err"], t0)
        if kind == "invalid":
            return schema.failed_entry(alias, verb, info["why"], t0)
        return self._master_entry(
            alias, verb, "unreachable",
            "no answer from agent (ssh exit %s%s)" % (info["rc"], (": " + info["err"]) if info["err"] else ""),
            t0, self._last_seen(alias))

    # ------------------------------------------------------------ update
    def _update(self, alias: str, local: bool, t0: str, raw: List[str]) -> Dict[str, Any]:
        timeout_min = inv.timeout_for(self.data, alias)
        began = self.now()
        ent, kind, info = self._call(alias, "update", local, raw)
        if ent is None:
            return self._no_answer(alias, "update", kind, info, t0)
        while ent["status"] in ("started", "running"):
            if self.now() - began >= timedelta(minutes=timeout_min):
                job = ent.get("job") or "?"
                return self._master_entry(alias, "update", "timeout",
                                          "job %s not finished after %d min" % (job, timeout_min), t0)
            self.opt.sleep(self.opt.poll_interval)
            polled, kind, info = self._call(alias, "report", local, raw)
            if polled is None:
                if kind in ("refused", "invalid"):
                    return self._no_answer(alias, "report", kind, info, t0)
                continue      # ssh cut (tailscale/openssh restarting): the detached job continues
            ent = polled
        return ent

    # ------------------------------------------------------------ one host (up)
    def _process(self, alias: str, local: bool) -> Dict[str, Any]:
        t0 = self._iso()
        raw: List[str] = []
        entry = self._gate(alias, "update", t0, local)
        if entry is None:
            entry = self._update(alias, local, t0, raw)
        entry.setdefault("last_seen", None)
        if not entry.get("started"):
            entry["started"] = t0
        if not entry.get("ended"):
            entry["ended"] = self._iso()
        with self._lock:
            self.results[alias] = entry
            self.raw[alias] = {"json": entry, "log": "\n".join(raw)}
            if entry["status"] in CANARY_BLOCKING and self.hosts[alias].get("canary"):
                self.canary_failed.add(self.hosts[alias]["kind"])
        self._log("%s: %s%s" % (alias, entry["status"], (" - " + entry["reason"]) if entry.get("reason") else ""))
        return entry

    def _safe_process(self, alias: str, local: bool = False) -> None:
        try:
            self._process(alias, local)
        except Exception as exc:  # noqa: BLE001 - one host must never abort the run
            entry = schema.failed_entry(alias, "update", "internal error: %s" % exc.__class__.__name__, self._iso())
            entry["last_seen"] = None
            with self._lock:
                self.results[alias] = entry
                self.raw[alias] = {"json": entry, "log": ""}
            self._log("%s: internal error %r" % (alias, exc.__class__.__name__))

    def _run_group(self, aliases: List[str], parallel: bool) -> None:
        if not aliases:
            return
        if not parallel or len(aliases) == 1:
            for alias in aliases:
                self._safe_process(alias)
            return
        by_site: Dict[str, List[str]] = {}
        for alias in aliases:
            by_site.setdefault(self.hosts[alias]["site"], []).append(alias)
        order: List[str] = []
        while any(by_site.values()):          # round-robin across sites: no site hogs the pool
            for site in list(by_site):
                if by_site[site]:
                    order.append(by_site[site].pop(0))
        sems = dict((s, threading.BoundedSemaphore(self.per_site)) for s in by_site)

        def task(alias: str) -> None:
            with sems[self.hosts[alias]["site"]]:
                self._safe_process(alias)

        with ThreadPoolExecutor(max_workers=self.total) as pool:
            for future in [pool.submit(task, a) for a in order]:
                future.result()

    def _stage(self, aliases: List[str], parallel: bool) -> None:
        canaries = [] if self.opt.no_canary else [a for a in aliases if self.hosts[a].get("canary")]
        self._run_group(canaries, parallel)           # witnesses first
        self._run_group([a for a in aliases if a not in canaries], parallel)

    # ------------------------------------------------------------ critical hosts
    def _critical_warning(self, alias: str, action: str) -> str:
        vms = self.transport.list_vms(alias)
        host = self.hosts[alias]
        if vms:
            listing = "VMs that will be interrupted: " + ", ".join(vms)
        else:
            listing = "VM list unavailable (no agent verb): assume every VM/service behind it is interrupted"
        return "WARNING: %s (%s) is critical. %s %s." % (alias, host["kind"], action, listing)

    def _confirm(self, prompt: str) -> bool:
        return bool(self.opt.confirm and self.opt.confirm(prompt))

    def _critical_stage(self, aliases: List[str], verb: str = "update") -> None:
        for alias in aliases:
            t0 = self._iso()
            if not self.opt.critical:
                self._store(alias, self._skip(alias, verb, "critical host: --critical required", t0))
                continue
            self.opt.say(self._critical_warning(alias, "Updating it may restart services."))
            if not self._confirm("Update critical host %s? [y/N] " % alias):
                self._store(alias, self._skip(alias, verb, "critical update not confirmed", t0))
                continue
            self._safe_process(alias, local=(alias == self.master))

    def _store(self, alias: str, entry: Dict[str, Any]) -> None:
        entry.setdefault("last_seen", None)
        with self._lock:
            self.results[alias] = entry
            self.raw[alias] = {"json": entry, "log": ""}
        self._log("%s: %s - %s" % (alias, entry["status"], entry.get("reason")))

    # ------------------------------------------------------------ begin / finish
    def _begin(self) -> None:
        self._reset()
        self.holds = self.st.active_holds(self.now())
        self.peers = self.transport.peers()

    def _run_id(self) -> str:
        moment = self.now()
        while True:
            rid = moment.strftime("%Y%m%dT%H%MZ") + "-" + self.master
            if not self.st.run_dir(rid).exists():
                return rid
            moment = moment + timedelta(minutes=1)

    def _finish(self, rid: str, started: str, aliases: List[str], selector_text: str,
                persist_history: bool) -> Tuple[Dict[str, Any], int]:
        entries = [self.results[a] for a in aliases if a in self.results]
        ended = self._iso()
        rep = report.build_report(rid, self.master, selector_text, started, ended, entries)
        if persist_history:
            for e in entries:
                self.st.append_history(rid, e)
                if e["status"] in report.OK_STATUSES:
                    self.st.set_last_success(e["host"], e.get("ended") or ended)
        report.write_run(self.st, rep, self.raw, self.log_lines, self.data)
        rc = 1 if any(e["status"] in report.BAD_STATUSES for e in entries) else 0
        return rep, rc

    def _notify(self, msg: Dict[str, Any]) -> None:
        """A notification problem (any exception) is logged, never allowed to abort the run."""
        if self.notifier is None:
            return
        try:
            self.notifier.send(msg)
        except Exception as exc:  # noqa: BLE001
            self._log("notification error %s" % exc.__class__.__name__)

    def _sync_and_purge(self) -> None:
        peers = [m for m in (self.data.get("masters") or []) if m != self.master]
        try:
            ok = self.transport.sync(self.master, peers) if peers else True
        except Exception as exc:  # noqa: BLE001
            ok = False
            self._log("sync error %s" % exc.__class__.__name__)
        if not ok:
            self._log("state sync to %s failed (will be retried by the next run)" % ", ".join(peers))
        self.st.purge(self.now())

    # ------------------------------------------------------------ up
    def run_up(self, aliases: Sequence[str], selector_text: str = "") -> Tuple[Dict[str, Any], int]:
        aliases = list(aliases)
        self._begin()
        rid = self._run_id()
        started = self._iso()
        plan = self.plan(aliases)
        self._log("run %s selector=%s targets=%d" % (rid, selector_text, len(aliases)))
        self._stage(plan.phases[0], True)
        self._stage(plan.phases[1], False)
        self._stage(plan.phases[2], False)
        self._critical_stage(plan.critical)
        if plan.last:
            self._safe_process(plan.last, local=True)    # current master: last, local, no reboot
        rep, rc = self._finish(rid, started, aliases, selector_text, persist_history=True)
        for host in self.refused:
            self._notify(notify.refused_message(self.master, host))
        self._notify(notify.summary_message(self.master, rep["hosts"]))
        stale = [s for s in report.stale_hosts(self.st.last_success(), self.now()) if s[0] in self.hosts]
        if stale:
            self._notify(notify.stale_message(self.master, stale))
        self._sync_and_purge()
        return rep, rc

    # ------------------------------------------------------------ reboot --pending
    def _reboot_one(self, alias: str) -> Dict[str, Any]:
        t0 = self._iso()
        raw: List[str] = []
        host = self.hosts[alias]
        self.raw[alias] = {"json": None, "log": ""}
        if alias == self.master:
            return self._skip(alias, "reboot", "current master: restart it by hand", t0)
        if host.get("critical") and not self.opt.critical:
            return self._skip(alias, "reboot", "critical host: --critical required", t0)
        gate = self._gate(alias, "reboot", t0, False)
        if gate is not None:
            return gate
        status, kind, info = self._call(alias, "reboot-status", False, raw)
        if status is None:
            return self._no_answer(alias, "reboot-status", kind, info, t0)
        if status.get("reboot_required") is not True:
            return self._skip(alias, "reboot", "no reboot pending", t0)
        if host.get("critical"):
            self.opt.say(self._critical_warning(alias, "Rebooting it interrupts everything it hosts."))
        if not self._confirm("Reboot %s (%s, %s)? [y/N] " % (alias, host["kind"], host["site"])):
            return self._skip(alias, "reboot", "reboot declined", t0)
        sent, kind, info = self._call(alias, "reboot", False, raw)
        if sent is None and kind in ("refused", "invalid"):
            return self._no_answer(alias, "reboot", kind, info, t0)
        if sent is not None and sent["status"] in ("failed", "busy", "skipped", "unsupported"):
            return sent                    # the agent said no: it is not going to reboot, do not wait for it
        wait = timedelta(minutes=self.opt.reboot_wait_min * (2 if host.get("critical") else 1))
        began = self.now()
        while self.now() - began < wait:
            self.opt.sleep(self.opt.poll_interval)
            back, kind, info = self._call(alias, "reboot-status", False, raw)
            if back is not None and back.get("reboot_required") is not True:
                done = dict(back)
                done.update({"verb": "reboot", "status": "updated", "reason": "rebooted"})
                self.raw[alias] = {"json": done, "log": "\n".join(raw)}
                return done
        self.raw[alias] = {"json": None, "log": "\n".join(raw)}
        self._notify(notify.not_back_message(self.master, alias))
        return self._master_entry(alias, "reboot", "timeout", "did not come back after reboot", t0,
                                  self._last_seen(alias))

    def run_reboot(self, aliases: Sequence[str], selector_text: str = "") -> Tuple[Dict[str, Any], int]:
        aliases = list(aliases)
        self._begin()
        rid = self._run_id()
        started = self._iso()
        for alias in aliases:     # strictly one machine at a time, each one confirmed
            try:
                entry = self._reboot_one(alias)
            except Exception as exc:  # noqa: BLE001
                entry = schema.failed_entry(alias, "reboot", "internal error: %s" % exc.__class__.__name__, self._iso())
            entry.setdefault("last_seen", None)
            entry.setdefault("started", started)
            entry.setdefault("ended", self._iso())
            if self.raw.get(alias, {}).get("json") is None:
                self.raw[alias] = {"json": entry, "log": self.raw.get(alias, {}).get("log", "")}
            self.results[alias] = entry
            self._log("%s: reboot %s" % (alias, entry["status"]))
        rep, rc = self._finish(rid, started, aliases, selector_text, persist_history=False)
        self._sync_and_purge()
        return rep, rc


# ---------------------------------------------------------------- CLI


def tty_confirm(prompt: str) -> bool:
    if not sys.stdin.isatty():
        return False
    sys.stderr.write(prompt)
    sys.stderr.flush()
    return sys.stdin.readline().strip().lower() in YES


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="fleet", add_help=True)
    sub = ap.add_subparsers(dest="cmd")

    def targets(p: argparse.ArgumentParser) -> None:
        p.add_argument("hosts", nargs="*")
        p.add_argument("-l", "--label", action="append", default=None, metavar="SELECTOR")

    up = sub.add_parser("up", help="update the fleet by phases")
    targets(up)
    up.add_argument("--dry-run", action="store_true")
    up.add_argument("--critical", action="store_true")
    up.add_argument("--no-canary", action="store_true")
    rb = sub.add_parser("reboot", help="reboot hosts that need it, one confirmation each")
    targets(rb)
    rb.add_argument("--pending", action="store_true")
    rb.add_argument("--critical", action="store_true")
    rb.add_argument("--dry-run", action="store_true")
    rp = sub.add_parser("report")
    rp.add_argument("--last", action="store_true")
    rp.add_argument("--run")
    lg = sub.add_parser("logs")
    targets(lg)
    lg.add_argument("--run")
    ch = sub.add_parser("changes")
    ch.add_argument("host")
    ch.add_argument("--since")
    hd = sub.add_parser("hold")
    hd.add_argument("hosts", nargs="+")
    hd.add_argument("--reason")
    hd.add_argument("--until")
    uh = sub.add_parser("unhold")
    uh.add_argument("hosts", nargs="+")
    sub.add_parser("holds")
    sub.add_parser("reminder")
    return ap


def _tokens(args: argparse.Namespace) -> Optional[List[str]]:
    """User-given selector tokens, or None when the user gave none."""
    given = list(getattr(args, "hosts", []) or []) + list(getattr(args, "label", None) or [])
    return given if (given or getattr(args, "label", None) is not None) else None


def _make_notifier(data: Dict[str, Any], st: "fstate.State", env: Dict[str, str],
                   err: Any) -> Optional["notify.Notifier"]:
    """Built only when a notification may actually be sent (never for --dry-run: no `op read`)."""
    cfg = data.get("ntfy") or {}
    token = notify.resolve_token(cfg.get("token_ref"), env, lambda args: notify.default_op_runner(args, env))
    try:
        return notify.Notifier(cfg.get("url", ""), cfg.get("topic", "fleet"), token, st.root / "ntfy-queue")
    except ValueError as exc:
        err.write("fleet: notifications disabled: %s\n" % exc)
        return None


def main(
    argv: Sequence[str], env: Optional[Dict[str, str]] = None, transport: Any = None,
    notifier: Optional["notify.Notifier"] = None, out: Any = None, err: Any = None,
    sleep: Callable[[float], None] = time.sleep, confirm: Optional[Callable[[str], bool]] = None,
) -> int:
    env = dict(os.environ) if env is None else env
    out = out or sys.stdout
    err = err or sys.stderr
    try:
        args = build_parser().parse_args(list(argv))
    except SystemExit as exc:
        return int(exc.code or 0) if isinstance(exc.code, int) else 2
    if not args.cmd:
        err.write("usage: fleet up|reboot|report|logs|changes|hold|unhold|holds ...\n")
        return 2
    yml = env.get("FLEET_YML") or os.path.join(
        env.get("FLEET_DIR") or os.path.join(env.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share"), "fleet"),
        "fleet.yml")
    try:
        data = inv.load_inventory(yml)
    except inv.InventoryError as exc:
        err.write("fleet: %s\n" % exc)
        return 2
    hostname = (env.get("FLEET_HOSTNAME") or socket.gethostname()).split(".")[0].lower()
    masters = data.get("masters") or []
    master = env.get("FLEET_MASTER") or (hostname if hostname in masters else None)

    # Resolve the targets FIRST: an empty/unknown selector stops here, nothing is contacted.
    aliases: List[str] = []
    selector_text = ""
    if args.cmd in ("up", "reboot", "logs", "hold", "unhold"):
        given = _tokens(args)
        try:
            if given is None:
                if args.cmd != "up":
                    raise selector.SelectorError("a target is required")
                aliases = implicit_targets(data, master)
            else:
                aliases = selector.resolve(data, given)
                selector_text = " ".join(given)
        except selector.SelectorError as exc:
            err.write("fleet: %s\n" % exc)
            return selector.EXIT_EMPTY
    if args.cmd == "reboot" and not args.pending:
        err.write("fleet: reboot requires --pending (only hosts that need a restart, confirmed one by one)\n")
        return 2
    if args.cmd == "hold" and (not args.reason or not args.until):
        err.write("fleet: hold needs --reason and --until\n")
        return 2
    if args.cmd == "hold" and fstate.parse_iso(args.until) is None:
        err.write("fleet: unreadable --until date (use YYYY-MM-DD or ISO8601)\n")
        return 2
    if args.cmd == "reminder" and master is None:
        err.write("fleet: reminder runs on a master only\n")
        return 2

    transport = transport or SshTransport(data, env)
    if master is None:   # console: hand over to the master of the targets' site, fail over
        if getattr(args, "dry_run", False):
            probe = Orchestrator(data, None, "console", transport, None,  # type: ignore[arg-type]
                                 Options(critical=getattr(args, "critical", False)))
            out.write(probe.describe_reboot(aliases) if args.cmd == "reboot"
                      else probe.describe_plan(probe.plan(aliases)))
            return 0
        for candidate in choose_masters(data, aliases):
            rc = transport.run_on_master(candidate, list(argv))
            if rc is not None:
                return rc
            err.write("fleet: master %s unreachable, trying the next\n" % candidate)
        err.write("fleet: no master reachable\n")
        return 1

    st = fstate.State(fstate.default_root(env), master)
    return _run_command(args, data, st, master, aliases, selector_text, transport, notifier, env,
                        out, err, sleep, confirm)


def _sync_holds(transport: Any, data: Dict[str, Any], master: str, err: Any) -> int:
    """Push the hold files to the other master. A failure is loud: it would not honour the hold."""
    peers = [m for m in data.get("masters") or [] if m != master]
    try:
        ok = transport.sync(master, peers) if peers else True
    except Exception:  # noqa: BLE001
        ok = False
    if ok:
        return 0
    err.write("fleet: WARNING: hold state not synchronized to %s; recorded here only, that master "
              "will NOT honour it until a sync succeeds (re-run this command when it is reachable)\n"
              % ", ".join(peers))
    return 1


def _run_command(args, data, st, master, aliases, selector_text, transport, notifier, env,  # type: ignore[no-untyped-def]
                 out, err, sleep, confirm) -> int:
    if args.cmd == "holds":
        for host, hold in sorted(st.active_holds().items()):
            out.write("%-22s until %s  %s\n" % (host, hold.get("until"), schema.clean_text(hold.get("reason") or "")))
        return 0
    if args.cmd == "hold":
        for alias in aliases:
            st.add_hold(alias, schema.clean_text(args.reason, 200), args.until)
            out.write("held %s until %s\n" % (alias, args.until))
        return _sync_holds(transport, data, master, err)
    if args.cmd == "unhold":
        for alias in aliases:
            st.lift_hold(alias)
            out.write("unheld %s\n" % alias)
        return _sync_holds(transport, data, master, err)
    if args.cmd == "report":
        if args.run:
            try:
                rep = report.read_report(st, args.run)
            except ValueError:
                rep = None
            found = (args.run, rep) if rep else None
        else:
            found = report.latest_run(st) if args.last else None
        if not args.last and not args.run:
            out.write(report.list_runs_text(st))
            return 0
        if not found:
            err.write("fleet: no such run\n")
            return 1
        out.write(report.render_terminal(found[1], data))
        return 0
    if args.cmd == "logs":
        shown = False
        for alias in aliases:
            try:
                text = report.host_logs(st, alias, args.run)
            except ValueError:
                err.write("fleet: bad run id\n")
                return 2
            if text:
                out.write("== %s\n%s" % (alias, text))
                shown = True
        if not shown:
            err.write("fleet: no log found\n")
            return 1
        return 0
    if args.cmd == "changes":
        if args.host not in data["hosts"]:
            err.write("fleet: unknown host %s\n" % schema.clean_text(args.host, 60))
            return 2
        since = fstate.parse_iso(args.since) if args.since else None
        if args.since and since is None:
            err.write("fleet: unreadable --since date\n")
            return 2
        out.write(report.host_changes(st, args.host, since))
        return 0

    if args.cmd == "reminder":
        notifier = notifier or _make_notifier(data, st, env, err)
        if notifier is None:
            return 1
        notify.reminder_check(st, notifier)
        return 0
    opts = Options(critical=args.critical, no_canary=getattr(args, "no_canary", False),
                   dry_run=args.dry_run, confirm=confirm or tty_confirm,
                   say=lambda text: err.write(text + "\n"), sleep=sleep)
    if args.dry_run:      # plans only: no lock, no notifier, no 1Password, no connection
        preview = Orchestrator(data, st, master, transport, None, opts)
        out.write(preview.describe_reboot(aliases) if args.cmd == "reboot"
                  else preview.describe_plan(preview.plan(aliases)))
        return 0
    lock = st.try_lock()
    if lock is None:
        err.write("fleet: another run in progress\n")
        return 3
    try:
        notifier = notifier or _make_notifier(data, st, env, err)
        orch = Orchestrator(data, st, master, transport, notifier, opts)
        if args.cmd == "up":
            rep, rc = orch.run_up(aliases, selector_text)
        else:
            rep, rc = orch.run_reboot(aliases, selector_text)
    finally:
        fstate.State.unlock(lock)
    out.write(report.render_terminal(rep, data))
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
