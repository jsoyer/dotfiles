#!/usr/bin/env python3
"""Regression tests for misew.

Origin: Intel macOS is Homebrew Tier 3 (no bottles). misew moves formulae to
prebuilt mise backends by editing the {{ if $intel }} block of the chezmoi
mise template, so the template edits must never touch the other blocks.
"""

import importlib.machinery
import importlib.util
import unittest
from pathlib import Path

_PATH = Path(__file__).resolve().parent / "executable_misew"
if not _PATH.exists():
    _PATH = _PATH.with_name(_PATH.name.removeprefix("executable_"))
_LOADER = importlib.machinery.SourceFileLoader("misew", str(_PATH))
_SPEC = importlib.util.spec_from_loader("misew", _LOADER)
assert _SPEC is not None
mod = importlib.util.module_from_spec(_SPEC)
_LOADER.exec_module(mod)

TEMPLATE = """\
[tools]
{{- if $globalLangs }}
node = "latest"
{{- if not $intel }}
ruby = "latest"
{{- end }}
{{- end }}
{{ if $intel }}
"aqua:BurntSushi/ripgrep" = "latest"
{{ end }}
[settings]
all_compile = false
"""

LOCK = """\
lockfile_version = 4

[[tools."aqua:Byron/dua-cli"]]
version = "3.0.0"
backend = "aqua:Byron/dua-cli"

[tools."aqua:Byron/dua-cli"."platforms.macos-x64"]
checksum = "sha256:abc"
url = "https://github.com/Byron/dua-cli/releases/download/v3.0.0/dua-x86_64-apple-darwin.tar.gz"

[tools."aqua:Byron/dua-cli"."platforms.linux-x64"]
url = "https://example.invalid/linux.tar.gz"

[[tools."aqua:foo/bar"]]
version = "1.0.0"

[tools."aqua:foo/bar"."platforms.linux-x64"]
url = "https://example.invalid/bar-linux.tar.gz"
"""


class PickBackend(unittest.TestCase):
    def test_prefers_aqua_over_asdf(self):
        cands = mod.parse_registry(
            "asdf:virtualroot/asdf-opentofu aqua:opentofu/opentofu\n"
        )
        self.assertEqual(mod.pick_backend(cands), "aqua:opentofu/opentofu")

    def test_accepts_pypi(self):
        self.assertEqual(mod.pick_backend(["pypi:ansible"]), "pypi:ansible")

    def test_rejects_source_build_backends(self):
        self.assertIsNone(
            mod.pick_backend(["cargo:ripgrep", "go:github.com/x/y", "asdf:z"])
        )

    def test_aqua_beats_npm_whatever_the_order(self):
        self.assertEqual(
            mod.pick_backend(["npm:fx", "aqua:antonmedv/fx"]), "aqua:antonmedv/fx"
        )


class GithubRepo(unittest.TestCase):
    def test_homepage(self):
        self.assertEqual(
            mod.github_repo("https://github.com/railwayapp/cli"), "railwayapp/cli"
        )

    def test_archive_url(self):
        url = "https://github.com/ipinfo/mmdbctl/archive/refs/tags/v1.4.7.tar.gz"
        self.assertEqual(mod.github_repo(url), "ipinfo/mmdbctl")

    def test_git_suffix(self):
        self.assertEqual(mod.github_repo("https://github.com/a/b.git"), "a/b")

    def test_not_github(self):
        self.assertIsNone(mod.github_repo("https://opentofu.org"))
        self.assertIsNone(mod.github_repo(None))


class PackageBackend(unittest.TestCase):
    def test_pypi_sdist(self):
        url = "https://files.pythonhosted.org/packages/ab/cd/ef/ansible_lint-25.1.0.tar.gz"
        self.assertEqual(mod.package_backend(url), "pypi:ansible-lint")

    def test_npm_plain_and_scoped(self):
        self.assertEqual(
            mod.package_backend(
                "https://registry.npmjs.org/eslint/-/eslint-9.30.0.tgz"
            ),
            "npm:eslint",
        )
        url = "https://registry.npmjs.org/@openspec/cli/-/cli-1.0.0.tgz"
        self.assertEqual(mod.package_backend(url), "npm:@openspec/cli")

    def test_other_sources(self):
        self.assertIsNone(
            mod.package_backend("https://github.com/a/b/archive/v1.tar.gz")
        )
        self.assertIsNone(mod.package_backend(None))

    def test_package_source_ranks_before_github(self):
        info = {
            "homepage": "https://github.com/eslint/eslint",
            "urls": {
                "stable": {
                    "url": "https://registry.npmjs.org/eslint/-/eslint-9.0.0.tgz"
                }
            },
        }
        orig = mod.run
        mod.run = lambda cmd, **kw: mod.subprocess.CompletedProcess(cmd, 1, "", "")
        try:
            cands = mod.resolve_candidates("eslint", info)
        finally:
            mod.run = orig
        self.assertEqual(
            cands, ["npm:eslint", "aqua:eslint/eslint", "github:eslint/eslint"]
        )


class LockUrls(unittest.TestCase):
    def test_keeps_only_macos_x64_assets(self):
        urls = mod.lock_urls(LOCK)
        self.assertEqual(list(urls), ["aqua:Byron/dua-cli"])
        self.assertTrue(
            urls["aqua:Byron/dua-cli"].endswith("x86_64-apple-darwin.tar.gz")
        )

    def test_failed_backend_from_stderr(self):
        err = (
            "mise WARN  something\n"
            "mise ERROR failed to resolve aqua:railwayapp/cli@latest for lockfile\n"
        )
        self.assertEqual(
            mod.failed_backend(err, ["aqua:Byron/dua-cli", "aqua:railwayapp/cli"]),
            "aqua:railwayapp/cli",
        )
        self.assertIsNone(mod.failed_backend("mise ERROR network down\n", ["aqua:a/b"]))


class UsableAsset(unittest.TestCase):
    def test_github_macos_binary(self):
        url = "https://github.com/railwayapp/cli/releases/download/v4.0.0/railway-v4.0.0-x86_64-apple-darwin.tar.gz"
        self.assertTrue(mod.usable_asset("github:railwayapp/cli", url))

    def test_github_source_tarball_rejected(self):
        url = "https://github.com/RsyncProject/rsync/releases/download/v3.4.1/rsync-3.4.1.tar.gz"
        self.assertFalse(mod.usable_asset("github:RsyncProject/rsync", url))

    def test_github_dmg_rejected(self):
        url = "https://github.com/fontforge/fontforge/releases/download/20251009/FontForge-2025-10-09-macOS.dmg"
        self.assertFalse(mod.usable_asset("github:fontforge/fontforge", url))

    def test_aqua_trusted_even_without_platform_name(self):
        url = "https://services.gradle.org/distributions/gradle-9.2-bin.zip"
        self.assertTrue(mod.usable_asset("aqua:gradle/gradle-distributions", url))


class TemplateEdits(unittest.TestCase):
    def test_appends_inside_intel_block_only(self):
        out = mod.add_to_intel_block(TEMPLATE, "aqua:Byron/dua-cli")
        lines = out.splitlines()
        i = lines.index('"aqua:Byron/dua-cli" = "latest"')
        self.assertEqual(lines[i - 1], '"aqua:BurntSushi/ripgrep" = "latest"')
        self.assertEqual(lines[i + 1], "{{ end }}")
        self.assertEqual(out.count("{{- end }}"), TEMPLATE.count("{{- end }}"))

    def test_idempotent(self):
        once = mod.add_to_intel_block(TEMPLATE, "aqua:Byron/dua-cli")
        self.assertEqual(mod.add_to_intel_block(once, "aqua:Byron/dua-cli"), once)

    def test_remove_restores(self):
        added = mod.add_to_intel_block(TEMPLATE, "pypi:ansible")
        self.assertEqual(mod.remove_from_template(added, "pypi:ansible"), TEMPLATE)

    def test_missing_block_raises(self):
        with self.assertRaises(ValueError):
            mod.add_to_intel_block('[tools]\nnode = "latest"\n', "aqua:a/b")

    def test_trimmed_markers(self):
        text = '{{- if $intel -}}\n"aqua:a/b" = "latest"\n{{- end }}\n'
        out = mod.add_to_intel_block(text, "aqua:c/d")
        self.assertEqual(out.splitlines()[2], '"aqua:c/d" = "latest"')


class BrewfileEdits(unittest.TestCase):
    def test_removes_plain_and_tapped(self):
        text = 'brew "rclone"\nbrew "rclone-browser"\nbrew "foo/tap/rclone"\ncask "rclone"\n'
        self.assertEqual(
            mod.remove_from_brewfile(text, "rclone"),
            'brew "rclone-browser"\ncask "rclone"\n',
        )

    def test_kwargs_line(self):
        text = 'brew "syncthing", restart_service: :changed\nbrew "jq"\n'
        self.assertEqual(mod.remove_from_brewfile(text, "syncthing"), 'brew "jq"\n')


class OutdatedLeaves(unittest.TestCase):
    def test_skips_pinned_deps_and_skip_list(self):
        outputs = {
            "outdated": '{"formulae": [{"name": "railway"}, {"name": "numpy"},'
            ' {"name": "docker"}, {"name": "libuv"}, {"name": "jq", "pinned": true}]}',
            "leaves": "railway\nnumpy\ndocker\njq\n",
        }

        def fake_run(cmd, **kw):
            key = "outdated" if "outdated" in cmd else "leaves"
            return mod.subprocess.CompletedProcess(cmd, 0, outputs[key], "")

        orig = mod.run
        mod.run = fake_run
        try:
            self.assertEqual(mod.outdated_leaves(), ["railway"])
        finally:
            mod.run = orig


class Cache(unittest.TestCase):
    def test_freshness(self):
        now = 1_000_000.0
        self.assertTrue(mod.is_fresh({"checked": now - 60}, now))
        self.assertFalse(mod.is_fresh({"checked": now - mod.CACHE_TTL - 1}, now))
        self.assertFalse(mod.is_fresh(None, now))


if __name__ == "__main__":
    unittest.main()
