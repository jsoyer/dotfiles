#!/usr/bin/env python3
"""Regression tests for breww host-local cask upgrade skips.

Uses stdlib unittest so it runs with `python3 test_breww.py` (no pytest).

Origin: the work MacBook Air (jsoyer-macOS, profile mac-pro) is a non-admin account. `bcu -a` / `bup`
prompted for sudo on casks that write to /Library (obs virtualcam, logitune).
The skip file must apply on bulk upgrades and stay out of the way when a
cask is named explicitly.
"""

import importlib.machinery
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path


# chezmoi strips the "executable_" prefix on apply, so the script sits next to
# this test under its bare name once deployed to ~/.local/bin.
_BREWW_PATH = Path(__file__).resolve().parent / "executable_breww"
if not _BREWW_PATH.exists():
    _BREWW_PATH = _BREWW_PATH.with_name(_BREWW_PATH.name.removeprefix("executable_"))
_LOADER = importlib.machinery.SourceFileLoader("breww", str(_BREWW_PATH))
_SPEC = importlib.util.spec_from_loader("breww", _LOADER)
assert _SPEC is not None
breww = importlib.util.module_from_spec(_SPEC)
_LOADER.exec_module(breww)
LayerError = breww.LayerError


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


class PlanBrewCommandsSourceBuilds(unittest.TestCase):
    def test_compile_plan_follows_bottled_plan(self):
        plans = breww.plan_brew_commands(
            ["upgrade"],
            [],
            upgradeable_formulae=["jq"],
            compile_formulae=["curl", "git"],
        )
        self.assertEqual(
            plans,
            [
                ["upgrade", "--formula", "jq"],
                ["upgrade", "--formula", "--build-from-source", "curl", "git"],
                ["upgrade", "--cask"],
            ],
        )

    def test_compile_plan_runs_even_when_nothing_pours(self):
        plans = breww.plan_brew_commands(
            ["upgrade", "--formula"],
            [],
            upgradeable_formulae=[],
            compile_formulae=["curl"],
        )
        self.assertEqual(
            plans, [["upgrade", "--formula", "--build-from-source", "curl"]]
        )

    def test_no_compile_plan_for_cask_only_or_empty(self):
        self.assertEqual(
            breww.plan_brew_commands(
                ["upgrade", "--cask"],
                [],
                upgradeable_formulae=[],
                compile_formulae=["curl"],
            ),
            [["upgrade", "--cask"]],
        )
        self.assertEqual(
            breww.plan_brew_commands(
                ["upgrade"], [], upgradeable_formulae=["jq"], compile_formulae=[]
            ),
            [["upgrade", "--formula", "jq"], ["upgrade", "--cask"]],
        )

    def test_every_outdated_unpoured_formula_is_built(self):
        self.assertEqual(
            breww.select_compile_formulae(
                ["curl", "git", "node", "gnupg", "libxml2"], ["git"]
            ),
            ["curl", "node", "gnupg", "libxml2"],
        )

    def test_old_allowlist_cannot_silently_disable_updates(self):
        with (
            unittest.mock.patch.dict("os.environ", {"BREWW_COMPILE_ALLOWLIST": ""}),
            unittest.mock.patch.object(
                breww, "brew_outdated_formulae", return_value=["node"]
            ),
        ):
            self.assertEqual(breww.brew_compile_formulae([]), ["node"])


class BulkUpgradeHealth(unittest.TestCase):
    def run_main(self, args, *, formulae=None, casks=None, command_rc=0, profile=True):
        with (
            unittest.mock.patch.object(breww.sys, "argv", ["breww", *args]),
            unittest.mock.patch.object(
                breww,
                "get_target_brewfile",
                return_value=Path("/tmp/Brewfile") if profile else None,
            ),
            unittest.mock.patch.object(breww, "load_cu_skip", return_value=["obs"]),
            unittest.mock.patch.object(
                breww, "brew_upgradeable_formulae", return_value=["jq"]
            ),
            unittest.mock.patch.object(
                breww, "brew_compile_formulae", return_value=["libxml2"]
            ),
            unittest.mock.patch.object(
                breww, "brew_outdated_formulae", return_value=formulae or []
            ),
            unittest.mock.patch.object(
                breww, "brew_outdated_casks", return_value=casks or []
            ),
            unittest.mock.patch.object(
                breww, "brew_list_casks", return_value=["obs", "zed"]
            ),
            unittest.mock.patch.object(breww.subprocess, "run"),
            unittest.mock.patch.object(
                breww, "run_brew_command", return_value=command_rc
            ) as run,
        ):
            with self.assertRaises(SystemExit) as exited:
                breww.main()
            return exited.exception.code, [call.args[0] for call in run.call_args_list]

    def test_bulk_upgrade_builds_remaining_formulae_and_verifies(self):
        rc, commands = self.run_main(["upgrade", "--formula"])
        self.assertEqual(rc, 0)
        self.assertIn(
            ["upgrade", "--formula", "--build-from-source", "libxml2"], commands
        )

    def test_pinned_or_failed_formula_is_reported_as_failure(self):
        rc, _ = self.run_main(["upgrade", "--formula"], formulae=["pinned-lib"])
        self.assertNotEqual(rc, 0)

    def test_deferred_cask_is_reported_as_failure(self):
        rc, _ = self.run_main(["upgrade", "--cask"], casks=["obs"])
        self.assertNotEqual(rc, 0)

    def test_failed_source_build_does_not_prevent_cask_attempt(self):
        rc, commands = self.run_main(["upgrade"], casks=["zed"], command_rc=42)
        self.assertEqual(rc, 42)
        self.assertIn(["upgrade", "--cask", "zed"], commands)

    def test_unknown_profile_still_uses_upgrade_policy(self):
        rc, commands = self.run_main(["upgrade", "--formula"], profile=False)
        self.assertEqual(rc, 0)
        self.assertIn(
            ["upgrade", "--formula", "--build-from-source", "libxml2"], commands
        )

    def test_dry_run_does_not_fail_for_remaining_updates(self):
        rc, _ = self.run_main(
            ["upgrade", "--formula", "--dry-run"], formulae=["libxml2"]
        )
        self.assertEqual(rc, 0)


class OutdatedQueries(unittest.TestCase):
    def test_query_error_cannot_be_treated_as_up_to_date(self):
        with unittest.mock.patch.object(
            breww.subprocess,
            "run",
            return_value=unittest.mock.Mock(
                returncode=1, stdout="", stderr="network down"
            ),
        ):
            for query in (breww.brew_outdated_formulae, breww.brew_outdated_casks):
                with self.subTest(query=query.__name__), self.assertRaises(
                    RuntimeError
                ):
                    query()


class SourceUpgradeIntegration(unittest.TestCase):
    """Run the wrapper and bottle helper together against a fake Homebrew."""

    def run_upgrade(self, *, stuck=False, failure=False):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            brew = root / "brew"
            brew.write_text(
                f"#!{sys.executable}\n"
                + r"""
import json, os, sys
from pathlib import Path
root = Path(os.environ["FAKE_BREW_ROOT"])
args = sys.argv[1:]
with (root / "calls").open("a") as handle:
    handle.write(json.dumps(args) + "\n")
names = [] if (root / "updated").exists() else ["libxml2", "node"]
if args[0] == "list":
    print("libxml2\nnode")
elif args[0] == "outdated":
    if "--json=v2" in args:
        print(json.dumps({"formulae": [{"name": n} for n in names]}))
    else:
        print("\n".join(names))
elif args[0] == "info":
    print(json.dumps({"formulae": [
        {"name": n, "dependencies": [], "bottle": {"stable": {"files": {}}}}
        for n in names
    ]}))
elif args[0] == "upgrade":
    if os.environ["FAIL"] == "1":
        sys.exit(42)
    if os.environ["STUCK"] != "1":
        (root / "updated").touch()
"""
            )
            brew.chmod(0o755)
            proc = subprocess.run(
                [sys.executable, str(_BREWW_PATH), "upgrade", "--formula"],
                env={
                    **os.environ,
                    "PATH": str(root) + os.pathsep + os.environ["PATH"],
                    "FAKE_BREW_ROOT": str(root),
                    "MACHINE_PROFILE": "mac-personal",
                    "CHEZMOI_SOURCE_PATH": str(root),
                    "STUCK": str(int(stuck)),
                    "FAIL": str(int(failure)),
                },
                capture_output=True,
                text=True,
                timeout=15,
            )
            calls = [
                json.loads(line) for line in (root / "calls").read_text().splitlines()
            ]
            return proc, calls

    def test_unbottled_tools_and_libraries_are_actually_upgraded(self):
        proc, calls = self.run_upgrade()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn(
            ["upgrade", "--formula", "--build-from-source", "libxml2", "node"], calls
        )
        self.assertNotIn("Skipping", proc.stderr)

    def test_pinned_formula_cannot_look_updated(self):
        proc, _ = self.run_upgrade(stuck=True)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("still outdated", proc.stderr)
        self.assertIn("node", proc.stderr)

    def test_source_build_failure_is_reported(self):
        proc, _ = self.run_upgrade(failure=True)
        self.assertEqual(proc.returncode, 42)


class DumpEnv(unittest.TestCase):
    def test_extra_dumpers_disabled(self):
        env = breww.dump_env()
        for kind in ("VSCODE", "GO", "CARGO", "UV", "KREW", "NPM", "FLATPAK", "WINGET"):
            self.assertEqual(env[f"HOMEBREW_BUNDLE_DUMP_NO_{kind}"], "1")

    def test_dump_host_overlay_passes_env_to_subprocess(self):
        fake = unittest.mock.Mock(returncode=1, stderr="x", stdout="")
        with unittest.mock.patch.object(
            breww.subprocess, "run", return_value=fake
        ) as run:
            with self.assertRaises(LayerError):
                breww.dump_host_overlay(None)
        self.assertEqual(
            run.call_args.kwargs["env"]["HOMEBREW_BUNDLE_DUMP_NO_KREW"], "1"
        )


class PlanBrewCommandsBottledFilter(unittest.TestCase):
    """Bulk formula upgrades are restricted to what can be poured (Intel Tier 3)."""

    UPGRADEABLE = ["jq", "wget"]

    def test_bulk_upgrade_without_skip_restricts_formulae_and_keeps_casks(self):
        plans = breww.plan_brew_commands(
            ["upgrade"], [], upgradeable_formulae=self.UPGRADEABLE
        )
        self.assertEqual(
            plans,
            [["upgrade", "--formula", "jq", "wget"], ["upgrade", "--cask"]],
        )

    def test_bulk_upgrade_formula_flag_restricts_formulae(self):
        plans = breww.plan_brew_commands(
            ["upgrade", "--formula"], [], upgradeable_formulae=self.UPGRADEABLE
        )
        self.assertEqual(plans, [["upgrade", "--formula", "jq", "wget"]])

    def test_empty_upgradeable_runs_no_formula_upgrade(self):
        plans = breww.plan_brew_commands(
            ["upgrade", "--formula"], [], upgradeable_formulae=[]
        )
        self.assertEqual(plans, [])

    def test_empty_upgradeable_still_upgrades_casks(self):
        plans = breww.plan_brew_commands(["upgrade"], [], upgradeable_formulae=[])
        self.assertEqual(plans, [["upgrade", "--cask"]])

    def test_filter_with_skip_list_keeps_cask_skip(self):
        plans = breww.plan_brew_commands(
            ["upgrade"],
            ["obs"],
            outdated_casks=["maccy", "obs"],
            upgradeable_formulae=self.UPGRADEABLE,
        )
        self.assertEqual(
            plans,
            [["upgrade", "--formula", "jq", "wget"], ["upgrade", "--cask", "maccy"]],
        )

    def test_filter_with_skip_list_formula_only(self):
        plans = breww.plan_brew_commands(
            ["upgrade", "--formula"],
            ["obs"],
            upgradeable_formulae=self.UPGRADEABLE,
        )
        self.assertEqual(plans, [["upgrade", "--formula", "jq", "wget"]])

    def test_cask_only_upgrade_ignores_filter(self):
        plans = breww.plan_brew_commands(
            ["upgrade", "--cask"], [], upgradeable_formulae=self.UPGRADEABLE
        )
        self.assertEqual(plans, [["upgrade", "--cask"]])

    def test_explicit_formula_name_is_honored(self):
        plans = breww.plan_brew_commands(
            ["upgrade", "gh"], [], upgradeable_formulae=self.UPGRADEABLE
        )
        self.assertEqual(plans, [["upgrade", "gh"]])

    def test_none_means_filter_unavailable_so_unfiltered(self):
        plans = breww.plan_brew_commands(
            ["upgrade", "--formula"], [], upgradeable_formulae=None
        )
        self.assertEqual(plans, [["upgrade", "--formula"]])

    def test_flags_are_kept(self):
        plans = breww.plan_brew_commands(
            ["upgrade", "--formula", "--verbose"],
            [],
            upgradeable_formulae=self.UPGRADEABLE,
        )
        self.assertEqual(plans, [["upgrade", "--formula", "--verbose", "jq", "wget"]])


class BrewUpgradeableFormulae(unittest.TestCase):
    def _run(self, **kw):
        with unittest.mock.patch.object(
            breww.subprocess, "run", return_value=unittest.mock.Mock(**kw)
        ) as run:
            return breww.brew_upgradeable_formulae(), run

    def test_returns_names_from_filter_stdout(self):
        names, run = self._run(returncode=0, stdout="jq\nwget\n")
        self.assertEqual(names, ["jq", "wget"])
        self.assertIn("--mode=upgradeable", run.call_args[0][0])

    def test_empty_stdout_is_empty_list_not_none(self):
        names, _ = self._run(returncode=0, stdout="")
        self.assertEqual(names, [])

    def test_filter_error_falls_back_to_none(self):
        names, _ = self._run(returncode=1, stdout="")
        self.assertIsNone(names)

    def test_missing_filter_script_falls_back_to_none(self):
        with unittest.mock.patch.object(
            breww, "_find_bottle_filter", return_value=None
        ):
            self.assertIsNone(breww.brew_upgradeable_formulae())


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
        with unittest.mock.patch.object(
            breww, "get_hostname", return_value="other-host"
        ):
            with unittest.mock.patch.dict("os.environ", {"MACHINE_PROFILE": "mac-pro"}):
                self.assertEqual(breww.load_cu_skip(), ["obs", "logitune"])

    def test_hostname_match_is_case_insensitive(self):
        (self.tmp / "Brewfile_cu_skip_jsoyer-macOS").write_text("obs\n")
        with unittest.mock.patch.object(
            breww, "get_hostname", return_value="jsoyer-macos"
        ):
            with unittest.mock.patch.dict(
                "os.environ", {"MACHINE_PROFILE": "mac-personal"}
            ):
                self.assertEqual(breww.load_cu_skip(), ["obs"])

    def test_profile_and_hostname_lists_are_merged(self):
        (self.tmp / "Brewfile_cu_skip_mac-pro").write_text("obs\nlogitune\n")
        (self.tmp / "Brewfile_cu_skip_jsoyer-macOS").write_text("obs\nxquartz\n")
        with unittest.mock.patch.object(
            breww, "get_hostname", return_value="jsoyer-macOS"
        ):
            with unittest.mock.patch.dict("os.environ", {"MACHINE_PROFILE": "mac-pro"}):
                self.assertEqual(breww.load_cu_skip(), ["obs", "xquartz", "logitune"])


class SyncToGitStaging(unittest.TestCase):
    """sync_to_git must stage only the manifests breww itself rewrote.

    Origin: it ran `git add .` over the whole chezmoi source, so anything else
    pending there was swept into a commit labelled "update brewfiles via breww"
    and pushed unreviewed. One such commit carried 224 files, of which exactly
    one was a Brewfile.
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.host = self.tmp / "dot_private" / "Brewfile_host"
        self.base = self.tmp / "dot_private" / "Brewfile_personal"
        self.host.parent.mkdir(parents=True, exist_ok=True)
        self.host.write_text('cask "chatgpt"\n')
        self.base.write_text('brew "git"\n')
        self.stray = self.tmp / "dot_aictx" / "skills" / "unrelated.md"
        self.stray.parent.mkdir(parents=True, exist_ok=True)
        self.stray.write_text("pending work by something else\n")

    def tearDown(self):
        self._tmp.cleanup()

    def _run(self, paths):
        """Call sync_to_git and return the argv of every git call it made."""
        with (
            unittest.mock.patch.object(breww, "CHEZMOI_SOURCE_PATH", self.tmp),
            unittest.mock.patch.object(breww, "subprocess") as sub,
        ):
            sub.run.return_value = unittest.mock.Mock(returncode=0)
            sub.CalledProcessError = Exception
            breww.sync_to_git(paths)
            return [c.args[0] for c in sub.run.call_args_list if c.args]

    def _add_argv(self, calls):
        return next((c for c in calls if len(c) > 1 and c[1] == "add"), None)

    def test_stages_only_the_given_paths(self):
        add = self._add_argv(self._run([self.host, self.base]))
        self.assertIsNotNone(add, "sync_to_git never staged anything")
        staged = [a for a in add[2:] if a != "--"]
        self.assertCountEqual(staged, [str(self.host), str(self.base)])

    def test_never_stages_the_whole_tree(self):
        add = self._add_argv(self._run([self.host]))
        self.assertNotIn(".", add[2:], "sync_to_git still stages the whole tree")
        self.assertNotIn("-A", add[2:])
        self.assertNotIn("--all", add[2:])

    def test_unrelated_pending_file_is_not_staged(self):
        add = self._add_argv(self._run([self.host]))
        self.assertNotIn(str(self.stray), add[2:])

    def test_missing_path_is_skipped(self):
        absent = self.tmp / "dot_private" / "Brewfile_nope"
        add = self._add_argv(self._run([self.host, absent]))
        staged = [a for a in add[2:] if a != "--"]
        self.assertEqual(staged, [str(self.host)])

    def test_no_paths_means_no_git_calls_at_all(self):
        self.assertEqual(self._run([]), [])


if __name__ == "__main__":
    unittest.main()
