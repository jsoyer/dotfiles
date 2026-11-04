#!/usr/bin/env python3
"""sysup-os-check: notify-only OS release check, run with env test seams (no network)."""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "dot_local/bin/executable_sysup-os-check"


class OsCheckTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)

    def run_check(self, osrelease=None, **env):
        e = {k: v for k, v in os.environ.items() if not k.startswith("SYSUP_")}
        e["SYSUP_OS_CHECK_PLATFORM"] = env.pop("PLATFORM", "linux")
        e["SYSUP_CONTAINERENV"] = str(self.tmp / "no-containerenv")
        e["SYSUP_OSTREE_FLAG"] = str(self.tmp / "no-ostree")
        e["SYSUP_RPI_ISSUE"] = str(self.tmp / "no-rpi")
        if osrelease is not None:
            rel = self.tmp / "os-release"
            rel.write_text(osrelease)
            e["SYSUP_OS_RELEASE"] = str(rel)
        e.update(env)
        p = subprocess.run(
            ["bash", str(SCRIPT)], env=e, capture_output=True, text=True, timeout=60
        )
        self.assertEqual(p.returncode, 0, p.stderr)
        return p.stdout.strip()

    FEDORA = 'ID=fedora\nVERSION_ID=44\nVERSION="44 (Workstation Edition)"\n'

    def test_fedora_newer(self):
        out = self.run_check(self.FEDORA, SYSUP_OS_CHECK_LATEST="45")
        self.assertIn("OS: Fedora 45 is available (installed: 44)", out)
        self.assertIn(
            "sudo dnf system-upgrade download --releasever=45 && sudo dnf system-upgrade reboot",
            out,
        )

    def test_fedora_up_to_date(self):
        out = self.run_check(self.FEDORA, SYSUP_OS_CHECK_LATEST="44")
        self.assertNotIn("available", out)
        self.assertIn("OS: Fedora 44", out)

    def test_fedora_rawhide_skipped(self):
        rel = "ID=fedora\nVERSION_ID=46\nREDHAT_SUPPORT_PRODUCT_VERSION=rawhide\n"
        self.assertEqual(self.run_check(rel, SYSUP_OS_CHECK_LATEST="45"), "")

    def test_fedora_atomic_rebase_ref(self):
        flag = self.tmp / "ostree"
        flag.touch()
        js = '{"deployments":[{"booted":false,"origin":"x"},{"booted":true,"origin":"fedora:fedora/44/x86_64/silverblue"}]}'
        out = self.run_check(
            self.FEDORA,
            SYSUP_OS_CHECK_LATEST="45",
            SYSUP_OSTREE_FLAG=str(flag),
            SYSUP_OS_CHECK_RPMOSTREE_JSON=js,
        )
        self.assertIn("rpm-ostree rebase fedora:fedora/45/x86_64/silverblue", out)

    def test_fedora_atomic_unknown_origin_generic_hint(self):
        flag = self.tmp / "ostree"
        flag.touch()
        out = self.run_check(
            self.FEDORA,
            SYSUP_OS_CHECK_LATEST="45",
            SYSUP_OSTREE_FLAG=str(flag),
            SYSUP_OS_CHECK_RPMOSTREE_JSON="{}",
        )
        self.assertIn("Fedora 45 is available", out)
        self.assertIn("rpm-ostree rebase", out)

    DEBIAN = 'ID=debian\nVERSION_ID="12"\n'

    def test_debian_newer(self):
        out = self.run_check(self.DEBIAN, SYSUP_OS_CHECK_LATEST="13")
        self.assertIn("Debian 13", out)
        self.assertIn("installed: 12", out)

    def test_debian_same(self):
        out = self.run_check(self.DEBIAN, SYSUP_OS_CHECK_LATEST="12")
        self.assertNotIn("available", out)
        self.assertNotIn("is stable (installed", out)

    def test_proxmox_hint(self):
        out = self.run_check(
            self.DEBIAN,
            SYSUP_OS_CHECK_LATEST="13",
            SYSUP_OS_CHECK_PVE_VERSION="pve-manager/8.4.1/abcdef (running kernel: 6.8)",
        )
        self.assertIn("Upgrade_from_8_to_9", out)
        self.assertIn("pve8to9", out)
        self.assertNotIn("apt full-upgrade", out)

    def test_rpi_hint(self):
        issue = self.tmp / "rpi-issue"
        issue.touch()
        out = self.run_check(
            self.DEBIAN, SYSUP_OS_CHECK_LATEST="13", SYSUP_RPI_ISSUE=str(issue)
        )
        self.assertIn("fresh install", out)

    def test_ubuntu_new_release(self):
        raw = "Checking for a new Ubuntu release\nNew release '26.04 LTS' available.\nRun 'do-release-upgrade' to upgrade to it.\n"
        out = self.run_check('ID=ubuntu\nVERSION_ID="24.04"\n', SYSUP_OS_CHECK_RAW=raw)
        self.assertIn("Ubuntu 26.04 LTS is available (installed: 24.04)", out)
        self.assertIn("sudo do-release-upgrade", out)

    def test_ubuntu_none(self):
        raw = "Checking for a new Ubuntu release\nNo new release found.\n"
        out = self.run_check('ID=ubuntu\nVERSION_ID="24.04"\n', SYSUP_OS_CHECK_RAW=raw)
        self.assertNotIn("available", out)

    MAC_RAW = (
        "Finding available software\nSoftware Update found the following full installers:\n"
        "* Title: macOS Tahoe, Version: 26.1, Size: 15000000KiB, Build: 25B78, Deprecated: NO\n"
        "* Title: macOS Sequoia, Version: 15.7.2, Size: 14000000KiB, Build: 24G325, Deprecated: NO\n"
    )

    def test_macos_newer_major(self):
        out = self.run_check(
            PLATFORM="darwin",
            SYSUP_OS_CHECK_MACOS_VERSION="15.6",
            SYSUP_OS_CHECK_RAW=self.MAC_RAW,
        )
        self.assertIn("macOS Tahoe 26.1 is available (installed: macOS 15.6)", out)
        self.assertIn("--full-installer-version 26.1", out)

    def test_macos_none(self):
        out = self.run_check(
            PLATFORM="darwin",
            SYSUP_OS_CHECK_MACOS_VERSION="26.0",
            SYSUP_OS_CHECK_RAW=self.MAC_RAW,
        )
        self.assertNotIn("available", out)

    def test_arch_skipped(self):
        self.assertEqual(self.run_check("ID=arch\n", SYSUP_OS_CHECK_LATEST="99"), "")

    def test_container_skipped(self):
        marker = self.tmp / "containerenv"
        marker.touch()
        self.assertEqual(
            self.run_check(
                self.FEDORA, SYSUP_OS_CHECK_LATEST="45", SYSUP_CONTAINERENV=str(marker)
            ),
            "",
        )

    def test_opt_out(self):
        self.assertEqual(
            self.run_check(
                self.FEDORA, SYSUP_OS_CHECK_LATEST="45", SYSUP_NO_OS_CHECK="1"
            ),
            "",
        )

    def test_network_failure_is_silent(self):
        out = self.run_check(
            self.FEDORA, SYSUP_OS_CHECK_FEDORA_URL="http://127.0.0.1:9/releases.json"
        )
        self.assertEqual(out, "")
        out = self.run_check(
            self.DEBIAN, SYSUP_OS_CHECK_DEBIAN_URL="http://127.0.0.1:9/Release"
        )
        self.assertEqual(out, "")


if __name__ == "__main__":
    unittest.main()
