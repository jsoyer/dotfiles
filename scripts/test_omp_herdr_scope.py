#!/usr/bin/env python3
"""Guards for omp and herdr install channels.

macOS keeps Homebrew for both. Linux (and the rest) use official one-liners.
"""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IGNORE = ROOT / '.chezmoiignore.tmpl'
INSTALL_AI = ROOT / 'dot_local/bin/executable_install-ai'
RUN12 = ROOT / '.chezmoiscripts/02-install/run_once_12-disable-macos-agent-stacks.sh.tmpl'
RUN14 = ROOT / '.chezmoiscripts/02-install/run_once_after_14-install-herdr.sh.tmpl'
BLACKLIST = ROOT / 'dot_private/Brewfile_blacklist'
ALIASES = ROOT / 'dot_shell_common/aliases.sh'
HERDR_SETUP = ROOT / 'dot_local/bin/executable_herdr-setup'


def _read(path: Path) -> str:
    return path.read_text()


class OmpIsSeventhCli(unittest.TestCase):
    def test_install_ai_has_omp_oneliner(self):
        text = _read(INSTALL_AI)
        self.assertIn('has_omp', text)
        self.assertIn('https://omp.sh/install', text)
        self.assertIn('claude|copilot|codex|grok|cursor|pi|omp', text)
        self.assertIn('migrate_omp', text)
        self.assertIn('Darwin', text)

    def test_update_ai_leaves_macos_brew_omp_alone(self):
        aliases = _read(ALIASES)
        self.assertIn('omp update', aliases)
        self.assertIn('omp: brew-managed — bup handles it', aliases)
        self.assertNotIn('migrating to https://omp.sh/install', aliases)
        fish = _read(ROOT / 'dot_config/private_fish/config.fish.tmpl')
        self.assertIn('omp update', fish)
        nu = _read(ROOT / 'dot_config/nushell/config.nu')
        self.assertIn('omp update', nu)

    def test_blacklist_does_not_block_macos_brew_omp(self):
        text = _read(BLACKLIST)
        self.assertNotIn('\nomp\n', text)
        self.assertNotIn('can1357/tap/omp', text)


class HerdrIsEverywhere(unittest.TestCase):
    def test_ignore_deploys_herdr_scripts_off_linux(self):
        block_start = _read(IGNORE).index('Agent stacks')
        block = _read(IGNORE)[block_start:_read(IGNORE).index('{{ end }}', block_start)]
        self.assertNotIn('herdr-setup', block)
        self.assertNotIn('update-herdr', block)
        self.assertNotIn('herdr-uninstall', block)
        self.assertIn('moshi-setup', block)
        self.assertIn('orca-setup', block)

    def test_run_once_12_does_not_wipe_herdr_wrappers(self):
        text = _read(RUN12)
        self.assertNotIn('${HOME}/.local/bin/herdr-setup', text)
        self.assertNotIn('${HOME}/.local/bin/update-herdr', text)
        self.assertNotIn('${HOME}/.local/bin/herdr-uninstall', text)
        self.assertIn('herdr-update.service', text)
        self.assertIn('eq .machine_profile "mac-pro"', text)

    def test_run_once_14_is_linux_only_oneliner(self):
        self.assertTrue(RUN14.exists())
        text = _read(RUN14)
        self.assertIn('eq .chezmoi.os "linux"', text)
        self.assertIn('herdr-setup', text)
        self.assertIn('--no-service', text)
        self.assertNotIn('brew install', text)

    def test_herdr_setup_does_not_uninstall_macos_brew(self):
        text = _read(HERDR_SETUP)
        self.assertIn('Darwin', text)
        self.assertIn('Linuxbrew copy found', text)

    def test_blacklist_does_not_block_macos_brew_herdr(self):
        self.assertNotIn('\nherdr\n', _read(BLACKLIST))

    def test_macos_overlays_keep_brew_herdr(self):
        overlay = ROOT / 'dot_private/Brewfile_Jerome-Soyers-Mac-mini-M4'
        text = overlay.read_text()
        self.assertIn('brew "herdr"', text)
        self.assertIn('can1357/tap/omp', text)

    def test_linux_brewfiles_do_not_ship_herdr_or_omp(self):
        offenders = []
        for name in ('Brewfile_brew_only', 'Brewfile_rpi', 'Brewfile_fedora_atomic'):
            path = ROOT / 'dot_private' / name
            if not path.exists():
                continue
            text = path.read_text()
            for needle in ('brew "herdr"', 'can1357/tap/omp', 'brew "omp"'):
                if needle in text:
                    offenders.append(f'{name}: {needle}')
        self.assertEqual(offenders, [], f'linux brewfile still has: {offenders}')

    def test_orca_update_is_os_split(self):
        text = _read(ALIASES)
        darwin = text[
            text.index('if [[ "$(uname -s)" == "Darwin" ]]; then') : text.index(
                'if [[ "$(uname -s)" == "Linux" ]]; then'
            )
        ]
        linux = text[text.index('if [[ "$(uname -s)" == "Linux" ]]; then') :]
        self.assertIn('stablyai/orca/orca', darwin)
        self.assertNotIn("alias orca-update='update-orca'", darwin)
        self.assertIn("alias orca-update='update-orca'", linux)
        self.assertNotIn('stablyai/orca/orca', linux)

    def test_herdr_aliases_are_not_linux_only(self):
        text = _read(ALIASES)
        install = text.index("alias herdr-install='herdr-setup'")
        stacks = text.index('Self-hosted agent stacks')
        self.assertLess(install, stacks)


if __name__ == '__main__':
    unittest.main()
