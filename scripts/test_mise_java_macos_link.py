#!/usr/bin/env python3
"""mise-java-macos-link: managed /Library/Java/JavaVirtualMachines entries.

Runs the real bash script on any OS (MISE_JAVA_LINK_OS=Darwin) against a
temporary JVM dir and installs dir, with a fake sudo that logs its calls.
"""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "dot_local/bin/executable_mise-java-macos-link"

FAKE_SUDO = """#!/bin/sh
echo "$@" >> "$FAKE_SUDO_LOG"
if [ "$1" = "-n" ] && [ -n "$FAKE_SUDO_DENY" ]; then exit 1; fi
if [ "$1" = "-n" ] || [ "$1" = "-v" ]; then shift; [ "$#" -eq 0 ] && exit 0; fi
exec "$@"
"""


class LinkTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.jvm = self.tmp / "jvm"
        self.jvm.mkdir()
        self.installs = self.tmp / "installs"
        self.installs.mkdir()
        self.log = self.tmp / "sudo.log"
        self.log.touch()
        self.sudo = self.tmp / "fake-sudo"
        self.sudo.write_text(FAKE_SUDO)
        self.sudo.chmod(0o755)

    def install(self, name, java=True):
        d = self.installs / name
        (d / "Contents/Home/bin").mkdir(parents=True)
        if java:
            j = d / "Contents/Home/bin/java"
            j.write_text("#!/bin/sh\n")
            j.chmod(0o755)
        return d

    def run_script(self, *args, deny=False, os_name="Darwin", stdin=subprocess.DEVNULL):
        env = {
            "PATH": os.environ["PATH"],
            "HOME": str(self.tmp),
            "JVM_DIR": str(self.jvm),
            "MISE_JAVA_INSTALLS_DIR": str(self.installs),
            "SUDO": str(self.sudo),
            "FAKE_SUDO_LOG": str(self.log),
            "MISE_JAVA_LINK_OS": os_name,
        }
        if deny:
            env["FAKE_SUDO_DENY"] = "1"
        return subprocess.run(
            ["bash", str(SCRIPT), *args],
            env=env, stdin=stdin, capture_output=True, text=True, timeout=30,
        )

    def contents(self, name):
        return self.jvm / f"mise-{name}.jdk" / "Contents"

    def test_creates_managed_link(self):
        d = self.install("temurin-25.0.1")
        r = self.run_script()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(self.contents("temurin-25.0.1").is_symlink())
        self.assertEqual(os.readlink(self.contents("temurin-25.0.1")), str(d.resolve() / "Contents"))

    def test_second_run_is_idempotent_and_never_calls_sudo(self):
        self.install("temurin-25.0.1")
        self.run_script()
        self.log.write_text("")
        r = self.run_script()
        self.assertEqual(r.returncode, 0)
        self.assertEqual(self.log.read_text(), "")
        self.assertIn("up to date", r.stdout)

    def test_wrong_target_is_fixed(self):
        d = self.install("temurin-25.0.1")
        jdk = self.jvm / "mise-temurin-25.0.1.jdk"
        jdk.mkdir()
        (jdk / "Contents").symlink_to(self.tmp / "elsewhere")
        r = self.run_script()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(os.readlink(jdk / "Contents"), str(d.resolve() / "Contents"))

    def test_stale_managed_entry_removed(self):
        self.install("temurin-25.0.1")
        stale = self.jvm / "mise-temurin-21.0.0.jdk"
        stale.mkdir()
        (stale / "Contents").symlink_to(self.tmp / "gone")
        r = self.run_script()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse(stale.exists())
        self.assertTrue(self.contents("temurin-25.0.1").is_symlink())

    def test_stale_entry_with_extra_content_is_kept_with_warning(self):
        stale = self.jvm / "mise-temurin-21.0.0.jdk"
        stale.mkdir()
        (stale / "Contents").symlink_to(self.tmp / "gone")
        (stale / "precious.txt").write_text("x")
        r = self.run_script()
        self.assertEqual(r.returncode, 0)
        self.assertTrue((stale / "precious.txt").exists())
        self.assertIn("not a managed entry", r.stderr)

    def test_foreign_jdk_untouched(self):
        foreign = self.jvm / "temurin-17.jdk"
        (foreign / "Contents").mkdir(parents=True)
        (foreign / "Contents/Info.plist").write_text("x")
        self.install("temurin-25.0.1")
        self.run_script()
        self.assertTrue((foreign / "Contents/Info.plist").exists())
        self.assertFalse((foreign / "Contents").is_symlink())

    def test_unsafe_names_refused(self):
        self.install("bad name;rm")
        r = self.run_script()
        self.assertEqual(r.returncode, 0)
        self.assertEqual(list(self.jvm.iterdir()), [])
        self.assertIn("unsafe", r.stderr)

    def test_install_without_java_binary_skipped(self):
        self.install("temurin-25.0.1", java=False)
        self.run_script()
        self.assertEqual(list(self.jvm.iterdir()), [])

    def test_non_darwin_is_noop(self):
        self.install("temurin-25.0.1")
        r = self.run_script(os_name="Linux")
        self.assertEqual(r.returncode, 0)
        self.assertEqual(list(self.jvm.iterdir()), [])
        self.assertEqual(self.log.read_text(), "")

    def test_alias_symlinks_deduplicated(self):
        self.install("temurin-25.0.1")
        (self.installs / "lts").symlink_to("temurin-25.0.1")
        (self.installs / "25").symlink_to("temurin-25.0.1")
        r = self.run_script()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual([p.name for p in self.jvm.iterdir()], ["mise-temurin-25.0.1.jdk"])

    def test_non_tty_sudo_failure_prints_instructions_and_exits_zero(self):
        self.install("temurin-25.0.1")
        r = self.run_script(deny=True)
        self.assertEqual(r.returncode, 0)
        self.assertEqual(list(self.jvm.iterdir()), [])
        self.assertIn("ln -sfn", r.stderr)
        self.assertIn("mise-temurin-25.0.1.jdk", r.stderr)

    def test_check_prints_plan_and_changes_nothing(self):
        self.install("temurin-25.0.1")
        r = self.run_script("--check")
        self.assertEqual(r.returncode, 0)
        self.assertIn("ln -sfn", r.stdout)
        self.assertEqual(list(self.jvm.iterdir()), [])
        self.assertEqual(self.log.read_text(), "")

    def test_unknown_option_exits_2(self):
        self.assertEqual(self.run_script("--bogus").returncode, 2)


if __name__ == "__main__":
    unittest.main()
