#!/usr/bin/env python3
"""Target selector (-l) shared by check, up, reboot and logs.

Syntax (spec section 12): ``alias``, ``site=<site>``, ``kind=<kind>``,
``tag:<tag>``, ``@<group>``, ``a,b`` (union), ``!x`` (exclusion, applied after
the union). Several tokens are a union too.

A selector that matches nothing is an error (EXIT_EMPTY = 2): it never falls
back to "every host". An exclusion-only selector (``!x`` alone) is therefore an
error as well: there is nothing to exclude from; write ``site=dijon,!x`` instead.
Every term must be known (alias, group, site, kind, tag): a typo is an error even
inside a union, it is never ignored.
Stdlib only, Python 3.9 compatible.
"""

from typing import Any, Dict, List

EXIT_EMPTY = 2

KINDS = (
    "chezmoi-linux", "chezmoi-macos", "omv", "pikvm", "homeassistant",
    "opnsense", "proxmox", "windows", "guardian",
)
SITES = ("dijon", "nice", "garage", "cloud", "mobile")


class SelectorError(Exception):
    """Unknown term or empty result; the caller exits with EXIT_EMPTY."""


def _match(data: Dict[str, Any], term: str) -> List[str]:
    hosts = data["hosts"]
    if term.startswith("@"):
        groups = data.get("groups") or {}
        name = term[1:]
        if name not in groups:
            raise SelectorError("unknown group %r" % name)
        return [a for a in groups[name] if a in hosts]
    if term.startswith("site="):
        site = term[5:]
        if site not in SITES:
            raise SelectorError("unknown site %r" % site)
        return [a for a, h in hosts.items() if h.get("site") == site]
    if term.startswith("kind="):
        kind = term[5:]
        if kind not in KINDS:
            raise SelectorError("unknown kind %r" % kind)
        return [a for a, h in hosts.items() if h.get("kind") == kind]
    if term.startswith("tag:"):
        tag = term[4:]
        known = set(t for h in hosts.values() for t in (h.get("tags") or []))
        if tag not in known:       # a typo inside a union must not be silently ignored
            raise SelectorError("unknown tag %r" % tag)
        return [a for a, h in hosts.items() if tag in (h.get("tags") or [])]
    if term in hosts:
        return [term]
    raise SelectorError("unknown host %r" % term)


def resolve(data: Dict[str, Any], tokens: List[str]) -> List[str]:
    """Aliases selected by ``tokens``, in fleet.yml order; SelectorError if none."""
    include: List[str] = []
    exclude: List[str] = []
    for token in tokens:
        for raw in token.split(","):
            term = raw.strip()
            if not term:
                continue
            if term.startswith("!"):
                exclude.extend(_match(data, term[1:].strip()))
            else:
                include.extend(_match(data, term))
    chosen = set(include) - set(exclude)
    ordered = [a for a in data["hosts"] if a in chosen]
    if not ordered:
        raise SelectorError("selector matches no host")
    return ordered
