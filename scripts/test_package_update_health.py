#!/usr/bin/env python3
"""Package update failures must survive independent steps (no real updates)."""

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SYSUP = ROOT / "dot_local/bin/executable_sysup"
UPDATE = ROOT / ".chezmoiscripts/04-update/run_onchange_update-homebrew.sh.tmpl"


class SysupHealth(unittest.TestCase):
    def run_sysup(self, failure=""):
        with tempfile.TemporaryDirectory() as tmp:
            # Source functions without running the entrypoint, then simulate a Mac.
            body = SYSUP.read_text().rsplit('\nsysup "$@"', 1)[0]
            body += r'''
OSTYPE=darwin
uname() { echo Darwin; }
breww() { echo "breww $*"; [[ "$FAIL" != breww ]]; }
brew() { echo "brew $*"; return 0; }
mas() { echo "mas $*"; [[ "$FAIL" != mas ]]; }
mise() { echo "mise $*"; [[ "$FAIL" != mise ]]; }
mise-java-macos-link() { return 0; }
_ai_brew_owned() { return 1; }
update-omz() { :; }
update-ai() { :; }
_update_herdr_if_present() { :; }
sysup
exit "$_sysup_rc"
'''
            return subprocess.run(
                ["bash", "-c", body],
                env={**os.environ, "HOME": tmp, "FAIL": failure, "SYSUP_NO_OS_CHECK": "1"},
                text=True, capture_output=True, timeout=15,
            )

    def test_success(self):
        proc = self.run_sysup()
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_each_package_manager_failure_is_preserved(self):
        for failure in ("breww", "mas", "mise"):
            with self.subTest(failure=failure):
                proc = self.run_sysup(failure)
                self.assertNotEqual(proc.returncode, 0)
                self.assertIn("breww cu -a", proc.stdout)
                self.assertIn("mas upgrade", proc.stdout)
                self.assertIn("brew cleanup", proc.stdout)

    def test_mise_runs_before_homebrew(self):
        proc = self.run_sysup()
        self.assertLess(proc.stdout.index("mise upgrade"), proc.stdout.index("breww upgrade"))


@unittest.skipUnless(shutil.which("chezmoi"), "chezmoi required to render the script")
class ChezmoiHomebrewHealth(unittest.TestCase):
    def run_update(self, failure="", profile="mac-personal", npm_case="empty"):
        preamble = (
            '{{- $_ := set . "machine_profile" "%s" -}}'
            '{{- $_ := set .chezmoi "os" "darwin" -}}\n' % profile
        )
        rendered = subprocess.run(
            ["chezmoi", "execute-template", "--source", str(ROOT)],
            input=preamble + UPDATE.read_text(), text=True, capture_output=True, timeout=30,
        )
        self.assertEqual(rendered.returncode, 0, rendered.stderr)
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            bins = base / "bin"
            bins.mkdir()
            wrapper = base / "dot_local/bin/executable_breww"
            wrapper.parent.mkdir(parents=True)
            wrapper.write_text(
                'import os,sys\n'
                'print("wrapper " + " ".join(sys.argv[1:]))\n'
                'sys.exit(42 if os.environ["FAIL"] in sys.argv[1:] else 0)\n'
            )
            for name, body in {
                "brew": 'echo "brew $*"\nexit 0\n',
                "npm": r'''
case "$1" in
    root)
        [ "$NPM_CASE" != root-error ] || exit 42
        printf '%s\n' "$NPM_TEST_ROOT"
        ;;
    ls)
        if [ ! -d "$NPM_TEST_ROOT" ]; then
            echo "ENOENT: global npm root does not exist" >&2
            exit 254
        fi
        [ "$NPM_CASE" != ls-error ] || { echo "EACCES" >&2; exit 1; }
        if [ "$NPM_CASE" = malformed ]; then
            echo "invalid JSON"
        elif [ "$NPM_CASE" = packages ] || [ "$NPM_CASE" = install-error ]; then
            echo '{"dependencies":{"@scope/tool":{"version":"1"},"plain":{"version":"0.2"}}}'
        else
            echo '{}'
        fi
        ;;
    install)
        echo "npm $*"
        [ "$NPM_CASE" != install-error ] || exit 42
        ;;
esac
''',
            }.items():
                path = bins / name
                path.write_text("#!/bin/sh\n" + body)
                path.chmod(0o755)
            return subprocess.run(
                ["bash", "-c", rendered.stdout.replace(str(ROOT), str(base))],
                env={**os.environ, "PATH": str(bins) + ":/usr/bin:/bin", "FAIL": failure,
                     "CHEZMOI_AUTOUPDATE": "0", "HOME": str(base), "NPM_CASE": npm_case,
                     "NPM_TEST_ROOT": str(base / "npm globals/lib/node_modules")},
                text=True, capture_output=True, timeout=15,
            )

    def test_formula_failure_does_not_hide_or_prevent_cask_update(self):
        proc = self.run_update("--formula")
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("wrapper upgrade --greedy --cask", proc.stdout)
        self.assertIn("brew cleanup", proc.stdout)
        self.assertNotIn("Upgrade complete!", proc.stdout)

    def test_cask_failure_is_not_hidden(self):
        proc = self.run_update("--cask")
        self.assertNotEqual(proc.returncode, 0)

    def test_success_and_work_mac_profile(self):
        proc = self.run_update(profile="mac-pro")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("wrapper upgrade --cask", proc.stdout)
        self.assertNotIn("--greedy", proc.stdout)

    def test_missing_global_prefix_is_initialized_as_empty(self):
        proc = self.run_update(profile="mac-pro")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("No global npm packages", proc.stdout)
        self.assertNotIn("npm install", proc.stdout)

    def test_json_inventory_updates_scoped_and_regular_packages(self):
        proc = self.run_update(npm_case="packages")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("npm install -g @scope/tool@latest", proc.stdout)
        self.assertIn("npm install -g plain@latest", proc.stdout)

    def test_real_npm_errors_still_fail_the_update(self):
        for case in ("root-error", "ls-error", "malformed", "install-error"):
            with self.subTest(case=case):
                proc = self.run_update(npm_case=case)
                self.assertNotEqual(proc.returncode, 0)
                self.assertNotIn("Upgrade complete!", proc.stdout)
                if case == "install-error":
                    self.assertIn("npm install -g plain@latest", proc.stdout)


if __name__ == "__main__":
    unittest.main()
