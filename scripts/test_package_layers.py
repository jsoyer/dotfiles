#!/usr/bin/env python3
"""Package selection and machine isolation, with fake managers (no installations)."""

import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "dot_local/bin"))
import package_layers as layers  # noqa: E402

PS_ENGINE = os.environ.get("PACKAGE_TEST_POWERSHELL") or shutil.which("pwsh")

CATALOG = json.loads(
    (ROOT / "dot_private/package-layers.json").read_text(encoding="utf-8")
)


class Fixture(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = self.root / "source"
        shutil.copytree(ROOT / "dot_private", self.source / "dot_private")
        self.private = self.source / "dot_private"
        self.context = layers.Context(self.source, "mac-personal", "base", "Neo")


class Selection(Fixture):
    def test_neo_gets_only_core_and_its_own_additions(self):
        (self.private / "Brewfile_OtherMac").write_text(
            'cask "discord"\n', encoding="utf-8"
        )
        (self.private / "Brewfile_Neo").write_text('cask "ghostty"\n', encoding="utf-8")
        entries = self.context.entries("brew")
        self.assertIn("brew:chezmoi", entries)
        self.assertIn("brew:mise", entries)
        self.assertIn("cask:ghostty", entries)
        self.assertNotIn("cask:discord", entries)
        self.assertNotIn("go:golang.org/x/tools/gopls", entries)
        self.assertEqual(len(entries), 21)

    def test_every_platform_has_a_base_without_legacy_gui_or_languages(self):
        forbidden = {
            "node",
            "nodejs",
            "npm",
            "go",
            "golang",
            "rust",
            "cargo",
            "docker",
            "claude-code",
        }
        for mp in CATALOG["profiles"]:
            context = layers.Context(self.source, mp, "base", "LayerTest")
            for manager in context.managers:
                with self.subTest(profile=mp, manager=manager):
                    entries = context.entries(manager)
                    names = {key.split(":", 1)[-1] for key in entries}
                    self.assertFalse(names & forbidden)
                    self.assertFalse(any(key.startswith("cask:") for key in entries))
                    if manager in ("flatpak", "snap", "aur"):
                        self.assertFalse(entries)

    def test_legacy_manifests_are_byte_for_byte_preserved(self):
        baseline = json.loads(
            (ROOT / "docs/PACKAGE_BASELINE_2026-11-14.json").read_text(encoding="utf-8")
        )
        for name, expected in baseline["files"].items():
            if expected["scope"] != "compatibility-shared":
                continue
            with self.subTest(file=name):
                raw = (ROOT / "dot_private" / name).read_bytes().replace(b"\r\n", b"\n")
                self.assertEqual(hashlib.sha256(raw).hexdigest(), expected["sha256"])

    def test_legacy_mac_preserves_the_full_shared_package_list(self):
        context = layers.Context(self.source, "mac-personal", "legacy", "Neo")
        self.assertEqual(
            context.selection("brew")["shared"], ["Brewfile_macos", "Brewfile_personal"]
        )
        self.assertGreater(len(context.entries("brew")), 400)

    def test_usage_is_optional_and_small(self):
        context = layers.Context(self.source, "mac-personal", "personal", "Neo")
        self.assertIn("brew:lazygit", context.entries("brew"))
        self.assertLess(len(context.entries("brew")), 35)

    def test_unknown_profiles_and_path_traversal_are_rejected(self):
        for mp, pp, host in [
            ("unknown", "base", "Neo"),
            ("windows", "typo", "PC"),
            ("windows", "base", "../other"),
        ]:
            with self.subTest(mp=mp, pp=pp, host=host), self.assertRaises(
                layers.LayerError
            ):
                layers.Context(self.source, mp, pp, host)
        with self.assertRaises(layers.LayerError):
            layers.Context(self.source, "mac-personal", "base", "macos").selection(
                "brew"
            )

    def test_conflicting_options_fail_instead_of_losing_metadata(self):
        (self.private / "Brewfile_Neo").write_text(
            'brew "git", args: ["HEAD"]\n', encoding="utf-8"
        )
        with self.assertRaises(layers.LayerError):
            self.context.entries("brew")

    def test_short_hostname_is_shared_with_templates(self):
        context = layers.Context(self.source, "windows", "base", "WindowsA.example.net")
        self.assertEqual(context.selection("scoop")["host"], "Scoopfile_WindowsA.json")


class Edits(Fixture):
    def test_uninstall_excludes_locally_without_touching_either_shared_layer(self):
        context = layers.Context(self.source, "mac-personal", "personal", "Neo")
        before = {
            name: (self.private / name).read_bytes()
            for name in context.selection("brew")["shared"]
        }
        layers.record(context, "brew", "remove", ["git", "lazygit"])
        self.assertNotIn("brew:git", context.entries("brew"))
        self.assertNotIn("brew:lazygit", context.entries("brew"))
        other = layers.Context(self.source, "mac-personal", "personal", "OtherMac")
        self.assertIn("brew:git", other.entries("brew"))
        self.assertIn("brew:lazygit", other.entries("brew"))
        for name, original in before.items():
            self.assertEqual((self.private / name).read_bytes(), original)
        layers.record(context, "brew", "add", ["git"])
        self.assertIn("brew:git", context.entries("brew"))

    def test_remove_last_or_absent_machine_package_does_not_fail(self):
        context = layers.Context(self.source, "ubuntu-desktop", "base", "LinuxA")
        layers.record(context, "apt", "remove", ["missing"])
        layers.record(context, "apt", "add", ["htop"])
        layers.record(context, "apt", "remove", ["htop"])
        self.assertEqual(
            (self.private / "Aptfile_LinuxA").read_text(encoding="utf-8"), ""
        )

    def test_aur_additions_never_modify_shared_aur_list(self):
        context = layers.Context(self.source, "arch-desktop", "personal", "ArchA")
        original = (self.private / "Pacfile_aur_desktop").read_bytes()
        layers.record(context, "aur", "add", ["rtk-bin"])
        self.assertEqual(
            (self.private / "Pacfile_aur_ArchA").read_text(encoding="utf-8"),
            "rtk-bin\n",
        )
        self.assertEqual((self.private / "Pacfile_aur_desktop").read_bytes(), original)

    def test_dump_subtracts_all_shared_layers_and_preserves_non_dumped_entries(self):
        context = layers.Context(self.source, "mac-personal", "personal", "Neo")
        host = self.private / "Brewfile_Neo"
        host.write_text(
            'go "example.org/tool/cmd/tool"\nnpm "@scope/tool"\n', encoding="utf-8"
        )
        installed = {
            "brew:git": 'brew "git"',
            "brew:lazygit": 'brew "lazygit"',
            "cask:ghostty": 'cask "ghostty"',
        }
        layers.dump_overlay(context, "brew", installed)
        self.assertEqual(
            set(layers.parse_entries(host, "brew")),
            {"go:example.org/tool/cmd/tool", "npm:@scope/tool", "cask:ghostty"},
        )

    def test_promotion_requires_an_explicit_nonlegacy_layer(self):
        (self.private / "Brewfile_Neo").write_text('cask "ghostty"\n', encoding="utf-8")
        with self.assertRaises(layers.LayerError):
            layers.promote(self.context, "brew", "ghostty", "usage")
        context = layers.Context(self.source, "mac-personal", "personal", "Neo")
        layers.promote(context, "brew", "ghostty", "usage")
        self.assertNotIn("cask:ghostty", context.entries("brew", layer="machine"))
        self.assertIn("cask:ghostty", context.entries("brew", shared=True))

    def test_migration_previews_then_preserves_only_this_machine(self):
        context = layers.Context(self.source, "mac-personal", "legacy", "Neo")
        (self.private / "Brewfile_OtherMac").write_text(
            'cask "a-different-app"\n', encoding="utf-8"
        )
        old = context.entries("brew")
        config = self.root / "chezmoi.toml"
        config.write_text(
            '[data]\nmachine_profile="mac-personal"\ncustom_setting="keep"\n',
            encoding="utf-8",
        )
        report = layers.migrate(context, "personal", config=config)
        self.assertNotIn("backup", report)
        self.assertNotIn("package_profile", config.read_text(encoding="utf-8"))
        layers.migrate(context, "personal", config=config, write=True)
        new = layers.Context(self.source, "mac-personal", "personal", "Neo")
        self.assertLessEqual(set(old), set(new.entries("brew")))
        self.assertNotIn("cask:a-different-app", new.entries("brew"))
        self.assertIn(
            'package_profile = "personal"', config.read_text(encoding="utf-8")
        )
        self.assertIn('custom_setting="keep"', config.read_text(encoding="utf-8"))
        self.assertEqual(
            (self.private / "Brewfile_OtherMac").read_text(encoding="utf-8"),
            'cask "a-different-app"\n',
        )

    def test_failed_native_install_does_not_record_or_publish(self):
        context = layers.Context(self.source, "ubuntu-desktop", "base", "LinuxA")
        with patch.object(
            layers.subprocess, "run", return_value=subprocess.CompletedProcess([], 42)
        ):
            self.assertEqual(layers.wrapper(context, "apt", ["install", "htop"]), 42)
        self.assertFalse((self.private / "Aptfile_LinuxA").exists())

    def test_each_unix_wrapper_records_only_its_machine_after_success(self):
        cases = [
            ("ubuntu-desktop", "apt", ["install", "htop"], "htop"),
            ("fedora-desktop", "dnf", ["install", "htop"], "htop"),
            ("arch-desktop", "pacman", ["-S", "htop"], "htop"),
            ("arch-desktop", "aur", ["-S", "rtk-bin"], "rtk-bin"),
            ("fedora-atomic", "rpm", ["install", "openssh-server"], "openssh-server"),
            (
                "fedora-desktop",
                "flatpak",
                ["install", "flathub", "org.example.App"],
                "org.example.App",
            ),
            (
                "ubuntu-desktop",
                "snap",
                ["install", "example-app", "--classic"],
                "example-app",
            ),
        ]
        for mp, manager, argv, name in cases:
            with self.subTest(manager=manager):
                context = layers.Context(self.source, mp, "base", "LocalHost")
                before = {
                    path.name: path.read_bytes()
                    for path in self.private.iterdir()
                    if path.is_file()
                }
                with patch.object(
                    layers.subprocess,
                    "run",
                    return_value=subprocess.CompletedProcess([], 0),
                ), patch.object(layers, "sync_manifests"), patch.object(
                    layers.os, "geteuid", return_value=1000, create=True
                ):
                    self.assertEqual(layers.wrapper(context, manager, argv), 0)
                path = self.private / context.selection(manager)["host"]
                self.assertIn(name, layers.parse_entries(path, manager))
                for filename in context.selection(manager)["shared"]:
                    self.assertEqual(
                        (self.private / filename).read_bytes(), before[filename]
                    )

    def test_simulation_does_not_claim_a_package_was_installed(self):
        context = layers.Context(self.source, "ubuntu-desktop", "base", "LinuxA")
        with patch.object(
            layers.subprocess, "run", return_value=subprocess.CompletedProcess([], 0)
        ), patch.object(layers, "sync_manifests") as sync:
            self.assertEqual(
                layers.wrapper(context, "apt", ["install", "--simulate", "htop"]), 0
            )
            sync.assert_not_called()
        self.assertFalse((self.private / "Aptfile_LinuxA").exists())

    def test_failed_inventory_never_replaces_a_good_overlay(self):
        context = layers.Context(self.source, "ubuntu-desktop", "base", "LinuxA")
        path = self.private / "Aptfile_LinuxA"
        path.write_text("important-package\n", encoding="utf-8")
        with patch.object(
            layers.subprocess,
            "run",
            side_effect=subprocess.CalledProcessError(1, "apt-mark"),
        ):
            with self.assertRaises(subprocess.CalledProcessError):
                layers.wrapper(context, "apt", ["dump"])
        self.assertEqual(path.read_text(encoding="utf-8"), "important-package\n")

    def test_reinstalling_an_auto_detected_cask_clears_only_its_exclusion(self):
        self.context.exclude_file.write_text(
            json.dumps({"brew": ["cask:ghostty", "brew:git"]}), encoding="utf-8"
        )
        layers.clear_exclusions(self.context, ["ghostty"])
        self.assertEqual(self.context.exclusions("brew"), ["brew:git"])
        self.assertFalse((self.private / "Brewfile_Neo").exists())

    def test_git_commit_is_limited_even_with_unrelated_staged_files(self):
        with patch.object(layers.subprocess, "run") as run:
            run.return_value = subprocess.CompletedProcess([], 0, stdout=" M file\n")
            path = self.private / "Aptfile_LinuxA"
            layers.sync_manifests(self.context, [path], "test")
            commit = [
                call.args[0]
                for call in run.call_args_list
                if call.args[0][:2] == ["git", "commit"]
            ][0]
            self.assertIn("--only", commit)
            self.assertEqual(commit[-1], str(path.resolve()))


@unittest.skipUnless(shutil.which("chezmoi"), "chezmoi not installed")
class Templates(Fixture):
    def setUp(self):
        super().setUp()
        shutil.copytree(ROOT / ".chezmoitemplates", self.source / ".chezmoitemplates")
        (self.source / ".chezmoitemplates/can-sudo").write_text(
            "true", encoding="utf-8"
        )
        (self.source / "dot_local/bin").mkdir(parents=True)
        shutil.copy2(
            ROOT / "dot_local/bin/executable_brewfile-filter-bottled",
            self.source / "dot_local/bin/executable_brewfile-filter-bottled",
        )
        self.config = self.root / "empty.toml"
        self.config.write_text("", encoding="utf-8")

    def render(self, text, mp="mac-personal", pp="base", arch="arm64", host="Neo"):
        os_name = CATALOG["profiles"][mp]["os"]
        data = {
            "machine_profile": mp,
            "package_profile": pp,
            "install_mas": False,
            "install_ocx": False,
            "install_docker": False,
        }
        preamble = "".join(
            "{{- $_ := set . %s %s -}}"
            % (
                json.dumps(key),
                json.dumps(value) if isinstance(value, str) else str(value).lower(),
            )
            for key, value in data.items()
        )
        preamble += "".join(
            "{{- $_ := set .chezmoi %s %s -}}" % (json.dumps(key), json.dumps(value))
            for key, value in {"os": os_name, "arch": arch, "hostname": host}.items()
        )
        result = subprocess.run(
            [
                "chezmoi",
                "--config",
                str(self.config),
                "--source",
                str(self.source),
                "execute-template",
            ],
            input=preamble + text,
            text=True,
            capture_output=True,
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def test_template_and_wrapper_selection_agree_for_every_supported_profile(self):
        for mp in CATALOG["profiles"]:
            for pp in layers.PROFILES:
                context = layers.Context(self.source, mp, pp, "LayerTest")
                for manager in context.managers:
                    with self.subTest(mp=mp, pp=pp, manager=manager):
                        template = (
                            '{{ includeTemplate "package-files" (dict "data" . "manager" "%s") }}'
                            % manager
                        )
                        actual = json.loads(
                            self.render(template, mp, pp, host="LayerTest")
                        )
                        self.assertEqual(actual, context.selection(manager))

    def test_effective_brewfile_matches_preview_and_stays_stable(self):
        text = (
            '{{ includeTemplate "package-manifest" (dict "data" . "manager" "brew") }}'
        )
        for pp in layers.PROFILES:
            with self.subTest(pp=pp):
                rendered = self.render(text, pp=pp)
                path = self.root / "rendered.Brewfile"
                path.write_text(rendered, encoding="utf-8")
                expected = layers.Context(
                    self.source, "mac-personal", pp, "Neo"
                ).entries("brew")
                expected = {
                    key: value
                    for key, value in expected.items()
                    if not key.startswith("mas:")
                }
                self.assertEqual(layers.parse_entries(path, "brew"), expected)
                self.assertEqual(rendered, self.render(text, pp=pp))

    def test_optional_installers_are_empty_in_base(self):
        names = [
            "run_once_01-install-1password.sh.tmpl",
            "run_once_06-install-claude-plugins.sh.tmpl",
            "run_once_11-codex-brew-channel.sh.tmpl",
            "run_once_after_14-install-herdr.sh.tmpl",
        ]
        for name in names:
            with self.subTest(script=name):
                self.assertFalse(
                    self.render(
                        (ROOT / ".chezmoiscripts/02-install" / name).read_text(
                            encoding="utf-8"
                        )
                    ).strip()
                )

    def test_intel_base_selects_shims_and_python_without_full_development_toolchains(
        self,
    ):
        text = (ROOT / "dot_config/mise/config.toml.tmpl").read_text(encoding="utf-8")
        output = self.render(text, arch="amd64")
        self.assertIn('"aqua:twpayne/chezmoi" = "latest"', output)
        self.assertIn('"aqua:carapace-sh/carapace-bin" = "latest"', output)
        self.assertIn('python = "latest"', output)
        for tool in (
            "node",
            "go",
            "rust",
            "java",
            "conda:ruby",
            "aqua:helm/helm",
            "aqua:derailed/k9s",
        ):
            self.assertNotIn(tool + " =", output)
            self.assertNotIn('"' + tool + '" =', output)

    def test_linux_scripts_and_macos_bash_parse_on_available_bash(self):
        if os.name == "nt" or not shutil.which("bash"):
            self.skipTest("Bash not available")
        paths = [
            ROOT / ".chezmoiscripts/02-install/run_onchange_03-brew-bundle.sh.tmpl",
            ROOT
            / ".chezmoiscripts/02-install/run_onchange_04-install-linux-packages.sh.tmpl",
        ]
        for mp in CATALOG["profiles"]:
            if mp == "windows":
                continue
            for path in paths:
                with self.subTest(profile=mp, script=path.name):
                    rendered = self.render(path.read_text(encoding="utf-8"), mp=mp)
                    result = subprocess.run(
                        ["bash", "-n"], input=rendered, text=True, capture_output=True
                    )
                    self.assertEqual(result.returncode, 0, result.stderr)

    def test_legacy_linux_local_removal_is_filtered_on_next_apply(self):
        if os.name == "nt" or not shutil.which("bash"):
            self.skipTest("Native Bash check")
        context = layers.Context(self.source, "ubuntu-desktop", "legacy", "Neo")
        layers.record(context, "apt", "remove", ["git"])
        rendered = self.render(
            '{{ includeTemplate "package-exclusion-filter" . }}',
            mp="ubuntu-desktop",
            pp="legacy",
        )
        result = subprocess.run(
            ["bash"],
            input=rendered + "\n_filter_pkg_exclusions apt <<EOF\ngit\ntmux\nEOF\n",
            text=True,
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "tmux\n")

    def test_legacy_host_app_store_choices_are_preserved(self):
        (self.private / "Brewfile_Neo").write_text(
            'mas "Explicit App", id: 123\n', encoding="utf-8"
        )
        text = (
            '{{ includeTemplate "package-manifest" (dict "data" . "manager" "brew") }}'
        )
        self.assertIn('mas "Explicit App"', self.render(text, pp="legacy"))
        self.assertNotIn('mas "Explicit App"', self.render(text, pp="base"))

    @unittest.skipUnless(PS_ENGINE, "PowerShell not installed")
    def test_windows_installer_and_shell_profiles_parse_natively(self):
        templates = [
            ROOT
            / ".chezmoiscripts/02-install/run_onchange_04-install-windows-packages.ps1.tmpl",
            ROOT / "Documents/PowerShell/Microsoft.PowerShell_profile.ps1.tmpl",
        ]
        check = self.root / "check.ps1"
        check.write_text(
            "param($Path)\n$tokens=$null; $errors=$null\n[System.Management.Automation.Language.Parser]::ParseFile($Path,[ref]$tokens,[ref]$errors) | Out-Null\nif ($errors.Count) { $errors | Format-List; exit 1 }\n",
            encoding="utf-8",
        )
        for pp in ("base", "legacy"):
            for template in templates:
                with self.subTest(template=template.name, profile=pp):
                    output = self.root / "rendered.ps1"
                    output.write_text(
                        self.render(
                            template.read_text(encoding="utf-8"), mp="windows", pp=pp
                        ),
                        encoding="utf-8",
                    )
                    result = subprocess.run(
                        [PS_ENGINE, "-NoProfile", "-File", str(check), str(output)],
                        text=True,
                        capture_output=True,
                    )
                    self.assertEqual(
                        result.returncode, 0, result.stdout + result.stderr
                    )

    def test_new_init_defaults_to_base_and_reinit_preserves_legacy(self):
        shutil.copy2(ROOT / ".chezmoi.toml.tmpl", self.source / ".chezmoi.toml.tmpl")
        # This fixture represents a genuinely new host, not a clone of this workstation.
        for prefix in CATALOG["host_prefixes"].values():
            for suffix in ("", ".json"):
                (
                    self.private
                    / (prefix + layers.short_hostname(platform.node()) + suffix)
                ).unlink(missing_ok=True)
        self.config.unlink()
        environment = dict(os.environ, CI="1")
        environment.pop("DOTFILES_PACKAGE_PROFILE", None)
        command = [
            "chezmoi",
            "--config",
            str(self.config),
            "--source",
            str(self.source),
            "--destination",
            str(self.root / "home"),
            "--persistent-state",
            str(self.root / "state.boltdb"),
            "init",
            "--no-tty",
            "--promptDefaults",
        ]
        result = subprocess.run(
            command, env=environment, text=True, capture_output=True
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(
            'package_profile = "base"', self.config.read_text(encoding="utf-8")
        )
        self.config.write_text(
            '[data]\nmachine_profile="ubuntu-desktop"\n', encoding="utf-8"
        )
        result = subprocess.run(
            command, env=environment, text=True, capture_output=True
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(
            'package_profile = "legacy"', self.config.read_text(encoding="utf-8")
        )
        environment["DOTFILES_PACKAGE_PROFILE"] = "base"
        result = subprocess.run(
            command, env=environment, text=True, capture_output=True
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(
            'package_profile = "base"', self.config.read_text(encoding="utf-8")
        )

    def test_new_host_cannot_silently_reuse_another_machines_packages(self):
        shutil.copy2(ROOT / ".chezmoi.toml.tmpl", self.source / ".chezmoi.toml.tmpl")
        self.config.unlink()
        manager = "scoop" if os.name == "nt" else "brew"
        suffix = ".json" if manager == "scoop" else ""
        path = self.private / (
            CATALOG["host_prefixes"][manager]
            + layers.short_hostname(platform.node())
            + suffix
        )
        path.write_text(
            '{"apps":[],"buckets":[]}'
            if manager == "scoop"
            else 'cask "another-machines-app"\n',
            encoding="utf-8",
        )
        environment = dict(os.environ, CI="1", DOTFILES_PACKAGE_PROFILE="base")
        environment.pop("DOTFILES_REUSE_HOST_PACKAGES", None)
        command = [
            "chezmoi",
            "--config",
            str(self.config),
            "--source",
            str(self.source),
            "--destination",
            str(self.root / "home"),
            "--persistent-state",
            str(self.root / "state.boltdb"),
            "init",
            "--no-tty",
            "--promptDefaults",
        ]
        result = subprocess.run(
            command, env=environment, text=True, capture_output=True
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("already owns package lists", result.stderr)
        environment["DOTFILES_REUSE_HOST_PACKAGES"] = "1"
        result = subprocess.run(
            command, env=environment, text=True, capture_output=True
        )
        self.assertEqual(result.returncode, 0, result.stderr)


@unittest.skipUnless(PS_ENGINE, "PowerShell not installed")
class Scoop(Fixture):
    def run_scoop(self, action, names, *, fail=False, malformed=False):
        context = layers.Context(self.source, "windows", "base", "WindowsA")
        (self.root / "selection.json").write_text(
            json.dumps(context.selection("scoop")), encoding="utf-8"
        )
        (self.root / "export.json").write_text(
            "broken"
            if malformed
            else json.dumps(
                {
                    "buckets": [{"name": "main"}],
                    "apps": [
                        {"name": "git", "bucket": "main"},
                        {"name": "machine-app", "bucket": "main", "version": "1.0"},
                    ],
                }
            ),
            encoding="utf-8",
        )
        harness = self.root / "harness.ps1"
        harness.write_text(
            r"""
param($Source, $Fixture, $Wrapper, $Operation, $Names, $Fail)
$env:CHEZMOI_SOURCE_PATH = $Source
$global:Fixture = $Fixture
$global:Fail = $Fail -eq 'true'
function global:chezmoi { $global:LASTEXITCODE = 0; Get-Content (Join-Path $global:Fixture 'selection.json') -Raw }
function global:scoop {
    param($Operation, [Parameter(ValueFromRemainingArguments)]$Rest)
    $global:LASTEXITCODE = 0
    if ($global:Fail -and $Operation -ne 'export') { $global:LASTEXITCODE = 42; return }
    if ($Operation -eq 'export') { Get-Content (Join-Path $global:Fixture 'export.json') -Raw }
}
function global:git {
    param([Parameter(ValueFromRemainingArguments)]$Rest)
    $global:LASTEXITCODE = 0
    Add-Content -Path (Join-Path $global:Fixture 'git.log') -Value ($Rest -join ' ')
    if ($Rest[0] -eq 'status') { ' M tracked-manifest' }
}
& $Wrapper $Operation ($Names -split ',')
exit $LASTEXITCODE
""",
            encoding="utf-8",
        )
        return subprocess.run(
            [
                PS_ENGINE,
                "-NoProfile",
                "-File",
                str(harness),
                str(self.source),
                str(self.root),
                str(ROOT / "dot_local/bin/scoopw.ps1"),
                action,
                ",".join(names),
                str(fail).lower(),
            ],
            text=True,
            capture_output=True,
        )

    def test_windows_install_only_records_machine_delta_without_pin(self):
        other = self.private / "Scoopfile_WindowsB.json"
        other.write_text('{"apps":[],"buckets":[]}', encoding="utf-8")
        result = self.run_scoop("install", ["machine-app"])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        manifest = json.loads(
            (self.private / "Scoopfile_WindowsA.json").read_text(encoding="utf-8-sig")
        )
        self.assertEqual(manifest["apps"], [{"name": "machine-app", "bucket": "main"}])
        self.assertEqual(other.read_text(encoding="utf-8"), '{"apps":[],"buckets":[]}')
        self.assertIn(
            "commit --only", (self.root / "git.log").read_text(encoding="utf-8")
        )

    def test_failed_install_and_invalid_export_leave_manifest_unchanged(self):
        path = self.private / "Scoopfile_WindowsA.json"
        original = '{"apps":[{"name":"important"}],"buckets":[]}'
        path.write_text(original, encoding="utf-8")
        for options in ({"fail": True}, {"malformed": True}):
            with self.subTest(options=options):
                result = self.run_scoop("install", ["machine-app"], **options)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(path.read_text(encoding="utf-8"), original)
                self.assertFalse((self.root / "git.log").exists())


if __name__ == "__main__":
    unittest.main()
