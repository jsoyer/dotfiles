#!/usr/bin/env python3
"""Sprint 3 appliances: OMV / PiKVM / Proxmox agent branches, OPNsense and Home Assistant
APIs, `fleet bootstrap`, and the routing / secrecy guarantees around them.

Nothing here contacts a real host, ntfy, Tailscale, 1Password, OPNsense or Home Assistant:
  * the agent runs for real (bash) in the sandbox of test_fleet_agent.py with fake
    rw / ro / pikvm-update / omv-upgrade / cloudflared / curl / qm binaries first on PATH;
  * the APIs talk to a local http.server on 127.0.0.1, allowed through the TEST-ONLY
    ``allow_hosts`` injection (the production URL policy is tested separately);
  * bootstrap runs with fake ssh / scp / ssh-keyscan / ssh-keygen / visudo scripts;
  * the live checks (real check / update on each type, real 403 probe) are BLOCKED.
"""

import base64
import json
import os
import re
import subprocess
import sys
import tempfile
import threading
import types
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / "dot_local/share/fleet/lib"
sys.path.insert(0, str(LIB))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import api_homeassistant as ha  # noqa: E402
import api_opnsense as opn  # noqa: E402
import bootstrap  # noqa: E402
import inventory as inv  # noqa: E402
import notify  # noqa: E402
import orchestrate  # noqa: E402
import schema  # noqa: E402
import state as fstate  # noqa: E402
import test_fleet_agent as ta  # noqa: E402  (module alias: its TestCases are not re-collected here)
import test_fleet_orchestrate as to  # noqa: E402

LINUX = sys.platform.startswith("linux")
KEY = "tk_" + "A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5"          # token-looking OPNsense API key
SECRET = "tk_" + "Z9y8X7w6V5u4T3s2R1q0P9o8N7m6L5"
JWT = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.c2lnbmF0dXJlLWZha2Utand0"
SECRET_GREP = re.compile(r"BEGIN [A-Z ]*PRIVATE KEY|tk_[A-Za-z0-9]{20,}|eyJ[A-Za-z0-9_-]{20,}\.")

REFS = {
    "op://V/I/key": KEY, "op://V/I/secret": SECRET, "op://V/I/hatoken": JWT,
}


def fake_op(args):
    if args[:2] != ["op", "read"] or args[2] not in REFS:
        raise OSError("op read failed")
    return REFS[args[2]] + "\n"


# ================================================================== agent branches


def _stub(sb, name, body):
    sb._script(sb.bin / name, "#!/usr/bin/env bash\n" + body)


def _real_sudo(sb):
    """A sudo that logs then runs the command: the agent calls exact absolute paths through it."""
    _stub(sb, "sudo", 'echo "sudo $*" >> "$STUB_DIR/sudo.log"\n[ "$1" = -n ] && shift\nexec "$@"\n')


@unittest.skipUnless(LINUX, "agent behaviour tests stub Linux tooling")
class AgentAppliance(unittest.TestCase):
    def setUp(self):
        self.sb = ta.Sandbox()
        self.addCleanup(self.sb.cleanup)
        _real_sudo(self.sb)

    def order(self):
        return [ln.split()[0] for ln in self.sb.read("order.log").splitlines()]

    def run_update(self, extra=None):
        env = {"FLEET_AGENT_CF_TRIES": "2", "FLEET_AGENT_CF_SLEEP": "0",
               "FLEET_AGENT_CF_READY_URL": "http://127.0.0.1:1/ready"}
        env.update(extra or {})
        proc = self.sb.run("update", env)
        self.assertEqual(self.sb.json_of(proc)["status"], "started", proc.stderr)
        return self.sb.wait_final(env)[1]

    # ---------------------------------------------------------------- OMV
    def _omv(self, rc=0):
        _stub(self.sb, "omv-upgrade",
              'echo "omv-upgrade fe=${DEBIAN_FRONTEND:-} args=$*" >> "$STUB_DIR/order.log"\n'
              'printf "openssl 3.0.14-1\\nbash 5.2-1\\n" > "$STUB_DIR/rpm.db"\n'
              'exit %d\n' % rc)

    def test_omv_uses_omv_upgrade_non_interactive_not_sysup_nor_apt(self):
        self._omv()
        final = self.run_update()
        self.assertEqual(final["status"], "updated", final)
        self.assertIn("omv-upgrade fe=noninteractive args=", self.sb.read("order.log"))
        calls = self.sb.read("calls.log")
        self.assertNotIn("sysup", calls)
        self.assertEqual([ln.split()[-1].rsplit("/", 1)[-1] for ln in self.sb.read("sudo.log").splitlines()], ["omv-upgrade"])

    def test_omv_failure_is_reported_with_its_exit_code(self):
        self._omv(rc=5)
        final = self.run_update()
        self.assertEqual(final["status"], "failed")
        self.assertEqual(final["reason"], "omv_upgrade_exit_5")

    # ---------------------------------------------------------------- PiKVM
    def _pikvm(self, update_rc=0, rw_rc=0, cf=True):
        _stub(self.sb, "rw", 'echo "rw" >> "$STUB_DIR/order.log"\nexit %d\n' % rw_rc)
        _stub(self.sb, "ro", 'echo "ro" >> "$STUB_DIR/order.log"\nexit 0\n')
        _stub(self.sb, "pikvm-update",
              'echo "pikvm-update" >> "$STUB_DIR/order.log"\n'
              'printf "openssl 3.0.14-1\\nbash 5.2-1\\n" > "$STUB_DIR/rpm.db"\nexit %d\n' % update_rc)
        _stub(self.sb, "curl",
              'echo "curl" >> "$STUB_DIR/order.log"\n'
              'n=$(cat "$STUB_DIR/curl.n" 2>/dev/null || echo 0); n=$((n+1)); echo $n > "$STUB_DIR/curl.n"\n'
              '[ "$n" -gt "${STUB_CURL_OK_FIRST:-0}" ] && [ "$n" -le "${STUB_CURL_FAIL_FIRST:-0}" ] && exit 22\nexit 0\n')
        self.cf = self.sb.root / "cloudflared"
        if cf:
            self.cf.write_text(
                "#!/usr/bin/env bash\nVER=1.0\n"
                'case "$1" in\n --version) echo "cloudflared version $VER";;\n'
                ' update) echo "cloudflared-update" >> "$STUB_DIR/order.log"\n'
                '   [ -n "${STUB_CF_NEWVER:-}" ] && sed -i "s/^VER=.*/VER=$STUB_CF_NEWVER/" "$0"\n'
                '   exit "${STUB_CF_RC:-0}";;\nesac\n')
            self.cf.chmod(0o755)
        self.base_env = {"FLEET_AGENT_CF_BIN": str(self.cf)}

    def pk(self, **extra):
        env = dict(self.base_env)
        env.update(extra)
        return self.run_update(env)

    def test_pikvm_update_failure_still_restores_ro(self):
        self._pikvm(update_rc=1)
        final = self.pk()
        self.assertEqual(final["status"], "failed")
        self.assertEqual(final["reason"], "pikvm_update_failed")
        self.assertEqual(self.order(), ["rw", "pikvm-update", "ro"])      # ONE rw window, ro last
        self.assertNotIn("cloudflared-update", self.order())

    def test_pikvm_rw_failure_still_calls_ro(self):
        self._pikvm(rw_rc=1)
        final = self.pk()
        self.assertEqual(final["reason"], "rw_failed")
        self.assertEqual(self.order(), ["rw", "ro"])

    def test_pikvm_happy_path_single_rw_window_cloudflared_unchanged_no_restart(self):
        self._pikvm()
        final = self.pk()
        self.assertEqual(final["status"], "updated", final)
        # the curl is the tunnel health probe made BEFORE the update (A3)
        self.assertEqual(self.order(), ["rw", "pikvm-update", "curl", "cloudflared-update", "ro"])
        self.assertNotIn("restart cloudflared", self.sb.read("calls.log"))   # version unchanged

    def test_pikvm_cloudflared_version_change_restarts_and_checks_tunnel(self):
        self._pikvm()
        final = self.pk(STUB_CF_NEWVER="2.0")
        self.assertEqual(final["status"], "updated", final)
        self.assertIn("restart cloudflared", self.sb.read("calls.log"))
        self.assertIn("curl", self.order())
        self.assertEqual(self.order()[-1], "ro")

    def test_pikvm_tunnel_down_restores_old_binary_and_keeps_a_copy(self):
        self._pikvm()
        # curl call 1 = healthy pre-update probe (old copy refreshed), 2-3 = tunnel down after update
        final = self.pk(STUB_CF_NEWVER="2.0", STUB_CURL_OK_FIRST="1", STUB_CURL_FAIL_FIRST="3")
        self.assertEqual(final["status"], "failed")
        self.assertEqual(final["reason"], "cloudflared_tunnel_down_restored")
        self.assertIn("VER=1.0", self.cf.read_text())                       # old version is back
        self.assertTrue((self.sb.state / "cloudflared.old").exists())
        self.assertEqual(self.order()[-1], "ro")

    def test_a1_rollback_renames_instead_of_overwriting_the_running_binary(self):
        self._pikvm()
        # a cp that refuses to write onto the cloudflared binary itself (ETXTBSY on a running one)
        _stub(self.sb, "cp", 'for a; do last="$a"; done\n'
                             '[ "$last" = "$STUB_CF" ] && { echo "Text file busy" >&2; exit 1; }\n'
                             'PATH=/usr/bin:/bin exec cp "$@"\n')
        final = self.pk(STUB_CF=str(self.cf), STUB_CF_NEWVER="2.0", STUB_CURL_OK_FIRST="1",
                        STUB_CURL_FAIL_FIRST="3")
        self.assertEqual(final["reason"], "cloudflared_tunnel_down_restored", final)
        self.assertIn("VER=1.0", self.cf.read_text())

    def test_a3_old_copy_is_kept_when_the_tunnel_was_not_healthy_before(self):
        self._pikvm()
        old = self.sb.state / "cloudflared.old"
        old.parent.mkdir(parents=True, exist_ok=True)
        old.write_text("LAST-GOOD\n")
        self.pk(STUB_CURL_FAIL_FIRST="99")
        self.assertEqual(old.read_text(), "LAST-GOOD\n")

    def test_a3_old_copy_is_refreshed_when_the_tunnel_was_healthy_before(self):
        self._pikvm()
        old = self.sb.state / "cloudflared.old"
        old.parent.mkdir(parents=True, exist_ok=True)
        old.write_text("STALE\n")
        self.pk()
        self.assertIn("VER=1.0", old.read_text())

    def test_a4_missing_systemctl_aborts_before_any_privileged_call(self):
        text = (ROOT / "dot_local/share/fleet/agent/fleet-agent.sh").read_text()
        lib = self.sb.root / "agent-lib.sh"
        lib.write_text(re.sub(r'(?m)^main "\$@"$', ":", text))
        cf = self.sb.root / "cf"
        cf.write_text("#!/bin/sh\necho v\n")
        cf.chmod(0o755)
        body = ('source "%s"\nSTATE_DIR="%s"\ntool_path() { return 0; }\n'
                'as_root() { echo "AS_ROOT $*"; }\nFLEET_AGENT_CF_BIN="%s"\npikvm_cloudflared; echo "rc=$?"\n'
                % (lib, self.sb.state, cf))
        proc = subprocess.run(["bash", "-c", body], capture_output=True, text=True, env=self.sb.env,
                              stdin=subprocess.DEVNULL)
        self.assertIn("rc=44", proc.stdout, proc.stderr)
        self.assertNotIn("AS_ROOT", proc.stdout)

    def test_a4_every_as_root_call_uses_an_absolute_path_variable(self):
        text = (ROOT / "dot_local/share/fleet/agent/fleet-agent.sh").read_text()
        calls = re.findall(r"^\s*(?:\w+=\S+ )*as_root (\S+)", text, re.M)
        self.assertTrue(calls)
        for first in calls:
            self.assertRegex(first, r'^"\$(cf|sc|rw|ro|pk|bin)"$|^"\$@"$', first)

    @unittest.skipIf(hasattr(os, "geteuid") and os.geteuid() == 0, "root can always write the binary")
    def test_pikvm_tunnel_down_without_write_access_asks_for_manual_restore(self):
        self._pikvm()
        # same sed target, but the binary is read-only for the agent account: closed sudoers
        # list has no command to write it, so the agent must say "restore by hand", not pretend.
        self.cf.chmod(0o555)
        final = self.pk(STUB_CF_NEWVER="2.0", STUB_CURL_FAIL_FIRST="99")
        self.assertEqual(final["status"], "failed")
        self.assertIn(final["reason"], ("cloudflared_update_failed",
                                        "cloudflared_tunnel_down_restore_by_hand"))
        self.assertEqual(self.order()[-1], "ro")

    def test_pikvm_kvmd_inactive_is_a_failure(self):
        self._pikvm()
        (self.sb.stub_dir / "down.list").write_text("kvmd\n")
        final = self.pk()
        self.assertEqual(final["reason"], "kvmd_inactive")
        self.assertEqual(self.order()[-1], "ro")

    def test_pikvm_tools_missing_fails_cleanly(self):
        # no rw / ro / pikvm-update on PATH but forced kind
        final = self.run_update({"FLEET_AGENT_KIND": "pikvm"})
        self.assertEqual(final["status"], "failed")

    # ---------------------------------------------------------------- Proxmox
    def _proxmox(self, vms=True):
        _stub(self.sb, "pveversion", "echo pve-manager/8.2\n")
        if vms:
            _stub(self.sb, "qm",
                  'echo "      VMID NAME                 STATUS     MEM(MB)    BOOTDISK(GB) PID"\n'
                  'echo "       100 web                  running    2048       32.00        1234"\n'
                  'echo "       101 db                   stopped    4096       64.00        0"\n')

    def test_proxmox_check_lists_vms_in_log_tail_without_a_new_verb(self):
        self._proxmox()
        proc = self.sb.run("check", {"STUB_DNF_PENDING": "3"})
        data = self.sb.json_of(proc)
        self.assertEqual(data["status"], "skipped")
        self.assertEqual(data["log_tail"].splitlines(), ["vm: 100 web running", "vm: 101 db stopped"])
        entry, why = schema.parse_agent_output(proc.stdout, "multibox", "check")
        self.assertIsNone(why)
        self.assertEqual(orchestrate.vm_lines(entry), ["100 web running", "101 db stopped"])

    def test_proxmox_check_without_qm_has_no_vm_lines(self):
        self._proxmox(vms=False)
        entry, _ = schema.parse_agent_output(self.sb.run("check").stdout, "multibox", "check")
        self.assertIsNone(orchestrate.vm_lines(entry))

    def test_proxmox_update_goes_through_sysup_and_never_reboots(self):
        self._proxmox()
        final = self.run_update({"STUB_RPM_AFTER": "openssl 3.0.14-1\\nbash 5.2-1"})
        self.assertIn(final["status"], ("updated", "up-to-date"))
        calls = self.sb.read("calls.log")
        self.assertIn("sysup", calls)
        self.assertNotIn("reboot", calls)
        self.assertNotIn("--reboot", calls)

    def test_agent_verb_whitelist_is_unchanged(self):
        text = ta.AGENT.read_text()
        self.assertIn("check|update|reboot-status|reboot|report) ;;", text)


# ================================================================== fake HTTP appliance servers


class FakeServer:
    """handler(method, path, headers, body) -> (status, obj_or_bytes[, extra_headers])."""

    def __init__(self, handler):
        self.requests = []
        self.lock = threading.Lock()
        outer = self

        class H(BaseHTTPRequestHandler):
            def _do(self):
                length = int(self.headers.get("Content-Length") or 0)
                body = self.rfile.read(length) if length else b""
                with outer.lock:
                    outer.requests.append((self.command, self.path, dict(self.headers), body))
                res = handler(self.command, self.path, dict(self.headers), body)
                status, payload = res[0], res[1]
                raw = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
                self.send_response(status)
                for k, v in (res[2] if len(res) > 2 else {}).items():
                    self.send_header(k, v)
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            do_GET = do_POST = _do

            def log_message(self, *args):
                pass

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.url = "http://127.0.0.1:%d" % self.httpd.server_address[1]
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    def stop(self):
        self.httpd.shutdown()
        self.httpd.server_close()

    def paths(self, method=None):
        return [(m, p) for m, p, _, _ in self.requests if method is None or m == method]


class ApiCase(unittest.TestCase):
    def setUp(self):
        self.clock = to.FakeClock()
        self.sent = []
        self.servers = []
        self.addCleanup(self._stop)

    def _stop(self):
        for s in self.servers:
            s.stop()

    def serve(self, handler):
        srv = FakeServer(handler)
        self.servers.append(srv)
        return srv

    def ctx(self, **kw):
        kw.setdefault("master", "diabolo")
        kw.setdefault("op", fake_op)
        kw.setdefault("allow_hosts", ("127.0.0.1",))
        kw.setdefault("sleep", self.clock.advance)
        kw.setdefault("now", self.clock.now)
        kw.setdefault("ping", lambda h: True)
        kw.setdefault("node_online", lambda h: True)
        kw.setdefault("notifier", self.sent.append)
        kw.setdefault("tailnet_name", "fw")
        kw.setdefault("poll_interval", 1.0)
        return opn.ApiContext(**kw)

    @staticmethod
    def data_for(srv, alias, **fields):
        return {"api": {alias: dict({"url": srv.url}, **fields)}}


def basic(key, secret):
    return "Basic " + base64.b64encode(("%s:%s" % (key, secret)).encode()).decode()


# ================================================================== OPNsense


class Opnsense(object):
    """Scriptable OPNsense firmware API. Time-based reboot window driven by the fake clock."""

    MINOR = {"status": "update", "updates": "2", "needs_reboot": "0", "product_version": "25.1.1",
             "upgrade_packages": [{"name": "opnsense", "old_version": "25.1.1", "new_version": "25.1.2"},
                                  {"name": "curl", "old_version": "8.1", "new_version": "8.2"}]}
    MAJOR = {"status": "upgrade", "updates": "0", "upgrade_major_version": "25.7",
             "product_version": "25.1.5", "needs_reboot": "0"}
    NONE = {"status": "none", "updates": "0", "needs_reboot": "0", "product_version": "25.1.2"}

    def __init__(self, clock, status, job=("running", "done"), reboot_down=None, forbidden=403,
                 stale=("done", "previous job"), stale_polls=0):
        self.clock, self.status, self.job = clock, dict(status), list(job)
        self.stale, self.stale_polls, self.started = stale, stale_polls, False
        self.reboot_down, self.down_until, self.forbidden = reboot_down, None, forbidden
        self.job_calls = 0
        self.updated = False

    def down(self):
        return self.down_until is not None and self.clock.now().timestamp() < self.down_until

    def __call__(self, method, path, headers, body):
        if self.down():
            return 503, {"error": "rebooting"}
        if headers.get("Authorization") != basic(KEY, SECRET):
            return 401, {"error": "auth"}
        if path == opn.EP_FIRMWARE_CHECK and method == "POST":
            return 200, {"status": "ok", "msg_uuid": "x"}
        if path == opn.EP_FIRMWARE_STATUS:
            return 200, self.status
        if path == opn.EP_FIRMWARE_UPDATE and method == "POST":
            self.updated = self.started = True
            return 200, {"status": "ok", "msg_uuid": "y"}
        if path == opn.EP_FIRMWARE_UPGRADESTATUS and (not self.started or self.stale_polls > 0):
            if self.started:
                self.stale_polls -= 1
            return 200, {"status": self.stale[0], "log": self.stale[1]}      # a PREVIOUS job's answer
        if path == opn.EP_FIRMWARE_UPGRADESTATUS:
            state = self.job[min(self.job_calls, len(self.job) - 1)]
            self.job_calls += 1
            if state in ("done", "reboot"):
                self.status = dict(self.NONE)
            if state == "reboot" and self.reboot_down is not None:
                self.down_until = self.clock.now().timestamp() + self.reboot_down
            return 200, {"status": state, "log": "..."}
        if path == opn.EP_FORBIDDEN_PROBE:
            return self.forbidden, {"status": self.forbidden}
        return 404, {}


class OpnsenseTest(ApiCase):
    def setUp(self):
        super().setUp()
        self.refs = {"key_ref": "op://V/I/key", "secret_ref": "op://V/I/secret"}

    def go(self, device, verb, ctx=None):
        srv = self.serve(device)
        self.srv = srv
        return opn.run(verb, "fw", self.data_for(srv, "fw", **self.refs), ctx or self.ctx())

    def test_check_reports_pending_minor_updates_and_flags_nothing_else(self):
        e = self.go(Opnsense(self.clock, Opnsense.MINOR), "check")
        self.assertEqual((e["status"], e["packages"], e["verb"]), ("skipped", 2, "check"))
        self.assertIsNone(e["major_available"])
        self.assertEqual(self.srv.paths("POST"), [("POST", opn.EP_FIRMWARE_CHECK)])

    def test_update_minor_applies_follows_the_job_and_reports_updated(self):
        dev = Opnsense(self.clock, Opnsense.MINOR)
        e = self.go(dev, "update")
        self.assertEqual(e["status"], "updated", e)
        self.assertTrue(dev.updated)
        self.assertEqual([c["name"] for c in e["changes"]], ["opnsense", "curl"])
        self.assertIn(("POST", opn.EP_FIRMWARE_UPDATE), self.srv.paths("POST"))

    def test_credentials_travel_in_a_basic_header_never_in_the_url(self):
        self.go(Opnsense(self.clock, Opnsense.MINOR), "check")
        for _, path, headers, _ in self.srv.requests:
            self.assertEqual(headers["Authorization"], basic(KEY, SECRET))
            self.assertNotIn(KEY, path)
            self.assertNotIn(SECRET, path)

    def test_major_release_is_reported_and_never_applied(self):
        dev = Opnsense(self.clock, Opnsense.MAJOR)
        e = self.go(dev, "update")
        self.assertEqual(e["status"], "up-to-date")
        self.assertEqual(e["major_available"], "25.7")
        self.assertFalse(dev.updated)
        posts = [p for m, p in self.srv.paths("POST")]
        self.assertNotIn(opn.EP_FIRMWARE_UPDATE, posts)        # no POST update
        self.assertNotIn(opn.EP_FIRMWARE_UPGRADE, posts)       # and no major upgrade either
        self.assertEqual(posts, [opn.EP_FIRMWARE_CHECK])

    def test_major_flag_kept_when_a_minor_update_is_also_applied(self):
        body = dict(Opnsense.MINOR, upgrade_major_version="25.7")
        e = self.go(Opnsense(self.clock, body), "update")
        self.assertEqual(e["status"], "updated")
        posts = [p for m, p in self.srv.paths("POST")]
        self.assertNotIn(opn.EP_FIRMWARE_UPGRADE, posts)

    def test_up_to_date_makes_no_update_call(self):
        e = self.go(Opnsense(self.clock, Opnsense.NONE), "update")
        self.assertEqual(e["status"], "up-to-date")
        self.assertEqual([p for m, p in self.srv.paths("POST")], [opn.EP_FIRMWARE_CHECK])

    def test_reboot_waits_for_ping_tailnet_and_api_then_succeeds(self):
        dev = Opnsense(self.clock, Opnsense.MINOR, job=("running", "reboot"), reboot_down=120)
        ctx = self.ctx(ping=lambda h: not dev.down(), node_online=lambda h: not dev.down())
        start = self.clock.now()
        e = self.go(dev, "update", ctx)
        self.assertEqual(e["status"], "updated", e)
        self.assertGreaterEqual((self.clock.now() - start).total_seconds(), 120)
        self.assertEqual(self.sent, [])

    def test_not_back_after_15_minutes_fails_and_notifies_priority_5(self):
        dev = Opnsense(self.clock, Opnsense.MINOR, job=("reboot",), reboot_down=10 ** 6)
        ctx = self.ctx(ping=lambda h: not dev.down(), node_online=lambda h: not dev.down())
        start = self.clock.now()
        e = self.go(dev, "update", ctx)
        waited = (self.clock.now() - start).total_seconds()
        self.assertEqual(e["status"], "failed")
        self.assertIn("did not come back", e["reason"])
        self.assertTrue(15 * 60 <= waited <= 20 * 60, waited)
        self.assertEqual([m["priority"] for m in self.sent], [5])

    def test_p4_minor_pending_with_a_major_available_is_never_up_to_date(self):
        body = dict(Opnsense.MINOR, status="upgrade", upgrade_major_version="25.7")
        e = self.go(Opnsense(self.clock, body), "check")
        self.assertEqual((e["status"], e["reason"], e["major_available"]), ("skipped", "updates_pending", "25.7"))
        dev = Opnsense(self.clock, body)
        e = self.go(dev, "update")
        self.assertNotEqual(e["status"], "up-to-date")
        self.assertEqual(e["major_available"], "25.7")
        posts = [p for m, p in self.srv.paths("POST")]
        self.assertIn(opn.EP_FIRMWARE_UPDATE, posts)
        self.assertNotIn(opn.EP_FIRMWARE_UPGRADE, posts)

    def test_p6_a_stale_terminal_state_from_a_previous_job_is_not_accepted(self):
        for stale in (("done", "previous job"), ("error", "previous job")):
            with self.subTest(stale=stale):
                dev = Opnsense(self.clock, Opnsense.MINOR, job=("running", "running", "done"),
                               stale=stale, stale_polls=3)
                e = self.go(dev, "update")
                self.assertEqual(e["status"], "updated", e)
                self.assertEqual(dev.status["status"], "none")

    def test_p6_a_job_finishing_before_it_is_seen_running_is_accepted_when_the_log_changed(self):
        dev = Opnsense(self.clock, Opnsense.MINOR, job=("done",))
        e = self.go(dev, "update")
        self.assertEqual(e["status"], "updated", e)

    def test_p6_a_job_that_never_starts_times_out_instead_of_trusting_the_stale_state(self):
        dev = Opnsense(self.clock, Opnsense.MINOR, stale_polls=10 ** 6)
        e = self.go(dev, "update")
        self.assertEqual(e["status"], "failed")
        self.assertIn("timeout", e["reason"])

    def test_p7_final_status_failing_after_the_return_retries_then_degrades_and_notifies(self):
        calls = {"n": 0}
        dev = Opnsense(self.clock, Opnsense.MINOR, job=("running", "done"))

        def handler(m, p, h, b):
            if p == opn.EP_FIRMWARE_STATUS and dev.updated and dev.job_calls >= 2:
                calls["n"] += 1
                return (503, {}) if calls["n"] <= 3 else dev(m, p, h, b)
            return dev(m, p, h, b)
        e = self.go(handler, "update")
        self.assertEqual(e["status"], "updated", e)                 # recovered within the deadline
        self.assertGreaterEqual(calls["n"], 4)
        dev2 = Opnsense(self.clock, Opnsense.MINOR, job=("running", "done"))

        def handler2(m, p, h, b):
            if p == opn.EP_FIRMWARE_STATUS and dev2.updated and dev2.job_calls >= 2:
                return 503, {}
            return dev2(m, p, h, b)
        self.sent[:] = []
        e = self.go(handler2, "update")
        self.assertEqual(e["status"], "degraded", e)
        self.assertTrue(e["reason"])
        self.assertEqual([m["priority"] for m in self.sent], [5])

    def test_p8_polling_has_an_iteration_guard_even_if_the_clock_never_moves(self):
        frozen = self.ctx(sleep=lambda s: None, now=lambda: to.START, poll_interval=15.0)
        n = {"calls": 0}

        def never():
            n["calls"] += 1
            return False
        self.assertFalse(opn.wait_until(frozen, never, 15))
        self.assertLessEqual(n["calls"], 15 * 60 / 15.0 + 2)

    def test_p2_verify_privileges_catches_everything_and_never_echoes_the_exception(self):
        srv = self.serve(Opnsense(self.clock, Opnsense.NONE))

        def boom(args):
            raise RuntimeError("secret " + KEY)
        res = opn.verify_privileges("fw", self.data_for(srv, "fw", **self.refs), self.ctx(op=boom))
        self.assertFalse(res["ok"])
        self.assertEqual(res["reason"], "internal error: RuntimeError")
        self.assertNotIn(KEY, json.dumps(res))

    def test_p2_verify_privileges_reason_is_cleaned(self):
        res = opn.verify_privileges("fw", {"api": {"fw": {"url": "https://a.ts.net", "key_ref": "op://V/I/key",
                                                          "secret_ref": "op://V/I/secret"}}},
                                    self.ctx(op=lambda a: "x\x1b[2J" + "y" * 1000, allow_hosts=()))
        self.assertFalse(res["ok"])
        self.assertNotIn("\x1b", res["reason"])
        self.assertLessEqual(len(res["reason"]), 200)

    def test_p3_secrets_with_control_characters_are_refused_without_echo(self):
        for bad in ("abc\ndef", "abc\rdef", "abc\x00def", "abc\x1bdef", "ab\tc", "abc\x7fdef"):
            with self.subTest(bad=repr(bad)):
                ctx = self.ctx(op=lambda a, b=bad: b + "\n")
                with self.assertRaises(opn.ApiError) as cm:
                    opn.read_secret(ctx, "op://V/I/key")
                self.assertNotIn("abc", str(cm.exception))
        self.assertEqual(opn.read_secret(self.ctx(op=lambda a: "  good-secret \n"), "op://V/I/key"), "good-secret")

    def test_verify_privileges_flags_a_user_that_can_leave_system_firmware(self):
        srv = self.serve(Opnsense(self.clock, Opnsense.NONE, forbidden=403))
        ok = opn.verify_privileges("fw", self.data_for(srv, "fw", **self.refs), self.ctx())
        self.assertTrue(ok["ok"], ok)
        self.assertIn((("GET", opn.EP_FORBIDDEN_PROBE)), srv.paths("GET"))
        srv2 = self.serve(Opnsense(self.clock, Opnsense.NONE, forbidden=200))
        bad = opn.verify_privileges("fw", self.data_for(srv2, "fw", **self.refs), self.ctx())
        self.assertFalse(bad["ok"])
        self.assertIn("too privileged", bad["reason"])

    # ----- hostile / broken answers and errors never leak or crash
    def test_invalid_json_is_failed_not_a_crash(self):
        e = self.go(lambda m, p, h, b: (200, b"{not json"), "check")
        self.assertEqual(e["status"], "failed")

    def test_non_object_json_is_failed(self):
        e = self.go(lambda m, p, h, b: (200, [1, 2, 3]), "check")
        self.assertEqual(e["status"], "failed")

    def test_oversized_response_is_refused(self):
        with mock.patch.object(opn, "MAX_RESPONSE", 64):
            e = self.go(lambda m, p, h, b: (200, b'{"status":"none","pad":"%s"}' % (b"x" * 500)), "check")
        self.assertEqual(e["status"], "failed")
        self.assertIn("too large", e["reason"])

    def test_redirect_is_refused_and_not_followed(self):
        other = self.serve(lambda m, p, h, b: (200, {"status": "none"}))
        e = self.go(lambda m, p, h, b: (302, b"", {"Location": other.url + "/steal"}), "check")
        self.assertEqual(e["status"], "failed")
        self.assertEqual(other.requests, [], "the Authorization header must not follow a redirect")

    def test_http_401_is_failed(self):
        srv = self.serve(Opnsense(self.clock, Opnsense.MINOR))
        ctx = self.ctx(op=lambda args: "wrong\n")
        e = opn.run("check", "fw", self.data_for(srv, "fw", **self.refs), ctx)
        self.assertEqual(e["status"], "failed")

    def test_unreachable_server_is_failed_without_leaking(self):
        srv = self.serve(lambda *a: (200, {}))
        url = srv.url
        srv.stop()
        self.servers.remove(srv)
        e = opn.run("check", "fw", {"api": {"fw": dict({"url": url}, **self.refs)}}, self.ctx())
        self.assertEqual(e["status"], "failed")
        self.assertNotIn(KEY, json.dumps(e))

    def test_1password_failure_is_failed_with_a_generic_reason(self):
        def broken(args):
            raise OSError("op: not signed in " + KEY)
        e = self.go(Opnsense(self.clock, Opnsense.NONE), "check", self.ctx(op=broken))
        self.assertEqual(e["status"], "failed")
        self.assertNotIn(KEY, json.dumps(e))
        self.assertEqual(self.srv.requests, [])

    def test_firmware_error_message_is_masked_in_the_entry(self):
        body = {"status": "error", "status_msg": "bad key %s and jwt %s" % (KEY, JWT)}
        e = self.go(lambda m, p, h, b: (200, body), "check")
        self.assertEqual(e["status"], "failed")
        text = json.dumps(e)
        self.assertNotIn(KEY, text)
        self.assertNotIn(JWT, text)

    def test_missing_api_parameters_are_failed(self):
        e = opn.run("check", "fw", {"api": {}}, self.ctx())
        self.assertEqual(e["status"], "failed")

    def test_unsupported_verbs_for_api_hosts(self):
        e = opn.run("reboot", "fw", {}, self.ctx())
        self.assertEqual(e["status"], "unsupported")


class UrlPolicyTest(unittest.TestCase):
    def test_accepts_https_ts_net_names_and_tailnet_literal_ips_only(self):
        for url in ("https://fw.tail1234.ts.net", "https://fw.tail1234.ts.net:8443", "http://100.64.1.2",
                    "http://100.127.255.254:8443", "https://100.64.0.9"):
            with self.subTest(url=url):
                opn.check_api_url(url)

    def test_p1_rejects_any_host_outside_the_tailnet_and_cleartext_to_names(self):
        for url in ("https://fw.example.org", "https://evil.com", "https://ts.net", "https://x.ts.net.evil.com",
                    "https://192.168.1.1", "https://8.8.8.8", "https://100.128.0.1", "https://100.63.255.255",
                    "http://fw.tail1234.ts.net", "https://[::1]", "https://localhost"):
            with self.subTest(url=url):
                with self.assertRaises(ValueError):
                    opn.check_api_url(url)

    def test_rejects_cleartext_elsewhere_credentials_paths_and_loopback(self):
        for url in ("http://fw.example.org", "http://192.168.1.1", "http://100.128.0.1", "ftp://x.ts.net",
                    "https://user:pw@fw.x.ts.net", "https://fw.x.ts.net/api", "https://fw.x.ts.net?x=1",
                    "http://127.0.0.1:8080", "", "https://"):
            with self.subTest(url=url):
                with self.assertRaises(ValueError):
                    opn.check_api_url(url)

    def test_loopback_only_through_the_explicit_test_injection(self):
        self.assertEqual(opn.check_api_url("http://127.0.0.1:9", allow_hosts=("127.0.0.1",)),
                         "http://127.0.0.1:9")

    def test_real_fleet_yml_api_parameters_follow_the_policy_and_use_op_references(self):
        data = inv.load_inventory(str(ROOT / "dot_local/share/fleet/fleet.yml"))
        for alias, params in data["api"].items():
            with self.subTest(alias=alias):
                self.assertIn(data["hosts"][alias]["kind"], ("opnsense", "homeassistant"))
                self.assertFalse(data["hosts"][alias].get("ssh_user"))
                opn.check_api_url(params["url"])
                refs = [v for k, v in params.items() if k.endswith("_ref")]
                self.assertTrue(refs and all(r.startswith("op://") for r in refs))
        self.assertEqual(set(data["api"]),
                         {"opnsense-amd64", "ha-dijon", "ha-nice", "ha-garage"})


# ================================================================== Home Assistant


class HomeAssistant(object):
    def __init__(self, clock, backup=("ok", 200), os_down=0, addon_name="SSH"):
        self.clock, self.backup, self.os_down = clock, backup, os_down
        self.down_until = None
        self.addons = {"core_ssh": ["1.0", "1.1", addon_name], "static": ["2.0", "2.0", "Static"]}
        self.core = ["2024.12.0", "2025.1.0"]            # a major-ish bump
        self.os = ["13.2", "14.0"]                        # a major OS bump
        self.posts = []
        self.core_fail = 0                                # HTTP status returned by the Core update POST
        self.os_status = 200                              # HTTP status returned by the OS update POST

    def down(self):
        return self.down_until is not None and self.clock.now().timestamp() < self.down_until

    def __call__(self, method, path, headers, body):
        if self.down():
            return 503, {}
        if headers.get("Authorization") != "Bearer " + JWT:
            return 401, {}
        if method == "POST":
            self.posts.append(path)
        if path == ha.EP_ADDONS:
            return 200, {"result": "ok", "data": {"addons": [
                {"slug": s, "name": v[2], "version": v[0], "version_latest": v[1],
                 "update_available": v[0] != v[1]} for s, v in self.addons.items()]}}
        if path == ha.EP_CORE_INFO:
            return 200, {"result": "ok", "data": {"version": self.core[0], "version_latest": self.core[1],
                                                  "update_available": self.core[0] != self.core[1]}}
        if path == ha.EP_OS_INFO:
            return 200, {"result": "ok", "data": {"version": self.os[0], "version_latest": self.os[1],
                                                  "update_available": self.os[0] != self.os[1]}}
        if path == ha.EP_BACKUP_FULL:
            state, code = self.backup
            return code, {"result": state, "data": {"slug": "abc"}}
        if path == ha.EP_CORE_UPDATE and self.core_fail:
            return self.core_fail, {"result": "error"}
        if path == ha.EP_CORE_UPDATE:
            self.core[0] = self.core[1]
            return 200, {"result": "ok"}
        if path == ha.EP_OS_UPDATE:
            self.os[0] = self.os[1]
            self.down_until = self.clock.now().timestamp() + self.os_down
            return self.os_status, {"result": "ok"}
        if path.startswith("/api/hassio/addons/") and path.endswith("/update"):
            slug = path.split("/")[4]
            self.addons[slug][0] = self.addons[slug][1]
            return 200, {"result": "ok"}
        if path == ha.EP_OWNER_ONLY_PROBE:
            return 403, {}
        return 404, {}


class HomeAssistantTest(ApiCase):
    def go(self, device, verb="update", ctx=None):
        srv = self.serve(device)
        self.srv = srv
        return ha.run(verb, "ha1", self.data_for(srv, "ha1", token_ref="op://V/I/hatoken"), ctx or self.ctx())

    def test_check_lists_pending_without_posting_anything(self):
        e = self.go(HomeAssistant(self.clock), "check")
        self.assertEqual((e["status"], e["packages"]), ("skipped", 3))
        self.assertEqual(self.srv.paths("POST"), [])

    def test_failed_backup_means_skipped_and_no_update_call_at_all(self):
        for backup in (("error", 200), ("ok", 500)):
            with self.subTest(backup=backup):
                dev = HomeAssistant(self.clock, backup=backup)
                e = self.go(dev, "update")
                self.assertEqual(e["status"], "skipped")
                self.assertIn("backup_failed", e["reason"])
                self.assertEqual(dev.posts, [ha.EP_BACKUP_FULL])        # nothing but the backup attempt
                self.assertEqual(dev.core[0], "2024.12.0")

    def test_backup_unreachable_is_skipped_too(self):
        dev = HomeAssistant(self.clock)

        def handler(m, p, h, b):
            if p == ha.EP_BACKUP_FULL:
                return 200, b"<html>not json</html>"
            return dev(m, p, h, b)
        e = self.go(handler)
        self.assertEqual(e["status"], "skipped")
        self.assertEqual(dev.posts, [])

    def test_major_updates_are_applied_after_a_successful_backup_in_order(self):
        dev = HomeAssistant(self.clock, os_down=120)
        ctx = self.ctx()
        e = self.go(dev, "update", ctx)
        self.assertEqual(e["status"], "updated", e)
        self.assertEqual(dev.posts, [ha.EP_BACKUP_FULL, ha.EP_ADDON_UPDATE % "core_ssh",
                                     ha.EP_CORE_UPDATE, ha.EP_OS_UPDATE])      # backup, add-ons, Core, OS last
        names = {c["name"]: (c["from"], c["to"]) for c in e["changes"]}
        self.assertEqual(names["Home Assistant OS"], ("13.2", "14.0"))
        self.assertEqual(names["Home Assistant Core"], ("2024.12.0", "2025.1.0"))
        self.assertEqual(self.sent, [])
        self.assertGreaterEqual(self.clock.now().timestamp() - to.START.timestamp(), 120)

    def test_os_update_not_back_in_15_minutes_notifies_priority_5(self):
        dev = HomeAssistant(self.clock, os_down=10 ** 6)
        start = self.clock.now()
        e = self.go(dev, "update")
        waited = (self.clock.now() - start).total_seconds()
        self.assertEqual(e["status"], "failed")
        self.assertIn("api_not_back", e["reason"])
        self.assertTrue(15 * 60 <= waited <= 17 * 60, waited)
        self.assertEqual([m["priority"] for m in self.sent], [5])

    def test_p9_restarting_core_or_os_answering_502_503_504_falls_through_to_the_version_wait(self):
        for code in (502, 503, 504):
            with self.subTest(code=code):
                dev = HomeAssistant(self.clock)
                dev.os_status = code
                e = self.go(dev, "update")
                self.assertEqual(e["status"], "updated", e)
                self.assertNotIn("refused", e.get("reason") or "")

    def test_p9_other_errors_are_still_refused(self):
        dev = HomeAssistant(self.clock)
        dev.core_fail = 401
        e = self.go(dev, "update")
        self.assertIn("refused", e["reason"])

    def test_p10_version_wait_accepts_update_available_false_or_absent(self):
        dev = HomeAssistant(self.clock)

        def handler(m, p, h, b):
            status, body = dev(m, p, h, b)[:2]
            if p == ha.EP_OS_INFO and dev.os[0] == dev.os[1]:
                return 200, {"result": "ok", "data": {"update_available": False}}      # version key absent
            return status, body
        e = self.go(handler, "update")
        self.assertEqual(e["status"], "updated", e)

    def test_p11_a_failed_core_update_never_proceeds_to_the_os_update(self):
        dev = HomeAssistant(self.clock)
        dev.core_fail = 500
        e = self.go(dev, "update")
        self.assertIn(e["status"], ("failed", "degraded"))
        self.assertIn("Core", e["reason"])
        self.assertNotIn(ha.EP_OS_UPDATE, dev.posts)
        self.assertEqual(dev.os[0], "13.2")

    def test_p2_verify_privileges_catch_all(self):
        srv = self.serve(HomeAssistant(self.clock))

        def boom(args):
            raise RuntimeError("leak " + JWT)
        res = ha.verify_privileges("ha1", self.data_for(srv, "ha1", token_ref="op://V/I/hatoken"), self.ctx(op=boom))
        self.assertEqual(res, {"ok": False, "reason": "internal error: RuntimeError"})

    def test_nothing_pending_makes_no_backup(self):
        dev = HomeAssistant(self.clock)
        dev.addons["core_ssh"][0] = "1.1"
        dev.core[0], dev.os[0] = dev.core[1], dev.os[1]
        e = self.go(dev)
        self.assertEqual(e["status"], "up-to-date")
        self.assertEqual(dev.posts, [])

    def test_bearer_header_only_and_token_not_in_urls(self):
        self.go(HomeAssistant(self.clock), "check")
        for _, path, headers, _ in self.srv.requests:
            self.assertEqual(headers["Authorization"], "Bearer " + JWT)
            self.assertNotIn(JWT, path)

    def test_hostile_add_on_name_is_masked_and_unsafe_slugs_are_ignored(self):
        dev = HomeAssistant(self.clock, addon_name="evil " + JWT + " " + KEY)
        dev.addons["../../etc"] = ["1", "2", "bad"]
        e = self.go(dev, "check")
        text = json.dumps(e)
        self.assertNotIn(JWT, text)
        self.assertNotIn(KEY, text)
        self.assertEqual(e["packages"], 3)                        # the unsafe slug is not counted

    def test_garbage_answers_are_failed(self):
        e = self.go(lambda m, p, h, b: (200, b"\xff\xfe not json"), "check")
        self.assertEqual(e["status"], "failed")

    def test_verify_privileges_requires_a_non_owner_user(self):
        dev = HomeAssistant(self.clock)
        srv = self.serve(dev)
        res = ha.verify_privileges("ha1", self.data_for(srv, "ha1", token_ref="op://V/I/hatoken"), self.ctx())
        self.assertTrue(res["ok"], res)
        srv2 = self.serve(lambda m, p, h, b: (200, {"data": {}}))
        res2 = ha.verify_privileges("ha1", self.data_for(srv2, "ha1", token_ref="op://V/I/hatoken"), self.ctx())
        self.assertFalse(res2["ok"])
        self.assertIn("too privileged", res2["reason"])


# ================================================================== orchestrator routing / secrecy


API_YML = """masters: [diabolo]
ntfy: {url: "https://ntfy.invalid", topic: fleet, token_ref: "op://V/I/f"}
parallel: {total: 10, per_site: 4}
%s
hosts:
%s"""


def api_hosts():
    def h(alias, kind, ssh=True, extra=""):
        crit = "true" if kind in ("opnsense", "proxmox") else "false"
        return ("  %s:\n    tailnet_name: %s\n    site: dijon\n    kind: %s\n    critical: %s\n%s%s"
                % (alias, alias, kind, crit, "    ssh_user: j\n" if ssh else "", extra))
    return (h("diabolo", "chezmoi-linux") + h("l1", "chezmoi-linux")
            + h("fw", "opnsense", ssh=False) + h("ha1", "homeassistant", ssh=False, extra="    tags: [infra]\n")
            + h("px", "proxmox"))


class RoutingBase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name)
        self.clock = to.FakeClock()
        self.servers = []
        self.addCleanup(lambda: [s.stop() for s in self.servers])
        self.sent = []
        self.root = self.tmp / "state"

    def build(self, opn_status=None, ha_dev=None):
        opn_dev = Opnsense(self.clock, opn_status or Opnsense.MINOR)
        ha_dev = ha_dev or HomeAssistant(self.clock)
        s1, s2 = FakeServer(opn_dev), FakeServer(ha_dev)
        self.servers += [s1, s2]
        self.opn_dev, self.ha_dev, self.opn_srv, self.ha_srv = opn_dev, ha_dev, s1, s2
        api = ("api:\n  fw: {url: \"%s\", key_ref: \"op://V/I/key\", secret_ref: \"op://V/I/secret\"}\n"
               "  ha1: {url: \"%s\", token_ref: \"op://V/I/hatoken\"}" % (s1.url, s2.url))
        yml = self.tmp / "fleet.yml"
        yml.write_text(API_YML % (api, api_hosts()))
        self.data = inv.load_inventory(str(yml))
        self.st = fstate.State(self.root, "diabolo", now=self.clock.now)

        def sender(url, topic, headers, body):
            self.sent.append((headers["Title"], int(headers["Priority"]), headers["Tags"], body))
        self.notifier = notify.Notifier("https://ntfy.invalid", "fleet", to.FAKE_TOKEN,
                                        self.root / "ntfy-queue", sender=sender, clock=self.clock.now)

    def orch(self, tr, **opts):
        opts.setdefault("sleep", self.clock.advance)
        opts.setdefault("poll_interval", 1.0)
        return orchestrate.Orchestrator(self.data, self.st, "diabolo", tr, self.notifier,
                                        orchestrate.Options(**opts), now=self.clock.now)


class ApiFakeTransport(to.FakeTransport):
    """FakeTransport whose `api` seam dispatches to the REAL api modules against local servers."""

    def __init__(self, data):
        super().__init__(data)
        self.api_calls = []

    def api(self, alias, verb, ctx):
        self.api_calls.append((alias, verb))
        ctx.op, ctx.allow_hosts = fake_op, ("127.0.0.1",)
        ctx.ping, ctx.node_online = (lambda h: True), (lambda h: True)
        return orchestrate.run_api(self.data_hosts[alias]["kind"], verb, alias, self.api_data, ctx)


class Routing(RoutingBase):
    def transport(self, **kw):
        tr = ApiFakeTransport(self.data)
        tr.data_hosts, tr.api_data = self.data["hosts"], self.data
        return tr

    def test_fleet_up_without_critical_touches_neither_opnsense_nor_multibox(self):
        self.build()
        tr = self.transport()
        rep, rc = self.orch(tr).run_up(list(self.data["hosts"]), "all")
        by = dict((e["host"], e) for e in rep["hosts"])
        self.assertEqual(by["fw"]["status"], "skipped")
        self.assertEqual(by["px"]["status"], "skipped")
        self.assertIn("--critical", by["fw"]["reason"])
        for alias in ("fw", "px"):
            self.assertNotIn(alias, [a for a, _, _ in tr.calls])           # zero transport calls
        self.assertNotIn("fw", [a for a, _ in tr.api_calls])              # zero API calls
        self.assertEqual(self.opn_srv.requests, [])
        self.assertEqual(tr.api_calls, [("ha1", "update")])               # HA is not critical: it runs

    def test_critical_run_does_opnsense_then_multibox_with_vm_warning_and_confirmation(self):
        self.build()
        tr = self.transport()
        said, asked = [], []
        tr.list_vms = lambda alias: ["100 web running", "101 db stopped"]
        rep, _ = self.orch(tr, critical=True, say=said.append,
                           confirm=lambda p: asked.append(p) or True).run_up(["fw", "px"], "fw,px")
        by = dict((e["host"], e) for e in rep["hosts"])
        self.assertEqual(by["fw"]["status"], "updated")
        self.assertEqual(by["px"]["status"], "updated")
        self.assertEqual(len(asked), 2)
        warning = [s for s in said if "px" in s and "VMs that will be interrupted" in s]
        self.assertTrue(warning and "100 web running" in warning[0] and "101 db stopped" in warning[0], said)
        self.assertEqual(tr.api_calls, [("fw", "update")])
        self.assertTrue(self.opn_dev.updated)
        # OPNsense BEFORE multibox
        self.assertEqual([("fw" in p, "px" in p) for p in asked], [(True, False), (False, True)])  # OPNsense THEN multibox

    def test_declined_confirmation_leaves_opnsense_untouched(self):
        self.build()
        tr = self.transport()
        rep, _ = self.orch(tr, critical=True, confirm=lambda p: False).run_up(["fw"], "fw")
        self.assertEqual(rep["hosts"][0]["status"], "skipped")
        self.assertEqual(self.opn_srv.requests, [])

    def test_api_hosts_have_no_reboot_verb(self):
        self.build()
        tr = self.transport()
        rep, _ = self.orch(tr, critical=True, confirm=lambda p: True).run_reboot(["fw"], "fw")
        self.assertEqual(rep["hosts"][0]["status"], "skipped")
        self.assertEqual(self.opn_srv.requests, [])

    def test_offline_api_host_is_offline_without_any_request(self):
        self.build()
        tr = self.transport()
        tr.online["ha1"] = False
        rep, _ = self.orch(tr).run_up(["ha1"], "ha1")
        self.assertEqual(rep["hosts"][0]["status"], "offline")
        self.assertEqual(self.ha_srv.requests, [])

    def test_vm_list_unavailable_falls_back_to_the_generic_warning(self):
        self.build()
        tr = self.transport()
        tr.list_vms = lambda alias: None
        said = []
        self.orch(tr, critical=True, say=said.append, confirm=lambda p: False).run_up(["px"], "px")
        self.assertTrue(any("VM list unavailable" in s for s in said), said)

    def test_ssh_transport_list_vms_reads_the_check_log_tail(self):
        tail = "vm: 100 web running\nvm: 101 db stopped"
        out = to.agent_line("px", "check", "skipped", log_tail=tail)
        fake = types.SimpleNamespace(call=lambda alias, verb: (0, out, ""))
        self.assertEqual(orchestrate.SshTransport.list_vms(fake, "px"), ["100 web running", "101 db stopped"])
        none = types.SimpleNamespace(call=lambda alias, verb: (255, "", "ssh: down"))
        self.assertIsNone(orchestrate.SshTransport.list_vms(none, "px"))
        garbage = types.SimpleNamespace(call=lambda alias, verb: (0, "not json", ""))
        self.assertIsNone(orchestrate.SshTransport.list_vms(garbage, "px"))

    def test_o2_hostile_log_tail_lines_never_reach_the_warning(self):
        hostile = ("vm: 100 web running\n"
                   "vm: 101 \x1b[2J\x1b]0;pwned\x07evil running\n"
                   "vm: 102 db stopped\x1b[31m\n"
                   "vm: 103 ok-name_1.x running\n"
                   "vm: 1234567 toolong running\n"
                   "vm: 104 spaced name running\n"
                   "vm: 105 a RUNNING\n"
                   "\x1b[2Jvm: 106 x running\n")
        out = to.agent_line("px", "check", "skipped", log_tail=hostile)
        fake = types.SimpleNamespace(call=lambda alias, verb: (0, out, ""))
        got = orchestrate.SshTransport.list_vms(fake, "px")
        # (the agent-line sanitiser already strips escape sequences; the strict shape is the second layer)
        self.assertTrue(got)
        for vm in got:
            self.assertRegex(vm, r"^[0-9]{1,6} [A-Za-z0-9._-]{1,63} [a-z]{1,16}$")
        joined = " ".join(got)
        for bad in ("pwned", "evil", "toolong", "spaced", "RUNNING", "\x1b", "\x07"):
            self.assertNotIn(bad, joined)
        self.assertIn("100 web running", got)
        self.assertIn("103 ok-name_1.x running", got)

    def test_o2_vm_lines_are_capped_at_50(self):
        tail = "\n".join("vm: %d v%d running" % (i, i) for i in range(200))
        self.assertEqual(len(orchestrate.vm_lines({"log_tail": tail})), 50)

    def test_o2_warning_strips_control_characters_even_from_a_custom_transport(self):
        self.build()
        tr = self.transport()
        tr.list_vms = lambda alias: ["100 we\x1b[2Jb\x1b]0;x\x07 running"]
        said = []
        self.orch(tr, critical=True, say=said.append, confirm=lambda p: False).run_up(["px"], "px")
        warning = next(s for s in said if "critical" in s)
        self.assertNotIn("\x1b", warning)
        self.assertNotIn("\x07", warning)

    def test_production_transport_routes_api_hosts_through_the_api_modules(self):
        self.build()
        data = self.data

        class Tr(orchestrate.SshTransport):
            def peers(self):
                return dict((h["tailnet_name"], {"online": True, "last_seen": None, "os": "x", "tags": []})
                            for h in data["hosts"].values())

            def probe(self, alias):
                return True

            def call(self, alias, verb, timeout=60):
                raise AssertionError("no ssh for %s" % alias)

            def sync(self, master, peers):
                return True

        tr = Tr(self.data, {})
        ctx = opn.ApiContext(master="diabolo", op=fake_op, allow_hosts=("127.0.0.1",), sleep=self.clock.advance,
                             now=self.clock.now, ping=lambda h: True, node_online=lambda h: True)
        entry = tr.api("fw", "check", ctx)
        self.assertEqual((entry["status"], entry["packages"]), ("skipped", 2))


class NoSecretOnDisk(RoutingBase):
    """A simulated API run with token-looking secrets leaves none in runs/, logs, ntfy queue or notifications."""

    def test_no_secret_anywhere_in_the_state_dir_or_notifications(self):
        hostile_opn = dict(Opnsense.MINOR, status_msg="key %s secret %s" % (KEY, SECRET))
        ha_dev = HomeAssistant(self.clock, os_down=10 ** 6, addon_name="x " + JWT)
        self.build(opn_status=hostile_opn, ha_dev=ha_dev)
        tr = ApiFakeTransport(self.data)
        tr.data_hosts, tr.api_data = self.data["hosts"], self.data
        # the notifier is also asked to refuse delivery once so the durable queue gets exercised
        calls = {"n": 0}

        def flaky(url, topic, headers, body):
            calls["n"] += 1
            if calls["n"] == 1:
                raise OSError("down")
            self.sent.append((headers["Title"], int(headers["Priority"]), headers["Tags"], body))
        self.notifier.sender = flaky
        rep, rc = self.orch(tr, critical=True, confirm=lambda p: True).run_up(["fw", "ha1", "px"], "all")
        self.assertEqual(dict((e["host"], e["status"]) for e in rep["hosts"])["ha1"], "failed")   # OS never back
        files = [p for p in self.root.rglob("*") if p.is_file()]
        self.assertTrue(any("runs" in str(p) for p in files), "the run must have been written")
        blob = b"".join(p.read_bytes() for p in files) + json.dumps(self.sent).encode()
        for secret in (KEY, SECRET, JWT):
            self.assertNotIn(secret.encode(), blob)
        self.assertIsNone(SECRET_GREP.search(blob.decode("utf-8", "replace")))
        self.assertTrue(self.sent, "a priority-5 notification was expected")
        for p in files:
            self.assertEqual(p.stat().st_mode & 0o077, 0, "state files are private: %s" % p)


# ================================================================== bootstrap


FAKE_SSH = r"""#!/usr/bin/env bash
echo "ssh $*" >> "$FAKE_LOG"
last="${@: -1}"
case "$last" in
  *fleet-verify*)
    for p in ${last##*fleet-verify }; do
      case " ${FAKE_VERIFY_BAD:-} " in *" $p "*) echo "BAD $p" ;; *) echo "OK $p" ;; esac
    done
    [ -n "${FAKE_VERIFY_GARBAGE:-}" ] && echo "$FAKE_VERIFY_GARBAGE" ;;
  *"command -v "*)
    name="${last##* command -v }"
    case "$name" in
      omv-upgrade) echo /usr/sbin/omv-upgrade ;;
      rw) echo /usr/local/bin/rw ;;
      ro) echo /usr/local/bin/ro ;;
      pikvm-update) echo /usr/bin/pikvm-update ;;
      systemctl) echo /usr/bin/systemctl ;;
      visudo) echo /usr/sbin/visudo ;;
      *) exit 1 ;;
    esac ;;
  "mktemp -d") echo "${FAKE_MKTEMP:-/tmp/fleet.Ab12Cd}" ;;
  sh\ /tmp/fleet.Ab12Cd/apply.sh*) echo "fleet-bootstrap: done"; exit "${FAKE_APPLY_RC:-0}" ;;
esac
exit 0
"""


def shlex_q(text):
    import shlex
    return shlex.quote(text)


SHA_A = "a" * 64
SHA_S = "b" * 64


class BootstrapBase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name)
        self.log = self.tmp / "calls.log"
        self.log.write_text("")
        bin_dir = self.tmp / "bin"
        bin_dir.mkdir()
        self.fakes = {}
        for name, body in {
            "ssh": FAKE_SSH,
            "scp": '#!/usr/bin/env bash\necho "scp $*" >> "$FAKE_LOG"\nexit "${FAKE_SCP_RC:-0}"\n',
            "ssh-keyscan": '#!/usr/bin/env bash\necho "keyscan $*" >> "$FAKE_LOG"\n'
                           'echo "# host"\necho "${@: -1} ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIFakeHostKeyForTests"\n',
            "ssh-keygen": '#!/usr/bin/env bash\nif [ "$1" = -F ]; then grep -F "$2 " "$4"; exit $?; fi\n'
                          'echo "256 SHA256:FakeFingerprint host (ED25519)"\n',
            "visudo": '#!/usr/bin/env bash\necho "visudo $*" >> "$FAKE_LOG"\nexit "${FAKE_VISUDO_RC:-0}"\n',
        }.items():
            path = bin_dir / name
            path.write_text(body)
            path.chmod(0o755)
            self.fakes[name] = str(path)
        self.known_hosts = self.tmp / "known_hosts"
        agent = self.tmp / "fleet-agent.sh"
        agent.write_text("#!/usr/bin/env bash\necho agent\n")
        self.agent = agent
        yml = self.tmp / "fleet.yml"
        yml.write_text(
            "masters: [diabolo, penelope]\nhosts:\n"
            + "".join("  %s:\n    tailnet_name: %s\n    site: dijon\n    kind: %s\n    critical: %s\n"
                      "    ssh_user: j\n" % (a, a, k, c) for a, k, c in (
                          ("diabolo", "chezmoi-linux", "false"), ("penelope", "chezmoi-linux", "false")))
            + "  omv1:\n    tailnet_name: omv1\n    site: dijon\n    kind: omv\n    critical: false\n"
            + "  pk:\n    tailnet_name: pk\n    site: dijon\n    kind: pikvm\n    critical: false\n"
            + "  fw:\n    tailnet_name: fw\n    site: dijon\n    kind: opnsense\n    critical: true\n")
        self.env = {
            "FLEET_YML": str(yml), "FLEET_SSH": self.fakes["ssh"], "FLEET_SCP": self.fakes["scp"],
            "FLEET_SSH_KEYSCAN": self.fakes["ssh-keyscan"], "FLEET_SSH_KEYGEN": self.fakes["ssh-keygen"],
            "FLEET_VISUDO": self.fakes["visudo"], "FLEET_KNOWN_HOSTS": str(self.known_hosts),
            "FAKE_LOG": str(self.log), "PATH": os.environ["PATH"], "HOME": str(self.tmp),
        }

    @staticmethod
    def op(args):
        master = args[2].rsplit("-", 1)[1]
        return "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAI%sKey comment\n" % master.capitalize()

    def boot(self, argv, confirm=None, op=None, env=None):
        import io
        out, err = io.StringIO(), io.StringIO()
        e = dict(self.env)
        e.update(env or {})
        rc = bootstrap.main(argv, env=e, confirm=confirm, op=op or self.op, out=out, err=err,
                            agent_path=str(self.agent))
        return rc, out.getvalue(), err.getvalue()

    def calls(self):
        return self.log.read_text().splitlines()


class SudoersFragment(unittest.TestCase):
    OMV_PATHS = {"omv-upgrade": "/usr/sbin/omv-upgrade", "systemctl": "/usr/bin/systemctl"}
    PIKVM_PATHS = {"rw": "/usr/local/bin/rw", "ro": "/usr/local/bin/ro", "pikvm-update": "/usr/bin/pikvm-update",
                   "systemctl": "/usr/bin/systemctl"}

    def test_omv_fragment_is_exactly_the_closed_list(self):
        text = bootstrap.render_sudoers("omv", "fleetsvc", self.OMV_PATHS)
        self.assertEqual(bootstrap.granted_commands(text), ['/usr/sbin/omv-upgrade ""', "/usr/bin/systemctl reboot"])

    def test_pikvm_fragment_is_exactly_the_closed_list(self):
        text = bootstrap.render_sudoers("pikvm", "fleetsvc", self.PIKVM_PATHS)
        self.assertEqual(bootstrap.granted_commands(text), [
            '/usr/local/bin/rw ""', '/usr/local/bin/ro ""', '/usr/bin/pikvm-update ""',
            "/usr/local/bin/cloudflared update", "/usr/bin/systemctl restart cloudflared",
            "/usr/bin/systemctl reboot"])

    def test_no_argument_commands_get_an_explicit_empty_argument_list(self):
        # sudoers: a command without an argument list allows ANY argument; `""` allows none.
        for kind, paths in (("omv", self.OMV_PATHS), ("pikvm", self.PIKVM_PATHS)):
            lines = [ln for ln in bootstrap.render_sudoers(kind, "fleetsvc", paths).splitlines()
                     if "NOPASSWD:" in ln]
            self.assertEqual(len(lines), len(bootstrap.CLOSED_LIST[kind]), kind)
            for (program, args), line in zip(bootstrap.CLOSED_LIST[kind], lines):
                if args:
                    self.assertFalse(line.endswith('""'), (kind, line))
                    self.assertTrue(line.endswith(" " + " ".join(args)), (kind, line))
                else:
                    self.assertTrue(line.endswith(' ""'), (kind, line))
                    self.assertEqual(line.count('""'), 1, (kind, line))

    def test_no_wildcard_no_shell_no_systemd_run_no_all_commands(self):
        for kind, paths in (("omv", self.OMV_PATHS), ("pikvm", self.PIKVM_PATHS)):
            text = "\n".join(ln for ln in bootstrap.render_sudoers(kind, "fleetsvc", paths).splitlines()
                             if not ln.startswith("#"))
            for bad in ("*", "ALL=(ALL", "systemd-run", "/bin/sh", "bash", "NOPASSWD: ALL", "apt"):
                self.assertNotIn(bad, text.replace("ALL=(root)", "").replace("Defaults!", ""), (kind, bad))

    def test_escapes_colon_equal_comma_backslash(self):
        self.assertEqual(bootstrap.sudoers_escape("a:b=c,d\\e"), "a\\:b\\=c\\,d\\\\e")
        text = bootstrap.render_sudoers("omv", "u", {"omv-upgrade": "/opt/a+b/omv-upgrade",
                                                       "systemctl": "/usr/bin/systemctl"})
        self.assertIn("/opt/a+b/omv-upgrade", text)

    def test_unsafe_inputs_are_refused(self):
        with self.assertRaises(bootstrap.BootstrapError):
            bootstrap.render_sudoers("omv", "bad user;", self.OMV_PATHS)
        with self.assertRaises(bootstrap.BootstrapError):
            bootstrap.render_sudoers("omv", "u", {"omv-upgrade": "relative/omv-upgrade", "systemctl": "/usr/bin/systemctl"})
        with self.assertRaises(bootstrap.BootstrapError):
            bootstrap.render_sudoers("omv", "u", {"omv-upgrade": "/usr/sbin/../bin/x y", "systemctl": "/usr/bin/systemctl"})
        with self.assertRaises(bootstrap.BootstrapError):
            bootstrap.render_sudoers("windows", "u", {})

    @unittest.skipUnless(bootstrap.find_visudo({}), "visudo not installed")
    def test_real_visudo_accepts_the_rendered_fragments(self):
        visudo = bootstrap.find_visudo({})
        for kind, paths in (("omv", self.OMV_PATHS), ("pikvm", self.PIKVM_PATHS)):
            with tempfile.TemporaryDirectory() as d:
                ok, msg = bootstrap.validate_fragment(
                    bootstrap.render_sudoers(kind, "fleetsvc", paths), {},
                    lambda cmd, t: tuple(self._run(cmd)), Path(d))
                self.assertTrue(ok, (kind, msg))
                proc = subprocess.run([visudo, "-cf", str(Path(d) / "fleet-sudoers")],
                                      capture_output=True, text=True)
                self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    @unittest.skipUnless(bootstrap.find_visudo({}), "visudo not installed")
    def test_real_visudo_rejects_a_broken_fragment(self):
        with tempfile.TemporaryDirectory() as d:
            ok, _ = bootstrap.validate_fragment("this is not sudoers (\n", {},
                                                lambda cmd, t: tuple(self._run(cmd)), Path(d))
            self.assertFalse(ok)

    @staticmethod
    def _run(cmd):
        proc = subprocess.run(cmd, capture_output=True, text=True)
        return proc.returncode, proc.stdout, proc.stderr


class BootstrapFlow(BootstrapBase):
    def test_dry_run_is_the_default_and_applies_nothing(self):
        rc, out, err = self.boot(["omv1", "--user", "fleetsvc"])
        self.assertEqual(rc, 0, err)
        self.assertIn("DRY RUN", out)
        self.assertIn("/usr/sbin/omv-upgrade", out)
        self.assertIn("visudo -cf", out)
        self.assertIn('restrict,command="/usr/local/libexec/fleet-agent"', out)
        joined = "\n".join(self.calls())
        self.assertNotIn("scp ", joined)
        self.assertNotIn("mktemp", joined)
        self.assertNotIn("apply.sh", joined)
        self.assertFalse(self.known_hosts.exists())

    def test_apply_without_a_terminal_is_declined(self):
        # default confirmation: stdin is not a tty under pytest => declined
        rc, out, err = self.boot(["omv1", "--user", "fleetsvc", "--apply"])
        self.assertEqual(rc, 1)
        self.assertIn("not confirmed", err)
        self.assertNotIn("scp ", "\n".join(self.calls()))
        self.assertFalse(self.known_hosts.exists())

    def test_apply_explicitly_declined(self):
        rc, _, err = self.boot(["pk", "--user", "root", "--apply"], confirm=lambda alias: False)
        self.assertEqual(rc, 1)
        self.assertNotIn("apply.sh", "\n".join(self.calls()))

    def test_confirmation_is_shown_the_fragment_before_it_is_asked(self):
        seen = []

        def confirm(alias):
            seen.append(alias)
            return False
        rc, out, _ = self.boot(["omv1", "--user", "fleetsvc", "--apply"], confirm=confirm)
        self.assertEqual(seen, ["omv1"])
        self.assertIn("NOPASSWD: /usr/sbin/omv-upgrade", out)           # shown before asking

    def test_apply_confirmed_copies_runs_the_script_and_pins_the_host_key(self):
        rc, out, err = self.boot(["omv1", "--user", "fleetsvc", "--apply"], confirm=lambda a: True)
        self.assertEqual(rc, 0, err)
        calls = self.calls()
        idx = {"mktemp": next(i for i, c in enumerate(calls) if "mktemp" in c),
               "scp ": next(i for i, c in enumerate(calls) if c.startswith("scp")),
               "apply.sh": next(i for i, c in enumerate(calls) if c.startswith("ssh") and " sh /tmp" in c)}
        self.assertLess(idx["mktemp"], idx["scp "])
        self.assertLess(idx["scp "], idx["apply.sh"])
        scp = calls[idx["scp "]]
        for name in ("fleet-agent", "fleet-sudoers", "authorized.lines", "apply.sh"):
            self.assertIn(name, scp)
        self.assertIn("fleetsvc@omv1", scp)
        self.assertIn("omv1 ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIFakeHostKeyForTests", self.known_hosts.read_text())
        self.assertEqual(self.known_hosts.stat().st_mode & 0o777, 0o600)

    def test_failed_apply_pins_nothing_and_reports(self):
        rc, _, err = self.boot(["omv1", "--user", "fleetsvc", "--apply"], confirm=lambda a: True,
                               env={"FAKE_APPLY_RC": "3"})
        self.assertEqual(rc, 2)
        self.assertFalse(self.known_hosts.exists())

    def test_invalid_fragment_blocks_apply(self):
        rc, _, err = self.boot(["omv1", "--user", "fleetsvc", "--apply"], confirm=lambda a: True,
                               env={"FAKE_VISUDO_RC": "1"})
        self.assertEqual(rc, 2)
        self.assertNotIn("scp ", "\n".join(self.calls()))

    def test_missing_master_key_blocks_apply_but_not_dry_run(self):
        def op(args):
            raise OSError("locked")
        rc, out, _ = self.boot(["omv1", "--user", "fleetsvc"], op=op)
        self.assertEqual(rc, 0)
        self.assertIn("WARNING: no usable public key", out)
        rc, _, err = self.boot(["omv1", "--user", "fleetsvc", "--apply"], confirm=lambda a: True, op=op)
        self.assertEqual(rc, 2)
        self.assertNotIn("scp ", "\n".join(self.calls()))

    def test_malformed_public_key_is_rejected(self):
        rc, out, _ = self.boot(["omv1", "--user", "fleetsvc"], op=lambda a: "ssh-rsa AAAA bad\n")
        self.assertIn("WARNING: no usable public key", out)

    def test_unsupported_kinds_and_unknown_hosts(self):
        for host in ("fw", "diabolo", "nope"):
            rc, _, err = self.boot([host, "--user", "u"])
            self.assertEqual(rc, 2, host)
        rc, _, _ = self.boot(["omv1", "--user", "bad user"])
        self.assertEqual(rc, 2)

    def test_path_override_skips_the_remote_lookup(self):
        rc, out, _ = self.boot(["omv1", "--user", "u", "--path", "omv-upgrade=/opt/omv/omv-upgrade",
                                "--path", "systemctl=/bin/systemctl", "--path", "visudo=/usr/sbin/visudo"])
        self.assertEqual(rc, 0)
        self.assertIn("/opt/omv/omv-upgrade", out)
        self.assertNotIn("command -v", "\n".join(self.calls()))

    def test_pikvm_script_runs_everything_in_one_rw_window_with_an_ro_trap(self):
        rc, _, err = self.boot(["pk", "--user", "root", "--apply"], confirm=lambda a: True)
        self.assertEqual(rc, 0, err)
        self.assertEqual(sum(1 for c in self.calls() if "apply.sh" in c and c.startswith("ssh")), 1)
        script = bootstrap.apply_script("pikvm", ["diabolo", "penelope"], {
            "rw": "/usr/local/bin/rw", "ro": "/usr/local/bin/ro", "visudo": "/usr/sbin/visudo"}, SHA_A, SHA_S)
        lines = script.splitlines()
        trap = next(i for i, ln in enumerate(lines) if ln.startswith("trap "))
        rw = next(i for i, ln in enumerate(lines) if ln == '$SUDO "$RW"')
        install = next(i for i, ln in enumerate(lines) if "fleet-agent" in ln and "install -o" in ln)
        self.assertLess(trap, rw)                                       # ro guaranteed before rw is even tried
        self.assertLess(rw, install)
        self.assertEqual(script.count('"$RW"'), 1)                      # assignment-free: one rw call + RW= line
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "apply.sh"
            p.write_text(script)
            self.assertEqual(subprocess.run(["sh", "-n", str(p)]).returncode, 0)
        omv = bootstrap.apply_script("omv", ["diabolo"], {"visudo": "/usr/sbin/visudo"}, SHA_A, SHA_S)
        self.assertNotIn("RW", omv)
        self.assertNotIn("\ntrap ", omv)

    def test_apply_script_refuses_unsafe_master_names(self):
        with self.assertRaises(bootstrap.BootstrapError):
            bootstrap.apply_script("omv", ["x; evil"], {"visudo": "/usr/sbin/visudo"}, SHA_A, SHA_S)

    def test_authorized_lines_use_the_forced_command(self):
        lines, missing = bootstrap.authorized_lines(["diabolo"], {}, self.op)
        self.assertEqual(missing, [])
        self.assertTrue(lines[0].startswith('restrict,command="/usr/local/libexec/fleet-agent" ssh-ed25519 '))
        self.assertTrue(lines[0].endswith(" fleet-master-diabolo"))

    # ---- review fixes B1..B10

    def _script(self, kind="omv"):
        return bootstrap.apply_script(kind, ["diabolo", "penelope"], {
            "rw": "/usr/local/bin/rw", "ro": "/usr/local/bin/ro", "visudo": "/usr/sbin/visudo"}, SHA_A, SHA_S)

    def test_b1_remote_lookup_uses_the_fixed_path_only(self):
        self.boot(["omv1", "--user", "fleetsvc"])
        lookups = [c for c in self.calls() if "command -v" in c]
        self.assertTrue(lookups)
        for c in lookups:
            self.assertIn("PATH='%s'; command -v" % bootstrap.REMOTE_PATH, c)
            self.assertNotIn("$PATH", c)

    def test_b1_untrusted_resolved_path_refuses_everything(self):
        rc, out, err = self.boot(["omv1", "--user", "fleetsvc", "--apply"], confirm=lambda a: True,
                                 env={"FAKE_VERIFY_BAD": "/usr/sbin/omv-upgrade"})
        self.assertEqual(rc, 2)
        self.assertIn("untrusted path", err)
        self.assertNotIn("NOPASSWD", out)                         # nothing rendered
        self.assertNotIn("scp ", "\n".join(self.calls()))

    def test_b1_overrides_and_cloudflared_are_checked_too(self):
        rc, _, err = self.boot(["omv1", "--user", "u", "--path", "omv-upgrade=/home/u/bin/omv-upgrade",
                                "--path", "systemctl=/bin/systemctl", "--path", "visudo=/usr/sbin/visudo"],
                               env={"FAKE_VERIFY_BAD": "/home/u/bin/omv-upgrade"})
        self.assertEqual(rc, 2)
        rc, _, err = self.boot(["pk", "--user", "root"], env={"FAKE_VERIFY_BAD": bootstrap.CLOUDFLARED})
        self.assertEqual(rc, 2)
        self.assertIn(bootstrap.CLOUDFLARED, err)
        verify = [c for c in self.calls() if "fleet-verify" in c][-1]
        self.assertIn(bootstrap.CLOUDFLARED, verify)

    def test_b1_garbage_from_the_target_is_refused(self):
        for garbage in ("OK /etc/passwd", "evil", "OK /usr/sbin/omv-upgrade"):    # unknown / unparseable / duplicate
            rc, _, err = self.boot(["omv1", "--user", "u"], env={"FAKE_VERIFY_GARBAGE": garbage})
            self.assertEqual(rc, 2, garbage)

    def test_b1_verify_script_logic_on_a_real_shell(self):
        proc = subprocess.run(["sh", "-c", bootstrap.VERIFY_SCRIPT, "fleet-verify", str(self.tmp), "/bin/sh"],
                              capture_output=True, text=True)
        lines = proc.stdout.splitlines()
        if os.getuid() != 0:
            self.assertIn("BAD %s" % self.tmp, lines)               # user-owned: untrusted
        self.assertTrue(all(re.fullmatch(r"(OK|BAD) /.+", ln) for ln in lines), lines)
        wr = self.tmp / "ww"
        wr.mkdir()
        wr.chmod(0o777)
        proc = subprocess.run(["sh", "-c", bootstrap.VERIFY_SCRIPT, "fleet-verify", str(wr)],
                              capture_output=True, text=True)
        self.assertEqual(proc.stdout.strip(), "BAD %s" % wr)

    def test_b2_everything_is_staged_and_verified_before_any_rename(self):
        for kind in ("omv", "pikvm"):
            script = self._script(kind)
            lines = script.splitlines()
            first_mv = next(i for i, ln in enumerate(lines) if "mv -f" in ln)
            for needle in ("-cf /etc/sudoers.d/.fleet-agent.new", "sha256sum /usr/local/libexec/.fleet-agent.new",
                           SHA_A, SHA_S, "authorized.lines"):
                idx = next(i for i, ln in enumerate(lines) if needle in ln)
                self.assertLess(idx, first_mv, needle)
            self.assertNotIn('-cf "$D/', script)                   # never validates the user-owned copy
            self.assertIn("mv -f /usr/local/libexec/.fleet-agent.new /usr/local/libexec/fleet-agent", script)
            self.assertIn("mv -f /etc/sudoers.d/.fleet-agent.new /etc/sudoers.d/fleet-agent", script)
            self.assertIn("0440", script)
            self.assertEqual(lines[-1], "echo fleet-bootstrap: done")

    def test_b2_b5_authorized_keys_grep_failure_aborts(self):
        script = self._script()
        self.assertNotIn("|| true", script)
        self.assertIn('[ "$rc" -le 1 ]', script)
        with tempfile.TemporaryDirectory() as d:
            dd = Path(d)
            (dd / "ak.new").write_text("ssh-ed25519 K x fleet-master-diabolo\n")
            line = next(ln for ln in script.splitlines() if "fleet-master-diabolo" in ln)
            body = 'D=%s\nset -eu\n%s\necho survived\n' % (shlex_q(str(dd)), line)
            ok = subprocess.run(["sh", "-c", body], capture_output=True, text=True)
            self.assertEqual(ok.returncode, 0, ok.stderr)          # grep exit 1 (nothing left) is fine
            (dd / "ak.new").write_text("ssh-ed25519 K x fleet-master-diabolo\n")
            fake = dd / "bin"
            fake.mkdir()
            (fake / "grep").write_text("#!/bin/sh\nexit 2\n")
            (fake / "grep").chmod(0o755)
            bad = subprocess.run(["sh", "-c", body], capture_output=True, text=True,
                                 env={"PATH": "%s:/usr/bin:/bin" % fake})
            self.assertNotEqual(bad.returncode, 0)
            self.assertNotIn("survived", bad.stdout)

    def test_b2_sha_mismatch_aborts_on_a_real_shell(self):
        script = self._script()
        line = next(ln for ln in script.splitlines() if SHA_A in ln)
        proc = subprocess.run(["sh", "-c", 'set -eu\nGOT=deadbeef\n%s\necho survived' % line],
                              capture_output=True, text=True)
        self.assertNotEqual(proc.returncode, 0)
        self.assertNotIn("survived", proc.stdout)

    def test_b2_dry_run_shows_the_local_sha_of_the_agent_and_the_fragment(self):
        import hashlib
        rc, out, _ = self.boot(["omv1", "--user", "fleetsvc"])
        self.assertIn(hashlib.sha256(self.agent.read_bytes()).hexdigest(), out)
        frag = bootstrap.render_sudoers("omv", "fleetsvc", {"omv-upgrade": "/usr/sbin/omv-upgrade",
                                                            "systemctl": "/usr/bin/systemctl"})
        self.assertIn(hashlib.sha256(frag.encode()).hexdigest(), out)

    def test_b3_pikvm_traps_signals_and_reports_a_failed_ro(self):
        script = self._script("pikvm")
        self.assertIn("trap 'exit 1' HUP INT TERM", script)
        self.assertIn("ro failed", script)
        with tempfile.TemporaryDirectory() as d:
            dd = Path(d)
            for name, body in (("rw", "exit 0"), ("ro", 'echo ro-called >> "%s/log"; exit 7' % dd)):
                (dd / name).write_text("#!/bin/sh\n" + body + "\n")
                (dd / name).chmod(0o755)
            sh = script.replace("/usr/local/bin/rw", str(dd / "rw")).replace("/usr/local/bin/ro", str(dd / "ro"))
            lines = sh.splitlines()
            head = [ln for ln in lines[: lines.index('$SUDO "$RW"') + 1] if not ln.startswith("SUDO=")
                    and not ln.startswith("D=")]
            proc = subprocess.run(["sh", "-c", "set -eu\nSUDO=\n" + "\n".join(head) + "\nexit 0"],
                                  capture_output=True, text=True)
            self.assertNotEqual(proc.returncode, 0)                # failed ro => non-zero even on success
            self.assertIn("ro failed", proc.stderr)
            self.assertEqual((dd / "log").read_text().strip(), "ro-called")

    def test_b4_a_different_pinned_key_is_refused(self):
        self.known_hosts.write_text("omv1 ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIOtherKey\n")
        rc, _, err = self.boot(["omv1", "--user", "fleetsvc", "--apply"], confirm=lambda a: True)
        self.assertEqual(rc, 2)
        self.assertIn("host key mismatch", err)
        self.assertNotIn("scp ", "\n".join(self.calls()))
        self.assertNotIn("FakeHostKey", self.known_hosts.read_text())

    def test_b4_identical_pin_is_a_no_op(self):
        line = "omv1 ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIFakeHostKeyForTests\n"
        self.known_hosts.write_text(line)
        rc, out, err = self.boot(["omv1", "--user", "fleetsvc", "--apply"], confirm=lambda a: True)
        self.assertEqual(rc, 0, err)
        self.assertEqual(self.known_hosts.read_text(), line)

    def test_b6_prompt_and_dry_run_show_fingerprint_sha_and_script(self):
        import hashlib
        import io
        sha = hashlib.sha256(self.agent.read_bytes()).hexdigest()
        rc, out, _ = self.boot(["omv1", "--user", "fleetsvc"])
        self.assertIn("apply script", out)
        self.assertIn("sha256sum", out)
        self.assertIn(sha, out)
        err = io.StringIO()
        with mock.patch.object(sys, "stdin", types.SimpleNamespace(isatty=lambda: True, readline=lambda: "x\n")), \
                mock.patch.object(sys, "stderr", err):
            bootstrap.tty_confirm("omv1", "host key 256 SHA256:Fp; agent sha256 %s." % sha)
        self.assertIn("SHA256:Fp", err.getvalue())
        self.assertIn(sha, err.getvalue())

    def test_b6_default_confirmation_receives_the_details(self):
        seen = {}

        def fake_confirm(alias, detail=""):
            seen["d"] = detail
            return False
        with mock.patch.object(bootstrap, "tty_confirm", fake_confirm):
            self.boot(["omv1", "--user", "fleetsvc", "--apply"], confirm=bootstrap.tty_confirm)
        self.assertIn("SHA256:FakeFingerprint", seen["d"])
        self.assertRegex(seen["d"], r"[0-9a-f]{64}")

    def test_b9_remote_tmp_path_is_validated(self):
        for bad in ("/etc", "/tmp/../etc", "/tmp/.", "/tmp/a/b", "/home/x", "/tmp/a b", "/", "/tmp/.."):
            self.log.write_text("")
            rc, _, err = self.boot(["omv1", "--user", "fleetsvc", "--apply"], confirm=lambda a: True,
                                   env={"FAKE_MKTEMP": bad})
            self.assertEqual(rc, 2, bad)
            self.assertNotIn("rm -", "\n".join(self.calls()), bad)

    def test_b10_apply_script_uses_sudo_n(self):
        script = self._script()
        self.assertIn('SUDO="sudo -n"', script)
        self.assertNotIn("SUDO=sudo;", script)

    def test_apply_scripts_are_valid_shell(self):
        for kind in ("omv", "pikvm"):
            with tempfile.TemporaryDirectory() as d:
                p = Path(d) / "apply.sh"
                p.write_text(self._script(kind))
                for shell in ("bash", "sh"):
                    self.assertEqual(subprocess.run([shell, "-n", str(p)]).returncode, 0, (kind, shell))

    def test_fleet_wrapper_exposes_the_bootstrap_verb(self):
        wrapper = ROOT / "dot_local/bin/executable_fleet"
        env = dict(os.environ, FLEET_DIR=str(ROOT / "dot_local/share/fleet"))
        proc = subprocess.run(["bash", str(wrapper), "bootstrap", "--help"], env=env, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("--apply", proc.stdout)
        proc = subprocess.run(["bash", str(wrapper), "help"], env=env, capture_output=True, text=True)
        self.assertIn("bootstrap", proc.stdout)


if __name__ == "__main__":
    unittest.main()
