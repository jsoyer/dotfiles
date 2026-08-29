#!/usr/bin/env python3
"""Guards for omp (omp.sh) and herdr (herdr.dev) one-liner channels.

OMP is the seventh mandatory AI CLI. HERDR is installed on every Unix host.
Neither belongs in a Brewfile.
"""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IGNORE = ROOT / '.chezmoiignore'
INSTALL_AI = ROOT / 'dot_local/bin/executable_install-ai'
RUN12 = ROOT / '.chezmoiscripts/02-install/run_once_12-disable-macos-agent-stacks.sh.tmpl'
RUN14 = ROOT / '.chezmoiscripts/02-install/run_once_after_14-install-herdr.sh.tmpl'
BLACKLIST = ROOT / 'dot_private/Brewfile_blacklist'
ALIASES = ROOT / 'dot_shell_common/aliases.sh'


def _read(path: Path) -> str:
    return path.read_text()


class OmpIsSeventhCli(unittest.TestCase):
    def test_install_ai_has_omp_oneliner(self):
        text = _read(INSTALL_AI)
        self.assertIn('has_omp', text)
        self.assertIn('https://omp.sh/install', text)
        self.assertIn('claude|copilot|codex|grok|cursor|pi|omp', text)
        self.assertIn('migrate_omp', text)

    def test_update_ai_mentions_omp(self):
        self.assertIn('omp update', _read(ALIASES))
        fish = _read(ROOT / 'dot_config/private_fish/config.fish.tmpl')
        self.assertIn('omp update', fish)
        nu = _read(ROOT / 'dot_config/nushell/config.nu')
        self.assertIn('omp update', nu)

    def test_blacklist_blocks_brew_omp(self):
        text = _read(BLACKLIST)
        self.assertIn('\nomp\n', text)
        self.assertIn('can1357/tap/omp', text)


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

    def test_run_once_14_uses_official_installer(self):
        self.assertTrue(RUN14.exists())
        text = _read(RUN14)
        self.assertIn('herdr-setup', text)
        self.assertIn('--no-service', text)
        self.assertNotIn('brew install', text)

    def test_blacklist_blocks_brew_herdr(self):
        self.assertIn('\nherdr\n', _read(BLACKLIST))

    def test_hostname_brewfiles_dropped_herdr_and_omp(self):
        offenders = []
        for path in (ROOT / 'dot_private').glob('Brewfile_*'):
            if path.name == 'Brewfile_blacklist':
                continue
            text = path.read_text()
            for needle in ('brew "herdr"', 'can1357/tap/omp', 'brew "omp"'):
                if needle in text:
                    offenders.append(f'{path.name}: {needle}')
        self.assertEqual(offenders, [], f'still brew-channel: {offenders}')

    def test_herdr_aliases_are_not_linux_only(self):
        text = _read(ALIASES)
        install = text.index("alias herdr-install='herdr-setup'")
        stacks = text.index('Self-hosted agent stacks')
        self.assertLess(install, stacks)


if __name__ == '__main__':
    unittest.main()
