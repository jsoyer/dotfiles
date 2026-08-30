#!/usr/bin/env python3
"""Extract zip/rar/7z archives that land in the media inbox.

The importer only sees video files. Archives must therefore be unpacked under
the same lock, after a disk-space check, and deleted only when the extracted
tree matches the archive catalogue (file count and uncompressed size).
"""
from __future__ import annotations

import logging
import re
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

LOGGER = logging.getLogger(__name__)

PARTIAL_EXTENSIONS = {'.part', '.tmp', '.crdownload', '.download'}
DEFAULT_MARGIN_BYTES = 10 * 1024 * 1024 * 1024
EXTRACT_TIMEOUT_SECONDS = 7200
LIST_TIMEOUT_SECONDS = 180

PART1_RE = re.compile(r'^(?P<stem>.+)\.part0*1\.(?P<ext>rar|zip)$', re.I)
PARTN_RE = re.compile(r'^(?P<stem>.+)\.part(?P<n>\d+)\.(?P<ext>rar|zip)$', re.I)
SEVENZ_VOL1_RE = re.compile(r'^(?P<stem>.+)\.7z\.001$', re.I)
SEVENZ_VOL_RE = re.compile(r'^(?P<stem>.+)\.7z\.(?P<n>\d+)$', re.I)
OLD_RAR_VOL_RE = re.compile(r'^(?P<stem>.+)\.r\d{2}$', re.I)
SPLIT_ZIP_RE = re.compile(r'^(?P<stem>.+)\.z\d{2}$', re.I)


@dataclass(frozen=True)
class ArchiveCatalog:
    """Uncompressed payload described by `7z l -slt`."""

    file_count: int
    uncompressed_bytes: int
    encrypted: bool
    names: tuple[str, ...] = ()
    sizes: tuple[int, ...] = ()


@dataclass
class ExtractResult:
    """Outcome of one archive, for logs and the inbox summary."""

    archive: Path
    extracted: bool
    detail: str


def is_partial_file(path):
    """Return True when a file still looks incomplete."""
    return path.suffix.lower() in PARTIAL_EXTENSIONS or path.name.endswith('.partial')


def is_stable_file(path, stability_seconds):
    """Return True when a file has not changed recently."""
    return time.time() - path.stat().st_mtime >= stability_seconds


def is_primary_archive(path):
    """True when this file is the one `7z` should be asked to open.

    Continuations (`.part2.rar`, `.r00`, `.7z.002`) are opened through the
    first volume; extracting them alone would duplicate or fail.
    """
    name = path.name
    if PARTN_RE.match(name):
        return bool(PART1_RE.match(name))
    if SEVENZ_VOL_RE.match(name):
        return bool(SEVENZ_VOL1_RE.match(name))
    if OLD_RAR_VOL_RE.match(name) or SPLIT_ZIP_RE.match(name):
        return False
    return path.suffix.lower() in {'.zip', '.rar', '.7z'}


def archive_members(primary):
    """Volumes that belong with `primary` and must vanish together."""
    parent = primary.parent
    name = primary.name
    match = PART1_RE.match(name)
    if match:
        stem, ext = match.group('stem'), match.group('ext')
        pattern = re.compile(rf'^{re.escape(stem)}\.part\d+\.{re.escape(ext)}$', re.I)
        return sorted(p for p in parent.iterdir() if p.is_file() and pattern.match(p.name))

    match = SEVENZ_VOL1_RE.match(name)
    if match:
        stem = match.group('stem')
        pattern = re.compile(rf'^{re.escape(stem)}\.7z\.\d+$', re.I)
        return sorted(p for p in parent.iterdir() if p.is_file() and pattern.match(p.name))

    if primary.suffix.lower() == '.rar':
        stem = primary.stem
        members = [primary]
        vol = re.compile(rf'^{re.escape(stem)}\.r\d{{2}}$', re.I)
        members.extend(p for p in parent.iterdir() if p.is_file() and vol.match(p.name))
        return sorted(set(members), key=lambda p: p.name.lower())

    if primary.suffix.lower() == '.zip':
        stem = primary.stem
        vol = re.compile(rf'^{re.escape(stem)}\.z\d{{2}}$', re.I)
        members = [primary]
        members.extend(p for p in parent.iterdir() if p.is_file() and vol.match(p.name))
        return sorted(set(members), key=lambda p: p.name.lower())

    return [primary]


def extract_dir_for(archive):
    """Sibling folder that receives the payload, named after the release."""
    name = archive.name
    name = PART1_RE.sub(r'\g<stem>', name)
    name = SEVENZ_VOL1_RE.sub(r'\g<stem>', name)
    name = re.sub(r'\.(zip|rar|7z)$', '', name, flags=re.I)
    return archive.parent / name


def _is_payload_file(item):
    """True for a real file entry in a `7z l -slt` record.

    Zip listings set `Folder = -`. 7z listings often omit `Folder` and only
    mark directories via `Attributes`. Either shape must count as a file.
    """
    if not item.get('Path'):
        return False
    if item.get('Folder') == '+':
        return False
    if item.get('Folder') == '-':
        return True
    attributes = item.get('Attributes') or ''
    tokens = attributes.replace('_', ' ').split()
    return 'D' not in tokens and not attributes.startswith('D')


def parse_7z_listing(text):
    """Read file count and uncompressed size out of `7z l -slt` output."""
    records = []
    current = {}
    in_files = False
    for raw in text.splitlines():
        line = raw.rstrip()
        if line.strip() == '----------':
            in_files = True
            if current:
                records.append(current)
                current = {}
            continue
        if not in_files:
            continue
        if not line.strip():
            if current:
                records.append(current)
                current = {}
            continue
        if ' = ' in line:
            key, value = line.split(' = ', 1)
            current[key] = value
    if current:
        records.append(current)

    files = [item for item in records if _is_payload_file(item)]
    encrypted = any(item.get('Encrypted') == '+' for item in records)
    total = sum(int(item.get('Size') or 0) for item in files)
    names = tuple(item['Path'] for item in files)
    sizes = tuple(int(item.get('Size') or 0) for item in files)
    return ArchiveCatalog(file_count=len(files), uncompressed_bytes=total,
                          encrypted=encrypted, names=names, sizes=sizes)


def catalog_archive(path):
    """Ask 7-Zip for the uncompressed catalogue of one archive."""
    result = subprocess.run(
        ['7z', 'l', '-slt', str(path)],
        capture_output=True, text=True, timeout=LIST_TIMEOUT_SECONDS,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or '7z listing failed').strip()
        raise RuntimeError(detail.splitlines()[-1] if detail else '7z listing failed')
    catalog = parse_7z_listing(result.stdout)
    if catalog.file_count == 0:
        raise RuntimeError('archive vide')
    return catalog


def disk_free(path):
    """Bytes free on the filesystem that holds `path`."""
    return shutil.disk_usage(path).free


def has_room(free, uncompressed, margin):
    """True when `uncompressed` plus the safety margin fit in `free`."""
    return free >= uncompressed + margin


def verify_extract(dest, catalog):
    """Compare extracted files to the catalogue, path by path and size by size."""
    files = [item for item in dest.rglob('*') if item.is_file()]
    if len(files) != catalog.file_count:
        return False
    for name, size in zip(catalog.names, catalog.sizes):
        path = dest / name
        if not path.is_file() or path.stat().st_size != size:
            return False
    return True


def extract_archive(archive, dest):
    """Unpack `archive` into a fresh `dest` (overwrite inside that folder)."""
    dest.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        ['7z', 'x', '-y', '-aoa', f'-o{dest}', str(archive)],
        capture_output=True, text=True, timeout=EXTRACT_TIMEOUT_SECONDS,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or '7z extract failed').strip()
        raise RuntimeError(detail.splitlines()[-1] if detail else '7z extract failed')


def _members_ready(primary, stability_seconds):
    """True when every volume of this set exists and is as stable as the primary."""
    members = archive_members(primary)
    if not members:
        return False
    for member in members:
        if not member.is_file() or is_partial_file(member):
            return False
        if not is_stable_file(member, stability_seconds):
            return False
    return True


def gather_archives(inbox, stability_seconds):
    """Stable primary archives under `inbox`, smallest first."""
    found = []
    for path in inbox.rglob('*'):
        if not path.is_file():
            continue
        relative = path.relative_to(inbox)
        if any(part.startswith('.') for part in relative.parts):
            continue
        if is_partial_file(path) or not is_stable_file(path, stability_seconds):
            continue
        if not is_primary_archive(path):
            continue
        if not _members_ready(path, stability_seconds):
            continue
        found.append(path)
    found.sort(key=lambda item: (item.stat().st_size, item.name.lower()))
    return found


def _human(nbytes):
    units = ('B', 'KiB', 'MiB', 'GiB', 'TiB')
    value = float(nbytes)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            if unit == 'B':
                return f'{int(value)}{unit}'
            return f'{value:.1f}{unit}'
        value /= 1024
    return f'{nbytes}B'


def _extract_one(archive, margin_bytes, dry_run):
    name = archive.name
    try:
        catalog = catalog_archive(archive)
    except Exception as exc:  # noqa: BLE001 - keep the archive, move on
        return ExtractResult(archive, False, f"[EXTRACT] {name}: catalogue illisible ({exc})")

    if catalog.encrypted:
        return ExtractResult(
            archive, False,
            f"[EXTRACT] {name}: archive chiffree — conservee")

    free = disk_free(archive.parent)
    if not has_room(free, catalog.uncompressed_bytes, margin_bytes):
        need = catalog.uncompressed_bytes + margin_bytes
        return ExtractResult(
            archive, False,
            f"[EXTRACT] {name}: espace insuffisant "
            f"({_human(free)} libre, {_human(need)} requis)")

    dest = extract_dir_for(archive)
    expected = (f"{catalog.file_count} fichier(s), "
                f"{_human(catalog.uncompressed_bytes)}")
    if dry_run:
        return ExtractResult(
            archive, False,
            f"[DRY] EXTRACT {name} -> {dest.name}/ ({expected})")

    staging = dest.with_name(dest.name + '.__extracting__')
    if staging.exists():
        shutil.rmtree(staging)
    try:
        extract_archive(archive, staging)
    except Exception as exc:  # noqa: BLE001
        shutil.rmtree(staging, ignore_errors=True)
        return ExtractResult(
            archive, False,
            f"[EXTRACT] {name}: echec 7z ({exc}) — archive conservee")

    if not verify_extract(staging, catalog):
        actual_files = [item for item in staging.rglob('*') if item.is_file()]
        actual_bytes = sum(item.stat().st_size for item in actual_files)
        shutil.rmtree(staging, ignore_errors=True)
        return ExtractResult(
            archive, False,
            f"[EXTRACT] {name}: verif KO — "
            f"{len(actual_files)} fichier(s) / {_human(actual_bytes)} "
            f"(attendu {expected}) — archive conservee")

    if dest.exists():
        shutil.rmtree(dest)
    staging.rename(dest)

    leftover = []
    for member in archive_members(archive):
        try:
            member.unlink()
        except OSError as exc:
            leftover.append(f'{member.name} ({exc})')
    if leftover:
        return ExtractResult(
            archive, False,
            f"[EXTRACT] {name} -> {dest.name}/ ({expected}) — "
            f"contenu OK mais archive non supprimee: {', '.join(leftover)}")
    return ExtractResult(
        archive, True,
        f"[EXTRACT] {name} -> {dest.name}/ ({expected}) — archive supprimee")


def extract_pending_archives(inbox, stability_seconds=300,
                             margin_bytes=DEFAULT_MARGIN_BYTES, dry_run=False):
    """Unpack every stable archive in `inbox`. Never deletes on a failed check."""
    results = []
    for archive in gather_archives(inbox, stability_seconds):
        result = _extract_one(archive, margin_bytes, dry_run)
        LOGGER.info(result.detail)
        results.append(result)
    return results
