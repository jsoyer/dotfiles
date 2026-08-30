#!/usr/bin/env python3
"""Headless Orca on Raspberry Pi must not depend on FUSE being present.

Origin: looping's orca-serve crash-looped (70+ restarts) with:
  dlopen(): error loading libfuse.so.2
  AppImages require FUSE to run.
Raspberry Pi OS / Debian ship fuse3; the AppImage type-2 runtime wants fuse2.
"""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SETUP = (ROOT / "dot_local/bin/executable_orca-setup").read_text()
GUI = (ROOT / "dot_local/bin/executable_orca-gui").read_text()
APT_RPI = (ROOT / "dot_private/Aptfile_rpi").read_text()


class FuseFallback(unittest.TestCase):
    def test_unit_extracts_without_fuse(self):
        self.assertIn("APPIMAGE_EXTRACT_AND_RUN=1", SETUP)
        self.assertIn("ensure_libfuse2", SETUP)
        self.assertIn("libfuse2t64", SETUP)

    def test_crash_loop_is_capped(self):
        self.assertIn("StartLimitBurst=8", SETUP)
        self.assertIn("Restart=on-failure", SETUP)

    def test_gui_also_extracts_without_fuse(self):
        self.assertIn("APPIMAGE_EXTRACT_AND_RUN=1", GUI)

    def test_rpi_aptfile_ships_libfuse2(self):
        self.assertRegex(APT_RPI, r"(?m)^libfuse2$")

    def test_setup_installs_electron_gtk_runtime(self):
        self.assertIn("ensure_electron_runtime", SETUP)
        self.assertIn("libgtk-3-0", SETUP)
        self.assertIn("libatk-1.0.so.0", SETUP)

    def test_rpi_aptfile_ships_electron_gtk_runtime(self):
        for pkg in ("libgtk-3-0", "libnss3", "libgbm1", "libasound2", "libatk-bridge2.0-0"):
            self.assertRegex(APT_RPI, rf"(?m)^{pkg}$")


if __name__ == "__main__":
    unittest.main()
