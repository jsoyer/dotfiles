#!/usr/bin/env python3
"""happy-setup guarantees: verified binary, private config, safe upgrade, health probe."""

import os
import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SETUP_PATH = ROOT / "dot_local/bin/executable_happy-setup"
SETUP = SETUP_PATH.read_text()
AGENTSVC = (ROOT / "dot_local/bin/executable_agentsvc").read_text()
IGNORE = (ROOT / ".chezmoiignore.tmpl").read_text()


class HappySetup(unittest.TestCase):
    def test_parses(self):
        subprocess.run(["bash", "-n", str(SETUP_PATH)], check=True)

    def test_binary_is_checksum_verified_and_root_owned(self):
        self.assertIn('sha256sum --check --status "${archive}.sha256"', SETUP)
        self.assertIn('install -m 0755 -o root -g root "$NEW_BIN" "$BIN"', SETUP)
        self.assertIn('BIN="/usr/local/bin/happy-agent"', SETUP)
        # Stable releases only unless a tag is pinned.
        self.assertIn("select(.draft == false and .prerelease == false)", SETUP)
        self.assertIn('x86_64)        TARGET="linux-x64"', SETUP)
        self.assertIn('aarch64|arm64) TARGET="linux-arm64"', SETUP)

    def test_config_created_once_and_private(self):
        # O_EXCL + 0600: an existing happy.toml is never rewritten.
        self.assertIn("os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600", SETUP)
        self.assertIn("exists, left untouched", SETUP)
        self.assertIn("secrets.token_bytes(32)", SETUP)
        self.assertIn("[feature.team]\\nenabled = false", SETUP)
        self.assertIn("[feature.tailcat]\\nenabled = true", SETUP)
        self.assertIn('[defaults]\\npermission_mode = "auto"', SETUP)
        self.assertNotIn("Full access", SETUP.split("# --- 2. Config")[1].split("# --- 3.")[0])

    def test_secrets_never_printed(self):
        # The token only travels inside python (config -> socket), never argv/echo.
        self.assertNotRegex(SETUP, r"echo[^\n]*\$\{?tok")
        self.assertNotRegex(SETUP, r"(?<![A-Za-z])cat\s+\"?\$\{?SVC_HOME\}?/\.happy/agent/tailcat/address")
        self.assertIn("address present (not shown)", SETUP)
        self.assertIn("Authorization: Bearer {tok}", SETUP)

    def test_unit_environment(self):
        self.assertIn("${SVC_HOME}/.local/share/mise/shims:${SVC_HOME}/.local/bin:${SVC_HOME}/.grok/bin", SETUP)
        for var in ("MISE_DATA_DIR", "MISE_CONFIG_DIR", "MISE_STATE_DIR", "MISE_CACHE_DIR"):
            self.assertIn(f'"{var}=${{SVC_HOME}}/', SETUP)
        self.assertIn("User=${SVC_USER}", SETUP)
        self.assertIn("UMask=0077", SETUP)
        self.assertIn("ExecStart=${BIN} run", SETUP)
        self.assertIn("EnvironmentFile=-${ENV_FILE}", SETUP)

    def test_upgrade_drains_and_rolls_back(self):
        up = SETUP.split("Upgrading ${CUR_VERSION}")[1].split("# --- 2. Config")[0]
        self.assertLess(up.index('"$BIN" drain'), up.index("systemctl stop happy-agent.service"))
        self.assertIn('cp -p "$BIN" "${BIN}.prev"', up)
        self.assertIn('install -m 0755 -o root -g root "${BIN}.prev" "$BIN"', up)
        self.assertIn("wait_ready 60", up)

    def test_health_restarts_after_two_misses(self):
        self.assertIn("declare -f probe_ready", SETUP)
        self.assertIn("if (( fails >= 2 )); then", SETUP)
        self.assertIn("systemctl restart happy-agent.service", SETUP)
        self.assertIn("OnUnitActiveSec=10min", SETUP)

    def test_rejects_bad_arguments(self):
        for args in (
            ["--user", "Bad User"],
            ["--user", "ok", "--version", "latest"],
            ["--user", "ok", "--relay", "ftp://x"],
            ["--user", "ok", "--email", "not-an-email"],
            ["--bogus"],
        ):
            with self.subTest(args=args):
                r = subprocess.run(
                    ["bash", str(SETUP_PATH), *args],
                    capture_output=True, text=True, check=False,
                    env=dict(os.environ, PATH="/usr/bin:/bin"),
                )
                self.assertNotEqual(r.returncode, 0)

    def test_wired_into_agentsvc_and_linux_only(self):
        self.assertIn("happy-agent.service", AGENTSVC)
        self.assertRegex(AGENTSVC, r"moshi\|orca\|cursor\|herdr\|t3\|paseo\|happy\|all\)")
        blocks = [b.split("{{ end }}")[0] for b in IGNORE.split('{{ if ne .chezmoi.os "linux" }}')[1:]]
        stacks = next(b for b in blocks if ".local/bin/paseo-setup" in b)
        self.assertIn(".local/bin/happy-setup", stacks)


if __name__ == "__main__":
    unittest.main()
