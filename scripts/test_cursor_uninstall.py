#!/usr/bin/env python3
"""Tests for cursor-uninstall: service teardown, safe symlink handling, and --purge."""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "dot_local/bin/executable_cursor-uninstall"
IGNORE = ROOT / ".chezmoiignore.tmpl"
RUN12 = (
    ROOT / ".chezmoiscripts/02-install/run_once_12-disable-macos-agent-stacks.sh.tmpl"
)

LOGGER = '#!/usr/bin/env bash\necho "$(basename "$0") $*" >> "$STUB_LOG"\n'


class CursorUninstallTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.home = self.root / "home"
        self.stubs = self.root / "stubs"
        self.log = self.root / "calls.log"
        self.home.mkdir()
        self.stubs.mkdir()
        self.log.write_text("")

        for name in ("cursor-setup", "systemctl"):
            stub = self.stubs / name
            stub.write_text(LOGGER)
            stub.chmod(0o755)

        self.bin_dir = self.home / ".local/bin"
        self.data_dir = self.home / ".local/share/cursor-agent"
        self.config_dir = self.home / ".config/cursor"
        self.dot_cursor = self.home / ".cursor"
        self.units_dir = self.home / ".config/systemd/user"
        self.dropin_dir = self.units_dir / "cursor-worker.service.d"

        for d in (
            self.bin_dir,
            self.data_dir / "versions/2026.11.22",
            self.config_dir,
            self.dot_cursor,
            self.dropin_dir,
        ):
            d.mkdir(parents=True)

        target = self.data_dir / "versions/2026.11.22/cursor-agent"
        target.write_text("#!/bin/sh\n")
        target.chmod(0o755)
        (self.bin_dir / "cursor-agent").symlink_to(target)
        (self.config_dir / "worker.env").write_text("CURSOR_API_KEY=test\n")
        (self.dot_cursor / "cli-config.json").write_text("{}\n")
        (self.dropin_dir / "override.conf").write_text("[Service]\n")
        for u in (
            "cursor-worker.service",
            "cursor-update.service",
            "cursor-update.timer",
        ):
            (self.units_dir / u).write_text("[Unit]\n")

    def run_uninstall(self, *args):
        env = {
            **os.environ,
            "HOME": str(self.home),
            "XDG_CONFIG_HOME": str(self.home / ".config"),
            "XDG_DATA_HOME": str(self.home / ".local/share"),
            "PATH": f"{self.stubs}:{os.environ['PATH']}",
            "STUB_LOG": str(self.log),
        }
        return subprocess.run(
            ["bash", str(SCRIPT), *args],
            env=env,
            text=True,
            capture_output=True,
        )

    def calls(self):
        return [line.strip() for line in self.log.read_text().splitlines() if line]

    def test_removes_cursor_agent_and_units_but_keeps_config_without_purge(self):
        target = self.data_dir / "versions/2026.11.22/cursor-agent"
        (self.bin_dir / "agent").symlink_to(target)

        r = self.run_uninstall("-y")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("cursor-setup --uninstall -y", self.calls())
        self.assertIn("systemctl --user daemon-reload", self.calls())

        self.assertFalse((self.bin_dir / "cursor-agent").exists())
        self.assertFalse((self.bin_dir / "cursor-agent").is_symlink())
        self.assertFalse((self.bin_dir / "agent").is_symlink())
        self.assertFalse(self.data_dir.exists())
        self.assertFalse(self.dropin_dir.exists())
        for u in (
            "cursor-worker.service",
            "cursor-update.service",
            "cursor-update.timer",
        ):
            self.assertFalse((self.units_dir / u).exists())

        # Config and auth survive without --purge
        self.assertTrue((self.config_dir / "worker.env").exists())
        self.assertTrue((self.dot_cursor / "cli-config.json").exists())

    def test_preserves_grok_agent_symlink(self):
        grok_bin = self.home / ".grok/bin"
        grok_bin.mkdir(parents=True)
        grok_agent = grok_bin / "agent"
        grok_agent.write_text("#!/bin/sh\n")
        (self.bin_dir / "agent").symlink_to(grok_agent)

        r = self.run_uninstall("-y")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue((self.bin_dir / "agent").is_symlink())
        self.assertEqual(os.readlink(self.bin_dir / "agent"), str(grok_agent))

    def test_purge_drops_config_and_dot_cursor(self):
        r = self.run_uninstall("-y", "--purge")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertFalse(self.config_dir.exists())
        self.assertFalse(self.dot_cursor.exists())

    def test_unknown_flag_exits_2(self):
        r = self.run_uninstall("--bogus")
        self.assertEqual(r.returncode, 2)

    def test_linux_only_scope_in_ignore_and_run_once_12(self):
        self.assertIn(".local/bin/cursor-uninstall", IGNORE.read_text())
        self.assertIn("${HOME}/.local/bin/cursor-uninstall", RUN12.read_text())


if __name__ == "__main__":
    unittest.main()
