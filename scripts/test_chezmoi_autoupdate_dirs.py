#!/usr/bin/env python3
"""chezmoi-autoupdate: `apply --exclude dirs` must not strand files in new dirs.

`chezmoi apply --exclude dirs` never creates directories, so a managed file
whose parent directory does not exist yet fails with
`stat <dir>: no such file or directory` (seen with
.local/share/agent-host/mise-agents.toml). The script therefore creates the
missing managed directories first, with their chezmoi modes.
"""

import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "dot_local/bin/executable_chezmoi-autoupdate"
FUNC = "ensure_missing_parent_dirs"


def extract_function(text):
    m = re.search(r"^%s\(\) \{\n.*?^\}\n" % FUNC, text, re.S | re.M)
    return m.group(0) if m else None


@unittest.skipUnless(shutil.which("chezmoi") and shutil.which("bash"), "needs chezmoi + bash")
class AutoupdateDirsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="autoupd-"))
        self.addCleanup(shutil.rmtree, str(self.tmp), True)
        src, self.home = self.tmp / "src", self.tmp / "home"
        (src / "dot_local/share/agent-host").mkdir(parents=True)
        (src / "private_dot_ssh").mkdir()
        (src / "dot_local/share/agent-host/mise-agents.toml").write_text("x\n")
        (src / "private_dot_ssh/config").write_text("y\n")
        self.home.mkdir()
        (self.tmp / "c.toml").write_text("")
        # `timeout chezmoi ...` bypasses shell functions, so wrap via PATH.
        (self.tmp / "bin").mkdir()
        wrapper = self.tmp / "bin/chezmoi"
        wrapper.write_text('#!/bin/sh\nexec %s --source %s --destination %s --config %s "$@"\n'
                           % (shutil.which("chezmoi"), src, self.home, self.tmp / "c.toml"))
        wrapper.chmod(0o755)

    def run_bash(self, body):
        return subprocess.run(["bash", "-c", body], capture_output=True, text=True, timeout=60)

    def apply_like_autoupdate(self, prelude=""):
        body = (
            "export PATH=%s:$PATH\n"
            "LOG_FILE=%s; CHEZMOI_PHASE_TIMEOUT=60\n"
            "log() { :; }; log_err() { echo \"$*\" >&2; }\n%s\n"
            "chezmoi apply --force --exclude dirs --no-tty --keep-going 2>&1\n"
        ) % (self.tmp / "bin", self.tmp / "log", prelude)
        return self.run_bash(body)

    def test_script_defines_and_calls_helper(self):
        text = SCRIPT.read_text()
        self.assertIsNotNone(extract_function(text), "helper missing")
        calls = [l for l in text.splitlines() if l.strip() == FUNC]
        self.assertTrue(calls, "helper never called before apply")
        self.assertLess(text.index("\n            " + FUNC), text.index("chezmoi apply --force --exclude dirs"))

    def test_bug_without_helper(self):
        r = self.apply_like_autoupdate()
        self.assertIn("agent-host: no such file or directory", r.stdout + r.stderr)

    def test_helper_creates_missing_dirs_with_modes(self):
        func = extract_function(SCRIPT.read_text())
        self.assertIsNotNone(func)
        r = self.apply_like_autoupdate(func + FUNC)
        self.assertNotIn("no such file", r.stdout + r.stderr)
        self.assertEqual((self.home / ".local/share/agent-host/mise-agents.toml").read_text(), "x\n")
        self.assertEqual((self.home / ".ssh").stat().st_mode & 0o777, 0o700)

    def test_helper_leaves_existing_dirs_alone(self):
        func = extract_function(SCRIPT.read_text())
        self.assertIsNotNone(func)
        ssh = self.home / ".ssh"
        ssh.mkdir(mode=0o755)
        ssh.chmod(0o755)
        self.apply_like_autoupdate(func + FUNC)
        self.assertEqual(ssh.stat().st_mode & 0o777, 0o755)


if __name__ == "__main__":
    unittest.main()
