#!/usr/bin/env python3
"""agent-alert: backend-agnostic push alerts (ntfy / Telegram) for the agent stacks.

A fake curl records argv, the --config stdin and the files the config refers to,
so we can assert payloads AND that no secret ever reaches argv (visible in `ps`).
Python 3.9-compatible, stdlib only.
"""

import stat
import unittest

from test_t3_paseo import LOGGER, BIN, ROOT, SandboxCase

FAKE_CURL = (
    LOGGER
    + r"""
echo "$*" > "$STUB_DIR/curl.argv"
cat > "$STUB_DIR/curl.stdin"
: > "$STUB_DIR/curl.body"
for f in $(sed -n 's/^data[-a-z]* = ".*@\(\/[^"]*\)"$/\1/p' "$STUB_DIR/curl.stdin"); do
  cat "$f" >> "$STUB_DIR/curl.body"
done
exit "${CURL_RC:-0}"
"""
)

TG_TOKEN = "123456:SECRET-tg_token"
NTFY_TOKEN = "tk_secretntfy"


class AgentAlert(SandboxCase):
    def box(self, conf=None, mode=0o600, env=None):
        sb = self.sandbox(extra_env=env)
        (sb.stubs / "curl").write_text(FAKE_CURL)
        (sb.stubs / "curl").chmod(0o755)
        if conf is not None:
            path = sb.tmp / "alert.conf"
            path.write_text(conf)
            path.chmod(mode)
            sb.env["AGENT_ALERT_CONF"] = str(path)
        return sb

    @staticmethod
    def argv(sb):
        return (sb.stubs / "curl.argv").read_text()

    @staticmethod
    def sent(sb):
        return (sb.stubs / "curl.stdin").read_text()

    @staticmethod
    def body(sb):
        return (sb.stubs / "curl.body").read_text()

    def assert_no_secret(self, sb, r, *secrets):
        seen = (
            (sb.stubs / "curl.argv").read_text()
            if (sb.stubs / "curl.argv").exists()
            else ""
        )
        for s in secrets:
            self.assertNotIn(s, seen, "secret leaked into curl argv")
            self.assertNotIn(s, r.stdout + r.stderr, "secret printed")

    def test_ntfy_payload_and_priority_mapping(self):
        sb = self.box(
            'ALERT_NTFY_URL="https://ntfy.example/topic"\nALERT_NTFY_TOKEN="%s"\n'
            % NTFY_TOKEN
        )
        r = sb.run(
            "agent-alert",
            "--title",
            "Down",
            "--priority",
            "high",
            "--tags",
            "a,b",
            "hello",
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        out = self.sent(sb)
        self.assertIn('url = "https://ntfy.example/topic"', out)
        self.assertIn('header = "Authorization: Bearer %s"' % NTFY_TOKEN, out)
        self.assertIn('header = "Title: Down"', out)
        self.assertIn('header = "Priority: urgent"', out)
        self.assertIn('header = "Tags: a,b"', out)
        self.assertEqual(self.body(sb), "hello")
        self.assert_no_secret(sb, r, NTFY_TOKEN)

    def test_legacy_orca_keys_are_honored(self):
        sb = self.box(
            'ORCA_ALERT_URL="https://ntfy.example/old"\nORCA_ALERT_TOKEN="%s"\n'
            % NTFY_TOKEN
        )
        r = sb.run("agent-alert", "--title", "T", "legacy")
        self.assertEqual(r.returncode, 0, r.stderr)
        out = self.sent(sb)
        self.assertIn('url = "https://ntfy.example/old"', out)
        self.assertIn("Bearer %s" % NTFY_TOKEN, out)
        self.assert_no_secret(sb, r, NTFY_TOKEN)

    def test_telegram_payload(self):
        sb = self.box(
            'ALERT_BACKEND="telegram"\nALERT_TELEGRAM_BOT_TOKEN="%s"\n'
            'ALERT_TELEGRAM_CHAT_ID="-1001"\n' % TG_TOKEN
        )
        r = sb.run("agent-alert", "--title", "Orca down", "line one")
        self.assertEqual(r.returncode, 0, r.stderr)
        out = self.sent(sb)
        self.assertIn(
            'url = "https://api.telegram.org/bot%s/sendMessage"' % TG_TOKEN, out
        )
        self.assertIn('data-urlencode = "chat_id=-1001"', out)
        body = self.body(sb)
        self.assertRegex(body, r"^\[.+\] Orca down\nline one$")
        self.assert_no_secret(sb, r, TG_TOKEN)

    def test_telegram_text_truncated(self):
        sb = self.box(
            'ALERT_BACKEND="telegram"\nALERT_TELEGRAM_BOT_TOKEN="%s"\n'
            'ALERT_TELEGRAM_CHAT_ID="1"\n' % TG_TOKEN
        )
        r = sb.run("agent-alert", "x" * 6000)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertLessEqual(len(self.body(sb)), 3900)

    def test_message_from_stdin(self):
        sb = self.box('ALERT_NTFY_URL="https://ntfy.example/t"\n')
        r = sb.run("agent-alert", "--title", "S", stdin="from stdin\n")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("from stdin", self.body(sb))

    def test_insecure_config_with_token_is_skipped(self):
        sb = self.box(
            'ALERT_NTFY_URL="https://ntfy.example/t"\nALERT_NTFY_TOKEN="%s"\n'
            % NTFY_TOKEN,
            mode=0o644,
        )
        r = sb.run("agent-alert", "msg")
        self.assertEqual(r.returncode, 0)
        self.assertIn("skipping", r.stderr)
        self.assertNotIn("curl", sb.calls())  # fell back to backend none
        self.assert_no_secret(sb, r, NTFY_TOKEN)

    def test_group_readable_config_without_token_is_fine(self):
        sb = self.box('ALERT_NTFY_URL="https://ntfy.example/t"\n', mode=0o644)
        self.assertEqual(sb.run("agent-alert", "msg").returncode, 0)
        self.assertIn("curl", sb.calls())

    def test_backend_none_is_journal_only(self):
        sb = self.box('ALERT_BACKEND="none"\nALERT_NTFY_URL="https://ntfy.example/t"\n')
        r = sb.run("agent-alert", "--title", "T", "quiet")
        self.assertEqual(r.returncode, 0)
        self.assertIn("quiet", r.stderr)
        self.assertNotIn("curl", sb.calls())

    def test_send_failure_is_soft_unless_strict(self):
        conf = 'ALERT_NTFY_URL="https://ntfy.example/t"\n'
        sb = self.box(conf, env={"CURL_RC": "22"})
        r = sb.run("agent-alert", "msg")
        self.assertEqual(r.returncode, 0)
        self.assertIn("failed to send", r.stderr)
        self.assertEqual(sb.run("agent-alert", "--strict", "msg").returncode, 1)
        self.assertEqual(sb.run("agent-alert", "--test").returncode, 1)

    def test_test_mode_reports_backend_without_secrets(self):
        sb = self.box(
            'ALERT_BACKEND="telegram"\nALERT_TELEGRAM_BOT_TOKEN="%s"\n'
            'ALERT_TELEGRAM_CHAT_ID="1"\n' % TG_TOKEN
        )
        r = sb.run("agent-alert", "--test")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("backend=telegram", r.stderr)
        self.assert_no_secret(sb, r, TG_TOKEN)

    def test_configure_writes_0600_telegram_config(self):
        sb = self.box()
        r = sb.run("agent-alert", "--configure", stdin="telegram\n%s\n42\n" % TG_TOKEN)
        self.assertEqual(r.returncode, 0, r.stderr)
        conf = sb.home / ".config/agent-alert.conf"
        self.assertEqual(stat.S_IMODE(conf.stat().st_mode), 0o600)
        text = conf.read_text()
        self.assertIn('ALERT_BACKEND="telegram"', text)
        self.assertIn('ALERT_TELEGRAM_CHAT_ID="42"', text)
        self.assert_no_secret(sb, r, TG_TOKEN)
        # The written file is picked up without AGENT_ALERT_CONF.
        sb.env.pop("AGENT_ALERT_CONF", None)
        r = sb.run("agent-alert", "--test")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("api.telegram.org", self.sent(sb))

    def test_configure_rejects_malformed_input(self):
        sb = self.box()
        r = sb.run("agent-alert", "--configure", stdin="telegram\nnot a token\n42\n")
        self.assertNotEqual(r.returncode, 0)
        self.assertFalse(
            (sb.home / ".config/agent-alert.conf").exists()
            and "not a token" in (sb.home / ".config/agent-alert.conf").read_text()
        )


class Routing(unittest.TestCase):
    def test_callers_use_agent_alert_not_their_own_curl(self):
        for name in ("orca-health", "t3-health", "agents-update"):
            text = (BIN / ("executable_" + name)).read_text()
            self.assertIn('"$ALERT_BIN"', text, name)
            self.assertNotIn("curl", text.replace("curl.sh", ""), name)
            self.assertNotIn("ORCA_ALERT_URL", text, name)

    def test_paseo_health_routes_through_agent_alert(self):
        # The health script is generated inline by paseo-setup (#71 design).
        text = (BIN / "executable_paseo-setup").read_text()
        self.assertIn("ALERT_BIN=\"/usr/local/bin/agent-alert\"", text)
        self.assertIn("--priority high --tags rotating_light", text)
        self.assertIn("install -m 0755 \"$SRC_ALERT\" \"$ALERT_BIN\"", text)
        self.assertNotIn("ORCA_ALERT_URL", text)
        self.assertNotIn('-H "Title:', text)
        # 2-misses-then-restart behaviour from #71 is preserved.
        self.assertIn("if (( fails >= 2 ))", text)

    def test_agent_alert_is_linux_only(self):
        ignore = (ROOT / ".chezmoiignore.tmpl").read_text()
        cleanup = (
            ROOT
            / ".chezmoiscripts/02-install/run_once_12-disable-macos-agent-stacks.sh.tmpl"
        ).read_text()
        self.assertIn(".local/bin/agent-alert\n", ignore)
        self.assertIn('.local/bin/agent-alert"', cleanup)

    def test_setup_scripts_point_to_configure(self):
        for name in ("t3-setup", "paseo-setup", "orca-setup"):
            self.assertIn(
                "agent-alert --configure",
                (BIN / ("executable_" + name)).read_text(),
                name,
            )


if __name__ == "__main__":
    unittest.main()
