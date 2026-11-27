#!/usr/bin/env python3
"""obsidian-update: channel detection, safe npm update, skills, agents-update hook."""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "dot_local/bin/executable_obsidian-update"
TEXT = SCRIPT.read_text()
UPDATE = (ROOT / "dot_local/bin/executable_agents-update").read_text()
SETUP = (ROOT / "dot_local/bin/executable_paseo-setup").read_text()
TEMPLATE = (ROOT / "dot_local/share/agent-host/mise-agents.toml").read_text()
IGNORE = (ROOT / ".chezmoiignore.tmpl").read_text()
HOST_SETUP = (ROOT / "dot_local/bin/executable_agent-host-setup").read_text()

STUB = """#!/bin/sh
echo "$(basename "$0") $*" >> "$CALLS"
case "$(basename "$0") $1" in
  "ob --version") echo 0.0.13 ;;
  "npm view") echo 0.0.14 ;;
esac
exit 0
"""


class ObsidianUpdate(unittest.TestCase):
    def run_script(self, layout, env_extra=None):
        """layout: dir (relative to a fake HOME) holding the `ob` stub."""
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            tools = home / "tools"
            tools.mkdir()
            for name in ("npm", "npx", "mise", "timeout"):
                (tools / name).write_text(STUB if name != "timeout" else '#!/bin/sh\nshift; exec "$@"\n')
                (tools / name).chmod(0o755)
            ob_dir = home / layout
            ob_dir.mkdir(parents=True, exist_ok=True)
            (ob_dir / "ob").write_text(STUB)
            (ob_dir / "ob").chmod(0o755)
            calls = home / "calls"
            path = f"{tools}:/usr/bin:/bin"
            if not layout.startswith(".npm-global"):
                path = f"{ob_dir}:{path}"
            env = {"HOME": str(home), "PATH": path, "CALLS": str(calls), **(env_extra or {})}
            r = subprocess.run(["sh", str(SCRIPT)], env=env, capture_output=True, text=True, check=False)
            return r, (calls.read_text() if calls.exists() else "")

    def test_parses(self):
        subprocess.run(["sh", "-n", str(SCRIPT)], check=True)

    def test_npm_channel_installs_latest_never_update_g(self):
        r, calls = self.run_script(".npm-global/bin")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("npm install -g obsidian-headless@0.0.14", calls)
        self.assertNotIn("npm update", calls)
        self.assertIn("npx --yes skills update -g -y", calls)

    def test_mise_channel_left_to_agents_update(self):
        r, calls = self.run_script(".local/share/mise/shims")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertNotIn("npm install", calls)
        self.assertNotIn("mise upgrade", calls)
        self.assertIn("skills update -g -y", calls)

    def test_mise_bump_when_asked(self):
        _, calls = self.run_script(".local/share/mise/shims", {"OB_MISE_BUMP": "1"})
        self.assertIn("mise upgrade --bump npm:obsidian-headless", calls)

    def test_other_location_is_skills_only(self):
        r, calls = self.run_script("linuxbrew/bin")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertNotIn("npm install", calls)
        self.assertIn("skills update -g -y", calls)


class Wiring(unittest.TestCase):
    def test_agents_update_runs_it_after_each_update(self):
        self.assertIn('post="ExecStopPost=-/usr/local/bin/obsidian-update"', UPDATE)
        self.assertIn("${post}", UPDATE)
        self.assertIn('install -m 0755 "${src_dir}/obsidian-update" /usr/local/bin/obsidian-update', UPDATE)

    def test_agent_path_covers_npm_global_and_linuxbrew(self):
        for text in (UPDATE, SETUP):
            self.assertIn('/.npm-global/bin" /home/linuxbrew/.linuxbrew/bin; do', text)

    def test_paseo_exec_goes_through_env_for_selinux(self):
        self.assertIn("ExecStart=/usr/bin/env ${SHIM} daemon run --home", SETUP)

    def test_devin_acp_provider(self):
        self.assertIn('devin={"extends":"acp","label":"Devin","command":["devin","acp"]}', SETUP)

    def test_agent_host_setup_adds_the_skills(self):
        self.assertIn("npx --yes skills add obsidianmd/obsidian-skills -g -y", HOST_SETUP)
        self.assertIn("/.agents/skills/obsidian-cli", HOST_SETUP)

    def test_template_and_linux_only(self):
        self.assertIn('"npm:obsidian-headless" = "0.0.14"', TEMPLATE)
        self.assertIn(".local/bin/obsidian-update", IGNORE)


if __name__ == "__main__":
    unittest.main()
