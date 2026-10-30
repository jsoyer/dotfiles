#!/usr/bin/env python3
"""fleet.yml inventory, YAML-subset parser, Tailscale merge and the `fleet` wrapper.

`fleet ping/check` are only exercised with stubbed ssh and tailscale: no host is
ever contacted.
"""

import importlib.util
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FLEET_DIR = ROOT / "dot_local/share/fleet"
FLEET_YML = FLEET_DIR / "fleet.yml"
INVENTORY_PY = FLEET_DIR / "lib/inventory.py"
FLEET_BIN = ROOT / "dot_local/bin/executable_fleet"

_spec = importlib.util.spec_from_file_location("fleet_inventory", INVENTORY_PY)
inv = importlib.util.module_from_spec(_spec)
sys.modules["fleet_inventory"] = inv
_spec.loader.exec_module(inv)

MINIMAL = """\
hosts:
  alpha:
    tailnet_name: alpha
    site: dijon
    kind: chezmoi-linux
    critical: false
    ssh_user: jerome
  firewall:
    tailnet_name: opn
    site: nice
    kind: opnsense
    critical: true
groups:
  both: [alpha, firewall]
"""


def parse(text):
    return inv.parse_yaml_subset(text)


def host(**over):
    base = {"tailnet_name": "h", "site": "dijon", "kind": "chezmoi-linux", "critical": False}
    base.update(over)
    return base


def problems(hosts, **extra):
    data = {"hosts": hosts}
    data.update(extra)
    return inv.validate(data)


class YamlSubset(unittest.TestCase):
    def test_nested_mappings_and_scalars(self):
        data = parse("a:\n  b: 1\n  c: true\n  d: null\n  e: text\n  f: 'q # not comment'\n")
        self.assertEqual(data, {"a": {"b": 1, "c": True, "d": None, "e": "text", "f": "q # not comment"}})

    def test_flow_sequence_and_map(self):
        data = parse("x: [a, b, 3]\ny: {k: v, n: 2}\nz: []\n")
        self.assertEqual(data, {"x": ["a", "b", 3], "y": {"k": "v", "n": 2}, "z": []})

    def test_comments_are_ignored(self):
        data = parse("# top\na: 1  # trailing\n\n  # indented comment\nb: 2\n")
        self.assertEqual(data, {"a": 1, "b": 2})

    def test_dedent_returns_to_parent(self):
        data = parse("a:\n  b:\n    c: 1\n  d: 2\ne: 3\n")
        self.assertEqual(data, {"a": {"b": {"c": 1}, "d": 2}, "e": 3})

    def test_block_sequence_rejected(self):
        with self.assertRaises(ValueError):
            parse("a:\n  - x\n")

    def test_duplicate_key_rejected(self):
        with self.assertRaises(ValueError):
            parse("a: 1\na: 2\n")

    def test_tab_indentation_rejected(self):
        with self.assertRaises(ValueError):
            parse("a:\n\tb: 1\n")

    def test_unterminated_flow_rejected(self):
        with self.assertRaises(ValueError):
            parse("a: [x, y\n")

    def test_garbage_line_rejected(self):
        with self.assertRaises(ValueError):
            parse("just some words\n")


class Validation(unittest.TestCase):
    def test_minimal_inventory_is_valid(self):
        self.assertEqual(inv.validate(parse(MINIMAL)), [])

    def test_kind_outside_list_is_rejected(self):
        self.assertTrue(any("kind" in p for p in problems({"a": host(kind="toaster")})))

    def test_site_outside_list_is_rejected(self):
        self.assertTrue(any("site" in p for p in problems({"a": host(site="mars")})))

    def test_all_closed_list_values_accepted(self):
        for kind in inv.KINDS:
            crit = kind in ("opnsense", "proxmox")
            self.assertEqual(problems({"a": host(kind=kind, critical=crit)}), [], kind)
        for site in inv.SITES:
            self.assertEqual(problems({"a": host(site=site)}), [], site)

    def test_critical_true_only_for_opnsense_and_proxmox(self):
        self.assertEqual(problems({"a": host(kind="opnsense", critical=True)}), [])
        self.assertEqual(problems({"a": host(kind="proxmox", critical=True)}), [])
        self.assertTrue(problems({"a": host(kind="opnsense", critical=False)}))
        self.assertTrue(problems({"a": host(kind="proxmox", critical=False)}))
        for kind in ("chezmoi-linux", "chezmoi-macos", "omv", "pikvm", "homeassistant", "windows", "guardian"):
            self.assertTrue(problems({"a": host(kind=kind, critical=True)}), kind)

    def test_critical_must_be_boolean(self):
        self.assertTrue(problems({"a": host(critical="yes")}))

    def test_missing_required_field(self):
        h = host()
        del h["site"]
        self.assertTrue(any("missing site" in p for p in problems({"a": h})))

    def test_unknown_field_rejected(self):
        self.assertTrue(problems({"a": host(phase=2)}))

    def test_group_must_reference_existing_aliases(self):
        self.assertTrue(problems({"a": host()}, groups={"g": ["a", "ghost"]}))
        self.assertEqual(problems({"a": host()}, groups={"g": ["a"]}), [])

    def test_duplicate_tailnet_name_rejected(self):
        self.assertTrue(problems({"a": host(tailnet_name="x"), "b": host(tailnet_name="X")}))

    def test_one_canary_per_kind(self):
        self.assertTrue(problems({"a": host(tailnet_name="a", canary=True), "b": host(tailnet_name="b", canary=True)}))
        self.assertEqual(
            problems({"a": host(tailnet_name="a", canary=True), "b": host(tailnet_name="b", kind="omv", canary=True)}), []
        )

    def test_unsafe_service_and_user_rejected(self):
        self.assertTrue(problems({"a": host(critical_services=["ok", "bad name; id"])}))
        self.assertTrue(problems({"a": host(ssh_user="root; id")}))

    def test_timeouts_validated_and_resolved(self):
        self.assertTrue(problems({"a": host()}, timeouts={"toaster": 5}))
        self.assertTrue(problems({"a": host()}, timeouts={"omv": 0}))
        data = {"hosts": {"a": host(), "b": host(tailnet_name="b", timeout_min=7)}, "timeouts": {"chezmoi-linux": 11}}
        self.assertEqual(inv.timeout_for(data, "a"), 11)
        self.assertEqual(inv.timeout_for(data, "b"), 7)
        data["timeouts"] = {}
        self.assertEqual(inv.timeout_for(data, "a"), 30)

    def test_empty_inventory_rejected(self):
        self.assertTrue(inv.validate({}))
        self.assertTrue(inv.validate({"hosts": {}}))

    def test_load_reports_every_problem(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "f.yml"
            path.write_text(MINIMAL.replace("site: dijon", "site: mars").replace("critical: true", "critical: false"))
            with self.assertRaises(inv.InventoryError) as ctx:
                inv.load_inventory(str(path))
            self.assertIn("mars", str(ctx.exception))
            self.assertIn("critical must be true", str(ctx.exception))

    def test_group_members_helper(self):
        data = parse(MINIMAL)
        self.assertEqual(inv.group_members(data, "both"), ["alpha", "firewall"])
        with self.assertRaises(inv.InventoryError):
            inv.group_members(data, "nope")


class ShippedInventory(unittest.TestCase):
    """The real fleet.yml, and the INVARIANTS.md greps on it."""

    def test_fleet_yml_is_valid(self):
        data = inv.load_inventory(str(FLEET_YML))
        self.assertGreaterEqual(len(data["hosts"]), 30)

    def test_critical_iff_opnsense_or_proxmox(self):
        data = inv.load_inventory(str(FLEET_YML))
        for alias, h in data["hosts"].items():
            self.assertEqual(h["critical"], h["kind"] in ("opnsense", "proxmox"), alias)
        crit = sorted(a for a, h in data["hosts"].items() if h["critical"])
        self.assertEqual(crit, ["multibox", "opnsense-amd64"])

    def test_guardians_and_bbh_network_are_not_critical(self):
        hosts = inv.load_inventory(str(FLEET_YML))["hosts"]
        for alias in ("bbh-dij-guardian", "bbh-nce-guardian", "bbh-network"):
            self.assertFalse(hosts[alias]["critical"])

    def test_kind_and_site_lines_are_bare_values(self):
        text = FLEET_YML.read_text()
        kinds = "|".join(inv.KINDS)
        sites = "|".join(inv.SITES)
        for line in text.splitlines():
            if re.match(r"^\s+kind:", line):
                self.assertRegex(line, r"kind:\s*(%s)\s*$" % kinds)
            if re.match(r"^\s+site:", line):
                self.assertRegex(line, r"site:\s*(%s)\s*$" % sites)

    def test_masters_and_multibox_present(self):
        hosts = inv.load_inventory(str(FLEET_YML))["hosts"]
        for alias in ("diabolo", "penelope", "multibox", "omv-nice", "fedora-rawhide"):
            self.assertIn(alias, hosts)
        self.assertEqual(hosts["multibox"]["kind"], "proxmox")

    def test_pikvm_critical_services(self):
        self.assertEqual(inv.load_inventory(str(FLEET_YML))["hosts"]["pikvm"]["critical_services"], ["kvmd", "cloudflared"])

    def test_no_ios_devices(self):
        text = FLEET_YML.read_text().lower()
        self.assertNotIn("iphone", text)
        self.assertNotIn("ipad", text)

    def test_cli_validate_passes(self):
        proc = subprocess.run(
            [sys.executable, "-I", str(INVENTORY_PY), "validate", "--file", str(FLEET_YML)],
            capture_output=True, text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_cli_validate_fails_on_bad_kind(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "bad.yml"
            bad.write_text(MINIMAL.replace("kind: chezmoi-linux", "kind: toaster"))
            proc = subprocess.run(
                [sys.executable, "-I", str(INVENTORY_PY), "validate", "--file", str(bad)],
                capture_output=True, text=True,
            )
            self.assertEqual(proc.returncode, 2)
            self.assertIn("toaster", proc.stderr)


TS_STATUS = {
    "Self": {"HostName": "diabolo", "DNSName": "diabolo.tail1.ts.net.", "Online": True, "OS": "linux"},
    "Peer": {
        "k1": {"HostName": "alpha", "DNSName": "alpha.tail1.ts.net.", "Online": True, "LastSeen": "2026-10-30T10:00:00Z"},
        "k2": {"HostName": "OPNsense-amd64", "DNSName": "opn.tail1.ts.net.", "Online": False,
               "LastSeen": "2026-10-29T08:00:00Z", "Tags": ["tag:infra"]},
        "k3": {"HostName": "never", "DNSName": "never.tail1.ts.net.", "Online": False, "LastSeen": "0001-01-01T00:00:00Z"},
    },
}


class TailscaleMerge(unittest.TestCase):
    def setUp(self):
        self.peers = inv.parse_tailscale(TS_STATUS)

    def test_parse_uses_dns_label(self):
        self.assertEqual(set(self.peers), {"diabolo", "alpha", "opn", "never"})
        self.assertEqual(self.peers["opn"]["tags"], ["tag:infra"])

    def test_zero_last_seen_is_none(self):
        self.assertIsNone(self.peers["never"]["last_seen"])

    def test_states(self):
        self.assertEqual(inv.peer_state("alpha", self.peers), ("online", "2026-10-30T10:00:00Z"))
        self.assertEqual(inv.peer_state("opn", self.peers), ("offline", "2026-10-29T08:00:00Z"))
        self.assertEqual(inv.peer_state("ghost", self.peers), ("absent", None))
        self.assertEqual(inv.peer_state("alpha", None), ("unknown", None))

    def test_plan_rows_and_unknown_alias(self):
        data = parse(MINIMAL)
        rows = inv.plan_rows(data, ["alpha"], self.peers)
        self.assertEqual(rows, [["alpha", "chezmoi-linux", "dijon", "jerome", "alpha", "online", "2026-10-30T10:00:00Z"]])
        all_rows = inv.plan_rows(data, [], self.peers)
        self.assertEqual([r[0] for r in all_rows], ["alpha", "firewall"])
        self.assertEqual(all_rows[1][3:6], ["-", "opn", "offline"])
        with self.assertRaises(inv.InventoryError):
            inv.plan_rows(data, ["alpha", "ghost"], self.peers)

    def test_read_tailscale_failure_is_none(self):
        def boom():
            raise OSError("no tailscale")
        self.assertIsNone(inv.read_tailscale(boom))
        self.assertIsNone(inv.read_tailscale(lambda: "not json"))
        self.assertIsNotNone(inv.read_tailscale(lambda: json.dumps(TS_STATUS)))


class AgentOutputValidation(unittest.TestCase):
    GOOD = {"schema": 1, "status": "up-to-date", "reason": None, "packages": 0, "reboot_required": False}

    def test_valid_line(self):
        s = inv.summarize_agent_output(json.dumps(self.GOOD))
        self.assertEqual((s["status"], s["packages"], s["reboot_required"]), ("up-to-date", 0, False))

    def test_master_only_status_from_agent_is_rejected(self):
        for status in ("offline", "unreachable", "timeout", "held", "pwned"):
            bad = dict(self.GOOD, status=status)
            self.assertEqual(inv.summarize_agent_output(json.dumps(bad))["status"], "failed", status)

    def test_wrong_schema_multiple_lines_and_garbage(self):
        self.assertEqual(inv.summarize_agent_output(json.dumps(dict(self.GOOD, schema=2)))["status"], "failed")
        two = json.dumps(self.GOOD) + "\n" + json.dumps(self.GOOD)
        self.assertEqual(inv.summarize_agent_output(two)["status"], "failed")
        self.assertEqual(inv.summarize_agent_output("hello")["status"], "failed")
        self.assertEqual(inv.summarize_agent_output("")["status"], "failed")

    def test_control_characters_in_reason_are_neutralised(self):
        s = inv.summarize_agent_output(json.dumps(dict(self.GOOD, reason="a\x1b[31mred\x07")))
        self.assertNotIn("\x1b", s["reason"])
        self.assertNotIn("\x07", s["reason"])


@unittest.skipIf(sys.platform == "win32", "bash wrapper")
class FleetWrapper(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="fleet-wrap-"))
        self.addCleanup(shutil.rmtree, self.root, True)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        fleet = self.root / "share/fleet"
        (fleet / "lib").mkdir(parents=True)
        shutil.copy(INVENTORY_PY, fleet / "lib/inventory.py")
        hosts_text, groups_text = MINIMAL.split("groups:")
        extra = "".join(
            "  %s:\n    tailnet_name: %s\n    site: nice\n    kind: %s\n    critical: false\n%s"
            % (name, name, kind, "    ssh_user: jerome\n" if user else "")
            for name, kind, user in (("nouser", "omv", False), ("gone", "chezmoi-linux", True), ("silent", "chezmoi-linux", True), ("refused", "chezmoi-linux", True))
        )
        (fleet / "fleet.yml").write_text(hosts_text + extra + "groups:" + groups_text)
        ts = dict(TS_STATUS)
        ts["Peer"] = dict(TS_STATUS["Peer"])
        ts["Peer"]["k4"] = {"DNSName": "nouser.t.ts.net.", "Online": True}
        ts["Peer"]["k5"] = {"DNSName": "silent.t.ts.net.", "Online": True}
        ts["Peer"]["k6"] = {"DNSName": "refused.t.ts.net.", "Online": True}
        (self.root / "ts.json").write_text(json.dumps(ts))
        self._stub("tailscale", f'cat "{self.root}/ts.json"\n')
        self._stub(
            "ssh",
            'echo "ssh $*" >> "$STUB_DIR/ssh.log"\n'
            'case "$*" in\n'
            '  *PreferredAuthentications=none*alpha*) echo "jerome@alpha: Permission denied (publickey)." >&2; exit 255 ;;\n'
            '  *PreferredAuthentications=none*silent*) echo "ssh: connect to host silent port 22: Connection timed out" >&2; exit 255 ;;\n'
            '  *alpha*" check") cat "$STUB_DIR/agent.out"; exit 0 ;;\n'
            '  *silent*" check") echo "ssh: connect to host silent port 22: Connection timed out" >&2; exit 255 ;;\n'
            '  *refused*" check") printf "fleet-agent: refused\\033[31m\\n" >&2; exit 1 ;;\n'
            'esac\nexit 255\n',
        )
        (self.root / "agent.out").write_text(
            json.dumps({"schema": 1, "status": "skipped", "reason": "updates_pending", "packages": 4, "reboot_required": True}) + "\n"
        )
        self.env = dict(
            os.environ,
            PATH=f"{self.bin}:{os.environ['PATH']}",
            FLEET_DIR=str(fleet),
            FLEET_YML=str(fleet / "fleet.yml"),
            STUB_DIR=str(self.root),
            HOME=str(self.root),
        )

    def _stub(self, name, body):
        p = self.bin / name
        p.write_text("#!/usr/bin/env bash\n" + body)
        p.chmod(p.stat().st_mode | stat.S_IXUSR)

    def fleet(self, *args):
        return subprocess.run(["bash", str(FLEET_BIN), *args], env=self.env, capture_output=True, text=True, timeout=30)

    def ssh_log(self):
        p = self.root / "ssh.log"
        return p.read_text() if p.exists() else ""

    def rows(self, proc):
        return {ln.split()[0]: ln for ln in proc.stdout.splitlines() if ln.strip()}

    def test_ping_distinguishes_ok_offline_unreachable(self):
        proc = self.fleet("ping", "alpha,firewall,silent")
        rows = self.rows(proc)
        self.assertIn("ok", rows["alpha"])
        self.assertIn("offline", rows["firewall"])
        self.assertIn("last seen 2026-10-29", rows["firewall"])
        self.assertIn("unreachable", rows["silent"])
        self.assertIn("timed out", rows["silent"])
        self.assertEqual(proc.returncode, 1)

    def test_ping_never_runs_a_command_on_the_agent_key(self):
        self.fleet("ping", "alpha")
        log = self.ssh_log()
        self.assertIn("PreferredAuthentications=none", log)
        self.assertNotRegex(log, r" check\s*$")
        self.assertIn("StrictHostKeyChecking=yes", log)

    def test_offline_host_gets_no_connection(self):
        self.fleet("ping", "firewall")
        self.assertEqual(self.ssh_log(), "")

    def test_absent_from_tailnet_is_unreachable_without_ssh(self):
        proc = self.fleet("ping", "gone")
        self.assertIn("unreachable", proc.stdout)
        self.assertIn("not in tailscale", proc.stdout)
        self.assertEqual(self.ssh_log(), "")

    def test_check_parses_agent_json(self):
        proc = self.fleet("check", "alpha")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("skipped", proc.stdout)
        self.assertIn("packages=4", proc.stdout)
        self.assertIn("reboot=yes", proc.stdout)
        self.assertIn("StrictHostKeyChecking=yes", self.ssh_log())
        self.assertRegex(self.ssh_log(), r"jerome@alpha check")

    def test_check_rejects_garbage_from_agent(self):
        (self.root / "agent.out").write_text("pwned\n")
        proc = self.fleet("check", "alpha")
        self.assertIn("failed", proc.stdout)
        self.assertEqual(proc.returncode, 1)

    def test_check_silent_host_is_unreachable(self):
        proc = self.fleet("check", "silent")
        self.assertIn("unreachable", proc.stdout)
        self.assertEqual(proc.returncode, 1)

    def test_check_silent_host_reports_ssh_exit_code_and_stderr(self):
        row = self.rows(self.fleet("check", "silent"))["silent"]
        self.assertIn("ssh exit 255", row)
        self.assertIn("timed out", row)

    def test_check_agent_refusal_is_distinguishable_from_no_answer(self):
        proc = self.fleet("check", "refused,silent")
        rows = self.rows(proc)
        self.assertIn("failed", rows["refused"])
        self.assertIn("agent refused", rows["refused"])
        self.assertIn("ssh exit 1", rows["refused"])
        self.assertNotIn("\x1b", proc.stdout, "remote stderr is sanitised")
        self.assertIn("unreachable", rows["silent"])
        self.assertNotIn("agent refused", rows["silent"])
        self.assertEqual(proc.returncode, 1)

    def test_check_host_without_agent_is_unsupported(self):
        proc = self.fleet("check", "nouser")
        self.assertIn("unsupported", proc.stdout)
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(self.ssh_log(), "")

    def test_unknown_host_is_an_error_not_everything(self):
        proc = self.fleet("check", "alpha,ghost")
        self.assertEqual(proc.returncode, 2)
        self.assertIn("ghost", proc.stderr)
        self.assertEqual(self.ssh_log(), "")

    def test_empty_selector_is_an_error(self):
        proc = self.fleet("check", ",")
        self.assertEqual(proc.returncode, 2)
        self.assertEqual(self.ssh_log(), "")

    def test_ping_is_a_wrapper_command_not_an_agent_verb(self):
        agent = (FLEET_DIR / "agent/fleet-agent.sh").read_text()
        self.assertNotRegex(agent, re.compile(r"^\s*'?ping'?\)", re.M | re.I))
        self.assertIn("cmd_ping", FLEET_BIN.read_text())

    def test_unknown_command_and_help(self):
        self.assertEqual(self.fleet("frobnicate").returncode, 2)
        self.assertEqual(self.fleet("help").returncode, 0)


if __name__ == "__main__":
    unittest.main()
