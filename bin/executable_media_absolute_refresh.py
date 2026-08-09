#!/usr/bin/env python3
"""Refresh the absolute -> season/episode tables from the remote libraries.

Run after adding a show to the registry, and whenever the remote library gains
episodes outside this script (a manual rename, a season reorganisation upstream).
Listing is server-side: nothing is downloaded.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import media_absolute_shows as abs_shows  # noqa: E402

DEFAULT_REGISTRY = Path.home() / 'bin/media_automation/shows_registry.toml'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--registry', type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument('--show', help='limit to this show name')
    parser.add_argument('--rclone', default='rclone')
    args = parser.parse_args()

    shows = abs_shows.load_registry(args.registry)
    if not shows:
        print(f'Aucune serie declaree dans {args.registry}')
        return 0
    failures = 0
    for show in shows:
        if args.show and show.name != args.show:
            continue
        try:
            mapping = abs_shows.refresh_mapping(show, rclone=args.rclone)
        except Exception as exc:  # noqa: BLE001 - surfaced to the operator
            print(f'[ECHEC] {show.name}: {exc}')
            failures += 1
            continue
        slot = mapping.next_slot()
        print(f'{show.name} : {len(mapping.seasons)} saisons, '
              f'dernier absolu {mapping.last_absolute}')
        if slot:
            print(f'  prochain episode attendu : absolu {mapping.last_absolute + 1} '
                  f'-> S{slot[0]:02d}E{slot[1]:02d}')
        print(f'  table ecrite : {show.mapping_file}')
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
