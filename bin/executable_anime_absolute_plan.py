#!/usr/bin/env python3
"""Build a rename plan mapping absolute anime episode numbers to TMDb seasons.

Long-running anime (One Piece, Naruto, Detective Conan...) ship with absolute
numbering -- "One Piece - 1050" -- while TMDb, Plex, Jellyfin and Infuse expect
season/episode pairs. Episode 1050 of One Piece is S21E159, not S01E1050.

This tool is deliberately separate from media_automation.py: that importer runs
unattended every 5 minutes and must not learn to read 4-digit numbers, or it
would parse "Blade Runner 2049" as episode 2049.

It never touches any file. It reads a list of names and emits a plan plus an
rclone script performing server-side renames (nothing is downloaded).

Usage:
    # 1. inventory (server-side listing, no download)
    rclone lsf gdrive:Anime/OnePiece -R --files-only > /tmp/onepiece.txt

    # 2. plan (no change made)
    ./anime_absolute_plan.py --show "One Piece" --year 1999 \
        --list /tmp/onepiece.txt \
        --remote gdrive:Anime/OnePiece \
        --out /tmp/onepiece-plan

    # 3. review /tmp/onepiece-plan.txt, then run /tmp/onepiece-plan.sh
"""
import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import media_automation as ma  # noqa: E402

VIDEO_SUFFIXES = {'.mkv', '.mp4', '.avi', '.m4v', '.mov', '.wmv'}
SUB_SUFFIXES = {'.srt', '.ass', '.ssa', '.sub', '.idx'}

# Tokens that carry digits but never an episode number. Stripped before parsing
# so that "1080p", "x265", "10bit", a CRC32 tag or a release year cannot win.
NOISE_RE = re.compile(
    r'\[[0-9A-F]{8}\]'                       # CRC32 tag: [A1B2C3D4]
    r'|\b\d{3,4}p\b'                         # 1080p, 720p, 2160p
    r'|\bx?26[45]\b|\bhevc\b|\bavc\b'
    r'|\b\d{1,2}[\s._-]?bits?\b'
    r'|\b(?:19|20)\d{2}\b'                   # release year
    r'|\bv\d\b'                              # v2 (release revision)
    r'|\b(?:aac|ac3|flac|opus|ddp?\d?|dts(?:-hd)?)\b'
    r'|\b\d\.\d(?:ch)?\b',                   # 5.1, 2.0ch
    re.I,
)

# Absolute episode number, tried in order of decreasing confidence.
# `(?:v\d)?` absorbs the release revision glued to the number ("1000v2").
ABSOLUTE_PATTERNS = [
    re.compile(r'(?:^|[\s._-])-\s*(?P<n>\d{1,4})(?:v\d)?(?=[\s._-]|$)'),      # "Show - 1050"
    re.compile(r'(?:^|[\s._-])(?:E|EP|EPISODE)[\s._-]?(?P<n>\d{1,4})(?:v\d)?(?=[\s._-]|$)', re.I),
    re.compile(r'(?:^|[\s._-])(?P<n>\d{2,4})(?:v\d)?(?=[\s._-]|$)'),          # bare trailing number
]


def build_absolute_table(seasons):
    """Return [(season, first_absolute, last_absolute, episode_count)] for real seasons."""
    table, cursor = [], 0
    for season in seasons:
        number = season.get('season_number')
        count = season.get('episode_count') or 0
        if not number or number < 1 or not count:
            continue  # skip specials (season 0) and empty seasons
        table.append((number, cursor + 1, cursor + count, count))
        cursor += count
    return table


def absolute_to_season_episode(absolute, table):
    """Map an absolute episode number onto (season, episode); None when out of range."""
    for season, low, high, _ in table:
        if low <= absolute <= high:
            return season, absolute - low + 1
    return None


def extract_absolute(filename):
    """Extract the absolute episode number from a release filename."""
    stem = Path(filename).stem
    # Drop bracketed group prefix: "[SubsPlease] One Piece - 1100" -> "One Piece - 1100"
    stem = re.sub(r'^\s*\[[^\]]+\]\s*', ' ', stem)
    cleaned = NOISE_RE.sub(' ', stem)
    # Remaining bracketed groups hold tags, never the episode number.
    cleaned = re.sub(r'\[[^\]]*\]|\([^)]*\)', ' ', cleaned)
    for pattern in ABSOLUTE_PATTERNS:
        matches = pattern.findall(cleaned)
        if matches:
            # The episode number is the last standalone number of the name.
            return int(matches[-1])
    return None


def plan_renames(names, table, show_name, subdir_template='Season {season:02d}'):
    """Return (plan, unresolved) where plan is a list of (source, destination)."""
    plan, unresolved = [], []
    for name in names:
        suffix = Path(name).suffix.lower()
        if suffix not in VIDEO_SUFFIXES | SUB_SUFFIXES:
            unresolved.append((name, 'extension ignoree'))
            continue
        absolute = extract_absolute(name)
        if absolute is None:
            unresolved.append((name, 'numero absolu introuvable'))
            continue
        mapped = absolute_to_season_episode(absolute, table)
        if mapped is None:
            unresolved.append((name, f'E{absolute} hors des saisons connues'))
            continue
        season, episode = mapped
        target = f'{subdir_template.format(season=season)}/{show_name} - S{season:02d}E{episode:02d}{suffix}'
        plan.append((name, target, absolute))
    return plan, unresolved


def shell_quote(value):
    """Quote a value for safe use inside single quotes in a POSIX shell."""
    return "'" + value.replace("'", "'\\''") + "'"


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--show', required=True, help='series title as searched on TMDb')
    parser.add_argument('--year', help='first air year, disambiguates the TMDb match')
    parser.add_argument('--list', required=True, type=Path,
                        help='file holding one release filename per line (rclone lsf)')
    parser.add_argument('--remote', required=True,
                        help='rclone source path, e.g. gdrive:Anime/OnePiece')
    parser.add_argument('--dest', help='rclone destination path (defaults to --remote)')
    parser.add_argument('--out', required=True, type=Path, help='output prefix (.txt and .sh)')
    parser.add_argument('--config', type=Path,
                        default=Path.home()/'bin/media_automation/media_automation.toml')
    parser.add_argument('--tpslimit', type=int, default=4,
                        help='rclone API calls per second (default 4, protects Drive quota)')
    args = parser.parse_args()

    config = ma.load_automation_config(args.config)
    candidate = ma.search_tmdb_tv(args.show, args.year, config.tmdb_api_key, config.tmdb_language)
    if not candidate:
        sys.exit(f'Aucune serie TMDb pour {args.show!r}')
    details = ma.get_tmdb_tv_details(candidate['id'], config.tmdb_api_key, config.tmdb_language)
    show_name = details.get('name') or args.show
    table = build_absolute_table(details.get('seasons', []))
    if not table:
        sys.exit(f'TMDb ne declare aucune saison exploitable pour {show_name!r}')
    total = table[-1][2]

    names = [line.strip() for line in args.list.read_text().splitlines() if line.strip()]
    plan, unresolved = plan_renames(names, table, show_name)

    dest = args.dest or args.remote
    report = args.out.with_suffix('.txt')
    script = args.out.with_suffix('.sh')

    lines = [
        f'# {show_name} (TMDb {candidate["id"]}) — {len(table)} saisons, {total} episodes',
        f'# source : {args.remote}',
        f'# dest   : {dest}',
        f'# {len(plan)} renommages, {len(unresolved)} non resolus',
        '',
        '## Table de conversion',
    ]
    lines += [f'  S{s:02d} : absolus {lo}-{hi} ({n} episodes)' for s, lo, hi, n in table]
    lines += ['', '## Renommages']
    lines += [f'  E{absolute:<5} {src}\n         -> {dst}' for src, dst, absolute in plan]
    if unresolved:
        lines += ['', '## NON RESOLUS (aucune action)']
        lines += [f'  [{reason}] {name}' for name, reason in unresolved]
    report.write_text('\n'.join(lines) + '\n')

    commands = [
        '#!/usr/bin/env bash',
        '# Renommages cote serveur : aucun octet ne transite.',
        '# Genere par anime_absolute_plan.py — relire le .txt avant de lancer.',
        'set -euo pipefail',
        f'echo "{len(plan)} renommages a effectuer"',
        '',
    ]
    for index, (src, dst, _) in enumerate(plan, 1):
        commands.append(f'echo "[{index}/{len(plan)}] {Path(src).name}"')
        commands.append(
            f'rclone moveto --tpslimit {args.tpslimit} '
            f'{shell_quote(args.remote + "/" + src)} {shell_quote(dest + "/" + dst)}'
        )
    script.write_text('\n'.join(commands) + '\n')
    script.chmod(0o755)

    print(f'serie      : {show_name} — {len(table)} saisons, {total} episodes')
    print(f'analyses   : {len(names)} fichiers')
    print(f'renommages : {len(plan)}')
    print(f'non resolus: {len(unresolved)}')
    print(f'rapport    : {report}')
    print(f'script     : {script}  (a relire avant execution)')
    return 1 if unresolved else 0


if __name__ == '__main__':
    sys.exit(main())
