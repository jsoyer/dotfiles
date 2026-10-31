#!/usr/bin/env python3
"""Agent-output schema, secret masking, state files, reports, ntfy queue, reminder.

Nothing here talks to a network, a real home directory or 1Password: state lives
in a tmp dir and the ntfy sender is a fake.
"""

import json
import os
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


class ReviewSchemaTest(unittest.TestCase):
    """Review fixes: masking of structures, hostile JSON, key=value coverage, strict fields."""

    SECRET = "s3cr3tvalue"

    def test_report_json_and_raw_roundtrip_as_valid_json_with_secrets_masked(self):
        with tempfile.TemporaryDirectory() as tmp:
            st = fstate.State(Path(tmp) / "fleet", "diabolo")
            ent, why = schema.parse_agent_output(
                line(agent(reason="password=x", log_tail="token: x\nline2")), "alpha", "update")
            self.assertIsNone(why)
            rep = report.build_report("20261030T2100Z-diabolo", "diabolo", "t", "a", "b", [ent])
            run = report.write_run(st, rep, {"alpha": {"json": ent, "log": "token: x"}}, ["password=x"])
            back = json.loads((run / "report.json").read_text())
            raw = json.loads((run / "raw" / "alpha.json").read_text())
            self.assertEqual(back["hosts"][0]["reason"], "password=[MASKED]")
            self.assertEqual(back["hosts"][0]["log_tail"], "token: [MASKED]\nline2")
            self.assertEqual(raw["log_tail"], "token: [MASKED]\nline2")
            self.assertIsNotNone(report.read_report(st, "20261030T2100Z-diabolo"))

    def test_report_json_is_valid_even_if_an_unmasked_secret_reaches_write_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            st = fstate.State(Path(tmp) / "fleet", "diabolo")
            e = {"host": "alpha", "status": "failed", "reason": 'password=x", "k": 1', "last_seen": None}
            rep = report.build_report("20261030T2100Z-diabolo", "diabolo", "t", "a", "b", [e])
            run = report.write_run(st, rep, {"alpha": {"json": e, "log": ""}}, [])
            json.loads((run / "report.json").read_text())
            json.loads((run / "raw" / "alpha.json").read_text())

    def test_mask_data_masks_strings_recursively_without_touching_structure(self):
        out = schema.mask_data({"a": ["password=x", 3, None, True], "b": {"c": "token: y"}})
        self.assertEqual(out, {"a": ["password=[MASKED]", 3, None, True], "b": {"c": "token: [MASKED]"}})

    def test_hostile_nesting_is_rejected_not_a_crash(self):
        for text in ("[" * 60000, '{"a":' + "[" * 60000, "{" * 60000, "[1]", " 5", '"x"'):
            ent, why = schema.parse_agent_output(text, "alpha", "update")
            self.assertIsNone(ent, msg=text[:20])
            self.assertTrue(why)

    def test_key_value_secrets_of_every_shape_are_masked(self):
        s = self.SECRET
        cases = [
            "DB_PASSWORD=" + s, "access_token=" + s, "AWS_SECRET_ACCESS_KEY=" + s,
            "client_secret=" + s, '"password": "%s"' % s, "'passwd': '%s'" % s,
            "export API_KEY=" + s, "secret: " + s, "my-token = " + s,
        ]
        for text in cases:
            out = schema.mask_secrets(text)
            self.assertNotIn(s, out, msg=text)
            self.assertIn(schema.MASK, out)

    def test_quoted_json_secret_keeps_json_valid(self):
        out = schema.mask_secrets('{"password": "%s", "n": 1}' % self.SECRET)
        self.assertEqual(json.loads(out)["n"], 1)

    def _assert_masked(self, text, gone, kept=()):
        out = schema.mask_secrets(text)
        for g in gone:
            self.assertNotIn(g, out, msg=text)
        for k in kept:
            self.assertIn(k, out, msg=text)
        return out

    def test_quoted_value_with_space_and_comma_is_fully_masked(self):
        self._assert_masked('password="ab,cd ef" next=1', ["ab", "cd", "ef"], ["next=1"])

    def test_single_quoted_value_with_semicolon_and_space_is_fully_masked(self):
        self._assert_masked("token='x;y z' ok", ["x;y", "y", "z"], ["ok"])

    def test_quoted_value_containing_the_other_quote_is_fully_masked(self):
        self._assert_masked('DB_PASSWORD="a\'b;c"', ["a'b", "b;c", "c"], [schema.MASK])
        self._assert_masked("secret='a\"b,c'", ['a"b', "b,c"], [schema.MASK])

    def test_json_style_pair_masks_only_its_own_value(self):
        out = self._assert_masked('{"password": "p,q r", "user": "bob"}', ["p,q", "q r"], ["user", "bob"])
        self.assertEqual(json.loads(out)["user"], "bob")

    def test_unterminated_quote_masks_to_end_of_line(self):
        self._assert_masked('password="abc def', ["abc", "def"])
        self._assert_masked("pw token='abc def\nnext line", ["abc", "def"], ["next line"])

    def test_unquoted_value_is_masked_through_commas(self):
        self._assert_masked("password=abc,def", ["abc", "def"])

    def test_url_userinfo_with_slash_and_at_in_password(self):
        self._assert_masked("https://u:p/a@b@host/x", ["p/a@b"], ["host/x"])

    def test_truncated_pem_body_is_masked(self):
        self._assert_masked(PEM_TRUNC, ["b3BlbnNzaC1", "AAAAB3NzaC1lZDI1"])

    def test_tokens_and_jwt_still_masked(self):
        for text in ("tk_" + "a1B2c3D4e5F6g7H8i9J0k1L2", "NTFY_tk_" + "a1B2c3D4e5F6g7H8i9J0k1L2",
                     "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.abcdefghijk"):
            self.assertNotRegex(schema.mask_secrets(text), SECRET_GREP, msg=text)
            self.assertIn(schema.MASK, schema.mask_secrets(text))

    def test_ntfy_token_masked_when_embedded(self):
        for text in ("NTFY_" + FAKE_TOKEN, "x" + FAKE_TOKEN, "a_b" + FAKE_TOKEN + "z", FAKE_TOKEN):
            out = schema.mask_secrets(text)
            self.assertNotRegex(out, SECRET_GREP, msg=text)
            self.assertNotIn("a1B2c3D4", out)

    def test_url_userinfo_token_masked_but_plain_user_kept(self):
        out = schema.mask_secrets("https://ghp_abcdefghijklmnopqrstuvwx@github.com/o/r")
        self.assertNotIn("ghp_abcdef", out)
        self.assertIn("@github.com/o/r", out)
        self.assertEqual(schema.mask_secrets("ssh://git@github.com/o/r"), "ssh://git@github.com/o/r")

    def test_control_chars_stripped_before_masking_so_splitting_cannot_hide_a_secret(self):
        for text in ("pass\x00word=" + self.SECRET, "tok\x1ben=%s" % self.SECRET, "pass​word=" + self.SECRET,
                     "pass‮word=" + self.SECRET):
            out = schema.clean_text(text)
            self.assertNotIn(self.SECRET, out, msg=repr(text))

    def test_surrogates_and_line_separators_are_cleaned(self):
        out = schema.clean_text("a\ud800b c d‮e‏f⁦g")
        out.encode("utf-8")   # must not raise
        for ch in (" ", " ", "‮", "‏", "⁦", "\ud800"):
            self.assertNotIn(ch, out)
        schema.clean_text("\ud83d", multiline=True).encode("utf-8")

    def test_masking_is_linear_on_big_inputs(self):
        import time as _t
        started = _t.time()
        schema.mask_secrets("a" * 65000)
        schema.mask_secrets("a-" * 32000 + "=")
        self.assertLess(_t.time() - started, 3)

    def test_escaped_quotes_and_glued_tails_are_fully_masked(self):
        out = schema.mask_secrets('password="ab\\"cd ef" next=1')
        for leak in ("ab", "cd", "ef"):
            self.assertNotIn(leak, out)
        self.assertIn("next=1", out)
        out = schema.mask_secrets("secret='ab\\'cd ef' ok")
        for leak in ("cd", "ef"):
            self.assertNotIn(leak, out)
        self.assertIn("ok", out)
        out = schema.mask_secrets('token="ab"cd tail')
        self.assertNotIn("ab", out)
        self.assertNotIn("cd", out)
        self.assertIn("tail", out)
        self.assertNotIn("cd", schema.mask_secrets("token='ab'cd;x"))
        out = schema.mask_secrets('{"password": "p\\"q r", "user": "bob"}')
        self.assertNotIn("q r", out)
        self.assertIn('"user": "bob"', out)

    def test_masking_hostile_quoted_input_is_fast(self):
        import time as _t
        for text in ('password="' + '\\"' * 30000, "token=" + '"a' * 30000):
            started = _t.time()
            schema.mask_secrets(text)
            self.assertLess(_t.time() - started, 0.5)

    def test_verb_must_match_the_requested_verb(self):
        ent, why = schema.parse_agent_output(line(agent(verb="report")), "alpha", "update")
        self.assertIsNone(ent)
        ent, _ = schema.parse_agent_output(line(agent(verb="update")), "alpha", "update")
        self.assertIsNotNone(ent)
        obj = agent()
        del obj["verb"]
        self.assertIsNotNone(schema.parse_agent_output(line(obj), "alpha", "update")[0])

    def test_strict_field_types_and_ranges(self):
        bad = [
            agent(schema=True), agent(schema=1.0), agent(schema="1"),
            agent(packages=100001), agent(packages=1.5),
            agent(health_after={"disk_free_pct": {"/": 101}}),
            agent(health_after={"disk_free_pct": {"/": -1}}),
            agent(health_after={"disk_free_pct": {"/": 12.5}}),
            agent(health_after={"disk_free_pct": {"/": True}}),
        ]
        for obj in bad:
            ent, why = schema.parse_agent_output(line(obj), "alpha", "update")
            self.assertIsNone(ent, msg=str(obj)[:80])
            self.assertTrue(why)
        ok, _ = schema.parse_agent_output(line(agent(health_after={"disk_free_pct": {"/": 0, "/data": 100}},
                                                     packages=100000)), "alpha", "update")
        self.assertIsNotNone(ok)

    def test_names_with_trailing_newline_are_not_safe(self):
        self.assertIsNone(report.SAFE_HOST.fullmatch("alpha\n"))
        self.assertIsNone(schema.SAFE_JOB.fullmatch("job\n"))
        self.assertIsNone(fstate.RUN_ID.fullmatch("20261030T2100Z-diabolo\n"))
        with self.assertRaises(ValueError):
            fstate.State(Path("/nonexistent-x"), "diabolo\n")
        with self.assertRaises(ValueError):
            report.host_logs(fstate.State(Path(tempfile.mkdtemp()), "d"), "alpha\n")


class ReviewReportTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "fleet"
        self.st = fstate.State(self.root, "diabolo")

    def _run(self, rid, report_obj=None, raw=None):
        d = self.st.run_dir(rid)
        fstate.make_private_dir(d / "raw")
        if report_obj is not None:
            fstate.write_private(d / "report.json", json.dumps(report_obj))
        for name, text in (raw or {}).items():
            fstate.write_private(d / "raw" / name, text)

    def test_host_changes_skips_malformed_entries(self):
        self._run("20261030T2100Z-diabolo", raw={"alpha.json": json.dumps(
            {"changes": [1, "x", None, {"name": "ok", "from": "1", "to": "2"}, {"x": 1}]})})
        self._run("20261030T2101Z-diabolo", raw={"alpha.json": json.dumps([1, 2])})
        self._run("20261030T2102Z-diabolo", raw={"alpha.json": json.dumps({"changes": "nope"})})
        self._run("20261030T2103Z-diabolo", raw={"alpha.json": "{broken"})
        text = report.host_changes(self.st, "alpha", None)
        self.assertIn("ok  1 -> 2", text)

    def test_list_runs_text_survives_malformed_reports(self):
        self._run("20261030T2100Z-diabolo", {"hosts": "nope"})
        self._run("20261030T2101Z-diabolo", {"hosts": [1, None, {"status": "updated"}, {"host": "a"}]})
        self._run("20261030T2102Z-diabolo", [1])
        self._run("20261030T2103Z-diabolo", {})
        out = report.list_runs_text(self.st)
        self.assertEqual(len(out.strip().splitlines()), 4)

    def test_render_survives_malformed_hosts(self):
        rep = {"master": "m", "run_id": "r", "hosts": [1, {"status": "updated"}, {"host": "a", "status": "failed"}]}
        self.assertIn("a", report.render_terminal(rep))
        self.assertIn("a", report.render_markdown(rep))

    def test_run_id_is_validated_before_any_path_is_built(self):
        for bad in ("../x", "20261030T2100Z-d/../../x", "20261030T2100Z-a..b", "20261030T2100Z-d\n", ""):
            with self.assertRaises(ValueError, msg=bad):
                self.st.run_dir(bad)
            if bad:
                with self.assertRaises(ValueError, msg=bad):
                    report.host_logs(self.st, "alpha", bad)

    def test_markdown_cells_escape_agent_text(self):
        e = {"host": "alpha", "status": "failed",
             "reason": "[click](http://evil) <b>x</b> ![i](u) a*b*c `c` _u_ \\ |", "last_seen": None}
        rep = report.build_report("r", "m", "[sel](x)", "s", "e", [e])
        md = report.render_markdown(rep)
        row = [ln for ln in md.splitlines() if ln.startswith("| alpha")][0]
        for raw in ("[click]", "<b>", "![i]", "a*b", "`c`", "_u_"):
            self.assertNotIn(raw, row)
        self.assertEqual(row.count("|") - row.count("\\|"), 5)   # only the real column separators
        self.assertNotIn("[sel](x)", md)

    def test_modes_of_every_state_file_and_directory(self):
        old = os.umask(0o022)
        self.addCleanup(os.umask, old)
        st = fstate.State(Path(self._tmp.name) / "a" / "b" / "fleet", "diabolo")
        e = schema.master_entry("alpha", "update", "held", "r", None, "s", "e")
        rid = "20261030T2100Z-diabolo"
        rep = report.build_report(rid, "diabolo", "", "s", "e", [e])
        report.write_run(st, rep, {"alpha": {"json": e, "log": "x"}}, ["l"])
        st.append_history(rid, e)
        st.set_last_success("alpha", "2026-10-30T20:00:00Z")
        st.add_hold("alpha", "why", "2026-12-01")

        def down(*a):
            raise OSError("down")

        n = notify.Notifier("https://ntfy.invalid", "fleet", None, st.root / "ntfy-queue", sender=down)
        n.send(notify.message("t", 2, [], "b"))
        seen = 0
        for p in [st.root] + list(st.root.rglob("*")):
            mode = stat.S_IMODE(p.stat().st_mode)
            self.assertEqual(mode, 0o700 if p.is_dir() else 0o600, str(p))
            seen += 1
        self.assertGreaterEqual(seen, 12)


class ReviewNotifyTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.qdir = Path(self._tmp.name) / "q"
        self.sent = []
        self.fail = None

        def sender(url, topic, headers, body):
            if self.fail is not None:
                raise self.fail
            self.sent.append(body)

        self.n = notify.Notifier("https://ntfy.invalid", "fleet", FAKE_TOKEN, self.qdir, sender=sender)

    def _http(self, code):
        import urllib.error
        return urllib.error.HTTPError("https://ntfy.invalid/fleet", code, "x", {}, None)

    def test_permanent_http_4xx_is_quarantined_and_does_not_block_the_queue(self):
        for code in (400, 413, 422):
            self.fail = self._http(code)
            self.assertFalse(self.n.send(notify.message("bad", 2, [], "b")))
            self.fail = None
            self.assertTrue(self.n.send(notify.message("good", 2, [], "g%d" % code)))
            self.assertEqual(self.n.pending(), [])
        self.assertEqual(len(list(self.qdir.glob("*.bad"))), 3)

    def test_queued_message_rejected_with_4xx_is_quarantined_then_next_is_sent(self):
        self.fail = OSError("down")
        self.n.send(notify.message("one", 2, [], "b1"))
        self.n.send(notify.message("two", 2, [], "b2"))
        self.assertEqual(len(self.n.pending()), 2)
        calls = []
        outer = self

        def sender(url, topic, headers, body):
            calls.append(body)
            if body == "b1":
                raise outer._http(413)

        self.n.sender = sender
        self.assertEqual(self.n.flush(), 1)
        self.assertEqual(calls, ["b1", "b2"])
        self.assertEqual(self.n.pending(), [])
        self.assertEqual(len(list(self.qdir.glob("*.bad"))), 1)

    def test_transient_http_statuses_and_http_exceptions_keep_the_queue(self):
        import http.client
        for exc in (self._http(500), self._http(503), self._http(401), self._http(403), self._http(429),
                    OSError("down"), http.client.BadStatusLine("x"), http.client.IncompleteRead(b"")):
            self.fail = exc
            self.assertFalse(self.n.send(notify.message("t", 2, [], "b")), msg=repr(exc))
            self.fail = None
            self.assertEqual(len(self.n.pending()), 1, msg=repr(exc))
            self.assertEqual(self.n.flush(), 1)

    def test_corrupt_queue_files_are_quarantined_without_exception(self):
        self.qdir.mkdir(parents=True)
        (self.qdir / "0001.json").write_text("{not json")
        (self.qdir / "0002.json").write_text(json.dumps({"title": "only"}))
        (self.qdir / "0003.json").write_text(json.dumps([1, 2]))
        (self.qdir / "0004.json").write_text(json.dumps({"title": 1, "body": ["x"], "priority": "p"}))
        self.assertTrue(self.n.send(notify.message("ok", 2, [], "fine")))
        self.assertEqual(self.sent, ["fine"])
        self.assertEqual(len(list(self.qdir.glob("*.bad"))), 4)
        self.assertEqual(self.n.pending(), [])

    def test_http_url_with_token_is_refused_except_for_loopback(self):
        with self.assertRaises(ValueError):
            notify.Notifier("http://ntfy.example.org", "fleet", FAKE_TOKEN, self.qdir)
        with self.assertRaises(ValueError):
            notify.Notifier("ftp://ntfy.example.org", "fleet", FAKE_TOKEN, self.qdir)
        notify.Notifier("http://localhost:8080", "fleet", FAKE_TOKEN, self.qdir)
        notify.Notifier("http://127.0.0.1:8080", "fleet", FAKE_TOKEN, self.qdir)
        notify.Notifier("http://ntfy.example.org", "fleet", None, self.qdir)
        notify.Notifier("https://ntfy.example.org", "fleet", FAKE_TOKEN, self.qdir)


class Review3Test(unittest.TestCase):
    """Review round 3: redirects, key-based masking, log sanitizing, ReDoS, queue locking."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "fleet"
        self.st = fstate.State(self.root, "diabolo")
        self.qdir = Path(self._tmp.name) / "q"

    def _serve(self, handler):
        import http.server
        import threading
        srv = http.server.HTTPServer(("127.0.0.1", 0), handler)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        self.addCleanup(srv.server_close)
        self.addCleanup(srv.shutdown)
        return srv.server_address[1]

    def _servers(self):
        import http.server
        seen = []

        class Target(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                seen.append(self.headers.get("Authorization"))
                self.send_response(200)
                self.end_headers()

            def log_message(self, *a):
                pass

        tport = self._serve(Target)

        class Redirector(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                self.send_response(302)
                self.send_header("Location", "http://127.0.0.1:%d/fleet" % tport)
                self.end_headers()

            def log_message(self, *a):
                pass

        return self._serve(Redirector), seen

    def test_redirect_is_refused_and_authorization_never_follows_it(self):
        rport, seen = self._servers()
        n = notify.Notifier("http://127.0.0.1:%d" % rport, "fleet", FAKE_TOKEN, self.qdir)
        self.assertFalse(n.send(notify.message("t", 2, [], "b")))
        self.assertEqual(seen, [])
        self.assertEqual(n.pending(), [])
        self.assertEqual(len(list(self.qdir.glob("*.bad"))), 1)

    def test_classify_3xx_is_permanent(self):
        import urllib.error
        for code in (301, 302, 303, 307, 308):
            exc = urllib.error.HTTPError("http://x/", code, "r", {}, None)
            self.assertEqual(notify.classify_failure(exc), "bad")

    def test_mask_data_masks_values_of_secret_keys(self):
        item = {"password": "hunter2", "token": "x", "detail": "ok", "db_password": "p",
                "Access_Token": 12345, "api-key": "k", "empty_secret": "", "nested": [{"passphrase": "z"}]}
        out = schema.mask_data(item)
        self.assertEqual(out["detail"], "ok")
        for key in ("password", "token", "db_password", "Access_Token", "api-key"):
            self.assertEqual(out[key], "[MASKED]", key)
        self.assertEqual(out["empty_secret"], "")
        self.assertEqual(out["nested"][0]["passphrase"], "[MASKED]")
        self.assertEqual(list(schema.mask_data({"pass\u00adword": "hunter2"}).values()), ["[MASKED]"])

    def test_raw_json_masks_secret_keys(self):
        rep = report.build_report("20261030T2100Z-diabolo", "diabolo", "", "s", "e", [])
        raw = {"alpha": {"json": agent(password="hunter2", token="x", detail="ok"), "log": ""}}
        run = report.write_run(self.st, rep, raw, [])
        text = (run / "raw" / "alpha.json").read_text()
        self.assertNotIn("hunter2", text)
        data = json.loads(text)
        self.assertEqual((data["password"], data["token"], data["detail"]), ("[MASKED]", "[MASKED]", "ok"))

    def test_raw_log_ansi_split_secret_is_masked_on_write_and_read(self):
        log = "x tk_abc\x1b[0mdefghijklmnopqrstuvwx y\x07\x00"
        rep = report.build_report("20261030T2100Z-diabolo", "diabolo", "", "s", "e", [])
        run = report.write_run(self.st, rep, {"alpha": {"json": {}, "log": log}}, [])
        written = (run / "raw" / "alpha.log").read_text()
        self.assertNotIn("\x1b", written)
        self.assertNotIn("defghij", written)
        (run / "raw" / "alpha.log").write_text(log)
        out = report.host_logs(self.st, "alpha", "20261030T2100Z-diabolo")
        self.assertNotIn("\x1b", out)
        self.assertNotIn("defghij", out)
        self.assertIn("[MASKED]", out)

    def test_raw_log_is_bounded(self):
        rep = report.build_report("20261030T2100Z-diabolo", "diabolo", "", "s", "e", [])
        run = report.write_run(self.st, rep, {"alpha": {"json": {}, "log": "a" * (report.MAX_RAW_LOG * 3)}}, [])
        self.assertLessEqual(len((run / "raw" / "alpha.log").read_bytes()), report.MAX_RAW_LOG + 1)
        (run / "raw" / "alpha.log").write_text("b" * (report.MAX_RAW_LOG * 3))
        self.assertLessEqual(len(report.host_logs(self.st, "alpha", "20261030T2100Z-diabolo")),
                             report.MAX_RAW_LOG)

    def test_redos_inputs_are_fast(self):
        import time
        for text in ("a://b:" * 10000, "BEGIN " * 10000):
            t0 = time.monotonic()
            schema.mask_secrets(text)
            self.assertLess(time.monotonic() - t0, 0.5, msg=text[:12])
        self.assertNotIn("p/w@x", schema.mask_secrets("postgres://u:p/w@x@db/x"))
        self.assertNotIn("AAAA", schema.mask_secrets(PEM_TRUNC))

    def test_invalid_header_and_invalid_url_are_permanent(self):
        import http.client
        for exc in (ValueError("Invalid header value"), http.client.InvalidURL("bad")):
            def sender(*a, _e=exc):
                raise _e
            n = notify.Notifier("https://ntfy.invalid", "fleet", FAKE_TOKEN, self.qdir, sender=sender)
            self.assertFalse(n.send(notify.message("t", 2, [], "b")))
            self.assertEqual(n.pending(), [], msg=repr(exc))
        self.assertEqual(len(list(self.qdir.glob("*.bad"))), 2)

    def test_newline_in_title_with_real_sender_is_quarantined(self):
        import http.server

        class H(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                self.send_response(200)
                self.end_headers()

            def log_message(self, *a):
                pass

        port = self._serve(H)
        n = notify.Notifier("http://127.0.0.1:%d" % port, "fleet", None, self.qdir)
        self.assertFalse(n.send({"title": "a\nb", "priority": 3, "tags": [], "body": "x"}))
        self.assertEqual(n.pending(), [])
        self.assertEqual(len(list(self.qdir.glob("*.bad"))), 1)

    def test_valid_message_rejects_infinite_priority(self):
        self.assertFalse(notify.valid_message({"title": "t", "body": "b", "priority": float("inf")}))
        self.assertFalse(notify.valid_message({"title": "t", "body": "b", "priority": float("nan")}))
        self.assertTrue(notify.valid_message({"title": "t", "body": "b", "priority": 3}))

    def test_infinity_priority_in_queue_file_is_quarantined(self):
        self.qdir.mkdir(parents=True)
        (self.qdir / "0001.json").write_text('{"title": "t", "body": "b", "priority": Infinity}')
        n = notify.Notifier("https://ntfy.invalid", "fleet", FAKE_TOKEN, self.qdir, sender=lambda *a: None)
        self.assertEqual(n.flush(), 0)
        self.assertEqual(len(list(self.qdir.glob("*.bad"))), 1)

    def test_host_status_line_keeps_status_when_host_looks_secret(self):
        msg = notify.summary_message("diabolo", [
            {"host": "secret-nas", "status": "failed", "reason": "token=abc123"},
            {"host": "token-box", "status": "updated"}])
        self.assertIn("secret-nas: failed", msg["body"])
        self.assertIn("token-box: updated", msg["body"])
        self.assertNotIn("abc123", msg["body"])

        def down(*a):
            raise OSError("down")
        n = notify.Notifier("https://ntfy.invalid", "fleet", None, self.qdir, sender=down)
        n.send(msg)
        queued = json.loads(n.pending()[0].read_text())
        self.assertIn("secret-nas: failed", queued["body"])
        self.assertNotIn("abc123", queued["body"])
        self.assertNotIn(FAKE_TOKEN, notify.message("t", 2, [], "x " + FAKE_TOKEN)["body"])

    def test_rendered_report_masks_per_field_and_cell_ending_in_token_keeps_pipe(self):
        e = [{"host": "alpha", "status": "failed", "reason": "boom token:"},
             {"host": "beta", "status": "failed", "reason": "password=hunter2 " + FAKE_TOKEN}]
        rep = report.build_report("20261030T2100Z-diabolo", "diabolo", "all", "s", "e", e)
        md = report.render_markdown(rep)
        row = [ln for ln in md.splitlines() if ln.startswith("| alpha")][0]
        self.assertTrue(row.endswith("boom token: |"), row)
        for text in (md, report.render_terminal(rep)):
            self.assertNotIn("hunter2", text)
            self.assertNotIn(FAKE_TOKEN, text)
        rep["hosts"][0]["reason"] = "api_key=zzz"
        rep["hosts"][0]["last_seen"] = "token=qqq"
        out = report.render_markdown(rep) + report.render_terminal(rep)
        self.assertNotIn("zzz", out)
        self.assertNotIn("qqq", out)

    def test_parse_agent_output_never_raises(self):
        orig = schema._build
        self.addCleanup(setattr, schema, "_build", orig)

        def boom(*a):
            raise RuntimeError("x")

        schema._build = boom
        ent, why = schema.parse_agent_output(line(agent()), "alpha", "update")
        self.assertIsNone(ent)
        self.assertIn("invalid agent output", why)

    def test_soft_hyphen_and_tag_chars_cannot_split_a_keyword(self):
        for sep in ("\u00ad", "\u061c", "\u180e", "\ufe0f", "\U000e0041"):
            out = schema.clean_text("pass%sword=hunter2" % sep)
            self.assertNotIn("hunter2", out, msg=repr(sep))

    def test_concurrent_flushes_send_each_message_once(self):
        import threading
        import time
        for round_no in range(20):
            qdir = Path(self._tmp.name) / ("race%d" % round_no)
            sent = []
            lock = threading.Lock()

            def sender(url, topic, headers, body):
                time.sleep(0.002)
                with lock:
                    sent.append(body)

            def down(*a):
                raise OSError("down")

            seed = notify.Notifier("https://ntfy.invalid", "fleet", None, qdir, sender=down)
            for i in range(5):
                seed.send(notify.message("t%d" % i, 2, [], "m%d" % i))
            self.assertEqual(len(seed.pending()), 5)
            errors = []

            def run(n):
                try:
                    n.flush()
                except Exception as exc:  # noqa: BLE001
                    errors.append(exc)

            threads = [threading.Thread(target=run, args=(
                notify.Notifier("https://ntfy.invalid", "fleet", None, qdir, sender=sender),))
                for _ in range(2)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()
            self.assertEqual(errors, [])
            self.assertEqual(sorted(sent), ["m0", "m1", "m2", "m3", "m4"], msg="round %d" % round_no)


if __name__ == "__main__":
    unittest.main()
