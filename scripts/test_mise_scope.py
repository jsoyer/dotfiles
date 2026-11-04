"""Which machines get global mise language toolchains.

Languages (node/python/go/rust/ruby/java) are declared globally only on the
work Mac (mac-pro) and Intel macOS. Personal Apple Silicon Macs use Homebrew,
Linux desktops the native package manager; they keep an empty [tools].
"""

import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MISE_CONFIG = ROOT / "dot_config/mise/config.toml.tmpl"
INSTALL_SCRIPT = (
    ROOT / ".chezmoiscripts/03-configure/run_onchange_after_install-mise-tools.sh.tmpl"
)
LANGS = ("node", "python", "go", "rust", "java")

# (profile, os, arch, expects global languages)
CASES = [
    ("mac-pro", "darwin", "arm64", True),
    ("mac-personal", "darwin", "arm64", False),
    ("mac-personal", "darwin", "amd64", True),
    ("fedora-desktop", "linux", "amd64", False),
]


def render(path: Path, profile: str, os_name: str, arch: str) -> str:
    preamble = (
        '{{- $_ := set . "machine_profile" "%s" -}}'
        '{{- $_ := set .chezmoi "os" "%s" -}}'
        '{{- $_ := set .chezmoi "arch" "%s" -}}\n' % (profile, os_name, arch)
    )
    res = subprocess.run(
        ["chezmoi", "execute-template", "--source", str(ROOT)],
        input=preamble + path.read_text(),
        capture_output=True, text=True, timeout=60,
    )
    assert res.returncode == 0, res.stderr
    return res.stdout


def tools_keys(rendered: str) -> set:
    keys, in_tools = set(), False
    for raw in rendered.splitlines():
        line = raw.strip()
        if line.startswith("["):
            in_tools = line == "[tools]"
        elif in_tools and "=" in line and not line.startswith("#"):
            keys.add(line.split("=")[0].strip().strip('"'))
    return keys


class TextualGating(unittest.TestCase):
    def test_languages_sit_inside_mac_pro_or_intel_block(self):
        text = MISE_CONFIG.read_text()
        self.assertIn('(eq $mp "mac-pro")', text)
        start = text.index("{{- if $globalLangs }}")
        end = text.index("{{ if $intel }}", start)
        block = text[start:end]
        for lang in LANGS:
            self.assertIn(f'\n{lang} = ', block)
        self.assertNotIn("[settings]", block)

    def test_install_script_prunes_only_without_global_languages(self):
        text = INSTALL_SCRIPT.read_text()
        self.assertIn("prune --yes", text)
        self.assertIn('(eq $mp "mac-pro")', text)


@unittest.skipUnless(shutil.which("chezmoi"), "chezmoi not installed")
class RenderedGating(unittest.TestCase):
    def test_config_languages_per_machine(self):
        for profile, os_name, arch, expected in CASES:
            with self.subTest(profile=profile, os=os_name, arch=arch):
                keys = tools_keys(render(MISE_CONFIG, profile, os_name, arch))
                for lang in LANGS:
                    self.assertEqual(lang in keys, expected, f"{lang} in {sorted(keys)}")
                self.assertEqual("ruby" in keys or "conda:ruby" in keys, expected)

    def test_settings_kept_everywhere(self):
        for profile, os_name, arch, _ in CASES:
            with self.subTest(profile=profile):
                out = render(MISE_CONFIG, profile, os_name, arch)
                self.assertIn("all_compile = false", out)

    def test_prune_rendered_only_without_global_languages(self):
        for profile, os_name, arch, expected in CASES:
            with self.subTest(profile=profile, os=os_name, arch=arch):
                out = render(INSTALL_SCRIPT, profile, os_name, arch)
                self.assertEqual("prune --yes" in out, not expected)


if __name__ == "__main__":
    unittest.main()
