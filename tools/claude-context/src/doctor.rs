use anyhow::Result;

use crate::config::AppConfig;
use crate::indexer::Index;
use crate::profile::ProfileManager;

/// Confidence tier thresholds
pub const TIER_CRITICAL: f32 = 0.95;
pub const TIER_HIGH: f32 = 0.80;
pub const TIER_MEDIUM: f32 = 0.60;

pub struct DoctorReport {
    pub checks: Vec<CheckResult>,
}

pub struct CheckResult {
    pub name: String,
    pub status: CheckStatus,
    pub message: String,
}

#[derive(PartialEq)]
pub enum CheckStatus {
    Ok,
    Warning,
    Error,
}

pub fn run_doctor(config: &AppConfig) -> Result<DoctorReport> {
    let mut checks = Vec::new();

    checks.push(check_source_dirs(config));
    checks.push(check_config_dir(config));
    checks.extend(check_index(config));
    checks.extend(check_profiles(config));
    checks.extend(check_project_symlinks(config));
    checks.extend(check_cli_detection(config));

    Ok(DoctorReport { checks })
}

fn check_source_dirs(config: &AppConfig) -> CheckResult {
    let skills_ok = config.paths.skills_dir.exists();
    let agents_ok = config.paths.agents_dir.exists();
    let commands_ok = config.paths.commands_dir.exists();
    let rules_ok = config.paths.rules_dir.exists();

    if skills_ok && agents_ok && commands_ok && rules_ok {
        CheckResult {
            name: "Source directories".to_string(),
            status: CheckStatus::Ok,
            message: format!(
                "skills: {}, agents: {}, commands: {}, rules: {}",
                config.paths.skills_dir.display(),
                config.paths.agents_dir.display(),
                config.paths.commands_dir.display(),
                config.paths.rules_dir.display(),
            ),
        }
    } else {
        let mut missing = Vec::new();
        if !skills_ok {
            missing.push(format!("skills: {}", config.paths.skills_dir.display()));
        }
        if !agents_ok {
            missing.push(format!("agents: {}", config.paths.agents_dir.display()));
        }
        if !commands_ok {
            missing.push(format!("commands: {}", config.paths.commands_dir.display()));
        }
        if !rules_ok {
            missing.push(format!("rules: {}", config.paths.rules_dir.display()));
        }
        CheckResult {
            name: "Source directories".to_string(),
            status: CheckStatus::Error,
            message: format!("Missing: {}", missing.join(", ")),
        }
    }
}

fn check_config_dir(config: &AppConfig) -> CheckResult {
    let config_ok = config.paths.config_dir.exists();
    let profiles_ok = config.paths.profiles_dir.exists();
    let defaults_ok = config.paths.config_dir.join("defaults.yaml").exists();

    if config_ok && profiles_ok && defaults_ok {
        CheckResult {
            name: "Config directory".to_string(),
            status: CheckStatus::Ok,
            message: "defaults.yaml and profiles/ present".to_string(),
        }
    } else {
        let mut missing = Vec::new();
        if !config_ok {
            missing.push("config dir");
        }
        if !profiles_ok {
            missing.push("profiles/");
        }
        if !defaults_ok {
            missing.push("defaults.yaml");
        }
        CheckResult {
            name: "Config directory".to_string(),
            status: CheckStatus::Warning,
            message: format!("Missing: {} (using built-in defaults)", missing.join(", ")),
        }
    }
}

fn check_index(config: &AppConfig) -> Vec<CheckResult> {
    let mut results = Vec::new();

    match Index::build(config) {
        Ok(index) => {
            let msg = format!(
                "{} skills, {} agents, {} commands",
                index.skills.len(),
                index.agents.len(),
                index.commands.len()
            );

            if index.skills.is_empty() && index.agents.is_empty() {
                results.push(CheckResult {
                    name: "Index".to_string(),
                    status: CheckStatus::Error,
                    message: format!("Empty index: {}", msg),
                });
            } else {
                results.push(CheckResult {
                    name: "Index".to_string(),
                    status: CheckStatus::Ok,
                    message: msg,
                });
            }

            // Check for duplicate names
            let mut skill_names: Vec<&str> = index.skills.iter().map(|s| s.name.as_str()).collect();
            skill_names.sort();
            let dupes: Vec<&&str> = skill_names.windows(2).filter(|w| w[0] == w[1]).map(|w| &w[0]).collect();
            if !dupes.is_empty() {
                results.push(CheckResult {
                    name: "Duplicate skills".to_string(),
                    status: CheckStatus::Warning,
                    message: format!("{} duplicates found", dupes.len()),
                });
            }
        }
        Err(e) => {
            results.push(CheckResult {
                name: "Index".to_string(),
                status: CheckStatus::Error,
                message: format!("Failed to build: {}", e),
            });
        }
    }

    results
}

fn check_profiles(config: &AppConfig) -> Vec<CheckResult> {
    let mut results = Vec::new();

    let pm = match ProfileManager::new(config) {
        Ok(pm) => pm,
        Err(e) => {
            results.push(CheckResult {
                name: "Profiles".to_string(),
                status: CheckStatus::Error,
                message: format!("Failed to init: {}", e),
            });
            return results;
        }
    };

    let profiles_dir = &config.paths.profiles_dir;
    if !profiles_dir.exists() {
        return results;
    }

    let mut profile_count = 0;
    let mut invalid_count = 0;

    if let Ok(entries) = std::fs::read_dir(profiles_dir) {
        for entry in entries.filter_map(|e| e.ok()) {
            let path = entry.path();
            if path.extension().map_or(false, |e| e == "yaml") && path.is_file() {
                profile_count += 1;
                let name = path.file_stem().unwrap().to_string_lossy().to_string();
                if pm.load(&name).is_err() {
                    invalid_count += 1;
                }
            }
        }
    }

    if invalid_count > 0 {
        results.push(CheckResult {
            name: "Profiles".to_string(),
            status: CheckStatus::Warning,
            message: format!("{}/{} profiles valid ({} invalid)", profile_count - invalid_count, profile_count, invalid_count),
        });
    } else {
        results.push(CheckResult {
            name: "Profiles".to_string(),
            status: CheckStatus::Ok,
            message: format!("{} profiles valid", profile_count),
        });
    }

    results
}

fn check_project_symlinks(_config: &AppConfig) -> Vec<CheckResult> {
    let mut results = Vec::new();

    let cwd = match std::env::current_dir() {
        Ok(d) => d,
        Err(_) => return results,
    };

    let claude_dir = cwd.join(".claude");
    if !claude_dir.exists() {
        results.push(CheckResult {
            name: "Project config".to_string(),
            status: CheckStatus::Ok,
            message: "No per-project config (using global)".to_string(),
        });
        return results;
    }

    for subdir in ["skills", "agents", "commands", "rules"] {
        let dir = claude_dir.join(subdir);
        if !dir.exists() {
            continue;
        }

        let mut total = 0;
        let mut broken = 0;

        if let Ok(entries) = std::fs::read_dir(&dir) {
            for entry in entries.filter_map(|e| e.ok()) {
                let path = entry.path();
                if path.read_link().is_ok() {
                    total += 1;
                    // Check if target exists
                    if !path.exists() {
                        broken += 1;
                    }
                }
            }
        }

        if broken > 0 {
            results.push(CheckResult {
                name: format!("Symlinks: {}", subdir),
                status: CheckStatus::Error,
                message: format!("{}/{} broken symlinks", broken, total),
            });
        } else if total > 0 {
            results.push(CheckResult {
                name: format!("Symlinks: {}", subdir),
                status: CheckStatus::Ok,
                message: format!("{} symlinks OK", total),
            });
        }
    }

    // Check settings.local.json
    let settings_local = claude_dir.join("settings.local.json");
    if settings_local.exists() {
        match std::fs::read_to_string(&settings_local) {
            Ok(content) => match serde_json::from_str::<serde_json::Value>(&content) {
                Ok(_) => {
                    results.push(CheckResult {
                        name: "settings.local.json".to_string(),
                        status: CheckStatus::Ok,
                        message: "Valid JSON".to_string(),
                    });
                }
                Err(e) => {
                    results.push(CheckResult {
                        name: "settings.local.json".to_string(),
                        status: CheckStatus::Error,
                        message: format!("Invalid JSON: {}", e),
                    });
                }
            },
            Err(e) => {
                results.push(CheckResult {
                    name: "settings.local.json".to_string(),
                    status: CheckStatus::Error,
                    message: format!("Cannot read: {}", e),
                });
            }
        }
    }

    results
}

fn check_cli_detection(config: &AppConfig) -> Vec<CheckResult> {
    let detected = config.detected_clis();
    let total = config.cli_registry.len();

    vec![CheckResult {
        name: "Detected CLIs".to_string(),
        status: CheckStatus::Ok,
        message: format!(
            "{}/{} ({})",
            detected.len(),
            total,
            detected.iter().map(|c| c.name.as_str()).collect::<Vec<_>>().join(", ")
        ),
    }]
}

impl DoctorReport {
    pub fn print(&self) {
        println!("Health check results:\n");

        for check in &self.checks {
            let icon = match check.status {
                CheckStatus::Ok => "\x1b[32m[OK]\x1b[0m",
                CheckStatus::Warning => "\x1b[33m[WARN]\x1b[0m",
                CheckStatus::Error => "\x1b[31m[ERR]\x1b[0m",
            };
            println!("  {} {:<24} {}", icon, check.name, check.message);
        }

        let errors = self.checks.iter().filter(|c| c.status == CheckStatus::Error).count();
        let warnings = self.checks.iter().filter(|c| c.status == CheckStatus::Warning).count();

        println!();
        if errors > 0 {
            println!("  {} error(s), {} warning(s)", errors, warnings);
        } else if warnings > 0 {
            println!("  {} warning(s), no errors", warnings);
        } else {
            println!("  All checks passed.");
        }
    }
}
