#!/usr/bin/env python3
"""T3 Code and Paseo command sets (thin wrappers around the upstream CLIs).

Every script runs against a temp HOME with fake t3/paseo/systemctl/loginctl/
tailscale/npm/node/sudo/curl/mise executables on PATH that log their argv, so we
assert WHICH upstream commands are invoked, never touching the real machine.
Python 3.9-compatible, stdlib only.
"""

import os
import shutil
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BIN = ROOT / "dot_local/bin"

T3_SCRIPTS = [
    "t3-setup",
    "update-t3",
    "t3-health",
    "t3-pair",
    "t3-version",
    "t3-uninstall",
]
PASEO_SCRIPTS = [
    "paseo-setup",
    "update-paseo",
    "paseo-pair",
    "paseo-version",
    "paseo-uninstall",
]
ALL_SCRIPTS = T3_SCRIPTS + PASEO_SCRIPTS
CORE_TOOLS = (
    "bash sh sed grep awk cat cut head tail tr dirname basename mkdir rmdir rm mv cp "
    "chmod stat cmp mktemp date hostname id uname sleep env printf ls sort uniq "
    "readlink wc"
).split()

# Generic logger: every stub appends "<name> <argv>" to $STUB_LOG.
LOGGER = '#!/bin/sh\necho "$(basename "$0") $*" >> "$STUB_LOG"\n'

STUBS = {
    "t3": LOGGER
    + r"""
case "$1" in
  --version) cat "$STUB_DIR/t3.version"; exit 0 ;;
  update) echo 0.0.2 > "$STUB_DIR/t3.version"; exit 0 ;;
  status) echo '{"status":"running"}'; exit 0 ;;
esac
exit 0
""",
    "paseo": LOGGER
    + r"""
case "$1" in
  --version) cat "$STUB_DIR/paseo.version"; exit 0 ;;
esac
exit 0
""",
    "systemctl": LOGGER
    + r"""
case "$*" in
  *show-environment*) exit 0 ;;
  *is-active*) if [ -n "$STUB_ACTIVE" ]; then echo active; exit 0; fi; echo inactive; exit 3 ;;
  *NRestarts*) echo 0; exit 0 ;;
esac
exit 0
""",
    "loginctl": LOGGER + 'echo "Linger=no"\n',
    "tailscale": LOGGER + "echo 100.64.0.7\n",
    "npm": LOGGER
    + r"""
case "$*" in
  *"@getpaseo/cli@latest"*) echo 0.18.0 > "$STUB_DIR/paseo.version" ;;
  *"@getpaseo/cli@0.17.4"*) echo 0.17.4 > "$STUB_DIR/paseo.version" ;;
  view*) echo 0.18.0 ;;
esac
exit 0
""",
    "node": LOGGER + "echo v22.3.0\n",
    "sudo": LOGGER,
    "curl": LOGGER + 'echo "echo stub-installer"\n',
    "mise": LOGGER,
    "agent-alert": LOGGER,
    # Smoke tests called by the updaters: exit code driven by $SMOKE_RC.
    "t3-health": LOGGER + 'exit "${SMOKE_RC:-0}"\n',
}


class Sandbox:
    """Temp HOME + stub bin dir; `run()` executes a script from the repo."""

    def __init__(self, omit=(), extra_env=None):
        self.tmp = Path(tempfile.mkdtemp(prefix="t3paseo-"))
        self.home = self.tmp / "home"
        self.stubs = self.tmp / "stubs"
        self.home.mkdir()
        self.stubs.mkdir()
        # Whitelisted core tools only: the real tailscale/node/mise/systemctl of the
        # host must stay invisible, otherwise `omit=` could not simulate absence.
        self.tools = self.tmp / "tools"
        self.tools.mkdir()
        for tool in CORE_TOOLS:
            found = shutil.which(tool)
            if found:
                os.symlink(found, str(self.tools / tool))
        self.log = self.tmp / "calls.log"
        self.log.write_text("")
        (self.stubs / "t3.version").write_text("0.0.1\n")
        (self.stubs / "paseo.version").write_text("0.17.4\n")
        for name, body in STUBS.items():
            if name in omit:
                continue
            path = self.stubs / name
            path.write_text(body)
            path.chmod(path.stat().st_mode | stat.S_IXUSR)
        self.env = {
            "HOME": str(self.home),
            "PATH": "%s:%s" % (self.stubs, self.tools),
            "STUB_LOG": str(self.log),
            "STUB_DIR": str(self.stubs),
            "XDG_RUNTIME_DIR": str(self.tmp),
            "LANG": "C",
        }
        self.env.update(extra_env or {})

    def run(self, script, *args, stdin=""):
        return subprocess.run(
            ["bash", str(BIN / ("executable_" + script)), *args],
            env=self.env,
            input=stdin,
            capture_output=True,
            text=True,
            timeout=120,
        )

    def calls(self):
        return self.log.read_text()

    def cleanup(self):
        shutil.rmtree(str(self.tmp), ignore_errors=True)


class SandboxCase(unittest.TestCase):
    def sandbox(self, **kw):
        sb = Sandbox(**kw)
        self.addCleanup(sb.cleanup)
        return sb


class Static(SandboxCase):
    def test_bash_syntax(self):
        for name in ALL_SCRIPTS:
            r = subprocess.run(
                ["bash", "-n", str(BIN / ("executable_" + name))],
                capture_output=True,
                text=True,
            )
            self.assertEqual(r.returncode, 0, "%s: %s" % (name, r.stderr))

    def test_scripts_stay_small(self):
        for name in ALL_SCRIPTS:
            n = len((BIN / ("executable_" + name)).read_text().splitlines())
            self.assertLess(n, 400, name)

    def test_help_exits_zero(self):
        for name in ALL_SCRIPTS:
            sb = Sandbox()
            self.addCleanup(sb.cleanup)
            r = sb.run(name, "--help")
            self.assertEqual(r.returncode, 0, "%s: %s" % (name, r.stderr))
            self.assertIn(
                "Usage", r.stdout + r.stderr, name
            ) if "uninstall" in name or "setup" in name else None
            self.assertEqual(sb.calls(), "", "%s --help must not call anything" % name)

    def test_unknown_option_rejected(self):
        for name in ("t3-setup", "paseo-setup", "t3-uninstall", "paseo-uninstall"):
            sb = self.sandbox()
            self.assertNotEqual(sb.run(name, "--bogus").returncode, 0, name)


class T3Setup(SandboxCase):
    def test_dry_run_prints_upstream_commands_and_changes_nothing(self):
        sb = self.sandbox()
        r = sb.run(
            "t3-setup", "--dry-run", "--lan", "--port", "3773", "--update-at", "04:30"
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        out = r.stdout
        self.assertIn("t3 service install", out)
        self.assertIn("sudo loginctl enable-linger", out)
        self.assertIn(
            "systemctl --user enable --now t3-health.timer t3-update.timer", out
        )
        self.assertIn("T3CODE_LAN=true", out)
        self.assertIn("T3CODE_PORT=3773", out)
        self.assertNotIn("t3 service install", sb.calls())  # printed, not executed
        self.assertFalse((sb.home / ".t3").exists())
        self.assertFalse((sb.home / ".config").exists())

    def test_dry_run_installs_cli_when_missing(self):
        sb = self.sandbox(omit=("t3",))
        r = sb.run("t3-setup", "--dry-run")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("curl -fsSL https://t3.codes/install.sh | sh", r.stdout)

    def test_real_run_writes_env_0600_and_units(self):
        sb = self.sandbox()
        r = sb.run(
            "t3-setup",
            "--lan",
            "--port",
            "3773",
            "--host",
            "100.64.0.7",
            "--update-at",
            "04:30",
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        env_file = sb.home / ".t3/service.env"
        self.assertEqual(stat.S_IMODE(env_file.stat().st_mode), 0o600)
        lines = env_file.read_text().splitlines()
        for want in ("T3CODE_LAN=true", "T3CODE_PORT=3773", "T3CODE_HOST=100.64.0.7"):
            self.assertIn(want, lines)
        calls = sb.calls()
        self.assertIn("t3 service install", calls)
        self.assertIn("t3 service restart", calls)  # env changed -> restart
        self.assertIn("sudo loginctl enable-linger", calls)
        units = sb.home / ".config/systemd/user"
        self.assertIn(
            "OnFailure=t3-alert@%n.service",
            (units / "t3code.service.d/zz-alert.conf").read_text(),
        )
        self.assertIn(
            "OnCalendar=*-*-* 04:30:00", (units / "t3-update.timer").read_text()
        )
        dropin = (units / "t3code.service.d/zz-user-path.conf").read_text()
        self.assertIn("%h/.local/share/mise/shims:%h/.local/bin:%h/.grok/bin", dropin)
        for var in ("MISE_DATA_DIR", "MISE_CONFIG_DIR", "MISE_STATE_DIR", "MISE_CACHE_DIR"):
            self.assertIn(f'"{var}=%h/', dropin)
        # The restart comes after daemon-reload, so it picks up the drop-ins.
        self.assertLess(calls.index("systemctl --user daemon-reload"),
                        calls.rindex("t3 service restart"))
        self.assertIn(
            "ExecStart=%h/.local/bin/update-t3",
            (units / "t3-update.service").read_text(),
        )

    def _opencode_sandbox(self, instance):
        import json
        sb = self.sandbox()
        os.symlink(shutil.which("python3"), str(sb.tools / "python3"))
        oc2 = sb.stubs / "opencode2"
        oc2.write_text("#!/bin/sh\nexit 0\n")
        oc2.chmod(0o755)
        settings = sb.home / ".t3/userdata/settings.json"
        settings.parent.mkdir(parents=True)
        settings.write_text(json.dumps({"providerInstances": {"opencode": instance}}))
        return sb, oc2, settings

    def test_opencode_instance_pointed_at_opencode2(self):
        import json
        sb, oc2, settings = self._opencode_sandbox({"driver": "opencode", "enabled": True})
        r = sb.run("t3-setup")
        self.assertEqual(r.returncode, 0, r.stderr)
        inst = json.loads(settings.read_text())["providerInstances"]["opencode"]
        self.assertEqual(inst["config"]["binaryPath"], str(oc2))
        self.assertEqual(stat.S_IMODE(settings.stat().st_mode), 0o600)
        self.assertTrue((settings.parent / "settings.json.bak-t3-setup").exists())
        calls = sb.calls()
        self.assertIn("systemctl --user stop t3code.service", calls)  # edited while stopped
        self.assertIn("t3 service restart", calls)

    def test_opencode_binary_path_set_by_hand_is_kept(self):
        import json
        sb, oc2, settings = self._opencode_sandbox(
            {"driver": "opencode", "config": {"binaryPath": "/opt/my-opencode"}})
        r = sb.run("t3-setup")
        self.assertEqual(r.returncode, 0, r.stderr)
        inst = json.loads(settings.read_text())["providerInstances"]["opencode"]
        self.assertEqual(inst["config"]["binaryPath"], "/opt/my-opencode")
        self.assertNotIn("systemctl --user stop t3code.service", sb.calls())

    def test_env_update_replaces_key_and_keeps_others(self):
        sb = self.sandbox()
        sb.run("t3-setup", "--lan", "--port", "3773")
        r = sb.run("t3-setup", "--port", "4000")
        self.assertEqual(r.returncode, 0, r.stderr)
        env_file = sb.home / ".t3/service.env"
        lines = env_file.read_text().splitlines()
        self.assertEqual(lines.count("T3CODE_PORT=4000"), 1)
        self.assertNotIn("T3CODE_PORT=3773", lines)
        self.assertIn("T3CODE_LAN=true", lines)
        self.assertEqual(stat.S_IMODE(env_file.stat().st_mode), 0o600)

    def test_rejects_unsafe_values(self):
        sb = self.sandbox()
        self.assertNotEqual(
            sb.run("t3-setup", "--dry-run", "--port", "99999").returncode, 0
        )
        self.assertNotEqual(
            sb.run("t3-setup", "--dry-run", "--host", "a\nB=c").returncode, 0
        )
        self.assertNotEqual(
            sb.run("t3-setup", "--dry-run", "--update-at", "25:00").returncode, 0
        )

    def test_uninstall_uses_upstream(self):
        sb = self.sandbox()
        r = sb.run("t3-setup", "--uninstall", "-y")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("t3 service uninstall", sb.calls())


class T3Wrappers(SandboxCase):
    def test_pair_passes_arguments_through(self):
        sb = self.sandbox()
        self.assertEqual(sb.run("t3-pair", "--tailscale").returncode, 0)
        self.assertIn("t3 pair --tailscale", sb.calls())

    def test_update_restarts_on_version_change_and_smokes(self):
        sb = self.sandbox()
        r = sb.run("update-t3")
        self.assertEqual(r.returncode, 0, r.stderr)
        calls = sb.calls()
        self.assertIn("t3 update --yes", calls)
        self.assertIn("t3 service restart", calls)
        self.assertIn("t3-health", calls)

    def test_update_fails_when_smoke_fails(self):
        sb = self.sandbox(extra_env={"SMOKE_RC": "1"})
        r = sb.run("update-t3")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("--allow-downgrade", r.stderr)

    def test_health_reports_inactive_service(self):
        sb = self.sandbox()
        r = sb.run("t3-health")
        self.assertEqual(r.returncode, 1)
        self.assertIn("<3>T3 Code down", r.stdout)
        self.assertIn("agent-alert --title T3 Code down on", sb.calls())
        self.assertIn("--priority high", sb.calls())

    def test_health_ok_when_active(self):
        sb = self.sandbox(extra_env={"STUB_ACTIVE": "1"})
        r = sb.run("t3-health")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("t3 status --json", sb.calls())

    def test_health_warns_on_restart_pending(self):
        sb = self.sandbox(extra_env={"STUB_ACTIVE": "1"})
        (sb.stubs / "t3").write_text(
            STUBS["t3"].replace('{"status":"running"}', '{"status":"restart-pending"}')
        )
        r = sb.run("t3-health")
        self.assertEqual(r.returncode, 0)
        self.assertIn("<4>T3 Code warning", r.stdout)

    def test_version_tolerates_missing_fields(self):
        sb = self.sandbox()
        r = sb.run("t3-version")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("0.0.1", r.stdout)

    def test_uninstall_keeps_data_unless_purge(self):
        sb = self.sandbox()
        (sb.home / ".t3").mkdir()
        (sb.home / ".t3/service.env").write_text("T3CODE_PORT=1\n")
        self.assertEqual(sb.run("t3-uninstall", "-y").returncode, 0)
        calls = sb.calls()
        self.assertIn("t3 service uninstall", calls)
        self.assertIn("t3 uninstall", calls)
        self.assertTrue((sb.home / ".t3").exists())
        self.assertEqual(sb.run("t3-uninstall", "-y", "--purge").returncode, 0)
        self.assertFalse((sb.home / ".t3").exists())


class PaseoHelpers(SandboxCase):
    """Helpers around the #71 system-scope Paseo server (paseo-setup is #71's)."""

    def test_pair_passes_arguments_through(self):
        sb = self.sandbox()
        self.assertEqual(sb.run("paseo-pair", "--relay").returncode, 0)
        self.assertIn("paseo daemon pair --relay", sb.calls())

    def test_pair_status_delegates_to_paseo_setup(self):
        sb = self.sandbox()
        (sb.stubs / "paseo-setup").write_text(LOGGER)
        (sb.stubs / "paseo-setup").chmod(0o755)
        self.assertEqual(sb.run("paseo-pair", "--status").returncode, 0)
        self.assertIn("paseo-setup --status", sb.calls())

    def test_update_is_a_thin_wrapper_over_agents_update(self):
        sb = self.sandbox()
        (sb.stubs / "agents-update").write_text(
            LOGGER + 'echo "restart_on=$AGENTS_UPDATE_RESTART_ON" >> "$STUB_LOG"\n'
        )
        (sb.stubs / "agents-update").chmod(0o755)
        r = sb.run("update-paseo", "--dry-run")
        self.assertEqual(r.returncode, 0, r.stderr)
        calls = sb.calls()
        self.assertIn("agents-update --dry-run", calls)
        self.assertIn("restart_on=paseo=paseo.service", calls)
        self.assertNotIn("npm install", calls)  # no duplicated update logic

    def test_update_propagates_agents_update_failure(self):
        sb = self.sandbox()
        (sb.stubs / "agents-update").write_text(LOGGER + "exit 3\n")
        (sb.stubs / "agents-update").chmod(0o755)
        self.assertEqual(sb.run("update-paseo").returncode, 3)

    def test_version_reports_installed_and_latest(self):
        sb = self.sandbox()
        r = sb.run("paseo-version")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("0.17.4", r.stdout)
        self.assertIn("0.18.0", r.stdout)

    def test_uninstall_runs_paseo_setup_and_keeps_data_unless_purge(self):
        sb = self.sandbox()
        (sb.stubs / "paseo-setup").write_text(LOGGER)
        (sb.stubs / "paseo-setup").chmod(0o755)
        (sb.home / ".paseo").mkdir()
        self.assertEqual(sb.run("paseo-uninstall", "-y").returncode, 0)
        self.assertIn("paseo-setup --uninstall", sb.calls())
        self.assertTrue((sb.home / ".paseo").exists())
        self.assertEqual(sb.run("paseo-uninstall", "-y", "--purge").returncode, 0)
        self.assertFalse((sb.home / ".paseo").exists())

    def test_uninstall_without_paseo_setup_removes_units_by_hand(self):
        sb = self.sandbox()
        self.assertEqual(sb.run("paseo-uninstall", "-y").returncode, 0)
        calls = sb.calls()
        self.assertIn(
            "systemctl disable --now paseo-health.timer paseo.service paseo-firewall.service",
            calls,
        )
        self.assertNotIn("npm uninstall", calls)


class Integration(unittest.TestCase):
    def test_agentsvc_knows_both_targets(self):
        text = (BIN / "executable_agentsvc").read_text()
        for needle in (
            "t3code.service",
            "paseo.service",
            "t3|paseo",
            "update-t3",
            "update-paseo",
        ):
            self.assertIn(needle, text)

    def test_linux_only_ignore_and_macos_cleanup(self):
        ignore = (ROOT / ".chezmoiignore.tmpl").read_text()
        cleanup = (
            ROOT
            / ".chezmoiscripts/02-install/run_once_12-disable-macos-agent-stacks.sh.tmpl"
        ).read_text()
        for name in ALL_SCRIPTS:
            self.assertIn(".local/bin/" + name, ignore, name)
            self.assertIn(".local/bin/" + name + '"', cleanup, name)

    def test_casks_present_in_mac_host_overlay(self):
        # Brewfile_personal / Brewfile_pro are frozen legacy manifests
        # (sha256-pinned in docs/PACKAGE_BASELINE_2026-11-14.json): new casks go
        # to the host overlay, next to the Orca cask.
        text = (ROOT / "dot_private" / "Brewfile_JeromeSacMiniM6").read_text()
        self.assertIn('cask "stablyai/orca/orca"', text)
        self.assertIn('cask "t3-code"', text)
        self.assertIn('cask "paseo"', text)


if __name__ == "__main__":
    unittest.main()
