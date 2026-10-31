#!/usr/bin/env python3
"""Contract of the Windows agent (fleet-agent.ps1) with the master, without Windows.

pwsh is not available in CI here, so the PowerShell agent cannot be run. Two
things are checked instead:

1. STATIC properties of the .ps1 sources (verb whitelist, status vocabulary, JSON
   key set read out of the script, PowerShell 5.1 compatibility, forbidden tools,
   pull mode isolation, ACL / firewall / forced command in the bootstrap);
2. JSON FIXTURES representative of what the agent prints (one per verb / status,
   built with the key order read from the .ps1 source) which must pass the
   master's validator ``lib/schema.py`` unchanged.

Live behaviour (real Windows Update, winget, Scoop, WSL, Event Log) needs a PC and
is NOT covered here.
"""

import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / "dot_local/share/fleet/lib"
AGENT_DIR = ROOT / "dot_local/share/fleet/agent"
PS_AGENT = AGENT_DIR / "fleet-agent.ps1"
PS_BOOT = AGENT_DIR / "fleet-bootstrap.ps1"
SH_AGENT = AGENT_DIR / "fleet-agent.sh"
sys.path.insert(0, str(LIB))
import schema  # noqa: E402

AGENT = PS_AGENT.read_text()
BOOT = PS_BOOT.read_text()


def strip_comments_and_strings(src):
    """Drop <# #> blocks, # comments and quoted strings (for syntax-level greps)."""
    src = re.sub(r"<#.*?#>", "", src, flags=re.S)
    src = re.sub(r"'(?:[^']|'')*'", "''", src)
    src = re.sub(r'"(?:[^"`]|`.)*"', '""', src)
    return "\n".join(re.sub(r"#.*$", "", ln) for ln in src.splitlines())


def result_keys():
    """Keys of the ordered hashtable built by Initialize-AgentResult, in order."""
    body = AGENT.split("function Initialize-AgentResult", 1)[1]
    body = body.split("$script:R = [ordered]@{", 1)[1].split("\n    }\n", 1)[0]
    return re.findall(r"^\s{8}([a-z_]+)\s+= ", body, re.M)


def function_body(name):
    start = AGENT.index("function %s " % name)
    nxt = AGENT.find("\nfunction ", start + 10)
    return AGENT[start:nxt if nxt != -1 else len(AGENT)]


def fixture(verb, status, **over):
    """JSON line as the agent prints it: key order taken from the .ps1 source."""
    base = {
        "schema": 1, "host": "desktop-test", "verb": verb, "status": status, "reason": None,
        "packages": None, "changes": [],
        "health_before": {"failed_units": [], "unhealthy_containers": [], "disk_free_pct": {"C:": 42}, "critical_services_down": []},
        "health_after": {"failed_units": [], "unhealthy_containers": [], "disk_free_pct": {"C:": 42}, "critical_services_down": []},
        "preflight": {"ok": True, "blocked_by": None}, "config_conflicts": [], "job": None,
        "reboot_required": False, "reboot_since": None, "os": "Microsoft Windows 11 Pro 10.0.26100",
        "kernel": "10.0.26100.0", "major_available": None, "started": "2026-10-31T10:00:00Z",
        "ended": "2026-10-31T10:00:05Z", "log_tail": "",
    }
    base.update(over)
    return json.dumps({k: base[k] for k in result_keys()}, separators=(",", ":"))


class StaticAgent(unittest.TestCase):
    def test_json_keys_are_exactly_schema_v1(self):
        v1 = {
            "schema", "host", "verb", "status", "reason", "packages", "changes",
            "health_before", "health_after", "preflight", "config_conflicts", "job",
            "reboot_required", "reboot_since", "os", "kernel", "major_available",
            "started", "ended", "log_tail",
        }
        keys = result_keys()
        self.assertEqual(set(keys), v1)
        self.assertEqual(len(keys), len(v1), "duplicate key")

    def test_verbs_exact_and_identical_to_unix_agent(self):
        m = re.search(r"\$script:Verbs = @\(([^)]*)\)", AGENT)
        verbs = re.findall(r"'([a-z-]+)'", m.group(1))
        self.assertEqual(verbs, list(schema.VERBS))
        m2 = re.search(r"^\s*([a-z|-]+)\) ;;$", SH_AGENT.read_text(), re.M)
        self.assertEqual(m2.group(1).split("|"), list(schema.VERBS))
        # the switch dispatch has one label per verb and nothing else
        sw = AGENT.split("switch -CaseSensitive ($verb) {", 1)[1].split("\n    }", 1)[0]
        labels = re.findall(r"^\s+'([^']+)' \{", sw, re.M)
        self.assertEqual(labels, list(schema.VERBS))

    def test_ping_and_pull_are_not_verbs(self):
        self.assertIsNone(re.search(r"^\s*'?ping'?\)", AGENT, re.M | re.I))
        self.assertNotIn("'ping'", AGENT)
        self.assertNotIn("'pull' {", AGENT)
        self.assertNotIn("'run-job'", AGENT)

    def test_refusal_is_exit_1_logged_in_event_log(self):
        body = function_body("Exit-AgentRefused")
        self.assertIn("REFUSED", body)
        self.assertIn("exit 1", body)
        self.assertIn("Write-EventLog", function_body("Write-AgentLog"))
        self.assertIn("$script:EventSource = 'fleet-agent'", AGENT)
        # every refusal path goes through Exit-AgentRefused before anything runs
        main = function_body("Invoke-AgentMain")
        self.assertIn("unexpected arguments", main)
        self.assertIn("interactive shell attempt", main)
        self.assertIn("-cnotcontains", main)
        self.assertLess(main.index("-cnotcontains"), main.index("switch -CaseSensitive"))

    def test_statuses_come_from_schema_vocabulary(self):
        used = set(re.findall(r"\['status'\]\s*=\s*'([a-z-]+)'", AGENT))
        used |= set(re.findall(r"status\s+= '([a-z-]+)'", AGENT))
        self.assertTrue(used)
        self.assertLessEqual(used, set(schema.AGENT_STATUSES), used - set(schema.AGENT_STATUSES))
        # master-only statuses are never produced by an agent
        self.assertFalse(used & set(schema.MASTER_STATUSES))

    def test_complete_agent_verb_names(self):
        for v in re.findall(r"Complete-AgentVerb -Verb '([a-z-]+)'", AGENT):
            self.assertIn(v, schema.VERBS + ("pull",))
        # 'pull' is only printed by the local-only entry
        for m in re.finditer(r"Complete-AgentVerb -Verb 'pull'", AGENT):
            self.assertLess(AGENT.rfind("function ", 0, m.start()), m.start())
            self.assertIn("function Invoke-AgentPull", AGENT[AGENT.rfind("function ", 0, m.start()):])

    def test_exit_codes(self):
        body = function_body("Get-ExitCodeFor")
        self.assertIn("'failed' { return 2 }", body)
        self.assertIn("'busy' { return 3 }", body)

    def test_powershell_51_compatibility(self):
        for name, src in (("agent", AGENT), ("bootstrap", BOOT)):
            code = strip_comments_and_strings(src)
            self.assertNotIn("??", code, name)
            self.assertNotRegex(code, r"&&|\|\|", name)
            self.assertNotRegex(code, r"-Parallel", name)
            self.assertNotRegex(code, r"\?\s*[^\s].*\s:\s", name)  # ternary
            self.assertNotRegex(code, r"\$\w+\?\.", name)  # null-conditional
            self.assertNotRegex(code, r"ForEach-Object\s+-Parallel", name)
            self.assertIsNone(re.search(r"\bpwsh\b", code), name)
            self.assertNotRegex(src, r"[^\x00-\x7f]", name + " must stay ASCII (no BOM needed)")

    def test_no_aliases_and_no_write_host(self):
        code = strip_comments_and_strings(AGENT + BOOT)
        for alias in ("gci", "iex", "foreach ", "%", "ls ", "cat ", "echo ", "rm ", "sleep "):
            if alias == "%":
                # '%' is also the format operator: only the ForEach-Object alias (`| % {`) is banned
                self.assertNotRegex(code, r"\|\s*%\s*[{(]", alias)
                continue
            self.assertNotRegex(code, r"(^|[\s(|;])" + re.escape(alias.strip()) + r"\s+-?\w", alias)
        self.assertNotIn("Write-Host", code)
        self.assertNotIn("Invoke-Expression", code)
        self.assertNotIn("$Host", code.replace("$HostName", ""))

    def test_forbidden_tools(self):
        code = strip_comments_and_strings(AGENT + BOOT)
        self.assertNotRegex(code, r"(?i)\bchoco(latey)?\b")
        for line in (AGENT + BOOT).splitlines():
            if "wsl" in line and "--shutdown" in line:
                self.assertTrue(line.lstrip().startswith(("#", "'")) or "never" in line.lower(), line)
        self.assertNotIn("wsl.exe --shutdown", AGENT)
        self.assertNotIn("'--shutdown'", AGENT)
        self.assertIn("Microsoft.Update.Session", AGENT)
        self.assertIn("Microsoft.Update.UpdateColl", AGENT)

    def test_update_steps_order_and_wsl_guard(self):
        job = function_body("Invoke-AgentJob")
        order = [job.index("-Name '%s'" % n) for n in ("windows_update", "winget", "scoop", "wsl", "defender")]
        self.assertEqual(order, sorted(order))
        scoop = function_body("Invoke-StepScoop")
        for cmd in ("scoop update'", "scoop update --all'", "scoop update --all --global"):
            self.assertIn(cmd, scoop)
        wsl = function_body("Invoke-StepWsl")
        self.assertIn("'--update'", wsl)
        self.assertIn("--running", wsl)
        self.assertIn("-l', '-q'", wsl)
        self.assertIn("sysup", wsl)
        self.assertLess(wsl.index("--running"), wsl.index("'--update'"))
        self.assertIn("Update-MpSignature", function_body("Invoke-StepDefender"))

    def test_winget_and_scoop_only_in_job_not_in_ssh_verbs(self):
        # winget/Scoop run in the scheduled task (-RunJob), never from the SSH verbs.
        for name in ("Invoke-VerbCheck", "Invoke-VerbReboot", "Invoke-VerbReport", "Invoke-StartUpdate", "Invoke-VerbRebootStatus"):
            body = function_body(name)
            self.assertNotIn("winget", body.replace("winget is not queried", ""), name)
            self.assertNotIn("scoop", body, name)
        self.assertIn("Start-ScheduledTask -TaskName $script:UpdateTask", function_body("Invoke-StartUpdate"))

    def test_preflight_checks(self):
        pre = function_body("Get-Preflight")
        for reason in ("disk_low", "on_battery", "metered_network", "update_in_progress", "user_active", "no_interactive_session"):
            self.assertIn(reason, pre)

    def test_local_only_entries_refused_in_ssh_context(self):
        main = function_body("Invoke-AgentMain")
        first = main.split("return\n    }", 1)[0]
        self.assertIn("Test-SshContext", first)
        self.assertLess(first.index("Test-SshContext"), first.index("Invoke-AgentJob"))
        ctx = function_body("Test-SshContext")
        self.assertIn("SSH_CONNECTION", ctx)
        self.assertIn("SSH_ORIGINAL_COMMAND", ctx)

    def test_pull_mode_never_restarts(self):
        # Everything reachable from the pull entry: no restart code.
        reachable = ["Invoke-AgentPull", "Get-PullDeniedReason", "Get-ConfValue", "Send-PullNotification",
                     "Invoke-StartUpdate", "Invoke-AgentJob"]
        for name in reachable:
            body = function_body(name)
            for word in ("shutdown", "Restart-Computer", "Invoke-VerbReboot", "/r "):
                self.assertNotIn(word, body, "%s reaches %s" % (name, word))
        # the only caller of the restart verb is the SSH switch
        self.assertEqual(len(re.findall(r"Invoke-VerbReboot(?!Status)", AGENT)), 2)  # definition + switch label
        self.assertEqual(len(re.findall(r"shutdown\.exe", AGENT)), 1)
        reboot = function_body("Invoke-VerbReboot")
        self.assertIn("/t 30", reboot)
        self.assertIn("$LASTEXITCODE -ne 0", reboot)
        self.assertIn("shutdown_failed", reboot)
        self.assertIn("'reboot' { Invoke-VerbReboot }", AGENT)

    def test_pull_rules(self):
        pull = function_body("Invoke-AgentPull")
        self.assertIn("recent_update", pull)
        self.assertIn("$script:PullDays * 86400", pull)
        self.assertIn("$script:PullDays = 7", AGENT)
        self.assertIn("guardian", function_body("Get-PullDeniedReason"))
        self.assertIn("pull-enabled", function_body("Get-PullDeniedReason"))
        self.assertIn("no-pull", function_body("Get-PullDeniedReason"))
        notify = function_body("Send-PullNotification")
        self.assertIn("Priority = '2'", notify)
        self.assertIn("https://", notify)
        # token: read from NTFY_TOKEN_FILE, only ever placed in the Authorization header
        self.assertIn("Get-ConfValue -Key 'NTFY_TOKEN_FILE'", notify)
        self.assertIn("$headers['Authorization'] = 'Bearer ' + $token", notify)
        self.assertEqual(len(re.findall(r"\$token\b", notify)), 3)  # assigned, validated, header
        for sink in ("-Uri ($url", "Write-AgentLog", "Start-Process", "-Body"):
            for line in notify.splitlines():
                if sink in line:
                    self.assertNotIn("$token", line, line)
        # the 7-day comparison reads the last-success stamp; a future stamp is stale
        self.assertIn("'last-success'", pull)
        self.assertIn("$age -ge 0", pull)
        self.assertIn("{1,11}", pull)
        self.assertEqual(len(re.findall(r"\bnot_enabled\b", function_body("Get-PullDeniedReason"))), 1)
        self.assertNotIn("pull_pull", AGENT)

    def test_serialization_depth_compress_arrays_int(self):
        build = function_body("Get-ResultJson")
        self.assertRegex(build, r"ConvertTo-Json -InputObject \$safe -Depth ([5-9]|\d\d) -Compress")
        self.assertIn("@($script:R[$arrayKey])", build)
        self.assertIn("'changes', 'config_conflicts'", build)
        self.assertIn("[int](Get-DiskFreePct)", function_body("Get-HealthSnapshot"))
        self.assertIn("return [int][math]::Floor", function_body("Get-DiskFreePct"))
        self.assertNotRegex(AGENT, r"ConvertTo-Json(?![^\n]*-Compress)")

    def test_ended_only_at_completion(self):
        build = function_body("Get-ResultJson")
        self.assertIn("if ($Final -and $null -eq $script:R['ended'])", build)
        job = function_body("Invoke-AgentJob")
        running = job.split("$script:R['status'] = 'running'", 1)[1].split("Invoke-UpdateStep", 1)[0]
        self.assertNotIn("-Final", running)
        self.assertIn("Save-JobState -JobDir $jobDir -Final", job)
        self.assertIn("Get-ResultJson -Verb 'update' -Final", function_body("Save-JobState"))

    def test_timeout_kills_tree_and_is_reported(self):
        proc = function_body("Invoke-CappedProcess")
        self.assertIn("taskkill.exe /T /F /PID", proc)
        self.assertNotIn(".Kill()", proc)
        self.assertIn("$script:JobMaxMinutes = 120", AGENT)
        job = function_body("Invoke-AgentJob")
        self.assertIn("$script:R['reason'] = 'timeout'", job)
        self.assertNotIn("'timeout'", re.sub(r"\$script:R\['reason'\] = 'timeout'", "", job).replace("# 'timeout' is a master-only status", ""))
        self.assertIn("JobDeadline", function_body("Invoke-UpdateStep"))

    def test_winget_and_wsl_changes_are_counted(self):
        winget = function_body("Invoke-StepWinget")
        self.assertLess(winget.index("Get-WingetUpgradeList"), winget.index("'--all'") if "'--all'" in winget else winget.index("upgrade', '--all'"))
        self.assertIn("Add-JobChange -Name ('winget:' + $pkg.Id)", winget)
        self.assertIn("--include-unknown", function_body("Get-WingetUpgradeList"))
        self.assertIn("-{5,}", function_body("ConvertFrom-WingetUpgradeTable"))
        wsl = function_body("Invoke-StepWsl")
        self.assertIn("Add-JobChange -Name ('wsl:' + $distro)", wsl)
        self.assertIn("Add-JobChange -Name 'wsl:kernel'", wsl)

    def test_lock_handoff_and_atomic_takeover(self):
        alive = function_body("Test-LockAlive")
        self.assertIn("Test-JobOwnerAlive", alive)
        owner = function_body("Test-JobOwnerAlive")
        self.assertIn("'started'", owner)
        self.assertIn("'running'", owner)
        self.assertIn("AddMinutes(-10)", owner)
        enter = function_body("Enter-AgentLock")
        self.assertIn("[System.IO.File]::Move($script:LockFile, $aside)", enter)
        self.assertIn("NewGuid", enter)
        self.assertNotIn("Remove-Item -LiteralPath $script:LockFile", enter)
        self.assertLess(enter.index("File]::Move"), enter.index("CreateNew") + len(enter))

    def test_no_named_kernel_objects_in_agent(self):
        # Global\ / Local\ named objects can be squatted by any local user (DoS).
        self.assertNotIn("System.Threading.Mutex", AGENT)
        self.assertNotIn("Global\\", AGENT)
        self.assertNotIn("Local\\", AGENT)

    def test_stale_takeover_is_serialized_by_a_state_dir_lock_file(self):
        enter = function_body("Enter-AgentLock")
        self.assertRegex(enter, r"\$takeoverPath = Join-Path \$script:StateDir ")
        self.assertRegex(enter, r"Open\(\$takeoverPath, \[System\.IO\.FileMode\]::OpenOrCreate, "
                                r"\[System\.IO\.FileAccess\]::ReadWrite, \[System\.IO\.FileShare\]::None\)")
        self.assertIn("Start-Sleep -Milliseconds 200", enter)
        self.assertIn("AddSeconds(15)", enter)
        self.assertRegex(enter, r"finally\s*\{[^}]*\$guard\.Dispose\(\)")
        # staleness is re-checked WHILE holding the file, before the stale lock is moved aside
        inside = enter[enter.index("FileShare]::None)\n                    }\n                    catch [System.UnauthorizedAccess"):]
        self.assertLess(inside.index("Test-LockAlive"), inside.index("File]::Move"))

    def test_takeover_errors_are_logged_not_swallowed(self):
        enter = function_body("Enter-AgentLock")
        m = re.search(r"catch \[System\.UnauthorizedAccessException\] \{(.*?)\n\s*\}", enter, re.S)
        self.assertIsNotNone(m, "UnauthorizedAccessException must be caught explicitly")
        self.assertIn("Write-AgentLog", m.group(1))
        self.assertIn("return $false", m.group(1))
        busy = re.search(r"catch \[System\.IO\.IOException\] \{\s*if \(\[DateTime\]::UtcNow -ge \$deadline\) \{(.*?)\}", enter, re.S)
        self.assertIsNotNone(busy, "IOException after the retry budget must be handled")
        self.assertIn("Write-AgentLog", busy.group(1))

    def test_external_utf8_output_is_read_as_utf8(self):
        winget = function_body("Get-WingetUpgradeList")
        self.assertRegex(winget, r"Get-Content -LiteralPath \$outFile -Encoding UTF8")
        self.assertIn("-Encoding UTF8", function_body("Get-CappedTail"))

    def test_test_overrides_restricted_to_temp(self):
        ov = function_body("Get-TestOverridePath")
        self.assertIn("$script:TestMode", ov)
        self.assertIn("$env:TEMP", ov)
        self.assertIn("StartsWith", ov)
        for name in ("FLEET_AGENT_STATE_DIR", "FLEET_AGENT_CONF_DIR"):
            self.assertIn("Get-TestOverridePath -Name '%s'" % name, AGENT)
            self.assertNotIn("$env:" + name, AGENT)

    def test_report_survives_corrupt_state_and_log_is_capped(self):
        rep = function_body("Invoke-VerbReport")
        self.assertIn("catch {", rep)
        self.assertIn("state_unreadable", rep)
        self.assertLess(rep.index("try {"), rep.index("ConvertFrom-Json"))
        log = function_body("Write-AgentLog")
        self.assertIn("$script:AgentLogMaxBytes", log)
        self.assertIn("$script:AgentLogMaxBytes = 1048576", AGENT)

    def test_secrets_masked_on_structures(self):
        self.assertIn("IDictionary", function_body("Protect-Data"))
        self.assertIn("Protect-Text -Text ([string]$key)", function_body("Protect-Data"))
        build = function_body("Get-ResultJson")
        self.assertLess(build.index("Protect-Data"), build.index("ConvertTo-Json"))
        self.assertNotRegex(build.split("ConvertTo-Json", 1)[1], r"Protect-Text")

    def test_remote_output_is_capped(self):
        self.assertIn("-RedirectStandardOutput", function_body("Invoke-CappedProcess"))
        self.assertIn("-RedirectStandardError", function_body("Invoke-CappedProcess"))
        self.assertIn("$script:LogCapChars", function_body("Get-CappedTail"))
        self.assertIn("-Lines 20", function_body("Invoke-AgentJob"))

    def test_lock_is_atomic(self):
        self.assertIn("FileMode]::CreateNew", function_body("Enter-AgentLock"))
        self.assertIn("FileShare]::None", function_body("Enter-AgentLock"))


class StaticBootstrap(unittest.TestCase):
    def test_firewall_tailnet_only(self):
        fw = function_body_of(BOOT, "Initialize-SshFirewall")
        self.assertIn("-RemoteAddress '100.64.0.0/10'", fw)
        self.assertIn("-LocalPort 22", fw)
        self.assertIn("Disable-NetFirewallRule -Name 'OpenSSH-Server-In-TCP'", fw)

    def test_forced_command_and_acl(self):
        self.assertIn("restrict,command=", BOOT)
        self.assertIn("administrators_authorized_keys", BOOT)
        acl = function_body_of(BOOT, "Protect-AclAdminOnly")
        self.assertIn("$adminSid = 'S-1-5-32-544'", BOOT)  # Administrators
        self.assertIn("$systemSid = 'S-1-5-18'", BOOT)  # SYSTEM
        self.assertIn("@($adminSid, $systemSid)", acl)
        self.assertIn("SetAccessRuleProtection($true, $false)", acl)
        keys = function_body_of(BOOT, "Write-AuthorizedKey")
        self.assertLess(keys.index("Protect-AclAdminOnly"), keys.index("Move-Item"))
        self.assertIn("Assert-AclAdminOnly", keys)
        self.assertIn("ssh-ed25519", BOOT)
        # no remote-supplied text ever reaches the command line
        self.assertIn("-File \\\"' + $agentDest + '\\\"'", BOOT)

    def test_acl_owner_and_reparse_checks(self):
        prot = function_body_of(BOOT, "Protect-AclAdminOnly")
        self.assertIn("$acl.SetOwner(", prot)
        self.assertIn("Get-ChildItem -LiteralPath $Path -Force", prot)
        self.assertIn("ReparsePoint", prot)
        self.assertIn("Protect-AclAdminOnly -Path $child.FullName", prot)
        assertion = function_body_of(BOOT, "Assert-AclAdminOnly")
        self.assertIn("Assert-OwnerTrusted", assertion)
        self.assertIn("Assert-NoReparsePoint", assertion)
        walk = function_body_of(BOOT, "Assert-NoReparsePoint")
        self.assertIn("Split-Path -Parent $cur", walk)  # ancestors
        self.assertIn("FileAttributes]::ReparsePoint", walk)
        self.assertIn("refusing reparse point", walk)
        owner = function_body_of(BOOT, "Assert-OwnerTrusted")
        self.assertIn("GetOwner(", owner)
        self.assertIn("throw", owner)
        init = function_body_of(BOOT, "Initialize-AdminDir")
        self.assertLess(init.index("Assert-NoReparsePoint"), init.index("New-Item"))
        self.assertLess(init.index("Assert-OwnerTrusted"), init.index("Protect-AclAdminOnly"))
        inst = function_body_of(BOOT, "Install-AgentFile")
        self.assertIn("Initialize-AdminDir -Path $dir", inst)
        self.assertIn("Assert-AclAdminOnly -Path $stateDir", inst)

    def test_firewall_tailscale_interface_only(self):
        fw = function_body_of(BOOT, "Initialize-SshFirewall")
        self.assertIn("-InterfaceAlias $alias", fw)
        self.assertIn("$alias = 'Tailscale'", fw)
        self.assertLess(fw.index("Get-NetAdapter"), fw.index("New-NetFirewallRule"))
        self.assertIn("Remove-NetFirewallRule -Name $rule", fw)  # idempotent

    def test_sshd_config_hardening(self):
        hard = function_body_of(BOOT, "Set-SshdHardening")
        for want in ("'PasswordAuthentication' -Value 'no'", "'KbdInteractiveAuthentication' -Value 'no'",
                     "'AllowUsers' -Value $SshUser", "fleet-bak-", "Match Group administrators",
                     "administrators_authorized_keys"):
            self.assertIn(want, hard)
        self.assertLess(hard.index("Copy-Item -LiteralPath $cfg"), hard.index("WriteAllLines"))
        self.assertLess(hard.index("sshd.exe"), hard.index("Restart-Service"))
        self.assertIn("$LASTEXITCODE -ne 0", hard)
        self.assertIn("Copy-Item -LiteralPath $backup -Destination $cfg", hard)
        self.assertLess(hard.index("Copy-Item -LiteralPath $backup"), hard.index("throw ('sshd -t"))
        self.assertRegex(BOOT, r"\[Parameter\(Mandatory = \$true\)\]\s*\[ValidatePattern\([^\n]*\)\]\s*\[string\]\$SshUser")
        self.assertLess(BOOT.index("\nSet-SshdHardening"), BOOT.index("\nWrite-AuthorizedKey"))

    def test_task_user_must_be_administrator(self):
        self.assertIn("Assert-IsLocalAdministrator -Account $TaskUser", function_body_of(BOOT, "Assert-TaskUserIsAdministrator"))
        self.assertLess(BOOT.index("\nAssert-TaskUserIsAdministrator"), BOOT.index("\nInstall-AgentFile"))

    def test_ssh_user_must_be_administrator_too(self):
        self.assertIn("Assert-IsLocalAdministrator -Account $SshUser", function_body_of(BOOT, "Assert-SshUserIsAdministrator"))
        self.assertLess(BOOT.index("\nAssert-SshUserIsAdministrator"), BOOT.index("\nInstall-AgentFile"))

    def test_admin_check_compares_sids_not_names(self):
        chk = function_body_of(BOOT, "Assert-IsLocalAdministrator")
        self.assertIn("System.Security.Principal.NTAccount($Account)", chk)
        self.assertIn("Translate([System.Security.Principal.SecurityIdentifier])", chk)
        self.assertIn("-notcontains $sid", chk)
        self.assertNotIn(".Name", chk)
        members = function_body_of(BOOT, "Get-AdministratorMemberSid")
        self.assertIn("Get-LocalGroupMember -SID $adminSid", members)
        self.assertIn("$m.SID.Value", members)
        # orphaned / AzureAD members make Get-LocalGroupMember throw: ADSI fallback, SIDs only
        self.assertIn("catch", members)
        self.assertIn("WinNT://./Administrators,group", members)
        self.assertIn("objectSid", members)
        self.assertIn("throw", chk)

    def test_sshd_stays_stopped_until_hardened(self):
        inst = function_body_of(BOOT, "Install-OpenSshServer")
        self.assertIn("Disable-NetFirewallRule -Name 'OpenSSH-Server-In-TCP'", inst)
        self.assertLess(inst.index("Add-WindowsCapability"), inst.index("Disable-NetFirewallRule"))
        self.assertIn("Stop-Service -Name sshd", inst)
        self.assertNotIn("Start-Service", inst)
        self.assertNotIn("Restart-Service", inst)
        hard = function_body_of(BOOT, "Set-SshdHardening")
        self.assertLess(hard.index("$LASTEXITCODE -ne 0"), hard.index("Restart-Service"))

    def test_full_powershell_path_and_hidden_update_task(self):
        self.assertIn("System32\\WindowsPowerShell\\v1.0\\powershell.exe", BOOT)
        self.assertIn("$psExe = $psExePath", function_body_of(BOOT, "Register-AgentTask"))
        reg = function_body_of(BOOT, "Register-AgentTask")
        self.assertIn("-File \"' + $agentDest + '\"'", reg)
        self.assertIn("'-WindowStyle Hidden ' + $baseArgs + ' -RunJob'", reg)
        self.assertNotRegex(BOOT, r"(?<![\\\w])powershell\.exe -NoProfile")

    def test_agent_installed_staged_verified_then_moved(self):
        inst = function_body_of(BOOT, "Install-AgentFile")
        self.assertLess(inst.index("Copy-Item"), inst.index("Get-FileHash"))
        self.assertLess(inst.index("Get-FileHash"), inst.index("Move-Item"))
        self.assertIn("hash mismatch", inst)

    def test_event_source_tasks_winget(self):
        self.assertIn("New-EventLog -LogName Application -Source 'fleet-agent'", BOOT)
        self.assertIn("fleet-agent-update", BOOT)
        self.assertIn("-LogonType Interactive", BOOT)
        self.assertIn("New-TimeSpan -Minutes 120", BOOT)
        self.assertIn("-RunJob", BOOT)
        self.assertIn("-RunPull", BOOT)
        self.assertIn("-UserId 'SYSTEM'", BOOT)
        self.assertIn("Microsoft.DesktopAppInstaller", BOOT)
        self.assertIn("RunSSH", BOOT)  # Tailscale SSH must stay off

    def test_pull_is_opt_in(self):
        reg = function_body_of(BOOT, "Register-AgentTask")
        self.assertIn("if ($EnablePull)", reg)
        self.assertLess(reg.index("if ($EnablePull)"), reg.index("fleet-agent-pull"))
        self.assertIn("pull-enabled", reg)

    def test_no_secret_handling(self):
        for word in ("op read", "op://", "Invoke-RestMethod", "password"):
            self.assertNotIn(word, BOOT.replace("op://Private/Fleet/public-key-<master>", ""), word)


def function_body_of(src, name):
    start = src.index("function %s " % name)
    nxt = src.find("\nfunction ", start + 10)
    nxt2 = src.find("\nif (", start + 10)
    ends = [e for e in (nxt, nxt2) if e != -1]
    return src[start:min(ends) if ends else len(src)]


class JsonFixtures(unittest.TestCase):
    def parse(self, verb, status, **over):
        line = fixture(verb, status, **over)
        self.assertEqual(len(line.splitlines()), 1)
        entry, problem = schema.parse_agent_output(line, "alias", verb)
        self.assertIsNone(problem, line)
        self.assertEqual(entry["status"], status)
        self.assertEqual(entry["host"], "alias")
        return entry

    def test_every_agent_status_validates(self):
        for status in schema.AGENT_STATUSES:
            with self.subTest(status=status):
                self.parse("check", status)

    def test_every_verb_validates(self):
        for verb in schema.VERBS:
            with self.subTest(verb=verb):
                self.parse(verb, "up-to-date")

    def test_check_pending_updates(self):
        e = self.parse("check", "skipped", reason="updates_pending", packages=7,
                       major_available="Windows 11, version 25H2")
        self.assertEqual((e["packages"], e["reason"]), (7, "updates_pending"))
        self.assertEqual(e["major_available"], "Windows 11, version 25H2")

    def test_update_started_and_final(self):
        e = self.parse("update", "started", job="20261031T100000Z-4242")
        self.assertEqual(e["job"], "20261031T100000Z-4242")
        e = self.parse("update", "updated", job="20261031T100000Z-4242", packages=2, reboot_required=True,
                       changes=[{"name": "2026-10 Cumulative Update (KB5000000)", "from": "", "to": "installed"},
                                {"name": "scoop:git", "from": "2.50.0", "to": "2.51.0"}],
                       log_tail="--- winget upgrade --all (exit 0)\nNo applicable upgrade found.")
        self.assertEqual(len(e["changes"]), 2)
        self.assertTrue(e["reboot_required"])

    def test_preflight_blocks(self):
        for why in ("on_battery", "metered_network", "user_active", "no_interactive_session", "disk_low", "update_in_progress"):
            with self.subTest(why=why):
                e = self.parse("update", "skipped", reason=why, preflight={"ok": False, "blocked_by": why})
                self.assertFalse(e["preflight"]["ok"])
                self.assertEqual(e["preflight"]["blocked_by"], why)

    def test_failed_and_degraded(self):
        self.parse("update", "failed", reason="winget_failed")
        e = self.parse("update", "degraded", reason="critical services down",
                       health_after={"failed_units": [], "unhealthy_containers": [], "disk_free_pct": {"C:": 9},
                                     "critical_services_down": ["sshd"]})
        self.assertEqual(e["health_after"]["critical_services_down"], ["sshd"])

    def test_disk_pct_must_be_integer(self):
        bad = fixture("check", "up-to-date", health_before={"failed_units": [], "unhealthy_containers": [], "disk_free_pct": {"C:": 42.5}})
        entry, problem = schema.parse_agent_output(bad, "alias", "check")
        self.assertIsNone(entry)
        self.assertIn("disk_free_pct", problem)

    def test_master_statuses_are_rejected_from_the_agent(self):
        for status in schema.MASTER_STATUSES:
            entry, problem = schema.parse_agent_output(fixture("check", status), "alias", "check")
            self.assertIsNone(entry, status)
            self.assertIn("status", problem, status)

    def test_pull_output_is_not_accepted_as_a_verb_result(self):
        # The local-only "pull" line is never fetched by the master over SSH.
        entry, problem = schema.parse_agent_output(fixture("pull", "skipped", reason="recent_update"), "alias", "check")
        self.assertIsNone(entry)
        self.assertIn("verb", problem)

    def test_secrets_in_fixture_are_masked_by_master_too(self):
        e = self.parse("update", "failed", reason="winget_failed",
                       log_tail="token=tk_abcdefghijklmnop0123 password=hunter22 ok")
        self.assertNotIn("hunter22", e["log_tail"])
        self.assertNotIn("tk_abcdefghijklmnop0123", e["log_tail"])


if __name__ == "__main__":
    unittest.main()
