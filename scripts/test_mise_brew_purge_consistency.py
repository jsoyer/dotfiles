"""
Consistency between the mise config and the Intel macOS brew purge list.

On Intel Macs, run_onchange_after_purge-brew-mise-duplicates uninstalls the
Homebrew copy of every tool mise provides. Its formula list is maintained by
hand, so a tool added to dot_config/mise/config.toml.tmpl without a matching
purge entry would leave a stale, never-upgraded brew copy behind. These tests
fail when the two drift apart.
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MISE_CONFIG = ROOT / "dot_config/mise/config.toml.tmpl"
PURGE_SCRIPT = (
    ROOT
    / ".chezmoiscripts/03-configure/run_onchange_after_purge-brew-mise-duplicates.sh.tmpl"
)

# mise tool short name -> Homebrew formula, when they differ.
FORMULA_ALIASES = {
    "cli": "gh",  # aqua:cli/cli
    "python": "python@3.13",
}

# mise tools whose Homebrew counterpart is deliberately NOT purged.
EXEMPT = {
    # Homebrew openjdk/openjdk@17 are dependencies of other formulae (gradle,
    # scala...); JDKs from mise are exposed via mise-java-macos-link instead.
    "java": "openjdk is a dependency of other formulae",
}


def mise_tools(text: str) -> set:
    """Tool short names from the [tools] section (all template branches)."""
    tools = set()
    in_tools = False
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith("{{"):
            continue
        if line.startswith("["):
            in_tools = line == "[tools]"
            continue
        if not in_tools:
            continue
        m = re.match(r'^"?([A-Za-z0-9_.@:/-]+)"?\s*=', line)
        if m:
            key = m.group(1)
            tools.add(re.split(r"[:/]", key)[-1])
    return tools


def purge_formulae(text: str) -> set:
    """Formula names from the PAIRS="formula:binary ..." block."""
    m = re.search(r'PAIRS="(.*?)"', text, re.S)
    if not m:
        return set()
    return {pair.split(":", 1)[0] for pair in m.group(1).split()}


def missing_from_purge(tools: set, formulae: set) -> list:
    return sorted(
        t
        for t in tools
        if t not in EXEMPT and FORMULA_ALIASES.get(t, t) not in formulae
    )


def stale_in_purge(tools: set, formulae: set) -> list:
    expected = {FORMULA_ALIASES.get(t, t) for t in tools if t not in EXEMPT}
    return sorted(formulae - expected)


class TestHelpers(unittest.TestCase):
    def test_parses_backends_and_template_branches(self):
        text = (
            "[tools]\nnode = \"latest\"\n{{- if x }}\nruby = \"latest\"\n{{- end }}\n"
            '"aqua:cli/cli" = "latest"\n"conda:git-delta" = "latest"\n'
            "[settings]\nall_compile = false\n"
        )
        self.assertEqual(mise_tools(text), {"node", "ruby", "cli", "git-delta"})

    def test_detects_missing_and_stale(self):
        tools = {"node", "cli", "ripgrep", "java"}
        formulae = {"node", "gh", "bat"}
        self.assertEqual(missing_from_purge(tools, formulae), ["ripgrep"])
        self.assertEqual(stale_in_purge(tools, formulae), ["bat"])


class TestRealFiles(unittest.TestCase):
    def setUp(self):
        self.tools = mise_tools(MISE_CONFIG.read_text())
        self.formulae = purge_formulae(PURGE_SCRIPT.read_text())

    def test_files_parse(self):
        self.assertIn("node", self.tools)
        self.assertIn("ripgrep", self.tools)
        self.assertIn("gh", self.formulae)

    def test_every_mise_tool_has_a_purge_entry(self):
        missing = missing_from_purge(self.tools, self.formulae)
        self.assertEqual(
            missing,
            [],
            "mise tools without a purge entry in "
            f"{PURGE_SCRIPT.name} (add 'formula:binary' to PAIRS, or to EXEMPT "
            "/ FORMULA_ALIASES in this test): " + ", ".join(missing),
        )

    def test_no_stale_purge_entry(self):
        stale = stale_in_purge(self.tools, self.formulae)
        self.assertEqual(
            stale,
            [],
            "purge entries no longer provided by mise (remove them, or the brew "
            "copy would be uninstalled with nothing replacing it): "
            + ", ".join(stale),
        )


if __name__ == "__main__":
    unittest.main()
