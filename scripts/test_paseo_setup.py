#!/usr/bin/env python3
"""paseo-setup guarantees, and the agents-update daemon restart hook."""

import os
import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SETUP_PATH = ROOT / "dot_local/bin/executable_paseo-setup"
UPDATE_PATH = ROOT / "dot_local/bin/executable_agents-update"
SETUP = SETUP_PATH.read_text()
UPDATE = UPDATE_PATH.read_text()


class PaseoSetup(unittest.TestCase):
    def test_parses(self):
        subprocess.run(["bash", "-n", str(SETUP_PATH)], check=True)

    def test_firewall_fails_closed(self):
        self.assertIn('tcp dport ${PORT} iifname != { "lo", "tailscale0" } drop', SETUP)
        self.assertIn("Requires=paseo-firewall.service", SETUP)
        self.assertIn("After=paseo-firewall.service", SETUP)

    def test_relay_off_web_ui_on(self):
        self.assertIn("daemon.relay.enabled false", SETUP)
        # The web UI is useful: keep it on, protect it instead.
        self.assertIn("features.webUi.enabled true", SETUP)
        self.assertNotIn("features.webUi.enabled false", SETUP)

    def test_unit_environment(self):
        self.assertIn("${SVC_HOME}/.local/share/mise/shims:${SVC_HOME}/.local/bin:${SVC_HOME}/.grok/bin", SETUP)
        for var in ("MISE_DATA_DIR", "MISE_CONFIG_DIR", "MISE_STATE_DIR", "MISE_CACHE_DIR"):
            self.assertIn(f'"{var}=${{SVC_HOME}}/', SETUP)
        self.assertIn("daemon run --home", SETUP)

    def test_no_start_without_password(self):
        self.assertIn("No Paseo password yet: not starting", SETUP)
        self.assertIn("--allow-no-password", SETUP)

    def test_rejects_bad_arguments(self):
        for args in (["--user", "Bad User"], ["--port", "80", "--user", "ok"], ["--bogus"]):
            with self.subTest(args=args):
                r = subprocess.run(
                    ["bash", str(SETUP_PATH), *args],
                    capture_output=True, text=True, check=False,
                    env=dict(os.environ, PATH="/usr/bin:/bin"),
                )
                self.assertNotEqual(r.returncode, 0)



def run_trusted_source(script_text, setup_uid_env, make):
    """Extract trusted_source() from a setup script and run it on a temp file.

    `make(dir_path, file_path)` adjusts modes/links; returns True if accepted.
    """
    import os
    import subprocess
    import tempfile

    start = script_text.index("trusted_source() {")
    func = script_text[start:script_text.index("\n}\n", start) + 3]
    with tempfile.TemporaryDirectory() as tmp:
        d = os.path.join(tmp, "bin")
        os.mkdir(d)
        os.chmod(d, 0o755)
        f = os.path.join(d, "helper")
        with open(f, "w") as fh:
            fh.write("#!/bin/sh\n")
        os.chmod(f, 0o644)
        target = make(d, f) or f
        env = {"PATH": os.environ["PATH"]}
        env.update(setup_uid_env)
        r = subprocess.run(["bash", "-c", func + '\ntrusted_source "$1"', "_", target],
                           env=env, capture_output=True, text=True)
        return r.returncode == 0


class TrustedSource:
    """Root-run helpers must come only from admin/root-owned, non-writable paths."""

    SCRIPT = None  # set by subclasses

    def check(self, env, make=lambda d, f: None):
        return run_trusted_source(self.SCRIPT, env, make)

    def test_owner_is_invoking_admin_and_not_writable(self):
        import os
        self.assertTrue(self.check({"SUDO_UID": str(os.getuid())}))

    def test_group_or_world_writable_file_refused(self):
        import os
        for mode in (0o666, 0o664, 0o646):
            with self.subTest(mode=oct(mode)):
                self.assertFalse(self.check({"SUDO_UID": str(os.getuid())},
                                            lambda d, f, m=mode: os.chmod(f, m)))

    def test_writable_directory_refused(self):
        import os
        for mode in (0o777, 0o775, 0o757):
            with self.subTest(mode=oct(mode)):
                self.assertFalse(self.check({"SUDO_UID": str(os.getuid())},
                                            lambda d, f, m=mode: os.chmod(d, m)))

    def test_symlink_refused(self):
        import os

        def link(d, f):
            ln = os.path.join(d, "link")
            os.symlink(f, ln)
            return ln

        self.assertFalse(self.check({"SUDO_UID": str(os.getuid())}, link))

    def test_unknown_non_root_owner_refused(self):
        import os
        if os.geteuid() == 0:
            self.skipTest("running as root: root-owned files are trusted")
        # No SUDO_UID, owner is a regular user: not trusted.
        self.assertFalse(self.check({}))
        # SUDO_UID of somebody else: not trusted either.
        self.assertFalse(self.check({"SUDO_UID": str(os.getuid() + 12345)}))


class PaseoTrustedSource(TrustedSource, unittest.TestCase):
    SCRIPT = SETUP

    def test_agent_alert_never_taken_from_service_user_home(self):
        self.assertNotIn("${SVC_HOME}/.local/bin/agent-alert", SETUP)
        self.assertIn('trusted_source "$c"', SETUP)


class AgentsUpdateRestartHook(unittest.TestCase):
    def test_paseo_and_gemini_smoke_tested(self):
        self.assertIn('"paseo:paseo --version"', UPDATE)
        self.assertIn('"gemini:gemini --version"', UPDATE)

    def test_restart_only_when_kept_and_changed(self):
        block = UPDATE[UPDATE.index("# --- 1b."):UPDATE.index("# --- 2.")]
        self.assertIn("rolled_back == 0", block)
        self.assertIn('grep -q "^${cli} " <<<"$changes"', block)
        self.assertIn('sudo -n systemctl restart "$unit"', block)

    def test_restart_on_is_validated_and_persisted(self):
        self.assertIn(r"^[a-z0-9_-]+=[A-Za-z0-9@_.-]+\.service$", UPDATE)
        self.assertIn('Environment="AGENTS_UPDATE_RESTART_ON=${restart_on[*]}"', UPDATE)
        pattern = re.compile(r"^[a-z0-9_-]+=[A-Za-z0-9@_.-]+\.service$")
        self.assertTrue(pattern.match("paseo=paseo.service"))
        self.assertFalse(pattern.match("paseo=paseo.service; rm -rf /"))


def extract_func(text, name):
    start = text.index(f"{name}() {{")
    return text[start:text.index("\n}\n", start) + 3]


class AgentsUpdateHold(unittest.TestCase):
    """rtk >= 1.2.0 dies with SIGILL on CPUs without AVX2 (Ivy Bridge host):
    it must be held, or the whole-set rollback cancels every agent update."""

    def test_rtk_smoke_tested(self):
        self.assertIn('"rtk:rtk --version"', UPDATE)

    def test_default_hold_only_without_avx2(self):
        self.assertIn('grep -qw avx2 /proc/cpuinfo', UPDATE)
        self.assertIn('HOLD="aqua:rtk-ai/rtk"', UPDATE)
        self.assertIn('AGENTS_UPDATE_HOLD+x', UPDATE)  # "" explicitly holds nothing

    def test_upgrade_targets_skip_held_tools(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            fake = Path(tmp, "mise")
            fake.write_text('#!/bin/sh\necho \'{"aqua:rtk-ai/rtk":[],"node":[],"npm:@openai/codex":[]}\'\n')
            fake.chmod(0o755)
            script = ("die(){ echo \"$*\" >&2; exit 1; }\n" + extract_func(UPDATE, "upgrade_targets")
                      + "\nHOLD='aqua:rtk-ai/rtk'; upgrade_targets\n")
            r = subprocess.run(["bash", "-c", script], capture_output=True, text=True,
                               env={"PATH": f"{tmp}:/usr/bin:/bin"}, check=True)
            self.assertEqual(r.stdout.split(), ["node", "npm:@openai/codex"])
            r = subprocess.run(["bash", "-c", script.replace("HOLD='aqua:rtk-ai/rtk'", "HOLD=''")],
                               capture_output=True, text=True,
                               env={"PATH": f"{tmp}:/usr/bin:/bin"}, check=True)
            self.assertEqual(r.stdout, "")  # no hold: plain `mise upgrade`, everything

    def test_both_upgrade_paths_use_the_holds(self):
        self.assertIn("mise_upgrade --dry-run", UPDATE)
        self.assertIn("mise_upgrade --no-prune --yes", UPDATE)
        self.assertNotRegex(UPDATE, r"(?m)^[^#\n]*mise upgrade --bump --pin --no-prune")


class PaseoProviders(unittest.TestCase):
    def py_block(self):
        start = SETUP.index("<<'PY'\n") + len("<<'PY'\n")
        return SETUP[start:SETUP.index("\nPY\n", start)]

    def run_block(self, home, *args):
        return subprocess.run(["python3", "-c", self.py_block(), *args], capture_output=True,
                              text=True, env=dict(os.environ, PASEO_HOME=home), check=True).stdout.strip()

    def test_acp_commands(self):
        for cmd in ('["cursor-agent","acp"]', '["gemini","--acp"]', '["grok","agent","stdio"]'):
            self.assertIn(cmd, SETUP)
        self.assertIn('"extends":"acp"', SETUP)

    def test_only_missing_keys_written_and_mode_600(self):
        import json, tempfile
        with tempfile.TemporaryDirectory() as home:
            cfg = Path(home, "config.json")
            cfg.write_text(json.dumps({"daemon": {"password": "h"},
                                       "agents": {"providers": {"grok": {"label": "Mine"}}}}))
            out = self.run_block(home, 'grok={"label":"Grok"}', 'omp={"enabled":true}')
            self.assertEqual(out, "omp")
            c = json.loads(cfg.read_text())
            self.assertEqual(c["agents"]["providers"]["grok"], {"label": "Mine"})
            self.assertEqual(c["agents"]["providers"]["omp"], {"enabled": True})
            self.assertEqual(c["daemon"]["password"], "h")
            self.assertEqual(cfg.stat().st_mode & 0o777, 0o600)
            self.assertEqual(self.run_block(home, 'omp={"enabled":false}'), "")  # idempotent

    def test_self_installs_where_sudo_finds_it(self):
        self.assertIn('SELF_BIN="/usr/local/bin/paseo-setup"', SETUP)


if __name__ == "__main__":
    unittest.main()
