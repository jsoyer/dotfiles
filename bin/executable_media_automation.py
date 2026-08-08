#!/usr/bin/env python3
"""Reorganize a movies directory into a clean Jellyfin/Plex/Kodi structure.

Usage:
    python3 reorganize_movies.py [OPTIONS] [DIRECTORY]

Arguments:
    DIRECTORY   Path to movies directory (default: current directory)

Options:
    --dry-run   Show what would be done without moving anything
    --stats     Show collection statistics (total, per-quality, multi-quality)
    --help      Show this help message

Structure target:
    movies/
      Title (Year)/
        Title (Year).mkv
        Title (Year).nfo
        poster.jpg
        fanart.jpg

Multi-version films get quality subdirectories:
    Title (Year)/
      1080p/
      2160p/
"""

import argparse
import json
import logging
import os
import re
import shutil
import sys
import time
import tomllib
import unicodedata
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass, field
from logging.handlers import RotatingFileHandler
from pathlib import Path

import fcntl

SCRIPT_NAME = Path(__file__).name
VIDEO_EXTENSIONS = {'.mkv', '.mp4', '.avi', '.wmv', '.m4v', '.mov'}
ART_NAMES = {'poster.jpg', 'fanart.jpg', 'fanart.png', 'logo.png', 'logo.svg',
             'clearlogo.png', 'clearlogo.svg', 'banner.jpg', 'thumb.jpg',
             'landscape.jpg', 'disc.png'}
ILLEGAL_CHARS = re.compile(r'[\\/:*?"<>|]')
QUALITY_DIR_NAMES = ('2160p', '1080p', '720p', '480p')
ROMAN_NUMERALS = {
    'i': '1',
    'ii': '2',
    'iii': '3',
    'iv': '4',
    'v': '5',
    'vi': '6',
    'vii': '7',
    'viii': '8',
    'ix': '9',
    'x': '10',
}
TMDB_API_BASE = 'https://api.themoviedb.org/3'
TMDB_IMAGE_BASE = 'https://image.tmdb.org/t/p/original'
PARTIAL_EXTENSIONS = {'.part', '.tmp', '.crdownload', '.download'}
ANIMATION_GENRE_ID = 16
LOGGER = logging.getLogger(SCRIPT_NAME)

QUALITY_PATTERNS = [
    (re.compile(r'2160p|4K|UHD', re.I), '2160p'),
    (re.compile(r'1080p', re.I), '1080p'),
    (re.compile(r'720p', re.I), '720p'),
    (re.compile(r'480p', re.I), '480p'),
]

PAREN_YEAR_RE = re.compile(r'^(.+?)\s*\((\d{4})\)')
DOT_YEAR_RE = re.compile(r'^(.+?)[.\s_](\d{4})[.\s_]')
DOT_YEAR_END_RE = re.compile(r'^(.+?)[.\s_](\d{4})$')
DASH_RE = re.compile(r'^(.+?)\s*-\s*(1080p|720p|2160p|mHD)', re.I)
EPISODE_PATTERNS = [
    re.compile(r'^(?P<title>.+?)[.\s_-]+S(?P<season>\d{1,2})E(?P<episode>\d{1,3})(?:E(?P<episode2>\d{1,3}))?', re.I),
    re.compile(r'^(?P<title>.+?)[.\s_-]+(?P<season>\d{1,2})x(?P<episode>\d{1,3})(?:-(?P<episode2>\d{1,3}))?', re.I),
    # Season-less releases: "Show.1982.TV.Series.E01.MULTi.1080p", "Show - Ep05".
    # The episode token must stand alone (delimiter or end of name) to avoid
    # matching release-group suffixes. Season defaults to 1, or is taken from
    # the parent directory when it advertises one.
    re.compile(
        r'^(?P<title>.+?)[.\s_-]+(?:E|EP|EPISODE)[.\s_-]?(?P<episode>\d{1,3})'
        r'(?:[-.\s_]?E(?P<episode2>\d{1,3}))?(?=[.\s_-]|$)',
        re.I,
    ),
]

# Standalone season markers used when the episode token carries no season.
SEASON_HINT_RE = re.compile(r'(?:^|[.\s_-])(?:S|SAISON|SEASON)[.\s_-]?(\d{1,2})(?=[.\s_-]|$)', re.I)

# Release noise stripped from a parsed series title before querying TMDb.
SERIES_TITLE_NOISE_RE = re.compile(
    r'(?:^|[.\s_-])(?:'
    r'TV[.\s_-]?SERIES|COMPLETE(?:D)?|INTEGRALE|INT[EÉ]GRALE|SERIE[.\s_-]?COMPLETE|'
    r'MULTI|VOSTFR|VF{1,2}|VFF|VFQ|TRUEFRENCH|FRENCH|SUBFRENCH|ENGLISH|JAPANESE|'
    r'\d{3,4}P|4K|UHD|HDR\d*|SDR|BLURAY|BLU[.\s_-]?RAY|BDRIP|BRRIP|WEB[.\s_-]?DL|'
    r'WEBRIP|HDTV|DVDRIP|REMUX|X26[45]|H[.\s_-]?26[45]|HEVC|AVC|XVID|DIVX|'
    r'\d{1,2}BITS?|AAC\d*|AC3|DTS(?:[.\s_-]?HD)?|DDP?\d?(?:[.\s_-]?\d)?|FLAC|OPUS|'
    r'ATMOS|TRUEHD|\d[.\s_-]?\d(?:CH)?|REPACK|PROPER|FINAL|EXTENDED|UNCUT'
    r')(?=[.\s_-]|$)',
    re.I,
)


@dataclass(slots=True)
class LoggingConfig:
    """Logging configuration for automated inbox scans."""

    file: Path | None = None
    level: str = 'INFO'
    max_bytes: int = 5 * 1024 * 1024
    backup_count: int = 5


@dataclass(slots=True)
class TelegramConfig:
    """Telegram notification settings."""

    enabled: bool = False
    bot_token: str | None = None
    chat_id: str | None = None
    timeout: int = 15


@dataclass(slots=True)
class InboxConfig:
    """Incoming scan settings."""

    path: Path
    stability_seconds: int = 300
    lock_file: Path | None = None


@dataclass(slots=True)
class RoutesConfig:
    """Output roots for imported media."""

    movies: Path
    series: Path
    anime: Path


@dataclass(slots=True)
class RoutingConfig:
    """Configurable routing for anime content."""

    anime_movies_to: str = 'anime'
    anime_series_to: str = 'anime'


@dataclass(slots=True)
class AutomationConfig:
    """Full automation settings loaded from TOML."""

    inbox: InboxConfig
    routes: RoutesConfig
    tmdb_api_key: str | None
    routing: RoutingConfig = field(default_factory=RoutingConfig)
    tmdb_language: str = 'fr-FR'
    fetch_metadata: bool = True
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    telegram: TelegramConfig = field(default_factory=TelegramConfig)


@dataclass(slots=True)
class IncomingItem:
    """A single stable incoming media file to import."""

    video_path: Path
    related_files: list[Path]


@dataclass(slots=True)
class ImportSummary:
    """Execution summary for an automated inbox scan."""

    detected_items: int = 0
    imported_items: int = 0
    imported_movies: int = 0
    imported_series: int = 0
    imported_anime: int = 0
    moved_files: int = 0
    skipped_items: int = 0
    errors: int = 0
    skipped_details: list[str] = field(default_factory=list)
    imported_details: list[str] = field(default_factory=list)


def sanitize(name):
    """Remove illegal filesystem characters."""
    return ILLEGAL_CHARS.sub('', name).strip()


def normalize(text):
    """Normalize text for fuzzy comparison."""
    text = re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', text)
    text = unicodedata.normalize('NFD', text)
    text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
    text = text.lower()
    text = text.replace('&', ' and ')
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def bool_from_config(value, default=False):
    """Parse a flexible boolean value from config input."""
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in {'1', 'true', 'yes', 'on'}
    return default


def resolve_config_path(value):
    """Return a resolved Path for a config value when provided."""
    if value in (None, ''):
        return None
    return Path(value).expanduser().resolve()


def configure_logging(settings):
    """Configure console and rotating-file logging."""
    LOGGER.handlers.clear()
    LOGGER.setLevel(getattr(logging, settings.level.upper(), logging.INFO))
    LOGGER.propagate = False

    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    LOGGER.addHandler(stream_handler)

    if settings.file:
        settings.file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            settings.file,
            maxBytes=settings.max_bytes,
            backupCount=settings.backup_count,
            encoding='utf-8',
        )
        file_handler.setFormatter(formatter)
        LOGGER.addHandler(file_handler)


def log_message(message, level='info'):
    """Log a message and keep legacy stdout-oriented flow visible."""
    log_func = getattr(LOGGER, level, LOGGER.info)
    if LOGGER.handlers:
        log_func(message)
    else:
        print(message)


def load_automation_config(config_path):
    """Load automation settings from a TOML config file."""
    with config_path.open('rb') as handle:
        raw = tomllib.load(handle)

    inbox_raw = raw.get('inbox', {})
    routes_raw = raw.get('routes', {})
    routing_raw = raw.get('routing', {})
    tmdb_raw = raw.get('tmdb', {})
    logging_raw = raw.get('logging', {})
    telegram_raw = raw.get('telegram', {})

    inbox_path = resolve_config_path(inbox_raw.get('path'))
    if not inbox_path:
        raise ValueError('Config section [inbox] must define `path`.')

    movies_root = resolve_config_path(routes_raw.get('movies'))
    series_root = resolve_config_path(routes_raw.get('series'))
    anime_root = resolve_config_path(routes_raw.get('anime'))
    if not all((movies_root, series_root, anime_root)):
        raise ValueError('Config section [routes] must define `movies`, `series` and `anime`.')

    anime_movies_to = str(routing_raw.get('anime_movies_to', 'anime')).strip().lower()
    anime_series_to = str(routing_raw.get('anime_series_to', 'anime')).strip().lower()
    if anime_movies_to not in {'movies', 'anime'}:
        raise ValueError('Config section [routing].anime_movies_to must be `movies` or `anime`.')
    if anime_series_to not in {'series', 'anime'}:
        raise ValueError('Config section [routing].anime_series_to must be `series` or `anime`.')

    return AutomationConfig(
        inbox=InboxConfig(
            path=inbox_path,
            stability_seconds=int(inbox_raw.get('stability_seconds', 300)),
            lock_file=resolve_config_path(inbox_raw.get('lock_file')),
        ),
        routes=RoutesConfig(
            movies=movies_root,
            series=series_root,
            anime=anime_root,
        ),
        tmdb_api_key=tmdb_raw.get('api_key') or os.environ.get('TMDB_API_KEY'),
        routing=RoutingConfig(
            anime_movies_to=anime_movies_to,
            anime_series_to=anime_series_to,
        ),
        tmdb_language=tmdb_raw.get('language', 'fr-FR'),
        fetch_metadata=bool_from_config(tmdb_raw.get('fetch_metadata'), True),
        logging=LoggingConfig(
            file=resolve_config_path(logging_raw.get('file')),
            level=str(logging_raw.get('level', 'INFO')).upper(),
            max_bytes=int(logging_raw.get('max_bytes', 5 * 1024 * 1024)),
            backup_count=int(logging_raw.get('backup_count', 5)),
        ),
        telegram=TelegramConfig(
            enabled=bool_from_config(telegram_raw.get('enabled'), False),
            bot_token=telegram_raw.get('bot_token') or os.environ.get('TELEGRAM_BOT_TOKEN'),
            chat_id=str(telegram_raw.get('chat_id') or os.environ.get('TELEGRAM_CHAT_ID') or '') or None,
            timeout=int(telegram_raw.get('timeout', 15)),
        ),
    )


def split_telegram_message(message, chunk_size=3900):
    """Split a Telegram message into safe chunks."""
    lines = message.splitlines()
    chunks = []
    current = []
    current_len = 0
    for line in lines:
        extra = len(line) + 1
        if current and current_len + extra > chunk_size:
            chunks.append('\n'.join(current))
            current = [line]
            current_len = extra
        else:
            current.append(line)
            current_len += extra
    if current:
        chunks.append('\n'.join(current))
    return chunks


def emojiize_telegram_message(message):
    """Add friendly emojis to Telegram messages without altering console logs."""
    transformed = []
    for line in message.splitlines():
        stripped = line.strip()

        if line.startswith('Detected '):
            transformed.append(f"🔎 {line}")
            continue
        if line.startswith('DRY-RUN Inbox summary'):
            transformed.append(f"🧪 {line}")
            continue
        if line.startswith('Inbox summary'):
            transformed.append(f"📦 {line}")
            continue
        if '[IMPORT:MOVIE]' in line:
            transformed.append(line.replace('[IMPORT:MOVIE]', '🎬 [FILM]'))
            continue
        if '[IMPORT:SERIES]' in line:
            transformed.append(line.replace('[IMPORT:SERIES]', '📺 [SÉRIE]'))
            continue
        if '[IMPORT:ANIME]' in line:
            transformed.append(line.replace('[IMPORT:ANIME]', '🌸 [ANIME]'))
            continue
        if '[SKIP]' in line:
            transformed.append(line.replace('[SKIP]', '⏭️ [SKIP]'))
            continue
        if '[ERROR]' in line:
            transformed.append(line.replace('[ERROR]', '❌ [ERROR]'))
            continue
        if '[SCAN]' in line:
            transformed.append(line.replace('[SCAN]', '🔎 [SCAN]'))
            continue
        if stripped == 'Skipped:':
            transformed.append('⏭️ Skipped:')
            continue
        if stripped == 'Imported:':
            transformed.append('✅ Imported:')
            continue
        if stripped.startswith('- detected items:'):
            transformed.append(line.replace('- detected items:', '🔎 detected items:'))
            continue
        if stripped.startswith('- imported items:'):
            transformed.append(line.replace('- imported items:', '✅ imported items:'))
            continue
        if stripped.startswith('- imported movies:'):
            transformed.append(line.replace('- imported movies:', '🎬 imported movies:'))
            continue
        if stripped.startswith('- imported series:'):
            transformed.append(line.replace('- imported series:', '📺 imported series:'))
            continue
        if stripped.startswith('- imported anime:'):
            transformed.append(line.replace('- imported anime:', '🌸 imported anime:'))
            continue
        if stripped.startswith('- moved files:'):
            transformed.append(line.replace('- moved files:', '📁 moved files:'))
            continue
        if stripped.startswith('- skipped items:'):
            transformed.append(line.replace('- skipped items:', '⏭️ skipped items:'))
            continue
        if stripped.startswith('- errors:'):
            transformed.append(line.replace('- errors:', '❌ errors:'))
            continue
        if stripped.startswith('- '):
            transformed.append(line.replace('- ', '• ', 1))
            continue
        if stripped.startswith('* '):
            transformed.append(line.replace('* ', '📎 ', 1))
            continue

        transformed.append(line)

    return '\n'.join(transformed)


def send_telegram_message(settings, message):
    """Send a Telegram notification when configured."""
    if not settings.enabled or not settings.bot_token or not settings.chat_id:
        return

    url = f"https://api.telegram.org/bot{settings.bot_token}/sendMessage"
    telegram_message = emojiize_telegram_message(message)
    for chunk in split_telegram_message(telegram_message):
        payload = urllib.parse.urlencode({
            'chat_id': settings.chat_id,
            'text': chunk,
            'disable_web_page_preview': 'true',
        }).encode('utf-8')
        request = urllib.request.Request(url, data=payload, method='POST')
        try:
            with urllib.request.urlopen(request, timeout=settings.timeout):
                pass
        except Exception as exc:
            LOGGER.warning("Telegram notification failed: %s", exc)


@contextmanager
def exclusive_lock(lock_path):
    """Prevent concurrent cron runs against the same inbox."""
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open('w', encoding='utf-8') as handle:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError(f"Another scan is already running (lock: {lock_path})") from exc
        handle.write(str(os.getpid()))
        handle.flush()
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def roman_to_arabic_tokens(text):
    """Convert standalone Roman numeral tokens to Arabic equivalents."""
    tokens = text.split()
    return ' '.join(ROMAN_NUMERALS.get(token, token) for token in tokens)


def remove_trailing_sequel_marker(text):
    """Drop a trailing sequel marker like 1/I used for the first film."""
    tokens = text.split()
    if tokens and tokens[-1] in {'1', 'i'}:
        return ' '.join(tokens[:-1]).strip()
    return text


def should_add_stripped_title_alias(text):
    """Return True when a stripped base title is specific enough to be safe."""
    tokens = [token for token in normalize(text).split() if len(token) > 1]
    return len(tokens) >= 2


def title_aliases(text):
    """Return normalized title aliases for loose FR/EN matching."""
    aliases = set()
    if not text:
        return aliases

    candidates = {text}
    for separator in (':', ' - ', ' – ', ' — '):
        if separator in text:
            stripped = text.split(separator, 1)[0].strip()
            if should_add_stripped_title_alias(stripped):
                candidates.add(stripped)

    for candidate in list(candidates):
        normalized = normalize(candidate)
        if not normalized:
            continue
        aliases.add(normalized)
        romanized = roman_to_arabic_tokens(normalized)
        aliases.add(romanized)
        trimmed = remove_trailing_sequel_marker(romanized)
        if trimmed:
            aliases.add(trimmed)

    return {alias for alias in aliases if alias}


def word_set(text):
    """Extract meaningful words from normalized text."""
    return {w for w in normalize(text).split() if len(w) > 1}


def detect_quality(filename):
    """Detect resolution from filename."""
    for pattern, label in QUALITY_PATTERNS:
        if pattern.search(filename):
            return label
    return None


def parse_nfo(nfo_path):
    """Extract title and year from NFO XML file."""
    metadata = parse_nfo_metadata(nfo_path)
    return metadata['title'], metadata['year']


def extract_unique_ids(root):
    """Extract TMDb and IMDb IDs from common NFO fields."""
    tmdbid = root.findtext('tmdbid')
    imdbid = root.findtext('id')

    for uniqueid in root.findall('uniqueid'):
        uid_type = (uniqueid.get('type') or '').strip().lower()
        uid_value = (uniqueid.text or '').strip()
        if not uid_value:
            continue
        if uid_type == 'tmdb' and not tmdbid:
            tmdbid = uid_value
        elif uid_type == 'imdb' and (not imdbid or imdbid.startswith('tt')):
            imdbid = uid_value

    tmdbid = tmdbid.strip() if tmdbid else None
    imdbid = imdbid.strip() if imdbid else None
    return tmdbid, imdbid


def parse_nfo_metadata(nfo_path):
    """Extract key metadata from an NFO XML file."""
    try:
        tree = ET.parse(nfo_path)
        root = tree.getroot()
        title = root.findtext('title')
        year = root.findtext('year')
        originaltitle = root.findtext('originaltitle')
        sorttitle = root.findtext('sorttitle')
        english_title = root.findtext('english_title')
        tmdbid, imdbid = extract_unique_ids(root)
        return {
            'title': title.strip() if title else None,
            'year': year.strip() if year else None,
            'originaltitle': originaltitle.strip() if originaltitle else None,
            'sorttitle': sorttitle.strip() if sorttitle else None,
            'english_title': english_title.strip() if english_title else None,
            'tmdbid': tmdbid,
            'imdbid': imdbid,
        }
    except Exception:
        return {
            'title': None,
            'year': None,
            'originaltitle': None,
            'sorttitle': None,
            'english_title': None,
            'tmdbid': None,
            'imdbid': None,
        }


def parse_filename(filename):
    """Extract title and year from a scene-style filename."""
    name = filename
    for suffix in ['-fanart', '-poster', '-clearlogo', '-logo', '-banner',
                   '-thumb', '-landscape', '-disc', '-backdrop']:
        name = name.split(suffix)[0]
    name = re.sub(r'\.(mkv|mp4|avi|jpg|png|svg|nfo|srt|sub|idx|ass)$', '', name, flags=re.I)

    m = PAREN_YEAR_RE.match(name)
    if m:
        title = m.group(1).replace('.', ' ').replace('_', ' ').strip()
        return title, m.group(2)

    m = DOT_YEAR_RE.match(name)
    if m:
        title = m.group(1).replace('.', ' ').replace('_', ' ').strip()
        year = m.group(2)
        if 1900 <= int(year) <= 2099:
            return title, year

    m = DOT_YEAR_END_RE.match(name)
    if m:
        title = m.group(1).replace('.', ' ').replace('_', ' ').strip()
        year = m.group(2)
        if 1900 <= int(year) <= 2099:
            return title, year

    m = DASH_RE.match(name)
    if m:
        title = m.group(1).replace('.', ' ').replace('_', ' ').strip()
        return title, None

    return None, None


def clean_series_title(raw_title):
    """Strip release noise and a trailing year from a parsed series title."""
    title = raw_title.replace('.', ' ').replace('_', ' ')
    previous = None
    while previous != title:
        previous = title
        title = SERIES_TITLE_NOISE_RE.sub(' ', title)
        title = SEASON_HINT_RE.sub(' ', title)
    title = re.sub(r'[\s.\-_]*\(?(?:19|20)\d{2}\)?[\s.\-_]*$', ' ', title)
    title = re.sub(r'\s+', ' ', title).strip(' -.')
    return title


def parse_season_hint(text):
    """Return a season number advertised by a directory or file name, if any."""
    if not text:
        return None
    match = SEASON_HINT_RE.search(text)
    return int(match.group(1)) if match else None


def parse_episode_filename(filename, parent_name=None):
    """Extract series title, season and episode numbers from common TV patterns."""
    name = re.sub(r'\.(mkv|mp4|avi|wmv|m4v|mov|srt|sub|idx|ass|ssa)$', '', filename, flags=re.I)
    name = name.replace('_', ' ').strip()
    for pattern in EPISODE_PATTERNS:
        match = pattern.match(name)
        if not match:
            continue
        raw_title = match.group('title')
        groups = match.groupdict()
        if groups.get('season'):
            season = int(groups['season'])
        else:
            # Season-less release: prefer a marker on the release/parent folder.
            season = parse_season_hint(raw_title) or parse_season_hint(parent_name) or 1
        title = clean_series_title(raw_title) or raw_title.replace('.', ' ').strip(' -.')
        episodes = [int(match.group('episode'))]
        if groups.get('episode2'):
            episodes.append(int(groups['episode2']))
        return title, season, episodes
    return None, None, []


def is_partial_file(path):
    """Return True when a file still looks incomplete."""
    return path.suffix.lower() in PARTIAL_EXTENSIONS or path.name.endswith('.partial')


def is_stable_file(path, stability_seconds):
    """Return True when a file has not changed recently."""
    age = time.time() - path.stat().st_mtime
    return age >= stability_seconds


def gather_incoming_items(incoming_dir, stability_seconds):
    """Collect stable video files and their companions from the inbox."""
    items = []
    seen = set()
    for video_path in sorted(incoming_dir.rglob('*')):
        if not video_path.is_file():
            continue
        if video_path.suffix.lower() not in VIDEO_EXTENSIONS:
            continue
        if is_partial_file(video_path) or not is_stable_file(video_path, stability_seconds):
            continue

        related = [
            candidate for candidate in find_incoming_related_files(video_path)
            if is_stable_file(candidate, stability_seconds)
        ]
        key = tuple(sorted(str(path) for path in related))
        if key in seen:
            continue
        seen.add(key)
        items.append(IncomingItem(video_path=video_path, related_files=related))
    return items


def summarize_incoming_items(items, inbox_dir):
    """Build a short text summary of what was detected in the inbox."""
    lines = [f"Detected {len(items)} stable item(s) in {inbox_dir}:", ""]
    for item in items:
        lines.append(f"- {item.video_path.relative_to(inbox_dir)}")
        for related in item.related_files:
            if related != item.video_path:
                lines.append(f"  * {related.relative_to(inbox_dir)}")
    return '\n'.join(lines)


def find_related_files(nfo_path):
    """Find all files related to a given NFO file."""
    nfo_dir = nfo_path.parent
    nfo_stem = nfo_path.stem

    if nfo_path.name == 'movie.nfo':
        return [f for f in nfo_dir.iterdir() if f.is_file()]

    related = []
    for f in nfo_dir.iterdir():
        if f.is_file() and f.name.startswith(nfo_stem):
            related.append(f)
    return related


def get_new_filename(f, clean_name):
    """Determine the new filename for a file."""
    ext = f.suffix.lstrip('.')
    name_lower = f.name.lower()

    if any(tag in name_lower for tag in ['-poster.', '_poster.']):
        return f"poster.{ext}"
    elif any(tag in name_lower for tag in ['-fanart.', '_fanart.', '-backdrop.']):
        return f"fanart.{ext}"
    elif any(tag in name_lower for tag in ['-clearlogo.', '-logo.']):
        return f"logo.{ext}"
    elif '-banner.' in name_lower:
        return f"banner.{ext}"
    elif '-thumb.' in name_lower:
        return f"poster.{ext}"
    elif '-landscape.' in name_lower:
        return f"landscape.{ext}"
    elif '-disc.' in name_lower:
        return f"disc.{ext}"
    elif ext == 'nfo':
        return f"{clean_name}.nfo"
    elif ext in ('mkv', 'mp4', 'avi', 'wmv'):
        return f"{clean_name}.{ext}"
    elif ext in ('srt', 'sub', 'idx', 'ass', 'ssa'):
        return f"{clean_name}.{ext}"
    return f.name


def get_art_name(f):
    """Normalize artwork filename."""
    ext = f.suffix
    name_lower = f.name.lower()
    if 'poster' in name_lower or 'thumb' in name_lower:
        return f"poster{ext}"
    elif 'fanart' in name_lower or 'backdrop' in name_lower:
        return f"fanart{ext}"
    elif 'clearlogo' in name_lower or 'logo' in name_lower:
        return f"logo{ext}"
    elif 'banner' in name_lower:
        return f"banner{ext}"
    elif 'landscape' in name_lower:
        return f"landscape{ext}"
    elif 'disc' in name_lower:
        return f"disc{ext}"
    return f.name


def fuzzy_match_dir(old_name, proper_dirs):
    """Find the best matching proper dir by word similarity."""
    old_words = word_set(old_name)
    if not old_words:
        return None, 0

    best = None
    best_score = 0

    for pd in proper_dirs:
        m = re.match(r'^(.+?)\s*\(\d{4}\)$', pd.name)
        if not m:
            continue
        pd_words = word_set(m.group(1))
        if not pd_words:
            continue

        common = old_words & pd_words
        if not common:
            continue

        score = len(common) / max(len(old_words), len(pd_words))
        if old_words <= pd_words:
            score += 0.5

        if score > best_score:
            best_score = score
            best = pd

    if best_score >= 0.4:
        return best, best_score
    return None, 0


def is_proper_dir(d):
    """A properly named dir ends with (YYYY)."""
    return bool(re.search(r'\(\d{4}\)$', d.name))


def is_script_file(f):
    """Check if file is a script or log."""
    return f.suffix in ('.py', '.sh', '.log')


def dir_has_art(d, art_type):
    """Check if directory or quality subdirs has artwork."""
    for ext in ('.jpg', '.png', '.svg'):
        if (d / f"{art_type}{ext}").exists():
            return True
    for sub in d.iterdir():
        if sub.is_dir():
            for ext in ('.jpg', '.png', '.svg'):
                if (sub / f"{art_type}{ext}").exists():
                    return True
    return False


def get_quality_subdirs(d):
    """Return known quality subdirectories in preferred order."""
    if not d.exists():
        return []
    quality_map = {
        sub.name: sub for sub in d.iterdir()
        if sub.is_dir() and sub.name in QUALITY_DIR_NAMES
    }
    return [quality_map[name] for name in QUALITY_DIR_NAMES if name in quality_map]


def get_root_media_files(d):
    """Return non-script root files for a movie directory."""
    return [f for f in d.iterdir() if f.is_file() and not is_script_file(f)]


def pick_quality_dir(root_file, quality_dirs):
    """Choose the quality directory that should own a root-level file."""
    detected = detect_quality(root_file.name)
    if detected:
        for quality_dir in quality_dirs:
            if quality_dir.name == detected:
                return quality_dir

    if len(quality_dirs) == 1:
        return quality_dirs[0]

    for preferred in ('1080p', '2160p', '720p', '480p'):
        for quality_dir in quality_dirs:
            if quality_dir.name == preferred:
                return quality_dir

    return quality_dirs[0]


def get_consolidated_filename(f, clean_name):
    """Normalize filenames when consolidating into a quality directory."""
    if f.suffix.lower() in ('.jpg', '.png', '.svg'):
        return get_art_name(f)
    return get_new_filename(f, clean_name)


def count_dir_files(d):
    """Count files recursively in a directory."""
    return sum(1 for f in d.rglob('*') if f.is_file())


def choose_group_quality(group):
    """Pick the default quality dir name for a duplicate group."""
    seen = {
        quality_dir.name
        for movie_dir in group
        for quality_dir in get_quality_subdirs(movie_dir)
    }
    for preferred in ('1080p', '2160p', '720p', '480p'):
        if preferred in seen:
            return preferred
    return '1080p'


def canonical_name_score(name):
    """Score a directory name for canonical duplicate selection."""
    score = 0
    score -= sum(1 for _ in re.finditer(r'\s{2,}', name))
    score -= name.count('_')
    score -= len(re.findall(r'\bMULTI\b', name, flags=re.I)) * 3
    score += len(re.findall(r'[A-Z]\.', name))
    score += len(re.findall(r"[A-Za-zÀ-ÿ]'[A-Za-zÀ-ÿ]", name))
    score += sum(1 for ch in name if ord(ch) > 127)
    return score


def get_preferred_group_name(group):
    """Choose the preferred canonical directory name for a duplicate group."""
    candidates = []
    for d in group:
        metadata = get_dir_metadata(d)
        dir_title, dir_year = parse_dir_name(d)
        year = metadata['year'] or dir_year

        if metadata['title'] and year:
            preferred_name = sanitize(f"{metadata['title']} ({year})")
            is_localized = (
                metadata['originaltitle']
                and normalize(metadata['title']) != normalize(metadata['originaltitle'])
            )
            candidates.append((
                preferred_name,
                2 if is_localized else 1,
                count_dir_files(d),
                canonical_name_score(preferred_name),
            ))

        if dir_year:
            fallback_name = sanitize(f"{dir_title} ({dir_year})")
            candidates.append((
                fallback_name,
                0,
                count_dir_files(d),
                canonical_name_score(fallback_name),
            ))

    if not candidates:
        return None

    return max(candidates, key=lambda item: item[1:])[0]


def choose_canonical_dir(group):
    """Choose the best directory to keep for a duplicate group."""
    preferred_name = get_preferred_group_name(group)
    if preferred_name:
        for d in group:
            if d.name == preferred_name:
                return d
    return max(
        group,
        key=lambda d: (count_dir_files(d), len(get_quality_subdirs(d)), canonical_name_score(d.name), -len(d.name))
    )


def iter_movie_files(d):
    """Iterate over all files contained in a movie directory."""
    return sorted((f for f in d.rglob('*') if f.is_file()), key=lambda p: (len(p.parts), str(p)))


def remove_empty_dirs(d, dry_run=False):
    """Remove empty directories from deepest to shallowest."""
    for child in sorted((p for p in d.rglob('*') if p.is_dir()), key=lambda p: len(p.parts), reverse=True):
        if not list(child.iterdir()):
            if dry_run:
                print(f"    rmdir: {child.relative_to(d.parent)}/")
            else:
                child.rmdir()
                print(f"    rmdir: {child.relative_to(d.parent)}/")
    if d.exists() and not list(d.iterdir()):
        if dry_run:
            print(f"    rmdir: {d.name}/")
        else:
            d.rmdir()
            print(f"    rmdir: {d.name}/")


def get_dir_nfo_candidates(d):
    """Return NFO files for a movie directory, preferring canonical ones first."""
    return sorted(
        (f for f in d.rglob('*.nfo') if f.is_file()),
        key=lambda f: (
            f.name != 'movie.nfo',
            f.stem != d.name,
            len(f.parts),
            str(f),
        ),
    )


def get_dir_metadata(d):
    """Return the best available NFO metadata for a movie directory."""
    for nfo_path in get_dir_nfo_candidates(d):
        metadata = parse_nfo_metadata(nfo_path)
        if metadata['title'] or metadata['tmdbid'] or metadata['imdbid']:
            return metadata
    return {
        'title': None,
        'year': None,
        'originaltitle': None,
        'sorttitle': None,
        'english_title': None,
        'tmdbid': None,
        'imdbid': None,
    }


def get_metadata_group_key(d):
    """Build a duplicate-group key from NFO metadata when possible."""
    metadata = get_dir_metadata(d)
    if metadata['tmdbid']:
        return ('tmdb', metadata['tmdbid'])
    if metadata['imdbid']:
        return ('imdb', metadata['imdbid'])

    meta_title = (
        metadata['originaltitle']
        or metadata['english_title']
        or metadata['sorttitle']
        or metadata['title']
    )
    if meta_title and metadata['year']:
        return ('metadata-title', normalize(meta_title), metadata['year'])
    return None


def parse_dir_name(d):
    """Extract title and year from a properly named directory."""
    match = re.match(r'^(.+?)\s*\((\d{4})\)$', d.name)
    if not match:
        return d.name, None
    return match.group(1).strip(), match.group(2)


def get_duplicate_group_keys(d):
    """Return all duplicate-matching keys for a movie directory."""
    metadata = get_dir_metadata(d)
    dir_title, dir_year = parse_dir_name(d)
    year = metadata['year'] or dir_year
    keys = set()

    if metadata['tmdbid']:
        keys.add(('tmdb', metadata['tmdbid']))
    if metadata['imdbid']:
        keys.add(('imdb', metadata['imdbid']))

    if dir_year:
        for alias in title_aliases(dir_title):
            keys.add(('title-year', alias, dir_year))

    for title in (
        metadata['title'],
        metadata['originaltitle'],
        metadata['sorttitle'],
        metadata['english_title'],
    ):
        if title and year:
            for alias in title_aliases(title):
                keys.add(('title-year', alias, year))

    return keys


def get_duplicate_groups(movies_dir):
    """Return duplicate groups using NFO identifiers and title aliases."""
    proper_dirs = [d for d in movies_dir.iterdir() if d.is_dir() and is_proper_dir(d)]
    parent = {d: d for d in proper_dirs}

    def find(d):
        while parent[d] != d:
            parent[d] = parent[parent[d]]
            d = parent[d]
        return d

    def union(left, right):
        root_left = find(left)
        root_right = find(right)
        if root_left != root_right:
            parent[root_right] = root_left

    key_to_dirs = defaultdict(list)
    for d in proper_dirs:
        for key in get_duplicate_group_keys(d):
            key_to_dirs[key].append(d)

    for dirs in key_to_dirs.values():
        if len(dirs) < 2:
            continue
        first = dirs[0]
        for other in dirs[1:]:
            union(first, other)

    grouped = defaultdict(list)
    for d in proper_dirs:
        grouped[find(d)].append(d)

    duplicate_groups = [
        sorted(group, key=lambda p: p.name)
        for group in grouped.values()
        if len(group) > 1
    ]
    return sorted(duplicate_groups, key=lambda group: group[0].name)


def tmdb_request(path, api_key, params):
    """Perform a TMDb API request and return parsed JSON."""
    query = dict(params)
    query['api_key'] = api_key
    url = f"{TMDB_API_BASE}{path}?{urllib.parse.urlencode(query)}"
    with urllib.request.urlopen(url, timeout=30) as response:
        return json.loads(response.read().decode('utf-8'))


def search_tmdb_movie(title, year, api_key, language):
    """Search TMDb for a movie candidate."""
    params = {'query': title, 'language': language}
    if year:
        params['year'] = year
    payload = tmdb_request('/search/movie', api_key, params)
    results = payload.get('results', [])
    if not results:
        return None
    if year:
        for result in results:
            release_date = result.get('release_date') or ''
            if release_date.startswith(str(year)):
                return result
    return results[0]


def get_tmdb_movie_details(movie_id, api_key, language):
    """Fetch detailed metadata and images for a TMDb movie."""
    return tmdb_request(
        f'/movie/{movie_id}',
        api_key,
        {'language': language, 'append_to_response': 'images,external_ids'}
    )


def search_tmdb_tv(title, year, api_key, language):
    """Search TMDb for a TV show candidate."""
    params = {'query': title, 'language': language}
    if year:
        params['first_air_date_year'] = year
    payload = tmdb_request('/search/tv', api_key, params)
    results = payload.get('results', [])
    if not results:
        return None
    if year:
        for result in results:
            first_air_date = result.get('first_air_date') or ''
            if first_air_date.startswith(str(year)):
                return result
    return results[0]


def get_tmdb_tv_details(tv_id, api_key, language):
    """Fetch detailed metadata and images for a TMDb TV show."""
    return tmdb_request(
        f'/tv/{tv_id}',
        api_key,
        {'language': language, 'append_to_response': 'images,external_ids'}
    )


def get_tmdb_episode_details(tv_id, season_number, episode_number, api_key, language):
    """Fetch TMDb metadata for a single TV episode."""
    return tmdb_request(
        f'/tv/{tv_id}/season/{season_number}/episode/{episode_number}',
        api_key,
        {'language': language},
    )


def write_tmdb_nfo(nfo_path, details, language):
    """Write a simple movie NFO from TMDb data."""
    movie = ET.Element('movie')
    fields = {
        'title': details.get('title'),
        'originaltitle': details.get('original_title'),
        'year': (details.get('release_date') or '')[:4] or None,
        'plot': details.get('overview'),
        'tagline': details.get('tagline'),
        'tmdbid': str(details.get('id')) if details.get('id') else None,
        'id': details.get('external_ids', {}).get('imdb_id'),
    }
    for key, value in fields.items():
        if value:
            ET.SubElement(movie, key).text = value

    tree = ET.ElementTree(movie)
    nfo_path.parent.mkdir(parents=True, exist_ok=True)
    tree.write(nfo_path, encoding='utf-8', xml_declaration=True)


def write_tmdb_tvshow_nfo(nfo_path, details):
    """Write a simple TV show NFO from TMDb data."""
    tvshow = ET.Element('tvshow')
    fields = {
        'title': details.get('name'),
        'originaltitle': details.get('original_name'),
        'year': (details.get('first_air_date') or '')[:4] or None,
        'plot': details.get('overview'),
        'tmdbid': str(details.get('id')) if details.get('id') else None,
        'id': details.get('external_ids', {}).get('imdb_id'),
    }
    for key, value in fields.items():
        if value:
            ET.SubElement(tvshow, key).text = value

    tree = ET.ElementTree(tvshow)
    nfo_path.parent.mkdir(parents=True, exist_ok=True)
    tree.write(nfo_path, encoding='utf-8', xml_declaration=True)


def write_tmdb_episode_nfo(nfo_path, series_details, episode_details, season_number, episode_number):
    """Write a simple episode NFO using TMDb TV metadata."""
    episode = ET.Element('episodedetails')
    fields = {
        'title': episode_details.get('name') or f"Episode {episode_number:02d}",
        'showtitle': series_details.get('name'),
        'season': str(season_number),
        'episode': str(episode_number),
        'plot': episode_details.get('overview'),
        'aired': episode_details.get('air_date'),
        'tmdbid': str(episode_details.get('id')) if episode_details.get('id') else None,
    }
    for key, value in fields.items():
        if value:
            ET.SubElement(episode, key).text = value

    tree = ET.ElementTree(episode)
    nfo_path.parent.mkdir(parents=True, exist_ok=True)
    tree.write(nfo_path, encoding='utf-8', xml_declaration=True)


def download_tmdb_asset(url, destination, dry_run=False):
    """Download a TMDb asset to a destination path."""
    if not url:
        return False
    if dry_run:
        print(f"    FETCH {destination.name}")
        return True
    destination.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, timeout=30) as response, destination.open('wb') as handle:
        shutil.copyfileobj(response, handle)
    return True


def pick_tmdb_logo(details, language):
    """Pick the best TMDb logo path for the requested language."""
    logos = details.get('images', {}).get('logos', [])
    if not logos:
        return None

    preferred_languages = []
    if language and '-' in language:
        preferred_languages.append(language.split('-', 1)[0])
    if language:
        preferred_languages.append(language)
    preferred_languages.extend(['fr', 'en', None])

    for preferred in preferred_languages:
        for logo in logos:
            if logo.get('iso_639_1') == preferred:
                return logo.get('file_path')
    return logos[0].get('file_path')


def fetch_tmdb_assets(details, target_dir, dry_run=False, language='fr-FR'):
    """Download common artwork assets from TMDb."""
    assets = []
    if details.get('poster_path'):
        assets.append((f"{TMDB_IMAGE_BASE}{details['poster_path']}", target_dir / 'poster.jpg'))
    if details.get('backdrop_path'):
        assets.append((f"{TMDB_IMAGE_BASE}{details['backdrop_path']}", target_dir / 'fanart.jpg'))
    logo_path = pick_tmdb_logo(details, language)
    if logo_path:
        assets.append((f"{TMDB_IMAGE_BASE}{logo_path}", target_dir / 'logo.png'))

    for url, destination in assets:
        download_tmdb_asset(url, destination, dry_run=dry_run)


def find_incoming_related_files(video_path):
    """Find files related to an incoming video by common stem."""
    stem = video_path.stem
    parent = video_path.parent
    return sorted(
        [
            f for f in parent.iterdir()
            if f.is_file() and (f == video_path or f.stem == stem or f.name.startswith(stem + '.'))
        ],
        key=lambda p: p.name,
    )


def process_incoming(incoming_dir, movies_dir, dry_run, api_key, language, fetch_metadata):
    """Process raw incoming video files via TMDb and build the target structure."""
    if not api_key:
        raise ValueError('TMDb API key required for --incoming. Use --tmdb-api-key or TMDB_API_KEY.')

    print("=" * 60)
    print("Incoming processing\n")

    moved = 0
    incoming_videos = sorted(
        f for f in incoming_dir.rglob('*')
        if f.is_file() and f.suffix.lower() in VIDEO_EXTENSIONS
    )

    for video_path in incoming_videos:
        title, year = parse_filename(video_path.name)
        if not title:
            title, year = parse_filename(video_path.parent.name)
        if not title:
            print(f"[SKIP] {video_path.name} (unable to parse title/year)")
            continue

        candidate = search_tmdb_movie(title, year, api_key, language)
        if not candidate:
            print(f"[SKIP] {video_path.name} (no TMDb match)")
            continue

        details = get_tmdb_movie_details(candidate['id'], api_key, language)
        release_year = (details.get('release_date') or '')[:4] or year
        fr_title = details.get('title') or title
        clean_name = sanitize(f"{fr_title} ({release_year})") if release_year else sanitize(fr_title)
        quality = detect_quality(video_path.name) or '1080p'
        target_dir = movies_dir / clean_name / quality

        print(f"[INCOMING] {video_path.name} -> {target_dir.relative_to(movies_dir)}/")
        if not dry_run:
            target_dir.mkdir(parents=True, exist_ok=True)

        for related in find_incoming_related_files(video_path):
            new_name = get_consolidated_filename(related, clean_name)
            safe_move(related, target_dir / new_name, dry_run)
            moved += 1

        if fetch_metadata:
            nfo_path = target_dir / f"{clean_name}.nfo"
            if dry_run:
                print(f"    FETCH {nfo_path.name}")
            else:
                write_tmdb_nfo(nfo_path, details, language)
            fetch_tmdb_assets(details, target_dir, dry_run=dry_run, language=language)
        print()

    return moved


def safe_move(src, dst, dry_run=False):
    """Move file, handling conflicts."""
    if src == dst:
        return dst
    if dst.exists():
        stem = dst.stem
        ext = dst.suffix
        i = 2
        while dst.exists():
            dst = dst.parent / f"{stem} ({i}){ext}"
            i += 1

    if dry_run:
        print(f"    {src.name} -> {dst.parent.name}/{dst.name}")
        return dst
    else:
        try:
            shutil.move(str(src), str(dst))
            print(f"    OK: {src.name} -> {dst.parent.name}/{dst.name}")
            return dst
        except Exception as e:
            print(f"    [FAIL] {src.name}: {e}")
            LOGGER.error("Move failed for %s -> %s: %s", src, dst, e)
            return None


def get_release_year(details, field):
    """Extract the year portion from a TMDb date field."""
    value = details.get(field) or ''
    return value[:4] or None


def is_anime_details(details):
    """Heuristic to route Japanese animation into the anime library."""
    genre_ids = {genre.get('id') for genre in details.get('genres', []) if isinstance(genre, dict)}
    countries = set(details.get('origin_country', []) or [])
    countries.update(
        country.get('iso_3166_1')
        for country in details.get('production_countries', [])
        if isinstance(country, dict)
    )
    original_language = (details.get('original_language') or '').lower()
    return ANIMATION_GENRE_ID in genre_ids and (original_language == 'ja' or 'JP' in countries)


def pick_route_root(routes, routing, media_type, details):
    """Select the destination library root for a media item."""
    if is_anime_details(details):
        if media_type == 'tv':
            if routing.anime_series_to == 'series':
                return routes.series, 'series'
            return routes.anime, 'anime'
        if routing.anime_movies_to == 'movies':
            return routes.movies, 'movie'
        return routes.anime, 'anime'
    if media_type == 'tv':
        return routes.series, 'series'
    return routes.movies, 'movie'


def display_relative(path, root):
    """Return a user-friendly relative path when possible."""
    try:
        return path.relative_to(root)
    except ValueError:
        return path


def build_episode_code(season_number, episodes):
    """Build a Kodi-friendly episode code."""
    base = f"S{season_number:02d}E{episodes[0]:02d}"
    if len(episodes) == 1:
        return base
    return f"{base}-E{episodes[-1]:02d}"


def get_episode_target_name(path, series_name, season_number, episodes):
    """Build the destination filename for an imported TV/anime episode asset."""
    episode_code = build_episode_code(season_number, episodes)
    ext = path.suffix.lower()
    if ext in ('.srt', '.sub', '.idx', '.ass', '.ssa', '.mkv', '.mp4', '.avi', '.wmv', '.m4v', '.mov'):
        return f"{series_name} - {episode_code}{path.suffix}"
    if ext == '.nfo':
        return f"{series_name} - {episode_code}.nfo"
    if ext in ('.jpg', '.png', '.svg'):
        return get_art_name(path)
    return path.name


def import_movie_item(item, config, dry_run, summary):
    """Import one incoming movie file into the configured library."""
    title, year = parse_filename(item.video_path.name)
    if not title:
        title, year = parse_filename(item.video_path.parent.name)
    if not title:
        summary.skipped_items += 1
        detail = f"[SKIP] {item.video_path.name} (unable to parse title/year)"
        summary.skipped_details.append(detail)
        log_message(detail, 'warning')
        return

    candidate = search_tmdb_movie(title, year, config.tmdb_api_key, config.tmdb_language)
    if not candidate:
        summary.skipped_items += 1
        detail = f"[SKIP] {item.video_path.name} (no TMDb movie match)"
        summary.skipped_details.append(detail)
        log_message(detail, 'warning')
        return

    details = get_tmdb_movie_details(candidate['id'], config.tmdb_api_key, config.tmdb_language)
    route_root, route_kind = pick_route_root(config.routes, config.routing, 'movie', details)
    release_year = get_release_year(details, 'release_date') or year
    localized_title = details.get('title') or title
    clean_name = sanitize(f"{localized_title} ({release_year})") if release_year else sanitize(localized_title)
    quality = detect_quality(item.video_path.name) or '1080p'
    target_dir = route_root / clean_name / quality

    log_message(f"[IMPORT:{route_kind.upper()}] {item.video_path.name} -> {display_relative(target_dir, route_root)}/")
    if not dry_run:
        target_dir.mkdir(parents=True, exist_ok=True)

    moved_now = 0
    for related in item.related_files:
        new_name = get_consolidated_filename(related, clean_name)
        moved_path = safe_move(related, target_dir / new_name, dry_run)
        if moved_path is not None:
            moved_now += 1

    if config.fetch_metadata:
        nfo_path = target_dir / f"{clean_name}.nfo"
        if dry_run:
            log_message(f"    FETCH {nfo_path.name}")
        else:
            write_tmdb_nfo(nfo_path, details, config.tmdb_language)
        fetch_tmdb_assets(details, target_dir, dry_run=dry_run, language=config.tmdb_language)

    summary.imported_items += 1
    summary.moved_files += moved_now
    if route_kind == 'anime':
        summary.imported_anime += 1
    else:
        summary.imported_movies += 1
    summary.imported_details.append(f"{item.video_path.name} -> {target_dir}")


def import_tv_item(item, config, dry_run, summary):
    """Import one incoming TV/anime episode into the configured library."""
    title, season_number, episodes = parse_episode_filename(
        item.video_path.name, item.video_path.parent.name
    )
    if not title:
        summary.skipped_items += 1
        detail = f"[SKIP] {item.video_path.name} (unable to parse series/episode pattern)"
        summary.skipped_details.append(detail)
        log_message(detail, 'warning')
        return

    year_hint = None
    parent_title, parent_year = parse_filename(item.video_path.parent.name)
    if parent_title:
        year_hint = parent_year

    inline_year = re.search(r'\((\d{4})\)\s*$', title)
    if inline_year:
        year_hint = year_hint or inline_year.group(1)
        title = title[:inline_year.start()].strip(' -.')

    if not year_hint:
        # Season-less releases often carry the year on the file itself, with or
        # without parentheses: "Show.1982.TV.Series.E01" / "Show.(2005).S01E01".
        file_year = re.search(
            r'(?:^|[.\s_-])\(?((?:19|20)\d{2})\)?(?=[.\s_-])', item.video_path.stem
        )
        year_hint = file_year.group(1) if file_year else None

    candidate = search_tmdb_tv(title, year_hint, config.tmdb_api_key, config.tmdb_language)
    if not candidate:
        summary.skipped_items += 1
        detail = f"[SKIP] {item.video_path.name} (no TMDb TV match)"
        summary.skipped_details.append(detail)
        log_message(detail, 'warning')
        return

    details = get_tmdb_tv_details(candidate['id'], config.tmdb_api_key, config.tmdb_language)
    route_root, route_kind = pick_route_root(config.routes, config.routing, 'tv', details)
    first_year = get_release_year(details, 'first_air_date') or year_hint
    series_name = details.get('name') or title
    clean_series_name = sanitize(f"{series_name} ({first_year})") if first_year else sanitize(series_name)
    show_dir = route_root / clean_series_name
    season_dir = show_dir / f"Season {season_number:02d}"
    log_message(f"[IMPORT:{route_kind.upper()}] {item.video_path.name} -> {display_relative(season_dir, route_root)}/")
    if not dry_run:
        season_dir.mkdir(parents=True, exist_ok=True)

    moved_now = 0
    for related in item.related_files:
        destination_parent = show_dir if related.suffix.lower() in ('.jpg', '.png', '.svg') else season_dir
        new_name = get_episode_target_name(related, series_name, season_number, episodes)
        moved_path = safe_move(related, destination_parent / new_name, dry_run)
        if moved_path is not None:
            moved_now += 1

    if config.fetch_metadata:
        show_nfo_path = show_dir / 'tvshow.nfo'
        if dry_run:
            log_message(f"    FETCH {show_nfo_path.name}")
        else:
            write_tmdb_tvshow_nfo(show_nfo_path, details)
        fetch_tmdb_assets(details, show_dir, dry_run=dry_run, language=config.tmdb_language)

        episode_details = get_tmdb_episode_details(
            details['id'],
            season_number,
            episodes[0],
            config.tmdb_api_key,
            config.tmdb_language,
        )
        episode_nfo_name = get_episode_target_name(Path(f"episode{item.video_path.suffix}"), series_name, season_number, episodes)
        episode_nfo_path = season_dir / Path(episode_nfo_name).with_suffix('.nfo')
        if dry_run:
            log_message(f"    FETCH {episode_nfo_path.name}")
        else:
            write_tmdb_episode_nfo(episode_nfo_path, details, episode_details, season_number, episodes[0])

    summary.imported_items += 1
    summary.moved_files += moved_now
    if route_kind == 'anime':
        summary.imported_anime += 1
    else:
        summary.imported_series += 1
    summary.imported_details.append(f"{item.video_path.name} -> {season_dir}")


def prune_empty_directories(root_dir, dry_run=False):
    """Remove empty directories left behind in the inbox."""
    removed = 0
    directories = sorted((d for d in root_dir.rglob('*') if d.is_dir()), key=lambda path: len(path.parts), reverse=True)
    for directory in directories:
        if any(directory.iterdir()):
            continue
        if dry_run:
            log_message(f"[DRY] rmdir {display_relative(directory, root_dir)}/")
        else:
            directory.rmdir()
            LOGGER.info("Removed empty directory %s", directory)
        removed += 1
    return removed


def format_import_summary(summary, inbox_dir, dry_run=False):
    """Render a human-readable summary for logs and Telegram."""
    lines = [
        f"{'DRY-RUN ' if dry_run else ''}Inbox summary for {inbox_dir}",
        f"- detected items: {summary.detected_items}",
        f"- imported items: {summary.imported_items}",
        f"- imported movies: {summary.imported_movies}",
        f"- imported series: {summary.imported_series}",
        f"- imported anime: {summary.imported_anime}",
        f"- moved files: {summary.moved_files}",
        f"- skipped items: {summary.skipped_items}",
        f"- errors: {summary.errors}",
    ]
    if summary.skipped_details:
        lines.append('')
        lines.append('Skipped:')
        lines.extend(f"  {detail}" for detail in summary.skipped_details[:20])
    if summary.imported_details:
        lines.append('')
        lines.append('Imported:')
        lines.extend(f"  {detail}" for detail in summary.imported_details[:20])
    return '\n'.join(lines)


def get_post_import_roots(config):
    """Return unique destination roots that should be reconciled after inbox import."""
    roots = [config.routes.movies]
    if config.routing.anime_movies_to == 'anime':
        roots.append(config.routes.anime)

    unique_roots = []
    seen = set()
    for root in roots:
        key = str(root)
        if key in seen:
            continue
        seen.add(key)
        unique_roots.append(root)
    return unique_roots


def run_post_import_reconciliation(config, dry_run=False):
    """Run safe duplicate and quality reconciliation on destination movie libraries."""
    total_moved = 0
    for root in get_post_import_roots(config):
        log_message(f"[POST] Reconcile destination library: {root}")
        total_moved += phase_quality_dirs(root, dry_run)
        total_moved += phase_duplicate_dirs(root, dry_run)
        phase_cleanup(root, dry_run)
    return total_moved


def process_automation_inbox(config, dry_run=False):
    """Process the configured inbox in a cron-friendly, lock-protected way."""
    lock_path = config.inbox.lock_file or (config.inbox.path / '.reorganize_movies.lock')
    summary = ImportSummary()

    with exclusive_lock(lock_path):
        for route_root in (config.routes.movies, config.routes.series, config.routes.anime):
            if not dry_run:
                route_root.mkdir(parents=True, exist_ok=True)

        items = gather_incoming_items(config.inbox.path, config.inbox.stability_seconds)
        summary.detected_items = len(items)
        if not items:
            log_message(f"[SCAN] No stable media detected in {config.inbox.path}")
            return summary

        detection_message = summarize_incoming_items(items, config.inbox.path)
        log_message(detection_message)
        send_telegram_message(config.telegram, detection_message)

        if not config.tmdb_api_key:
            raise ValueError('TMDb API key required for inbox automation. Set it in config or TMDB_API_KEY.')

        for item in items:
            try:
                title, season_number, episodes = parse_episode_filename(
                    item.video_path.name, item.video_path.parent.name
                )
                if title and season_number and episodes:
                    import_tv_item(item, config, dry_run, summary)
                else:
                    import_movie_item(item, config, dry_run, summary)
            except Exception as exc:
                summary.errors += 1
                detail = f"[ERROR] {item.video_path.name}: {exc}"
                summary.skipped_details.append(detail)
                LOGGER.exception("Failed to process incoming item %s", item.video_path)

        if summary.imported_items:
            run_post_import_reconciliation(config, dry_run=dry_run)
        prune_empty_directories(config.inbox.path, dry_run=dry_run)
        summary_message = format_import_summary(summary, config.inbox.path, dry_run=dry_run)
        log_message(summary_message)
        send_telegram_message(config.telegram, summary_message)
        return summary


def phase_nfo(movies_dir, dry_run):
    """Phase 1: Process all NFO files."""
    nfo_files = sorted(movies_dir.rglob("*.nfo"))
    print(f"Phase 1: {len(nfo_files)} NFO files\n")

    movies = defaultdict(list)
    handled_files = set()

    for nfo_path in nfo_files:
        title, year = parse_nfo(nfo_path)
        if not title:
            continue

        clean_name = sanitize(f"{title} ({year})") if year else sanitize(title)

        related = find_related_files(nfo_path)
        video_files = [f for f in related if f.suffix in VIDEO_EXTENSIONS]
        quality = detect_quality(video_files[0].name) if video_files else detect_quality(nfo_path.name)

        movies[clean_name].append({
            'nfo': nfo_path, 'related': related,
            'quality': quality, 'source_dir': nfo_path.parent,
        })

    moved = 0
    for clean_name, versions in sorted(movies.items()):
        is_multi = len(versions) > 1
        target_dir = movies_dir / clean_name

        if is_multi:
            print(f"[MULTI] {clean_name} ({len(versions)} versions)")

        for v in versions:
            related = v['related']
            quality = v['quality'] or '1080p'
            source_dir = v['source_dir']
            final_dir = (target_dir / quality) if is_multi else target_dir

            if source_dir == final_dir:
                needs_work = any(get_new_filename(f, clean_name) != f.name for f in related)
                if not needs_work:
                    for f in related:
                        handled_files.add(f)
                    continue

            if is_multi:
                print(f"  [{quality}]")
            else:
                print(f"[MOVE] {clean_name}")

            if not dry_run:
                final_dir.mkdir(parents=True, exist_ok=True)

            for f in sorted(related):
                handled_files.add(f)
                new_name = get_new_filename(f, clean_name)
                safe_move(f, final_dir / new_name, dry_run)
                moved += 1

        if is_multi or len(versions) == 1:
            print()

    return handled_files, moved


def phase_orphans(movies_dir, handled_files, dry_run):
    """Phase 2: Process orphan files (no NFO)."""
    print("=" * 60)
    print("Phase 2: Orphan files (no NFO)\n")

    orphan_files = []
    for f in movies_dir.iterdir():
        if f.is_file() and f not in handled_files and not is_script_file(f):
            orphan_files.append(f)
    for d in movies_dir.iterdir():
        if d.is_dir():
            for f in d.iterdir():
                if f.is_file() and f not in handled_files and not is_script_file(f):
                    orphan_files.append(f)

    groups = defaultdict(list)
    unparseable = []
    for f in orphan_files:
        title, year = parse_filename(f.name)
        if title and year:
            groups[(title, year)].append(f)
        else:
            unparseable.append(f)

    moved = 0
    for (title, year), files in sorted(groups.items()):
        clean_name = sanitize(f"{title} ({year})")
        target_dir = movies_dir / clean_name

        video_files = [f for f in files if f.suffix in VIDEO_EXTENSIONS]
        qualities = {detect_quality(vf.name) for vf in video_files}

        if len(qualities) > 1:
            print(f"[ORPHAN-MULTI] {clean_name}")
            by_quality = defaultdict(list)
            for f in files:
                by_quality[detect_quality(f.name) or '1080p'].append(f)
            for q, qfiles in sorted(by_quality.items()):
                final_dir = target_dir / q
                if not dry_run:
                    final_dir.mkdir(parents=True, exist_ok=True)
                print(f"  [{q}]")
                for f in sorted(qfiles):
                    handled_files.add(f)
                    safe_move(f, final_dir / get_new_filename(f, clean_name), dry_run)
                    moved += 1
        else:
            print(f"[ORPHAN] {clean_name}")
            if not dry_run:
                target_dir.mkdir(parents=True, exist_ok=True)
            for f in sorted(files):
                handled_files.add(f)
                safe_move(f, target_dir / get_new_filename(f, clean_name), dry_run)
                moved += 1
        print()

    return handled_files, moved, unparseable


def phase_old_dirs(movies_dir, dry_run):
    """Phase 3: Handle old-style directories."""
    print("=" * 60)
    print("Phase 3: Old-style directories\n")

    proper_dirs = [d for d in movies_dir.iterdir() if d.is_dir() and is_proper_dir(d)]
    old_dirs = [d for d in movies_dir.iterdir() if d.is_dir() and not is_proper_dir(d)]

    moved = 0

    for d in sorted(old_dirs):
        files = [f for f in d.iterdir() if f.is_file()]
        if not files:
            continue

        has_video = any(f.suffix in VIDEO_EXTENSIONS for f in files)
        has_nfo = any(f.suffix == '.nfo' for f in files)
        is_art_only = all(f.suffix in ('.jpg', '.png', '.svg') for f in files)

        # Dirs with NFO/video: parse and move
        if has_nfo or has_video:
            title, year = None, None
            nfos = [f for f in files if f.suffix == '.nfo']
            for nfo in nfos:
                title, year = parse_nfo(nfo)
                if title and year:
                    break
            if not title or not year:
                # Try movie.nfo
                movie_nfo = d / 'movie.nfo'
                if movie_nfo.exists():
                    title, year = parse_nfo(movie_nfo)
            if not title:
                videos = [f for f in files if f.suffix in VIDEO_EXTENSIONS]
                if videos:
                    title, year = parse_filename(videos[0].name)
            if not title:
                title, year = parse_filename(d.name)

            if title:
                clean_name = sanitize(f"{title} ({year})") if year else sanitize(title)
                target_dir = movies_dir / clean_name

                if target_dir != d:
                    if target_dir.exists():
                        quality = detect_quality(d.name) or '1080p'
                        final_dir = target_dir / quality
                    else:
                        final_dir = target_dir

                    print(f"[DIR-FIX] {d.name}/ -> {final_dir.relative_to(movies_dir)}/")
                    if not dry_run:
                        final_dir.mkdir(parents=True, exist_ok=True)

                    for f in sorted(files):
                        new_name = get_new_filename(f, clean_name)
                        safe_move(f, final_dir / new_name, dry_run)
                        moved += 1

                    if not dry_run:
                        try:
                            remaining = list(d.iterdir())
                            if not remaining:
                                d.rmdir()
                                print(f"    rmdir: {d.name}/")
                            else:
                                for r in remaining:
                                    if r.is_file():
                                        r.unlink()
                                if not list(d.iterdir()):
                                    d.rmdir()
                                    print(f"    rmdir: {d.name}/ (cleaned leftovers)")
                        except Exception:
                            pass
                    print()
                continue

        # Art-only dirs: fuzzy match
        if is_art_only:
            match, score = fuzzy_match_dir(d.name, proper_dirs)
            if match:
                needs_art = any(
                    not dir_has_art(match, get_art_name(f).split('.')[0])
                    for f in files
                )
                if not needs_art:
                    if not dry_run:
                        for f in files:
                            f.unlink()
                        try:
                            d.rmdir()
                        except Exception:
                            pass
                    print(f"[DUP] {d.name}/ (artwork in {match.name}/)")
                else:
                    print(f"[ART] {d.name}/ -> {match.name}/")
                    for f in sorted(files):
                        new_name = get_art_name(f)
                        safe_move(f, match / new_name, dry_run)
                        moved += 1
                    if not dry_run:
                        try:
                            if not list(d.iterdir()):
                                d.rmdir()
                                print(f"    rmdir: {d.name}/")
                        except Exception:
                            pass
                print()

    return moved


def phase_quality_dirs(movies_dir, dry_run):
    """Phase 4: Ensure quality-based movies have all files inside quality dirs."""
    print("=" * 60)
    print("Phase 4: Consolidate quality directories\n")

    moved = 0
    for movie_dir in sorted(d for d in movies_dir.iterdir() if d.is_dir() and is_proper_dir(d)):
        quality_dirs = get_quality_subdirs(movie_dir)
        if not quality_dirs:
            continue

        root_files = get_root_media_files(movie_dir)
        if not root_files:
            continue

        print(f"[SPLIT] {movie_dir.name}")
        for root_file in sorted(root_files):
            target_dir = pick_quality_dir(root_file, quality_dirs)
            new_name = get_consolidated_filename(root_file, movie_dir.name)
            safe_move(root_file, target_dir / new_name, dry_run)
            moved += 1
        print()

    return moved


def phase_duplicate_dirs(movies_dir, dry_run):
    """Phase 5: Merge duplicate properly named movie directories."""
    print("=" * 60)
    print("Phase 5: Merge duplicate movie directories\n")

    moved = 0
    duplicate_groups = get_duplicate_groups(movies_dir)
    for group in duplicate_groups:
        preferred_name = get_preferred_group_name(group)
        if preferred_name:
            existing_target = next((d for d in group if d.name == preferred_name), None)
            target_dir = existing_target or (movies_dir / preferred_name)
        else:
            target_dir = choose_canonical_dir(group)
        source_dirs = [d for d in group if d != target_dir]
        group_quality = choose_group_quality(group)

        print(f"[MERGE] {target_dir.name} <= {', '.join(d.name for d in source_dirs)}")
        if not dry_run:
            target_dir.mkdir(parents=True, exist_ok=True)

        for source_dir in source_dirs:
            for src in iter_movie_files(source_dir):
                relative = src.relative_to(source_dir)
                parts = relative.parts
                if parts and parts[0] in QUALITY_DIR_NAMES:
                    dst = target_dir.joinpath(*parts)
                else:
                    target_quality_dirs = get_quality_subdirs(target_dir)
                    if target_quality_dirs:
                        quality_dir = pick_quality_dir(src, target_quality_dirs)
                        new_name = get_consolidated_filename(src, target_dir.name)
                        dst = quality_dir / new_name
                    else:
                        new_name = get_consolidated_filename(src, target_dir.name)
                        dst = target_dir / new_name

                if not dry_run:
                    dst.parent.mkdir(parents=True, exist_ok=True)
                safe_move(src, dst, dry_run)
                moved += 1

            target_quality_dirs = get_quality_subdirs(target_dir)
            if not target_quality_dirs and any(parts.name in QUALITY_DIR_NAMES for parts in source_dir.iterdir() if parts.is_dir()):
                quality_dir = target_dir / group_quality
                if not dry_run:
                    quality_dir.mkdir(parents=True, exist_ok=True)

            if source_dir.exists():
                remove_empty_dirs(source_dir, dry_run)
        print()

    return moved


def phase_cleanup(movies_dir, dry_run):
    """Phase 6: Clean empty dirs and fix unknown/ subdirs."""
    print("=" * 60)
    print("Phase 6: Cleanup\n")

    # Fix unknown/ subdirs: merge into parent or rename to 1080p
    unknown_dirs = sorted(movies_dir.rglob('unknown'))
    for u in unknown_dirs:
        if not u.is_dir():
            continue
        parent = u.parent
        siblings = [d for d in parent.iterdir() if d.is_dir() and d.name != 'unknown']

        if not siblings:
            # No quality siblings: move files up
            print(f"  [FIX] {parent.name}/unknown/ -> move to parent")
            if not dry_run:
                for f in u.iterdir():
                    if f.is_file():
                        dst = parent / f.name
                        if not dst.exists():
                            shutil.move(str(f), str(dst))
                try:
                    if not list(u.iterdir()):
                        u.rmdir()
                except Exception:
                    pass
        else:
            # Has quality siblings: rename to 1080p
            target = parent / '1080p'
            print(f"  [FIX] {parent.name}/unknown/ -> 1080p/")
            if not dry_run:
                if target.exists():
                    for f in u.iterdir():
                        if f.is_file():
                            dst = target / f.name
                            if not dst.exists():
                                f.rename(dst)
                    try:
                        if not list(u.iterdir()):
                            u.rmdir()
                    except Exception:
                        pass
                else:
                    try:
                        u.rename(target)
                    except Exception:
                        pass

    # Clean empty dirs
    for _ in range(5):
        for d in sorted(movies_dir.rglob("*")):
            if d.is_dir():
                try:
                    if not list(d.iterdir()):
                        if not dry_run:
                            d.rmdir()
                        print(f"  rmdir: {d.relative_to(movies_dir)}/")
                except Exception:
                    pass


def phase_report(movies_dir):
    """Phase 7: Report remaining issues."""
    print("\n" + "=" * 60)
    print("REMAINING ISSUES:")
    print("=" * 60)

    remaining_dirs = []
    for d in sorted(movies_dir.iterdir()):
        if d.is_dir() and not is_proper_dir(d):
            files = [f for f in d.rglob('*') if f.is_file()]
            if files:
                remaining_dirs.append(d)
                has_mkv = any(f.suffix in VIDEO_EXTENSIONS for f in files)
                tag = "FILM" if has_mkv else "ART"
                print(f"  [{tag}] {d.name}/ ({len(files)} files)")

    split_layouts = []
    for d in sorted(movies_dir.iterdir()):
        if not d.is_dir() or not is_proper_dir(d):
            continue
        quality_dirs = get_quality_subdirs(d)
        if not quality_dirs:
            continue
        root_files = get_root_media_files(d)
        if root_files:
            split_layouts.append((d, root_files))
            print(f"  [SPLIT] {d.name}/ ({len(root_files)} root files outside quality dirs)")

    duplicate_groups = get_duplicate_groups(movies_dir)
    for group in duplicate_groups:
        print(f"  [DUP] {' | '.join(d.name for d in group)}")

    remaining_loose = [f for f in sorted(movies_dir.iterdir())
                       if f.is_file() and not is_script_file(f)]
    if remaining_loose:
        print()
        for f in remaining_loose:
            tag = "FILM" if f.suffix in VIDEO_EXTENSIONS else "FILE"
            print(f"  [{tag}] {f.name}")

    if not remaining_dirs and not remaining_loose and not split_layouts and not duplicate_groups:
        print("  (none)")

    # Summary
    proper = sum(1 for d in movies_dir.iterdir() if d.is_dir() and is_proper_dir(d))
    print(f"\n  Properly organized: {proper} movies")
    print(f"  Unresolved dirs:    {len(remaining_dirs) + len(split_layouts) + len(duplicate_groups)}")
    print(f"  Loose files:        {len(remaining_loose)}")


def phase_stats(movies_dir):
    """Show statistics: total films, multi-quality, per-quality breakdown."""
    print(f"=== MOVIE STATISTICS ===")
    print(f"Directory: {movies_dir}\n")

    proper_dirs = sorted(
        d for d in movies_dir.iterdir() if d.is_dir() and is_proper_dir(d)
    )

    quality_counts = defaultdict(int)
    multi_quality = []

    for d in proper_dirs:
        subdirs = [s for s in d.iterdir() if s.is_dir() and s.name in
                   ('2160p', '1080p', '720p', '480p')]

        if subdirs:
            qualities = sorted(s.name for s in subdirs)
            for q in qualities:
                quality_counts[q] += 1
            if len(qualities) > 1:
                multi_quality.append((d.name, qualities))
        else:
            # Single version: detect quality from video file
            videos = [f for f in d.iterdir() if f.suffix in VIDEO_EXTENSIONS]
            if videos:
                q = detect_quality(videos[0].name) or '1080p'
            else:
                q = '1080p'
            quality_counts[q] += 1

    print(f"Total films: {len(proper_dirs)}\n")

    # Quality breakdown
    quality_order = ['2160p', '1080p', '720p', '480p']
    print("Films par qualite:")
    for q in quality_order:
        if q in quality_counts:
            print(f"  {q}: {quality_counts[q]}")
    for q in sorted(quality_counts):
        if q not in quality_order:
            print(f"  {q}: {quality_counts[q]}")

    # Multi-quality films
    print(f"\nFilms en multi-qualite: {len(multi_quality)}")
    if multi_quality:
        for name, qualities in multi_quality:
            print(f"  {name}: {', '.join(qualities)}")


def main():
    parser = argparse.ArgumentParser(
        description="Reorganize a movies directory into a clean Jellyfin/Plex/Kodi structure."
    )
    parser.add_argument('directory', nargs='?', default='.',
                        help='Path to movies directory (default: current directory)')
    parser.add_argument('--config',
                        help='Path to a TOML config file for automated inbox processing')
    parser.add_argument('--scan-inbox', action='store_true',
                        help='Process the configured inbox once (cron-friendly)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Show what would be done without moving anything')
    parser.add_argument('--stats', action='store_true',
                        help='Show statistics: total films, multi-quality, per-quality counts')
    parser.add_argument('--incoming',
                        help='Path to a directory of newly downloaded files to identify and import')
    parser.add_argument('--tmdb-api-key',
                        help='TMDb API key (defaults to TMDB_API_KEY environment variable)')
    parser.add_argument('--tmdb-language', default='fr-FR',
                        help='Preferred TMDb language for title and metadata (default: fr-FR)')
    parser.add_argument('--fetch-metadata', action='store_true',
                        help='Download NFO and artwork from TMDb while processing --incoming')

    args = parser.parse_args()

    if args.scan_inbox:
        if not args.config:
            print("Error: --scan-inbox requires --config", file=sys.stderr)
            sys.exit(1)
        config_path = Path(args.config).expanduser().resolve()
        if not config_path.is_file():
            print(f"Error: {config_path} is not a file", file=sys.stderr)
            sys.exit(1)
        try:
            config = load_automation_config(config_path)
            configure_logging(config.logging)
            process_automation_inbox(config, dry_run=args.dry_run)
        except Exception as exc:
            LOGGER.exception("Automated inbox scan failed")
            if 'config' in locals():
                send_telegram_message(config.telegram, f"[ERROR] Automated inbox scan failed: {exc}")
            print(f"Error: {exc}", file=sys.stderr)
            sys.exit(1)
        return

    movies_dir = Path(args.directory).resolve()

    if not movies_dir.is_dir():
        print(f"Error: {movies_dir} is not a directory", file=sys.stderr)
        sys.exit(1)

    if args.stats:
        phase_stats(movies_dir)
        return

    moved0 = 0
    if args.incoming:
        incoming_dir = Path(args.incoming).resolve()
        if not incoming_dir.is_dir():
            print(f"Error: {incoming_dir} is not a directory", file=sys.stderr)
            sys.exit(1)
        api_key = args.tmdb_api_key or os.environ.get('TMDB_API_KEY')
        try:
            moved0 = process_incoming(
                incoming_dir,
                movies_dir,
                args.dry_run,
                api_key,
                args.tmdb_language,
                args.fetch_metadata,
            )
        except Exception as exc:
            print(f"Error: {exc}", file=sys.stderr)
            sys.exit(1)

    mode = "DRY-RUN" if args.dry_run else "EXECUTE"
    print(f"=== MOVIE REORGANIZATION ({mode}) ===")
    print(f"Directory: {movies_dir}\n")

    handled, moved1 = phase_nfo(movies_dir, args.dry_run)
    handled, moved2, _ = phase_orphans(movies_dir, handled, args.dry_run)
    moved3 = phase_old_dirs(movies_dir, args.dry_run)
    moved4 = phase_quality_dirs(movies_dir, args.dry_run)
    moved5 = phase_duplicate_dirs(movies_dir, args.dry_run)
    phase_cleanup(movies_dir, args.dry_run)
    phase_report(movies_dir)

    total = moved0 + moved1 + moved2 + moved3 + moved4 + moved5
    print(f"\n  Total files {'to move' if args.dry_run else 'moved'}: {total}")


if __name__ == '__main__':
    main()
