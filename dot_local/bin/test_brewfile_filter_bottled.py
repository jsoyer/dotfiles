#!/usr/bin/env python3
"""Regression tests for brewfile-filter-bottled.

Origin: Intel macOS Sequoia is Homebrew Tier 3. brew bundle tries to install
or upgrade formulae with no pourable bottle, then prints
"Installing X has failed!" / "Upgrading X has failed!" during chezmoi update.
"""
import importlib.machinery
import importlib.util
import unittest
from pathlib import Path

_PATH = Path(__file__).resolve().parent / "executable_brewfile-filter-bottled"
_LOADER = importlib.machinery.SourceFileLoader("brewfile_filter_bottled", str(_PATH))
_SPEC = importlib.util.spec_from_loader("brewfile_filter_bottled", _LOADER)
assert _SPEC is not None
mod = importlib.util.module_from_spec(_SPEC)
_LOADER.exec_module(mod)


def rec(name, *, bottled=True, deps=None, aliases=None):
    files = {"sonoma": {"url": "https://example.invalid"}} if bottled else {}
    return {
        "name": name,
        "aliases": aliases or [],
        "dependencies": deps or [],
        "bottle": {"stable": {"files": files}},
    }


class ParseBrewfile(unittest.TestCase):
    def test_extracts_formula_from_kwargs_line(self):
        line = 'brew "ollama", restart_service: :changed, link: false'
        self.assertEqual(mod.formula_name(line), "ollama")

    def test_extracts_tapped_formula(self):
        self.assertEqual(
            mod.formula_name('brew "can1357/tap/omp", trusted: true'),
            "can1357/tap/omp",
        )

    def test_ignores_cask_and_comments(self):
        self.assertIsNone(mod.formula_name('cask "ghostty"'))
        self.assertIsNone(mod.formula_name("# brew \"awscli\""))
        self.assertIsNone(mod.formula_name("tap \"buo/cask-upgrade\""))


class SkipReason(unittest.TestCase):
    def setUp(self):
        self.info = mod.index_info(
            [
                rec("awscli", bottled=False, deps=["python@3.14"]),
                rec("python@3.14", bottled=True),
                rec("gstreamer", bottled=True, deps=["orc", "ffmpeg"]),
                rec("orc", bottled=False),
                rec("ffmpeg", bottled=True),
                rec("gnu-tar", bottled=False),
                rec("starship", bottled=True),
                rec("dua-cli", bottled=False),
                rec("podman-compose", bottled=True, deps=["podman"]),
                rec("podman", bottled=False),
                rec("cycle-a", bottled=True, deps=["cycle-b"]),
                rec("cycle-b", bottled=True, deps=["cycle-a"]),
            ]
        )
        self.installed = {"gnu-tar", "dua-cli", "python@3.14", "ffmpeg"}
        self.outdated = {"gnu-tar", "dua-cli"}

    def _reason(self, name):
        return mod.skip_reason(name, self.info, self.installed, self.outdated)

    def test_unbottled_missing_formula_is_skipped(self):
        self.assertEqual(self._reason("awscli"), "no bottle")

    def test_unbottled_outdated_upgrade_is_skipped(self):
        self.assertEqual(self._reason("gnu-tar"), "no bottle")
        self.assertEqual(self._reason("dua-cli"), "no bottle")

    def test_bottled_formula_with_unbottled_missing_dep_is_skipped(self):
        self.assertIn("orc", self._reason("gstreamer"))

    def test_bottled_formula_with_unbottled_missing_formula_dep_is_skipped(self):
        self.assertIn("podman", self._reason("podman-compose"))

    def test_bottled_formula_with_ok_deps_is_kept(self):
        self.assertIsNone(self._reason("starship"))

    def test_installed_current_unbottled_is_kept(self):
        # python@3.14 is bottled here; simulate an already-satisfied unbottled keg
        self.info = mod.index_info([rec("gnutls", bottled=False)])
        self.installed = {"gnutls"}
        self.outdated = set()
        self.assertIsNone(self._reason("gnutls"))

    def test_unknown_formula_is_kept(self):
        self.assertIsNone(self._reason("can1357/tap/omp"))

    def test_circular_deps_do_not_loop(self):
        self.assertIsNone(self._reason("cycle-a"))


class FilterBrewfile(unittest.TestCase):
    def test_drops_unbottled_keeps_rest(self):
        text = "\n".join(
            [
                'tap "buo/cask-upgrade"',
                'brew "awscli"',
                'brew "starship"',
                'brew "gstreamer"',
                'brew "gnu-tar"',
                'brew "ollama", restart_service: :changed, link: false',
                'cask "ghostty"',
                'mas "Infuse", id: 1136220934',
                "",
            ]
        )
        info = mod.index_info(
            [
                rec("awscli", bottled=False),
                rec("starship", bottled=True),
                rec("gstreamer", bottled=True, deps=["orc"]),
                rec("orc", bottled=False),
                rec("gnu-tar", bottled=False),
                rec("ollama", bottled=True),
            ]
        )
        filtered, skipped = mod.filter_brewfile(
            text,
            info,
            installed={"gnu-tar"},
            outdated={"gnu-tar"},
        )
        self.assertIn('tap "buo/cask-upgrade"', filtered)
        self.assertIn('brew "starship"', filtered)
        self.assertIn('brew "ollama", restart_service: :changed, link: false', filtered)
        self.assertIn('cask "ghostty"', filtered)
        self.assertIn('mas "Infuse", id: 1136220934', filtered)
        self.assertNotIn('brew "awscli"', filtered)
        self.assertNotIn('brew "gstreamer"', filtered)
        self.assertNotIn('brew "gnu-tar"', filtered)
        skipped_names = [name for name, _ in skipped]
        self.assertEqual(skipped_names, ["awscli", "gstreamer", "gnu-tar"])

    def test_empty_input_is_empty(self):
        filtered, skipped = mod.filter_brewfile("", {}, set(), set())
        self.assertEqual(filtered, "")
        self.assertEqual(skipped, [])


class Upgradeable(unittest.TestCase):
    def test_lists_only_outdated_formulae_that_can_pour(self):
        info = mod.index_info(
            [
                rec("starship", bottled=True),
                rec("gnu-tar", bottled=False),
                rec("node", bottled=False),
                rec("ripgrep", bottled=True),
            ]
        )
        names = mod.upgradeable_formulae(
            info,
            installed={"starship", "gnu-tar", "node", "ripgrep"},
            outdated={"starship", "gnu-tar", "node"},
        )
        self.assertEqual(names, ["starship"])


if __name__ == "__main__":
    unittest.main()
