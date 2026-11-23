"""Package layers shared by previews and package-manager wrappers (stdlib only).

The catalog is also read by chezmoi's package-files template, so initial renders
do not need Python or an installed copy of this module. Existing configurations
without package_profile select legacy; new init persists base explicitly.
"""

from __future__ import annotations

import argparse
import difflib
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
PACKAGE_USAGES = ("base", "personal", "professional", "server")
BREW_ENTRY = re.compile(
    r"^(brew|cask|tap|mas|go|npm|cargo|uv|krew|vscode|flatpak|winget)\s+"
    r"[\"']([^\"']+)[\"'](.*)$"
)
SAFE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+@/:-]*$")
_VISUAL_TUI = False


def base_profile_name(machine_profile: str, package_profile: str) -> str:
    """Show the selected system and usage combination as one base profile."""
    if machine_profile == "mac-personal" and package_profile in (
        "base",
        "personal",
        "legacy",
    ):
        return "mac-personal"
    if machine_profile == "mac-pro" and package_profile in (
        "base",
        "professional",
        "legacy",
    ):
        return "mac-professional"
    if package_profile in ("base", "legacy") or machine_profile.endswith(
        f"-{package_profile}"
    ):
        return machine_profile
    return f"{machine_profile}-{package_profile}"


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
    target_kind: str | None = None

    def __post_init__(self):
        self.source = Path(self.source)
        self.hostname = short_hostname(self.hostname)
        self.catalog = read_json(self.source / "dot_private/package-layers.json")
        self.machine_profile = self.catalog.get("profile_aliases", {}).get(
            self.machine_profile, self.machine_profile
        )
        if self.machine_profile not in self.catalog["profiles"]:
            raise LayerError(f"Unknown machine_profile: {self.machine_profile!r}")
        if self.package_profile not in PROFILES:
            raise LayerError(f"Unknown package_profile: {self.package_profile!r}")
        if self.target_kind is None:
            self.target_kind = self.catalog["profiles"][self.machine_profile].get(
                "target_kind", "host"
            )
        if self.target_kind not in ("host", "container"):
            raise LayerError(f"Unknown target_kind: {self.target_kind!r}")

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
            "target_kind": self.target_kind,
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
    hostname = short_hostname(
        getattr(args, "hostname", None) or data.get("hostname") or platform.node()
    )
    registered = {}
    registry_path = machine_registry(source)
    if registry_path.exists():
        registry = read_json(registry_path)
        if not isinstance(registry, dict) or not isinstance(
            registry.get("machines"), dict
        ):
            raise LayerError(f"Invalid machine registry: {registry_path}")
        registered = next(
            (
                value
                for key, value in registry["machines"].items()
                if key.casefold() == hostname.casefold()
            ),
            {},
        )
        if not isinstance(registered, dict):
            raise LayerError(
                f"Invalid machine entry for {hostname!r} in {registry_path}"
            )
    mp = (
        getattr(args, "machine_profile", None)
        or registered.get("machine_profile")
        or data.get("machine_profile")
        or os.environ.get("MACHINE_PROFILE")
    )
    pp = next(
        (
            value
            for value in (
                getattr(args, "profile", None),
                registered.get("package_profile"),
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
            encoding="utf-8",
        )
        chezmoi_data = json.loads(result.stdout)
        mp = chezmoi_data.get("machine_profile")
        if pp is None:
            pp = chezmoi_data.get("package_profile")
    return Context(
        source,
        mp or "",
        "legacy" if pp is None else pp,
        hostname,
        bool(data.get("install_mas", False)),
        registered.get("target_kind"),
    )


def machine_registry(source: Path) -> Path:
    return Path(source) / "dot_private/package-machines.json"


def _visual_menu(prompt: str, options: list[str], default: int = 0) -> str:
    """Render a keyboard-navigable full-screen selection menu with curses."""
    import curses

    def draw(screen):
        curses.curs_set(0)
        if curses.has_colors():
            curses.start_color()
            curses.use_default_colors()
            curses.init_pair(1, curses.COLOR_CYAN, -1)
            curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_CYAN)
        selected = max(0, min(default, len(options) - 1))
        first = 0
        while True:
            screen.erase()
            height, width = screen.getmaxyx()
            screen.addnstr(
                1,
                2,
                "DOTFILES  /  GESTION DES PAQUETS",
                width - 4,
                curses.color_pair(1) | curses.A_BOLD
                if curses.has_colors()
                else curses.A_BOLD,
            )
            screen.addnstr(3, 2, prompt, width - 4, curses.A_BOLD)
            visible = max(1, height - 7)
            if selected < first:
                first = selected
            elif selected >= first + visible:
                first = selected - visible + 1
            for row, index in enumerate(
                range(first, min(len(options), first + visible)), 5
            ):
                attr = (
                    curses.A_REVERSE | curses.A_BOLD
                    if index == selected
                    else curses.A_NORMAL
                )
                if index == selected and curses.has_colors():
                    attr |= curses.color_pair(2)
                screen.addnstr(
                    row,
                    2,
                    ("› " if index == selected else "  ") + options[index],
                    width - 4,
                    attr,
                )
            screen.addnstr(
                height - 2,
                2,
                "↑/↓ choisir   Entrée valider   Échap = choix par défaut",
                width - 4,
            )
            screen.refresh()
            key = screen.getch()
            if key in (curses.KEY_UP, ord("k")):
                selected = (selected - 1) % len(options)
            elif key in (curses.KEY_DOWN, ord("j")):
                selected = (selected + 1) % len(options)
            elif key == curses.KEY_HOME:
                selected = 0
            elif key == curses.KEY_END:
                selected = len(options) - 1
            elif key == curses.KEY_NPAGE:
                selected = min(len(options) - 1, selected + visible)
            elif key == curses.KEY_PPAGE:
                selected = max(0, selected - visible)
            elif key in (curses.KEY_ENTER, 10, 13):
                return options[selected]
            elif key == 27:
                return options[default]

    return curses.wrapper(draw)


def _visual_checklist(
    title: str,
    labels: dict[str, str],
    selected: set[str],
    *,
    filter_text: str = "",
) -> tuple[set[str], str]:
    """Return selected entries and an action: save, add, or cancel."""
    import curses

    keys = list(labels)

    def draw(screen):
        curses.curs_set(0)
        cursor = 0
        first = 0
        query = filter_text
        while True:
            visible_keys = [
                key
                for key in keys
                if query.casefold() in labels[key].casefold()
                or query.casefold() in key.casefold()
            ]
            cursor = max(0, min(cursor, len(visible_keys) - 1)) if visible_keys else 0
            screen.erase()
            height, width = screen.getmaxyx()
            screen.addnstr(
                1, 2, "DOTFILES  /  GESTION DES PAQUETS", width - 4, curses.A_BOLD
            )
            screen.addnstr(3, 2, title, width - 4, curses.A_BOLD)
            if query:
                screen.addnstr(4, 2, f"Filtre : {query}", width - 4)
            visible = max(1, height - 9)
            if cursor < first:
                first = cursor
            elif cursor >= first + visible:
                first = cursor - visible + 1
            for row, index in enumerate(
                range(first, min(len(visible_keys), first + visible)), 6
            ):
                key = visible_keys[index]
                marker = "[x]" if key in selected else "[ ]"
                text = f"{marker} {labels[key]}"
                attr = (
                    curses.A_REVERSE | curses.A_BOLD
                    if index == cursor
                    else curses.A_NORMAL
                )
                screen.addnstr(row, 2, text, width - 4, attr)
            screen.addnstr(
                height - 2,
                2,
                "↑↓ déplacer Space cocher / filtre a+ *=tout -=rien Entrée valider Esc annuler",
                width - 4,
            )
            screen.refresh()
            keypress = screen.getch()
            if keypress in (curses.KEY_UP, ord("k")) and visible_keys:
                cursor = (cursor - 1) % len(visible_keys)
            elif keypress in (curses.KEY_DOWN, ord("j")) and visible_keys:
                cursor = (cursor + 1) % len(visible_keys)
            elif keypress == curses.KEY_HOME:
                cursor = 0
            elif keypress == curses.KEY_END and visible_keys:
                cursor = len(visible_keys) - 1
            elif keypress == curses.KEY_NPAGE and visible_keys:
                cursor = min(len(visible_keys) - 1, cursor + visible)
            elif keypress == curses.KEY_PPAGE and visible_keys:
                cursor = max(0, cursor - visible)
            elif keypress == ord(" ") and visible_keys:
                identity = visible_keys[cursor]
                if identity in selected:
                    selected.remove(identity)
                else:
                    selected.add(identity)
            elif keypress == ord("*"):
                selected.update(visible_keys)
            elif keypress == ord("-"):
                selected.difference_update(visible_keys)
            elif keypress == ord("/"):
                curses.echo()
                curses.curs_set(1)
                screen.addnstr(height - 3, 2, "Filtrer : ", width - 4)
                screen.refresh()
                raw = screen.getstr(height - 3, 12, max(1, width - 14))
                query = raw.decode("utf-8", errors="replace").strip()
                curses.noecho()
                curses.curs_set(0)
                cursor = first = 0
            elif keypress == ord("a"):
                return set(selected), "add"
            elif keypress in (curses.KEY_ENTER, 10, 13):
                return set(selected), "save"
            elif keypress in (27, ord("q")):
                return set(selected), "cancel"

    return curses.wrapper(draw)


def select_packages(
    title: str,
    manager: str,
    entries: dict,
    origins: dict[str, list[str]] | None = None,
) -> tuple[set[str] | None, dict[str, str]]:
    """Checkbox editor for a package selection; additions are entered by name."""
    selected = set(entries)
    added: dict[str, str] = {}
    labels = {
        identity: f"{identity}"
        + (f"  ·  {', '.join((origins or {}).get(identity, []))}" if origins else "")
        for identity in sorted(entries)
    }
    while True:
        if _VISUAL_TUI and sys.stdin.isatty() and sys.stdout.isatty():
            try:
                selected, action = _visual_checklist(title, labels, selected)
            except Exception:
                action = "fallback"
        else:
            action = "fallback"
        if action == "fallback":
            print(f"\n{title} — coche les numéros à basculer, Entrée termine")
            visible = sorted(labels)
            for index, identity in enumerate(visible, 1):
                marker = "x" if identity in selected else " "
                print(f"  {index:>3}. [{marker}] {labels[identity]}")
            answer = input(
                "Numéros séparés par des virgules (a=ajouter, q=annuler): "
            ).strip()
            if not answer:
                action = "save"
            elif answer.lower() == "q":
                return None, {}
            elif answer.lower() == "a":
                action = "add"
            else:
                try:
                    for item in answer.split(","):
                        index = int(item.strip()) - 1
                        identity = visible[index]
                        selected.symmetric_difference_update({identity})
                except (ValueError, IndexError):
                    print("Sélection invalide.")
                    continue
                continue
        if action == "cancel":
            return None, {}
        if action == "save":
            return selected, added
        if action == "add":
            name = prompt_text("Nom du paquet (Homebrew : formule ou cask:nom) : ")
            if not name:
                continue
            identity = entry_identity(manager, name, entries)
            selected.add(identity)
            labels.setdefault(identity, identity)
            added[identity] = name


def choose(prompt: str, options: list[str], *, default: int = 0) -> str:
    """Choose in a visual terminal menu when TUI mode is active."""
    if not options:
        raise LayerError(f"No choices available for {prompt.lower()}")
    if _VISUAL_TUI and sys.stdin.isatty() and sys.stdout.isatty():
        try:
            return _visual_menu(prompt, options, default)
        except Exception:
            pass
    while True:
        print(f"\n{prompt}")
        for number, option in enumerate(options, 1):
            marker = " (par défaut)" if number - 1 == default else ""
            print(f"  {number}. {option}{marker}")
        answer = input(f"Choix [1-{len(options)}, défaut {default + 1}]: ").strip()
        if not answer:
            return options[default]
        if answer.isdigit() and 1 <= int(answer) <= len(options):
            return options[int(answer) - 1]
        print("Choisis l'un des numéros affichés.")


def confirm(prompt: str, *, default: bool = False) -> bool:
    if _VISUAL_TUI and sys.stdin.isatty() and sys.stdout.isatty():
        return choose(prompt, ["Oui", "Non"], default=0 if default else 1) == "Oui"
    suffix = "O/n" if default else "o/N"
    while True:
        answer = input(f"{prompt} [{suffix}] ").strip().lower()
        if not answer:
            return default
        if answer in ("y", "yes", "o", "oui"):
            return True
        if answer in ("n", "no", "non"):
            return False
        print("Réponds par oui ou non.")


def prompt_text(prompt: str, *, default: str = "") -> str:
    if _VISUAL_TUI and sys.stdin.isatty() and sys.stdout.isatty():
        try:
            import curses

            def draw(screen):
                curses.curs_set(1)
                screen.erase()
                height, width = screen.getmaxyx()
                screen.addnstr(
                    2, 2, "DOTFILES  /  GESTION DES PAQUETS", width - 4, curses.A_BOLD
                )
                label = f"{prompt} [{default}]" if default else prompt
                screen.addnstr(4, 2, label, width - 4)
                screen.addnstr(6, 2, "> ", width - 4, curses.A_BOLD)
                screen.refresh()
                value = screen.getstr(6, 4, max(1, width - 6))
                answer = value.decode("utf-8", errors="replace").strip()
                return answer or default

            return curses.wrapper(draw)
        except Exception:
            pass
    answer = input(f"{prompt} [{default}]: " if default else prompt).strip()
    return answer or default


def _visual_view(title: str, content: str) -> None:
    import curses

    lines = content.splitlines() or [""]

    def draw(screen):
        curses.curs_set(0)
        offset = 0
        while True:
            screen.erase()
            height, width = screen.getmaxyx()
            screen.addnstr(1, 2, title, width - 4, curses.A_BOLD)
            visible = max(1, height - 5)
            for row, line in enumerate(lines[offset : offset + visible], 3):
                screen.addnstr(row, 2, line, width - 4)
            screen.addnstr(
                height - 2, 2, "↑/↓ défiler   Entrée/Échap continuer", width - 4
            )
            screen.refresh()
            key = screen.getch()
            if key in (curses.KEY_UP, ord("k")):
                offset = max(0, offset - 1)
            elif key in (curses.KEY_DOWN, ord("j")):
                offset = min(max(0, len(lines) - visible), offset + 1)
            elif key == curses.KEY_PPAGE:
                offset = max(0, offset - visible)
            elif key == curses.KEY_NPAGE:
                offset = min(max(0, len(lines) - visible), offset + visible)
            elif key in (curses.KEY_ENTER, 10, 13, 27):
                return

    curses.wrapper(draw)


def show_file_changes(source: Path, updates: dict[Path, str]) -> None:
    sections = []
    for path, content in updates.items():
        before = path.read_text(encoding="utf-8-sig") if path.exists() else ""
        diff = difflib.unified_diff(
            before.splitlines(keepends=True),
            content.splitlines(keepends=True),
            fromfile=f"{path.relative_to(source)} (avant)",
            tofile=f"{path.relative_to(source)} (après)",
        )
        rendered = "".join(diff)
        sections.append(rendered or f"{path.relative_to(source)}: aucune différence")
    content = "\n".join(sections)
    if _VISUAL_TUI and sys.stdin.isatty() and sys.stdout.isatty():
        try:
            _visual_view("Aperçu des changements", content)
            return
        except Exception:
            pass
    print(content)


def configure_machine(
    source: Path,
    host: str | None = None,
    *,
    replace_existing: bool = False,
    allow_legacy: bool = False,
    changed_paths: list[Path] | None = None,
) -> Context | None:
    """Register a machine's package layers without installing any software."""
    source = Path(source)
    catalog = read_json(source / "dot_private/package-layers.json")
    profiles = catalog["profiles"]
    host = (host or prompt_text("Nom court de la machine : ")).split(".", 1)[0]
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", host):
        raise LayerError(f"Nom de machine invalide : {host!r}")
    discovered = discover_machine_manifests(source)
    matched_host = next(
        (name for name in discovered if name.casefold() == host.casefold()), None
    )
    if matched_host:
        host = matched_host

    labels = {
        "mac-personal": "macOS — personnel",
        "mac-pro": "macOS — professionnel",
        "ubuntu-desktop": "Linux — Ubuntu avec bureau",
        "ubuntu-server": "Linux — Ubuntu serveur",
        "debian": "Linux — Debian",
        "rpi": "Linux — Raspberry Pi / Debian",
        "fedora-desktop": "Linux — Fedora avec bureau",
        "fedora-server": "Linux — Fedora serveur",
        "toolbox": "Linux — Fedora Toolbox",
        "fedora-atomic": "Linux — Fedora Atomic",
        "arch-desktop": "Linux — Arch avec bureau",
        "arch-server": "Linux — Arch serveur",
        "omarchy": "Linux — Omarchy",
        "alpine": "Linux — Alpine",
        "arch-container": "Linux — Arch en conteneur",
        "freebsd": "BSD — FreeBSD",
        "windows": "Windows",
    }
    groups = {}
    for key, config in profiles.items():
        groups.setdefault(config["os"], []).append(key)
    os_names = {
        "darwin": "macOS",
        "linux": "Linux",
        "freebsd": "BSD",
        "windows": "Windows",
    }
    os_keys = sorted(
        groups,
        key=lambda key: {"darwin": 0, "linux": 1, "freebsd": 2, "windows": 3}.get(
            key, 4
        ),
    )
    selected_os = choose(
        "Système d'exploitation", [os_names.get(key, key) for key in os_keys]
    )
    os_key = next(key for key in os_keys if os_names.get(key, key) == selected_os)
    available = groups[os_key]
    profile_labels = [labels.get(key, key) for key in available]
    selected_label = choose("Profil de base", profile_labels)
    machine_profile = available[profile_labels.index(selected_label)]
    target_kind = profiles[machine_profile].get("target_kind", "host")
    if os_key == "linux":
        target_options = ["Machine hôte", "Conteneur"]
        default_target = 1 if target_kind == "container" else 0
        selected_target = choose(
            "Type de cible", target_options, default=default_target
        )
        target_kind = "container" if selected_target == "Conteneur" else "host"
    usage_labels = {
        "base": "Base uniquement",
        "personal": "Personnel",
        "professional": "Professionnel",
        "server": "Serveur",
    }
    existing_manifests = discovered.get(host, [])
    usage_options = list(usage_labels.values())
    if existing_manifests or replace_existing or allow_legacy:
        usage_labels["legacy"] = "Conserver les listes historiques (legacy)"
        usage_options.append(usage_labels["legacy"])
    selected_usage = choose("Variante de la base", usage_options)
    usage = next(key for key, label in usage_labels.items() if label == selected_usage)

    registry_path = machine_registry(source)
    registry = (
        read_json(registry_path)
        if registry_path.exists()
        else {"version": 1, "machines": {}}
    )
    if not isinstance(registry, dict) or not isinstance(
        registry.get("machines", {}), dict
    ):
        raise LayerError(f"Invalid machine registry: {registry_path}")
    machines = registry.setdefault("machines", {})
    existing_key = next(
        (key for key in machines if key.casefold() == host.casefold()), None
    )
    if existing_key and not replace_existing:
        raise LayerError(f"{host} is already registered in {registry_path.name}")
    if existing_key:
        host = existing_key
        previous = machines[existing_key]
        print(
            "Configuration enregistrée : base "
            f"{base_profile_name(previous.get('machine_profile', '?'), previous.get('package_profile', '?'))}"
        )
        if previous.get("package_profile") == "legacy":
            print("  Mode compatibilité avec les manifestes historiques")
        if not confirm("Remplacer ce profil ?", default=False):
            return None

    context = Context(source, machine_profile, usage, host, target_kind=target_kind)
    collisions = discover_machine_manifests(source).get(host, [])
    if collisions:
        print("Manifestes déjà présents : " + ", ".join(collisions))
        if not confirm(
            "Associer ces manifestes à cette machine ? Vérifie le hostname.",
            default=False,
        ):
            print("Enregistrement annulé ; aucun fichier modifié.")
            return None

    title = (
        "Profil de machine mis à jour"
        if existing_key
        else "Machine existante à configurer"
        if collisions
        else "Nouvelle machine"
    )
    print(f"\n{title} : {host}")
    print(f"  Système : {os_names.get(os_key, os_key)}")
    print(f"  Base :    {base_profile_name(machine_profile, usage)}")
    print(
        f"  Cible :   {'conteneur' if target_kind == 'container' else 'machine hôte'}"
    )
    if usage == "legacy":
        print("  Mode :    compatibilité avec les manifestes historiques")
    for manager in context.managers:
        plan = context.selection(manager)
        count = len(context.entries(manager))
        print(f"  {manager} : {count} paquets déclarés")
        print("    couches : " + ", ".join(plan["files"] or ["aucun manifeste actif"]))
        print(f"    manifeste machine : {plan['host']}")
    print("  Aucun paquet ne sera installé.")
    if not confirm(
        "Enregistrer cette machine dans package-machines.json ?", default=False
    ):
        print("Aucun fichier modifié.")
        return None

    machines[host] = {
        "machine_profile": machine_profile,
        "package_profile": usage,
        "target_kind": target_kind,
    }
    registry["version"] = 1
    atomic_write(
        registry_path, json.dumps(registry, indent=2, ensure_ascii=False) + "\n"
    )
    if changed_paths is not None:
        changed_paths.append(registry_path)
    print(f"Créé : {registry_path.relative_to(source)}")
    print(
        "Le prochain `chezmoi apply` utilisera ce profil pour sélectionner les paquets."
    )
    if not existing_key:
        print(
            "Une première initialisation chezmoi sur ce hostname enregistrera aussi ce choix localement."
        )
    return context


def create_machine(
    source: Path, changed_paths: list[Path] | None = None
) -> Context | None:
    return configure_machine(source, changed_paths=changed_paths)


def discover_machine_manifests(source: Path) -> dict[str, list[str]]:
    catalog = read_json(source / "dot_private/package-layers.json")
    shared = {
        filename
        for profile in catalog["profiles"].values()
        for manager in profile["managers"].values()
        for layer in manager.values()
        for filename in layer
    }
    shared.update(
        filename
        for files in catalog["legacy_brew_host_prefixes"].values()
        for filename in files
    )
    shared.update(catalog.get("reserved_files", []))
    found: dict[str, list[str]] = {}
    for manager, prefix in catalog["host_prefixes"].items():
        for path in sorted((source / "dot_private").glob(f"{prefix}*")):
            if not path.is_file() or path.name in shared:
                continue
            suffix = ".json" if manager == "scoop" else ""
            if suffix and not path.name.endswith(suffix):
                continue
            hostname = (
                path.name[len(prefix) : -len(suffix)]
                if suffix
                else path.name[len(prefix) :]
            )
            if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", hostname):
                found.setdefault(hostname, []).append(path.name)
    return found


def select_machine_for_tui(
    current: Context, changed_paths: list[Path] | None = None
) -> Context | None:
    registry_path = machine_registry(current.source)
    registry = read_json(registry_path) if registry_path.exists() else {"machines": {}}
    if not isinstance(registry, dict) or not isinstance(registry.get("machines"), dict):
        raise LayerError(f"Invalid machine registry: {registry_path}")
    machines = registry["machines"]
    registered_names = {hostname.casefold() for hostname in machines}
    candidates = discover_machine_manifests(current.source)
    current_target = "conteneur" if current.target_kind == "container" else "hôte"
    choices = [
        f"Cette machine — {current.hostname} ({current.machine_profile}, "
        f"{current.package_profile}, {current_target})"
    ]
    targets = [(choices[0], "current", current.hostname)]
    for hostname, details in sorted(
        machines.items(), key=lambda item: item[0].casefold()
    ):
        if hostname.casefold() == current.hostname.casefold():
            continue
        if not isinstance(details, dict):
            raise LayerError(
                f"Invalid machine entry for {hostname!r} in {registry_path}"
            )
        label = (
            f"{hostname} — {details.get('machine_profile', '?')}, "
            f"{details.get('package_profile', '?')}, "
            f"{'conteneur' if details.get('target_kind') == 'container' else 'hôte'} "
            "(enregistrée)"
        )
        choices.append(label)
        targets.append((label, "registered", hostname))
    for hostname, files in sorted(
        candidates.items(), key=lambda item: item[0].casefold()
    ):
        if (
            hostname.casefold() in registered_names
            or hostname.casefold() == current.hostname.casefold()
        ):
            continue
        label = f"{hostname} — machine à configurer ({', '.join(files)})"
        choices.append(label)
        targets.append((label, "candidate", hostname))
    choices.append("Configurer un autre hostname…")
    targets.append((choices[-1], "manual", ""))
    selected = choose("Quelle machine veux-tu gérer ?", choices)
    _, kind, hostname = next(item for item in targets if item[0] == selected)
    if kind == "current":
        return current
    if kind == "registered":
        details = next(
            value
            for key, value in machines.items()
            if key.casefold() == hostname.casefold()
        )
        return Context(
            current.source,
            details.get("machine_profile", ""),
            details.get("package_profile", "legacy"),
            hostname,
            current.install_mas,
            details.get("target_kind"),
        )
    if kind == "manual":
        hostname = prompt_text("Nom court de la machine : ").split(".", 1)[0]
        registered = next(
            (
                value
                for key, value in machines.items()
                if key.casefold() == hostname.casefold()
            ),
            None,
        )
        if registered:
            return Context(
                current.source,
                registered.get("machine_profile", ""),
                registered.get("package_profile", "legacy"),
                hostname,
                current.install_mas,
                registered.get("target_kind"),
            )
    if kind == "candidate":
        return configure_machine(current.source, hostname, changed_paths=changed_paths)
    return configure_machine(current.source, hostname, changed_paths=changed_paths)


def run_package_tui(context: Context, changed_paths: list[Path]) -> int:
    """Top-level editor for system/base assignment and base/machine packages."""
    while True:
        action = choose(
            f"{context.hostname} · que veux-tu modifier ?",
            [
                "Système et base — choisir OS, distribution et profil",
                "Base — cocher les paquets partagés",
                "Machine — cocher les paquets propres à cette machine",
                "Terminer et finaliser",
            ],
            default=3,
        )
        if action == "Terminer et finaliser":
            return 0
        if action.startswith("Système et base"):
            registry_path = machine_registry(context.source)
            registry = read_json(registry_path) if registry_path.exists() else {}
            machines = registry.get("machines", {})
            is_registered = any(
                hostname.casefold() == context.hostname.casefold()
                for hostname in machines
            )
            updated = configure_machine(
                context.source,
                context.hostname,
                replace_existing=is_registered,
                allow_legacy=context.package_profile == "legacy",
                changed_paths=changed_paths,
            )
            if updated is not None:
                context = updated
            continue
        scope = "base" if action.startswith("Base") else "machine"
        edit_packages(context, changed_paths, scope_filter=scope)


def publish_tui_changes(
    source: Path, changed_paths: list[Path], *, apply_local: bool = True
) -> None:
    """Offer to commit or push only paths changed by this TUI session."""
    paths = list(dict.fromkeys(Path(path).resolve() for path in changed_paths))
    if not paths:
        return
    root = Path(source).resolve()
    relative = []
    for path in paths:
        try:
            relative.append(str(path.relative_to(root)))
        except ValueError as error:
            raise LayerError(
                f"TUI change is outside the chezmoi source: {path}"
            ) from error

    if apply_local:
        actions = [
            "Garder les fichiers enregistrés, sans apply",
            "Appliquer avec chezmoi, sans commit",
            "Appliquer et committer",
            "Appliquer, committer et pousser vers origin",
        ]
        default_action = 2
    else:
        actions = [
            "Garder les fichiers enregistrés en local",
            "Committer les changements",
            "Committer et pousser vers origin",
        ]
        default_action = 1
        print(
            "La cible est une autre machine ; chezmoi apply devra être lancé sur celle-ci."
        )
    action = choose("Finaliser les changements", actions, default=default_action)
    if action in (
        "Garder les fichiers enregistrés, sans apply",
        "Garder les fichiers enregistrés en local",
    ):
        print("Fichiers enregistrés localement ; aucune autre action lancée.")
        return
    branch = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
        encoding="utf-8",
    ).stdout.strip()
    if not branch:
        raise LayerError("Cannot publish TUI changes from a detached HEAD")
    if apply_local:
        print("Application des dotfiles et des changements de paquets : chezmoi apply")
        apply_result = subprocess.run(["chezmoi", "apply"], cwd=root)
        if apply_result.returncode:
            raise LayerError(
                "chezmoi apply a échoué ; les fichiers sont enregistrés, aucun commit n'a été créé."
            )
        if action == "Appliquer avec chezmoi, sans commit":
            print("Apply terminé ; les modifications restent non commitées.")
            return

    status = subprocess.run(
        ["git", "status", "--porcelain=v1", "--", *relative],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
        encoding="utf-8",
    ).stdout.splitlines()
    staged_before = {
        line[3:] for line in status if len(line) > 3 and line[0] not in (" ", "?")
    }
    subprocess.run(["git", "add", "--", *relative], cwd=root, check=True)
    staged_diff = subprocess.run(
        ["git", "diff", "--cached", "--", *relative],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
        encoding="utf-8",
    ).stdout
    if _VISUAL_TUI and sys.stdin.isatty() and sys.stdout.isatty():
        try:
            _visual_view("Diff qui sera commité", staged_diff or "Aucun changement.")
        except Exception:
            print(staged_diff or "Aucun changement.")
    else:
        print(staged_diff or "Aucun changement.")
    if not confirm("Confirmer ce commit ?", default=False):
        unstage = [path for path in relative if path not in staged_before]
        if unstage:
            subprocess.run(
                ["git", "restore", "--staged", "--", *unstage],
                cwd=root,
                check=True,
            )
        print("Commit annulé ; les fichiers restent modifiés localement.")
        return

    message = prompt_text(
        "Message du commit", default="chore(packages): update package manifests"
    )
    commit = subprocess.run(
        ["git", "commit", "--only", "-m", message, "--", *relative],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if commit.stdout:
        print(commit.stdout, end="")
    if commit.returncode:
        if commit.stderr:
            print(commit.stderr, file=sys.stderr, end="")
        raise LayerError("Git commit failed; the TUI changes remain available locally")
    if action in (
        "Appliquer, committer et pousser vers origin",
        "Committer et pousser vers origin",
    ):
        push = subprocess.run(
            ["git", "push", "origin", branch],
            cwd=root,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if push.stdout:
            print(push.stdout, end="")
        if push.stderr:
            print(push.stderr, file=sys.stderr, end="")
        if push.returncode:
            raise LayerError(
                "Commit créé localement, mais le push a échoué. Synchronise la branche puis repousse."
            )


def edit_packages(
    context: Context,
    changed_paths: list[Path] | None = None,
    *,
    scope_filter: str | None = None,
) -> int:
    """Edit package selections with checkboxes and explicit save confirmation."""
    manager_labels = {
        "brew": "Homebrew / Linuxbrew",
        "apt": "APT",
        "dnf": "DNF",
        "pacman": "Pacman",
        "aur": "AUR",
        "rpm": "rpm-ostree",
        "flatpak": "Flatpak",
        "snap": "Snap",
        "apk": "APK",
        "pkg": "FreeBSD pkg",
        "scoop": "Scoop",
    }
    while True:
        managers = list(context.managers)
        manager_label = choose(
            "Système · choisir le gestionnaire de paquets",
            [manager_labels.get(item, item) for item in managers],
        )
        manager = managers[
            [manager_labels.get(item, item) for item in managers].index(manager_label)
        ]
        selection = context.selection(manager)
        scopes = []
        if scope_filter in (None, "machine"):
            scopes.append(("machine", f"Cette machine — {selection['host']}", None))
        if context.package_profile != "legacy" and scope_filter in (None, "base"):
            scopes.extend(
                ("base", f"Base partagée — {filename}", filename)
                for filename in selection["base"]
            )
            scopes.extend(
                ("usage", f"Variante partagée — {filename}", filename)
                for filename in selection["usage"]
            )
        if not scopes:
            print(
                "Cette machine est encore en compatibilité legacy ; migre-la avant de modifier ses bases partagées."
            )
            return 0
        scope_label = choose(
            "Base ou manifeste machine à modifier",
            [item[1] for item in scopes],
        )
        scope, _, filename = next(item for item in scopes if item[1] == scope_label)

        if scope == "machine":
            entries = context.entries(manager)
            source_files = selection["files"]
        else:
            manifest = context.directory / filename
            entries = parse_entries(manifest, manager) if manifest.exists() else {}
            source_files = [filename]
        origins = {}
        for source_file in source_files:
            source_path = context.directory / source_file
            if not source_path.exists():
                continue
            for identity in parse_entries(source_path, manager):
                if identity in entries:
                    origins.setdefault(identity, []).append(source_file)
        if scope in ("base", "usage"):
            consumers = manifest_consumers(context, manager, filename)
            print(
                f"Ce manifeste est partagé par : {', '.join(consumers) or 'aucun autre profil'}"
            )
        selected, added = select_packages(
            f"{manager_label} · {scope_label} · coche les paquets à conserver",
            manager,
            entries,
            origins,
        )
        if selected is None:
            print("Sélection annulée ; aucun fichier modifié.")
        else:
            additions = {key: value for key, value in added.items() if key in selected}
            updates = plan_selection_changes(
                context,
                manager,
                scope,
                filename,
                entries,
                selected,
                additions,
            )
            if updates:
                show_file_changes(context.source, updates)
                if confirm("Sauvegarder cette sélection ?", default=False):
                    for path, content in updates.items():
                        atomic_write(path, content)
                        if changed_paths is not None:
                            changed_paths.append(path)
                    print("Sélection sauvegardée :")
                    for path in updates:
                        print(f"  {path.relative_to(context.source)}")
                else:
                    print("Aucun fichier modifié.")
            else:
                print("La sélection n'a pas changé.")

        next_action = choose(
            "Gestion des paquets",
            ["Modifier un autre manifeste", "Terminer et finaliser"],
            default=1,
        )
        if next_action == "Terminer et finaliser":
            return 0


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


def serialize_preserving_comments(entries: dict, manager: str, original: str) -> str:
    """Keep handwritten comments, blank lines and declaration ordering on edits."""
    if manager == "scoop":
        return serialize_entries(entries, manager)
    remaining = set(entries)
    output = []
    for raw in original.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            output.append(raw)
            continue
        if manager == "brew":
            match = BREW_ENTRY.fullmatch(line)
            identity = f"{match[1]}:{match[2]}" if match else None
        elif manager == "snap":
            parts = shlex.split(line)
            identity = parts[0] if parts else None
        else:
            identity = line
        if identity in remaining:
            output.append(raw)
            remaining.remove(identity)
    if remaining:
        if output and output[-1].strip():
            output.append("")
        output.extend(
            str(entries[identity]) for identity in entries if identity in remaining
        )
    return "\n".join(output) + ("\n" if output else "")


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


def package_value(manager: str, name: str, identity: str):
    if manager == "brew":
        kind, value = identity.split(":", 1)
        return f'{kind} "{value}"'
    if manager == "scoop":
        value = identity.split(":", 1)[1] if identity.startswith("bucket:") else name
        return {"name": value}
    return name


def plan_selection_changes(
    context: Context,
    manager: str,
    scope: str,
    filename: str | None,
    initial_entries: dict,
    selected: set[str],
    added: dict[str, str],
) -> dict[Path, str]:
    """Build manifest changes from one confirmed checkbox selection."""
    removed = set(initial_entries) - selected
    if scope == "machine":
        selection = context.selection(manager)
        host = context.directory / selection["host"]
        local = parse_entries(host, manager) if host.exists() else {}
        shared = context.entries(manager, shared=True, exclusions=False)
        exclude_data = (
            read_json(context.exclude_file) if context.exclude_file.exists() else {}
        )
        excluded = context.exclusions(manager)
        for identity in removed:
            local.pop(identity, None)
            if identity in shared and identity not in excluded:
                excluded.append(identity)
        for identity, name in added.items():
            resolved = entry_identity(manager, name, shared | local)
            excluded = [item for item in excluded if item != resolved]
            if resolved not in shared:
                local[resolved] = package_value(manager, name, resolved)
        original = host.read_text(encoding="utf-8-sig") if host.exists() else ""
        updates = {}
        host_content = serialize_preserving_comments(local, manager, original)
        if host_content != original:
            updates[host] = host_content
        if sorted(excluded) != sorted(exclude_data.get(manager, [])):
            exclude_data[manager] = sorted(excluded)
            updates[context.exclude_file] = json.dumps(exclude_data, indent=2) + "\n"
        return updates

    if not filename:
        raise LayerError("A shared manifest was not selected")
    path = context.directory / filename
    entries = dict(initial_entries)
    for identity in removed:
        entries.pop(identity, None)
    shared = context.entries(manager, shared=True, exclusions=False)
    for identity, name in added.items():
        resolved = entry_identity(manager, name, shared | entries)
        if resolved in shared and resolved not in entries:
            raise LayerError(
                f"{resolved} is already declared in another active shared layer"
            )
        entries[resolved] = package_value(manager, name, resolved)
    original = path.read_text(encoding="utf-8-sig") if path.exists() else ""
    content = serialize_preserving_comments(entries, manager, original)
    return {path: content} if content != original else {}


def plan_record(
    context: Context, manager: str, action: str, names: list[str]
) -> dict[Path, str]:
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
                    value = (
                        identity.split(":", 1)[1]
                        if identity.startswith("bucket:")
                        else name
                    )
                    local[identity] = {"name": value}
                else:
                    local[identity] = name
    updates = {}
    original = host.read_text(encoding="utf-8-sig") if host.exists() else ""
    content = serialize_preserving_comments(local, manager, original)
    if (host.exists() and host.read_text(encoding="utf-8-sig") != content) or (
        not host.exists() and local
    ):
        updates[host] = content
    if sorted(excluded) != sorted(exclude_data.get(manager, [])):
        exclude_data[manager] = sorted(excluded)
        updates[context.exclude_file] = json.dumps(exclude_data, indent=2) + "\n"
    return updates


def record(context: Context, manager: str, action: str, names: list[str]) -> list[Path]:
    updates = plan_record(context, manager, action, names)
    for path, content in updates.items():
        atomic_write(path, content)
    return list(updates)


def plan_layer_record(
    context: Context,
    manager: str,
    filename: str,
    action: str,
    name: str,
) -> dict[Path, str]:
    path = context.directory / filename
    entries = parse_entries(path, manager) if path.exists() else {}
    shared = context.entries(manager, shared=True, exclusions=False)
    identity = entry_identity(manager, name, shared | entries)
    if action == "add":
        if identity in shared and identity not in entries:
            raise LayerError(
                f"{identity} is already declared in another active shared layer; "
                "remove it there before adding it to this layer"
            )
        if manager == "brew":
            kind, value = identity.split(":", 1)
            entries[identity] = f'{kind} "{value}"'
        elif manager == "scoop":
            value = (
                identity.split(":", 1)[1] if identity.startswith("bucket:") else name
            )
            entries[identity] = {"name": value}
        else:
            entries[identity] = name
    else:
        entries.pop(identity, None)
    previous = path.read_text(encoding="utf-8-sig") if path.exists() else ""
    content = serialize_preserving_comments(entries, manager, previous)
    return {path: content} if content != previous else {}


def manifest_consumers(context: Context, manager: str, filename: str) -> list[str]:
    consumers = []
    for profile_name, profile in context.catalog["profiles"].items():
        config = profile["managers"].get(manager, {})
        for layer_name, files in config.items():
            if filename in files:
                consumers.append(f"{profile_name}/{layer_name}")
    return consumers


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
        encoding="utf-8",
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
        return subprocess.run(
            args, check=True, capture_output=True, text=True, encoding="utf-8"
        ).stdout

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
    elif manager == "apk":
        world = Path("/etc/apk/world")
        if not world.exists():
            raise LayerError("Cannot read /etc/apk/world; APK inventory left unchanged")
        names = []
        for line in world.read_text(encoding="utf-8").splitlines():
            entry = line.strip()
            if not entry or entry.startswith("#"):
                continue
            names.append(re.split(r"[=<>~]", entry, maxsplit=1)[0])
    elif manager == "pkg":
        names = query("pkg", "query", "-e", "%a = 0", "%n").splitlines()
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
        "apk": ["apk"]
        if hasattr(os, "geteuid") and os.geteuid() == 0
        else ["sudo", "apk"],
        "pkg": ["pkg"]
        if hasattr(os, "geteuid") and os.geteuid() == 0
        else ["sudo", "pkg"],
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
    elif operation in (
        "install",
        "add",
        "remove",
        "uninstall",
        "purge",
        "delete",
        "del",
    ):
        action = "add" if operation == "install" else "remove"
        if operation in ("add",):
            action = "add"
        elif operation in ("delete", "del"):
            action = "remove"
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
        context.target_kind,
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
            encoding="utf-8",
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

    # Registered machines take precedence over the local chezmoi config during
    # package selection. Keep both sources in sync when this host is registered.
    registry_path = machine_registry(context.source)
    if registry_path.is_file():
        registry = read_json(registry_path)
        if not isinstance(registry, dict) or not isinstance(
            registry.get("machines"), dict
        ):
            raise LayerError(f"Invalid machine registry: {registry_path}")
        registry_host = next(
            (
                host
                for host in registry["machines"]
                if host.casefold() == context.hostname.casefold()
            ),
            None,
        )
        if registry_host is not None:
            machine = registry["machines"][registry_host]
            if not isinstance(machine, dict):
                raise LayerError(
                    f"Invalid machine entry for {registry_host!r} in {registry_path}"
                )
            if machine.get("package_profile") != target_profile:
                machine["package_profile"] = target_profile
                updates[registry_path] = (
                    json.dumps(registry, indent=2, ensure_ascii=False) + "\n"
                )
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
    if registry_path in updates:
        report["registry"] = str(registry_path)
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
        "edit",
        "create",
        "tui",
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
        command = args.command or "preview"
        global _VISUAL_TUI
        _VISUAL_TUI = command in ("create", "edit", "tui")
        if command == "create":
            context_path = Path(
                os.environ.get(
                    "PACKAGE_CONTEXT_FILE",
                    Path.home() / ".config/dotfiles/package-context.json",
                )
            )
            saved_context = read_json(context_path) if context_path.exists() else {}
            if not isinstance(saved_context, dict):
                raise LayerError(f"Expected an object in {context_path}")
            source = (
                args.source
                or os.environ.get("CHEZMOI_SOURCE_PATH")
                or saved_context.get("source_dir")
                or Path.home() / ".local/share/chezmoi"
            )
            changed_paths: list[Path] = []
            created = create_machine(Path(source), changed_paths)
            if created is None:
                return 0
            publish_tui_changes(
                Path(source),
                changed_paths,
                apply_local=(
                    created.hostname.casefold()
                    == short_hostname(platform.node()).casefold()
                ),
            )
            return 0
        context = context_from_environment(args)
        manager = getattr(args, "manager", None)
        if command in ("edit", "tui"):
            changed_paths = []
            selected_context = select_machine_for_tui(context, changed_paths)
            if selected_context is None:
                return 0
            result = run_package_tui(selected_context, changed_paths)
            publish_tui_changes(
                context.source,
                changed_paths,
                apply_local=(
                    selected_context.hostname.casefold() == context.hostname.casefold()
                ),
            )
            return result
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
                system = context.catalog["profiles"][context.machine_profile]["os"]
                system_name = {
                    "darwin": "macOS",
                    "linux": "Linux",
                    "freebsd": "BSD",
                    "windows": "Windows",
                }.get(system, system)
                print(f"Machine : {context.hostname}")
                print(f"Système : {system_name}")
                print(
                    f"Base :    {base_profile_name(context.machine_profile, context.package_profile)}"
                )
                if context.package_profile == "legacy":
                    print("Mode :    compatibilité avec les manifestes historiques")
                for plan in plans:
                    print(f"\n{plan['manager']}: {plan['count']} declarations")
                    for name in plan["files"]:
                        layer = (
                            "legacy"
                            if context.package_profile == "legacy"
                            and name in plan["base"]
                            else "base"
                            if name in plan["base"] or name in plan["usage"]
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
