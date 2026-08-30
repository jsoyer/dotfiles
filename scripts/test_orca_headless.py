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

    def test_unit_wraps_exec_in_xvfb(self):
        self.assertIn("xvfb-run --auto-servernum", SETUP)
        self.assertIn("xvfb", APT_RPI)

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
        self.assertIn("libcups2", SETUP)
        self.assertIn("libcairo2", SETUP)
        self.assertIn("ELECTRON_APT_PKGS", SETUP)

    def test_rpi_aptfile_ships_electron_gtk_runtime(self):
        for pkg in (
            "libfuse2",
            "libgtk-3-0",
            "libatk1.0-0",
            "libatk-bridge2.0-0",
            "libatspi2.0-0",
            "libnss3",
            "libnspr4",
            "libgbm1",
            "libasound2",
            "libcups2",
            "libdrm2",
            "libcairo2",
            "libpango-1.0-0",
            "libpangocairo-1.0-0",
            "libgdk-pixbuf-2.0-0",
            "libglib2.0-0",
            "libxss1",
            "libxtst6",
            "libnotify4",
            "libx11-6",
            "libxcb1",
            "libxext6",
            "libxfixes3",
            "libvulkan1",
            "fonts-liberation",
            "xvfb",
        ):
            self.assertRegex(APT_RPI, rf"(?m)^{pkg}$")
            self.assertIn(pkg, SETUP)


if __name__ == "__main__":
    unittest.main()
