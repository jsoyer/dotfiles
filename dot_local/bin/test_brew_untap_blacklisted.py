#!/usr/bin/env python3
"""Tests for brew-untap-blacklisted tap parsing.

Origin: Homebrew 6 aborts brew update on sidneys/homebrew
(`depends_on macos: :sierra` is disabled). That tap was already in
Brewfile_blacklist but still tapped, so chezmoi update-homebrew.sh exited 1.
"""
import importlib.machinery
import importlib.util
import unittest
from pathlib import Path

_PATH = Path(__file__).resolve().parent / "executable_brew-untap-blacklisted"
_LOADER = importlib.machinery.SourceFileLoader("brew_untap_blacklisted", str(_PATH))
_SPEC = importlib.util.spec_from_loader("brew_untap_blacklisted", _LOADER)
assert _SPEC is not None
mod = importlib.util.module_from_spec(_SPEC)
_LOADER.exec_module(mod)

SAMPLE = """
# comment
sidneys/homebrew
updatest/tap
updatest/tap,
@mariozechner/pi-coding-agent
awscli
jandedobbeleer/oh-my-posh  # moved to core
homebrew/bundle
"""


class BlacklistTaps(unittest.TestCase):
    def test_extracts_user_repo_and_strips_comma_dupes(self):
        self.assertEqual(
            mod.blacklist_taps(SAMPLE),
            [
                "sidneys/homebrew",
                "updatest/tap",
                "jandedobbeleer/oh-my-posh",
                "homebrew/bundle",
            ],
        )

    def test_skips_npm_scopes_and_plain_packages(self):
        taps = mod.blacklist_taps(SAMPLE)
        self.assertNotIn("@mariozechner/pi-coding-agent", taps)
        self.assertNotIn("awscli", taps)


class MatchingTapped(unittest.TestCase):
    def test_matches_tap_name_with_trailing_comma(self):
        tapped = ["buo/cask-upgrade", "sidneys/homebrew", "updatest/tap,"]
        self.assertEqual(
            mod.matching_tapped("sidneys/homebrew", tapped),
            ["sidneys/homebrew"],
        )
        self.assertEqual(
            mod.matching_tapped("updatest/tap", tapped),
            ["updatest/tap,"],
        )
        self.assertEqual(mod.matching_tapped("missing/tap", tapped), [])

    def test_plan_untaps_uses_actual_brew_tap_names(self):
        tapped = ["sidneys/homebrew", "updatest/tap,", "can1357/tap"]
        self.assertEqual(
            mod.plan_untaps(SAMPLE, tapped),
            ["sidneys/homebrew", "updatest/tap,"],
        )


if __name__ == "__main__":
    unittest.main()
