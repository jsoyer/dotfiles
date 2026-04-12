use anyhow::{Context, Result};
use std::path::{Path, PathBuf};

use crate::config::AppConfig;
use crate::matcher::Recommendations;
use crate::scope::{scope_str, ResolvedScope, Scope};

#[derive(Debug)]
pub struct ApplyPreview {
    pub actions: Vec<PreviewAction>,
    pub scope: Scope,
}

#[derive(Debug)]
pub struct PreviewAction {
    pub cli_name: String,
    pub resource_type: String,
    pub count: usize,
    #[allow(dead_code)]
    pub target_dir: PathBuf,
}

#[derive(Debug)]
pub struct ProjectStatus {
    pub skills: Vec<String>,
    pub agents: Vec<String>,
    pub commands: Vec<String>,
    pub hooks: Vec<String>,
    pub rules: Vec<String>,
    pub mcp: Vec<String>,
    pub plugins: Vec<String>,
    pub detected_clis: Vec<String>,
    pub scope: Scope,
}

/// Resolve the CLI target directory based on scope.
/// - Global: cli.config_dir (e.g., ~/.claude/)
/// - Project: <project_root>/<cli.project_dir> (e.g., ./myproject/.claude/)
/// - UserProject: resolved.target_dir (e.g., ~/.claude/projects/<hash>/)
fn cli_target_dir(cli: &crate::config::CliEntry, resolved: &ResolvedScope) -> PathBuf {
    match resolved.scope {
        Scope::Global => cli.config_dir.clone(),
        Scope::Project => resolved.target_dir.join(&cli.project_dir),
        Scope::UserProject => resolved.target_dir.clone(),
    }
}

pub fn preview(
    config: &AppConfig,
    resolved: &ResolvedScope,
    selections: &Recommendations,
) -> Result<ApplyPreview> {
    let mut actions = Vec::new();
    let scope_s = scope_str(resolved.scope);

    for cli in config.detected_clis() {
        if !cli.scopes.contains(&scope_s.to_string()) {
            continue;
        }

        let target = cli_target_dir(cli, resolved);

        if resolved.supports_symlinks {
            if cli.supports.contains(&"skills".to_string()) && !selections.skills.is_empty() {
                actions.push(PreviewAction {
                    cli_name: cli.name.clone(),
                    resource_type: "skills".to_string(),
                    count: selections.skills.len(),
                    target_dir: target.join("skills"),
                });
            }

            if cli.supports.contains(&"agents".to_string()) && !selections.agents.is_empty() {
                actions.push(PreviewAction {
                    cli_name: cli.name.clone(),
                    resource_type: "agents".to_string(),
                    count: selections.agents.len(),
                    target_dir: target.join("agents"),
                });
            }

            if cli.supports.contains(&"commands".to_string()) && !selections.commands.is_empty() {
                actions.push(PreviewAction {
                    cli_name: cli.name.clone(),
                    resource_type: "commands".to_string(),
                    count: selections.commands.len(),
                    target_dir: target.join("commands"),
                });
            }

            if cli.supports.contains(&"rules".to_string()) && !selections.rules.is_empty() {
                actions.push(PreviewAction {
                    cli_name: cli.name.clone(),
                    resource_type: "rules".to_string(),
                    count: selections.rules.len(),
                    target_dir: target.join("rules"),
                });
            }
        }

        if cli.supports.contains(&"mcp".to_string()) && !selections.mcp.is_empty() {
            actions.push(PreviewAction {
                cli_name: cli.name.clone(),
                resource_type: "mcp".to_string(),
                count: selections.mcp.len(),
                target_dir: target.clone(),
            });
        }

        if cli.supports.contains(&"plugins".to_string()) && !selections.plugins.is_empty() {
            actions.push(PreviewAction {
                cli_name: cli.name.clone(),
                resource_type: "plugins".to_string(),
                count: selections.plugins.len(),
                target_dir: target,
            });
        }
    }

    Ok(ApplyPreview {
        actions,
        scope: resolved.scope,
    })
}

/// Check if a directory looks like a project
pub fn is_project_dir(dir: &Path) -> bool {
    let signals = [
        ".git",
        "CLAUDE.md",
        ".claude",
        "package.json",
        "Cargo.toml",
        "go.mod",
        "pyproject.toml",
        "setup.py",
        "Gemfile",
        "composer.json",
        "pom.xml",
        "build.gradle",
        "CMakeLists.txt",
        "Makefile",
        "flake.nix",
        "mix.exs",
        "pubspec.yaml",
    ];
    signals.iter().any(|s| dir.join(s).exists())
}

pub fn apply(
    config: &AppConfig,
    resolved: &ResolvedScope,
    selections: &Recommendations,
) -> Result<()> {
    let scope_s = scope_str(resolved.scope);

    println!("Applying configuration (scope: {})...", resolved.scope);

    for cli in config.detected_clis() {
        if !cli.scopes.contains(&scope_s.to_string()) {
            continue;
        }

        let target = cli_target_dir(cli, resolved);

        // Symlink-based resources (only for scopes that support it)
        if resolved.supports_symlinks {
            if cli.supports.contains(&"skills".to_string()) {
                let skills_target = target.join("skills");
                // Skip if target == source (global mode: avoid self-symlinks)
                if skills_target != config.paths.skills_dir {
                    create_symlinks(
                        &skills_target,
                        &config.paths.skills_dir,
                        &selections.skill_names(),
                        true,
                    )?;
                }
            }

            if cli.supports.contains(&"agents".to_string()) {
                let agents_target = target.join("agents");
                if agents_target != config.paths.agents_dir {
                    create_symlinks(
                        &agents_target,
                        &config.paths.agents_dir,
                        &selections.agent_names(),
                        false,
                    )?;
                }
            }

            if cli.supports.contains(&"commands".to_string()) {
                let commands_target = target.join("commands");
                if commands_target != config.paths.commands_dir {
                    create_symlinks(
                        &commands_target,
                        &config.paths.commands_dir,
                        &selections.command_names(),
                        false,
                    )?;
                }
            }

            if cli.supports.contains(&"hooks".to_string()) {
                let hooks_target = target.join("hooks");
                if hooks_target != config.paths.hooks_dir {
                    create_symlinks(
                        &hooks_target,
                        &config.paths.hooks_dir,
                        &selections.hook_names(),
                        false,
                    )?;
                }
            }

            if cli.supports.contains(&"rules".to_string()) {
                for lang in &selections.rules {
                    let rule_name = match lang.as_str() {
                        "go" => "golang",
                        other => other,
                    };
                    let source = config.paths.rules_dir.join(rule_name);
                    if source.exists() {
                        let rule_target = target.join("rules").join(rule_name);
                        std::fs::create_dir_all(rule_target.parent().unwrap())?;
                        symlink_dir(&source, &rule_target)?;
                    }
                }
                // Always include common rules
                let common_source = config.paths.rules_dir.join("common");
                if common_source.exists() {
                    let common_target = target.join("rules").join("common");
                    std::fs::create_dir_all(common_target.parent().unwrap())?;
                    symlink_dir(&common_source, &common_target)?;
                }
            }
        }

        // Settings-based resources (MCP, plugins) — all scopes
        if cli.supports.contains(&"mcp".to_string())
            || cli.supports.contains(&"plugins".to_string())
        {
            let settings_path = settings_path_for_scope(&target, resolved.scope);
            merge_settings_file(&settings_path, &selections.mcp, &selections.plugins)?;
        }
    }

    Ok(())
}

pub fn reset(config: &AppConfig, resolved: &ResolvedScope) -> Result<()> {
    let scope_s = scope_str(resolved.scope);

    for cli in &config.cli_registry {
        if !cli.scopes.contains(&scope_s.to_string()) {
            continue;
        }

        let target = cli_target_dir(cli, resolved);

        if resolved.supports_symlinks {
            for subdir in ["skills", "agents", "commands", "hooks", "rules"] {
                let dir = target.join(subdir);
                if dir.exists() {
                    // Only remove symlinks, not real files
                    if let Ok(entries) = std::fs::read_dir(&dir) {
                        for entry in entries.filter_map(|e| e.ok()) {
                            let path = entry.path();
                            if path.read_link().is_ok() {
                                std::fs::remove_file(&path)?;
                            }
                        }
                    }
                    // Remove dir if empty
                    if dir
                        .read_dir()
                        .map(|mut d| d.next().is_none())
                        .unwrap_or(true)
                    {
                        let _ = std::fs::remove_dir(&dir);
                    }
                }
            }
        }

        // Remove settings file (settings.local.json for backward compat, settings.json for user-project)
        let settings_local = target.join("settings.local.json");
        if settings_local.exists() {
            std::fs::remove_file(&settings_local)?;
        }

        // For user-project scope, also clean the settings.json managed keys
        if resolved.scope == Scope::UserProject {
            let settings = target.join("settings.json");
            if settings.exists() {
                remove_cctx_keys_from_settings(&settings)?;
            }
        }
    }

    Ok(())
}

pub fn status(config: &AppConfig, resolved: &ResolvedScope) -> Result<ProjectStatus> {
    let scope_s = scope_str(resolved.scope);

    // Find the claude CLI entry to read status from
    let claude_cli = config.cli_registry.iter().find(|c| c.name == "claude");

    let target = match claude_cli {
        Some(cli) if cli.scopes.contains(&scope_s.to_string()) => cli_target_dir(cli, resolved),
        _ => resolved.target_dir.clone(),
    };

    let (skills, agents, commands, hooks, rules) = if resolved.supports_symlinks {
        (
            list_symlinks(&target.join("skills")),
            list_symlinks(&target.join("agents")),
            list_symlinks(&target.join("commands")),
            list_symlinks_with_ext(&target.join("hooks"), "sh"),
            list_symlinks(&target.join("rules")),
        )
    } else {
        (Vec::new(), Vec::new(), Vec::new(), Vec::new(), Vec::new())
    };

    let (mcp, plugins) = read_settings(&target, resolved.scope);

    let detected_clis: Vec<String> = config
        .detected_clis()
        .iter()
        .filter(|c| c.scopes.contains(&scope_s.to_string()))
        .map(|c| c.name.clone())
        .collect();

    Ok(ProjectStatus {
        skills,
        agents,
        commands,
        hooks,
        rules,
        mcp,
        plugins,
        detected_clis,
        scope: resolved.scope,
    })
}

/// Get status for a specific CLI entry (what's active in its directory).
pub fn status_for_cli(cli: &crate::config::CliEntry, resolved: &ResolvedScope) -> ProjectStatus {
    let scope_s = scope_str(resolved.scope);

    if !cli.scopes.contains(&scope_s.to_string()) {
        return ProjectStatus {
            skills: Vec::new(),
            agents: Vec::new(),
            commands: Vec::new(),
            hooks: Vec::new(),
            rules: Vec::new(),
            mcp: Vec::new(),
            plugins: Vec::new(),
            detected_clis: vec![cli.name.clone()],
            scope: resolved.scope,
        };
    }

    let target = cli_target_dir(cli, resolved);

    let skills = if cli.supports.contains(&"skills".to_string()) {
        list_symlinks(&target.join("skills"))
    } else {
        Vec::new()
    };
    let agents = if cli.supports.contains(&"agents".to_string()) {
        list_symlinks(&target.join("agents"))
    } else {
        Vec::new()
    };
    let commands = if cli.supports.contains(&"commands".to_string()) {
        list_symlinks(&target.join("commands"))
    } else {
        Vec::new()
    };
    let hooks = if cli.supports.contains(&"hooks".to_string()) {
        list_symlinks_with_ext(&target.join("hooks"), "sh")
    } else {
        Vec::new()
    };
    let rules = if cli.supports.contains(&"rules".to_string()) {
        list_symlinks(&target.join("rules"))
    } else {
        Vec::new()
    };

    let (mcp, plugins) = if cli.supports.contains(&"mcp".to_string())
        || cli.supports.contains(&"plugins".to_string())
    {
        read_settings(&target, resolved.scope)
    } else {
        (Vec::new(), Vec::new())
    };

    ProjectStatus {
        skills,
        agents,
        commands,
        hooks,
        rules,
        mcp,
        plugins,
        detected_clis: vec![cli.name.clone()],
        scope: resolved.scope,
    }
}

fn create_symlinks(
    target_dir: &Path,
    source_dir: &Path,
    names: &[String],
    are_dirs: bool,
) -> Result<()> {
    std::fs::create_dir_all(target_dir)
        .with_context(|| format!("Failed to create {}", target_dir.display()))?;

    // Clean existing symlinks
    if let Ok(entries) = std::fs::read_dir(target_dir) {
        for entry in entries.filter_map(|e| e.ok()) {
            if entry.path().read_link().is_ok() {
                std::fs::remove_file(entry.path())?;
            }
        }
    }

    for name in names {
        let source = if are_dirs {
            source_dir.join(name)
        } else {
            let with_ext = source_dir.join(format!("{}.md", name));
            if with_ext.exists() {
                with_ext
            } else {
                source_dir.join(name)
            }
        };

        if source.exists() {
            let target = if are_dirs {
                target_dir.join(name)
            } else {
                let filename = source.file_name().unwrap();
                target_dir.join(filename)
            };

            #[cfg(unix)]
            std::os::unix::fs::symlink(&source, &target).with_context(|| {
                format!(
                    "Failed to symlink {} -> {}",
                    source.display(),
                    target.display()
                )
            })?;

            #[cfg(windows)]
            {
                if source.is_dir() {
                    std::os::windows::fs::symlink_dir(&source, &target)?;
                } else {
                    std::os::windows::fs::symlink_file(&source, &target)?;
                }
            }
        }
    }

    Ok(())
}

fn symlink_dir(source: &Path, target: &Path) -> Result<()> {
    if target.exists() || target.read_link().is_ok() {
        std::fs::remove_file(target).or_else(|_| std::fs::remove_dir_all(target))?;
    }

    #[cfg(unix)]
    std::os::unix::fs::symlink(source, target)?;

    #[cfg(windows)]
    std::os::windows::fs::symlink_dir(source, target)?;

    Ok(())
}

/// Determine the settings file path based on scope.
fn settings_path_for_scope(cli_dir: &Path, scope: Scope) -> PathBuf {
    match scope {
        // For global and project, use settings.local.json (backward compatible, doesn't
        // overwrite user's settings.json)
        Scope::Global | Scope::Project => cli_dir.join("settings.local.json"),
        // For user-project, we write directly to settings.json
        // (this is the Claude Code user-project dir, aictx manages it)
        Scope::UserProject => cli_dir.join("settings.json"),
    }
}

/// Merge MCP and plugin settings into a settings file (atomic write).
fn merge_settings_file(path: &Path, extra_mcp: &[String], plugins: &[String]) -> Result<()> {
    if extra_mcp.is_empty() && plugins.is_empty() {
        return Ok(());
    }

    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent)?;
    }

    // Read existing settings if any
    let mut settings: serde_json::Map<String, serde_json::Value> = if path.exists() {
        let content = std::fs::read_to_string(path)?;
        serde_json::from_str(&content).unwrap_or_default()
    } else {
        serde_json::Map::new()
    };

    // Merge plugins
    if !plugins.is_empty() {
        let mut enabled = serde_json::Map::new();
        for plugin in plugins {
            enabled.insert(plugin.clone(), serde_json::Value::Bool(true));
        }
        settings.insert(
            "enabledPlugins".to_string(),
            serde_json::Value::Object(enabled),
        );
    }

    // Atomic write via temp file
    let json = serde_json::to_string_pretty(&settings)?;
    let tmp_path = path.with_extension("json.tmp");
    std::fs::write(&tmp_path, &json)?;
    std::fs::rename(&tmp_path, path)?;

    Ok(())
}

/// Remove aictx-managed keys from a settings.json without touching other keys.
fn remove_cctx_keys_from_settings(path: &Path) -> Result<()> {
    let content = std::fs::read_to_string(path)?;
    let mut settings: serde_json::Map<String, serde_json::Value> =
        serde_json::from_str(&content).unwrap_or_default();

    settings.remove("enabledPlugins");

    if settings.is_empty() {
        std::fs::remove_file(path)?;
    } else {
        let json = serde_json::to_string_pretty(&settings)?;
        std::fs::write(path, json)?;
    }

    Ok(())
}

fn list_symlinks(dir: &Path) -> Vec<String> {
    if !dir.exists() {
        return Vec::new();
    }

    std::fs::read_dir(dir)
        .ok()
        .map(|entries| {
            entries
                .filter_map(|e| e.ok())
                .filter(|e| e.path().read_link().is_ok())
                .map(|e| {
                    e.path()
                        .file_stem()
                        .unwrap_or_default()
                        .to_string_lossy()
                        .to_string()
                })
                .collect()
        })
        .unwrap_or_default()
}

/// List symlinks in a directory that have the given file extension.
/// Returns the file stem (name without extension) for each match.
fn list_symlinks_with_ext(dir: &Path, ext: &str) -> Vec<String> {
    if !dir.exists() {
        return Vec::new();
    }

    std::fs::read_dir(dir)
        .ok()
        .map(|entries| {
            entries
                .filter_map(|e| e.ok())
                .filter(|e| {
                    e.path().read_link().is_ok()
                        && e.path()
                            .extension()
                            .map_or(false, |x| x == ext)
                })
                .map(|e| {
                    e.path()
                        .file_stem()
                        .unwrap_or_default()
                        .to_string_lossy()
                        .to_string()
                })
                .collect()
        })
        .unwrap_or_default()
}

/// Read settings from the appropriate file for the given scope.
fn read_settings(cli_dir: &Path, scope: Scope) -> (Vec<String>, Vec<String>) {
    let path = settings_path_for_scope(cli_dir, scope);
    if !path.exists() {
        // Fallback: try the other filename for backward compat
        let fallback = match scope {
            Scope::Global | Scope::Project => cli_dir.join("settings.json"),
            Scope::UserProject => cli_dir.join("settings.local.json"),
        };
        if fallback.exists() {
            return read_settings_from_file(&fallback);
        }
        return (Vec::new(), Vec::new());
    }

    read_settings_from_file(&path)
}

fn read_settings_from_file(path: &Path) -> (Vec<String>, Vec<String>) {
    let content = std::fs::read_to_string(path).unwrap_or_default();
    let json: serde_json::Value = serde_json::from_str(&content).unwrap_or_default();

    let plugins = json
        .get("enabledPlugins")
        .and_then(|v| v.as_object())
        .map(|obj| {
            obj.iter()
                .filter(|(_, v)| v.as_bool().unwrap_or(false))
                .map(|(k, _)| k.clone())
                .collect()
        })
        .unwrap_or_default();

    (Vec::new(), plugins)
}

/// Set all plugins to enabled or disabled in a settings file.
pub fn set_all_plugins_enabled(path: &Path, enabled: bool) -> Result<()> {
    if !path.exists() {
        return Ok(());
    }
    let content = std::fs::read_to_string(path)?;
    let mut settings: serde_json::Map<String, serde_json::Value> =
        serde_json::from_str(&content).unwrap_or_default();

    if let Some(serde_json::Value::Object(plugins)) = settings.get_mut("enabledPlugins") {
        for value in plugins.values_mut() {
            *value = serde_json::Value::Bool(enabled);
        }
    }

    let json = serde_json::to_string_pretty(&settings)?;
    let tmp = path.with_extension("json.tmp");
    std::fs::write(&tmp, &json)?;
    std::fs::rename(&tmp, path)?;
    Ok(())
}

impl ApplyPreview {
    pub fn print(&self) {
        println!("Will create (scope: {}):", self.scope);
        for action in &self.actions {
            println!(
                "  {}/{:<12} {} {}",
                action.cli_name,
                action.resource_type,
                action.count,
                if action.resource_type == "mcp" || action.resource_type == "plugins" {
                    "entries in settings"
                } else {
                    "symlinks"
                }
            );
        }
    }
}

impl ProjectStatus {
    pub fn empty(scope: Scope) -> Self {
        ProjectStatus {
            skills: Vec::new(),
            agents: Vec::new(),
            commands: Vec::new(),
            hooks: Vec::new(),
            rules: Vec::new(),
            mcp: Vec::new(),
            plugins: Vec::new(),
            detected_clis: Vec::new(),
            scope,
        }
    }

    pub fn print(&self) {
        println!("Status (scope: {}):", self.scope);
        println!("  Skills:   {}", self.skills.len());
        println!("  Agents:   {}", self.agents.len());
        println!("  Commands: {}", self.commands.len());
        println!("  Hooks:    {}", self.hooks.len());
        println!("  Rules:    {}", self.rules.len());
        println!("  MCP:      {}", self.mcp.len());
        println!("  Plugins:  {}", self.plugins.len());
        println!("  CLIs:     {}", self.detected_clis.join(", "));

        if !self.skills.is_empty() {
            println!("\n  Active skills: {}", self.skills.join(", "));
        }
        if !self.agents.is_empty() {
            println!("  Active agents: {}", self.agents.join(", "));
        }
    }
}
