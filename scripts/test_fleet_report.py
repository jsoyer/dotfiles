#!/usr/bin/env python3
"""Agent-output schema, secret masking, state files, reports, ntfy queue, reminder.

Nothing here talks to a network, a real home directory or 1Password: state lives
in a tmp dir and the ntfy sender is a fake.
"""

import json
import re
import stat
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / "dot_local/share/fleet/lib"
sys.path.insert(0, str(LIB))

import inventory as inv  # noqa: E402
import notify  # noqa: E402
import report  # noqa: E402
import schema  # noqa: E402
import state as fstate  # noqa: E402

NOW = datetime(2026, 10, 30, 21, 0, 0, tzinfo=timezone.utc)
SECRET_GREP = re.compile(r"BEGIN [A-Z ]*PRIVATE KEY|tk_[A-Za-z0-9]{20,}|eyJ[A-Za-z0-9_-]{20,}\.")
FAKE_TOKEN = "tk_" + "a1B2c3D4e5F6g7H8i9J0k1L2m3N4"
FAKE_JWT = "eyJ" + "hbGciOiJIUzI1NiJ9" + "xx.payloadpayloadpayload.sigsigsig"
PEM_BEGIN = "-----BEGIN OPENSSH " + "PRIVATE KEY-----"  # split: keeps scanners quiet
PEM_END = "-----END OPENSSH " + "PRIVATE KEY-----"
PEM_TRUNC = PEM_BEGIN + "\nb3BlbnNzaC1rZXktdjEAAAAA\nAAAAB3NzaC1lZDI1NTE5"


def agent(**over):
    base = {
        "schema": 1, "host": "alpha", "verb": "update", "status": "updated",
        "reason": None, "packages": 3, "changes": [{"name": "openssl", "from": "1", "to": "2"}],
        "reboot_required": False, "job": None, "started": "2026-10-30T20:00:00Z",
        "ended": "2026-10-30T20:05:00Z", "log_tail": "ok",
    }
    base.update(over)
    return base


def line(obj):
    return json.dumps(obj)


class SchemaTest(unittest.TestCase):
    def test_valid_output_is_accepted_and_host_comes_from_the_master(self):
        ent, why = schema.parse_agent_output(line(agent(host="evil")), "alpha", "update")
        self.assertIsNone(why)
        self.assertEqual(ent["status"], "updated")
        self.assertEqual(ent["host"], "alpha")
        self.assertEqual(ent["packages"], 3)

    def test_invalid_fixtures_are_rejected(self):
        bad = [
            "", "not json", "[]", "{}", line(agent(schema=2)), line(agent(status="exploded")),
            # master-only statuses can never be claimed by an agent
            line(agent(status="offline")), line(agent(status="held")),
            line(agent(packages="3")), line(agent(packages=True)),
            line(agent(job="x; rm -rf /")), line(agent(job="$(id)")),
            line(agent(changes="nope")), line(agent(changes=[{"name": 1}])),
            line(agent(reboot_required="yes")),
            line(agent()) + "\n" + line(agent()),
            "x" * 200000,
        ]
        for text in bad:
            ent, why = schema.parse_agent_output(text, "alpha", "update")
            self.assertIsNone(ent, msg=text[:60])
            self.assertTrue(why)

    def test_failed_entry_and_master_entry_shapes(self):
        f = schema.failed_entry("alpha", "update", "invalid agent output", "2026-10-30T21:00:00Z")
        self.assertEqual((f["schema"], f["status"], f["host"]), (1, "failed", "alpha"))
        m = schema.master_entry("alpha", "update", "offline", "peer down", "2026-10-29T10:00:00Z",
                                "2026-10-30T21:00:00Z", "2026-10-30T21:00:00Z")
        self.assertEqual(m["last_seen"], "2026-10-29T10:00:00Z")
        with self.assertRaises(ValueError):
            schema.master_entry("alpha", "update", "updated", "", None, "", "")

    def test_control_characters_and_secrets_are_scrubbed(self):
        ent, _ = schema.parse_agent_output(
            line(agent(log_tail="\x1b[31mred\x1b[0m\n" + FAKE_TOKEN, reason="bad\x07 " + FAKE_JWT)),
            "alpha", "update")
        blob = json.dumps(ent)
        self.assertNotIn("\x1b", blob)
        self.assertNotRegex(blob, SECRET_GREP)

    def test_log_tail_capped_to_20_lines(self):
        ent, _ = schema.parse_agent_output(
            line(agent(log_tail="\n".join("l%d" % i for i in range(60)))), "alpha", "update")
        self.assertLessEqual(len(ent["log_tail"].splitlines()), 20)

    def test_vocabulary_matches_spec(self):
        self.assertEqual(set(schema.AGENT_STATUSES), {
            "started", "running", "updated", "up-to-date", "degraded", "failed", "busy",
            "skipped", "unsupported"})
        self.assertEqual(set(schema.MASTER_STATUSES), {"offline", "unreachable", "timeout", "held"})


class MaskTest(unittest.TestCase):
    def test_patterns(self):
        cases = [
            "https://user:p/ss@w0rd@host.example/path",
            "https://user:pa@ss@host/x",
            PEM_TRUNC,
            PEM_TRUNC + "\n" + PEM_END + "\nafter",
            "Authorization: Bearer " + FAKE_TOKEN,
            "token " + FAKE_TOKEN, FAKE_JWT, "password=hunter2 next",
        ]
        for text in cases:
            out = schema.mask_secrets(text)
            self.assertNotRegex(out, SECRET_GREP, msg=text)
            self.assertNotIn("hunter2", out)
            self.assertNotIn("p/ss", out)
            self.assertNotIn("pa@ss", out)
            self.assertNotIn("b3BlbnNz", out)

    def test_harmless_text_untouched(self):
        self.assertEqual(schema.mask_secrets("openssl 3.0.13 -> 3.0.15 on host"), "openssl 3.0.13 -> 3.0.15 on host")

    def test_text_after_complete_pem_is_kept(self):
        out = schema.mask_secrets(PEM_TRUNC + "\n" + PEM_END + "\nafter")
        self.assertIn("after", out)


class StateTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "fleet"
        self.diabolo = fstate.State(self.root, "diabolo")
        self.penelope = fstate.State(self.root, "penelope")

    def _entry(self, host, status="updated", started="2026-10-30T20:00:00Z"):
        return {"host": host, "status": status, "reason": None, "packages": 1,
                "reboot_required": False, "last_seen": None, "started": started, "ended": started}

    def test_files_are_private(self):
        self.diabolo.append_history("20261030T2000Z-diabolo", self._entry("a"))
        self.diabolo.set_last_success("a", "2026-10-30T20:00:00Z")
        self.diabolo.add_hold("a", "why", "2026-12-01")
        for p in list(self.root.glob("*.json*")):
            self.assertEqual(stat.S_IMODE(p.stat().st_mode), 0o600, p.name)
        self.assertEqual(stat.S_IMODE(self.root.stat().st_mode), 0o700)

    def test_history_merge_dedups_run_id_host(self):
        rid = "20261030T2000Z-diabolo"
        self.diabolo.append_history(rid, self._entry("a"))
        self.diabolo.append_history(rid, self._entry("a"))  # duplicate
        self.penelope.append_history("20261030T2100Z-penelope", self._entry("a"))
        merged = self.diabolo.history()
        self.assertEqual(len(merged), 2)
        self.assertEqual({r["master"] for r in merged}, {"diabolo", "penelope"})

    def test_each_master_writes_only_its_own_files(self):
        self.diabolo.append_history("20261030T2000Z-diabolo", self._entry("a"))
        self.assertTrue((self.root / "history-diabolo.jsonl").exists())
        self.assertFalse((self.root / "history-penelope.jsonl").exists())

    def test_retention_purges_history_and_runs_but_never_last_success(self):
        old = NOW - timedelta(days=40)
        old_id = old.strftime("%Y%m%dT%H%MZ") + "-diabolo"
        new_id = (NOW - timedelta(days=2)).strftime("%Y%m%dT%H%MZ") + "-diabolo"
        self.diabolo.append_history(old_id, self._entry("a", started=fstate.iso(old)))
        self.diabolo.append_history(new_id, self._entry("a", started=fstate.iso(NOW - timedelta(days=2))))
        self.diabolo.set_last_success("a", fstate.iso(old))
        for rid in (old_id, new_id):
            d = self.diabolo.run_dir(rid)
            (d / "raw").mkdir(parents=True, exist_ok=True)
            (d / "report.json").write_text("{}")
        self.diabolo.purge(NOW, days=31)
        ids = {r["run_id"] for r in self.diabolo.history()}
        self.assertEqual(ids, {new_id})
        self.assertFalse(self.diabolo.run_dir(old_id).exists())
        self.assertTrue(self.diabolo.run_dir(new_id).exists())
        self.assertEqual(self.diabolo.last_success()["a"], fstate.iso(old))

    def test_stale_alert_survives_history_purge_40_days(self):
        old = NOW - timedelta(days=40)
        self.diabolo.append_history(old.strftime("%Y%m%dT%H%MZ") + "-diabolo",
                                    self._entry("a", started=fstate.iso(old)))
        self.diabolo.set_last_success("a", fstate.iso(old))
        self.diabolo.purge(NOW, days=31)
        self.assertEqual(self.diabolo.history(), [])
        stale = report.stale_hosts(self.diabolo.last_success(), NOW, days=30)
        self.assertEqual([s[0] for s in stale], ["a"])
        self.assertGreaterEqual(stale[0][2], 40)
        fresh = report.stale_hosts({"a": fstate.iso(NOW - timedelta(days=3))}, NOW, days=30)
        self.assertEqual(fresh, [])

    def test_last_success_merge_keeps_latest(self):
        self.diabolo.set_last_success("a", "2026-10-01T00:00:00Z")
        self.penelope.set_last_success("a", "2026-10-20T00:00:00Z")
        self.assertEqual(self.diabolo.last_success()["a"], "2026-10-20T00:00:00Z")

    def test_hold_expiry_and_unhold_wins_across_masters(self):
        self.diabolo.add_hold("a", "maintenance", "2026-11-30")
        self.assertIn("a", self.penelope.active_holds(NOW))
        self.penelope.lift_hold("a")  # lift written by the OTHER master
        self.assertNotIn("a", self.diabolo.active_holds(NOW + timedelta(seconds=5)))
        self.diabolo.add_hold("b", "short", "2026-10-29")
        self.assertNotIn("b", self.diabolo.active_holds(NOW))  # expired

    def test_new_hold_after_unhold_applies_again(self):
        t0 = datetime(2026, 10, 30, 10, 0, 0, tzinfo=timezone.utc)
        s = fstate.State(self.root, "diabolo", now=lambda: t0)
        s.add_hold("a", "one", "2026-12-01")
        s2 = fstate.State(self.root, "diabolo", now=lambda: t0 + timedelta(minutes=1))
        s2.lift_hold("a")
        s3 = fstate.State(self.root, "diabolo", now=lambda: t0 + timedelta(minutes=2))
        s3.add_hold("a", "two", "2026-12-01")
        self.assertEqual(s3.active_holds(t0 + timedelta(minutes=3))["a"]["reason"], "two")

    def test_last_run_started(self):
        self.assertIsNone(self.diabolo.last_run_started())
        self.diabolo.append_history("20261001T0000Z-diabolo", self._entry("a", started="2026-10-01T00:00:00Z"))
        self.penelope.append_history("20261015T0000Z-penelope", self._entry("a", started="2026-10-15T00:00:00Z"))
        self.assertEqual(self.diabolo.last_run_started(), datetime(2026, 10, 15, tzinfo=timezone.utc))


FLEET = """\
hosts:
  alpha:
    tailnet_name: alpha
    site: dijon
    kind: chezmoi-linux
    critical: false
    ssh_user: j
  beta:
    tailnet_name: beta
    site: nice
    kind: omv
    critical: false
    ssh_user: j
"""


class ReportTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "fleet"
        self.st = fstate.State(self.root, "diabolo")
        self.data = inv.parse_yaml_subset(FLEET)

    def _entries(self):
        a = schema.parse_agent_output(
            line(agent(log_tail="line\n" + PEM_TRUNC + "\n" + FAKE_TOKEN, reboot_required=True)),
            "alpha", "update")[0]
        h = schema.master_entry("beta", "update", "held", "maintenance until 2026-11-30", None,
                                "2026-10-30T21:00:00Z", "2026-10-30T21:00:00Z")
        o = schema.master_entry("gone", "update", "offline", "peer down", "2026-10-20T08:00:00Z",
                                "2026-10-30T21:00:00Z", "2026-10-30T21:00:00Z")
        return [a, h, o]

    def _write(self):
        rep = report.build_report("20261030T2100Z-diabolo", "diabolo", "site=dijon",
                                  "2026-10-30T21:00:00Z", "2026-10-30T21:05:00Z", self._entries())
        raw = {e["host"]: {"json": e, "log": (e.get("log_tail") or "") + "\nstderr " + FAKE_JWT}
               for e in rep["hosts"]}
        report.write_run(self.st, rep, raw, ["start " + FAKE_TOKEN, "done"])
        return rep

    def test_summary_line(self):
        s = report.summary_line(self._entries())
        self.assertIn("1 ✅", s)
        self.assertIn("1 offline", s)
        self.assertIn("1 held", s)
        self.assertIn("1 reboot", s)

    def test_held_and_offline_visible_in_every_rendering(self):
        rep = self._write()
        for text in (report.render_terminal(rep, self.data), report.render_markdown(rep, self.data)):
            self.assertIn("held", text)
            self.assertIn("maintenance", text)
            self.assertIn("offline", text)
            self.assertIn("2026-10-20T08:00:00Z", text)  # last connection date

    def test_run_directory_layout_and_secret_free(self):
        self._write()
        run = self.st.run_dir("20261030T2100Z-diabolo")
        for name in ("report.json", "report.md", "run.log", "raw/alpha.json", "raw/alpha.log"):
            self.assertTrue((run / name).is_file(), name)
        for p in run.rglob("*"):
            mode = stat.S_IMODE(p.stat().st_mode)
            self.assertEqual(mode, 0o700 if p.is_dir() else 0o600, str(p))
            if p.is_file():
                self.assertNotRegex(p.read_text(), SECRET_GREP, str(p))
        # equivalent of: grep -rE <secret patterns> runs/  => empty
        hits = [p for p in self.root.rglob("*") if p.is_file() and SECRET_GREP.search(p.read_text())]
        self.assertEqual(hits, [])
        self.assertEqual(json.loads((run / "report.json").read_text())["schema"], 1)

    def test_report_last_logs_and_changes(self):
        self._write()
        rid, rep = report.latest_run(self.st)
        self.assertEqual(rid, "20261030T2100Z-diabolo")
        self.assertEqual(rep["master"], "diabolo")
        self.assertIn("line", report.host_logs(self.st, "alpha"))
        self.assertNotRegex(report.host_logs(self.st, "alpha"), SECRET_GREP)
        ch = report.host_changes(self.st, "alpha", None)
        self.assertIn("openssl", ch)
        self.assertEqual(report.host_changes(self.st, "alpha", datetime(2026, 12, 1, tzinfo=timezone.utc)), "")

    def test_latest_run_spans_masters(self):
        self._write()
        other = fstate.State(self.root, "penelope")
        rep = report.build_report("20261031T0100Z-penelope", "penelope", "", "2026-10-31T01:00:00Z",
                                  "2026-10-31T01:01:00Z", [])
        report.write_run(other, rep, {}, [])
        self.assertEqual(report.latest_run(self.st)[0], "20261031T0100Z-penelope")

    def test_host_logs_rejects_path_tricks(self):
        self._write()
        with self.assertRaises(ValueError):
            report.host_logs(self.st, "../../etc/passwd")


class NotifyTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.qdir = Path(self._tmp.name) / "ntfy-queue"
        self.sent = []
        self.up = True

        def sender(url, topic, headers, body):
            if not self.up:
                raise OSError("ntfy down")
            self.sent.append((url, topic, dict(headers), body))

        self.n = notify.Notifier("https://ntfy.invalid", "fleet", FAKE_TOKEN, self.qdir, sender=sender)

    def test_send_ok(self):
        self.n.send(notify.message("fleet diabolo : ok", 2, ["ok"], "body"))
        self.assertEqual(len(self.sent), 1)
        self.assertEqual(self.sent[0][2]["Priority"], "2")
        self.assertEqual(self.n.pending(), [])

    def test_queue_when_down_then_flushed_in_order_after_recovery(self):
        self.up = False
        for i in range(3):
            self.n.send(notify.message("t%d" % i, 4, ["failed"], "b%d " % i + FAKE_TOKEN))
        self.assertEqual(len(self.n.pending()), 3)
        for p in self.qdir.iterdir():
            self.assertEqual(stat.S_IMODE(p.stat().st_mode), 0o600)
            self.assertNotRegex(p.read_text(), SECRET_GREP)  # token never persisted
        self.up = True
        self.n.send(notify.message("t3", 2, ["ok"], "b3"))
        self.assertEqual([s[2]["Title"] for s in self.sent], ["t0", "t1", "t2", "t3"])
        self.assertEqual(self.n.pending(), [])

    def test_still_down_keeps_queue(self):
        self.up = False
        self.n.send(notify.message("a", 2, ["ok"], "b"))
        self.assertEqual(self.n.flush(), 0)
        self.assertEqual(len(self.n.pending()), 1)

    def test_token_is_sent_as_header_only(self):
        self.n.send(notify.message("a", 2, ["ok"], "b"))
        self.assertEqual(self.sent[0][2]["Authorization"], "Bearer " + FAKE_TOKEN)

    def test_six_event_types_priorities_and_tags(self):
        ok = [schema.parse_agent_output(line(agent()), "alpha", "update")[0]]
        bad = ok + [schema.failed_entry("beta", "update", "boom", "2026-10-30T21:00:00Z")]
        deg = [schema.parse_agent_output(line(agent(status="degraded")), "alpha", "update")[0]]
        got = {
            "ok": notify.summary_message("diabolo", ok),
            "failed": notify.summary_message("diabolo", bad),
            "degraded": notify.summary_message("diabolo", deg),
            "stale": notify.stale_message("diabolo", [("zeta", "2026-09-01T00:00:00Z", 59)]),
            "not_back": notify.not_back_message("diabolo", "opnsense-amd64"),
            "refused": notify.refused_message("diabolo", "alpha"),
            "pull": notify.pull_message("diabolo", "alpha", "3 packages"),
            "reminder": notify.reminder_message("diabolo", 15),
        }
        prio = {k: v["priority"] for k, v in got.items()}
        self.assertEqual(prio, {"ok": 2, "failed": 4, "degraded": 4, "stale": 4, "not_back": 5,
                                "refused": 5, "pull": 2, "reminder": 3})
        self.assertEqual(got["ok"]["tags"], ["ok"])
        self.assertIn("failed", got["failed"]["tags"])
        self.assertIn("degraded", got["degraded"]["tags"])
        self.assertEqual(got["not_back"]["tags"], ["reboot"])
        self.assertEqual(got["refused"]["tags"], ["refused"])
        self.assertEqual(got["pull"]["tags"], ["pull"])
        self.assertEqual(got["reminder"]["tags"], ["reminder"])
        self.assertTrue(got["ok"]["title"].startswith("fleet diabolo : "))
        for m in got.values():
            self.assertLessEqual(len(m["body"].splitlines()), 20)

    def test_body_never_has_log_tail_or_secret(self):
        e = schema.parse_agent_output(line(agent(status="failed", log_tail="RAWTAIL " + FAKE_TOKEN,
                                                 reason="r " + FAKE_JWT)), "alpha", "update")[0]
        m = notify.summary_message("diabolo", [e])
        self.assertNotIn("RAWTAIL", m["body"])
        self.assertNotRegex(json.dumps(m), SECRET_GREP)

    def test_body_capped_at_20_lines(self):
        es = [schema.failed_entry("h%d" % i, "update", "x", "2026-10-30T21:00:00Z") for i in range(50)]
        self.assertLessEqual(len(notify.summary_message("d", es)["body"].splitlines()), 20)

    def test_token_resolution_env_first_then_op_runner(self):
        self.assertEqual(notify.resolve_token("op://x", {"FLEET_NTFY_TOKEN": "envtok"}, None), "envtok")
        calls = []

        def runner(args):
            calls.append(args)
            return "optok\n"

        self.assertEqual(notify.resolve_token("op://V/I/f", {}, runner), "optok")
        self.assertEqual(calls, [["op", "read", "op://V/I/f"]])
        self.assertIsNone(notify.resolve_token("", {}, runner))

    def test_non_latin1_title_is_header_safe(self):
        enc = notify.encode_header("fleet diabolo : 24 ✅ · 1 ❌")
        enc.encode("latin-1")  # must not raise


class ReminderTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "fleet"
        self.st = fstate.State(self.root, "diabolo")
        self.sent = []
        self.n = notify.Notifier("https://ntfy.invalid", "fleet", None, self.root / "q",
                                 sender=lambda *a: self.sent.append(a))

    def _hist(self, days_ago):
        t = NOW - timedelta(days=days_ago)
        self.st.append_history(t.strftime("%Y%m%dT%H%MZ") + "-diabolo", {
            "host": "a", "status": "updated", "reason": None, "packages": 1, "reboot_required": False,
            "last_seen": None, "started": fstate.iso(t), "ended": fstate.iso(t)})

    def test_reminder_after_14_days(self):
        self._hist(20)
        self.assertTrue(notify.reminder_check(self.st, self.n, NOW))
        self.assertEqual(self.sent[0][2]["Priority"], "3")

    def test_no_reminder_when_recent(self):
        self._hist(5)
        self.assertFalse(notify.reminder_check(self.st, self.n, NOW))
        self.assertEqual(self.sent, [])

    def test_reminder_when_never_run(self):
        self.assertTrue(notify.reminder_check(self.st, self.n, NOW))


class TimerUnitsTest(unittest.TestCase):
    def test_units_exist_and_open_no_connection(self):
        d = ROOT / "dot_config/systemd/user"
        svc = (d / "fleet-reminder.service").read_text()
        tmr = (d / "fleet-reminder.timer").read_text()
        self.assertIn("ExecStart=%h/.local/bin/fleet reminder", svc)
        self.assertIn("OnCalendar=daily", tmr)
        self.assertIn("Unit=fleet-reminder.service", tmr)
        self.assertNotIn("ssh", svc.lower().replace("fleet_ssh", ""))


if __name__ == "__main__":
    unittest.main()
