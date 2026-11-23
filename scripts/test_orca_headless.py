#!/usr/bin/env python3
"""Headless Orca on Raspberry Pi must not depend on FUSE being present.

Origin: looping's orca-serve crash-looped (70+ restarts) with:
  dlopen(): error loading libfuse.so.2
  AppImages require FUSE to run.
Raspberry Pi OS / Debian ship fuse3; the AppImage type-2 runtime wants fuse2.
"""

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SETUP = (ROOT / "dot_local/bin/executable_orca-setup").read_text()
GUI = (ROOT / "dot_local/bin/executable_orca-gui").read_text()
APT_RPI = (ROOT / "dot_private/Aptfile_rpi").read_text()


class FuseFallback(unittest.TestCase):
    def test_unit_extracts_without_fuse(self):
        self.assertIn("APPIMAGE_EXTRACT_AND_RUN=1", SETUP)
        self.assertIn("ensure_libfuse2", SETUP)
        self.assertIn("libfuse2t64", SETUP)

    def test_unit_wraps_exec_in_xvfb(self):
        self.assertIn("xvfb-run --auto-servernum", SETUP)
        self.assertIn("xvfb", APT_RPI)

    def test_setup_writes_fallback_port_before_start(self):
        self.assertIn("mobile-ws-fallback-port.json", SETUP)
        self.assertIn('printf \'{"port":%s}\\n\' "$PORT"', SETUP)
        self.assertIn("Waiting for port", SETUP)
        update = (ROOT / "dot_local/bin/executable_update-orca").read_text()
        # update-orca only rewrites the port file when the profile dir already
        # exists (14a753ea dropped the root-owned `mkdir -p`); it must not
        # create the profile itself.
        body = update.split("enforce_port_file() {", 1)[1].split("\n}\n", 1)[0]
        self.assertIn('[[ -d "$dir" ]]', body)
        self.assertNotIn("mkdir", body)
        self.assertIn('> "$FALLBACK_PORT_FILE"', body)

    def test_unquoted_unit_heredoc_does_not_expand_display(self):
        # set -u: `$DISPLAY` in <<EOF aborted orca-setup on diabolo.
        unit = SETUP.split('write_file "/etc/systemd/system/${SERVICE}" <<EOF', 1)[1]
        unit = unit.split("EOF", 1)[0]
        self.assertNotIn("$DISPLAY", unit)

    def test_crash_loop_is_capped(self):
        self.assertIn("StartLimitBurst=8", SETUP)
        self.assertIn("Restart=on-failure", SETUP)

    def test_gui_also_extracts_without_fuse(self):
        self.assertIn("APPIMAGE_EXTRACT_AND_RUN=1", GUI)

    def test_rpi_aptfile_ships_libfuse2(self):
        self.assertRegex(APT_RPI, r"(?m)^libfuse2$")

    def test_setup_installs_electron_gtk_runtime(self):
        self.assertIn("ensure_electron_runtime", SETUP)
        self.assertIn("libgtk-3-0", SETUP)
        self.assertIn("libcups2", SETUP)
        self.assertIn("libcairo2", SETUP)
        self.assertIn("ELECTRON_APT_PKGS", SETUP)

    def test_rpi_aptfile_ships_electron_gtk_runtime(self):
        for pkg in (
            "libfuse2",
            "libgtk-3-0",
            "libatk1.0-0",
            "libatk-bridge2.0-0",
            "libatspi2.0-0",
            "libnss3",
            "libnspr4",
            "libgbm1",
            "libasound2",
            "libcups2",
            "libdrm2",
            "libcairo2",
            "libpango-1.0-0",
            "libpangocairo-1.0-0",
            "libgdk-pixbuf-2.0-0",
            "libglib2.0-0",
            "libxss1",
            "libxtst6",
            "libnotify4",
            "libx11-6",
            "libxcb1",
            "libxext6",
            "libxfixes3",
            "libvulkan1",
            "fonts-liberation",
            "xvfb",
            "zlib1g",
            "zlib1g-dev",
        ):
            self.assertRegex(APT_RPI, rf"(?m)^{pkg}$")
            self.assertIn(pkg, SETUP)


PAIR = (ROOT / "dot_local/bin/executable_orca-pair").read_text()
HEALTH = (ROOT / "dot_local/bin/executable_orca-health").read_text()
AGENTS = (ROOT / "dot_local/bin/executable_agents-update").read_text()


class OrcaServerHardening(unittest.TestCase):
    """orcadev (CT 205): a long-lived Orca server reached from iOS + desktops."""

    def unit(self):
        unit = SETUP.split('write_file "/etc/systemd/system/${SERVICE}" <<EOF', 1)[1]
        return unit.split("\nEOF", 1)[0]

    def test_service_never_logs_a_pairing_link(self):
        # Every start printed a fresh pairing link (a credential) to the journal.
        self.assertRegex(self.unit(), r"(?m)^ExecStart=.* serve .*--no-pairing")

    def test_pairing_goes_through_the_running_server(self):
        self.assertIn("orca \"${args[@]}\"", PAIR)
        self.assertIn("args=(pair --address", PAIR)
        self.assertIn("--mobile", PAIR)
        self.assertIn("--rotate", PAIR)
        # It must never restart the service to pair.
        self.assertNotRegex(PAIR, r"systemctl (stop|restart|start) ")

    def test_agent_path_dropin_sorts_after_the_environment_reset(self):
        # zz-tmp-fix.conf has an empty `Environment=` that wipes earlier values.
        self.assertIn("zz-user-path.conf", SETUP)
        self.assertGreater("zz-user-path.conf", "zz-tmp-fix.conf")
        # Orca isolates XDG_* for agent logins: mise must not depend on them.
        for var in ("MISE_DATA_DIR", "MISE_CONFIG_DIR", "MISE_STATE_DIR", "MISE_CACHE_DIR"):
            self.assertIn(f'"{var}=${{SVC_HOME}}/', SETUP)
        self.assertIn(".local/share/mise/shims", SETUP)

    def test_sudo_reexec_keeps_the_options(self):
        # The parsing loop shifts "$@" empty before the elevation.
        self.assertIn('ORIG_ARGS=("$@")', SETUP)
        self.assertIn('exec sudo -- "$self" "${ORIG_ARGS[@]}"', SETUP)

    def test_unit_heredoc_has_no_command_substitution(self):
        # An unquoted <<EOF runs `backticks` and $(...) — a comment is not safe.
        self.assertNotIn("`", self.unit())

    def test_starts_after_tailscale(self):
        self.assertIn("After=tailscaled.service", SETUP)

    def test_profile_dir_is_created_as_the_user(self):
        body = SETUP.split("enforce_port_file() {", 1)[1].split("\n}\n", 1)[0]
        self.assertIn('runuser -u "$SVC_USER" -- mkdir -p "$dir"', body)
        self.assertNotRegex(body, r"(?m)^\s*run mkdir -p")

    def test_fixed_update_time_clears_the_default_calendar(self):
        self.assertIn("--update-at", SETUP)
        self.assertRegex(SETUP, r"OnCalendar=\nOnCalendar=\*-\*-\* \$\{UPDATE_AT\}:00")

    def test_tailnet_only_firewall_is_opt_in_and_scoped(self):
        self.assertIn("TAILNET_ONLY=0", SETUP)
        self.assertIn('iifname != { "lo", "tailscale0" } drop', SETUP)
        # Own table only: never flush someone else's ruleset.
        self.assertNotIn("flush ruleset", SETUP)

    def test_alerts_support_a_protected_ntfy(self):
        self.assertIn("Authorization: Bearer ${ORCA_ALERT_TOKEN}", HEALTH)
        self.assertIn("Authorization: Bearer ${ORCA_ALERT_TOKEN}", AGENTS)


class AgentsUpdate(unittest.TestCase):
    def test_mise_keeps_previous_versions_for_rollback(self):
        self.assertIn("mise upgrade --bump --pin --no-prune", AGENTS)
        self.assertIn('cp -f "$backup" "$MISE_CONFIG"', AGENTS)

    def test_never_probes_a_bare_agent_binary(self):
        # Grok and cursor-agent have both shipped an `agent` binary.
        self.assertNotRegex(AGENTS, r'"agent:|command -v agent\b')

    def test_refuses_root(self):
        self.assertIn("Run as the agents' user, not root", AGENTS)


if __name__ == "__main__":
    unittest.main()
