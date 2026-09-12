#!/usr/bin/env python3
"""Regression tests for breww host-local cask upgrade skips.

Uses stdlib unittest so it runs with `python3 test_breww.py` (no pytest).

Origin: Mac Pro (jsoyer-macOS) is a non-admin account. `bcu -a` / `bup`
prompted for sudo on casks that write to /Library (obs virtualcam, logitune).
The skip file must apply on bulk upgrades and stay out of the way when a
cask is named explicitly.
"""
import importlib.machinery
import importlib.util
import tempfile
import unittest
import unittest.mock
from pathlib import Path

_BREWW_PATH = Path(__file__).resolve().parent / "executable_breww"
_LOADER = importlib.machinery.SourceFileLoader("breww", str(_BREWW_PATH))
_SPEC = importlib.util.spec_from_loader("breww", _LOADER)
assert _SPEC is not None
breww = importlib.util.module_from_spec(_SPEC)
_LOADER.exec_module(breww)


class LoadPackageList(unittest.TestCase):
    def test_strips_comments_blanks_and_keeps_order(self):
        with tempfile.NamedTemporaryFile("w", delete=False) as fh:
            fh.write(
                "# header\n"
                "\n"
                "obs\n"
                "logitune  # firmware updater\n"
                "logi-options+\n"
                "# xquartz\n"
            )
            path = Path(fh.name)
        try:
            self.assertEqual(
                breww.load_package_list(path),
                ["obs", "logitune", "logi-options+"],
            )
        finally:
            path.unlink()

    def test_missing_file_is_empty(self):
        self.assertEqual(breww.load_package_list(Path("/no/such/skip")), [])


class PlanBrewCommandsCu(unittest.TestCase):
    SKIP = ["obs", "logitune", "logi-options+"]
    INSTALLED = ["maccy", "obs", "zed", "logitune", "rectangle"]

    def test_bulk_cu_drops_skipped_casks(self):
        plans = breww.plan_brew_commands(
            ["cu", "-a"],
            self.SKIP,
            installed_casks=self.INSTALLED,
        )
        self.assertEqual(plans, [["cu", "-a", "maccy", "zed", "rectangle"]])

    def test_bulk_cu_without_skip_is_passthrough(self):
        self.assertEqual(
            breww.plan_brew_commands(
                ["cu", "-a"],
                [],
                installed_casks=self.INSTALLED,
            ),
            [["cu", "-a"]],
        )

    def test_explicit_cu_target_is_honored_even_if_skipped(self):
        self.assertEqual(
            breww.plan_brew_commands(
                ["cu", "-a", "obs"],
                self.SKIP,
                installed_casks=self.INSTALLED,
            ),
            [["cu", "-a", "obs"]],
        )

    def test_pin_subcommand_is_passthrough(self):
        self.assertEqual(
            breww.plan_brew_commands(["cu", "pin", "obs"], self.SKIP),
            [["cu", "pin", "obs"]],
        )

    def test_bulk_cu_with_everything_skipped_does_not_run_bare_cu(self):
        """A bare `cu -a` would upgrade ALL casks, including the skip list."""
        plans = breww.plan_brew_commands(
            ["cu", "-a"],
            self.SKIP,
            installed_casks=["obs", "logitune"],
        )
        self.assertEqual(plans, [])


class PlanBrewCommandsUpgrade(unittest.TestCase):
    SKIP = ["obs", "logitune"]
    OUTDATED = ["maccy", "obs", "wget"]

    def test_bulk_upgrade_splits_formulae_and_non_skipped_casks(self):
        plans = breww.plan_brew_commands(
            ["upgrade"],
            self.SKIP,
            outdated_casks=self.OUTDATED,
        )
        self.assertEqual(
            plans,
            [
                ["upgrade", "--formula"],
                ["upgrade", "--cask", "maccy", "wget"],
            ],
        )

    def test_greedy_flag_is_kept_on_both_halves(self):
        plans = breww.plan_brew_commands(
            ["upgrade", "--greedy"],
            self.SKIP,
            outdated_casks=self.OUTDATED,
        )
        self.assertEqual(
            plans,
            [
                ["upgrade", "--formula", "--greedy"],
                ["upgrade", "--cask", "--greedy", "maccy", "wget"],
            ],
        )

    def test_upgrade_cask_only_drops_skipped(self):
        plans = breww.plan_brew_commands(
            ["upgrade", "--cask"],
            self.SKIP,
            outdated_casks=self.OUTDATED,
        )
        self.assertEqual(plans, [["upgrade", "--cask", "maccy", "wget"]])

    def test_upgrade_formula_only_is_passthrough(self):
        self.assertEqual(
            breww.plan_brew_commands(
                ["upgrade", "--formula"],
                self.SKIP,
                outdated_casks=self.OUTDATED,
            ),
            [["upgrade", "--formula"]],
        )

    def test_explicit_upgrade_target_is_honored(self):
        self.assertEqual(
            breww.plan_brew_commands(["upgrade", "obs"], self.SKIP),
            [["upgrade", "obs"]],
        )

    def test_no_skip_is_passthrough(self):
        self.assertEqual(
            breww.plan_brew_commands(["upgrade"], []),
            [["upgrade"]],
        )

    def test_all_outdated_casks_skipped_runs_formulae_only(self):
        plans = breww.plan_brew_commands(
            ["upgrade"],
            self.SKIP,
            outdated_casks=["obs", "logitune"],
        )
        self.assertEqual(plans, [["upgrade", "--formula"]])


class SkipFilePath(unittest.TestCase):
    def test_hostname_is_in_the_filename(self):
        path = breww.get_cu_skip_file()
        self.assertEqual(path.parent, breww.BREWFILE_DIR)
        self.assertTrue(path.name.startswith("Brewfile_cu_skip_"))
        self.assertIn(breww.get_hostname(), path.name)


class LoadCuSkip(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.prev_dir = breww.BREWFILE_DIR
        breww.BREWFILE_DIR = self.tmp

    def tearDown(self):
        breww.BREWFILE_DIR = self.prev_dir
        for child in self.tmp.iterdir():
            child.unlink()
        self.tmp.rmdir()

    def test_profile_file_is_loaded_when_hostname_does_not_match(self):
        (self.tmp / "Brewfile_cu_skip_mac-pro").write_text("obs\nlogitune\n")
        with unittest.mock.patch.object(breww, "get_hostname", return_value="other-host"):
            with unittest.mock.patch.dict("os.environ", {"MACHINE_PROFILE": "mac-pro"}):
                self.assertEqual(breww.load_cu_skip(), ["obs", "logitune"])

    def test_hostname_match_is_case_insensitive(self):
        (self.tmp / "Brewfile_cu_skip_jsoyer-macOS").write_text("obs\n")
        with unittest.mock.patch.object(breww, "get_hostname", return_value="jsoyer-macos"):
            with unittest.mock.patch.dict("os.environ", {"MACHINE_PROFILE": "mac-personal"}):
                self.assertEqual(breww.load_cu_skip(), ["obs"])

    def test_profile_and_hostname_lists_are_merged(self):
        (self.tmp / "Brewfile_cu_skip_mac-pro").write_text("obs\nlogitune\n")
        (self.tmp / "Brewfile_cu_skip_jsoyer-macOS").write_text("obs\nxquartz\n")
        with unittest.mock.patch.object(breww, "get_hostname", return_value="jsoyer-macOS"):
            with unittest.mock.patch.dict("os.environ", {"MACHINE_PROFILE": "mac-pro"}):
                self.assertEqual(breww.load_cu_skip(), ["obs", "xquartz", "logitune"])


class RemoveFromBase(unittest.TestCase):
    """`breww uninstall` must also drop the entry from the profile base Brewfile.

    Origin: removing a cask only from the machine left the line in
    Brewfile_personal, so the next `chezmoi apply` reinstalled it — the
    remove/resurrect loop visible on firefox and visual-studio-code.
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.base = self.tmp / "Brewfile_personal"
        self.shared = self.tmp / "Brewfile_macos"

    def tearDown(self):
        self._tmp.cleanup()

    def test_removes_cask_and_leaves_every_other_line_untouched(self):
        self.base.write_text(
            '# Personal casks\n'
            'cask "firefox"\n'
            'cask "visual-studio-code"\n'
            '\n'
            'brew "git"\n'
        )
        removed = breww.remove_from_base(["visual-studio-code"], self.base, [])
        self.assertEqual(removed, ["visual-studio-code"])
        self.assertEqual(
            self.base.read_text(),
            '# Personal casks\ncask "firefox"\n\nbrew "git"\n',
        )

    def test_removes_formula(self):
        self.base.write_text('brew "git"\nbrew "wget"\n')
        self.assertEqual(breww.remove_from_base(["wget"], self.base, []), ["wget"])
        self.assertEqual(self.base.read_text(), 'brew "git"\n')

    def test_removes_several_names_at_once(self):
        self.base.write_text('cask "firefox"\ncask "microsoft-edge"\nbrew "git"\n')
        removed = breww.remove_from_base(["firefox", "microsoft-edge"], self.base, [])
        self.assertEqual(sorted(removed), ["firefox", "microsoft-edge"])
        self.assertEqual(self.base.read_text(), 'brew "git"\n')

    def test_absent_name_is_a_noop(self):
        original = 'cask "firefox"\nbrew "git"\n'
        self.base.write_text(original)
        self.assertEqual(breww.remove_from_base(["nope"], self.base, []), [])
        self.assertEqual(self.base.read_text(), original)

    def test_shared_file_is_reported_but_never_modified(self):
        self.base.write_text('brew "git"\n')
        self.shared.write_text('cask "firefox"\n')
        with unittest.mock.patch.object(breww, "print") as _p:
            removed = breww.remove_from_base(["firefox"], self.base, [self.shared])
        self.assertEqual(removed, [])
        self.assertEqual(self.shared.read_text(), 'cask "firefox"\n')

    def test_missing_base_is_a_noop(self):
        self.assertEqual(breww.remove_from_base(["firefox"], None, []), [])
        self.assertEqual(
            breww.remove_from_base(["firefox"], self.tmp / "absent", []), []
        )

    def test_fully_qualified_tap_entry(self):
        self.base.write_text(
            'brew "infisical/get-cli/infisical", trusted: true\nbrew "git"\n'
        )
        removed = breww.remove_from_base(
            ["infisical/get-cli/infisical"], self.base, []
        )
        self.assertEqual(removed, ["infisical/get-cli/infisical"])
        self.assertEqual(self.base.read_text(), 'brew "git"\n')


class UninstallWiring(unittest.TestCase):
    """main() must route uninstall through remove_from_base, not just the dump."""

    def _run(self, argv):
        calls = {}
        with unittest.mock.patch.object(breww.sys, "argv", ["breww", *argv]), \
             unittest.mock.patch("shutil.which", return_value="/usr/bin/brew"), \
             unittest.mock.patch.object(breww, "get_target_brewfile", return_value=Path("/tmp/Brewfile_personal")), \
             unittest.mock.patch.object(breww, "run_brew_command", return_value=0), \
             unittest.mock.patch.object(breww, "load_cu_skip", return_value=[]), \
             unittest.mock.patch.object(breww, "check_native_available"), \
             unittest.mock.patch.object(breww, "dump_host_overlay"), \
             unittest.mock.patch.object(breww, "sync_to_git"), \
             unittest.mock.patch.object(breww, "remove_from_base") as remove:
            remove.return_value = []
            with self.assertRaises(SystemExit):
                breww.main()
            calls["remove"] = remove.call_args_list
        return calls

    def test_uninstall_drops_the_entry_from_the_base(self):
        calls = self._run(["uninstall", "--cask", "visual-studio-code"])
        self.assertEqual(len(calls["remove"]), 1)
        self.assertEqual(calls["remove"][0].args[0], ["visual-studio-code"])

    def test_uninstall_handles_several_packages(self):
        calls = self._run(["uninstall", "firefox", "microsoft-edge"])
        self.assertEqual(calls["remove"][0].args[0], ["firefox", "microsoft-edge"])

    def test_install_never_touches_the_base(self):
        calls = self._run(["install", "ripgrep"])
        self.assertEqual(calls["remove"], [])


if __name__ == "__main__":
    unittest.main()
