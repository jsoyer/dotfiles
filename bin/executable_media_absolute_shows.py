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

# How far back a single global offset stays trustworthy. Specials sprinkled
# through the release numbering shift the drift, so a number far below the
# newest episode is refused rather than resolved with the recent calibration.
RECENT_WINDOW = 60

# Only these count as episodes. Libraries also hold artwork, subtitles and NFO
# files; counting them would inflate the absolute numbering and misplace every
# incoming episode -- observed after 46 season posters were added.
VIDEO_SUFFIXES = {'.mkv', '.mp4', '.avi', '.m4v', '.mov', '.wmv', '.ts', '.m2ts'}

SEASON_DIR_RE = re.compile(r'^Season[\s._-]*(\d{1,3})$', re.I)
# TMDb fills unreleased episode-group slots with this placeholder. It is not a
# title: naming a file after it would just repeat the number we already have.
PLACEHOLDER_TITLE_RE = re.compile(r'^(?:Épisode|Episode)\s+\d+$', re.I)
# Code de saison et de rang tel que la bibliotheque les ecrit.
EPISODE_CODE_RE = re.compile(r'[Ss](\d{1,3})[Ee](\d{1,4})(?!\d)')
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
    tmdb_id: int = 0            # set to use the reference ordering below
    order_group: str = 'TVDB Order'
    # Drift between the release numbering and the reference. Declared rather
    # than derived: it depends on what the release counted, and items excluded
    # from the library (a crossover filed elsewhere) leave no trace to infer it.
    absolute_offset: int | None = None


@dataclass
class Mapping:
    """absolute -> (season, episode) for a show's season structure.

    `offset` absorbs the gap between the release numbering and the reference
    ordering. Release groups usually count crossovers and specials in their
    absolute sequence while TheTVDB keeps them out of the seasons, so the two
    drift apart by however many the release counted. One Piece drifts by one,
    from the Toriko crossover.
    """
    seasons: list = field(default_factory=list)   # [(season, first_abs, last_abs)]
    last_absolute: int = 0
    source: str = ''
    offset: int = 0

    def resolve(self, absolute):
        position = absolute - self.offset
        for season, low, high in self.seasons:
            if low <= position <= high:
                return season, position - low + 1
        return None

    def dernier_present(self, presents):
        """Plus grand numero absolu dont l'episode figure vraiment sur place.

        Compter les fichiers pour deviner le dernier numero suppose une serie
        sans trou : chaque episode manquant abaisse l'estimation d'autant, et le
        garde-fou finit par ecarter des episodes parfaitement legitimes. One
        Piece, a qui il manquait un episode, voyait ainsi son 1174e refuse.

        On parcourt donc la table a l'envers et l'on retient le premier numero
        dont la saison et le rang sont presents.
        """
        if not self.seasons:
            return 0
        dernier_abs = max(high for _, _, high in self.seasons) + self.offset
        for absolu in range(dernier_abs, self.offset, -1):
            resolu = self.resolve(absolu)
            if resolu is not None and resolu in presents:
                return absolu
        return 0

    def next_slot(self):
        """Where the episode following the last known one would land."""
        if not self.seasons:
            return None
        resolved = self.resolve(self.last_absolute + 1)
        if resolved is not None:
            return resolved  # still inside a known season, or opening the next one
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
            tmdb_id=int(entry.get('tmdb_id', 0)),
            order_group=str(entry.get('order_group', 'TVDB Order')),
            absolute_offset=(int(entry['absolute_offset'])
                             if entry.get('absolute_offset') is not None else None),
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
        path = Path(line.strip())
        if path.suffix.lower() not in VIDEO_SUFFIXES:
            continue
        parts = path.parts
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


def build_mapping_from_tvdb_order(tmdb_id, api_key, language='fr-FR',
                                  group_name='TVDB Order', offset=0, timeout=60):
    """Build the table from TMDb's mirror of the TheTVDB ordering.

    TheTVDB's own API is paid, but TMDb publishes the same ordering as an
    "episode group" and that is free with the key we already use. It is
    authoritative on season boundaries, which a table derived from the library
    cannot be: the library only knows the episodes it already holds, so it
    cannot tell that upstream has opened a new season.
    """
    import urllib.parse
    import urllib.request

    def fetch(path, **params):
        params['api_key'] = api_key
        url = f'https://api.themoviedb.org/3{path}?{urllib.parse.urlencode(params)}'
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return json.loads(response.read().decode())

    listing = fetch(f'/tv/{tmdb_id}/episode_groups')
    match = next((g for g in listing.get('results', []) if g.get('name') == group_name), None)
    if match is None:
        available = ', '.join(sorted(g.get('name', '?') for g in listing.get('results', [])))
        raise ValueError(f'Groupe {group_name!r} absent pour TMDb {tmdb_id}. Disponibles: {available}')

    detail = fetch(f'/tv/episode_group/{match["id"]}', language=language)
    seasons, cursor = [], 0
    for group in sorted(detail.get('groups', []), key=lambda g: g.get('order', 0)):
        order = group.get('order', 0)
        count = len(group.get('episodes', []))
        if order < 1 or not count:
            continue  # order 0 holds the specials, which seasons must not absorb
        seasons.append((order, cursor + 1, cursor + count))
        cursor += count
    if not seasons:
        raise ValueError(f'Groupe {group_name!r} sans saison exploitable')
    # `last_absolute` stays 0 here: the reference knows episodes we may not hold
    # yet, and the lookahead guard must be based on what the library actually has.
    return Mapping(seasons=seasons, last_absolute=0,
                   source=f'tmdb:{tmdb_id}:{group_name}', offset=offset)


def calibrate_offset(seasons, season_counts, total_items):
    """Deduce the release-vs-reference drift from the library.

    The library's newest episode is the anchor. The release numbered it after
    counting everything it shipped -- specials and crossovers included, hence
    `total_items` -- while the reference ordering places it at a position that
    counts seasons only. The difference is the drift.
    """
    if not season_counts or not seasons:
        return 0
    last_season = max(season_counts)
    held = season_counts[last_season]
    position = next((low + held - 1 for season, low, high in seasons if season == last_season), None)
    if position is None:
        return 0
    return total_items - position


def load_mapping(path):
    """Read a cached mapping produced by save_mapping."""
    data = json.loads(Path(path).read_text())
    return Mapping(seasons=[tuple(row) for row in data['seasons']],
                   last_absolute=data['last_absolute'],
                   source=data.get('source', ''),
                   offset=data.get('offset', 0))


def save_mapping(mapping, path):
    Path(path).write_text(json.dumps({
        'source': mapping.source,
        'last_absolute': mapping.last_absolute,
        'offset': mapping.offset,
        'seasons': [list(row) for row in mapping.seasons],
    }, indent=2) + '\n')


def refresh_mapping(show, rclone='rclone', timeout=300, api_key=None, language='fr-FR'):
    """Rebuild the table, preferring the reference ordering over the library.

    The library listing is always read: it says which episode is the newest one
    held, and by how much the release numbering drifts from the reference. But
    the season boundaries come from the reference when the show declares one,
    because a library cannot know that upstream has opened a new season.
    """
    result = subprocess.run(
        [rclone, 'lsf', show.destination, '-R', '--files-only'],
        capture_output=True, text=True, timeout=timeout, check=True)
    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    episodes = [line for line in lines if Path(line).suffix.lower() in VIDEO_SUFFIXES]

    if not (show.tmdb_id and api_key):
        mapping = build_mapping_from_listing(episodes, source=show.destination)
        save_mapping(mapping, show.mapping_file)
        return mapping

    season_counts = Counter()
    for line in episodes:
        parts = Path(line).parts
        if len(parts) == 2:
            match = SEASON_DIR_RE.match(parts[0])
            if match:
                season_counts[int(match.group(1))] += 1

    reference = build_mapping_from_tvdb_order(
        show.tmdb_id, api_key, language, group_name=show.order_group)
    if show.absolute_offset is not None:
        offset = show.absolute_offset
    else:
        offset = calibrate_offset(reference.seasons, season_counts, len(episodes))
    mapping = build_mapping_from_tvdb_order(
        show.tmdb_id, api_key, language, group_name=show.order_group, offset=offset)
    # Le dernier numero est celui du dernier episode reellement present, non le
    # nombre de fichiers : un trou dans la serie fausserait le compte, et le
    # garde-fou refuserait ensuite des episodes legitimes.
    presents = set()
    for ligne in episodes:
        parts = Path(ligne).parts
        trouve = EPISODE_CODE_RE.search(Path(ligne).stem)
        if len(parts) == 2 and trouve:
            presents.add((int(trouve.group(1)), int(trouve.group(2))))
    mapping.last_absolute = mapping.dernier_present(presents) or len(episodes) + offset
    save_mapping(mapping, show.mapping_file)
    return mapping


def title_from_episode_group(detail, season, episode):
    """Episode title at (season, episode) in a TMDb episode-group payload.

    Returns None when the slot is missing or TMDb has only a placeholder name.
    The group `order` is the season number; episodes are 1-indexed in list order.
    """
    group = next((item for item in detail.get('groups', [])
                  if item.get('order') == season), None)
    if group is None:
        return None
    episodes = group.get('episodes') or []
    if not 1 <= episode <= len(episodes):
        return None
    name = (episodes[episode - 1].get('name') or '').strip()
    if not name or PLACEHOLDER_TITLE_RE.match(name):
        return None
    return name


def fetch_episode_title(show, season, episode, api_key, language='fr-FR', timeout=60):
    """Title of one episode in the show's declared TMDb ordering, or None."""
    if not (show.tmdb_id and api_key):
        return None
    import urllib.parse
    import urllib.request

    def fetch(path, **params):
        params['api_key'] = api_key
        url = f'https://api.themoviedb.org/3{path}?{urllib.parse.urlencode(params)}'
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return json.loads(response.read().decode())

    listing = fetch(f'/tv/{show.tmdb_id}/episode_groups')
    match = next((group for group in listing.get('results', [])
                  if group.get('name') == show.order_group), None)
    if match is None:
        return None
    detail = fetch(f'/tv/episode_group/{match["id"]}', language=language)
    return title_from_episode_group(detail, season, episode)


def remote_episode_path(show, season, episode, suffix, episode_title=None):
    """Season-relative destination, using the same naming rule as local imports."""
    from media_automation import get_episode_target_name
    name = get_episode_target_name(
        Path(f'x{suffix}'), show.name, season, [episode], episode_title)
    return f'Season {season:02d}/{name}'


def plan_episode(filename, show, mapping):
    """Return (destination_relative_path, season, episode) or raise ValueError."""
    absolute = extract_absolute(filename)
    if absolute is None:
        raise ValueError('numero absolu introuvable')
    if mapping.last_absolute and absolute < mapping.last_absolute - RECENT_WINDOW:
        raise ValueError(
            f'E{absolute} est trop ancien (dernier connu {mapping.last_absolute}) : le decalage '
            f'de numerotation est calibre sur les episodes recents et ne vaut pas si loin en arriere')
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
    target = remote_episode_path(show, season, episode, Path(filename).suffix)
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
