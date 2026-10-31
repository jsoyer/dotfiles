#!/usr/bin/env python3
"""fleet-agent pull mode (local-only entry), macOS update checks, timer/launchd units.

Pull mode is exercised for real (bash) in the same sandbox as test_fleet_agent
(stubs first on PATH, no network, no root). What is proven:

* the pull entry is NOT a verb and cannot be reached through the forced command;
* it updates only when the last successful update is older than 7 days;
* it never reaches the restart code path (sudo/systemctl stubs record nothing even
  when a restart is required), never runs on guardians / critical kinds / hosts
  without the opt-in marker;
* the ntfy notification has priority 2 and the token never appears in argv, a log
  or a state file.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_fleet_agent as ta  # noqa: E402  (module alias: its TestCases are not re-collected here)

ROOT = ta.ROOT
AGENT = ta.AGENT
UNIT_DIR = ROOT / "dot_config/systemd/user"
PLIST = ROOT / "Library/private_LaunchAgents/com.jsoyer.fleet-pull.plist.tmpl"
TOKEN = "tk_abcdefghijklmnopqrstuvwxyz0123"


def agent_text():
    return AGENT.read_text()


def pull_block():
    """Source of the pull-mode section of the agent."""
    text = agent_text()
    start = text.index("# ---------------------------------------------------------------- pull mode")
    end = text.index("# ---------------------------------------------------------------- main")
    return text[start:end]


@unittest.skipUnless(ta.LINUX, "agent behaviour tests stub Linux tooling")
class PullCase(unittest.TestCase):
    def setUp(self):
        self.sb = ta.Sandbox()
        self.addCleanup(self.sb.cleanup)
        # curl records its argv and its stdin (the config that carries the token).
        ta.Sandbox._script(
            self.sb.bin / "curl",
            '#!/usr/bin/env bash\necho "$*" >> "$STUB_DIR/curl.args"\ncat >> "$STUB_DIR/curl.stdin"\n',
        )
        self.conf = self.sb.root / "conf"
        self.conf.mkdir()
        self.sb.env["FLEET_AGENT_CONF_DIR"] = str(self.conf)

    def enable(self, token=True):
        (self.conf / "pull-enabled").write_text("")
        lines = ["NTFY_URL=https://ntfy.example.test", "NTFY_TOPIC=fleet"]
        if token:
            tokfile = self.sb.root / "ntfy-token"
            tokfile.write_text(TOKEN + "\n")
            lines.append(f"NTFY_TOKEN_FILE={tokfile}")
        (self.conf / "pull.conf").write_text("\n".join(lines) + "\n")

    def pull(self, extra_env=None, args=(), ssh=False, command=None):
        env = dict(self.sb.env, FLEET_AGENT_PULL="1")
        env.pop("SSH_ORIGINAL_COMMAND", None)
        if not ssh:
            env.pop("SSH_CONNECTION", None)
        env.update(extra_env or {})
        if command is not None:
            env["SSH_ORIGINAL_COMMAND"] = command
        return subprocess.run(
            ["bash", str(AGENT), *args], env=env, capture_output=True, text=True,
            timeout=30, stdin=subprocess.DEVNULL,
        )

    def last_success(self, days_ago):
        self.sb.state.mkdir(parents=True, exist_ok=True)
        (self.sb.state / "last-success").write_text(str(int(time.time() - days_ago * 86400)) + "\n")

    def poll(self, predicate, timeout=5.0):
        """Wait (up to `timeout` s) for a condition instead of sleeping a fixed time."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            if predicate():
                return True
            time.sleep(0.05)
        return predicate()

    def enable_url(self, url, token=True):
        (self.conf / "pull-enabled").write_text("")
        tokfile = self.sb.root / "ntfy-token"
        tokfile.write_text(TOKEN + "\n")
        lines = [f"NTFY_URL={url}", "NTFY_TOPIC=fleet"]
        if token:
            lines.append(f"NTFY_TOKEN_FILE={tokfile}")
        (self.conf / "pull.conf").write_text("\n".join(lines) + "\n")

    def reset_state(self):
        self.poll(lambda: not (self.sb.state / "update.lock").exists(), 10)
        shutil.rmtree(self.sb.state, ignore_errors=True)
        for f in ("curl.args", "curl.stdin"):
            (self.sb.stub_dir / f).unlink(missing_ok=True)

    def wait_job(self):
        proc, data = self.sb.wait_final()
        return data

    def no_sysup(self):
        self.assertFalse((self.sb.stub_dir / "sysup.started").exists())
        self.assertFalse((self.sb.state / "jobs").exists())


class NotAVerb(PullCase):
    def test_pull_is_not_an_ssh_verb(self):
        for cmd in ("pull", "run-pull", "check pull"):
            with self.subTest(cmd=cmd):
                proc = self.sb.run(cmd)
                self.assertEqual(proc.returncode, 1)
                self.assertEqual(proc.stdout, "")
                self.assertIn("REFUSED", self.sb.read("logger.log"))
        self.no_sysup()

    def test_env_pull_entry_refused_in_ssh_context(self):
        self.enable()
        for kwargs in ({"ssh": True}, {"command": "check"}, {"ssh": True, "command": "update"}):
            with self.subTest(**kwargs):
                proc = self.pull(**kwargs)
                self.assertEqual(proc.returncode, 1, (proc.stdout, proc.stderr))
                self.assertEqual(proc.stdout, "", "a refusal must not print a result")
        self.no_sysup()
        self.assertIn("REFUSED", self.sb.read("logger.log"))

    def test_env_pull_entry_refused_with_arguments_or_bad_value(self):
        self.enable()
        self.assertEqual(self.pull(args=("update",)).returncode, 1)
        self.assertEqual(self.pull({"FLEET_AGENT_PULL": "yes"}).returncode, 1)
        self.no_sysup()

    def test_production_context_keeps_pull_entry_refusal(self):
        # No test flag + sshd context: the variable is not stripped, it is refused.
        self.enable()
        proc = self.pull({"FLEET_AGENT_TEST": ""}, ssh=True)
        self.assertEqual(proc.returncode, 1)
        self.no_sysup()

    def test_verb_list_and_pull_source(self):
        text = agent_text()
        self.assertIn("check|update|reboot-status|reboot|report)", text)
        self.assertIsNone(re.search(r"^\s*'?pull'?\)", text, re.M | re.I))
        self.assertIsNone(re.search(r"^\s*'?ping'?\)", text, re.M | re.I))

    def test_pull_section_never_reaches_restart_code(self):
        block = pull_block()
        self.assertNotIn("verb_reboot", block)
        for word in ("systemctl", "shutdown", "sudo", "as_root"):
            self.assertNotIn(word, block)


class PullBehaviour(PullCase):
    def test_not_enabled_does_nothing(self):
        proc = self.pull()
        data = self.sb.json_of(proc)
        self.assertEqual((proc.returncode, data["status"], data["reason"]), (0, "skipped", "pull_not_enabled"))
        self.no_sysup()

    def test_recent_update_is_skipped(self):
        self.enable()
        self.last_success(days_ago=1)
        data = self.sb.json_of(self.pull())
        self.assertEqual((data["status"], data["reason"]), ("skipped", "recent_update"))
        self.no_sysup()
        self.assertFalse((self.sb.stub_dir / "curl.args").exists(), "no notification when nothing ran")

    def test_exactly_inside_window_is_skipped_and_outside_runs(self):
        self.enable()
        self.last_success(days_ago=6.9)
        self.assertEqual(self.sb.json_of(self.pull())["status"], "skipped")
        self.last_success(days_ago=7.1)
        self.assertEqual(self.sb.json_of(self.pull())["status"], "started")
        self.wait_job()
        self.assertTrue((self.sb.stub_dir / "sysup.started").exists())

    def test_never_updated_host_catches_up_and_notifies_priority_2(self):
        self.enable()
        proc = self.pull()
        data = self.sb.json_of(proc)
        self.assertEqual(data["status"], "started")
        final = self.wait_job()
        self.assertIn(final["status"], ("updated", "up-to-date"))
        for _ in range(50):
            if (self.sb.stub_dir / "curl.stdin").exists():
                break
            time.sleep(0.1)
        cfg = self.sb.read("curl.stdin")
        self.assertIn('header = "Priority: 2"', cfg)
        self.assertIn("pull-mode update", cfg)
        self.assertIn("https://ntfy.example.test/fleet", cfg)
        # token: only in the stdin config, never in argv / logs / state / stdout
        self.assertEqual(self.sb.read("curl.args").strip(), "-K -")
        self.assertNotIn(TOKEN, self.sb.read("curl.args"))
        self.assertNotIn(TOKEN, proc.stdout + proc.stderr)
        self.assertNotIn(TOKEN, self.sb.read("logger.log"))
        for f in self.sb.state.rglob("*"):
            if f.is_file():
                self.assertNotIn(TOKEN, f.read_text(errors="replace"), str(f))
        self.assertTrue((self.sb.state / "last-success").exists(), "success stamp for the next pull")

    def test_pull_never_restarts_even_when_required(self):
        self.enable()
        (self.sb.root / "reboot-required").write_text("")  # restart required
        self.sb.json_of(self.pull({"FLEET_AGENT_REBOOT_DELAY": "0"}))
        final = self.wait_job()
        self.assertTrue(final["reboot_required"])
        # the notification is the last thing the job does: wait for it, then check nothing restarted
        self.assertTrue(self.poll(lambda: "NOT done" in self.sb.read("curl.stdin")), "notification never sent")
        self.assertEqual(self.sb.read("sudo.log"), "", "pull must never call sudo")
        self.assertNotIn("reboot", self.sb.read("calls.log"))

    def test_denied_hosts(self):
        self.enable()
        cases = [
            ("guardian name", {"FLEET_AGENT_HOST": "bbh-dij-guardian"}, "pull_guardian"),
            ("proxmox", {"FLEET_AGENT_KIND": "proxmox"}, "pull_kind_proxmox"),
            ("omv", {"FLEET_AGENT_KIND": "omv"}, "pull_kind_omv"),
            ("pikvm", {"FLEET_AGENT_KIND": "pikvm"}, "pull_kind_pikvm"),
            ("guardian kind", {"FLEET_AGENT_KIND": "guardian"}, "pull_kind_guardian"),
        ]
        for label, env, reason in cases:
            with self.subTest(label):
                data = self.sb.json_of(self.pull(env))
                self.assertEqual((data["status"], data["reason"]), ("skipped", reason))
        (self.conf / "no-pull").write_text("")
        data = self.sb.json_of(self.pull())
        self.assertEqual(data["reason"], "pull_denied")
        self.no_sysup()

    def test_host_with_critical_services_is_denied(self):
        self.enable()
        (self.sb.root / "critical-services").write_text("cloudflared\n")
        data = self.sb.json_of(self.pull())
        self.assertEqual((data["status"], data["reason"]), ("skipped", "pull_critical_services"))
        self.no_sysup()
        # an empty file does not make the host critical
        (self.sb.root / "critical-services").write_text("")
        self.assertEqual(self.sb.json_of(self.pull())["status"], "started")
        self.wait_job()

    def test_last_success_parsing_is_strict(self):
        self.enable()
        now = int(time.time())
        cases = {
            "garbage": "abc",
            "empty": "",
            "too many digits": str(now) + "000000",
            "zero padded old": "0000000008",
            "future": str(now + 10 * 86400),
        }
        for label, content in cases.items():
            with self.subTest(label):
                self.sb.state.mkdir(parents=True, exist_ok=True)
                (self.sb.state / "last-success").write_text(content + "\n")
                proc = self.pull()
                data = self.sb.json_of(proc)
                self.assertEqual(data["status"], "started", (label, proc.stderr))
                self.wait_job()
                self.reset_state()
        # a zero-padded RECENT stamp still counts as recent (no octal misparse)
        self.sb.state.mkdir(parents=True, exist_ok=True)
        (self.sb.state / "last-success").write_text("0" + str(now - 3600) + "\n")
        self.assertEqual(self.sb.json_of(self.pull())["reason"], "recent_update")

    def test_token_only_to_https_or_exact_loopback(self):
        cases = [
            ("https://ntfy.example.test", True),
            ("http://127.0.0.1", True),
            ("http://127.0.0.1:8080", True),
            ("http://localhost/", True),
            ("http://localhost:2586", True),
            ("http://127.0.0.1.evil.com", False),
            ("http://localhost.evil.com", False),
            ("http://127.0.0.10", False),
            ("http://ntfy.example.test", False),
        ]
        for url, allowed in cases:
            with self.subTest(url=url):
                self.enable_url(url)
                self.assertEqual(self.sb.json_of(self.pull())["status"], "started")
                self.wait_job()
                self.assertTrue(self.poll(lambda: (self.sb.stub_dir / "curl.stdin").exists()), "no notification")
                cfg = self.sb.read("curl.stdin")
                self.assertIn(f"url = \"{url.rstrip(chr(47))}/fleet\"", cfg)
                self.assertEqual("Authorization: Bearer" in cfg, allowed, cfg)
                self.assertNotIn(TOKEN, self.sb.read("curl.args"))
                self.reset_state()

    def test_failed_pull_backs_off_24h_and_notifies_once(self):
        self.enable()
        self.assertEqual(self.sb.json_of(self.pull({"STUB_SYSUP_RC": "4"}))["status"], "started")
        self.assertEqual(self.wait_job()["status"], "failed")
        self.assertTrue(self.poll(lambda: (self.sb.stub_dir / "curl.stdin").exists()))
        self.assertTrue((self.sb.state / "last-attempt").exists())
        notified = self.sb.read("curl.args").count("-K -")
        for _ in range(2):
            data = self.sb.json_of(self.pull())
            self.assertEqual((data["status"], data["reason"]), ("skipped", "pull_backoff"))
        self.assertEqual(self.sb.read("curl.args").count("-K -"), notified, "no notification during backoff")
        self.assertEqual(self.sb.read("calls.log").count("sysup"), 1, "no retry during backoff")
        # 25 h later the next pull may retry
        (self.sb.state / "last-attempt").write_text(str(int(time.time()) - 25 * 3600) + "\n")
        self.assertEqual(self.sb.json_of(self.pull())["status"], "started")
        self.wait_job()

    def test_pull_update_has_a_hard_timeout_systemd(self):
        self.enable()
        self.sb.json_of(self.pull())
        self.wait_job()
        self.assertIn("RuntimeMaxSec=7200", self.sb.read("systemd-run.log"))

    def test_pull_update_has_a_hard_timeout_without_systemd(self):
        # macOS path: watchdog subshell kills a hung update, the lock does not stay held forever.
        self.enable()
        env = {"FLEET_AGENT_NO_SYSTEMD_RUN": "1", "FLEET_AGENT_JOB_MAX_SECS": "2", "STUB_SYSUP_SLEEP": "60"}
        self.assertEqual(self.sb.json_of(self.pull(env))["status"], "started")
        self.assertFalse((self.sb.stub_dir / "systemd-run.log").exists())

        def died():
            data = self.sb.json_of(self.sb.run("report"))
            return data["status"] == "failed" and data["reason"] == "job_died"

        self.assertTrue(self.poll(died, 15), "hung update was not terminated by the watchdog")
        data = self.sb.json_of(self.pull())
        self.assertEqual((data["status"], data["reason"]), ("skipped", "pull_backoff"))

    def test_pull_log_is_capped(self):
        log = self.sb.root / "fleet-pull.log"
        log.write_text("x" * 100 + "\n" * 1 + ("line of log output\n" * 80000))
        self.assertGreater(log.stat().st_size, 1048576)
        self.pull({"FLEET_AGENT_PULL_LOG": str(log)})
        self.assertLess(log.stat().st_size, 100000)
    def test_busy_when_a_normal_update_holds_the_lock(self):
        self.enable()
        first = self.sb.json_of(self.sb.run("update", {"STUB_SYSUP_SLEEP": "2"}))
        self.assertEqual(first["status"], "started")
        proc = self.pull()
        data = self.sb.json_of(proc)
        self.assertEqual(data["status"], "busy")
        self.assertEqual(proc.returncode, 0, "pull mode must not fail the timer unit on busy")
        self.sb.wait_final()

    def test_lock_race_20x(self):
        # Three pull runs released together by a start barrier: exactly one job starts, two are busy.
        self.enable()
        env = {k: v for k, v in self.sb.env.items() if k != "SSH_CONNECTION"}
        env.update({"FLEET_AGENT_PULL": "1", "STUB_SYSUP_SLEEP": "2"})
        for round_no in range(20):
            barrier = self.sb.root / f"barrier-{round_no}"
            procs = [
                subprocess.Popen(
                    ["bash", "-c", 'while [ ! -e "$1" ]; do sleep 0.005; done; exec bash "$2"', "race", str(barrier), str(AGENT)],
                    env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, stdin=subprocess.DEVNULL,
                )
                for _ in range(3)
            ]
            barrier.write_text("go")
            results = []
            for p in procs:
                out, _err = p.communicate(timeout=30)
                results.append((p.returncode, json.loads(out.splitlines()[0])["status"]))
            statuses = [st for _rc, st in results]
            self.assertEqual(statuses.count("started"), 1, results)
            self.assertEqual(statuses.count("busy"), 2, results)
            self.assertEqual({rc for rc, _st in results}, {0}, "busy is not an error in pull mode")
            self.sb.wait_final()
            self.reset_state()


class MacosChecks(PullCase):
    def test_disabled_native_auto_updates_are_reported(self):
        ta.Sandbox._script(
            self.sb.bin / "defaults",
            '#!/usr/bin/env bash\necho "defaults $*" >> "$STUB_DIR/calls.log"\n'
            'case "$3" in AutomaticDownload) echo 0 ;; CriticalUpdateInstall) echo 1 ;; *) exit 1 ;; esac\n',
        )
        proc = self.sb.run("check", {"FLEET_AGENT_SWUPDATE_DOMAIN": "/tmp/com.apple.SoftwareUpdate"})
        data = self.sb.json_of(proc)
        self.assertEqual(data["config_conflicts"], ["macos_auto_updates_off: AutomaticDownload"])

    def test_not_checked_on_linux_without_domain(self):
        ta.Sandbox._script(self.sb.bin / "defaults", '#!/usr/bin/env bash\necho 0\n')
        data = self.sb.json_of(self.sb.run("check"))
        self.assertEqual(data["config_conflicts"], [])

    def test_agent_never_installs_macos_itself(self):
        text = agent_text()
        self.assertIsNone(re.search(r"softwareupdate\s+(-i|--install|-a)", text))
        self.assertIsNone(re.search(r"\bsoftwareupdate\b[^\n]*\binstall", text))

    def test_bash32_constructs_absent_from_pull_section(self):
        block = pull_block()
        for pattern in (r"\$\{[A-Za-z_]+,,", r"\$\{[A-Za-z_]+\^\^", r"\bmapfile\b", r"\breadarray\b", r"declare -A"):
            self.assertIsNone(re.search(pattern, block), pattern)


@unittest.skipUnless(shutil.which("systemd-analyze"), "systemd-analyze not available")
class SystemdUnits(unittest.TestCase):
    def test_units_verify(self):
        scratch = Path(os.environ.get("TMPDIR", "/tmp")) / f"fleet-pull-units-{os.getpid()}"
        unit_dir = scratch / ".config/systemd/user"
        unit_dir.mkdir(parents=True)
        self.addCleanup(shutil.rmtree, scratch, True)
        for name in ("fleet-pull.service", "fleet-pull.timer"):
            shutil.copy(UNIT_DIR / name, unit_dir / name)
        env = dict(os.environ, HOME=str(scratch), XDG_CONFIG_HOME=str(scratch / ".config"))
        proc = subprocess.run(
            ["systemd-analyze", "--user", "verify", str(unit_dir / "fleet-pull.service"), str(unit_dir / "fleet-pull.timer")],
            env=env, capture_output=True, text=True, timeout=60,
        )
        # The agent path does not exist in the scratch HOME: only that warning is tolerated.
        bad = [ln for ln in proc.stderr.splitlines() if ln.strip() and "/usr/local/libexec/fleet-agent" not in ln]
        self.assertEqual(bad, [], proc.stderr)

    def test_service_is_local_pull_entry_only(self):
        svc = (UNIT_DIR / "fleet-pull.service").read_text()
        self.assertIn("Environment=FLEET_AGENT_PULL=1", svc)
        self.assertIn("ExecStart=/usr/local/libexec/fleet-agent\n", svc)
        self.assertIn("ConditionPathExists=%h/.config/fleet-agent/pull-enabled", svc)
        self.assertIn("ConditionACPower", svc)
        self.assertNotRegex(svc, r"(?i)reboot|systemctl|shutdown")
        self.assertNotIn("network-online", svc)  # no effect in the user manager
        self.assertIn("Nice=19", svc)
        self.assertIn("IOSchedulingClass=idle", svc)
        self.assertNotIn("NoNewPrivileges", svc)
        timer = (UNIT_DIR / "fleet-pull.timer").read_text()
        self.assertIn("Persistent=true", timer)
        self.assertIn("Unit=fleet-pull.service", timer)


@unittest.skipUnless(shutil.which("chezmoi"), "chezmoi not available")
class LaunchdPlist(unittest.TestCase):
    def render(self):
        # The template is gated on darwin; render it as if on a Mac (only the gate changes).
        src = PLIST.read_text()
        self.assertIn('eq .chezmoi.os "darwin"', src)
        src = src.replace('eq .chezmoi.os "darwin"', 'ne .chezmoi.os "darwin-never"')
        proc = subprocess.run(
            ["chezmoi", "execute-template"], input=src, capture_output=True, text=True,
            timeout=60, cwd=str(ROOT),
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return proc.stdout

    def test_renders_valid_plist(self):
        import plistlib
        data = plistlib.loads(self.render().encode())
        self.assertEqual(data["Label"], "com.jsoyer.fleet-pull")
        self.assertEqual(data["ProgramArguments"], ["/usr/local/libexec/fleet-agent"])
        self.assertEqual(data["EnvironmentVariables"]["FLEET_AGENT_PULL"], "1")
        self.assertIn("StartInterval", data)
        self.assertTrue(data["RunAtLoad"])
        self.assertNotIn("Authorization", json.dumps(data, default=str))
        # the detached update must survive the end of this short launchd run
        self.assertIs(data["AbandonProcessGroup"], True)
        self.assertEqual(data["ProcessType"], "Background")
        self.assertIs(data["LowPriorityIO"], True)


if __name__ == "__main__":
    unittest.main()
