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
    ("rpi", "linux", "arm64", False),
    ("rpi", "linux", "arm", False),
    ("ubuntu-server", "linux", "amd64", False),
    ("fedora-server", "linux", "arm64", False),
    ("arch-server", "linux", "amd64", False),
    ("debian", "linux", "amd64", False),
]

STANDALONE_ASSETS = ("linux-x64", "linux-arm64", "linux-armv7")


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

    def test_every_linux_profile_gets_mise_install(self):
        for profile, os_name, arch, _ in [c for c in CASES if c[1] == "linux"]:
            with self.subTest(profile=profile, arch=arch):
                out = render(INSTALL_SCRIPT, profile, os_name, arch)
                self.assertIn("install_standalone_mise", out)
                self.assertIn("brew_has_bottle_for_mise", out)
                for asset in STANDALONE_ASSETS:
                    self.assertIn(asset, out)
                self.assertNotIn("macos-x64", out)
                res = subprocess.run(["bash", "-n"], input=out, text=True, capture_output=True)
                self.assertEqual(res.returncode, 0, res.stderr)

    def test_server_rpi_debian_config_empty_and_pruned(self):
        for profile in ("rpi", "debian", "ubuntu-server", "fedora-server", "arch-server"):
            with self.subTest(profile=profile):
                self.assertEqual(tools_keys(render(MISE_CONFIG, profile, "linux", "arm64")), set())
                self.assertIn("prune --yes", render(INSTALL_SCRIPT, profile, "linux", "arm64"))

    def test_nothing_ignores_mise_config(self):
        for profile, os_name, arch in [("rpi", "linux", "arm"), ("ubuntu-server", "linux", "amd64"),
                                       ("debian", "linux", "arm64"), ("windows", "windows", "amd64")]:
            with self.subTest(profile=profile):
                self.assertNotIn(".config/mise/", render(ROOT / ".chezmoiignore.tmpl", profile, os_name, arch))
                render(MISE_CONFIG, profile, os_name, arch)

    def test_windows_has_no_bash_install_script(self):
        self.assertEqual(render(INSTALL_SCRIPT, "windows", "windows", "amd64").strip(), "")
        self.assertIn('"name": "mise"', (ROOT / "dot_private/Scoopfile.json").read_text())


class LinuxbrewDefault(unittest.TestCase):
    BREW = ROOT / ".chezmoiscripts/02-install/run_once_02-install-linuxbrew.sh.tmpl"
    BUNDLE = ROOT / ".chezmoiscripts/02-install/run_onchange_03-brew-bundle.sh.tmpl"

    @unittest.skipUnless(shutil.which("chezmoi"), "chezmoi not installed")
    def test_linuxbrew_gate_by_arch(self):
        # can-sudo is evaluated for real; only assert the arch gate (32-bit never renders)
        self.assertEqual(render(self.BREW, "rpi", "linux", "arm").strip(), "")
        self.assertEqual(render(self.BREW, "windows", "windows", "amd64").strip(), "")

    def test_server_profiles_use_minimal_brewfile(self):
        self.assertEqual((ROOT / "dot_private/Brewfile_minimal").read_text().split("\n")[2:3], ['brew "mise"'])
        lines = [line for line in (ROOT / "dot_private/Brewfile_minimal").read_text().splitlines()
                 if line and not line.startswith("#")]
        self.assertEqual(lines, ['brew "mise"'])
        text = self.BUNDLE.read_text()
        self.assertIn('"ubuntu-server" "fedora-server" "arch-server"', text)
        self.assertIn("Brewfile_minimal", text)
        self.assertIn('(list "rpi" "debian" "ubuntu-server" "fedora-server" "arch-server")', text)

    def test_light_profiles_render_mise_only_brewfile(self):
        tmpl = ROOT / "dot_private/Brewfile.tmpl"
        for profile, arch in (("rpi", "arm64"), ("debian", "amd64"), ("ubuntu-server", "amd64"),
                              ("fedora-server", "amd64"), ("arch-server", "amd64")):
            with self.subTest(profile=profile):
                entries = [line.strip() for line in render(tmpl, profile, "linux", arch).splitlines()
                           if line.strip() and not line.strip().startswith("#")]
                self.assertEqual(entries, ['brew "mise"'])


if __name__ == "__main__":
    unittest.main()
