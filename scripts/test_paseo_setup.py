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


if __name__ == "__main__":
    unittest.main()
