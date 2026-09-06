#!/usr/bin/env python3
"""Guards for the chezmoi consistency review.

These lock the remarks from the 2026-08-28 repo analysis: one ignore file,
OmArchy target paths, no chezmoiremove fight over ~/.agents, machine_profile
instead of a hardcoded hostname in apply scripts, and mac-pro-only leftover
wipes.
"""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IGNORE = ROOT / '.chezmoiignore.tmpl'
REMOVE = ROOT / '.chezmoiremove.tmpl'
RUN12 = ROOT / '.chezmoiscripts/02-install/run_once_12-disable-macos-agent-stacks.sh.tmpl'
NUSHELL = ROOT / 'dot_config/nushell/env.nu.tmpl'
FISH = ROOT / 'dot_config/private_fish/config.fish.tmpl'
ZSH_PATH = ROOT / 'dot_zsh/01-path.zsh'
BASH_PATH = ROOT / 'dot_bash/01-path.bash'

# Hostname stays only where it *defines* the profile, or names a Brewfile overlay.
HOSTNAME_ALLOWED = {
    ROOT / '.chezmoi.toml.tmpl',
}


def _read(path: Path) -> str:
    return path.read_text()


class OneIgnoreFile(unittest.TestCase):
    def test_plain_chezmoiignore_is_gone(self):
        self.assertFalse((ROOT / '.chezmoiignore').exists())
        self.assertTrue(IGNORE.exists())

    def test_omarchy_uses_target_paths_not_source_names(self):
        text = _read(IGNORE)
        start = text.index('{{- if eq $mp "omarchy" }}')
        block = text[start:text.index('{{- end }}', start + 1)]
        self.assertNotIn('\ndot_zsh/', block)
        self.assertNotIn('\ndot_zshrc.tmpl', block)
        self.assertNotIn('\ndot_config/nvim/', block)
        self.assertIn('\n.zsh/\n', block)
        self.assertIn('\n.zshrc\n', block)
        self.assertIn('\n.config/nvim/\n', block)

    def test_agents_and_skills_are_ignored(self):
        text = _read(IGNORE)
        self.assertIn('\n.agents\n', text)
        self.assertIn('\n.skills\n', text)
        self.assertIn('.bash/secrets.bash', text)


class RemoveDoesNotFightIgnore(unittest.TestCase):
    def test_chezmoiremove_has_no_target_paths(self):
        targets = [
            line.strip()
            for line in _read(REMOVE).splitlines()
            if line.strip() and not line.lstrip().startswith('#')
        ]
        self.assertEqual(targets, [], f'chezmoiremove still lists {targets}')


class MachineProfileNotHostname(unittest.TestCase):
    SCRIPT_GLOBS = (
        '.chezmoiscripts/**/*.tmpl',
        'dot_zshrc.tmpl',
        'dot_zsh/00-env.zsh.tmpl',
        'dot_bash/00-env.bash.tmpl',
    )

    def test_apply_scripts_key_off_machine_profile(self):
        offenders = []
        for glob in self.SCRIPT_GLOBS:
            for path in ROOT.glob(glob):
                if path.resolve() in {p.resolve() for p in HOSTNAME_ALLOWED}:
                    continue
                text = path.read_text()
                if 'jsoyer-macOS' in text:
                    offenders.append(str(path.relative_to(ROOT)))
        self.assertEqual(offenders, [], f'hardcoded hostname: {offenders}')

    def test_shells_take_profile_from_chezmoi(self):
        for rel in ('dot_zsh/00-env.zsh.tmpl', 'dot_bash/00-env.bash.tmpl'):
            text = _read(ROOT / rel)
            self.assertIn('{{ .machine_profile }}', text)
            self.assertEqual(text.count('export MACHINE_PROFILE='), 1, rel)


class MacProOnlyLeftoverWipe(unittest.TestCase):
    def test_run_once_12_wipes_shims_only_on_mac_pro(self):
        text = _read(RUN12)
        # The shim list must sit inside a mac-pro guard, not a bare darwin block.
        shim = text.index('moshi-hook-launch')
        before = text[:shim]
        self.assertIn('eq .machine_profile "mac-pro"', before)
        # After the last mac-pro open before the shim, there must be no
        # unmatched {{ end }} that would close the guard early.
        last_guard = before.rfind('eq .machine_profile "mac-pro"')
        self.assertGreater(last_guard, 0)
        self.assertNotIn('moshi-hook-launch', text[text.find('{{ end -}}', last_guard):])


class NushellPath(unittest.TestCase):
    def test_texlive_is_darwin_only(self):
        text = _read(NUSHELL)
        # /Library/TeX/texbin is the version-independent symlink the MacTeX
        # installer keeps pointed at the current distribution. A versioned path
        # such as texlive/2025basic silently goes dead on every yearly upgrade,
        # which is exactly what happened before this was switched over.
        tex = text.index('/Library/TeX/texbin')
        window = text[text.rfind('{{- if', 0, tex):tex]
        self.assertIn('darwin', window)

    def test_no_versioned_texlive_path(self):
        # Guard against reintroducing a year-stamped TeX Live path anywhere in
        # the shell PATH configuration.
        for path in (NUSHELL, FISH, BASH_PATH, ZSH_PATH):
            with self.subTest(path=path.name):
                self.assertNotIn('texlive/20', _read(path))


if __name__ == '__main__':
    unittest.main()
