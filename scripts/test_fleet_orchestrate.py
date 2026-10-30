#!/usr/bin/env python3
"""Orchestrator: phases, caps, canary, guardians, master order, failover, detached jobs.

No host, ntfy server, Tailscale daemon or 1Password is ever contacted: the
transport is a fake (or a fake `ssh` script in a tmp dir), the state lives in a
tmp dir. Concurrency tests are meant to be looped (see the sprint verification).
"""

import io
import json
import os
import re
import stat
import sys
import tempfile
import threading
import time
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / "dot_local/share/fleet/lib"
sys.path.insert(0, str(LIB))

import inventory as inv  # noqa: E402
import notify  # noqa: E402
import orchestrate  # noqa: E402
import state as fstate  # noqa: E402

SECRET_GREP = re.compile(r"BEGIN [A-Z ]*PRIVATE KEY|tk_[A-Za-z0-9]{20,}|eyJ[A-Za-z0-9_-]{20,}\.")
FAKE_TOKEN = "tk_" + "a1B2c3D4e5F6g7H8i9J0k1L2m3N4"
START = datetime(2026, 10, 30, 21, 0, 0, tzinfo=timezone.utc)


def host(alias, site="dijon", kind="chezmoi-linux", extra=""):
    crit = "true" if kind in ("opnsense", "proxmox") else "false"
    return (
        "  %s:\n    tailnet_name: %s\n    site: %s\n    kind: %s\n    critical: %s\n    ssh_user: j\n%s"
        % (alias, alias, site, kind, crit, extra)
    )


def fleet_text(extra_hosts=""):
    hosts = [
        host("diabolo"), host("penelope", "nice"),
        host("l1", extra="    canary: true\n"), host("l2"), host("l3", "nice"),
        host("m1", kind="chezmoi-macos"),
        host("omvn", "nice", "omv", "    tags: [site-router]\n"),
        host("ha1", kind="homeassistant", extra="    tags: [infra]\n"),
        host("g1", kind="guardian", extra="    tags: [infra]\n"),
        host("g2", "nice", "guardian", "    tags: [infra]\n"),
        host("gw", "nice", extra="    tags: [infra]\n"),
        host("fw", kind="opnsense"), host("px", kind="proxmox"),
    ]
    return (
        "masters: [diabolo, penelope]\n"
        'ntfy: {url: "https://ntfy.invalid", topic: fleet, token_ref: "op://V/I/f", gateway: gw}\n'
        "parallel: {total: 10, per_site: 4}\n"
        "master_priority: {nice: penelope}\n"
        "hosts:\n" + "".join(hosts) + extra_hosts +
        "groups:\n  guardians: [g1, g2]\n"
    )


def agent_line(alias, verb="update", status="updated", **over):
    obj = {
        "schema": 1, "host": alias, "verb": verb, "status": status, "reason": None,
        "packages": 2, "changes": [], "job": None, "reboot_required": False,
        "started": "2026-10-30T21:00:00Z", "ended": "2026-10-30T21:01:00Z", "log_tail": "",
    }
    obj.update(over)
    return json.dumps(obj)


class FakeClock:
    def __init__(self):
        self.t = START
        self.lock = threading.Lock()

    def now(self):
        with self.lock:
            return self.t

    def advance(self, seconds):
        with self.lock:
            self.t = self.t + timedelta(seconds=seconds)


class FakeTransport:
    """Scriptable transport. script[alias](verb, n) -> (rc, stdout, stderr)."""

    def __init__(self, data, online=None, delay=0.0):
        self.lock = threading.Lock()
        self.calls = []          # (alias, verb, local)
        self.connects = 0
        self.script = {}
        self.delay = delay
        self.active = {}
        self.active_site = {}
        self.max_total = 0
        self.max_site = {}
        self.sites = {a: h["site"] for a, h in data["hosts"].items()}
        self.tn = {a: h["tailnet_name"] for a, h in data["hosts"].items()}
        self.online = dict((a, True) for a in data["hosts"])
        self.online.update(online or {})
        self.counts = {}
        self.synced = []
        self.on_master = []
        self.master_up = {}
        self.sync_ok = True
        self.timeline = []   # (alias, verb, 'begin'|'end')

    def _touch(self):
        with self.lock:
            self.connects += 1

    def peers(self):
        self._touch()
        return dict((self.tn[a], {"online": up, "last_seen": "2026-10-20T08:00:00Z" if not up else None,
                                  "os": "linux", "tags": []}) for a, up in self.online.items())

    def probe(self, alias):
        self._touch()
        return self.online.get(alias, False)

    def list_vms(self, alias):
        return ["vm100 web", "vm101 db"]

    def _default(self, alias, verb, n):
        if verb == "update":
            return 0, agent_line(alias, "update", "started", job="job-%s" % alias), ""
        if verb == "report":
            return 0, agent_line(alias, "report", "updated"), ""
        if verb == "reboot-status":
            return 0, agent_line(alias, "reboot-status", "up-to-date", reboot_required=True), ""
        return 0, agent_line(alias, verb, "updated"), ""

    def call(self, alias, verb, timeout=60, local=False):
        self._touch()
        with self.lock:
            self.calls.append((alias, verb, local))
            n = self.counts[(alias, verb)] = self.counts.get((alias, verb), 0) + 1
            self.timeline.append((alias, verb, "begin"))
            if verb == "update":
                self.active_site[self.sites[alias]] = self.active_site.get(self.sites[alias], 0) + 1
                self.active[alias] = 1
                self.max_total = max(self.max_total, sum(self.active.values()))
                s = self.sites[alias]
                self.max_site[s] = max(self.max_site.get(s, 0), self.active_site[s])
        if self.delay:
            time.sleep(self.delay)
        fn = self.script.get(alias)
        res = fn(verb, n) if fn else self._default(alias, verb, n)
        with self.lock:
            self.timeline.append((alias, verb, "end"))
        try:
            status = json.loads(res[1])["status"]
        except (ValueError, KeyError, TypeError):
            status = None
        if verb == "update" and status != "started":
            self._leave(alias)
        elif verb == "report" and status is not None and status not in ("started", "running"):
            self._leave(alias)
        return res

    def _leave(self, alias):
        with self.lock:
            if self.active.get(alias):
                self.active[alias] = 0
                self.active_site[self.sites[alias]] -= 1

    def local_call(self, alias, verb, timeout=60):
        return self.call(alias, verb, timeout, local=True)

    def sync(self, master, peers):
        self.synced.append((master, list(peers)))
        return self.sync_ok

    def run_on_master(self, master, argv):
        self.on_master.append((master, list(argv)))
        return None if not self.master_up.get(master, True) else 0


class Env(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name)
        self.yml = self.tmp / "fleet.yml"
        self.yml.write_text(fleet_text())
        self.data = inv.load_inventory(str(self.yml))
        self.root = self.tmp / "state"
        self.clock = FakeClock()
        self.st = fstate.State(self.root, "diabolo", now=self.clock.now)
        self.sent = []
        self.ntfy_up = True

        def sender(url, topic, headers, body):
            if not self.ntfy_up:
                raise OSError("down")
            self.sent.append((headers["Title"], int(headers["Priority"]), headers["Tags"], body))

        self.notifier = notify.Notifier("https://ntfy.invalid", "fleet", FAKE_TOKEN,
                                        self.root / "ntfy-queue", sender=sender, clock=self.clock.now)
        self.tr = FakeTransport(self.data)

    def orch(self, tr=None, **opts):
        opts.setdefault("sleep", self.clock.advance)
        opts.setdefault("poll_interval", 1.0)
        return orchestrate.Orchestrator(
            self.data, self.st, "diabolo", tr or self.tr, self.notifier,
            orchestrate.Options(**opts), now=self.clock.now)

    def run_up(self, aliases, **opts):
        rep, rc = self.orch(**opts).run_up(aliases, "test")
        return dict((e["host"], e) for e in rep["hosts"]), rc, rep

    def order(self, verb="update"):
        return [a for a, v, _ in self.tr.calls if v == verb]


class PlanTest(Env):
    def test_phases_derived_from_fleet_yml(self):
        plan = self.orch().plan(list(self.data["hosts"]))
        self.assertEqual(plan.phases[0], ["penelope", "l1", "l2", "l3", "m1"])
        self.assertEqual(plan.phases[1], ["omvn", "ha1", "g1", "g2"])
        self.assertEqual(plan.phases[2], ["gw"])
        self.assertEqual(plan.critical, ["fw", "px"])
        self.assertEqual(plan.last, "diabolo")
        self.assertNotIn("diabolo", sum(plan.phases, []))

    def test_phase_follows_edited_inventory_not_hardcoded(self):
        self.data["hosts"]["l2"]["tags"] = ["infra"]
        plan = self.orch().plan(["l1", "l2"])
        self.assertEqual(plan.phases[0], ["l1"])
        self.assertIn("l2", plan.phases[1])

    def test_phase_order_respected(self):
        by, rc, _ = self.run_up(list(self.data["hosts"]), critical=True, confirm=lambda p: True)
        order = self.order()
        idx = dict((a, order.index(a)) for a in order)
        p1 = ["penelope", "l1", "l2", "l3", "m1"]
        p2 = ["omvn", "ha1", "g1", "g2"]
        self.assertLess(max(idx[a] for a in p1), min(idx[a] for a in p2))
        self.assertLess(max(idx[a] for a in p2), idx["gw"])
        self.assertLess(idx["gw"], idx["fw"])
        self.assertLess(idx["fw"], idx["px"])          # OPNsense then multibox
        self.assertEqual(order[-1], "diabolo")         # current master last
        self.assertEqual([a for a in order if a in p2], p2)  # phase 2 is serial, in order

    def test_current_master_local_last_and_never_rebooted(self):
        self.run_up(["diabolo", "l2"])
        self.assertEqual(self.tr.calls[-1][0], "diabolo")
        self.assertTrue(all(local for a, v, local in self.tr.calls if a == "diabolo"))
        self.assertFalse(any(local for a, v, local in self.tr.calls if a != "diabolo"))
        self.assertNotIn("reboot", [v for a, v, _ in self.tr.calls])

    def test_other_master_excluded_from_implicit_whole_fleet(self):
        names = orchestrate.implicit_targets(self.data, "diabolo")
        self.assertNotIn("penelope", names)
        self.assertIn("diabolo", names)


class CanaryTest(Env):
    def test_canary_runs_first_in_phase_one(self):
        self.run_up(["l1", "l2", "l3"])
        order = self.order()
        self.assertEqual(order[0], "l1")

    def test_failed_canary_skips_others_of_the_kind(self):
        self.tr.script["l1"] = lambda v, n: (0, agent_line("l1", v, "failed", reason="boom"), "") \
            if v != "update" else (0, agent_line("l1", v, "failed", reason="boom"), "")
        by, rc, _ = self.run_up(["l1", "l2", "l3", "m1"])
        self.assertEqual(by["l1"]["status"], "failed")
        for a in ("l2", "l3"):
            self.assertEqual(by[a]["status"], "skipped")
            self.assertIn("canary failed", by[a]["reason"])
        self.assertEqual(by["m1"]["status"], "updated")        # other kind unaffected
        self.assertNotIn("l2", [a for a, _, _ in self.tr.calls])
        self.assertEqual(rc, 1)

    def test_degraded_canary_also_blocks(self):
        self.tr.script["l1"] = lambda v, n: (0, agent_line("l1", v, "degraded"), "")
        by, _, _ = self.run_up(["l1", "l2"])
        self.assertEqual(by["l2"]["status"], "skipped")

    def test_no_canary_flag_forces(self):
        self.tr.script["l1"] = lambda v, n: (0, agent_line("l1", v, "failed"), "")
        by, _, _ = self.run_up(["l1", "l2"], no_canary=True)
        self.assertEqual(by["l2"]["status"], "updated")


class GuardianTest(Env):
    def test_guardian_skipped_when_no_other_host_of_site_online(self):
        for a in ("diabolo", "l1", "l2", "m1", "ha1", "fw", "px"):  # all other dijon hosts down
            self.tr.online[a] = False
        by, _, _ = self.run_up(["g1"])
        self.assertEqual(by["g1"]["status"], "skipped")
        self.assertIn("site", by["g1"]["reason"])
        self.assertNotIn(("g1", "update", False), self.tr.calls)

    def test_guardian_updated_when_site_healthy(self):
        by, _, _ = self.run_up(["g1"])
        self.assertEqual(by["g1"]["status"], "updated")

    def test_other_guardian_does_not_count_as_healthy_site(self):
        self.data["hosts"]["g3"] = dict(self.data["hosts"]["g1"], tailnet_name="g3")
        self.tr = FakeTransport(self.data)
        for a, h in self.data["hosts"].items():
            if h["site"] == "dijon" and h["kind"] != "guardian":
                self.tr.online[a] = False
        by, _, _ = self.run_up(["g1", "g3"])
        self.assertEqual(by["g1"]["status"], "skipped")
        self.assertEqual(by["g3"]["status"], "skipped")


class StatusTest(Env):
    def test_offline_carries_last_seen_and_run_continues(self):
        self.tr.online["l2"] = False
        by, rc, _ = self.run_up(["l1", "l2", "l3"])
        self.assertEqual(by["l2"]["status"], "offline")
        self.assertEqual(by["l2"]["last_seen"], "2026-10-20T08:00:00Z")
        self.assertEqual(by["l3"]["status"], "updated")
        self.assertNotIn("l2", [a for a, _, _ in self.tr.calls])   # no connection tried
        self.assertEqual(rc, 0)

    def test_unreachable_when_online_but_ssh_fails(self):
        self.tr.script["l2"] = lambda v, n: (255, "", "ssh: connect to host l2: Connection timed out")
        by, rc, _ = self.run_up(["l2"])
        self.assertEqual(by["l2"]["status"], "unreachable")
        self.assertEqual(rc, 1)

    def test_agent_refusal_is_failed_and_notifies_priority_5(self):
        self.tr.script["l2"] = lambda v, n: (1, "", "fleet-agent: refused (verb)")
        by, _, _ = self.run_up(["l2"])
        self.assertEqual(by["l2"]["status"], "failed")
        self.assertIn((5, "refused"), [(p, t) for _, p, t, _ in self.sent])

    def test_held_host_is_not_contacted_and_visible(self):
        self.st.add_hold("l2", "maintenance", "2026-12-01")
        by, _, rep = self.run_up(["l1", "l2"])
        self.assertEqual(by["l2"]["status"], "held")
        self.assertIn("maintenance", by["l2"]["reason"])
        self.assertNotIn("l2", [a for a, _, _ in self.tr.calls])
        self.assertIn("held", (self.st.run_dir(rep["run_id"]) / "report.md").read_text())

    def test_expired_hold_is_ignored(self):
        self.st.add_hold("l2", "old", "2026-10-01")
        by, _, _ = self.run_up(["l2"])
        self.assertEqual(by["l2"]["status"], "updated")

    def test_invalid_agent_output_is_failed(self):
        for bad in ("garbage", "{}", json.dumps({"schema": 1, "status": "offline"}), "x" * 70000):
            self.tr.script["l2"] = lambda v, n, b=bad: (0, b, "")
            by, _, _ = self.run_up(["l2"])
            self.assertEqual(by["l2"]["status"], "failed", msg=bad[:30])

    def test_host_without_agent_is_unsupported(self):
        del self.data["hosts"]["l2"]["ssh_user"]
        by, rc, _ = self.run_up(["l2"])
        self.assertEqual(by["l2"]["status"], "unsupported")
        self.assertEqual(self.tr.calls, [])
        self.assertEqual(rc, 0)

    def test_busy_agent(self):
        self.tr.script["l2"] = lambda v, n: (3, agent_line("l2", v, "busy"), "")
        by, _, _ = self.run_up(["l2"])
        self.assertEqual(by["l2"]["status"], "busy")


class DetachedJobTest(Env):
    def test_started_then_report_polled_until_final(self):
        seq = []

        def script(v, n):
            seq.append(v)
            if v == "update":
                return 0, agent_line("l2", v, "started", job="j1"), ""
            return (0, agent_line("l2", v, "running", job="j1"), "") if n < 3 else \
                (0, agent_line("l2", v, "updated", job="j1", packages=7), "")

        self.tr.script["l2"] = script
        by, _, _ = self.run_up(["l2"])
        self.assertEqual(seq, ["update", "report", "report", "report"])
        self.assertEqual((by["l2"]["status"], by["l2"]["packages"]), ("updated", 7))

    def test_timeout_when_job_never_finishes(self):
        self.data["hosts"]["l2"]["timeout_min"] = 5
        self.tr.script["l2"] = lambda v, n: (0, agent_line("l2", v, "started" if v == "update" else "running"), "")
        orch = self.orch(poll_interval=60.0)
        rep, rc = orch.run_up(["l2"], "t")
        self.assertEqual(rep["hosts"][0]["status"], "timeout")
        self.assertEqual(rc, 1)
        self.assertLess(self.tr.counts[("l2", "report")], 20)

    def test_ssh_cut_during_job_is_tolerated(self):
        def script(v, n):
            if v == "update":
                return 0, agent_line("l2", v, "started", job="j1"), ""
            if n <= 2:
                return 255, "", "Connection closed"      # tailscale restarting
            return 0, agent_line("l2", v, "updated", job="j1"), ""

        self.tr.script["l2"] = script
        by, _, _ = self.run_up(["l2"])
        self.assertEqual(by["l2"]["status"], "updated")

    def test_default_timeouts_per_kind(self):
        self.assertEqual(inv.timeout_for(self.data, "l2"), 30)
        self.assertEqual(inv.timeout_for(self.data, "ha1"), 45)


class CriticalTest(Env):
    def test_critical_hosts_need_the_flag(self):
        by, _, _ = self.run_up(["fw", "px"])
        self.assertEqual(by["fw"]["status"], "skipped")
        self.assertIn("--critical", by["fw"]["reason"])
        self.assertEqual(self.tr.calls, [])

    def test_critical_confirmation_and_vm_warning(self):
        said = []
        asked = []
        orch = self.orch(critical=True, confirm=lambda p: asked.append(p) or False, say=said.append)
        rep, _ = orch.run_up(["px"], "t")
        self.assertEqual(rep["hosts"][0]["status"], "skipped")
        self.assertIn("not confirmed", rep["hosts"][0]["reason"])
        self.assertTrue(any("vm100" in s and "vm101" in s for s in said))   # VMs listed BEFORE asking
        self.assertEqual(len(asked), 1)
        self.assertEqual(self.tr.calls, [])

    def test_critical_confirmed_runs_in_order(self):
        by, _, _ = self.run_up(["px", "fw"], critical=True, confirm=lambda p: True)
        self.assertEqual(by["fw"]["status"], "updated")
        self.assertLess(self.order().index("fw"), self.order().index("px"))


class ConcurrencyTest(Env):
    def many(self, per_site_hosts):
        extra = "".join(host("c%02d" % i, site) for i, site in per_site_hosts)
        self.yml.write_text(fleet_text(extra))
        self.data = inv.load_inventory(str(self.yml))
        self.tr = FakeTransport(self.data, delay=0.05)   # >= 50 ms: overlap does not depend on scheduling luck

    LAYOUT = [(i, "dijon" if i < 16 else "nice" if i < 24 else "garage") for i in range(30)]

    def test_caps_total_10_and_site_4(self):
        self.many(self.LAYOUT)
        names = ["c%02d" % i for i in range(30)]
        by, rc, _ = self.run_up(names)
        self.assertTrue(all(by[n]["status"] == "updated" for n in names))
        self.assertLessEqual(self.tr.max_total, 10)
        for site, peak in self.tr.max_site.items():
            self.assertLessEqual(peak, 4, site)
        self.assertGreater(self.tr.max_total, 1)       # it really ran in parallel
        self.assertEqual(self.tr.max_site["dijon"], 4)  # and the per-site cap was actually reached

    def test_caps_negative_control_the_measurement_sees_raised_caps(self):
        self.many(self.LAYOUT)
        self.data["parallel"] = {"total": 30, "per_site": 30}
        names = ["c%02d" % i for i in range(30)]
        self.run_up(names)
        self.assertGreater(self.tr.max_total, 10)       # the same test would fail with raised caps
        self.assertGreater(self.tr.max_site["dijon"], 4)

    def test_detached_jobs_tracked_independently_in_parallel(self):
        self.many([(i, "dijon" if i % 2 else "nice") for i in range(12)])
        names = ["c%02d" % i for i in range(12)]
        for n in names:
            self.tr.script[n] = (lambda nn: lambda v, k: (0, agent_line(nn, v, "started", job="job-" + nn), "")
                                 if v == "update" else (0, agent_line(nn, v, "running" if k < 3 else "updated",
                                                                      job="job-" + nn, packages=len(nn)), ""))(n)
        by, _, _ = self.run_up(names)
        self.assertEqual([by[n]["status"] for n in names], ["updated"] * 12)
        for n in names:
            self.assertEqual(self.tr.counts[(n, "report")], 3)

    def test_ntfy_queue_survives_parallel_sends(self):
        self.ntfy_up = False
        threads = [threading.Thread(target=lambda i=i: self.notifier.send(
            notify.message("t%d" % i, 2, ["ok"], "b"))) for i in range(40)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(len(self.notifier.pending()), 40)
        self.ntfy_up = True
        self.assertEqual(self.notifier.flush(), 40)
        self.assertEqual(len(self.sent), 40)


class OutcomeTest(Env):
    def test_ntfy_down_during_run_is_resent_afterwards(self):
        self.ntfy_up = False
        self.tr.script["l2"] = lambda v, n: (0, agent_line("l2", v, "failed"), "")
        self.run_up(["l2", "l3"])
        self.assertEqual(self.sent, [])
        self.assertGreaterEqual(len(self.notifier.pending()), 1)
        self.ntfy_up = True
        self.notifier.flush()
        self.assertTrue(any(p == 4 for _, p, _, _ in self.sent))
        self.assertEqual(self.notifier.pending(), [])

    def test_summary_priorities(self):
        self.run_up(["l2"])
        self.assertEqual([p for _, p, _, _ in self.sent], [2])

    def test_stale_alert_survives_the_real_31_day_purge(self):
        old = START - timedelta(days=40)
        old_id = old.strftime("%Y%m%dT%H%MZ") + "-diabolo"
        self.st.append_history(old_id, {"host": "l3", "status": "updated", "started": fstate.iso(old),
                                        "ended": fstate.iso(old)})
        self.st.set_last_success("l3", fstate.iso(old))
        self.assertEqual(len(self.st.history()), 1)
        self.st.purge(START)                                 # the REAL purge, 31 days
        self.assertEqual(self.st.history(), [])             # the history is really gone...
        self.assertEqual(self.st.last_success()["l3"], fstate.iso(old))   # ...last-success is not
        self.run_up(["l2"])
        stale = [s for s in self.sent if "without update" in s[0]]
        self.assertEqual(len(stale), 1)
        self.assertEqual(stale[0][1], 4)
        self.assertIn("l3", stale[0][3])
        self.assertNotIn("l2", stale[0][3])

    def test_no_stale_alert_for_a_recently_updated_host(self):       # negative control
        self.st.set_last_success("l3", fstate.iso(START - timedelta(days=2)))
        self.run_up(["l2"])
        self.assertEqual([s for s in self.sent if "without update" in s[0]], [])

    def test_history_and_last_success_written_and_secrets_masked(self):
        self.tr.script["l2"] = lambda v, n: (0, agent_line("l2", v, "updated", log_tail="k " + FAKE_TOKEN), "")
        _, _, rep = self.run_up(["l2"])
        self.assertEqual([h["host"] for h in self.st.history()], ["l2"])
        self.assertIn("l2", self.st.last_success())
        for p in self.root.rglob("*"):
            if p.is_file():
                self.assertNotRegex(p.read_text(), SECRET_GREP, str(p))
        self.assertEqual(stat.S_IMODE((self.st.run_dir(rep["run_id"]) / "report.json").stat().st_mode), 0o600)

    def test_state_synced_to_peer_master_at_end(self):
        self.run_up(["l2"])
        self.assertEqual(self.tr.synced, [("diabolo", ["penelope"])])


class RebootTest(Env):
    def test_confirmation_per_machine_and_return_check(self):
        state = {"n": 0}

        def script(v, n):
            if v == "reboot-status":
                state["n"] += 1
                if state["n"] == 1:
                    return 0, agent_line("l2", v, "up-to-date", reboot_required=True), ""
                if state["n"] <= 3:
                    return 255, "", "refused connection"
                return 0, agent_line("l2", v, "up-to-date", reboot_required=False), ""
            return 0, agent_line("l2", v, "updated"), ""

        self.tr.script["l2"] = script
        self.tr.script["l3"] = lambda v, n: (0, agent_line("l3", v, "up-to-date", reboot_required=False), "")
        asked = []
        rep, rc = self.orch(confirm=lambda p: asked.append(p) or True).run_reboot(["l2", "l3"], "t")
        by = dict((e["host"], e) for e in rep["hosts"])
        self.assertEqual(len(asked), 1)                       # asked for l2 only: l3 needs no reboot
        self.assertIn("l2", asked[0])
        self.assertEqual(by["l2"]["status"], "updated")
        self.assertEqual(by["l2"]["reason"], "rebooted")
        self.assertEqual(by["l3"]["status"], "skipped")
        self.assertNotIn(("l3", "reboot", False), self.tr.calls)

    def test_declined_reboot_not_sent(self):
        by = dict((e["host"], e) for e in self.orch(confirm=lambda p: False).run_reboot(["l2"], "t")[0]["hosts"])
        self.assertEqual(by["l2"]["status"], "skipped")
        self.assertNotIn("reboot", [v for _, v, _ in self.tr.calls])

    def test_not_back_notifies_priority_5(self):
        def script(v, n):
            if v == "reboot-status" and n == 1:
                return 0, agent_line("l2", v, "up-to-date", reboot_required=True), ""
            if v == "reboot-status":
                return 255, "", "no route"
            return 0, agent_line("l2", v, "updated"), ""

        self.tr.script["l2"] = script
        rep, rc = self.orch(confirm=lambda p: True, reboot_wait_min=2).run_reboot(["l2"], "t")
        self.assertEqual(rep["hosts"][0]["status"], "timeout")
        self.assertEqual(rc, 1)
        self.assertIn((5, "reboot"), [(p, t) for _, p, t, _ in self.sent])

    def test_current_master_is_never_rebooted(self):
        rep, _ = self.orch(confirm=lambda p: True).run_reboot(["diabolo"], "t")
        self.assertEqual(rep["hosts"][0]["status"], "skipped")
        self.assertEqual(self.tr.calls, [])

    def test_critical_reboot_needs_flag(self):
        rep, _ = self.orch(confirm=lambda p: True).run_reboot(["fw"], "t")
        self.assertEqual(rep["hosts"][0]["status"], "skipped")
        self.assertEqual(self.tr.calls, [])


class CliTest(Env):
    def env(self, **extra):
        e = {"FLEET_YML": str(self.yml), "FLEET_STATE_DIR": str(self.root), "FLEET_MASTER": "diabolo"}
        e.update(extra)
        return e

    def main(self, argv, **kw):
        out, err = io.StringIO(), io.StringIO()
        env = kw.pop("env", self.env())
        rc = orchestrate.main(argv, env=env, transport=kw.pop("transport", self.tr),
                              notifier=self.notifier, out=out, err=err, sleep=self.clock.advance, **kw)
        return rc, out.getvalue(), err.getvalue()

    def test_empty_selector_exit_2_and_no_connection(self):
        for argv in (["up", "-l", "site=inexistant"], ["up", "-l", ""], ["up", "-l", "!l2"],
                     ["up", "ghost"], ["reboot", "--pending", "-l", "kind=windows"]):
            rc, out, err = self.main(argv)
            self.assertEqual(rc, 2, msg=str(argv))
            self.assertEqual(self.tr.connects, 0, msg=str(argv))
            self.assertEqual(self.tr.calls, [])
        self.assertEqual(self.sent, [])

    def test_dry_run_lists_targets_without_connecting(self):
        rc, out, _ = self.main(["up", "--dry-run", "-l", "site=nice"])
        self.assertEqual(rc, 0)
        self.assertEqual(self.tr.connects, 0)
        for a in ("penelope", "l3", "omvn", "g2", "gw"):
            self.assertIn(a, out)
        self.assertNotIn("l2", out)

    def test_up_with_selector_prints_report_and_exit_code(self):
        rc, out, _ = self.main(["up", "-l", "l2,l3"])
        self.assertEqual(rc, 0)
        self.assertIn("l2", out)
        self.assertIn("✅", out)

    def test_up_without_selector_targets_whole_fleet_but_not_critical(self):
        rc, out, _ = self.main(["up"])
        by = dict(line.split()[:2] for line in out.splitlines() if line.startswith(("fw ", "px ", "l1 ")))
        self.assertEqual(by["fw"], "skipped")
        self.assertEqual(by["l1"], "updated")

    def test_report_logs_changes_holds_commands(self):
        self.main(["up", "-l", "l2"])
        rc, out, _ = self.main(["report", "--last"])
        self.assertEqual(rc, 0)
        self.assertIn("l2", out)
        rc, out, _ = self.main(["logs", "l2"])
        self.assertEqual(rc, 0)
        rc, out, _ = self.main(["hold", "l3", "--reason", "demo", "--until", "2026-12-31"])
        self.assertEqual(rc, 0)
        rc, out, _ = self.main(["holds"])
        self.assertIn("l3", out)
        self.assertIn("demo", out)
        rc, out, _ = self.main(["up", "-l", "l3"])
        self.assertIn("held", out)
        self.main(["unhold", "l3"])
        rc, out, _ = self.main(["holds"])
        self.assertNotIn("l3", out)

    def test_hold_requires_reason_and_valid_until(self):
        self.assertEqual(self.main(["hold", "l3"])[0], 2)
        self.assertEqual(self.main(["hold", "l3", "--reason", "x", "--until", "tomorrow-ish"])[0], 2)
        self.assertEqual(self.main(["hold", "ghost", "--reason", "x", "--until", "2026-12-31"])[0], 2)

    def test_reboot_requires_pending(self):
        self.assertEqual(self.main(["reboot", "-l", "l2"])[0], 2)

    def test_reminder_makes_no_connection(self):
        rc, _, _ = self.main(["reminder"])
        self.assertEqual(rc, 0)
        self.assertEqual(self.tr.connects, 0)
        self.assertIn(3, [p for _, p, _, _ in self.sent])

    def test_console_delegates_to_site_master_with_failover(self):
        env = self.env(FLEET_HOSTNAME="laptop")
        env.pop("FLEET_MASTER")
        self.tr.master_up = {"penelope": False}
        rc, _, _ = self.main(["up", "-l", "l3"], env=env)       # l3 is in nice -> penelope first
        self.assertEqual([m for m, _ in self.tr.on_master], ["penelope", "diabolo"])
        self.assertEqual(rc, 0)
        self.assertEqual(self.tr.on_master[0][1][:2], ["up", "-l"])
        self.assertEqual(self.tr.calls, [])                    # the console itself never contacts a host

    def test_console_dijon_and_off_site_prefer_diabolo(self):
        self.assertEqual(orchestrate.choose_masters(self.data, ["l2"]), ["diabolo", "penelope"])
        self.assertEqual(orchestrate.choose_masters(self.data, ["l3"]), ["penelope", "diabolo"])
        self.assertEqual(orchestrate.choose_masters(self.data, ["m1", "l3"]), ["diabolo", "penelope"])

    def test_console_all_masters_down(self):
        env = self.env(FLEET_HOSTNAME="laptop")
        env.pop("FLEET_MASTER")
        self.tr.master_up = {"penelope": False, "diabolo": False}
        rc, _, err = self.main(["up", "-l", "l2"], env=env)
        self.assertEqual(rc, 1)
        self.assertIn("master", err)


class SshTransportTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name)

    def fake_ssh(self, body):
        path = self.tmp / "ssh"
        path.write_text("#!/usr/bin/env bash\n" + body + "\n")
        path.chmod(0o700)
        return str(path)

    def transport(self, ssh):
        data = inv.parse_yaml_subset(fleet_text())
        return orchestrate.SshTransport(data, {"FLEET_SSH": ssh, "FLEET_LOCAL_AGENT": str(self.tmp / "agent")})

    def test_stdout_flood_is_byte_capped_and_the_process_killed(self):
        marker = self.tmp / "survived"
        body = ('(head -c 400000 /dev/zero | tr "\\0" E >&2) & head -c 400000 /dev/zero | tr "\\0" O; '
                'wait; sleep 1; touch %s' % marker)
        t = self.transport(self.fake_ssh(body))
        started = time.time()
        rc, out, err = t.call("l2", "check", timeout=8)
        self.assertLessEqual(len(out), orchestrate.OUT_CAP)
        self.assertLessEqual(len(err), orchestrate.ERR_CAP + 64)
        self.assertLess(time.time() - started, 7)
        time.sleep(1.5)
        self.assertFalse(marker.exists())      # killed with its process group, did not run to the end
        self.assertNotEqual(rc, 0)

    def test_stderr_over_cap_does_not_kill_the_call(self):
        t = self.transport(self.fake_ssh(
            'head -c 300000 /dev/zero | tr "\\0" E >&2; echo \'{"ok":1}\'; exit 0'))
        rc, out, err = t.call("l2", "check", timeout=10)
        self.assertEqual(rc, 0)
        self.assertEqual(out.strip(), '{"ok":1}')
        self.assertLessEqual(len(err), orchestrate.ERR_CAP + 64)
        self.assertTrue(err.startswith("E" * 100))
        self.assertIn("truncated", err)

    def test_timeout_kills_a_silent_process(self):
        t = self.transport(self.fake_ssh("sleep 30"))
        started = time.time()
        rc, out, err = t.call("l2", "check", timeout=1)
        self.assertLess(time.time() - started, 10)
        self.assertNotEqual(rc, 0)

    def test_argument_after_double_dash_and_leading_dash_refused(self):
        log = self.tmp / "argv2"
        t = self.transport(self.fake_ssh('printf "%%s\\n" "$@" > %s; echo ok' % log))
        t.call("l2", "check")
        argv = [a for a in log.read_text().split("\n") if a]
        self.assertEqual(argv[-3:], ["--", "j@l2", "check"])
        t.data["hosts"]["l2"]["tailnet_name"] = "-oProxyCommand=evil"
        with self.assertRaises(ValueError):
            t.call("l2", "check")
        with self.assertRaises(ValueError):
            t.probe("l2")
        t.data["hosts"]["l2"].update({"tailnet_name": "l2", "ssh_user": "-oProxyCommand=evil"})
        with self.assertRaises(ValueError):
            t.call("l2", "check")

    def test_only_whitelisted_verbs_reach_ssh(self):
        t = self.transport(self.fake_ssh("exit 0"))
        for bad in ("ping", "update; id", "$(id)", "update extra", ""):
            with self.assertRaises(ValueError):
                t.call("l2", bad)

    def test_verb_is_passed_as_a_single_argument_never_through_a_shell(self):
        log = self.tmp / "argv"
        t = self.transport(self.fake_ssh('printf "%%s\\n" "$@" > %s; echo ok' % log))
        t.call("l2", "check")
        argv = log.read_text().split("\n")
        argv = [a for a in argv if a]
        self.assertEqual(argv[-2:], ["j@l2", "check"])

    def test_local_call_sets_ssh_original_command_for_the_agent(self):
        agent = self.tmp / "agent"
        agent.write_text('#!/usr/bin/env bash\necho "{\\"v\\":\\"$SSH_ORIGINAL_COMMAND\\"}"\n')
        agent.chmod(0o700)
        t = self.transport("unused")
        rc, out, _ = t.local_call("diabolo", "check")
        self.assertEqual(json.loads(out), {"v": "check"})

    def test_probe_accepts_permission_denied_only(self):
        t = self.transport(self.fake_ssh('echo "j@l2: Permission denied (publickey)." >&2; exit 255'))
        self.assertTrue(t.probe("l2"))
        t = self.transport(self.fake_ssh('echo "ssh: connect timed out" >&2; exit 255'))
        self.assertFalse(t.probe("l2"))


class WrapperTest(unittest.TestCase):
    """The bash wrapper dispatches to the orchestrator; ssh and tailscale are stubbed to fail loudly."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name)
        self.tripwire = self.tmp / "tripwire"
        stub = self.tmp / "ssh"
        stub.write_text('#!/usr/bin/env bash\necho called >> %s\nexit 255\n' % self.tripwire)
        stub.chmod(0o700)
        self.stub = str(stub)

    def run_fleet(self, *args):
        import subprocess
        env = dict(os.environ, FLEET_DIR=str(ROOT / "dot_local/share/fleet"), FLEET_SSH=self.stub,
                   FLEET_STATE_DIR=str(self.tmp / "state"), FLEET_MASTER="diabolo", FLEET_SYNC="0")
        env.pop("FLEET_YML", None)
        return subprocess.run(["bash", str(ROOT / "dot_local/bin/executable_fleet")] + list(args),
                              capture_output=True, text=True, env=env, timeout=60)

    def test_empty_selector_exits_2_without_any_connection(self):
        proc = self.run_fleet("up", "-l", "site=inexistant")
        self.assertEqual(proc.returncode, 2, proc.stderr)
        self.assertFalse(self.tripwire.exists())

    def test_dry_run_on_real_inventory_lists_phases_without_connection(self):
        proc = self.run_fleet("up", "--dry-run", "-l", "site=garage")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("omv-garage", proc.stdout)
        self.assertIn("ha-garage", proc.stdout)
        self.assertFalse(self.tripwire.exists())

    def test_real_inventory_phases(self):
        proc = self.run_fleet("up", "--dry-run")
        self.assertIn("phase 3 (alone): bbh-network", proc.stdout)
        self.assertIn("critical (needs --critical + confirmation): opnsense-amd64, multibox", proc.stdout)
        self.assertNotIn("penelope", proc.stdout)      # the other master is not part of an implicit run
        self.assertFalse(self.tripwire.exists())

    def test_unknown_command_and_help(self):
        self.assertEqual(self.run_fleet("bogus").returncode, 2)
        self.assertIn("up ", self.run_fleet("help").stdout)


class SyncTest(unittest.TestCase):
    def test_rsync_pushes_only_own_files_to_the_peer(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            log = tmp / "argv"
            rs = tmp / "rsync"
            rs.write_text('#!/usr/bin/env bash\nprintf "%%s\\n" "$@" > %s\n' % log)
            rs.chmod(0o700)
            data = inv.parse_yaml_subset(fleet_text())
            t = orchestrate.SshTransport(data, {"FLEET_RSYNC": str(rs), "FLEET_STATE_DIR": str(tmp / "s")})
            self.assertTrue(t.sync("diabolo", ["penelope"]))
            argv = log.read_text().split("\n")
            self.assertIn("--include=history-diabolo.jsonl", argv)
            self.assertIn("--exclude=*", argv)
            self.assertNotIn("--include=history-penelope.jsonl", argv)
            self.assertIn("j@penelope:.local/state/fleet/", argv)


class ReviewCliTest(Env):
    def env(self, **extra):
        e = {"FLEET_YML": str(self.yml), "FLEET_STATE_DIR": str(self.root), "FLEET_MASTER": "diabolo"}
        e.update(extra)
        return e

    def main(self, argv, **kw):
        out, err = io.StringIO(), io.StringIO()
        env = kw.pop("env", self.env())
        rc = orchestrate.main(argv, env=env, transport=kw.pop("transport", self.tr),
                              notifier=kw.pop("notifier", self.notifier), out=out, err=err,
                              sleep=self.clock.advance, **kw)
        return rc, out.getvalue(), err.getvalue()

    # -- hold / unhold: a failed sync is loud
    def test_hold_with_failed_sync_warns_on_stderr_exits_1_but_records_the_hold(self):
        self.tr.sync_ok = False
        rc, out, err = self.main(["hold", "l3", "--reason", "demo", "--until", "2026-12-31"])
        self.assertEqual(rc, 1)
        self.assertIn("WARNING", err)
        self.assertIn("not synchronized", err)
        self.assertIn("l3", self.st.active_holds(START))      # recorded locally anyway

    def test_unhold_with_failed_sync_warns_and_exits_1(self):
        self.main(["hold", "l3", "--reason", "demo", "--until", "2026-12-31"])
        self.tr.sync_ok = False
        rc, _, err = self.main(["unhold", "l3"])
        self.assertEqual(rc, 1)
        self.assertIn("WARNING", err)
        self.assertNotIn("l3", self.st.active_holds(START))

    def test_hold_with_working_sync_exits_0(self):
        rc, _, err = self.main(["hold", "l3", "--reason", "demo", "--until", "2026-12-31"])
        self.assertEqual((rc, err), (0, ""))

    # -- run lock
    def test_second_run_is_refused_with_exit_3_and_contacts_nothing(self):
        fd = self.st.try_lock()
        self.addCleanup(lambda: fstate.State.unlock(fd) if fd is not None else None)
        for argv in (["up", "-l", "l2"], ["reboot", "--pending", "-l", "l2"]):
            rc, out, err = self.main(argv)
            self.assertEqual(rc, 3, msg=str(argv))
            self.assertIn("fleet: another run in progress", err)
        self.assertEqual(self.tr.connects, 0)
        self.assertEqual(self.sent, [])

    def test_lock_is_released_after_the_run_and_dry_run_ignores_it(self):
        self.assertEqual(self.main(["up", "-l", "l2"])[0], 0)
        self.assertEqual(self.main(["up", "-l", "l2"])[0], 0)
        fd = self.st.try_lock()
        self.addCleanup(lambda: fstate.State.unlock(fd) if fd is not None else None)
        self.assertEqual(self.main(["up", "--dry-run", "-l", "l2"])[0], 0)
        self.assertEqual(self.main(["holds"])[0], 0)

    def test_two_concurrent_runs_exactly_one_wins_20_times(self):
        for i in range(20):
            self.tr = FakeTransport(self.data, delay=0.05)
            gate = threading.Barrier(2)
            results = []

            def attempt():
                gate.wait()
                results.append(self.main(["up", "-l", "l2"])[0])

            threads = [threading.Thread(target=attempt) for _ in range(2)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()
            self.assertEqual(sorted(results), [0, 3], msg="iteration %d" % i)
            self.assertEqual(self.tr.counts.get(("l2", "update")), 1, msg="iteration %d" % i)

    # -- dry-run must not resolve the ntfy token
    def _op_stub(self):
        trip = self.tmp / "op-called"
        stub = self.tmp / "op"
        stub.write_text("#!/usr/bin/env bash\necho called >> %s\necho tk_%s\n" % (trip, "z" * 24))
        stub.chmod(0o700)
        return trip, str(stub)

    def test_dry_run_never_calls_op_read(self):
        trip, stub = self._op_stub()
        env = self.env(FLEET_OP=stub)
        for argv in (["up", "--dry-run", "-l", "l2"], ["reboot", "--pending", "--dry-run", "-l", "l2"],
                     ["up", "--dry-run"]):
            rc, _, _ = self.main(argv, env=env, notifier=None)
            self.assertEqual(rc, 0, msg=str(argv))
        self.assertFalse(trip.exists())

    def test_positive_control_building_the_notifier_does_call_op(self):
        trip, stub = self._op_stub()
        notifier = orchestrate._make_notifier(self.data, self.st, {"FLEET_OP": stub}, io.StringIO())
        self.assertIsNotNone(notifier)
        self.assertTrue(trip.exists())
        self.assertTrue(notifier.token.startswith("tk_"))

    def test_http_ntfy_url_with_a_token_gives_no_notifier_and_a_warning(self):
        self.data["ntfy"]["url"] = "http://ntfy.example.org"
        err = io.StringIO()
        notifier = orchestrate._make_notifier(self.data, self.st, {"FLEET_NTFY_TOKEN": FAKE_TOKEN}, err)
        self.assertIsNone(notifier)
        self.assertIn("https", err.getvalue())

    # -- reboot dry-run
    def test_reboot_dry_run_prints_reboot_targets_not_the_update_plan(self):
        rc, out, _ = self.main(["reboot", "--pending", "--dry-run", "-l", "l2,l3,fw,diabolo"], notifier=None)
        self.assertEqual(rc, 0)
        self.assertEqual(self.tr.connects, 0)
        self.assertNotIn("phase", out)
        self.assertRegex(out, r"reboot[^\n]*: l2, l3")
        self.assertRegex(out, r"fw[^\n]*--critical")
        self.assertRegex(out, r"diabolo[^\n]*master")
        rc, out, _ = self.main(["reboot", "--pending", "--dry-run", "--critical", "-l", "fw"], notifier=None)
        self.assertRegex(out, r"reboot[^\n]*: fw")

    def test_console_reboot_dry_run_also_prints_reboot_targets(self):
        env = self.env(FLEET_HOSTNAME="laptop")
        env.pop("FLEET_MASTER")
        rc, out, _ = self.main(["reboot", "--pending", "--dry-run", "-l", "l2"], env=env, notifier=None)
        self.assertEqual(rc, 0)
        self.assertNotIn("phase", out)
        self.assertIn("l2", out)

    # -- modes of everything a real run leaves behind
    def test_every_file_and_directory_left_by_a_run_is_private(self):
        old = os.umask(0o022)
        self.addCleanup(os.umask, old)
        self.ntfy_up = False
        self.assertEqual(self.main(["up", "-l", "l2"])[0], 0)
        self.main(["hold", "l3", "--reason", "x", "--until", "2026-12-31"])
        names = set()
        for p in [self.root] + list(self.root.rglob("*")):
            self.assertEqual(stat.S_IMODE(p.stat().st_mode), 0o700 if p.is_dir() else 0o600, str(p))
            names.add(p.name)
        for needed in ("runs", "raw", "report.md", "report.json", "run.log", "run.lock", "ntfy-queue",
                       "history-diabolo.jsonl", "last-success-diabolo.json", "holds-diabolo.json"):
            self.assertIn(needed, names)

    # -- the real fleet.yml
    def test_real_inventory_garage_plan_contains_every_garage_host(self):
        real = ROOT / "dot_local/share/fleet/fleet.yml"
        data = inv.load_inventory(str(real))
        garage = [a for a, h in data["hosts"].items() if h["site"] == "garage"]
        self.assertGreaterEqual(len(garage), 2)
        out, err = io.StringIO(), io.StringIO()
        rc = orchestrate.main(["up", "--dry-run", "-l", "site=garage"], env={
            "FLEET_YML": str(real), "FLEET_STATE_DIR": str(self.root), "FLEET_MASTER": "diabolo"},
            transport=FakeTransport(data), notifier=None, out=out, err=err)
        self.assertEqual(rc, 0, err.getvalue())
        for alias in garage:
            self.assertIn(alias, out.getvalue())
        # omv-garage is kind omv (phase 1 by kind) but carries the site-router tag: phase 2, serial.
        self.assertEqual(data["hosts"]["omv-garage"]["kind"], "omv")
        self.assertIn("site-router", data["hosts"]["omv-garage"]["tags"])
        self.assertIn("phase 2 (serial): omv-garage, ha-garage", out.getvalue())
        self.assertNotIn("phase 1", out.getvalue())


class ReviewOrchestrateTest(Env):
    def test_a_notifier_exception_never_aborts_the_run(self):
        class Broken:
            def send(self, msg):
                raise RuntimeError("ntfy exploded")

        self.tr.script["l2"] = lambda v, n: (1, "", "fleet-agent: refused (verb)")
        orch = orchestrate.Orchestrator(self.data, self.st, "diabolo", self.tr, Broken(),
                                        orchestrate.Options(sleep=self.clock.advance), now=self.clock.now)
        self.st.set_last_success("l3", fstate.iso(START - timedelta(days=40)))
        rep, rc = orch.run_up(["l2", "l3"], "t")
        self.assertEqual(rc, 1)
        self.assertTrue((self.st.run_dir(rep["run_id"]) / "report.json").is_file())
        self.assertEqual(self.tr.synced, [("diabolo", ["penelope"])])       # sync + purge still ran
        self.assertTrue(any("notification" in line for line in orch.log_lines))

    def test_a_valid_failed_reply_to_reboot_is_returned_at_once(self):
        def script(v, n):
            if v == "reboot-status":
                return 0, agent_line("l2", v, "up-to-date", reboot_required=True), ""
            return 0, agent_line("l2", v, "failed", reason="sudo denied"), ""

        self.tr.script["l2"] = script
        rep, rc = self.orch(confirm=lambda p: True).run_reboot(["l2"], "t")
        self.assertEqual(rep["hosts"][0]["status"], "failed")
        self.assertIn("sudo denied", rep["hosts"][0]["reason"])
        self.assertEqual(self.tr.counts[("l2", "reboot-status")], 1)      # no polling for a return
        self.assertEqual(rc, 1)
        self.assertEqual(self.sent, [])                                   # not a "did not come back"

    def test_a_critical_master_still_needs_the_critical_flag(self):
        self.data["hosts"]["diabolo"]["critical"] = True
        by, _, _ = self.run_up(["diabolo"])
        self.assertEqual(by["diabolo"]["status"], "skipped")
        self.assertIn("--critical", by["diabolo"]["reason"])
        self.assertEqual(self.tr.calls, [])
        asked = []
        by, _, _ = self.run_up(["diabolo"], critical=True, confirm=lambda p: asked.append(p) or True)
        self.assertEqual(by["diabolo"]["status"], "updated")
        self.assertEqual(len(asked), 1)
        self.assertTrue(all(local for a, v, local in self.tr.calls))      # the master is still updated locally

    def test_canary_finishes_before_the_other_hosts_of_its_kind_start(self):
        self.tr = FakeTransport(self.data, delay=0.03)
        self.run_up(["l1", "l2", "l3"])
        events = self.tr.timeline
        last_canary = max(i for i, (a, v, k) in enumerate(events) if a == "l1")
        first_other = min(i for i, (a, v, k) in enumerate(events) if a in ("l2", "l3"))
        self.assertLess(last_canary, first_other)

    def test_canary_negative_control_without_canary_they_overlap(self):
        self.tr = FakeTransport(self.data, delay=0.03)
        self.run_up(["l1", "l2", "l3"], no_canary=True)
        events = self.tr.timeline
        last_canary = max(i for i, (a, v, k) in enumerate(events) if a == "l1")
        first_other = min(i for i, (a, v, k) in enumerate(events) if a in ("l2", "l3"))
        self.assertGreater(last_canary, first_other)

    def test_phases_2_and_3_are_strictly_serial(self):
        self.tr = FakeTransport(self.data, delay=0.03)
        by, _, _ = self.run_up(["omvn", "ha1", "g1", "g2", "gw"])
        self.assertTrue(all(e["status"] == "updated" for e in by.values()))
        self.assertEqual(self.tr.max_total, 1)

    def test_phase_1_negative_control_runs_in_parallel(self):
        self.tr = FakeTransport(self.data, delay=0.03)
        self.run_up(["penelope", "l2", "l3", "m1"])
        self.assertGreater(self.tr.max_total, 1)

    def test_no_secret_anywhere_in_the_state_dir_even_with_ntfy_down(self):
        pem = "-----BEGIN OPENSSH " + "PRIVATE KEY-----\nb3BlbnNzaC1rZXk"
        jwt = "eyJ" + "hbGciOiJIUzI1NiJ9" + "xx.payloadpayloadpayload.sigsig"
        self.ntfy_up = False
        self.tr.script["l2"] = lambda v, n: (
            0, agent_line("l2", v, "failed", reason="token " + FAKE_TOKEN, log_tail="k " + FAKE_TOKEN + "\n" + pem),
            "stderr " + FAKE_TOKEN + " " + jwt)
        self.tr.script["l3"] = lambda v, n: (1, "", "fleet-agent: refused " + FAKE_TOKEN + " " + jwt)
        self.tr.script["m1"] = lambda v, n: (255, "", "ssh: " + pem.replace("\n", " ") + " " + FAKE_TOKEN)
        self.run_up(["l2", "l3", "m1"])
        self.assertGreaterEqual(len(self.notifier.pending()), 1)          # ntfy down: queue files exist
        scanned = 0
        for p in self.root.rglob("*"):
            if p.is_file():
                scanned += 1
                self.assertNotRegex(p.read_text(), SECRET_GREP, str(p))
        self.assertGreater(scanned, 8)
        self.assertNotIn(FAKE_TOKEN[3:12], "".join(p.read_text() for p in self.root.rglob("*") if p.is_file()))


class ReviewInventoryNamesTest(unittest.TestCase):
    def load(self, host_extra="", alias="alpha", name="alpha", user="j"):
        text = ("hosts:\n  %s:\n    tailnet_name: %s\n    site: dijon\n    kind: chezmoi-linux\n"
                "    critical: false\n    ssh_user: %s\n%s" % (alias, name, user, host_extra))
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "fleet.yml"
            path.write_text(text)
            return inv.load_inventory(str(path))

    def test_valid_names_load(self):
        self.assertIn("alpha", self.load()["hosts"])

    def test_leading_dash_in_alias_tailnet_name_or_user_is_rejected(self):
        for kwargs in ({"alias": "-oProxyCommand=x"}, {"name": "-oProxyCommand=x"}, {"user": "-oProxyCommand=x"},
                       {"name": "-x"}, {"user": "-j"}):
            with self.assertRaises(inv.InventoryError, msg=str(kwargs)):
                self.load(**kwargs)

    def test_name_patterns_do_not_accept_a_trailing_newline(self):
        self.assertIsNone(inv.SAFE_NAME.fullmatch("alpha\n"))
        self.assertIsNone(inv.SAFE_USER.fullmatch("j\n"))
        self.assertIsNone(inv.SAFE_SERVICE.fullmatch("kvmd\n"))


if __name__ == "__main__":
    unittest.main()
