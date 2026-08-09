#!/usr/bin/env python3
"""Reformat an already season-organised library to the Infuse/Plex convention.

Some libraries are already laid out as `Season NN/Show - 13x03 - Title.mkv`:
the season split is correct, only the episode token uses the `NNxMM` form that
Infuse does not read. This tool rewrites that token to `SNNEMM` and changes
nothing else -- files stay in their season folder.

That restraint is deliberate. A library's season split may follow TheTVDB while
TMDb splits the same show differently; recomputing seasons from an external
source would scatter a correct library. Here the existing structure is the
reference, and every rename is verified against it.

A season whose files carry a bare running number instead (`Show - 591 - Title`)
can be numbered from their order with --derive-order, but only when the numbers
are contiguous and none is missing.

Nothing is ever guessed: anything ambiguous is reported and left untouched.

Usage:
    rclone lsf "gdrive:Infuse/One Piece" -R --files-only > /tmp/op.txt
    ./infuse_rename_plan.py --show "One Piece" --list /tmp/op.txt \
        --remote "gdrive:Infuse/One Piece" --derive-order 16 --out /tmp/op-plan
"""
import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

MEDIA_SUFFIXES = {'.mkv', '.mp4', '.avi', '.m4v', '.mov', '.wmv',
                  '.srt', '.ass', '.ssa', '.sub', '.idx'}

SEASON_DIR_RE = re.compile(r'^Season[\s._-]*(\d{1,3})$', re.I)
# "Show - S13E03 - Title" : already in the target form. Recognising it makes a
# partial run resumable -- regenerate the plan and only the remainder is listed.
ALREADY_RE = re.compile(r'^.*?[\s._-]+S(?P<season>\d{1,2})E(?P<episode>\d{1,3})(?:[\s._-]|$)', re.I)
# "Show - 13x03 - Title" : the season/episode token already present.
SXE_RE = re.compile(r'^(?P<prefix>.*?)[\s._-]+(?P<season>\d{1,2})x(?P<episode>\d{1,3})'
                    r'(?P<rest>[\s._-]+.*)?$')
# "Show - 591 - Title" : a bare running number.
RUNNING_RE = re.compile(r'^(?P<prefix>.*?)[\s._-]+-[\s._-]+(?P<number>\d{2,4})'
                        r'(?P<rest>[\s._-]+-[\s._-]+.*)?$')

# Drive, like most filesystems, caps a single name at 255 bytes.
MAX_NAME_BYTES = 255


def split_entry(path):
    """Return (season_number, filename) for a `Season NN/file` entry, else None."""
    parts = Path(path).parts
    if len(parts) != 2:
        return None
    match = SEASON_DIR_RE.match(parts[0])
    return (int(match.group(1)), parts[1]) if match else None


def build_plan(entries, show_name, derive_orders):
    """Return (plan, unresolved). Plan entries are (source, destination, label)."""
    plan, unresolved = [], []
    by_season = defaultdict(list)

    for entry in entries:
        split = split_entry(entry)
        if split is None:
            unresolved.append((entry, 'hors structure "Season NN/fichier"'))
            continue
        season, filename = split
        if Path(filename).suffix.lower() not in MEDIA_SUFFIXES:
            unresolved.append((entry, 'extension non media'))
            continue
        by_season[season].append((entry, filename))

    for season in sorted(by_season):
        items = by_season[season]
        tagged, running = [], []
        for entry, filename in items:
            stem, suffix = Path(filename).stem, Path(filename).suffix
            done = ALREADY_RE.match(stem)
            if done and int(done.group('season')) == season:
                continue  # already conformant: nothing to do, and safe to re-run
            match = SXE_RE.match(stem)
            if match:
                tagged.append((entry, stem, suffix, match))
            else:
                running.append((entry, stem, suffix, RUNNING_RE.match(stem)))

        # Case 1 -- the episode token is already there: rewrite it in place.
        for entry, stem, suffix, match in tagged:
            declared = int(match.group('season'))
            if declared != season:
                unresolved.append(
                    (entry, f'le fichier annonce la saison {declared}, le dossier {season}'))
                continue
            episode = int(match.group('episode'))
            rest = (match.group('rest') or '').strip(' -._')
            plan.append(_make_rename(entry, season, episode, show_name, rest, suffix))

        if not running:
            continue

        # Case 2 -- bare running numbers, numbered from their order on request.
        if season not in derive_orders:
            for entry, _, _, _ in running:
                unresolved.append(
                    (entry, f'numero brut ; utiliser --derive-order {season} apres verification'))
            continue
        if tagged:
            for entry, _, _, _ in running:
                unresolved.append(
                    (entry, f'saison {season} mixte : derivation par ordre refusee'))
            continue
        if any(match is None for _, _, _, match in running):
            for entry, _, _, _ in running:
                unresolved.append((entry, f'saison {season} : numero brut illisible'))
            continue

        numbers = sorted(int(match.group('number')) for _, _, _, match in running)
        expected = numbers[-1] - numbers[0] + 1
        if len(numbers) != len(set(numbers)) or expected != len(numbers):
            for entry, _, _, _ in running:
                unresolved.append(
                    (entry, f'saison {season} : numeros non contigus ({numbers[0]}-{numbers[-1]} '
                            f'pour {len(numbers)} fichiers), derivation refusee'))
            continue

        offset = numbers[0]
        for entry, _, suffix, match in sorted(running, key=lambda r: int(r[3].group('number'))):
            episode = int(match.group('number')) - offset + 1
            rest = (match.group('rest') or '').strip(' -._')
            plan.append(_make_rename(entry, season, episode, show_name, rest,
                                     suffix, derived=True))

    return plan, unresolved


def _make_rename(source, season, episode, show_name, title, suffix, derived=False):
    """Build the destination path, dropping the title if the name would be too long."""
    code = f'S{season:02d}E{episode:02d}'
    base = f'{show_name} - {code}'
    name = f'{base} - {title}{suffix}' if title else f'{base}{suffix}'
    if len(name.encode('utf-8')) > MAX_NAME_BYTES:
        name = f'{base}{suffix}'
    label = f'{code}{" (ordre)" if derived else ""}'
    return source, f'Season {season:02d}/{name}', label


def find_collisions(plan):
    """Return destinations claimed by more than one source."""
    seen = defaultdict(list)
    for source, destination, _ in plan:
        seen[destination].append(source)
    return {dst: srcs for dst, srcs in seen.items() if len(srcs) > 1}


def shell_quote(value):
    """Quote a value for safe use inside single quotes in a POSIX shell."""
    return "'" + value.replace("'", "'\\''") + "'"


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--show', required=True, help='series name used in the new filenames')
    parser.add_argument('--list', required=True, type=Path, help='rclone lsf -R output')
    parser.add_argument('--remote', required=True, help='rclone path, e.g. "gdrive:Infuse/One Piece"')
    parser.add_argument('--dest', help='destination rclone path (defaults to --remote)')
    parser.add_argument('--out', required=True, type=Path, help='output prefix (.txt and .sh)')
    parser.add_argument('--derive-order', type=int, action='append', default=[], metavar='SEASON',
                        help='number this season from the order of its bare numbers (repeatable)')
    parser.add_argument('--tpslimit', type=int, default=2,
                        help='rclone API calls per second, per worker (default 2)')
    parser.add_argument('--parallel', type=int, default=6,
                        help='concurrent renames (default 6). Wall time is dominated by rclone '
                             'process startup, not by the API, so concurrency helps a lot')
    args = parser.parse_args()

    entries = [line.strip() for line in args.list.read_text().splitlines() if line.strip()]
    plan, unresolved = build_plan(entries, args.show, set(args.derive_order))
    collisions = find_collisions(plan)

    # A rename whose destination is already claimed would silently overwrite.
    if collisions:
        for destination, sources in collisions.items():
            unresolved.extend((source, f'collision sur {destination}') for source in sources)
        plan = [row for row in plan if row[1] not in collisions]

    unchanged = [row for row in plan if row[0] == row[1]]
    plan = [row for row in plan if row[0] != row[1]]

    dest = args.dest or args.remote
    report, script = args.out.with_suffix('.txt'), args.out.with_suffix('.sh')

    lines = [
        f'# {args.show} — {len(entries)} entrees analysees',
        f'# source : {args.remote}',
        f'# dest   : {dest}',
        f'# {len(plan)} renommages, {len(unchanged)} deja conformes, {len(unresolved)} non resolus',
        '', '## Renommages',
    ]
    lines += [f'  {label:14} {src}\n{"":17}-> {dst}' for src, dst, label in plan]
    if unresolved:
        lines += ['', '## NON RESOLUS (aucune action)']
        lines += [f'  [{reason}] {name}' for name, reason in unresolved]
    report.write_text('\n'.join(lines) + '\n')

    # No `set -e`: one failed rename must not abandon the other thousand. Each
    # result is counted and the run ends with a verdict. To resume, regenerate
    # the plan from a fresh listing -- files already renamed are recognised as
    # conformant and dropped, so only the remainder is replayed.
    # Source/destination pairs, NUL-separated so quotes, brackets and accents in
    # episode titles survive untouched.
    pairs = args.out.with_suffix('.pairs')
    payload = bytearray()
    for src, dst, _ in plan:
        payload += f'{args.remote}/{src}'.encode() + b'\0'
        payload += f'{dest}/{dst}'.encode() + b'\0'
    pairs.write_bytes(bytes(payload))

    commands = [
        '#!/usr/bin/env bash',
        '# Renommages cote serveur : aucun octet ne transite.',
        '# Genere par infuse_rename_plan.py — relire le .txt avant de lancer.',
        '# Reprise apres interruption : regenerer le plan, puis relancer.',
        'set -uo pipefail',
        f'PAIRS={shell_quote(str(pairs))}',
        f'TOTAL={len(plan)}',
        'FAILLOG=$(mktemp)',
        'export FAILLOG',
        f'echo "$TOTAL renommages, {args.parallel} en parallele"',
        '',
        f"xargs -0 -n2 -P {args.parallel} -a \"$PAIRS\" bash -c '",
        f'  if rclone moveto --tpslimit {args.tpslimit} "$0" "$1"; then',
        '    echo "OK $(basename "$1")"',
        '  else',
        '    echo "$0" >> "$FAILLOG"; echo "ECHEC $(basename "$0")" >&2',
        "  fi'",
        '',
        'nfail=$(wc -l < "$FAILLOG")',
        'echo "termine : $((TOTAL - nfail)) renommes, $nfail echecs sur $TOTAL"',
        'if [ "$nfail" -gt 0 ]; then',
        '  echo "Fichiers en echec :" >&2; cat "$FAILLOG" >&2',
        '  echo "Regenerer le plan puis relancer pour reprendre." >&2',
        '  exit 1',
        'fi',
    ]
    script.write_text('\n'.join(commands) + '\n')
    script.chmod(0o755)

    print(f'analysees      : {len(entries)}')
    print(f'renommages     : {len(plan)}')
    print(f'deja conformes : {len(unchanged)}')
    print(f'non resolus    : {len(unresolved)}')
    print(f'collisions     : {len(collisions)}')
    print(f'rapport        : {report}')
    print(f'script         : {script}  (a relire avant execution)')
    return 1 if unresolved or collisions else 0


if __name__ == '__main__':
    sys.exit(main())
