#!/usr/bin/env python3
"""Guard: media_automation scripts stay NAS-only (omv-nice / omv-dijon).

serie_renommer.py was added after the ignore list and leaked onto Mac Pro.
These checks fail if another bin/ sibling is introduced without the same scope.
"""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def nas_ignore_block():
    ignore = (ROOT / '.chezmoiignore').read_text()
    start = ignore.index('media_automation : NAS uniquement')
    return ignore[start:ignore.index('{{ end }}', start)]


def target_for(path: Path) -> str | None:
    if path.name.startswith('executable_'):
        return 'bin/' + path.name.removeprefix('executable_')
    if path.name == 'test_media_automation.py':
        return 'bin/test_media_automation.py'
    if path.name == 'media_automation':
        return 'bin/media_automation'
    return None


class MediaScriptsStayNasOnly(unittest.TestCase):
    def test_every_bin_script_is_in_the_nas_ignore_list(self):
        block = nas_ignore_block()
        missing = []
        for path in sorted((ROOT / 'bin').iterdir()):
            target = target_for(path)
            if target and target not in block:
                missing.append(target)
        self.assertEqual(missing, [], f'NAS ignore missing: {missing}')

    def test_leaked_renamer_is_removed_off_nas(self):
        remove = (ROOT / '.chezmoiremove.tmpl').read_text()
        self.assertIn('bin/serie_renommer.py', remove)
        self.assertIn('omv-nice', remove)
        self.assertIn('omv-dijon', remove)


if __name__ == '__main__':
    unittest.main()
