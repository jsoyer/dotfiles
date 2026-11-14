#!/usr/bin/env python3
"""Exercise generated files in isolated homes with fake 1Password and real parsers."""

import contextlib
from concurrent.futures import ThreadPoolExecutor
import importlib.machinery
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "dot_local/bin/executable_dotfiles-generated-config"
loader = importlib.machinery.SourceFileLoader("generated_config", str(HELPER))
spec = importlib.util.spec_from_loader(loader.name, loader)
generated = importlib.util.module_from_spec(spec)
loader.exec_module(generated)


@unittest.skipUnless(
    os.name == "posix" and shutil.which("ssh"), "Unix OpenSSH required"
)
class GeneratedFiles(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.home = Path(self.temporary.name) / "home with spaces"
        self.ssh = self.home / ".ssh/config"
        self.zsh = self.home / ".zsh/secrets.zsh"
        self.bash = self.home / ".bash/secrets.bash"
        for path, content in (
            (
                self.ssh,
                b"Host private\n  HostName 192.0.2.42\n  User operator\n  UseKeychain yes\n",
            ),
            (self.zsh, b"export OLD_ZSH=previous\n"),
            (self.bash, b"export OLD_BASH=previous\n"),
        ):
            path.parent.mkdir(parents=True, mode=0o700)
            path.write_bytes(content)
            path.chmod(0o600)
        self.original = {
            path: path.read_bytes() for path in (self.ssh, self.zsh, self.bash)
        }
        self.calls = []
        self.raw = json.dumps(
            {"fields": [{"label": "GITHUB_TOKEN", "value": "synthetic-token"}]}
        ).encode()
        self.document = b"Host updated\n  HostName 192.0.2.43\n  User new-user\n"
        self.real_run = subprocess.run

        def run(command, **kwargs):
            if command[0] != "op":
                return self.real_run(command, **kwargs)
            self.calls.append(command)
            content = self.document if command[1:3] == ["document", "get"] else self.raw
            return subprocess.CompletedProcess(command, 0, stdout=content, stderr=b"")

        self.runner = patch.object(generated.subprocess, "run", side_effect=run)
        self.runner.start()
        self.addCleanup(self.runner.stop)
        self.op_path = patch.object(generated.shutil, "which", return_value="/fake/op")
        self.op_path.start()
        self.addCleanup(self.op_path.stop)

    def assert_original(self):
        for path, content in self.original.items():
            self.assertEqual(path.read_bytes(), content)

    def test_linux_preserves_hosts_and_uses_a_dedicated_global_fragment(self):
        generated.generate_ssh(self.home, "linux")
        self.assertTrue(self.ssh.read_bytes().endswith(self.original[self.ssh]))
        fragment = self.home / ".ssh/config.d/chezmoi.conf"
        self.assertEqual(fragment.read_text(), "IgnoreUnknown UseKeychain\n")
        parsed = self.real_run(
            ["ssh", "-G", "-F", str(self.ssh), "private"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(parsed.returncode, 0, parsed.stderr)
        self.assertIn("hostname 192.0.2.42", parsed.stdout)
        self.assertIn("user operator", parsed.stdout)
        backups = list(self.ssh.parent.glob(".config.before-chezmoi-*"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_bytes(), self.original[self.ssh])
        self.assertFalse(self.calls)

    def test_linux_is_idempotent_and_does_not_duplicate_includes(self):
        generated.generate_ssh(self.home, "linux")
        before, modified = self.ssh.read_bytes(), self.ssh.stat().st_mtime_ns
        generated.generate_ssh(self.home, "linux")
        self.assertEqual(self.ssh.read_bytes(), before)
        self.assertEqual(self.ssh.stat().st_mtime_ns, modified)
        self.assertEqual(len(list(self.ssh.parent.glob(".config.before-chezmoi-*"))), 1)

    def test_linux_keeps_existing_global_ignore_patterns(self):
        self.ssh.write_bytes(
            b"IgnoreUnknown FutureOption\nFutureOption yes\n" + self.original[self.ssh]
        )
        generated.generate_ssh(self.home, "linux")
        parsed = self.real_run(
            ["ssh", "-G", "-F", str(self.ssh), "private"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(parsed.returncode, 0, parsed.stderr)
        self.assertIn("hostname 192.0.2.42", parsed.stdout)

    def test_macos_publishes_valid_1password_document_and_keeps_a_private_backup(self):
        generated.generate_ssh(self.home, "darwin")
        self.assertEqual(self.ssh.read_bytes(), self.document)
        backup = next(self.ssh.parent.glob(".config.before-chezmoi-*"))
        self.assertEqual(backup.read_bytes(), self.original[self.ssh])
        self.assertEqual(backup.stat().st_mode & 0o777, 0o600)

    def test_invalid_or_empty_ssh_document_preserves_previous_configuration(self):
        for data in (
            b"",
            b"\n  ",
            b"\xff",
            b"Host missing\nInvalidOption yes\n",
            b"Host \x00bad",
        ):
            with self.subTest(document=data), self.assertRaises(generated.ConfigError):
                self.document = data
                generated.generate_ssh(self.home, "darwin")
            self.assert_original()

    def test_ssh_validation_does_not_execute_match_or_included_commands(self):
        marker = self.home / "must-not-exist"
        included = self.home / "untrusted-include"
        included.write_text(f'Match exec "touch {marker}"\n  User unexpected\n')
        self.document = (
            f'Include "{included}"\nMatch exec "touch {marker}"\nHost known\n  User operator\n'
        ).encode()
        generated.generate_ssh(self.home, "darwin")
        self.assertFalse(marker.exists())
        self.assertEqual(self.ssh.read_bytes(), self.document)

    def test_read_failures_do_not_leak_output_or_replace_either_secret_file(self):
        failure = subprocess.CompletedProcess(
            ["op"], 42, stdout=b"private-partial-content", stderr=b"secret-error"
        )
        output = io.StringIO()
        with patch.object(
            generated.subprocess, "run", return_value=failure
        ), contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            with self.assertRaises(generated.ConfigError) as raised:
                generated.generate_secrets(self.home)
        self.assert_original()
        self.assertNotIn(
            "private-partial-content", str(raised.exception) + output.getvalue()
        )
        self.assertNotIn("secret-error", str(raised.exception) + output.getvalue())

    def test_malformed_or_ambiguous_item_preserves_both_shells(self):
        cases = (
            b"{broken",
            b"[]",
            b"{}",
            b'{"fields":{}}',
            json.dumps({"fields": [{"label": "GITHUB_TOKEN", "value": 5}]}).encode(),
            json.dumps(
                {"fields": [{"label": "GITHUB_TOKEN", "value": "a\0b"}]}
            ).encode(),
            json.dumps(
                {
                    "fields": [
                        {"label": "GITHUB_TOKEN", "value": "one"},
                        {"label": "GITHUB_TOKEN", "value": "two"},
                    ]
                }
            ).encode(),
        )
        for data in cases:
            with self.subTest(item=data), self.assertRaises(generated.ConfigError):
                self.raw = data
                generated.generate_secrets(self.home)
            self.assert_original()

    def test_one_item_read_generates_both_shells_and_optional_fields_may_be_absent(
        self,
    ):
        generated.generate_secrets(self.home)
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(self.calls[0][1:3], ["item", "get"])
        for path in (self.zsh, self.bash):
            text = path.read_text()
            self.assertIn("export GITHUB_TOKEN=synthetic-token", text)
            self.assertIn("export HOMEBREW_GITHUB_API_TOKEN=synthetic-token", text)
            self.assertNotIn("LINEAR_API_KEY", text)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            backup = next(path.parent.glob(f".{path.name}.before-chezmoi-*"))
            self.assertEqual(backup.read_bytes(), self.original[path])

    def test_shell_values_are_quoted_without_expansion(self):
        marker = self.home / "no-shell-execution"
        value = f"a'b\nbackslash\\ $(touch '{marker}') $VAR `id`"
        self.raw = json.dumps(
            {"fields": [{"label": "GITHUB_TOKEN", "value": value}]}
        ).encode()
        generated.generate_secrets(self.home)
        result = self.real_run(
            [
                "bash",
                "-c",
                'source "$1"; printf "%s" "$GITHUB_TOKEN"',
                "test",
                str(self.bash),
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, value)
        self.assertFalse(marker.exists())

    def test_failed_or_interrupted_second_publish_rolls_back_the_first(self):
        replace = os.replace
        for error in (OSError("simulated replacement failure"), KeyboardInterrupt()):
            failed = False

            def fail_second(source, target):
                nonlocal failed
                if target == self.bash and not failed:
                    failed = True
                    raise error
                replace(source, target)

            with self.subTest(error=type(error).__name__), patch.object(
                generated.os, "replace", side_effect=fail_second
            ), contextlib.redirect_stderr(io.StringIO()), self.assertRaises(
                type(error)
            ):
                generated.generate_secrets(self.home)
            self.assert_original()

    def test_staging_failure_leaves_every_live_file_untouched(self):
        real_stage = generated.stage

        def fail_bash(path, content, **kwargs):
            if path == self.bash:
                raise OSError("no space for second file")
            return real_stage(path, content, **kwargs)

        with patch.object(generated, "stage", side_effect=fail_bash), self.assertRaises(
            OSError
        ):
            generated.generate_secrets(self.home)
        self.assert_original()
        self.assertFalse(list(self.zsh.parent.glob(".secrets.zsh.chezmoi-*")))

    def test_symlink_targets_are_preserved(self):
        actual = self.home / "user-file"
        actual.write_bytes(b"personal contents\n")
        self.zsh.unlink()
        self.zsh.symlink_to(actual)
        with self.assertRaises(generated.ConfigError):
            generated.generate_secrets(self.home)
        self.assertTrue(self.zsh.is_symlink())
        self.assertEqual(actual.read_bytes(), b"personal contents\n")
        self.assertEqual(self.bash.read_bytes(), self.original[self.bash])

    def test_concurrent_generators_publish_a_consistent_pair(self):
        responses = iter(
            json.dumps({"fields": [{"label": "GITHUB_TOKEN", "value": value}]}).encode()
            for value in ("first-generation", "second-generation")
        )
        with patch.object(
            generated, "op_output", side_effect=lambda _: next(responses)
        ):
            with ThreadPoolExecutor(max_workers=2) as pool:
                results = [
                    pool.submit(generated.generate_secrets, self.home) for _ in range(2)
                ]
                for result in results:
                    result.result(timeout=15)
        self.assertEqual(
            self.zsh.read_text().splitlines()[1:],
            self.bash.read_text().splitlines()[1:],
        )
        self.assertIn("second-generation", self.zsh.read_text())
        self.assertEqual(
            len(list(self.zsh.parent.glob(".secrets.zsh.before-chezmoi-*"))), 2
        )


@unittest.skipUnless(shutil.which("chezmoi"), "chezmoi required")
class RenderedGenerators(unittest.TestCase):
    def render(self, text, source):
        config = source / "empty.toml"
        config.write_text("")
        preamble = '{{ $_ := set . "machine_profile" "mac-personal" }}{{ $_ := set . "package_profile" "personal" }}{{ $_ := set .chezmoi "os" "darwin" }}'
        result = subprocess.run(
            [
                "chezmoi",
                "--config",
                str(config),
                "--source",
                str(source),
                "execute-template",
            ],
            input=preamble + text,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def test_aictx_source_contents_trigger_rebuild_including_root_and_nested_files(
        self,
    ):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp)
            main = source / "tools/aictx/src/main.rs"
            nested = source / "tools/aictx/src/tui/app.rs"
            nested.parent.mkdir(parents=True)
            main.write_text("before")
            nested.write_text("nested")
            text = (
                ROOT / ".chezmoiscripts/03-configure/run_onchange_build-aictx.sh.tmpl"
            ).read_text()
            first = self.render(text, source)
            main.write_text("after")
            second = self.render(text, source)
            self.assertNotEqual(first, second)
            nested.write_text("nested changed")
            self.assertNotEqual(second, self.render(text, source))
            self.assertIn("--locked", first)
            self.assertIn("exit 1", first)


if __name__ == "__main__":
    unittest.main()
