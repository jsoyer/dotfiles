#!/usr/bin/env python3
"""Target selector (-l): aliases, site=, kind=, tag:, @group, union, exclusion.

An empty or non-matching selector is an error (exit 2), never "the whole fleet".
"""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / "dot_local/share/fleet/lib"
sys.path.insert(0, str(LIB))

import inventory as inv  # noqa: E402
import selector  # noqa: E402

FLEET = """\
hosts:
  alpha:
    tailnet_name: alpha
    site: dijon
    kind: chezmoi-linux
    critical: false
    ssh_user: j
  beta:
    tailnet_name: beta
    site: dijon
    kind: omv
    critical: false
    ssh_user: j
    tags: [site-router]
  gamma:
    tailnet_name: gamma
    site: nice
    kind: omv
    critical: false
    ssh_user: j
    tags: [site-router, infra]
  delta:
    tailnet_name: delta
    site: nice
    kind: chezmoi-linux
    critical: false
    ssh_user: j
groups:
  nas: [beta, gamma]
"""


def data():
    return inv.parse_yaml_subset(FLEET)


class SelectorTest(unittest.TestCase):
    def test_alias_and_union(self):
        self.assertEqual(selector.resolve(data(), ["alpha"]), ["alpha"])
        self.assertEqual(selector.resolve(data(), ["delta,alpha"]), ["alpha", "delta"])

    def test_site_kind_tag_group(self):
        d = data()
        self.assertEqual(selector.resolve(d, ["site=nice"]), ["gamma", "delta"])
        self.assertEqual(selector.resolve(d, ["kind=omv"]), ["beta", "gamma"])
        self.assertEqual(selector.resolve(d, ["tag:infra"]), ["gamma"])
        self.assertEqual(selector.resolve(d, ["@nas"]), ["beta", "gamma"])

    def test_union_of_selectors_and_exclusion_after_union(self):
        d = data()
        self.assertEqual(selector.resolve(d, ["site=nice,kind=omv"]), ["beta", "gamma", "delta"])
        self.assertEqual(selector.resolve(d, ["kind=omv,!gamma"]), ["beta"])
        # exclusion is applied after the union whatever its position
        self.assertEqual(selector.resolve(d, ["!gamma,kind=omv"]), ["beta"])
        self.assertEqual(selector.resolve(d, ["site=nice", "!kind=omv"]), ["delta"])

    def test_multiple_tokens_are_a_union(self):
        self.assertEqual(selector.resolve(data(), ["alpha", "delta"]), ["alpha", "delta"])

    def test_no_match_is_an_error_never_everything(self):
        d = data()
        for bad in (["site=inexistant"], ["kind=windows"], ["tag:nope"], [""], [","], ["alpha,!alpha"]):
            with self.assertRaises(selector.SelectorError, msg=str(bad)):
                selector.resolve(d, bad)

    def test_exclusion_only_does_not_widen_to_the_fleet(self):
        with self.assertRaises(selector.SelectorError):
            selector.resolve(data(), ["!alpha"])

    def test_unknown_alias_group_site_kind(self):
        for bad in (["ghost"], ["@ghost"], ["site=mars"], ["kind=toaster"]):
            with self.assertRaises(selector.SelectorError, msg=str(bad)):
                selector.resolve(data(), bad)

    def test_exit_code_constant(self):
        self.assertEqual(selector.EXIT_EMPTY, 2)


class SelectorReviewTest(unittest.TestCase):
    def test_unknown_or_empty_tag_in_a_union_is_an_error_not_silently_ignored(self):
        d = data()
        for bad in (["alpha,tag:infrra"], ["tag:infra,tag:"], ["tag:"], ["alpha,!tag:nope"], ["alpha", "tag:typo"]):
            with self.assertRaises(selector.SelectorError, msg=str(bad)):
                selector.resolve(d, bad)

    def test_typos_never_widen_to_all_hosts(self):
        d = data()
        for bad in (["alpah"], ["site=nic"], ["kind=om"], ["!"], ["!ghost"], ["alpha,!ghost"], ["@"], [" "],
                    ["site = nice"], ["Site=nice"]):
            with self.assertRaises(selector.SelectorError, msg=str(bad)):
                selector.resolve(d, bad)

    def test_exclusion_alone_is_documented_as_an_error(self):
        self.assertIn("exclusion-only", selector.__doc__)
        with self.assertRaises(selector.SelectorError):
            selector.resolve(data(), ["!alpha,!beta"])

    def test_known_tag_in_exclusion_still_works(self):
        self.assertEqual(selector.resolve(data(), ["kind=omv,!tag:infra"]), ["beta"])


if __name__ == "__main__":
    unittest.main()
