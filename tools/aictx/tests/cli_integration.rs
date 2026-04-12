//! Integration tests for cctx CLI subcommands.
//!
//! These tests run the binary and verify output/exit codes.

use std::path::PathBuf;
use std::process::Command;

fn cctx_bin() -> PathBuf {
    // Use cargo to find the built binary
    let mut path = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    path.push("target");
    path.push("debug");
    path.push("aictx");
    path
}

fn run_cctx(args: &[&str]) -> std::process::Output {
    Command::new(cctx_bin())
        .args(args)
        .env("HOME", std::env::var("HOME").unwrap_or_default())
        .output()
        .expect("Failed to run cctx binary")
}

fn run_cctx_in_dir(args: &[&str], dir: &std::path::Path) -> std::process::Output {
    Command::new(cctx_bin())
        .args(args)
        .current_dir(dir)
        .env("HOME", std::env::var("HOME").unwrap_or_default())
        .output()
        .expect("Failed to run cctx binary")
}

// ── Version / Help ──────────────────────────────────────────────────────

#[test]
fn version_prints_and_exits_ok() {
    let output = run_cctx(&["--version"]);
    assert!(output.status.success());
    let stdout = String::from_utf8_lossy(&output.stdout);
    assert!(stdout.contains("aictx"));
}

#[test]
fn help_prints_subcommands() {
    let output = run_cctx(&["--help"]);
    assert!(output.status.success());
    let stdout = String::from_utf8_lossy(&output.stdout);
    assert!(stdout.contains("scan"));
    assert!(stdout.contains("apply"));
    assert!(stdout.contains("status"));
    assert!(stdout.contains("doctor"));
    assert!(stdout.contains("watch"));
    assert!(stdout.contains("plugin"));
    assert!(stdout.contains("hook"));
    assert!(stdout.contains("config"));
}

// ── Scan ────────────────────────────────────────────────────────────────

#[test]
fn scan_detects_rust_project() {
    let manifest_dir = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    let output = run_cctx_in_dir(&["scan"], &manifest_dir);
    assert!(output.status.success());
    let stdout = String::from_utf8_lossy(&output.stdout);
    assert!(stdout.to_lowercase().contains("rust"));
}

#[test]
fn scan_empty_dir_succeeds() {
    let tmp = std::env::temp_dir().join("cctx-integ-scan-empty");
    let _ = std::fs::create_dir_all(&tmp);
    let output = run_cctx_in_dir(&["scan"], &tmp);
    assert!(output.status.success());
    let _ = std::fs::remove_dir_all(&tmp);
}

// ── Index ───────────────────────────────────────────────────────────────

#[test]
fn index_prints_counts() {
    let output = run_cctx(&["index"]);
    assert!(output.status.success());
    let stdout = String::from_utf8_lossy(&output.stdout);
    assert!(stdout.contains("Indexed"));
    assert!(stdout.contains("skills"));
}

// ── Doctor ──────────────────────────────────────────────────────────────

#[test]
fn doctor_runs_without_error() {
    let output = run_cctx(&["doctor"]);
    assert!(output.status.success());
    let stdout = String::from_utf8_lossy(&output.stdout);
    assert!(stdout.contains("Health check"));
}

// ── Cost ────────────────────────────────────────────────────────────────

#[test]
fn cost_runs_in_project_dir() {
    let manifest_dir = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    let output = run_cctx_in_dir(&["cost"], &manifest_dir);
    // May succeed or fail depending on state, but should not panic
    assert!(
        output.status.success() || !String::from_utf8_lossy(&output.stderr).contains("panicked")
    );
}

// ── Status ──────────────────────────────────────────────────────────────

#[test]
fn status_runs_in_project_dir() {
    let manifest_dir = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    let output = run_cctx_in_dir(&["status"], &manifest_dir);
    assert!(output.status.success());
    let stdout = String::from_utf8_lossy(&output.stdout);
    assert!(stdout.contains("Status"));
}

// ── Hook ────────────────────────────────────────────────────────────────

#[test]
fn hook_zsh_outputs_valid_code() {
    let output = run_cctx(&["hook", "zsh"]);
    assert!(output.status.success());
    let stdout = String::from_utf8_lossy(&output.stdout);
    assert!(stdout.contains("chpwd"));
    assert!(stdout.contains("cctx apply"));
}

#[test]
fn hook_bash_outputs_valid_code() {
    let output = run_cctx(&["hook", "bash"]);
    assert!(output.status.success());
    let stdout = String::from_utf8_lossy(&output.stdout);
    assert!(stdout.contains("PROMPT_COMMAND"));
}

#[test]
fn hook_fish_outputs_valid_code() {
    let output = run_cctx(&["hook", "fish"]);
    assert!(output.status.success());
    let stdout = String::from_utf8_lossy(&output.stdout);
    assert!(stdout.contains("on-variable PWD"));
}

#[test]
fn hook_unknown_shell_fails() {
    let output = run_cctx(&["hook", "powershell"]);
    assert!(!output.status.success());
}

// ── Config ──────────────────────────────────────────────────────────────

#[test]
fn config_list_shows_keys() {
    let output = run_cctx(&["config", "list"]);
    assert!(output.status.success());
    let stdout = String::from_utf8_lossy(&output.stdout);
    assert!(stdout.contains("ai.enabled"));
    assert!(stdout.contains("ai.provider"));
}

#[test]
fn config_get_known_key() {
    let output = run_cctx(&["config", "get", "ai.enabled"]);
    assert!(output.status.success());
    let stdout = String::from_utf8_lossy(&output.stdout);
    assert!(stdout.contains("ai.enabled"));
}

#[test]
fn config_get_unknown_key() {
    let output = run_cctx(&["config", "get", "nonexistent.key"]);
    assert!(output.status.success());
    let stdout = String::from_utf8_lossy(&output.stdout);
    assert!(stdout.contains("not found"));
}

// ── Plugin subcommands ──────────────────────────────────────────────────

#[test]
fn plugin_list_runs() {
    let output = run_cctx(&["plugin", "list"]);
    assert!(output.status.success());
}

#[test]
fn plugin_search_no_results() {
    let output = run_cctx(&["plugin", "search", "zzz_nonexistent_xyz"]);
    assert!(output.status.success());
    let stdout = String::from_utf8_lossy(&output.stdout);
    assert!(stdout.contains("No resources matching"));
}

// ── Profiles ────────────────────────────────────────────────────────────

#[test]
fn profiles_list_runs() {
    let output = run_cctx(&["profiles"]);
    assert!(output.status.success());
    let stdout = String::from_utf8_lossy(&output.stdout);
    assert!(stdout.contains("Profiles"));
}

// ── Trim ────────────────────────────────────────────────────────────────

#[test]
fn trim_nonexistent_file_fails() {
    let output = run_cctx(&["trim", "/tmp/cctx-nonexistent-file.md"]);
    assert!(!output.status.success());
}

// ── Config set/get roundtrip ────────────────────────────────────────────

#[test]
fn config_set_and_get_roundtrip() {
    let tmp = std::env::temp_dir().join("cctx-integ-config-rt");
    let _ = std::fs::create_dir_all(tmp.join(".git")); // Make it a project
    let _ = std::fs::remove_file(tmp.join(".cctx.yaml"));

    let output = run_cctx_in_dir(&["config", "set", "ai.enabled", "true"], &tmp);
    assert!(output.status.success());

    let output = run_cctx_in_dir(&["config", "get", "ai.enabled"], &tmp);
    assert!(output.status.success());
    let stdout = String::from_utf8_lossy(&output.stdout);
    assert!(stdout.contains("true"));
    assert!(stdout.contains("[project]"));

    let _ = std::fs::remove_dir_all(&tmp);
}
