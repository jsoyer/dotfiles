use anyhow::{Context, Result};
use std::path::{Path, PathBuf};

use crate::config::AppConfig;
use crate::matcher::Recommendations;

#[derive(Debug)]
pub struct ApplyPreview {
    pub actions: Vec<PreviewAction>,
}

#[derive(Debug)]
pub struct PreviewAction {
    pub cli_name: String,
    pub resource_type: String,
    pub count: usize,
    pub target_dir: PathBuf,
}

#[derive(Debug)]
pub struct ProjectStatus {
    pub skills: Vec<String>,
    pub agents: Vec<String>,
    pub commands: Vec<String>,
    pub rules: Vec<String>,
    pub mcp: Vec<String>,
    pub plugins: Vec<String>,
    pub detected_clis: Vec<String>,
}

pub fn preview(
    config: &AppConfig,
    project_dir: &Path,
    selections: &Recommendations,
) -> Result<ApplyPreview> {
    let mut actions = Vec::new();

    for cli in config.detected_clis() {
        let cli_project_dir = project_dir.join(&cli.project_dir);

        if cli.supports.contains(&"skills".to_string()) {
            actions.push(PreviewAction {
                cli_name: cli.name.clone(),
                resource_type: "skills".to_string(),
                count: selections.skills.len(),
                target_dir: cli_project_dir.join("skills"),
            });
        }

        if cli.supports.contains(&"agents".to_string()) {
            actions.push(PreviewAction {
                cli_name: cli.name.clone(),
                resource_type: "agents".to_string(),
                count: selections.agents.len(),
                target_dir: cli_project_dir.join("agents"),
            });
        }

        if cli.supports.contains(&"commands".to_string()) {
            actions.push(PreviewAction {
                cli_name: cli.name.clone(),
                resource_type: "commands".to_string(),
                count: selections.commands.len(),
                target_dir: cli_project_dir.join("commands"),
            });
        }

        if cli.supports.contains(&"rules".to_string()) && !selections.rules.is_empty() {
            actions.push(PreviewAction {
                cli_name: cli.name.clone(),
                resource_type: "rules".to_string(),
                count: selections.rules.len(),
                target_dir: cli_project_dir.join("rules"),
            });
        }

        if cli.supports.contains(&"mcp".to_string()) && !selections.mcp.is_empty() {
            actions.push(PreviewAction {
                cli_name: cli.name.clone(),
                resource_type: "mcp".to_string(),
                count: selections.mcp.len(),
                target_dir: cli_project_dir.clone(),
            });
        }

        if cli.supports.contains(&"plugins".to_string()) && !selections.plugins.is_empty() {
            actions.push(PreviewAction {
                cli_name: cli.name.clone(),
                resource_type: "plugins".to_string(),
                count: selections.plugins.len(),
                target_dir: cli_project_dir,
            });
        }
    }

    Ok(ApplyPreview { actions })
}

pub fn apply(
    config: &AppConfig,
    project_dir: &Path,
    selections: &Recommendations,
) -> Result<()> {
    for cli in config.detected_clis() {
        let cli_project_dir = project_dir.join(&cli.project_dir);

        if cli.supports.contains(&"skills".to_string()) {
            create_symlinks(
                &cli_project_dir.join("skills"),
                &config.paths.skills_dir,
                &selections.skill_names(),
                true, // skills are directories
            )?;
        }

        if cli.supports.contains(&"agents".to_string()) {
            create_symlinks(
                &cli_project_dir.join("agents"),
                &config.paths.agents_dir,
                &selections.agent_names(),
                false, // agents are .md files
            )?;
        }

        if cli.supports.contains(&"commands".to_string()) {
            create_symlinks(
                &cli_project_dir.join("commands"),
                &config.paths.commands_dir,
                &selections.command_names(),
                false,
            )?;
        }

        if cli.supports.contains(&"rules".to_string()) {
            for lang in &selections.rules {
                let rule_name = match lang.as_str() {
                    "go" => "golang",
                    other => other,
                };
                let source = config.paths.rules_dir.join(rule_name);
                if source.exists() {
                    let target = cli_project_dir.join("rules").join(rule_name);
                    std::fs::create_dir_all(target.parent().unwrap())?;
                    symlink_dir(&source, &target)?;
                }
            }
            // Always include common rules
            let common_source = config.paths.rules_dir.join("common");
            if common_source.exists() {
                let common_target = cli_project_dir.join("rules").join("common");
                std::fs::create_dir_all(common_target.parent().unwrap())?;
                symlink_dir(&common_source, &common_target)?;
            }
        }

        if cli.supports.contains(&"mcp".to_string()) || cli.supports.contains(&"plugins".to_string()) {
            generate_settings_local(
                &cli_project_dir,
                &config.base.mcp,
                &selections.mcp,
                &selections.plugins,
            )?;
        }
    }

    Ok(())
}

pub fn reset(config: &AppConfig, project_dir: &Path) -> Result<()> {
    for cli in &config.cli_registry {
        let cli_dir = project_dir.join(&cli.project_dir);

        for subdir in ["skills", "agents", "commands", "rules"] {
            let dir = cli_dir.join(subdir);
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
                if dir.read_dir().map(|mut d| d.next().is_none()).unwrap_or(true) {
                    let _ = std::fs::remove_dir(&dir);
                }
            }
        }

        let settings_local = cli_dir.join("settings.local.json");
        if settings_local.exists() {
            std::fs::remove_file(&settings_local)?;
        }
    }

    Ok(())
}

pub fn status(config: &AppConfig, project_dir: &Path) -> Result<ProjectStatus> {
    let claude_dir = project_dir.join(".claude");

    let skills = list_symlinks(&claude_dir.join("skills"));
    let agents = list_symlinks(&claude_dir.join("agents"));
    let commands = list_symlinks(&claude_dir.join("commands"));
    let rules = list_symlinks(&claude_dir.join("rules"));

    let (mcp, plugins) = read_settings_local(&claude_dir);

    let detected_clis: Vec<String> = config
        .detected_clis()
        .iter()
        .map(|c| c.name.clone())
        .collect();

    Ok(ProjectStatus {
        skills,
        agents,
        commands,
        rules,
        mcp,
        plugins,
        detected_clis,
    })
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
            std::os::unix::fs::symlink(&source, &target)
                .with_context(|| format!("Failed to symlink {} -> {}", source.display(), target.display()))?;

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

fn generate_settings_local(
    cli_dir: &Path,
    _base_mcp: &[String],
    extra_mcp: &[String],
    plugins: &[String],
) -> Result<()> {
    std::fs::create_dir_all(cli_dir)?;

    let mut settings = serde_json::Map::new();

    // MCP: only add extra servers beyond base
    if !extra_mcp.is_empty() {
        // Note: we don't need to disable base MCP (they're always on)
        // Just document what's active for this project
    }

    // Plugins: enable only selected ones
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

    if !settings.is_empty() {
        let json = serde_json::to_string_pretty(&settings)?;
        std::fs::write(cli_dir.join("settings.local.json"), json)?;
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

fn read_settings_local(cli_dir: &Path) -> (Vec<String>, Vec<String>) {
    let path = cli_dir.join("settings.local.json");
    if !path.exists() {
        return (Vec::new(), Vec::new());
    }

    let content = std::fs::read_to_string(&path).unwrap_or_default();
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

impl ApplyPreview {
    pub fn print(&self) {
        println!("Will create:");
        for action in &self.actions {
            println!(
                "  {}/{:<12} {} {}",
                action.cli_name, action.resource_type, action.count,
                if action.resource_type == "mcp" || action.resource_type == "plugins" {
                    "entries in settings.local.json"
                } else {
                    "symlinks"
                }
            );
        }
    }
}

impl ProjectStatus {
    pub fn print(&self) {
        println!("Skills:   {}", self.skills.len());
        println!("Agents:   {}", self.agents.len());
        println!("Commands: {}", self.commands.len());
        println!("Rules:    {}", self.rules.len());
        println!("MCP:      {}", self.mcp.len());
        println!("Plugins:  {}", self.plugins.len());
        println!("CLIs:     {}", self.detected_clis.join(", "));

        if !self.skills.is_empty() {
            println!("\nActive skills: {}", self.skills.join(", "));
        }
        if !self.agents.is_empty() {
            println!("Active agents: {}", self.agents.join(", "));
        }
    }
}
