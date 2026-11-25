#!/usr/bin/env python3
"""Proxmox host helpers: pct-snapshot rotation and pct-bootstrap guarantees.

pct-snapshot runs against a fake `pct` (state in a temp dir), so the rotation
is tested for real: only "<prefix>-YYYYMMDD-HHMM" snapshots are rotated, every
other snapshot (pre-install, manual) survives.
"""

import os
import shutil
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "dot_local/bin/executable_pct-snapshot"
BOOTSTRAP = ROOT / "dot_local/bin/executable_pct-bootstrap"

FAKE_PCT = r"""#!/usr/bin/env bash
# Minimal pct: config/listsnapshot/snapshot/delsnapshot on a file per guest.
state="$FAKE_PCT_STATE"; cmd="$1"; id="$2"
[[ -f "$state/$id" ]] || { echo "CT $id does not exist" >&2; exit 2; }
case "$cmd" in
  config) echo "hostname: ct$id" ;;
  listsnapshot)
    while read -r n; do echo "\`-> $n   2026-11-23 04:20:00   desc"; done < "$state/$id"
    echo " \`-> current   You are here!" ;;
  snapshot) echo "$3" >> "$state/$id" ;;
  delsnapshot) grep -vx -- "$3" "$state/$id" > "$state/$id.tmp"; mv "$state/$id.tmp" "$state/$id" ;;
  *) exit 3 ;;
esac
"""


class PctSnapshot(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        bindir = self.tmp / "bin"
        bindir.mkdir()
        pct = bindir / "pct"
        pct.write_text(FAKE_PCT)
        pct.chmod(pct.stat().st_mode | stat.S_IEXEC)
        self.state = self.tmp / "state"
        self.state.mkdir()
        self.env = dict(
            os.environ,
            PATH=f"{bindir}:/usr/bin:/bin",
            FAKE_PCT_STATE=str(self.state),
        )

    def guest(self, gid, snapshots):
        (self.state / gid).write_text("".join(f"{s}\n" for s in snapshots))

    def snaps(self, gid):
        return (self.state / gid).read_text().split()

    def run_snapshot(self, *args):
        return subprocess.run(
            ["bash", str(SNAPSHOT), *args],
            env=self.env,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_rotation_keeps_only_newest_managed(self):
        self.guest(
            "205",
            [
                "pre-orca",
                "auto-20261120-0420",
                "auto-20261121-0420",
                "auto-20261122-0420",
                "manual-before-upgrade",
            ],
        )
        r = self.run_snapshot("205", "--keep", "3")
        self.assertEqual(r.returncode, 0, r.stderr)
        snaps = self.snaps("205")
        self.assertIn("pre-orca", snaps)
        self.assertIn("manual-before-upgrade", snaps)
        autos = sorted(s for s in snaps if s.startswith("auto-"))
        self.assertEqual(len(autos), 3)
        self.assertNotIn("auto-20261120-0420", autos)
        self.assertIn("auto-20261122-0420", autos)

    def test_prefix_isolates_rotation(self):
        self.guest("101", ["auto-20261101-0420", "nightly-20261101-0300"])
        r = self.run_snapshot("101", "--keep", "1", "--prefix", "nightly")
        self.assertEqual(r.returncode, 0, r.stderr)
        snaps = self.snaps("101")
        self.assertIn("auto-20261101-0420", snaps)
        self.assertNotIn("nightly-20261101-0300", snaps)
        self.assertEqual(len([s for s in snaps if s.startswith("nightly-")]), 1)

    def test_list_shows_managed_only(self):
        self.guest("205", ["pre-orca", "auto-20261122-0420"])
        r = self.run_snapshot("--list", "205")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.split(), ["auto-20261122-0420"])

    def test_unknown_guest_fails(self):
        r = self.run_snapshot("999")
        self.assertNotEqual(r.returncode, 0)

    def test_rejects_bad_arguments(self):
        self.guest("205", [])
        for args in (["205", "--keep", "0"], ["20;5"], ["205", "--prefix", "a b"]):
            with self.subTest(args=args):
                self.assertNotEqual(self.run_snapshot(*args).returncode, 0)
        self.assertEqual(self.snaps("205"), [])

    def test_timer_needs_root_and_valid_time(self):
        text = SNAPSHOT.read_text()
        self.assertIn("--install-timer must run as root", text)
        self.assertIn("^([01][0-9]|2[0-3]):[0-5][0-9]$", text)
        self.assertIn("Persistent=true", text)
        # The unit runs a root-owned system copy, not root's chezmoi home.
        self.assertIn('INSTALL_PATH="/usr/local/sbin/pct-snapshot"', text)
        # A second guest's timer is installed from the installed copy itself.
        self.assertIn('|| install -m 0755 "$(readlink -f -- "$0")" "$INSTALL_PATH"', text)


class PctBootstrap(unittest.TestCase):
    text = BOOTSTRAP.read_text()

    def test_sudoers_rule_is_visudo_checked(self):
        self.assertIn('visudo -cf "$tmp"', self.text)
        self.assertIn("NOPASSWD:ALL", self.text)
        self.assertIn('chmod 0440 "$tmp"', self.text)

    def test_root_ssh_dropin_is_validated(self):
        self.assertIn("PermitRootLogin no", self.text)
        self.assertIn('"$SSHD" -t ||', self.text)
        # Restart, never reload: the SIGHUP re-exec killed sshd on Debian 13.
        self.assertIn(
            "systemctl try-restart ssh.service sshd.service >/dev/null 2>&1 || true",
            self.text,
        )
        self.assertNotIn("try-reload-or-restart ssh", self.text)
        # A daemon that died anyway is started again (not with ssh.socket active).
        self.assertIn("systemctl start ssh.service", self.text)
        self.assertIn("! systemctl is-active --quiet ssh.socket", self.text)

    def test_dns_fix_only_with_systemd_resolved(self):
        self.assertIn("/etc/.pve-ignore.resolv.conf", self.text)
        self.assertIn("/run/systemd/resolve/stub-resolv.conf", self.text)
        self.assertIn("systemctl is-active --quiet systemd-resolved", self.text)

    def test_parameters_go_through_env(self):
        # The in-container script is a quoted heredoc: no host-side expansion.
        self.assertIn("read -r -d '' INNER <<'INNER_EOF'", self.text)
        self.assertIn('bash -c "$INNER"', self.text)

    def test_rejects_bad_login_and_id(self):
        for args in (["205", "--user", "Bad User"], ["abc", "--user", "ok"], []):
            with self.subTest(args=args):
                r = subprocess.run(
                    ["bash", str(BOOTSTRAP), *args],
                    capture_output=True,
                    text=True,
                    check=False,
                    env=dict(os.environ, PATH="/usr/bin:/bin"),
                )
                self.assertNotEqual(r.returncode, 0)

    def test_scripts_parse(self):
        for script in (SNAPSHOT, BOOTSTRAP):
            with self.subTest(script=script.name):
                subprocess.run(["bash", "-n", str(script)], check=True)


if __name__ == "__main__":
    unittest.main()
