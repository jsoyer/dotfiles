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

    def test_future_bin_siblings_are_covered_by_glob(self):
        self.assertIn('bin/**', nas_ignore_block())

    def test_leaked_renamer_is_deleted_once_not_prompted(self):
        remove = (ROOT / '.chezmoiremove.tmpl').read_text()
        self.assertNotIn('bin/serie_renommer.py', remove)
        script = (ROOT / '.chezmoiscripts/02-install'
                  / 'run_once_13-remove-nas-media-leftovers.sh.tmpl').read_text()
        self.assertIn('bin/serie_renommer.py', script)
        self.assertIn('omv-nice', script)
        self.assertIn('omv-dijon', script)


if __name__ == '__main__':
    unittest.main()
