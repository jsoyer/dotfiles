#!/usr/bin/env python3
"""agent-host-setup: shared mise template, merge of missing tools, bashrc block."""

import os
import shutil
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "dot_local/bin/executable_agent-host-setup"
TEMPLATE = ROOT / "dot_local/share/agent-host/mise-agents.toml"
TOOLS = ("bash sh sed grep awk cat cut head tail tr dirname mkdir rm mv cp chmod "
         "stat cmp mktemp date id env printf ls sort python3 ldconfig jq curl git").split()


class Sandbox:
    def __init__(self, test):
        self.tmp = Path(tempfile.mkdtemp(prefix="agenthost-"))
        test.addCleanup(shutil.rmtree, str(self.tmp), True)
        self.home = self.tmp / "home"
        self.bin = self.tmp / "bin"
        self.home.mkdir()
        self.bin.mkdir()
        for t in TOOLS:
            found = shutil.which(t) or (f"/sbin/{t}" if os.path.exists(f"/sbin/{t}") else None)
            if found:
                os.symlink(found, str(self.bin / t))
        self.log = self.tmp / "calls.log"
        self.log.write_text("")
        # mise stub: logs its calls, installs nothing.
        mise = self.bin / "mise"
        mise.write_text('#!/bin/sh\necho "mise $*" >> "%s"\n' % self.log)
        mise.chmod(0o755)
        self.config = self.home / ".config/mise/config.toml"
        self.bashrc = self.home / ".bashrc"
        self.bashrc.write_text("# user rc\n")
        self.env = {
            "HOME": str(self.home), "USER": "agent", "LANG": "C",
            "PATH": str(self.bin),
            "AGENT_HOST_TEMPLATE": str(TEMPLATE),
            "MISE_GLOBAL_CONFIG_FILE": str(self.config),
            "AGENT_HOST_BASHRC": str(self.bashrc),
            "AGENT_HOST_NO_PREREQS": "1",
        }

    def run(self, *args):
        return subprocess.run(["bash", str(SCRIPT), *args], env=self.env,
                              capture_output=True, text=True, timeout=60)


@unittest.skipIf(os.geteuid() == 0, "the script refuses root")
class AgentHostSetup(unittest.TestCase):
    def test_parses(self):
        subprocess.run(["bash", "-n", str(SCRIPT)], check=True)

    def test_template_keeps_the_known_pitfalls(self):
        t = TEMPLATE.read_text()
        self.assertIn('"npm:@earendil-works/pi-coding-agent"', t)
        self.assertNotIn("@mariozechner", t.replace("the @mariozechner scope", ""))
        self.assertIn('"aqua:rtk-ai/rtk" = "1.1.0"', t)
        # opencode v1 must stay `opencode`: opencode-ai is listed before @opencode/cli.
        self.assertLess(t.index('"npm:opencode-ai"'), t.index('"npm:@opencode/cli"'))
        for pkg in ("claude-code", "opencode-ai", "@opencode/cli"):
            line = next(l for l in t.splitlines() if pkg in l and "=" in l and not l.startswith("#"))
            self.assertIn("--ignore-scripts=false", line)
        self.assertIn('npm.package_manager = "npm"', t)

    def test_fresh_host_gets_template_and_bashrc_block(self):
        sb = Sandbox(self)
        r = sb.run("--no-rtk")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(sb.config.read_text(), TEMPLATE.read_text())
        rc = sb.bashrc.read_text()
        self.assertIn("# >>> agent-host (managed by agent-host-setup) >>>", rc)
        self.assertIn('$HOME/.local/share/mise/shims:$HOME/.local/bin:$HOME/.grok/bin', rc)
        self.assertIn("MISE_DATA_DIR=", rc)
        self.assertIn("mise install -y", sb.log.read_text())
        # Second run: nothing duplicated.
        r = sb.run("--no-rtk")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(sb.bashrc.read_text().count(">>> agent-host"), 1)
        self.assertEqual(sb.config.read_text(), TEMPLATE.read_text())

    def test_existing_config_only_gains_missing_tools(self):
        sb = Sandbox(self)
        sb.config.parent.mkdir(parents=True)
        sb.config.write_text('[tools]\nnode = "22"\n"npm:@openai/codex" = "0.1.0"\n\n'
                             '[settings]\nall_compile = false\n')
        r = sb.run("--no-rtk", "--paseo")
        self.assertEqual(r.returncode, 0, r.stderr)
        c = sb.config.read_text()
        self.assertIn('node = "22"', c)                       # kept
        self.assertIn('"npm:@openai/codex" = "0.1.0"', c)     # kept, not bumped
        self.assertEqual(c.count('"npm:@openai/codex"'), 1)
        self.assertIn('"npm:@anthropic-ai/claude-code"', c)   # added
        self.assertIn('"npm:@getpaseo/cli"', c)               # --paseo
        # Added inside [tools], before [settings].
        self.assertLess(c.index('"npm:@anthropic-ai/claude-code"'), c.index("[settings]"))
        self.assertTrue(Path(str(sb.config) + ".bak-agent-host").exists())

    def test_check_reports_without_changing(self):
        sb = Sandbox(self)
        r = sb.run("--check")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("missing tools", r.stdout)
        self.assertIn("bashrc", r.stdout)
        self.assertFalse(sb.config.exists())
        self.assertEqual(sb.bashrc.read_text(), "# user rc\n")
        # Nothing missing is not an error (pipefail on an empty grep).
        sb.run("--no-rtk")
        r = sb.run("--check")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("missing tools  none", r.stdout)

    def test_hand_written_bashrc_pins_are_left_alone(self):
        sb = Sandbox(self)
        sb.bashrc.write_text('export PATH="$HOME/.local/share/mise/shims:$PATH"\n'
                             'export MISE_DATA_DIR="$HOME/.local/share/mise"\n')
        r = sb.run("--no-rtk")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn(">>> agent-host", sb.bashrc.read_text())

    def test_vendor_installers_only_with_flag(self):
        sb = Sandbox(self)
        r = sb.run("--no-rtk")
        self.assertIn("grok missing", r.stderr)
        self.assertIn("https://x.ai/cli/install.sh", r.stderr)
        r = sb.run("--no-rtk", "--vendor", "--dry-run")
        self.assertIn("curl -fsSL https://x.ai/cli/install.sh | bash", r.stdout)

    def test_rejects_unknown_option(self):
        r = Sandbox(self).run("--bogus")
        self.assertNotEqual(r.returncode, 0)


if __name__ == "__main__":
    unittest.main()
