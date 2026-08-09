#!/usr/bin/env python3
"""Route explicitly declared absolute-numbered shows to a remote library.

Some series ship as absolute episode numbers ("One Piece - 1173") and live on a
cloud remote rather than the local libraries. This module handles exactly those,
and only those: a series absent from the registry keeps the default behaviour.

That opt-in design is the whole point. Teaching the general importer to read
4-digit episode numbers would make it parse "Blade Runner 2049" as episode 2049;
here the rule only fires for a title the registry names.

The absolute -> season/episode table is derived from the destination library
itself, so it follows whatever reference organised it (TheTVDB, in practice)
rather than imposing TMDb's own split.
"""
import json
import re
import subprocess
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python < 3.11
    import tomli as tomllib

SEASON_DIR_RE = re.compile(r'^Season[\s._-]*(\d{1,3})$', re.I)
SEASON_EPISODE_TOKEN_RE = re.compile(
    r'(?:^|[\s._-])(?:\d{1,2}x\d{1,3}|S\d{1,2}E\d{1,3})(?=[\s._-]|$)', re.I)

# Digit-bearing tokens that are never an episode number.
NOISE_RE = re.compile(
    r'\[[0-9A-F]{8}\]|\b\d{3,4}p\b|\bx?26[45]\b|\bhevc\b|\bavc\b'
    r'|\b\d{1,2}[\s._-]?bits?\b|\b(?:19|20)\d{2}\b|\bv\d\b'
    r'|\b(?:aac|ac3|flac|opus|ddp?\d?|dts(?:-hd)?)\b|\b\d\.\d(?:ch)?\b',
    re.I,
)
ABSOLUTE_PATTERNS = [
    re.compile(r'(?:^|[\s._-])-\s*(?P<n>\d{1,4})(?:v\d)?(?=[\s._-]|$)'),
    re.compile(r'(?:^|[\s._-])(?:E|EP|EPISODE)[\s._-]?(?P<n>\d{1,4})(?:v\d)?(?=[\s._-]|$)', re.I),
    re.compile(r'(?:^|[\s._-])(?P<n>\d{2,4})(?:v\d)?(?=[\s._-]|$)'),
]


@dataclass(frozen=True)
class AbsoluteShow:
    """A series whose episodes arrive numbered absolutely and live on a remote."""
    name: str
    destination: str
    mapping_file: Path
    aliases: tuple = ()
    lookahead: int = 1  # how far past the last known episode we dare go


@dataclass
class Mapping:
    """absolute -> (season, episode), derived from the destination library."""
    seasons: list = field(default_factory=list)   # [(season, first_abs, last_abs)]
    last_absolute: int = 0
    source: str = ''

    def resolve(self, absolute):
        for season, low, high in self.seasons:
            if low <= absolute <= high:
                return season, absolute - low + 1
        return None

    def next_slot(self):
        """Where the episode following the library would land."""
        if not self.seasons:
            return None
        season, low, high = self.seasons[-1]
        return season, high - low + 2


def load_registry(path):
    """Read the show registry; returns [] when the file is absent."""
    path = Path(path)
    if not path.is_file():
        return []
    raw = tomllib.loads(path.read_text())
    shows = []
    for entry in raw.get('show', []):
        name = entry.get('name')
        destination = entry.get('destination')
        mapping = entry.get('mapping')
        if not (name and destination and mapping):
            raise ValueError(f'Entree de registre incomplete: {entry!r}')
        if entry.get('numbering', 'absolute') != 'absolute':
            continue
        shows.append(AbsoluteShow(
            name=name,
            destination=destination,
            mapping_file=(path.parent / mapping) if not Path(mapping).is_absolute() else Path(mapping),
            aliases=tuple(entry.get('aliases') or [name]),
            lookahead=int(entry.get('lookahead', 1)),
        ))
    return shows


def normalise(text):
    """Lowercase alphanumeric form used to compare titles."""
    return re.sub(r'[^a-z0-9]+', ' ', text.lower()).strip()


def match_show(filename, shows):
    """Return the registered show whose alias prefixes this filename, else None.

    Fansub releases lead with a group tag ("[SubsPlease] One Piece - 1173"),
    which is stripped first so the title still anchors at the start.
    """
    stem = normalise(re.sub(r'^\s*\[[^\]]+\]\s*', ' ', Path(filename).stem))
    best = None
    for show in shows:
        for alias in show.aliases:
            key = normalise(alias)
            # Anchored at the start: a title mentioned mid-name is not the show.
            if key and (stem == key or stem.startswith(key + ' ')):
                if best is None or len(key) > len(normalise(best[1])):
                    best = (show, alias)
    return best[0] if best else None


def extract_absolute(filename):
    """Absolute episode number, or None when the name is not absolutely numbered."""
    stem = Path(filename).stem
    if SEASON_EPISODE_TOKEN_RE.search(stem):
        return None  # already season/episode: not our case
    stem = re.sub(r'^\s*\[[^\]]+\]\s*', ' ', stem)
    cleaned = NOISE_RE.sub(' ', stem)
    cleaned = re.sub(r'\[[^\]]*\]|\([^)]*\)', ' ', cleaned)
    for pattern in ABSOLUTE_PATTERNS:
        found = pattern.findall(cleaned)
        if found:
            return int(found[-1])
    return None


def build_mapping_from_listing(lines, source=''):
    """Derive the absolute table from a `rclone lsf -R` listing of the library.

    Season N holds the absolute numbers following season N-1, in season order.
    Verified against a library whose season 16 carried real absolute numbers:
    the cumulative count predicted its first number exactly.
    """
    counts = Counter()
    for line in lines:
        parts = Path(line.strip()).parts
        if len(parts) != 2:
            continue
        match = SEASON_DIR_RE.match(parts[0])
        if match:
            counts[int(match.group(1))] += 1
    seasons, cursor = [], 0
    for season in sorted(counts):
        count = counts[season]
        seasons.append((season, cursor + 1, cursor + count))
        cursor += count
    return Mapping(seasons=seasons, last_absolute=cursor, source=source)


def load_mapping(path):
    """Read a cached mapping produced by save_mapping."""
    data = json.loads(Path(path).read_text())
    return Mapping(seasons=[tuple(row) for row in data['seasons']],
                   last_absolute=data['last_absolute'],
                   source=data.get('source', ''))


def save_mapping(mapping, path):
    Path(path).write_text(json.dumps({
        'source': mapping.source,
        'last_absolute': mapping.last_absolute,
        'seasons': [list(row) for row in mapping.seasons],
    }, indent=2) + '\n')


def refresh_mapping(show, rclone='rclone', timeout=300):
    """Rebuild the table from the live destination library."""
    result = subprocess.run(
        [rclone, 'lsf', show.destination, '-R', '--files-only'],
        capture_output=True, text=True, timeout=timeout, check=True)
    mapping = build_mapping_from_listing(result.stdout.splitlines(), source=show.destination)
    save_mapping(mapping, show.mapping_file)
    return mapping


def plan_episode(filename, show, mapping):
    """Return (destination_relative_path, season, episode) or raise ValueError."""
    absolute = extract_absolute(filename)
    if absolute is None:
        raise ValueError('numero absolu introuvable')
    resolved = mapping.resolve(absolute)
    if resolved is None:
        limit = mapping.last_absolute + show.lookahead
        if absolute > limit:
            raise ValueError(
                f'E{absolute} depasse la bibliotheque connue (dernier {mapping.last_absolute}, '
                f'tolerance +{show.lookahead}) — nouvelle saison probable, verification requise')
        slot = mapping.next_slot()
        if slot is None:
            raise ValueError('table de conversion vide')
        resolved = slot
    season, episode = resolved
    suffix = Path(filename).suffix
    target = f'Season {season:02d}/{show.name} - S{season:02d}E{episode:02d}{suffix}'
    return target, season, episode


def remote_exists(destination, rclone='rclone', timeout=120):
    """True when the remote path already holds a file (never overwrite blindly)."""
    result = subprocess.run([rclone, 'lsf', destination],
                            capture_output=True, text=True, timeout=timeout)
    return result.returncode == 0 and bool(result.stdout.strip())


def push_episode(local_path, destination, dry_run=False, rclone='rclone',
                 tpslimit=4, timeout=7200):
    """Upload one episode and remove the local copy. Returns the command run."""
    command = [rclone, 'moveto', '--tpslimit', str(tpslimit),
               str(local_path), destination]
    if dry_run:
        return command
    subprocess.run(command, check=True, capture_output=True, text=True, timeout=timeout)
    return command
