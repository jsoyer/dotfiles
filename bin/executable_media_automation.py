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
from datetime import date
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
# "S018E30 Pokémon - Pikachu en vedette !" : le jeton ouvre le nom et le titre
# suit. Le separateur consomme espaces et points mais PAS le tiret, pour que
# "S01E01 - Titre" laisse un tiret en tete : signe qu'aucun nom de serie ne
# precede et qu'il faut se rabattre sur le dossier parent.
LEADING_EPISODE_RE = re.compile(
    r'^S(?P<season>\d{1,3})[.\s_-]?E(?P<episode>\d{1,4})(?!\d)'
    r'(?:[-.\s_]?E(?P<episode2>\d{1,4}))?(?=[.\s_-]|$)[.\s_]*(?P<title>.*)$',
    re.I,
)

EPISODE_PATTERNS = [
    re.compile(r'^(?P<title>.+?)[.\s_-]+S(?P<season>\d{1,2})E(?P<episode>\d{1,4})(?!\d)(?:[-.\s_]?E(?P<episode2>\d{1,4})(?!\d))?', re.I),
    re.compile(r'^(?P<title>.+?)[.\s_-]+(?P<season>\d{1,2})x(?P<episode>\d{1,3})(?:-(?P<episode2>\d{1,3}))?', re.I),
    # Season-less releases: "Show.1982.TV.Series.E01.MULTi.1080p", "Show - Ep05".
    # The episode token must stand alone (delimiter or end of name) to avoid
    # matching release-group suffixes. Season defaults to 1, or is taken from
    # the parent directory when it advertises one.
    re.compile(
        r'^(?P<title>.+?)[.\s_-]+(?:E|EP|EPISODE)[.\s_-]?(?P<episode>\d{1,4})(?!\d)'
        r'(?:[-.\s_]?E(?P<episode2>\d{1,4})(?!\d))?(?=[.\s_-]|$)',
        re.I,
    ),
    # Convention de fansub : « Serie - 124 (VOSTFR-FR 1920x1080 H264 AAC) ».
    # Le numero suit un tiret, sans lettre pour l'annoncer. Cette forme est
    # ambigue — « Blade Runner - 2049 (2017) » lui ressemble — d'ou les deux
    # garde-fous appliques plus bas : le numero ne doit pas etre une annee
    # plausible, et ce qui suit ne doit pas en etre une non plus.
    re.compile(
        r'^(?P<title>.+?)\s+-\s+(?P<episode>\d{1,4})(?!\d)'
        r'\s*(?P<apres>[\(\[][^)\]]*[\)\]])?'
        # Une reedition ajoute sa marque apres la parenthese : « …AAC)v2 ».
        # Exiger que le nom s'arrete la faisait echouer la lecture pour deux
        # caracteres, et trois episodes repartaient dans le tas des films.
        r'\s*(?:v\d{1,2}|final|repack|corrected?)?\s*$', re.I),
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
class NtfyConfig:
    """ntfy notification settings."""

    enabled: bool = False
    server: str = 'https://ntfy.sh'
    topic: str | None = None
    token: str | None = None
    priority: int = 3
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
    ntfy: NtfyConfig = field(default_factory=NtfyConfig)


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
    """Remove illegal filesystem characters, leaving no hole where they stood.

    TMDb writes "Pokemon : Les horizons". Dropping the colon alone would leave
    the two spaces that framed it, and the library grows a directory whose name
    is indistinguishable to the eye from the correct one — yet a different
    string for every tool that compares paths. Whitespace runs are collapsed.
    """
    return re.sub(r'\s+', ' ', ILLEGAL_CHARS.sub('', name)).strip()


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
    ntfy_raw = raw.get('ntfy', {})

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
        ntfy=NtfyConfig(
            enabled=bool_from_config(ntfy_raw.get('enabled'), False),
            server=str(ntfy_raw.get('server')
                       or os.environ.get('NTFY_SERVER') or 'https://ntfy.sh'),
            topic=ntfy_raw.get('topic') or os.environ.get('NTFY_TOPIC'),
            token=ntfy_raw.get('token') or os.environ.get('NTFY_TOKEN'),
            priority=int(ntfy_raw.get('priority', 3)),
            timeout=int(ntfy_raw.get('timeout', 15)),
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


NTFY_TAILLE_MAX = 3900


def _entete_transmissible(valeur):
    """Un en-tete HTTP ne survit pas hors du latin-1.

    http.client encode les en-tetes dans cet alphabet : un titre accentue ou
    porteur d'emoji ferait echouer l'envoi au moment du socket, loin du point
    d'appel. On prefere perdre le titre que la notification.
    """
    try:
        valeur.encode('latin-1')
    except UnicodeEncodeError:
        return False
    return True


def decouper_pour_ntfy(message, taille=NTFY_TAILLE_MAX):
    """Decoupe un message en corps acceptables par ntfy.

    On reutilise le decoupeur de Telegram, qui coupe proprement aux sauts de
    ligne, puis on tranche sans ceremonie ce qui depasse encore : une ligne
    unique tres longue en ressort intacte et ntfy la rejetterait.
    """
    morceaux = []
    for chunk in split_telegram_message(message, taille):
        if len(chunk.encode('utf-8')) <= taille:
            morceaux.append(chunk)
            continue
        for debut in range(0, len(chunk), taille):
            morceaux.append(chunk[debut:debut + taille])
    return morceaux


def send_ntfy_message(settings, message, titre=None):
    """Publish a notification to an ntfy topic when configured."""
    if not settings.enabled or not settings.topic:
        return

    url = f"{settings.server.rstrip('/')}/{settings.topic}"
    # Cloudflare protege le serveur ntfy et refuse la signature par defaut
    # d'urllib (« Python-urllib/3.x ») par une erreur 1010, qui se presente
    # comme un 403 et ressemble a tort a un jeton invalide.
    entetes = {'Priority': str(settings.priority),
               'User-Agent': 'media_automation/1.0'}
    if settings.token:
        entetes['Authorization'] = f"Bearer {settings.token}"
    if titre and _entete_transmissible(titre):
        entetes['Title'] = titre

    for chunk in decouper_pour_ntfy(message):
        request = urllib.request.Request(
            url, data=chunk.encode('utf-8'), headers=dict(entetes), method='POST')
        try:
            with urllib.request.urlopen(request, timeout=settings.timeout):
                pass
        except Exception as exc:
            LOGGER.warning("ntfy notification failed: %s", exc)


def notifier(config, message, titre=None):
    """Diffuse un message sur tous les canaux de notification actives.

    Point de dispatch unique : la bascule d'un canal a l'autre se joue dans le
    TOML, jamais dans les appelants. Chaque emetteur garde par ailleurs son
    propre garde-fou, pour qu'un appel direct reste sans effet s'il est eteint.
    """
    if config.telegram.enabled:
        send_telegram_message(config.telegram, message)
    if config.ntfy.enabled:
        send_ntfy_message(config.ntfy, message, titre)


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


def annee_plausible(valeur):
    """Un film ne sort pas dans vingt ans.

    « Ghost.In.The.Shell.SAC.2045.Sustainable.War.2021 » porte deux nombres a
    quatre chiffres : 2045 appartient au titre, 2021 est l'annee. Accepter tout
    jusqu'a 2099 faisait retenir le premier venu, tronquait le titre, et TMDb ne
    connaissait evidemment aucun film sorti en 2045.
    """
    return 1900 <= int(valeur) <= date.today().year + 1


def _titre_autour_de_l_annee(avant, apres):
    """Recompose le titre quand la release le place apres l'annee.

    « Lupin.III.Special.01.1989.Goodbye.Lady.Liberty.1080p… » ne donne, avant
    l'annee, que « Lupin III Special 01 » — un rang, que TMDb ne connait sous
    aucun nom. Le titre veritable suit l'annee.

    On ne recompose que lorsque ce qui precede se termine par un rang : ailleurs,
    ce qui suit l'annee n'est que du bruit de release. Et l'on conserve le
    prefixe de la saga, sans quoi « From Russia with love » ramene le James Bond
    de 1963 plutot que le Lupin III de 1992.
    """
    if not RANG_FINAL_RE.search(avant):
        return avant
    suite = apres.replace('.', ' ').replace('_', ' ').strip(' -')
    coupe = QUALITE_RE.search(suite)
    if coupe:
        suite = suite[:coupe.start()]
    suite = re.sub(r'\s+', ' ', suite).strip(' -')
    if len(suite) < 3:
        return avant
    prefixe = RANG_FINAL_RE.sub('', avant).strip(' -')
    return f'{prefixe} {suite}'.strip() if prefixe else suite


def parse_filename(filename):
    """Extract title and year from a scene-style filename."""
    name = filename
    for suffix in ['-fanart', '-poster', '-clearlogo', '-logo', '-banner',
                   '-thumb', '-landscape', '-disc', '-backdrop']:
        name = name.split(suffix)[0]
    name = re.sub(r'\.(mkv|mp4|avi|jpg|png|svg|nfo|srt|sub|idx|ass)$', '', name, flags=re.I)
    # Les etiquettes entre crochets encadrent le titre sans en faire partie :
    # groupe de release en tete, mentions de qualite en queue. Les laisser
    # empechait toute extraction — le fichier etait ecarte sans titre du tout.
    name = re.sub(r'\[[^\]]*\]', ' ', name)
    name = re.sub(r'\s+', ' ', name).strip(' .-_')

    m = PAREN_YEAR_RE.match(name)
    if m and annee_plausible(m.group(2)):
        title = m.group(1).replace('.', ' ').replace('_', ' ').strip()
        return title, m.group(2)

    # On parcourt tous les nombres a quatre chiffres et on retient le premier qui
    # puisse etre une annee : ce qui precede est le titre, ceux qu'on a franchis
    # lui appartiennent.
    for trouve in re.finditer(r'[.\s_](\d{4})(?=[.\s_]|$)', name):
        if not annee_plausible(trouve.group(1)):
            continue
        title = name[:trouve.start()].replace('.', ' ').replace('_', ' ').strip()
        if title:
            return _titre_autour_de_l_annee(title, name[trouve.end():]), trouve.group(1)

    m = DASH_RE.match(name)
    if m:
        title = m.group(1).replace('.', ' ').replace('_', ' ').strip()
        return title, None

    # Dernier recours : ce qui subsiste une fois le bruit de release retire.
    # Un fichier sans annee ni marqueur de qualite reconnu n'est pas pour autant
    # sans titre — « Détective Conan - Le Cauchemar Noir de Jais » etait ecarte
    # sans qu'aucune recherche n'ait seulement ete tentee. Mieux vaut une
    # recherche qui echoue, elle se lit dans le journal.
    reste = SERIES_TITLE_NOISE_RE.sub(' ', name.replace('.', ' ').replace('_', ' '))
    reste = re.sub(r'\s+', ' ', reste).strip(' -.')
    if len(reste) >= 3 and re.search(r'[^\W\d_]', reste):
        return reste, None

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
    # Une etiquette de groupe ouvre souvent le nom : « [Pokemon Fansub] Serie ».
    # Elle encadre le titre sans en faire partie, et TMDb ne connait personne
    # sous ce nom. parse_filename la retire deja pour les films.
    name = re.sub(r'^\s*\[[^\]]*\]\s*', '', name).strip()

    # Jeton en tete de nom : la serie, si elle est la, precede le titre d'episode.
    leading = LEADING_EPISODE_RE.match(name)
    if leading:
        reste = (leading.group('title') or '').strip()
        # Un tiret en tete signale que le titre d'episode suit directement,
        # sans nom de serie : on prend alors celui du dossier parent.
        serie = '' if reste.startswith('-') else reste.split(' - ')[0]
        title = clean_series_title(serie) if serie else ''
        if not title and parent_name:
            title = clean_series_title(parent_name)
        if title:
            episodes = [int(leading.group('episode'))]
            if leading.group('episode2'):
                episodes.append(int(leading.group('episode2')))
            return title, int(leading.group('season')), episodes

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
        numero = int(match.group('episode'))
        # Un numero nu apres un tiret peut aussi bien etre un rang d'episode
        # qu'une part de titre : « Blade Runner - 2049 (2017) » n'est pas le
        # 2049e episode de Blade Runner. On refuse donc quand le numero peut
        # etre une annee, ou quand ce qui le suit en est une — un film porte son
        # millesime entre parentheses, un fansub y met ses mentions techniques.
        if 'apres' in match.groupdict():
            apres = (match.group('apres') or '').strip('()[] ')
            # annee_plausible attend un nombre : « VOSTFR-FR 1920x1080 » n'en
            # est pas un, et n'a donc pas a lui etre soumis.
            suite_est_une_annee = apres.isdigit() and annee_plausible(apres)
            if annee_plausible(numero) or suite_est_une_annee:
                continue
        title = clean_series_title(raw_title) or raw_title.replace('.', ' ').strip(' -.')
        episodes = [numero]
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


def get_consolidated_filename(f, clean_name):
    """Normalize filenames when consolidating into a quality directory."""
    if f.suffix.lower() in ('.jpg', '.png', '.svg'):
        return get_art_name(f)
    return get_new_filename(f, clean_name)


def nom_de_version(clean_name, quality):
    """Nom de base d'une version, au format multi-version d'Emby.

    « Chaque version doit commencer par le nom du dossier, suivi de " - " » ;
    ce qui suit le tiret devient le libelle affiche dans l'application.
    """
    return f"{clean_name} - {quality}"


def aplatir_dossier_qualite(dossier, dry_run=False):
    """Remonte les fichiers des sous-dossiers de qualite dans le dossier du film.

    Les visuels gardent leur nom generique : deux affiches homonymes venues de
    deux qualites sont le meme visuel, la premiere suffit. Pour tout autre
    type de fichier, une collision n'entraine aucune suppression — on laisse le
    fichier ou il est et on conserve le sous-dossier, quitte a ne rien faire.
    """
    remontes = 0
    for sous in sorted(get_quality_subdirs(dossier), key=lambda p: p.name):
        radical = nom_de_version(dossier.name, sous.name)
        conflits = []
        for f in sorted(p for p in sous.rglob('*') if p.is_file()):
            cible = dossier / get_consolidated_filename(f, radical)
            if cible.exists():
                if f.suffix.lower() in ('.jpg', '.png', '.svg'):
                    if not dry_run:
                        f.unlink()
                else:
                    conflits.append(f)
                continue
            if not dry_run:
                f.rename(cible)
            remontes += 1
        if conflits:
            log_message(f"[FLAT] {dossier.name}/{sous.name}: {len(conflits)} "
                        f"fichier(s) en conflit, sous-dossier conserve", 'warning')
        elif not dry_run:
            shutil.rmtree(sous)
    return remontes

def count_dir_files(d):
    """Count files recursively in a directory."""
    return sum(1 for f in d.rglob('*') if f.is_file())


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


def _alias_discriminants(titre):
    """Alias d'un titre, prive de ceux qui ne designent qu'une saga.

    title_aliases produit aussi la portion qui precede le tiret : « Dragon Ball
    Z » pour « Dragon Ball Z - Baddack contre Freezer ». Cet alias tronque
    nomme la saga, non le film. Associe a la seule annee, il declare doublons
    deux longs metrages differents sortis la meme annee — et la phase de fusion
    les reunit alors dans un seul dossier, ou le serveur de medias n'en montre
    plus qu'un.

    C'est ainsi que quatre films de Dragon Ball Z ont disparu dans le dossier
    de leurs voisins. On ecarte donc tout alias qui n'est que le prefixe d'un
    autre : seul le titre complet identifie un film. Les identifiants TMDb et
    IMDb, eux, restent des cles fiables et suffisent aux vrais doublons.
    """
    alias = {a for a in title_aliases(titre) if len(a) >= 3}
    # Contenu, et non plus seulement prefixe : « Dragon Ball Z - Fusions » et
    # « Dragon Ball Z - L'Attaque du dragon » partageaient l'alias « z », qui ne
    # prefixe ni l'un ni l'autre mais figure dans les deux. Une lettre isolee
    # suffisait ainsi a declarer doublons deux films de 1995. Un alias contenu
    # dans un autre n'ajoute aucune information : il ne peut qu'egarer.
    return {a for a in alias
            if not any(autre != a and a in autre for autre in alias)}


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
        for alias in _alias_discriminants(dir_title):
            keys.add(('title-year', alias, dir_year))

    for title in (
        metadata['title'],
        metadata['originaltitle'],
        metadata['sorttitle'],
        metadata['english_title'],
    ):
        if title and year:
            for alias in _alias_discriminants(title):
                keys.add(('title-year', alias, year))

    return keys


def identite_du_dossier_diverge(dossier, tmdb_id):
    """Dit si un dossier existant revendique un autre film que celui resolu.

    Retourne None si le dossier est absent, muet, ou d'accord ; « perime » s'il
    revendique un autre film sans plus contenir la moindre video — le NFO est
    alors un residu du film parti ; « occupe » s'il revendique un autre film et
    l'heberge encore.
    """
    if not dossier.is_dir():
        return None
    declare = get_dir_metadata(dossier)['tmdbid']
    # TMDb renvoie un entier la ou le NFO porte du texte : cette seule
    # difference ne doit pas faire conclure a une divergence.
    if not declare or str(declare) == str(tmdb_id):
        return None
    a_une_video = any(f.suffix.lower() in VIDEO_EXTENSIONS
                      for f in iter_movie_files(dossier))
    return 'occupe' if a_une_video else 'perime'

# Un suffixe de copie « (2) » nait d'une collision de noms. Trois chiffres au
# plus, pour ne pas confondre avec l'annee que porte la fin du nom de dossier :
# « Le Parrain (1972) » ne doit pas perdre son millesime.
SUFFIXE_COPIE_RE = re.compile(r'\s\(\d{1,3}\)$')


def etiquette_de_version(fichier, nom_dossier):
    """Etiquette de version d'un fichier, au sens multi-version d'Emby.

    Chaque version commence par le nom du dossier suivi de « - » ; ce qui suit
    est l'etiquette affichee dans l'application. Un suffixe de copie ne fait
    pas une version : deux fichiers ainsi nommes sont deux copies de la meme.
    """
    radical = SUFFIXE_COPIE_RE.sub('', Path(fichier).stem)
    if not radical.startswith(nom_dossier):
        return None
    reste = radical[len(nom_dossier):]
    if not reste.startswith(' - '):
        return None
    return reste[3:].strip() or None


def _videos_du_dossier(dossier):
    return sorted(f for f in dossier.iterdir()
                  if f.is_file() and f.suffix.lower() in VIDEO_EXTENSIONS)


def videos_hors_convention(dossier):
    """Videos qu'Emby ne peut rattacher au film, faute d'en porter le nom."""
    return [f for f in _videos_du_dossier(dossier)
            if not SUFFIXE_COPIE_RE.sub('', f.stem).startswith(dossier.name)]


def doublons_internes(dossier):
    """Groupes de videos d'un meme dossier qui pretendent a la meme version."""
    par_etiquette = defaultdict(list)
    for f in _videos_du_dossier(dossier):
        if SUFFIXE_COPIE_RE.sub('', f.stem).startswith(dossier.name):
            par_etiquette[etiquette_de_version(f, dossier.name)].append(f)
    return [groupe for _, groupe in
            sorted(par_etiquette.items(), key=lambda kv: str(kv[0]))
            if len(groupe) > 1]

def get_duplicate_groups(movies_dir):
    """Return duplicate groups using NFO identifiers and title aliases.

    Deux natures de cle cohabitent : l'identite (tmdbid, imdbid), qui fait foi,
    et la ressemblance de titre, qui n'est qu'une hypothese. Les traiter a
    egalite a deja reuni deux films distincts partageant un alias — « Dragon
    Ball Z - Fusions » et « Dragon Ball Z - L'Attaque du dragon ». Une
    ressemblance n'unit donc plus deux groupes dont les identites se
    contredisent.
    """
    proper_dirs = sorted((d for d in movies_dir.iterdir()
                          if d.is_dir() and is_proper_dir(d)),
                         key=lambda p: p.name)
    parent = {d: d for d in proper_dirs}

    # Identifiants revendiques par chaque groupe, refondus a chaque union.
    identites = {}
    for d in proper_dirs:
        metadata = get_dir_metadata(d)
        identites[d] = (
            {str(metadata['tmdbid'])} if metadata['tmdbid'] else set(),
            {str(metadata['imdbid'])} if metadata['imdbid'] else set(),
        )

    def find(d):
        while parent[d] != d:
            parent[d] = parent[parent[d]]
            d = parent[d]
        return d

    def union(left, right):
        root_left = find(left)
        root_right = find(right)
        if root_left == root_right:
            return
        parent[root_right] = root_left
        tmdb_gauche, imdb_gauche = identites[root_left]
        tmdb_droite, imdb_droite = identites[root_right]
        identites[root_left] = (tmdb_gauche | tmdb_droite,
                                imdb_gauche | imdb_droite)

    def se_contredisent(left, right):
        """Vrai si unir ces deux groupes reunirait deux identites distinctes."""
        tmdb_gauche, imdb_gauche = identites[find(left)]
        tmdb_droite, imdb_droite = identites[find(right)]
        return (len(tmdb_gauche | tmdb_droite) > 1
                or len(imdb_gauche | imdb_droite) > 1)

    key_to_dirs = defaultdict(list)
    for d in proper_dirs:
        for key in get_duplicate_group_keys(d):
            key_to_dirs[key].append(d)

    # L'identite passe en premier : elle fixe les groupes que la ressemblance
    # devra ensuite respecter.
    for key, dirs in key_to_dirs.items():
        if key[0] not in ('tmdb', 'imdb') or len(dirs) < 2:
            continue
        for other in dirs[1:]:
            union(dirs[0], other)

    for key, dirs in key_to_dirs.items():
        if key[0] in ('tmdb', 'imdb') or len(dirs) < 2:
            continue
        for other in dirs[1:]:
            if se_contredisent(dirs[0], other):
                continue
            union(dirs[0], other)

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


# Un rang dans la saga — « FiLM x 09 », « Film 3 » — sert au rangement, pas a
# l'identification : TMDb ne connait aucun film sous ce nom.
RANG_SAGA_RE = re.compile(r'\b(?:le\s+)?films?\s*(?:x\s*)?\d{0,2}\b', re.I)
# Elision perdue : un nom de fichier ne peut pas porter d'apostrophe, elle y
# devient un souligne, puis une espace. « Les Mercenaires de L espace » ne
# ressemble alors plus a rien de cherchable.
# Un rang de serie ferme parfois le titre : « Lupin III Special 01 ».
RANG_FINAL_RE = re.compile(
    r'\s*\b(?:specials?|films?|vol\.?|volumes?|oav|ova|ep|episodes?|partie|part)\s*\d{1,3}$',
    re.I)
# Premier marqueur de qualite : ce qui suit n'appartient plus au titre.
QUALITE_RE = re.compile(
    r'\b(?:\d{3,4}[pi]|bluray|blu-ray|bdrip|brrip|webrip|web-dl|web|hdlight|hdtv|dvdrip|'
    r'x26[45]|h\.?26[45]|hevc|avc|aac|ac3|eac3|dts|flac|multi|vff|vfq|vostfr|vo|truefrench|'
    r'french|remux|repack|proper|fansub|notag)\b', re.I)

ELISION_RE = re.compile(r"\b([ldjnmtcsLDJNMTCS])\s+(?=[aeiouyhàâéèêëîïôöûüAEIOUYH])")


def _variantes_titre(titre):
    """Formes successives d'un titre, de la plus fidele a la plus depouillee.

    Une release ecrit rarement le titre seul : elle le prefixe du nom de la saga,
    y glisse un rang, le suffixe de son groupe, et remplace les apostrophes par
    ce qu'un systeme de fichiers accepte. Chacune de ces marques suffit a faire
    echouer la recherche, et le fichier est alors ecarte sans qu'on sache
    pourquoi.

    On produit donc plusieurs lectures du meme nom, de la plus proche du fichier
    a la plus reduite. La premiere qui ramene un resultat gagne : commencer par
    la forme integrale evite qu'un titre trop court attrape un homonyme.
    """
    vues, variantes = set(), []

    def ajouter(candidat):
        candidat = re.sub(r'\s+', ' ', candidat or '').strip(' -.')
        if len(candidat) >= 3 and candidat.lower() not in vues:
            vues.add(candidat.lower())
            variantes.append(candidat)

    formes = [titre]
    # Le groupe de release ferme souvent le nom, apres un tiret.
    formes.append(re.sub(r'\s+-\s+[A-Za-z0-9]{2,10}$', '', titre))
    formes.append(RANG_SAGA_RE.sub(' ', formes[-1]))
    # En dernier ressort, ce qui suit le dernier tiret : le titre propre, quand
    # ce qui precede n'est que le nom de la saga.
    if ' - ' in formes[-1]:
        formes.append(formes[-1].rsplit(' - ', 1)[1])
    # Un chiffre isole au milieu du titre est un rang de suite ajoute par la
    # release : « Fullmetal Alchemist 2 The Revenge of Scar ». Le retirer en
    # dernier seulement, car « Toy Story 2 » se trouve des la forme integrale et
    # n'atteint jamais cette variante.
    sans_rang_isole = re.sub(r'(?<=\S)\s+\d{1,2}\s+(?=\S)', ' ', formes[-1])
    if sans_rang_isole != formes[-1]:
        formes.append(sans_rang_isole)

    for forme in formes:
        ajouter(forme)
        avec_elision = ELISION_RE.sub(r"\1'", forme)
        if avec_elision != forme:
            ajouter(avec_elision)
    return variantes


def search_tmdb_movie(title, year, api_key, language):
    """Search TMDb for a movie candidate, choosing rather than taking the first.

    TMDb does not order by relevance: 'X-Men' with year 2000 returns
    'X-Men: The Mutant Watch', a making-of, ahead of the film. Series have long
    been protected from this — an obscure chibi spin-off once outranked Attack
    on Titan — but movies were not, so an import could file a feature under its
    own documentary.
    """
    results, retenu = [], title
    for variante in _variantes_titre(title):
        params = {'query': variante, 'language': language}
        if year:
            params['year'] = year
        results = (tmdb_request('/search/movie', api_key, params) or {}).get('results', [])
        if results:
            retenu = variante
            break
    if not results:
        return None
    title = retenu
    if year:
        millesime = [r for r in results
                     if (r.get('release_date') or '').startswith(str(year))]
        if millesime:
            return _meilleur_candidat_film(title, millesime)
    return _meilleur_candidat_film(title, results)


def _meilleur_candidat_film(query, results):
    """An exact title wins outright; otherwise popularity decides."""
    cible = normalize(query)
    exacts = [r for r in results
              if cible in {normalize(r.get('title') or ''),
                           normalize(r.get('original_title') or '')}]
    return max(exacts or results, key=lambda r: r.get('popularity') or 0)


def get_tmdb_movie_details(movie_id, api_key, language):
    """Fetch detailed metadata and images for a TMDb movie."""
    return tmdb_request(
        f'/movie/{movie_id}',
        api_key,
        {'language': language, 'append_to_response': 'images,external_ids'}
    )


def search_tmdb_tv(title, year, api_key, language):
    """Search TMDb for a TV show candidate.

    The year is a hint, never a requirement. Release folders name the year of
    the season they contain, not the year the series began: 'Saison 21 (2016)'
    of Detective Conan handed 2016 to a series that started in 1996, TMDb
    answered with an empty list, and every episode of the pack was rejected as
    unknown. So a year that finds nothing is dropped and the search retried.
    """
    params = {'query': title, 'language': language}
    if year:
        params['first_air_date_year'] = year
    payload = tmdb_request('/search/tv', api_key, params)
    results = payload.get('results', [])
    if not results and year:
        year = None
        results = tmdb_request(
            '/search/tv', api_key, {'query': title, 'language': language}
        ).get('results', [])
    if not results:
        return None
    if year:
        millesime = [r for r in results
                     if (r.get('first_air_date') or '').startswith(str(year))]
        if millesime:
            return _meilleur_candidat_tv(title, millesime)
    return _meilleur_candidat_tv(title, results)


def _meilleur_candidat_tv(query, results):
    """Pick the best match instead of whatever TMDb happened to list first.

    TMDb's ordering is not by relevance: searching "Attack on Titan" returns an
    obscure chibi spin-off ahead of the actual series, which is far more popular.
    An exact title match wins outright; otherwise popularity decides.
    """
    cible = normalize(query)
    exacts = [r for r in results
              if cible in {normalize(r.get('name') or ''), normalize(r.get('original_name') or '')}]
    lot = exacts or results
    return max(lot, key=lambda r: r.get('popularity') or 0)


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
        target_dir = movies_dir / clean_name
        radical = nom_de_version(clean_name, quality)

        print(f"[INCOMING] {video_path.name} -> {target_dir.relative_to(movies_dir)}/")
        if not dry_run:
            target_dir.mkdir(parents=True, exist_ok=True)

        for related in find_incoming_related_files(video_path):
            new_name = get_consolidated_filename(related, radical)
            safe_move(related, target_dir / new_name, dry_run)
            moved += 1

        if fetch_metadata:
            nfo_path = target_dir / f"{radical}.nfo"
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


def get_episode_target_name(path, series_name, season_number, episodes, episode_title=None):
    """Build the destination filename for an imported TV/anime episode asset.

    The title belongs in the name. A bare code says nothing to the viewer, and
    it makes a misfiled episode impossible to spot by eye — the only clue left
    would be the number, which is precisely what cannot be trusted when an
    import went astray. When TMDb has no title to offer, the bare code stands.
    """
    episode_code = build_episode_code(season_number, episodes)
    title = sanitize(episode_title or '')
    if title:
        episode_code = f"{episode_code} - {title}"
    series_name = sanitize(series_name)
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

    # Un dossier au bon nom n'est pas forcement le bon dossier : on confronte
    # l'identifiant resolu a celui que le NFO declare avant d'y deverser quoi
    # que ce soit.
    dossier_film = route_root / clean_name
    divergence = identite_du_dossier_diverge(dossier_film, candidate['id'])
    if divergence == 'occupe':
        summary.skipped_items += 1
        detail = (f"[SKIP] {item.video_path.name} "
                  f"({clean_name} heberge deja un autre film)")
        summary.skipped_details.append(detail)
        log_message(detail, 'warning')
        notifier(config, f"⚠️ {detail}", 'media')
        return
    if divergence == 'perime':
        # Le film a quitte ce dossier en y laissant son NFO. Le garder ferait
        # croire au prochain passage que la place est prise.
        for nfo in list(get_dir_nfo_candidates(dossier_film)):
            log_message(f"[NFO] residu ecarte: {display_relative(nfo, route_root)}")
            if not dry_run:
                nfo.unlink()

    target_dir = route_root / clean_name
    # La qualite passe du dossier au nom : Emby reconnait ainsi plusieurs
    # versions d'un meme film cohabitant dans un seul dossier.
    radical = nom_de_version(clean_name, quality)

    log_message(f"[IMPORT:{route_kind.upper()}] {item.video_path.name} -> {display_relative(target_dir, route_root)}/")
    if not dry_run:
        target_dir.mkdir(parents=True, exist_ok=True)

    moved_now = 0
    for related in item.related_files:
        new_name = get_consolidated_filename(related, radical)
        moved_path = safe_move(related, target_dir / new_name, dry_run)
        if moved_path is not None:
            moved_now += 1

    if config.fetch_metadata:
        nfo_path = target_dir / f"{radical}.nfo"
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

    # The title must be known before anything moves: it goes into every
    # destination filename, and a file already renamed would need a second pass
    # to gain it. TMDb answers 404 whenever the release numbers its seasons
    # differently than TMDb does — that must cost the episode its title and
    # nothing more, the file itself being perfectly valid.
    episode_details = None
    if config.fetch_metadata:
        try:
            episode_details = get_tmdb_episode_details(
                details['id'],
                season_number,
                episodes[0],
                config.tmdb_api_key,
                config.tmdb_language,
            )
        except Exception as exc:  # noqa: BLE001 - a missing title never blocks an import
            log_message(
                f"    [WARN] TMDb has no {build_episode_code(season_number, episodes)} "
                f"for {series_name}: {exc}",
                'warning',
            )
    episode_title = (episode_details or {}).get('name')

    moved_now = 0
    for related in item.related_files:
        destination_parent = show_dir if related.suffix.lower() in ('.jpg', '.png', '.svg') else season_dir
        new_name = get_episode_target_name(
            related, series_name, season_number, episodes, episode_title
        )
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

        # episode_details was fetched before the move, above. Without it there is
        # nothing to describe, so the episode NFO is skipped rather than written
        # empty — the warning has already been logged.
        if episode_details is not None:
            episode_nfo_name = get_episode_target_name(
                Path(f"episode{item.video_path.suffix}"), series_name,
                season_number, episodes, episode_title,
            )
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
        # L'aplatissement n'a pas sa place ici : il tourne a la demande, dans
        # le mode manuel. Le cycle automatique se contente de reconcilier les
        # doublons, les fichiers arrivant deja a plat.
        total_moved += phase_duplicate_dirs(root, dry_run)
        phase_cleanup(root, dry_run)
    return total_moved


ABSOLUTE_REGISTRY_PATH = Path(__file__).resolve().parent / 'media_automation' / 'shows_registry.toml'


def load_absolute_shows(registry_path=None):
    """Load the opt-in registry of absolute-numbered shows; [] when unavailable.

    A missing or broken registry must never stop the regular import, so any
    failure is logged and degrades to "no show declared".
    """
    try:
        import media_absolute_shows
    except Exception as exc:  # noqa: BLE001 - optional feature, never fatal
        LOGGER.warning("Absolute-show support unavailable: %s", exc)
        return []
    try:
        return media_absolute_shows.load_registry(registry_path or ABSOLUTE_REGISTRY_PATH)
    except Exception as exc:  # noqa: BLE001
        log_message(f"[WARN] Registre des series absolues illisible: {exc}", 'warning')
        return []


def match_absolute_show(filename, shows):
    """Return the declared show this file belongs to, or None."""
    if not shows:
        return None
    import media_absolute_shows
    return media_absolute_shows.match_show(filename, shows)


def _ecarter_episode(name, raison, summary, show=None, config=None):
    """Enregistre un episode ecarte, avec sa raison, et previent comme avant."""
    summary.skipped_items += 1
    detail = f"[SKIP] {name} ({raison})"
    summary.skipped_details.append(detail)
    log_message(detail, 'warning')
    if show is not None and config is not None:
        notifier(config, f"⚠️ {show.name}: {name}\n{raison}", 'media')


def import_absolute_item(item, show, config, dry_run, summary):
    """Send one episode of a declared absolute-numbered show to its remote library."""
    import media_absolute_shows as abs_shows

    name = item.video_path.name
    try:
        mapping = abs_shows.load_mapping(show.mapping_file)
    except Exception as exc:  # noqa: BLE001
        summary.skipped_items += 1
        detail = f"[SKIP] {name} (table de conversion illisible: {exc})"
        summary.skipped_details.append(detail)
        log_message(detail, 'warning')
        return

    try:
        relative, season_number, episode_number = abs_shows.plan_episode(name, show, mapping)
    except ValueError as exc:
        # La table ne se rafraichit qu'apres un import reussi : un episode
        # ecarte parce qu'il « depasse la bibliotheque » ne la met donc jamais
        # a jour, et le rejet se reproduit a chaque passage. On la reconstruit
        # une fois, puis on retente — si l'episode etait simplement plus recent
        # que la table, il passe ; s'il est vraiment aberrant, il est ecarte
        # comme avant, mais sur des donnees fraiches.
        if 'depasse la bibliotheque' in str(exc):
            try:
                mapping = abs_shows.refresh_mapping(
                    show, api_key=config.tmdb_api_key, language=config.language)
                relative, season_number, episode_number = abs_shows.plan_episode(
                    name, show, mapping)
                log_message(f"[INFO] Table {show.name} rafraichie, {name} accepte")
            except Exception:  # noqa: BLE001
                _ecarter_episode(name, exc, summary, show, config)
                return
        else:
            _ecarter_episode(name, exc, summary, show, config)
            return
    destination = f"{show.destination}/{relative}"
    log_message(f"[IMPORT:REMOTE] {name} -> {show.name} S{season_number:02d}E{episode_number:02d}")

    # Never overwrite an episode already present upstream.
    try:
        if abs_shows.remote_exists(destination):
            summary.skipped_items += 1
            detail = f"[SKIP] {name} (deja present: {relative})"
            summary.skipped_details.append(detail)
            log_message(detail, 'warning')
            return
    except Exception as exc:  # noqa: BLE001
        summary.errors += 1
        detail = f"[ERROR] {name} (verification distante impossible: {exc})"
        summary.skipped_details.append(detail)
        log_message(detail, 'warning')
        return

    if dry_run:
        print(f"    {name} -> {destination}")
        summary.imported_items += 1
        summary.imported_details.append(f"{name} -> {destination}")
        return

    try:
        abs_shows.push_episode(item.video_path, destination)
    except Exception as exc:  # noqa: BLE001
        summary.errors += 1
        detail = f"[ERROR] {name} (transfert distant echoue: {exc})"
        summary.skipped_details.append(detail)
        log_message(detail, 'warning')
        notifier(config, f"❌ {show.name}: transfert echoue\n{name}", 'media')
        return

    print(f"    OK: {name} -> {relative}")
    summary.imported_items += 1
    summary.imported_series += 1
    summary.imported_details.append(f"{name} -> {destination}")
    notifier(
        config,
        f"☁️ {show.name} S{season_number:02d}E{episode_number:02d} envoye sur Drive\n{relative}")

    # Keep the table in step so the next episode lands on the following slot.
    try:
        abs_shows.refresh_mapping(show)
    except Exception as exc:  # noqa: BLE001
        log_message(f"[WARN] Table {show.name} non rafraichie: {exc}", 'warning')


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
        notifier(config, detection_message, 'media')

        if not config.tmdb_api_key:
            raise ValueError('TMDb API key required for inbox automation. Set it in config or TMDB_API_KEY.')

        absolute_shows = load_absolute_shows()

        for item in items:
            try:
                # Declared absolute-numbered shows go to their remote library.
                # Everything else keeps the default local routing untouched.
                show = match_absolute_show(item.video_path.name, absolute_shows)
                if show is not None:
                    import_absolute_item(item, show, config, dry_run, summary)
                    continue

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
        notifier(config, summary_message, 'media')
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
            # Plusieurs versions cohabitent desormais dans un seul dossier,
            # distinguees par leur nom : Emby les presente comme un film unique
            # assorti d'un selecteur de version.
            final_dir = target_dir
            radical = nom_de_version(clean_name, quality) if is_multi else clean_name

            if source_dir == final_dir:
                needs_work = any(get_new_filename(f, radical) != f.name for f in related)
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
                new_name = get_new_filename(f, radical)
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
                    # Rejoindre un dossier occupe ne creuse plus de sous-dossier :
                    # c'est le nom du fichier qui evite la collision.
                    quality = detect_quality(d.name) or '1080p'
                    radical = (nom_de_version(clean_name, quality)
                               if target_dir.exists() else clean_name)
                    final_dir = target_dir

                    print(f"[DIR-FIX] {d.name}/ -> {final_dir.relative_to(movies_dir)}/")
                    if not dry_run:
                        final_dir.mkdir(parents=True, exist_ok=True)

                    for f in sorted(files):
                        new_name = get_new_filename(f, radical)
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


def phase_aplatir_qualites(movies_dir, dry_run):
    """Phase 4: faire remonter les fichiers hors des sous-dossiers de qualite.

    L'exact inverse de ce que cette phase faisait autrefois. La qualite vit
    desormais dans le nom du fichier, au format multi-version d'Emby, qui
    presente alors les versions comme un seul film assorti d'un selecteur.
    """
    print("=" * 60)
    print("Phase 4: Aplatir les sous-dossiers de qualite\n")

    moved = 0
    for movie_dir in sorted(d for d in movies_dir.iterdir()
                            if d.is_dir() and is_proper_dir(d)):
        if not get_quality_subdirs(movie_dir):
            continue
        print(f"[FLAT] {movie_dir.name}")
        moved += aplatir_dossier_qualite(movie_dir, dry_run)
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
        print(f"[MERGE] {target_dir.name} <= {', '.join(d.name for d in source_dirs)}")
        if not dry_run:
            target_dir.mkdir(parents=True, exist_ok=True)

        for source_dir in source_dirs:
            for src in iter_movie_files(source_dir):
                # La qualite d'origine, qu'elle vienne d'un sous-dossier ou du
                # nom, se retrouve dans le nom du fichier fusionne.
                parts = src.relative_to(source_dir).parts
                radical = (nom_de_version(target_dir.name, parts[0])
                           if parts and parts[0] in QUALITY_DIR_NAMES
                           else target_dir.name)
                dst = target_dir / get_consolidated_filename(src, radical)

                if not dry_run:
                    dst.parent.mkdir(parents=True, exist_ok=True)
                safe_move(src, dst, dry_run)
                moved += 1

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
                notifier(config, f"[ERROR] Automated inbox scan failed: {exc}",
                         'media')
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
    moved4 = phase_aplatir_qualites(movies_dir, args.dry_run)
    moved5 = phase_duplicate_dirs(movies_dir, args.dry_run)
    phase_cleanup(movies_dir, args.dry_run)
    phase_report(movies_dir)

    total = moved0 + moved1 + moved2 + moved3 + moved4 + moved5
    print(f"\n  Total files {'to move' if args.dry_run else 'moved'}: {total}")


if __name__ == '__main__':
    main()
