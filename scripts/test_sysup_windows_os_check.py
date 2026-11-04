#!/usr/bin/env python3
"""Windows OS release check: sysup msys branch wiring + the .ps1 contract."""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SYSUP = ROOT / "dot_local/bin/executable_sysup"
PS1 = ROOT / "dot_local/bin/sysup-os-check.ps1"
IGNORE = ROOT / ".chezmoiignore.tmpl"


class SysupWindowsBranchTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.bin = self.tmp / "bin"
        self.bin.mkdir()
        self.home = self.tmp / "home"
        (self.home / ".local/bin").mkdir(parents=True)
        (self.home / ".local/bin/sysup-os-check.ps1").write_text("# stub\n")
        self.log = self.tmp / "calls.log"
        stubs = {
            "scoop": 'echo "scoop $*" >> "$CALLS"',
            "cygpath": 'echo "C:\\\\fake\\\\$(basename "$2")"',
            "powershell.exe": 'echo "powershell $*" >> "$CALLS"; exit "${PS_RC:-0}"',
        }
        for name, body in stubs.items():
            f = self.bin / name
            f.write_text("#!/bin/sh\n" + body + "\n")
            f.chmod(0o755)
        # Run the real script but pretend to be on msys.
        self.script = self.tmp / "sysup"
        self.script.write_text(
            SYSUP.read_text().replace('case "$OSTYPE" in', 'case "msys" in', 1)
        )

    def run_sysup(self, **env):
        e = {k: v for k, v in os.environ.items() if not k.startswith("SYSUP_")}
        e.update(
            HOME=str(self.home),
            CALLS=str(self.log),
            PATH=f"{self.bin}:{e['PATH']}",
            MACHINE_PROFILE="windows",
        )
        e.update(env)
        p = subprocess.run(
            ["bash", str(self.script)],
            env=e,
            capture_output=True,
            text=True,
            timeout=60,
        )
        calls = self.log.read_text() if self.log.exists() else ""
        return p, calls

    def test_invokes_powershell_check(self):
        p, calls = self.run_sysup()
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn(
            "powershell -NoProfile -ExecutionPolicy Bypass -File C:\\fake\\sysup-os-check.ps1",
            calls,
        )

    def test_opt_out(self):
        p, calls = self.run_sysup(SYSUP_NO_OS_CHECK="1")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertNotIn("powershell", calls)

    def test_powershell_failure_is_not_fatal(self):
        p, _ = self.run_sysup(PS_RC="1")
        self.assertEqual(p.returncode, 0, p.stderr)


class Ps1ContractTest(unittest.TestCase):
    def test_script_contract(self):
        text = PS1.read_text()
        self.assertIn("SYSUP_NO_OS_CHECK", text)
        self.assertIn("-eq 'Upgrades'", text)
        self.assertIn("IsInstalled=0", text)
        self.assertIn("-Timeout 60", text)
        self.assertIn("exit 0", text)
        self.assertIn("#Requires -Version 5.1", text)

    def test_ignored_off_windows(self):
        text = IGNORE.read_text()
        i = text.index(".local/bin/sysup-os-check.ps1")
        self.assertIn('ne .chezmoi.os "windows"', text[max(0, i - 80) : i])


if __name__ == "__main__":
    unittest.main()
