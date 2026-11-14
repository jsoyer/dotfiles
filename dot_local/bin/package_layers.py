"""Package layers shared by previews and package-manager wrappers (stdlib only).

The catalog is also read by chezmoi's package-files template, so initial renders
do not need Python or an installed copy of this module. Existing configurations
without package_profile select legacy; new init persists base explicitly.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from dataclasses import dataclass
from pathlib import Path

PROFILES = ("base", "personal", "professional", "server", "legacy")
BREW_ENTRY = re.compile(
    r"^(brew|cask|tap|mas|go|npm|cargo|uv|krew|vscode|flatpak|winget)\s+"
    r"[\"']([^\"']+)[\"'](.*)$"
)
SAFE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+@/:-]*$")


class LayerError(ValueError):
    pass


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(content)
        if path.exists():
            os.chmod(temporary, path.stat().st_mode & 0o777)
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as error:
        raise LayerError(f"Cannot read {path}: {error}") from error


def short_hostname(host: str) -> str:
    host = host.split(".")[0]
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", host):
        raise LayerError(f"Unsafe package hostname: {host!r}")
    return host


@dataclass
class Context:
    source: Path
    machine_profile: str
    package_profile: str
    hostname: str
    install_mas: bool = False

    def __post_init__(self):
        self.source = Path(self.source)
        self.hostname = short_hostname(self.hostname)
        self.catalog = read_json(self.source / "dot_private/package-layers.json")
        if self.machine_profile not in self.catalog["profiles"]:
            raise LayerError(f"Unknown machine_profile: {self.machine_profile!r}")
        if self.package_profile not in PROFILES:
            raise LayerError(f"Unknown package_profile: {self.package_profile!r}")

    @property
    def directory(self) -> Path:
        return self.source / "dot_private"

    @property
    def managers(self) -> dict:
        return self.catalog["profiles"][self.machine_profile]["managers"]

    @property
    def exclude_file(self) -> Path:
        return self.directory / f"PackageExcludes_{self.hostname}.json"

    def exclusions(self, manager: str) -> list[str]:
        if not self.exclude_file.exists():
            return []
        data = read_json(self.exclude_file)
        if not isinstance(data, dict):
            raise LayerError(f"Expected an object in {self.exclude_file}")
        excluded = data.get(manager, [])
        if not isinstance(excluded, list) or any(
            not isinstance(x, str) for x in excluded
        ):
            raise LayerError(f"Invalid {manager} exclusions in {self.exclude_file}")
        return excluded

    def selection(self, manager: str) -> dict:
        if manager not in self.catalog["host_prefixes"]:
            raise LayerError(f"Unknown package manager: {manager!r}")
        suffix = ".json" if manager == "scoop" else ""
        host = self.catalog["host_prefixes"][manager] + self.hostname + suffix
        reserved = {
            name
            for profile in self.catalog["profiles"].values()
            for config in profile["managers"].values()
            for files in config.values()
            for name in files
        }
        reserved.update(
            name
            for files in self.catalog["legacy_brew_host_prefixes"].values()
            for name in files
        )
        reserved.update(self.catalog.get("reserved_files", []))
        if host in reserved:
            raise LayerError(
                f"Hostname {self.hostname!r} collides with shared file {host}"
            )
        config = self.managers.get(manager)
        base, usage = [], []
        if config:
            if self.package_profile == "legacy":
                base = config["legacy"]
                if manager == "brew":
                    for prefix, files in self.catalog[
                        "legacy_brew_host_prefixes"
                    ].items():
                        if self.hostname.startswith(prefix):
                            base = files
            else:
                base = config["base"]
                if self.package_profile != "base":
                    usage = config[self.package_profile]
        shared = list(dict.fromkeys(base + usage))
        files = list(shared)
        if config and (self.directory / host).is_file():
            files.append(host)
        return {
            "machine_profile": self.machine_profile,
            "package_profile": self.package_profile,
            "hostname": self.hostname,
            "manager": manager,
            "supported": config is not None,
            "base": base,
            "usage": usage,
            "shared": shared,
            "files": files,
            "host": host,
            "exclude_file": self.exclude_file.name,
            "excluded": self.exclusions(manager),
        }

    def entries(
        self, manager: str, *, shared=False, layer=None, exclusions=True
    ) -> dict:
        selection = self.selection(manager)
        files = selection["shared"] if shared else selection["files"]
        if layer:
            files = [selection["host"]] if layer == "machine" else selection[layer]
        entries = {}
        for filename in files:
            path = self.directory / filename
            if layer == "machine" and not path.exists():
                continue
            for identity, value in parse_entries(path, manager).items():
                if identity in entries and entries[identity] != value:
                    raise LayerError(f"Conflicting package {identity} in {filename}")
                entries[identity] = value
        if exclusions:
            for identity in selection["excluded"]:
                entries.pop(identity, None)
        return entries


def context_from_environment(args=None) -> Context:
    args = args or argparse.Namespace()
    context_path = Path(
        os.environ.get(
            "PACKAGE_CONTEXT_FILE",
            Path.home() / ".config/dotfiles/package-context.json",
        )
    )
    data = read_json(context_path) if context_path.exists() else {}
    if not isinstance(data, dict):
        raise LayerError(f"Expected an object in {context_path}")
    source = Path(
        getattr(args, "source", None)
        or os.environ.get("CHEZMOI_SOURCE_PATH")
        or data.get("source_dir")
        or Path.home() / ".local/share/chezmoi"
    )
    # A newly applied context takes precedence over stale values in an open shell.
    if (
        data.get("source_dir")
        and Path(data["source_dir"]).resolve() != source.resolve()
    ):
        data = {}
    mp = (
        getattr(args, "machine_profile", None)
        or data.get("machine_profile")
        or os.environ.get("MACHINE_PROFILE")
    )
    pp = next(
        (
            value
            for value in (
                getattr(args, "profile", None),
                data.get("package_profile"),
                os.environ.get("PACKAGE_PROFILE"),
            )
            if value is not None
        ),
        None,
    )
    if not mp:
        result = subprocess.run(
            ["chezmoi", "data", "--format=json"],
            capture_output=True,
            text=True,
            check=True,
        )
        chezmoi_data = json.loads(result.stdout)
        mp = chezmoi_data.get("machine_profile")
        if pp is None:
            pp = chezmoi_data.get("package_profile")
    return Context(
        source,
        mp or "",
        "legacy" if pp is None else pp,
        getattr(args, "hostname", None) or data.get("hostname") or platform.node(),
        bool(data.get("install_mas", False)),
    )


def parse_entries(path: Path, manager: str) -> dict:
    if manager == "scoop":
        data = read_json(path)
        if (
            not isinstance(data, dict)
            or not isinstance(data.get("apps"), list)
            or not isinstance(data.get("buckets"), list)
        ):
            raise LayerError(f"Invalid Scoop manifest: {path}")
        entries = {}
        for kind in ("buckets", "apps"):
            for item in data[kind]:
                if not isinstance(item, dict) or not isinstance(item.get("name"), str):
                    raise LayerError(f"Invalid Scoop {kind} in {path}")
                key = f"bucket:{item['name']}" if kind == "buckets" else item["name"]
                if key in entries and entries[key] != item:
                    raise LayerError(f"Conflicting Scoop entry {key} in {path}")
                entries[key] = item
        return entries
    entries = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if manager == "brew":
            match = BREW_ENTRY.fullmatch(line)
            if not match:
                raise LayerError(f"Unsupported Brewfile declaration in {path}: {line}")
            identity = f"{match[1]}:{match[2]}"
            value = re.sub(r"\s+#.*$", "", line).strip()
        elif manager == "snap":
            parts = shlex.split(line)
            if (
                not parts
                or not SAFE_NAME.fullmatch(parts[0])
                or any(not x.startswith("--") for x in parts[1:])
            ):
                raise LayerError(f"Invalid Snap declaration in {path}: {line}")
            identity, value = parts[0], line
        else:
            if not SAFE_NAME.fullmatch(line):
                raise LayerError(f"Invalid {manager} package in {path}: {line}")
            identity, value = line, line
        if identity in entries and entries[identity] != value:
            raise LayerError(f"Conflicting package {identity} in {path}")
        entries[identity] = value
    return entries


def serialize_entries(entries: dict, manager: str) -> str:
    if manager == "scoop":
        return (
            json.dumps(
                {
                    "buckets": [
                        v for k, v in entries.items() if k.startswith("bucket:")
                    ],
                    "apps": [
                        v for k, v in entries.items() if not k.startswith("bucket:")
                    ],
                },
                indent=2,
                ensure_ascii=False,
            )
            + "\n"
        )
    return "\n".join(entries.values()) + ("\n" if entries else "")


def entry_identity(manager: str, name: str, entries: dict | None = None) -> str:
    if not SAFE_NAME.fullmatch(name):
        raise LayerError(f"Invalid package name: {name!r}")
    if manager != "brew" or ":" in name:
        return name
    matches = [key for key in (entries or {}) if key.split(":", 1)[-1] == name]
    if len(matches) > 1:
        raise LayerError(
            f"Ambiguous package {name}; specify brew:{name} or cask:{name}"
        )
    return matches[0] if matches else f"brew:{name}"


def record(context: Context, manager: str, action: str, names: list[str]) -> list[Path]:
    selection = context.selection(manager)
    if not selection["supported"]:
        raise LayerError(f"{manager} is not supported by {context.machine_profile}")
    host = context.directory / selection["host"]
    local = parse_entries(host, manager) if host.exists() else {}
    shared = context.entries(manager, shared=True, exclusions=False)
    exclude_data = (
        read_json(context.exclude_file) if context.exclude_file.exists() else {}
    )
    excluded = context.exclusions(manager)
    for name in names:
        identity = entry_identity(manager, name, shared | local)
        if action == "remove":
            local.pop(identity, None)
            if identity in shared and identity not in excluded:
                excluded.append(identity)
        else:
            excluded = [key for key in excluded if key != identity]
            if identity not in shared:
                if manager == "brew":
                    kind, value = identity.split(":", 1)
                    local[identity] = f'{kind} "{value}"'
                elif manager == "scoop":
                    local[identity] = {"name": name}
                else:
                    local[identity] = name
    changed = []
    content = serialize_entries(local, manager)
    if (host.exists() and host.read_text(encoding="utf-8-sig") != content) or (
        not host.exists() and local
    ):
        atomic_write(host, content)
        changed.append(host)
    if sorted(excluded) != sorted(exclude_data.get(manager, [])):
        exclude_data[manager] = sorted(excluded)
        atomic_write(context.exclude_file, json.dumps(exclude_data, indent=2) + "\n")
        changed.append(context.exclude_file)
    return changed


def dump_overlay(context: Context, manager: str, installed: dict) -> list[Path]:
    selection = context.selection(manager)
    shared = context.entries(manager, shared=True, exclusions=False)
    excluded = context.exclusions(manager)
    local = {
        key: value
        for key, value in installed.items()
        if key not in shared and key not in excluded
    }
    host = context.directory / selection["host"]
    if manager == "brew" and host.exists():
        # brew bundle dump may omit npm/go/cargo. Keep declarations it cannot manage.
        for key, value in parse_entries(host, manager).items():
            if (
                key.split(":", 1)[0] not in ("brew", "cask", "tap", "mas")
                and key not in excluded
            ):
                local.setdefault(key, value)
    atomic_write(host, serialize_entries(local, manager))
    return [host]


def clear_exclusions(context: Context, names: list[str]) -> list[Path]:
    """An unqualified brew install can resolve to a cask; do not invent its type."""
    if not context.exclude_file.exists():
        return []
    data = read_json(context.exclude_file)
    excluded = context.exclusions("brew")
    kept = [
        key
        for key in excluded
        if not any(
            key == name or (":" not in name and key.split(":", 1)[-1] == name)
            for name in names
        )
    ]
    if kept == excluded:
        return []
    data["brew"] = kept
    atomic_write(context.exclude_file, json.dumps(data, indent=2) + "\n")
    return [context.exclude_file]


def promote(context: Context, manager: str, name: str, target: str) -> list[Path]:
    selection = context.selection(manager)
    if context.package_profile == "legacy":
        raise LayerError(
            "Choose a package_profile before promoting; legacy lists are read-only"
        )
    files = selection[target]
    if not files:
        raise LayerError(f"No {target} layer for {manager}/{context.package_profile}")
    host = context.directory / selection["host"]
    local = parse_entries(host, manager)
    identity = entry_identity(manager, name, local)
    if identity not in local:
        raise LayerError(f"{name} is not declared in {host.name}")
    destination = context.directory / files[-1]
    entries = parse_entries(destination, manager)
    value = local.pop(identity)
    if identity in entries and entries[identity] != value:
        raise LayerError(
            f"Conflicting declaration for {identity} in {destination.name}"
        )
    entries[identity] = value
    previous = destination.read_text(encoding="utf-8")
    try:
        atomic_write(destination, serialize_entries(entries, manager))
        atomic_write(host, serialize_entries(local, manager))
    except OSError:
        atomic_write(destination, previous)
        raise
    print(
        f"Promoted {identity} to {destination.name} ({target}; shared by matching machines)",
        file=sys.stderr,
    )
    return [host, destination]


def sync_manifests(context: Context, paths: list[Path], message: str) -> None:
    """Commit only owned paths, even if the user has other staged changes."""
    paths = list(dict.fromkeys(str(p.resolve()) for p in paths))
    if not paths:
        return
    status = subprocess.run(
        ["git", "status", "--porcelain", "--", *paths],
        cwd=context.source,
        check=True,
        capture_output=True,
        text=True,
    )
    if not status.stdout.strip():
        return
    subprocess.run(["git", "add", "--", *paths], cwd=context.source, check=True)
    subprocess.run(
        ["git", "commit", "--only", "-m", message, "--", *paths],
        cwd=context.source,
        check=True,
    )
    subprocess.run(["git", "push"], cwd=context.source, check=True)


def installed_entries(context: Context, manager: str) -> dict:
    def query(*args):
        return subprocess.run(args, check=True, capture_output=True, text=True).stdout

    if manager == "apt":
        names = query("apt-mark", "showmanual").splitlines()
    elif manager == "dnf":
        binary = "dnf" if shutil.which("dnf") else "yum"
        names = query(
            binary, "repoquery", "--userinstalled", "--queryformat", "%{name}\n"
        ).splitlines()
    elif manager in ("pacman", "aur"):
        foreign = set(query("pacman", "-Qqem").splitlines())
        names = (
            foreign
            if manager == "aur"
            else set(query("pacman", "-Qqe").splitlines()) - foreign
        )
    elif manager == "flatpak":
        scope = "--system" if context.machine_profile == "fedora-atomic" else "--user"
        names = query(
            "flatpak", "list", scope, "--app", "--columns=application"
        ).splitlines()
    elif manager == "rpm":
        deployments = json.loads(query("rpm-ostree", "status", "--json"))["deployments"]
        names = deployments[0].get("requested-packages", [])
    elif manager == "snap":
        names = [
            line.split()[0]
            for line in query("snap", "list").splitlines()[1:]
            if line.strip()
        ]
    else:
        raise LayerError(f"No inventory command for {manager}")
    entries = {}
    for name in sorted(set(names)):
        if not SAFE_NAME.fullmatch(name):
            raise LayerError(
                f"Invalid package returned by {manager}: {name!r}; manifest left unchanged"
            )
        entries[name] = name
    return entries


def wrapper(context: Context, manager: str, arguments: list[str]) -> int:
    """Native commands keep their syntax; only successful mutations record a delta."""
    if arguments[:1] == ["--"]:
        arguments = arguments[1:]
    selection = context.selection(manager)
    if not selection["supported"]:
        raise LayerError(f"{manager} is not supported by {context.machine_profile}")
    if arguments[:1] in (["--help"], ["-h"]):
        print(
            f"{manager} wrapper: native command syntax; installs are recorded for {context.hostname} only."
        )
        print(
            "Use package-plan preview, or package-plan promote --manager "
            + manager
            + " NAME --to base|usage"
        )
        return 0
    if manager == "aur" and hasattr(os, "geteuid") and os.geteuid() == 0:
        raise LayerError(
            "yay must not run as root; run the AUR wrapper as your regular user"
        )
    if arguments[:1] == ["dump"]:
        installed = installed_entries(
            context, manager
        )  # no writes on inventory failure
        paths = dump_overlay(context, manager, installed)
        sync_manifests(
            context,
            paths,
            f"feat({manager}w): update {context.hostname} package inventory",
        )
        return 0
    binaries = {
        "apt": ["sudo", "apt-get"],
        "dnf": ["sudo", "dnf" if shutil.which("dnf") else "yum"],
        "pacman": ["sudo", "pacman"],
        "aur": ["yay"],
        "rpm": ["sudo", "rpm-ostree"],
        "flatpak": ["flatpak"],
        "snap": ["sudo", "snap"],
    }
    command = binaries[manager]
    if not arguments:
        return subprocess.run(command).returncode
    operation, rest = arguments[0], arguments[1:]
    action = None
    if manager in ("pacman", "aur"):
        if operation == "--sync" or re.fullmatch(r"-S[yuw]*", operation):
            action = "add"
        elif operation in ("-R", "-Rs", "-Rns", "--remove"):
            action = "remove"
    elif operation in ("install", "remove", "uninstall", "purge"):
        action = "add" if operation == "install" else "remove"
    names, skip_value = [], False
    value_flags = {
        "--enablerepo",
        "--disablerepo",
        "--releasever",
        "--config",
        "--channel",
        "--revision",
        "--arch",
    }
    for value in rest:
        if skip_value:
            skip_value = False
        elif value in value_flags:
            skip_value = True
        elif not value.startswith("-"):
            names.append(value)
    if action and (
        any(
            flag in rest
            for flag in (
                "--downloadonly",
                "--download-only",
                "--simulate",
                "--dry-run",
                "-s",
                "-w",
            )
        )
        or (manager in ("pacman", "aur") and "w" in operation)
    ):
        action = None  # download/simulation must not claim packages were installed
    if manager in ("pacman", "aur") and not names:
        action = None  # e.g. a normal -Syu system upgrade
    if manager == "flatpak" and names[:1] == ["flathub"]:
        names = names[1:]
    if action:
        if not names:
            raise LayerError(f"{operation} requires a package name")
        for name in names:
            if not SAFE_NAME.fullmatch(name) or name.startswith("-") or "/" in name:
                raise LayerError(f"Invalid package name: {name!r}")
            if manager == "flatpak" and not re.fullmatch(
                r"[A-Za-z][A-Za-z0-9_-]*(\.[A-Za-z][A-Za-z0-9_-]*){2,}", name
            ):
                raise LayerError(f"Invalid Flatpak application ID: {name!r}")
        # Validate shared declarations and exclusions before changing installed packages.
        context.entries(manager)
        if any(
            flag.split("=", 1)[0]
            in ("--root", "--installroot", "--dbpath", "--sysroot")
            for flag in rest
        ):
            raise LayerError(
                "Use the native manager for an alternate installation root; host manifests were not changed"
            )
    if manager == "apt" and operation in (
        "search",
        "show",
        "list",
        "depends",
        "rdepends",
    ):
        command = ["apt"]
    elif manager == "apt" and action:
        arguments = [operation, "-y", *rest]
    elif manager == "flatpak" and action:
        scope = "--system" if context.machine_profile == "fedora-atomic" else "--user"
        other_scope = "--user" if scope == "--system" else "--system"
        if other_scope in rest:
            raise LayerError(
                f"This machine records {scope} Flatpak applications; use native flatpak for another scope"
            )
        arguments = [operation, scope, "-y", *[x for x in rest if x != scope]]
    result = subprocess.run([*command, *arguments])
    if result.returncode:
        return result.returncode
    if action:
        paths = record(context, manager, action, names)
        if manager == "snap" and action == "add":
            flags = []
            index = 0
            while index < len(rest):
                flag = rest[index]
                if flag in ("--channel", "--revision"):
                    if index + 1 >= len(rest):
                        raise LayerError(f"Missing value for {flag}")
                    flags.append(f"{flag}={rest[index + 1]}")
                    index += 2
                else:
                    if flag.startswith("--"):
                        flags.append(flag)
                    index += 1
            if flags:
                host = context.directory / selection["host"]
                entries = parse_entries(host, manager) if host.exists() else {}
                for name in names:
                    if name in entries:
                        entries[name] = " ".join([name, *flags])
                if entries:
                    atomic_write(host, serialize_entries(entries, manager))
                    paths.append(host)
        sync_manifests(
            context,
            paths,
            f"feat({manager}w): {action} {' '.join(names)} on {context.hostname}",
        )
    return 0


def migrate(context: Context, target_profile: str, *, write=False, config=None) -> dict:
    """Preserve this machine's declared intent, with a preview before explicit writes.

    Other hosts' files are never consulted. Installed state may contain additional
    packages; wrappers' explicit dump commands can capture those before migration.
    """
    target = Context(
        context.source,
        context.machine_profile,
        target_profile,
        context.hostname,
        context.install_mas,
    )
    report = {
        "hostname": context.hostname,
        "from": context.package_profile,
        "to": target_profile,
        "inventory": "declared packages (not an installed-state audit)",
        "managers": {},
    }
    updates = {}
    for manager in context.managers:
        old_entries = context.entries(manager)
        shared = target.entries(manager, shared=True)
        conflicts = [
            key
            for key in old_entries.keys() & shared.keys()
            if old_entries[key] != shared[key]
        ]
        if conflicts:
            raise LayerError(
                f"Migration would change {manager} options for {', '.join(conflicts)}; reconcile them first"
            )
        local = {key: value for key, value in old_entries.items() if key not in shared}
        filename = target.selection(manager)["host"]
        updates[target.directory / filename] = serialize_entries(local, manager)
        report["managers"][manager] = {
            "host_file": filename,
            "preserved": len(local),
            "added_by_base_or_usage": sorted(set(shared) - set(old_entries)),
            "removed": [],
        }
    if not write:
        return report
    if config is None:
        result = subprocess.run(
            ["chezmoi", "execute-template", "{{ .chezmoi.configFile }}"],
            capture_output=True,
            text=True,
            check=True,
        )
        config = Path(result.stdout.strip())
    config = Path(config)
    if not config.is_file():
        raise LayerError(f"Chezmoi config does not exist: {config}")
    old_config = config.read_text(encoding="utf-8")
    lines = old_config.splitlines(keepends=True)
    in_data, insertion, matches = False, None, []
    for i, line in enumerate(lines):
        if line.strip().startswith("["):
            in_data = line.strip() == "[data]"
            if in_data:
                if insertion is not None:
                    raise LayerError(
                        "Duplicate [data] table; migrate package_profile manually"
                    )
                insertion = i + 1
        elif in_data and re.match(r"\s*package_profile\s*=", line):
            matches.append(i)
    if insertion is None or len(matches) > 1:
        raise LayerError("Cannot safely locate package_profile in [data]")
    value = f'    package_profile = "{target_profile}"\n'
    if matches:
        lines[matches[0]] = value
    else:
        lines.insert(insertion, value)
    updates[config] = "".join(lines)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    backup_dir = config.parent / "package-layer-backups" / stamp
    backup_dir.mkdir(parents=True, mode=0o700)
    originals = {}
    for path in updates:
        originals[path] = path.read_text(encoding="utf-8") if path.exists() else None
        if path.exists():
            shutil.copy2(path, backup_dir / path.name)
    atomic_write(
        backup_dir / "migration.json",
        json.dumps(
            {
                "report": report,
                "restore": {
                    str(path.resolve()): path.name if old is not None else None
                    for path, old in originals.items()
                },
            },
            indent=2,
        )
        + "\n",
    )
    try:
        for path, content in updates.items():
            atomic_write(path, content)
    except OSError:
        for path, previous in originals.items():
            if previous is None:
                path.unlink(missing_ok=True)
            else:
                atomic_write(path, previous)
        raise
    report["backup"] = str(backup_dir)
    print(
        "Migration saved. Run chezmoi apply, then open a new shell. Review and commit the host manifests.",
        file=sys.stderr,
    )
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Preview and manage base + usage + machine package layers"
    )
    parser.add_argument("--source", type=Path)
    parser.add_argument("--machine-profile")
    parser.add_argument("--profile", choices=PROFILES)
    parser.add_argument("--hostname")
    commands = parser.add_subparsers(dest="command")
    for command in (
        "preview",
        "files",
        "names",
        "manifest",
        "record",
        "promote",
        "wrapper",
    ):
        child = commands.add_parser(command)
        child.add_argument("--manager")
        if command in ("files", "names", "manifest"):
            child.add_argument("--shared", action="store_true")
        if command == "preview":
            child.add_argument("--json", action="store_true")
        if command == "record":
            child.add_argument("action", choices=("add", "remove"))
            child.add_argument("names", nargs="+")
        if command == "promote":
            child.add_argument("name")
            child.add_argument("--to", choices=("base", "usage"), required=True)
        if command == "wrapper":
            child.add_argument("arguments", nargs=argparse.REMAINDER)
    migration = commands.add_parser("migrate")
    migration.add_argument("--to", choices=PROFILES[:-1], required=True)
    migration.add_argument("--write", action="store_true")
    migration.add_argument("--config", type=Path)
    args = parser.parse_args(argv)
    try:
        context = context_from_environment(args)
        command = args.command or "preview"
        manager = getattr(args, "manager", None)
        if command not in ("preview", "migrate") and not manager:
            raise LayerError("--manager is required")
        if command == "preview":
            plans = []
            for manager in [manager] if manager else context.managers:
                selection = context.selection(manager)
                entries = context.entries(manager)
                selection["count"] = len(
                    [key for key in entries if not key.startswith("bucket:")]
                )
                selection["packages"] = entries
                origins = {}
                for filename in selection["files"]:
                    for key in parse_entries(context.directory / filename, manager):
                        if key in entries:
                            origins.setdefault(key, []).append(filename)
                selection["origins"] = origins
                selection["install_mas"] = context.install_mas
                plans.append(selection)
            if getattr(args, "json", False):
                print(json.dumps(plans, indent=2, ensure_ascii=False))
            else:
                print(
                    f"{context.hostname}: {context.machine_profile}, packages={context.package_profile}"
                )
                for plan in plans:
                    print(f"\n{plan['manager']}: {plan['count']} declarations")
                    for name in plan["files"]:
                        layer = (
                            "base"
                            if name in plan["base"]
                            else "usage"
                            if name in plan["usage"]
                            else "machine"
                        )
                        print(f"  {layer}: {name}")
                    if plan["excluded"]:
                        print("  excluded: " + ", ".join(plan["excluded"]))
        elif command == "files":
            selection = context.selection(manager)
            for name in selection["shared" if args.shared else "files"]:
                print(context.directory / name)
        elif command in ("names", "manifest"):
            entries = context.entries(manager, shared=args.shared)
            if command == "manifest":
                if manager == "brew" and not context.install_mas:
                    entries = {
                        key: value
                        for key, value in entries.items()
                        if not key.startswith("mas:")
                    }
                print(serialize_entries(entries, manager), end="")
            else:
                print(
                    "\n".join(
                        sorted(key for key in entries if not key.startswith("bucket:"))
                    )
                )
        elif command == "record":
            for path in record(context, manager, args.action, args.names):
                print(path)
        elif command == "promote":
            for path in promote(context, manager, args.name, args.to):
                print(path)
        elif command == "wrapper":
            return wrapper(context, manager, args.arguments)
        elif command == "migrate":
            print(
                json.dumps(
                    migrate(context, args.to, write=args.write, config=args.config),
                    indent=2,
                )
            )
        return 0
    except (LayerError, OSError, subprocess.SubprocessError, ValueError) as error:
        print(f"package-plan: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
