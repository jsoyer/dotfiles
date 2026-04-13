use anyhow::Result;
use std::path::Path;

use crate::config::AppConfig;
use crate::profile::ProfileManager;

/// Confidence tier thresholds
pub const TIER_CRITICAL: f32 = 0.95;
pub const TIER_HIGH: f32 = 0.80;
pub const TIER_MEDIUM: f32 = 0.60;

// ── Section types ──────────────────────────────────────────────────────────

pub struct DoctorReport {
    pub sections: Vec<Section>,
}

pub struct Section {
    pub title: String,
    pub items: Vec<Item>,
}

pub struct Item {
    pub status: ItemStatus,
    pub label: String,
    pub detail: String,
}

#[derive(Debug, PartialEq, Clone, Copy)]
pub enum ItemStatus {
    Ok,
    Warning,
    Error,
}

impl ItemStatus {
    fn icon(self) -> &'static str {
        match self {
            ItemStatus::Ok => "\u{2705}",
            ItemStatus::Warning => "\u{26A0}\u{FE0F} ",
            ItemStatus::Error => "\u{274C}",
        }
    }
}

// ── Public entry point ─────────────────────────────────────────────────────

pub fn run_doctor(config: &AppConfig) -> Result<DoctorReport> {
    let home = dirs::home_dir().unwrap_or_else(|| std::path::PathBuf::from("/tmp"));

    let sections = vec![
        build_config_summary(config),
        build_cache_health(config),
        build_cli_coverage(config),
        build_symlink_health(config),
        build_config_files(config),
        build_profiles_section(config),
        build_settings_section(&home),
    ];

    Ok(DoctorReport { sections })
}

// ── Section builders ───────────────────────────────────────────────────────

fn build_config_summary(config: &AppConfig) -> Section {
    let version = env!("CARGO_PKG_VERSION");
    let config_dir = config.paths.config_dir.display().to_string();
    let cache_dir = dirs::home_dir()
        .map(|h| h.join(".aictx").display().to_string())
        .unwrap_or_else(|| "~/.aictx".to_string());

    let detected = config.detected_clis();
    let cli_list = if detected.is_empty() {
        "none".to_string()
    } else {
        detected
            .iter()
            .map(|c| {
                let dir = shorten_home(&c.config_dir.display().to_string());
                format!("{} ({})", c.name, dir)
            })
            .collect::<Vec<_>>()
            .join(", ")
    };

    Section {
        title: "Configuration".to_string(),
        items: vec![
            Item {
                status: ItemStatus::Ok,
                label: "Version".to_string(),
                detail: format!("aictx {}", version),
            },
            Item {
                status: ItemStatus::Ok,
                label: "Config".to_string(),
                detail: shorten_home(&config_dir),
            },
            Item {
                status: ItemStatus::Ok,
                label: "Cache".to_string(),
                detail: shorten_home(&cache_dir),
            },
            Item {
                status: if detected.is_empty() {
                    ItemStatus::Warning
                } else {
                    ItemStatus::Ok
                },
                label: "Detected CLIs".to_string(),
                detail: cli_list,
            },
        ],
    }
}

fn build_cache_health(config: &AppConfig) -> Section {
    let mut items = Vec::new();

    // Skills
    let skills_dir = &config.paths.skills_dir;
    let skill_count = count_entries(skills_dir);
    items.push(Item {
        status: if skill_count == 0 {
            ItemStatus::Warning
        } else {
            ItemStatus::Ok
        },
        label: "Skills".to_string(),
        detail: if skill_count == 0 {
            format!(
                "0 (empty — run 'aictx apply' to populate)  [{}]",
                shorten_home(&skills_dir.display().to_string())
            )
        } else {
            format!("{}", skill_count)
        },
    });

    // Agents
    let agents_dir = &config.paths.agents_dir;
    let agent_count = count_entries(agents_dir);
    items.push(Item {
        status: if agent_count == 0 {
            ItemStatus::Warning
        } else {
            ItemStatus::Ok
        },
        label: "Agents".to_string(),
        detail: format!("{}", agent_count),
    });

    // Commands
    let commands_dir = &config.paths.commands_dir;
    let cmd_count = count_file_entries(commands_dir);
    items.push(Item {
        status: if cmd_count == 0 {
            ItemStatus::Warning
        } else {
            ItemStatus::Ok
        },
        label: "Commands".to_string(),
        detail: format!("{}", cmd_count),
    });

    // Rules — count subdirectory names
    let rules_dir = &config.paths.rules_dir;
    let (rules_count, rules_names) = count_subdirs_with_names(rules_dir);
    items.push(Item {
        status: if rules_count == 0 {
            ItemStatus::Warning
        } else {
            ItemStatus::Ok
        },
        label: "Rules".to_string(),
        detail: if rules_count == 0 {
            "0 dirs".to_string()
        } else {
            format!("{} dirs ({})", rules_count, rules_names.join(", "))
        },
    });

    // Hooks
    let hooks_dir = &config.paths.hooks_dir;
    let hook_count = count_entries(hooks_dir);
    items.push(Item {
        status: if hook_count == 0 {
            ItemStatus::Warning
        } else {
            ItemStatus::Ok
        },
        label: "Hooks".to_string(),
        detail: if hook_count == 0 {
            "0 (empty)".to_string()
        } else {
            format!("{}", hook_count)
        },
    });

    Section {
        title: "Cache health".to_string(),
        items,
    }
}

fn build_cli_coverage(config: &AppConfig) -> Section {
    let mut items = Vec::new();

    for cli in &config.cli_registry {
        let detected = match &cli.detect {
            None => true,
            Some(_) => cli.config_dir.exists(),
        };

        if !detected {
            items.push(Item {
                status: ItemStatus::Warning,
                label: cli.name.clone(),
                detail: "not detected".to_string(),
            });
            continue;
        }

        // Count resources per supported type
        let mut parts = Vec::new();
        for resource_type in &cli.supports {
            let dir = cli.config_dir.join(resource_type);
            if dir.exists() {
                let count = count_entries(&dir);
                parts.push(format!("{} {}", count, resource_type));
            }
        }

        let total_resources: usize = cli
            .supports
            .iter()
            .map(|rt| count_entries(&cli.config_dir.join(rt)))
            .sum();

        if total_resources == 0 {
            items.push(Item {
                status: ItemStatus::Warning,
                label: cli.name.clone(),
                detail: "0 resources (run 'aictx apply' to wire)".to_string(),
            });
        } else {
            items.push(Item {
                status: ItemStatus::Ok,
                label: cli.name.clone(),
                detail: parts.join(", "),
            });
        }
    }

    Section {
        title: "CLI coverage".to_string(),
        items,
    }
}

fn build_symlink_health(config: &AppConfig) -> Section {
    let mut broken_links: Vec<String> = Vec::new();

    for cli in &config.cli_registry {
        let detected = match &cli.detect {
            None => true,
            Some(_) => cli.config_dir.exists(),
        };
        if !detected {
            continue;
        }

        for resource_type in &cli.supports {
            let dir = cli.config_dir.join(resource_type);
            if !dir.exists() {
                continue;
            }
            collect_broken_symlinks(&dir, &cli.name, resource_type, &mut broken_links);
        }
    }

    // Also check the global ~/.claude scope for all resource dirs
    let home = dirs::home_dir().unwrap_or_else(|| std::path::PathBuf::from("/tmp"));
    let global_claude = home.join(".claude");
    if global_claude.exists() {
        for subdir in ["skills", "agents", "commands", "rules", "hooks"] {
            let dir = global_claude.join(subdir);
            if dir.exists() {
                collect_broken_symlinks(&dir, "~/.claude", subdir, &mut broken_links);
            }
        }
    }

    // Dedup
    broken_links.sort();
    broken_links.dedup();

    let items = if broken_links.is_empty() {
        vec![Item {
            status: ItemStatus::Ok,
            label: "Broken symlinks".to_string(),
            detail: "none found".to_string(),
        }]
    } else {
        broken_links
            .iter()
            .map(|link| Item {
                status: ItemStatus::Error,
                label: "Broken".to_string(),
                detail: link.clone(),
            })
            .collect()
    };

    Section {
        title: "Symlink health".to_string(),
        items,
    }
}

fn build_config_files(config: &AppConfig) -> Section {
    let config_dir = &config.paths.config_dir;
    let mut items = Vec::new();

    for filename in ["defaults.yaml", "sources.yaml"] {
        let path = config_dir.join(filename);
        items.push(Item {
            status: if path.exists() {
                ItemStatus::Ok
            } else {
                ItemStatus::Warning
            },
            label: filename.to_string(),
            detail: if path.exists() {
                shorten_home(&path.display().to_string())
            } else {
                format!("not found ({})", shorten_home(&path.display().to_string()))
            },
        });
    }

    Section {
        title: "Config files".to_string(),
        items,
    }
}

fn build_profiles_section(config: &AppConfig) -> Section {
    let profiles_dir = &config.paths.profiles_dir;

    if !profiles_dir.exists() {
        return Section {
            title: "Profiles".to_string(),
            items: vec![Item {
                status: ItemStatus::Warning,
                label: "profiles/".to_string(),
                detail: "directory not found".to_string(),
            }],
        };
    }

    let pm = match ProfileManager::new(config) {
        Ok(pm) => pm,
        Err(e) => {
            return Section {
                title: "Profiles".to_string(),
                items: vec![Item {
                    status: ItemStatus::Error,
                    label: "Profiles".to_string(),
                    detail: format!("Failed to init: {}", e),
                }],
            };
        }
    };

    let mut profile_count = 0usize;
    let mut invalid_count = 0usize;

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

    let items = if profile_count == 0 {
        vec![Item {
            status: ItemStatus::Ok,
            label: "Profiles".to_string(),
            detail: "none saved".to_string(),
        }]
    } else if invalid_count > 0 {
        vec![Item {
            status: ItemStatus::Warning,
            label: "Profiles".to_string(),
            detail: format!(
                "{}/{} valid ({} invalid)",
                profile_count - invalid_count,
                profile_count,
                invalid_count
            ),
        }]
    } else {
        vec![Item {
            status: ItemStatus::Ok,
            label: "Profiles".to_string(),
            detail: format!("{} valid", profile_count),
        }]
    };

    Section {
        title: "Profiles".to_string(),
        items,
    }
}

fn build_settings_section(home: &Path) -> Section {
    let mut items = Vec::new();

    let global_claude = home.join(".claude");

    // Check settings JSON validity
    for filename in ["settings.json", "settings.local.json"] {
        let path = global_claude.join(filename);
        if !path.exists() {
            continue;
        }
        match std::fs::read_to_string(&path) {
            Ok(content) => match serde_json::from_str::<serde_json::Value>(&content) {
                Ok(_) => items.push(Item {
                    status: ItemStatus::Ok,
                    label: filename.to_string(),
                    detail: "valid JSON".to_string(),
                }),
                Err(e) => items.push(Item {
                    status: ItemStatus::Error,
                    label: filename.to_string(),
                    detail: format!("invalid JSON: {}", e),
                }),
            },
            Err(e) => items.push(Item {
                status: ItemStatus::Error,
                label: filename.to_string(),
                detail: format!("cannot read: {}", e),
            }),
        }
    }

    // Warn if both coexist
    let local = global_claude.join("settings.local.json");
    let main = global_claude.join("settings.json");
    if local.exists() && main.exists() {
        items.push(Item {
            status: ItemStatus::Warning,
            label: "settings overlap".to_string(),
            detail: "both settings.json and settings.local.json exist — consider merging"
                .to_string(),
        });
    }

    if items.is_empty() {
        items.push(Item {
            status: ItemStatus::Warning,
            label: "settings.json".to_string(),
            detail: "not found in ~/.claude/".to_string(),
        });
    }

    Section {
        title: "Settings files".to_string(),
        items,
    }
}

// ── Helpers ────────────────────────────────────────────────────────────────

/// Count direct children (files + symlinks + dirs) in a directory.
fn count_entries(dir: &Path) -> usize {
    if !dir.exists() {
        return 0;
    }
    std::fs::read_dir(dir)
        .map(|entries| entries.filter_map(|e| e.ok()).count())
        .unwrap_or(0)
}

/// Count only regular files (not dirs) directly inside a directory.
fn count_file_entries(dir: &Path) -> usize {
    if !dir.exists() {
        return 0;
    }
    std::fs::read_dir(dir)
        .map(|entries| {
            entries
                .filter_map(|e| e.ok())
                .filter(|e| e.path().is_file())
                .count()
        })
        .unwrap_or(0)
}

/// Return (count, names) of immediate subdirectories.
fn count_subdirs_with_names(dir: &Path) -> (usize, Vec<String>) {
    if !dir.exists() {
        return (0, Vec::new());
    }
    let mut names: Vec<String> = std::fs::read_dir(dir)
        .map(|entries| {
            entries
                .filter_map(|e| e.ok())
                .filter(|e| e.path().is_dir())
                .filter_map(|e| {
                    e.path()
                        .file_name()
                        .map(|n| n.to_string_lossy().to_string())
                })
                .collect()
        })
        .unwrap_or_default();
    names.sort();
    let count = names.len();
    (count, names)
}

/// Collect broken symlinks in `dir` and append formatted entries to `out`.
fn collect_broken_symlinks(dir: &Path, cli_name: &str, resource_type: &str, out: &mut Vec<String>) {
    let Ok(entries) = std::fs::read_dir(dir) else {
        return;
    };
    for entry in entries.filter_map(|e| e.ok()) {
        let path = entry.path();
        if path.read_link().is_ok() && !path.exists() {
            let target = path
                .read_link()
                .map(|t| t.display().to_string())
                .unwrap_or_else(|_| "?".to_string());
            let name = path
                .file_name()
                .map(|n| n.to_string_lossy().to_string())
                .unwrap_or_else(|| path.display().to_string());
            out.push(format!(
                "{}/{}/{} -> {} (target missing)",
                cli_name, resource_type, name, target
            ));
        }
    }
}

/// Replace the home directory prefix with `~` for compact display.
fn shorten_home(path: &str) -> String {
    let home = dirs::home_dir()
        .map(|h| h.display().to_string())
        .unwrap_or_default();
    if !home.is_empty() && path.starts_with(&home) {
        format!("~{}", &path[home.len()..])
    } else {
        path.to_string()
    }
}

// ── Display ────────────────────────────────────────────────────────────────

impl DoctorReport {
    pub fn print(&self) {
        println!("\u{1F50D} aictx doctor\n");

        let mut total_errors = 0usize;
        let mut total_warnings = 0usize;

        for section in &self.sections {
            let section_icon = match section.title.as_str() {
                "Configuration" => "\u{1F4CB}",
                "Cache health" => "\u{1F4E6}",
                "CLI coverage" => "\u{1F517}",
                "Symlink health" => "\u{1F50D}",
                "Config files" => "\u{1F4C4}",
                "Profiles" => "\u{1F4C1}",
                "Settings files" => "\u{2699}\u{FE0F} ",
                _ => "\u{1F538}",
            };
            println!("{} {}", section_icon, section.title);

            for item in &section.items {
                match item.status {
                    ItemStatus::Error => total_errors += 1,
                    ItemStatus::Warning => total_warnings += 1,
                    ItemStatus::Ok => {}
                }
                println!("  {} {}: {}", item.status.icon(), item.label, item.detail);
            }
            println!();
        }

        // Summary footer
        if total_errors > 0 {
            println!(
                "\u{274C} {} error(s), {} warning(s)",
                total_errors, total_warnings
            );
        } else if total_warnings > 0 {
            println!("\u{26A0}\u{FE0F}  {} warning(s), no errors", total_warnings);
        } else {
            println!("\u{2705} All checks passed.");
        }
    }
}

// ── Tests ──────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;
    use std::path::PathBuf;

    /// Create a unique temporary directory using only stdlib (no tempfile crate needed).
    fn make_tmp(tag: &str) -> PathBuf {
        use std::time::{SystemTime, UNIX_EPOCH};
        let nanos = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .map(|d| d.subsec_nanos())
            .unwrap_or(0);
        let dir = std::env::temp_dir().join(format!("aictx-test-{}-{}", tag, nanos));
        fs::create_dir_all(&dir).unwrap();
        dir
    }

    fn make_temp_config(base: &Path) -> AppConfig {
        use crate::config::{AiConfig, BaseConfig, CliEntry, PathsConfig};

        AppConfig {
            base: BaseConfig {
                skills: vec![],
                agents: vec![],
                commands: vec![],
                mcp: vec![],
                rules: vec![],
                plugins: vec![],
            },
            ai: AiConfig {
                enabled: false,
                provider: "ollama".to_string(),
                model: "qwen3:8b".to_string(),
                fallback: None,
                max_tokens: 500,
                cache_ttl: "7d".to_string(),
            },
            paths: PathsConfig {
                skills_dir: base.join("skills"),
                agents_dir: base.join("agents"),
                commands_dir: base.join("commands"),
                hooks_dir: base.join("hooks"),
                rules_dir: base.join("rules"),
                config_dir: base.join("config"),
                profiles_dir: base.join("config").join("profiles"),
            },
            cli_registry: vec![CliEntry {
                name: "testcli".to_string(),
                config_dir: base.join("testcli"),
                project_dir: ".testcli".to_string(),
                supports: vec!["skills".to_string()],
                scopes: vec!["global".to_string()],
                detect: None,
            }],
        }
    }

    #[test]
    fn count_entries_returns_zero_for_missing_dir() {
        assert_eq!(count_entries(&PathBuf::from("/nonexistent/path/xyz")), 0);
    }

    #[test]
    fn count_entries_counts_all_children() {
        let tmp = make_tmp("count-entries");
        fs::write(tmp.join("a.md"), "").unwrap();
        fs::write(tmp.join("b.md"), "").unwrap();
        fs::create_dir(tmp.join("subdir")).unwrap();
        assert_eq!(count_entries(&tmp), 3);
    }

    #[test]
    fn count_file_entries_skips_directories() {
        let tmp = make_tmp("count-file-entries");
        fs::write(tmp.join("a.md"), "").unwrap();
        fs::create_dir(tmp.join("subdir")).unwrap();
        assert_eq!(count_file_entries(&tmp), 1);
    }

    #[test]
    fn count_subdirs_with_names_returns_sorted_names() {
        let tmp = make_tmp("count-subdirs");
        fs::create_dir(tmp.join("rust")).unwrap();
        fs::create_dir(tmp.join("common")).unwrap();
        fs::write(tmp.join("ignored.yaml"), "").unwrap();
        let (count, names) = count_subdirs_with_names(&tmp);
        assert_eq!(count, 2);
        assert_eq!(names, vec!["common", "rust"]);
    }

    #[test]
    fn shorten_home_replaces_prefix() {
        let home = dirs::home_dir().unwrap();
        let path = home.join(".config").join("aictx").display().to_string();
        let short = shorten_home(&path);
        assert!(short.starts_with('~'), "expected ~ prefix, got: {}", short);
    }

    #[test]
    fn shorten_home_leaves_non_home_paths_unchanged() {
        let path = "/etc/hosts";
        assert_eq!(shorten_home(path), path);
    }

    #[test]
    fn collect_broken_symlinks_detects_dangling_link() {
        let tmp = make_tmp("broken-symlinks");
        let link = tmp.join("broken_link");
        let _ = std::os::unix::fs::symlink("/nonexistent/target/file", &link);

        let mut out = Vec::new();
        collect_broken_symlinks(&tmp, "testcli", "skills", &mut out);
        assert_eq!(out.len(), 1);
        assert!(out[0].contains("broken_link"));
        assert!(out[0].contains("target missing"));
    }

    #[test]
    fn collect_broken_symlinks_ignores_valid_symlinks() {
        let tmp = make_tmp("good-symlinks");
        let real_file = tmp.join("real.md");
        fs::write(&real_file, "content").unwrap();
        let link = tmp.join("good_link");
        let _ = std::os::unix::fs::symlink(&real_file, &link);

        let mut out = Vec::new();
        collect_broken_symlinks(&tmp, "testcli", "skills", &mut out);
        assert!(out.is_empty());
    }

    #[test]
    fn run_doctor_returns_expected_sections() {
        let tmp = make_tmp("run-doctor");
        let config = make_temp_config(&tmp);

        let report = run_doctor(&config).unwrap();
        let titles: Vec<&str> = report.sections.iter().map(|s| s.title.as_str()).collect();

        assert!(titles.contains(&"Configuration"));
        assert!(titles.contains(&"Cache health"));
        assert!(titles.contains(&"CLI coverage"));
        assert!(titles.contains(&"Symlink health"));
        assert!(titles.contains(&"Config files"));
    }

    #[test]
    fn cache_health_warns_on_empty_skills_dir() {
        let tmp = make_tmp("cache-warn");
        let config = make_temp_config(&tmp);
        // skills_dir does not exist yet

        let section = build_cache_health(&config);
        let skills_item = section.items.iter().find(|i| i.label == "Skills").unwrap();
        assert_eq!(skills_item.status, ItemStatus::Warning);
    }

    #[test]
    fn cache_health_ok_when_skills_present() {
        let tmp = make_tmp("cache-ok");
        let config = make_temp_config(&tmp);
        fs::create_dir_all(&config.paths.skills_dir).unwrap();
        fs::write(config.paths.skills_dir.join("git-commit"), "").unwrap();

        let section = build_cache_health(&config);
        let skills_item = section.items.iter().find(|i| i.label == "Skills").unwrap();
        assert_eq!(skills_item.status, ItemStatus::Ok);
    }

    #[test]
    fn cli_coverage_warns_when_no_resources() {
        let tmp = make_tmp("cli-warn");
        let config = make_temp_config(&tmp);
        // testcli config dir exists but skills subdir does not
        fs::create_dir_all(&config.cli_registry[0].config_dir).unwrap();

        let section = build_cli_coverage(&config);
        let item = &section.items[0];
        assert_eq!(item.status, ItemStatus::Warning);
        assert!(item.detail.contains("aictx apply"));
    }

    #[test]
    fn cli_coverage_ok_when_resources_present() {
        let tmp = make_tmp("cli-ok");
        let config = make_temp_config(&tmp);
        let cli_skills = config.cli_registry[0].config_dir.join("skills");
        fs::create_dir_all(&cli_skills).unwrap();
        fs::write(cli_skills.join("git-commit"), "").unwrap();

        let section = build_cli_coverage(&config);
        let item = &section.items[0];
        assert_eq!(item.status, ItemStatus::Ok);
    }

    #[test]
    fn config_files_warns_when_missing() {
        let tmp = make_tmp("cfgfiles-warn");
        let config = make_temp_config(&tmp);
        // config_dir does not exist

        let section = build_config_files(&config);
        for item in &section.items {
            assert_eq!(item.status, ItemStatus::Warning);
        }
    }

    #[test]
    fn config_files_ok_when_present() {
        let tmp = make_tmp("cfgfiles-ok");
        let config = make_temp_config(&tmp);
        fs::create_dir_all(&config.paths.config_dir).unwrap();
        fs::write(config.paths.config_dir.join("defaults.yaml"), "").unwrap();
        fs::write(config.paths.config_dir.join("sources.yaml"), "").unwrap();

        let section = build_config_files(&config);
        for item in &section.items {
            assert_eq!(item.status, ItemStatus::Ok);
        }
    }

    #[test]
    fn item_status_icons_are_distinct() {
        assert_ne!(ItemStatus::Ok.icon(), ItemStatus::Warning.icon());
        assert_ne!(ItemStatus::Ok.icon(), ItemStatus::Error.icon());
        assert_ne!(ItemStatus::Warning.icon(), ItemStatus::Error.icon());
    }
}
