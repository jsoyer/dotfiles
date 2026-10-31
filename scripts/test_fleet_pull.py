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
        # The only caller of the restart verb is the SSH verb dispatch.
        self.assertEqual(len(re.findall(r"\bverb_reboot\b", agent_text())), 3)  # def, comment-free call, dispatch


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
        time.sleep(0.5)
        self.assertEqual(self.sb.read("sudo.log"), "", "pull must never call sudo")
        self.assertNotIn("reboot", self.sb.read("calls.log"))
        self.assertIn("NOT done", self.sb.read("curl.stdin"))

    def test_denied_hosts(self):
        self.enable()
        cases = [
            ("guardian name", {"FLEET_AGENT_HOST": "bbh-dij-guardian"}, "pull_guardian"),
            ("proxmox", {"FLEET_AGENT_KIND": "proxmox"}, "pull_kind_proxmox"),
            ("omv", {"FLEET_AGENT_KIND": "omv"}, "pull_kind_omv"),
            ("pikvm", {"FLEET_AGENT_KIND": "pikvm"}, "pull_kind_pikvm"),
        ]
        for label, env, reason in cases:
            with self.subTest(label):
                data = self.sb.json_of(self.pull(env))
                self.assertEqual((data["status"], data["reason"]), ("skipped", reason))
        (self.conf / "no-pull").write_text("")
        data = self.sb.json_of(self.pull())
        self.assertEqual(data["reason"], "pull_pull_denied")
        self.no_sysup()

    def test_busy_when_a_normal_update_holds_the_lock(self):
        self.enable()
        first = self.sb.json_of(self.sb.run("update", {"STUB_SYSUP_SLEEP": "2"}))
        self.assertEqual(first["status"], "started")
        data = self.sb.json_of(self.pull())
        self.assertEqual(data["status"], "busy")
        self.sb.wait_final()

    def test_lock_race_20x(self):
        # Many pull runs at once: exactly one job starts, the rest are busy.
        self.enable()
        for _ in range(20):
            procs = [
                subprocess.Popen(
                    ["bash", str(AGENT)],
                    env={**{k: v for k, v in self.sb.env.items() if k != "SSH_CONNECTION"},
                         "FLEET_AGENT_PULL": "1", "STUB_SYSUP_SLEEP": "1"},
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, stdin=subprocess.DEVNULL,
                )
                for _ in range(3)
            ]
            statuses = []
            for p in procs:
                out, _err = p.communicate(timeout=30)
                statuses.append(json.loads(out.splitlines()[0])["status"])
            self.assertEqual(statuses.count("started"), 1, statuses)
            self.sb.wait_final()
            shutil.rmtree(self.sb.state, ignore_errors=True)


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


if __name__ == "__main__":
    unittest.main()
