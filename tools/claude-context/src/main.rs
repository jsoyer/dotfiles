mod ai;
mod cli;
mod config;
mod cost;
mod doctor;
mod hooks;
mod indexer;
mod matcher;

mod plugins;
mod profile;
mod scanner;
mod scope;
mod symlinker;
mod trim;
mod tui;

use anyhow::Result;
use clap::Parser;

use cli::{Cli, Command, ConfigAction, PluginAction};
use config::AppConfig;
use indexer::Index;
use profile::ProfileManager;
use scanner::Scanner;
use scope::ResolvedScope;

fn main() -> Result<()> {
    let cli = Cli::parse();

    let config = AppConfig::load()?;
    let cwd = std::env::current_dir()?;
    let resolved = scope::resolve(&cwd, cli.scope)?;

    match cli.command.unwrap_or(Command::Tui { smart: false }) {
        Command::Tui { smart } => run_tui(&config, &resolved, smart),
        Command::Scan => run_scan(),
        Command::Apply {
            profile,
            auto: _,
            smart,
            yes,
        } => run_apply(&config, &resolved, profile, smart, yes, cli.scope),
        Command::Status => run_status(&config, &resolved),
        Command::Diff => run_diff(&config, &resolved),
        Command::Cost => run_cost(&config, &resolved),
        Command::Save { name } => run_save(&config, &resolved, &name),
        Command::Profiles => run_profiles(&config),
        Command::Reset { yes } => run_reset(&config, &resolved, yes),
        Command::Init => run_init(&config, &resolved),
        Command::Trim { file, auto, yes } => run_trim(file, auto, yes),
        Command::Index => run_index(&config),
        Command::Doctor => run_doctor(&config),
        Command::Export { profile } => run_export(&config, &profile),
        Command::Import { file } => run_import(&config, &file),
        Command::Config { action } => run_config(&config, action),
        Command::Hook { shell } => run_hook(&shell),
        Command::Plugin { action } => run_plugin(&config, &resolved, action),
        Command::Update => run_update(&config),
        Command::Completions { shell } => run_completions(shell),
        Command::Man => run_man(),
        Command::Watch { interval } => run_watch(&config, &resolved, interval),
    }
}

fn run_tui(config: &AppConfig, resolved: &ResolvedScope, smart: bool) -> Result<()> {
    let index = Index::build(config)?;
    let cwd = std::env::current_dir()?;
    let fingerprint = Scanner::scan(&cwd)?;
    let recommendations = matcher::recommend(&fingerprint, &index, smart, &config.ai)?;

    // Load remote resources for the TUI (skills, agents, commands, plugins)
    let pm = plugins::PluginManager::new(&config.paths.config_dir)?;
    let remote_resources = pm.all_available().unwrap_or_default();

    tui::run(config, resolved, &index, &fingerprint, &recommendations, &remote_resources)
}

fn run_scan() -> Result<()> {
    let fingerprint = Scanner::scan(&std::env::current_dir()?)?;
    fingerprint.print();
    Ok(())
}

fn run_apply(
    config: &AppConfig,
    resolved: &ResolvedScope,
    profile: Option<String>,
    smart: bool,
    yes: bool,
    explicit_scope: Option<scope::Scope>,
) -> Result<()> {
    let index = Index::build(config)?;

    let (selections, resolved) = if let Some(name) = profile {
        let pm = ProfileManager::new(config)?;
        let (recs, profile_scope) = pm.load_with_scope(&name)?;
        // Use profile's scope if user didn't explicitly override
        let resolved = if explicit_scope.is_none() {
            if let Some(scope_str) = profile_scope {
                let parsed = match scope_str.as_str() {
                    "global" => Some(scope::Scope::Global),
                    "project" => Some(scope::Scope::Project),
                    "user-project" => Some(scope::Scope::UserProject),
                    _ => None,
                };
                if let Some(s) = parsed {
                    let cwd = std::env::current_dir()?;
                    scope::resolve(&cwd, Some(s))?
                } else {
                    resolved.clone()
                }
            } else {
                resolved.clone()
            }
        } else {
            resolved.clone()
        };
        (recs, resolved)
    } else {
        let cwd = std::env::current_dir()?;
        let fingerprint = Scanner::scan(&cwd)?;
        let recs = matcher::recommend(&fingerprint, &index, smart, &config.ai)?;
        (recs, resolved.clone())
    };

    if !yes {
        let preview = symlinker::preview(config, &resolved, &selections)?;
        preview.print();

        if !dialoguer::Confirm::new()
            .with_prompt("Apply?")
            .default(true)
            .interact()?
        {
            println!("Cancelled.");
            return Ok(());
        }
    }

    symlinker::apply(config, &resolved, &selections)?;
    println!("Applied successfully.");
    Ok(())
}

fn run_status(config: &AppConfig, resolved: &ResolvedScope) -> Result<()> {
    let status = symlinker::status(config, resolved)?;
    status.print();
    Ok(())
}

fn run_diff(config: &AppConfig, resolved: &ResolvedScope) -> Result<()> {
    let index = Index::build(config)?;
    let cwd = std::env::current_dir()?;
    let fingerprint = Scanner::scan(&cwd)?;
    let recommended = matcher::recommend(&fingerprint, &index, false, &config.ai)?;
    let current = symlinker::status(config, resolved)?;

    cost::print_diff(&current, &recommended);
    Ok(())
}

fn run_cost(config: &AppConfig, resolved: &ResolvedScope) -> Result<()> {
    let status = symlinker::status(config, resolved)?;
    cost::print(&status);
    Ok(())
}

fn run_save(config: &AppConfig, resolved: &ResolvedScope, name: &str) -> Result<()> {
    let status = symlinker::status(config, resolved)?;
    let pm = ProfileManager::new(config)?;
    pm.save(name, &status)?;
    println!("Profile '{}' saved.", name);
    Ok(())
}

fn run_profiles(config: &AppConfig) -> Result<()> {
    let pm = ProfileManager::new(config)?;
    pm.list()?;
    Ok(())
}

fn run_reset(config: &AppConfig, resolved: &ResolvedScope, yes: bool) -> Result<()> {
    if !yes {
        if !dialoguer::Confirm::new()
            .with_prompt(format!(
                "Remove per-{} config?",
                resolved.scope
            ))
            .default(false)
            .interact()?
        {
            println!("Cancelled.");
            return Ok(());
        }
    }

    symlinker::reset(config, resolved)?;
    println!("Config reset (scope: {}).", resolved.scope);
    Ok(())
}

fn run_init(config: &AppConfig, resolved: &ResolvedScope) -> Result<()> {
    let cwd = std::env::current_dir()?;
    let fingerprint = Scanner::scan(&cwd)?;

    if fingerprint.is_empty() {
        let choices = &[
            "frontend",
            "backend-ts",
            "fullstack",
            "rust",
            "python",
            "golang",
            "devops",
            "mobile",
            "ai-ml",
            "security",
            "data-engineering",
            "cli-tools",
            "monorepo",
            "saas-platform",
            "dotfiles",
            "custom",
        ];
        let selection = dialoguer::Select::new()
            .with_prompt("What kind of project?")
            .items(choices)
            .default(0)
            .interact()?;

        let profile_name = choices[selection];
        if profile_name == "custom" {
            println!("Run `cctx` to configure manually.");
            return Ok(());
        }

        let pm = ProfileManager::new(config)?;
        if let Ok(selections) = pm.load(profile_name) {
            symlinker::apply(config, resolved, &selections)?;
            println!("Applied '{}' profile (scope: {}).", profile_name, resolved.scope);
        } else {
            println!(
                "No '{}' profile found. Run `cctx` to configure manually.",
                profile_name
            );
        }
    } else {
        fingerprint.print();
        println!("\nRun `cctx apply --auto` to apply recommendations.");
    }

    Ok(())
}

fn run_trim(file: Option<String>, auto: bool, yes: bool) -> Result<()> {
    let path = file.unwrap_or_else(|| "CLAUDE.md".to_string());

    if auto {
        if !yes {
            let report = trim::analyze(&path)?;
            report.print();
            if !dialoguer::Confirm::new()
                .with_prompt("Apply trim with backup?")
                .default(false)
                .interact()?
            {
                println!("Cancelled.");
                return Ok(());
            }
        }
        trim::auto_trim(&path)?;
    } else {
        let report = trim::analyze(&path)?;
        report.print();
    }

    Ok(())
}

fn run_index(config: &AppConfig) -> Result<()> {
    let index = Index::build(config)?;
    println!(
        "Indexed {} skills, {} agents, {} commands.",
        index.skills.len(),
        index.agents.len(),
        index.commands.len()
    );
    Ok(())
}

fn run_doctor(config: &AppConfig) -> Result<()> {
    let report = doctor::run_doctor(config)?;
    report.print();
    Ok(())
}

fn run_export(config: &AppConfig, profile: &str) -> Result<()> {
    let pm = ProfileManager::new(config)?;
    let yaml = pm.export(profile)?;
    print!("{}", yaml);
    Ok(())
}

fn run_import(config: &AppConfig, file: &str) -> Result<()> {
    let pm = ProfileManager::new(config)?;
    pm.import(file)?;
    println!("Profile imported from {}.", file);
    Ok(())
}

// ── P4: Config command ──────────────────────────────────────────────────

fn run_config(config: &AppConfig, action: ConfigAction) -> Result<()> {
    let cwd = std::env::current_dir()?;
    let project_config_path = cwd.join(".cctx.yaml");

    match action {
        ConfigAction::Get { key } => {
            // Check project-level first, then global
            if let Some(val) = config_get_from_file(&project_config_path, &key) {
                println!("{} = {} [project]", key, val);
            } else if let Some(val) = config_get_from_app(config, &key) {
                println!("{} = {} [global]", key, val);
            } else {
                println!("{}: not found", key);
            }
        }
        ConfigAction::Set { key, value } => {
            config_set_in_file(&project_config_path, &key, &value)?;
            println!("Set {} = {} [project]", key, value);
        }
        ConfigAction::List => {
            println!("Configuration:");
            // Global config
            for (k, v) in config_list_global(config) {
                let scope = if config_get_from_file(&project_config_path, &k).is_some() {
                    "project"
                } else {
                    "global"
                };
                println!("  {:<30} = {:<20} [{}]", k, v, scope);
            }
        }
    }
    Ok(())
}

fn config_get_from_file(path: &std::path::Path, key: &str) -> Option<String> {
    if !path.exists() {
        return None;
    }
    let content = std::fs::read_to_string(path).ok()?;
    let yaml: serde_yaml::Value = serde_yaml::from_str(&content).ok()?;
    let parts: Vec<&str> = key.split('.').collect();
    let mut current = &yaml;
    for part in &parts {
        current = current.get(part)?;
    }
    Some(format!("{}", serde_yaml::to_string(current).ok()?.trim()))
}

fn config_get_from_app(config: &AppConfig, key: &str) -> Option<String> {
    match key {
        "ai.enabled" => Some(config.ai.enabled.to_string()),
        "ai.provider" => Some(config.ai.provider.clone()),
        "ai.model" => Some(config.ai.model.clone()),
        "ai.max_tokens" => Some(config.ai.max_tokens.to_string()),
        "ai.cache_ttl" => Some(config.ai.cache_ttl.clone()),
        "paths.skills_dir" => Some(config.paths.skills_dir.display().to_string()),
        "paths.agents_dir" => Some(config.paths.agents_dir.display().to_string()),
        "paths.commands_dir" => Some(config.paths.commands_dir.display().to_string()),
        "paths.rules_dir" => Some(config.paths.rules_dir.display().to_string()),
        "paths.config_dir" => Some(config.paths.config_dir.display().to_string()),
        "paths.profiles_dir" => Some(config.paths.profiles_dir.display().to_string()),
        _ => None,
    }
}

fn config_set_in_file(path: &std::path::Path, key: &str, value: &str) -> Result<()> {
    let mut yaml: serde_yaml::Value = if path.exists() {
        let content = std::fs::read_to_string(path)?;
        serde_yaml::from_str(&content)?
    } else {
        serde_yaml::Value::Mapping(serde_yaml::Mapping::new())
    };

    let parts: Vec<&str> = key.split('.').collect();
    let mut current = &mut yaml;
    for (i, part) in parts.iter().enumerate() {
        if i == parts.len() - 1 {
            // Parse value: try bool, then number, then string
            let parsed: serde_yaml::Value = if value == "true" {
                serde_yaml::Value::Bool(true)
            } else if value == "false" {
                serde_yaml::Value::Bool(false)
            } else if let Ok(n) = value.parse::<i64>() {
                serde_yaml::Value::Number(n.into())
            } else {
                serde_yaml::Value::String(value.to_string())
            };
            current[serde_yaml::Value::String(part.to_string())] = parsed;
        } else {
            let key = serde_yaml::Value::String(part.to_string());
            if !current.get(&key).is_some() {
                current[key.clone()] = serde_yaml::Value::Mapping(serde_yaml::Mapping::new());
            }
            current = current.get_mut(&key).unwrap();
        }
    }

    let output = serde_yaml::to_string(&yaml)?;
    std::fs::write(path, output)?;
    Ok(())
}

fn config_list_global(config: &AppConfig) -> Vec<(String, String)> {
    vec![
        ("ai.enabled".into(), config.ai.enabled.to_string()),
        ("ai.provider".into(), config.ai.provider.clone()),
        ("ai.model".into(), config.ai.model.clone()),
        ("ai.max_tokens".into(), config.ai.max_tokens.to_string()),
        ("ai.cache_ttl".into(), config.ai.cache_ttl.clone()),
        ("paths.skills_dir".into(), config.paths.skills_dir.display().to_string()),
        ("paths.agents_dir".into(), config.paths.agents_dir.display().to_string()),
        ("paths.commands_dir".into(), config.paths.commands_dir.display().to_string()),
        ("paths.rules_dir".into(), config.paths.rules_dir.display().to_string()),
    ]
}

// ── P5: Shell hooks ─────────────────────────────────────────────────────

fn run_hook(shell: &str) -> Result<()> {
    let code = hooks::generate(shell)?;
    print!("{}", code);
    Ok(())
}

// ── P7: Plugin management ───────────────────────────────────────────────

fn run_plugin(config: &AppConfig, resolved: &ResolvedScope, action: PluginAction) -> Result<()> {
    match action {
        PluginAction::List => {
            let pm = plugins::PluginManager::new(&config.paths.config_dir)?;
            let all = pm.all_available()?;
            if all.is_empty() {
                println!("No resources cached. Run `cctx plugin refresh` first.");
            } else {
                println!("Available resources ({}):", all.len());
                for entry in &all {
                    println!(
                        "  [{:<7}] {:<30} {} ({})",
                        entry.resource_type, entry.install_id, entry.description, entry.source_name
                    );
                }
            }
        }
        PluginAction::Search { query } => {
            let pm = plugins::PluginManager::new(&config.paths.config_dir)?;
            let results = pm.search(&query)?;
            if results.is_empty() {
                println!("No resources matching '{}'.", query);
            } else {
                println!("Resources matching '{}' ({}):", query, results.len());
                for entry in &results {
                    println!(
                        "  [{:<7}] {:<30} {} ({})",
                        entry.resource_type, entry.install_id, entry.description, entry.source_name
                    );
                }
            }
        }
        PluginAction::Refresh => {
            let pm = plugins::PluginManager::new(&config.paths.config_dir)?;
            pm.refresh()?;
            let all = pm.all_available()?;
            let mut counts = std::collections::HashMap::new();
            for e in &all {
                *counts.entry(e.resource_type).or_insert(0usize) += 1;
            }
            let summary: Vec<String> = counts
                .iter()
                .map(|(t, c)| format!("{} {}s", c, t))
                .collect();
            println!("Refreshed. {} resources ({})", all.len(), summary.join(", "));
        }
        PluginAction::Install { name } => {
            let pm = plugins::PluginManager::new(&config.paths.config_dir)?;
            let all = pm.all_available()?;
            let resource = all
                .iter()
                .find(|e| e.install_id == name || e.name == name);
            match resource {
                Some(r) => {
                    pm.install(
                        r,
                        &config.paths.skills_dir,
                        &config.paths.agents_dir,
                        &config.paths.commands_dir,
                    )?;
                }
                None => println!("Resource '{}' not found. Run `cctx plugin refresh` first.", name),
            }
        }
        PluginAction::Uninstall { name } => {
            let pm = plugins::PluginManager::new(&config.paths.config_dir)?;
            let all = pm.all_available()?;
            let resource = all.iter().find(|e| e.install_id == name || e.name == name);
            match resource {
                Some(r) => {
                    pm.uninstall(
                        &name,
                        r.resource_type,
                        &config.paths.skills_dir,
                        &config.paths.agents_dir,
                        &config.paths.commands_dir,
                    )?;
                }
                None => {
                    // Try to detect type from filesystem
                    let skill_dir = config.paths.skills_dir.join(&name);
                    let agent_file = config.paths.agents_dir.join(format!("{}.md", &name));
                    let cmd_file = config.paths.commands_dir.join(format!("{}.md", &name));
                    if skill_dir.exists() {
                        pm.uninstall(&name, plugins::ResourceType::Skill, &config.paths.skills_dir, &config.paths.agents_dir, &config.paths.commands_dir)?;
                    } else if agent_file.exists() {
                        pm.uninstall(&name, plugins::ResourceType::Agent, &config.paths.skills_dir, &config.paths.agents_dir, &config.paths.commands_dir)?;
                    } else if cmd_file.exists() {
                        pm.uninstall(&name, plugins::ResourceType::Command, &config.paths.skills_dir, &config.paths.agents_dir, &config.paths.commands_dir)?;
                    } else {
                        println!("Resource '{}' not found locally.", name);
                    }
                }
            }
        }
        PluginAction::Add { name, url, resources } => {
            let resource_types: Vec<plugins::ResourceType> = resources
                .split(',')
                .filter_map(|s| match s.trim() {
                    "skill" => Some(plugins::ResourceType::Skill),
                    "agent" => Some(plugins::ResourceType::Agent),
                    "command" => Some(plugins::ResourceType::Command),
                    "plugin" => Some(plugins::ResourceType::Plugin),
                    _ => None,
                })
                .collect();
            if resource_types.is_empty() {
                println!("Invalid resource types. Use: skill,agent,command,plugin");
            } else {
                plugins::add_source(&config.paths.config_dir, &name, &url, &resource_types)?;
            }
        }
        PluginAction::DisableAll => {
            let scope_s = scope::scope_str(resolved.scope);
            let mut count = 0;
            for cli in &config.cli_registry {
                if !cli.supports.contains(&"plugins".to_string()) {
                    continue;
                }
                if !cli.scopes.contains(&scope_s.to_string()) {
                    continue;
                }
                for filename in ["settings.json", "settings.local.json"] {
                    let path = cli.config_dir.join(filename);
                    if path.exists() {
                        symlinker::set_all_plugins_enabled(&path, false)?;
                        count += 1;
                    }
                }
            }
            println!("Disabled all plugins in {} settings files.", count);
        }
        PluginAction::EnableAll => {
            let scope_s = scope::scope_str(resolved.scope);
            let mut count = 0;
            for cli in &config.cli_registry {
                if !cli.supports.contains(&"plugins".to_string()) {
                    continue;
                }
                if !cli.scopes.contains(&scope_s.to_string()) {
                    continue;
                }
                for filename in ["settings.json", "settings.local.json"] {
                    let path = cli.config_dir.join(filename);
                    if path.exists() {
                        symlinker::set_all_plugins_enabled(&path, true)?;
                        count += 1;
                    }
                }
            }
            println!("Enabled all plugins in {} settings files.", count);
        }
    }
    Ok(())
}

// ── Update command ──────────────────────────────────────────────────────

fn run_update(config: &AppConfig) -> Result<()> {
    let pm = plugins::PluginManager::new(&config.paths.config_dir)?;

    println!("Refreshing resource cache...");
    pm.refresh()?;

    println!("Updating installed resources...");
    let count = pm.update_installed(
        &config.paths.skills_dir,
        &config.paths.agents_dir,
        &config.paths.commands_dir,
    )?;

    if count > 0 {
        println!("Updated {} resource(s).", count);
    } else {
        println!("No remote resources installed to update.");
    }
    Ok(())
}

// ── Completions command ─────────────────────────────────────────────────

fn run_completions(shell: clap_complete::Shell) -> Result<()> {
    use clap::CommandFactory;
    let mut cmd = cli::Cli::command();
    clap_complete::generate(shell, &mut cmd, "cctx", &mut std::io::stdout());
    Ok(())
}

// ── Man page command ────────────────────────────────────────────────────

fn run_man() -> Result<()> {
    use clap::CommandFactory;
    let cmd = cli::Cli::command();
    let man = clap_mangen::Man::new(cmd);
    man.render(&mut std::io::stdout())?;
    Ok(())
}

// ── Watch command ────────────────────────────────────────────────────────

fn run_watch(config: &AppConfig, resolved: &ResolvedScope, interval: u64) -> Result<()> {
    use notify::{Config as NotifyConfig, RecommendedWatcher, RecursiveMode, Watcher};
    use std::sync::mpsc;
    use std::time::Duration;

    let cwd = std::env::current_dir()?;
    println!("Watching {} for changes (interval: {}s)...", cwd.display(), interval);
    println!("Press Ctrl+C to stop.\n");

    let (tx, rx) = mpsc::channel();

    let mut watcher = RecommendedWatcher::new(
        move |res: notify::Result<notify::Event>| {
            if let Ok(event) = res {
                if event.kind.is_modify() || event.kind.is_create() || event.kind.is_remove() {
                    let _ = tx.send(());
                }
            }
        },
        NotifyConfig::default().with_poll_interval(Duration::from_secs(interval)),
    )?;

    // Watch common project files
    for path in [
        "Cargo.toml",
        "package.json",
        "go.mod",
        "pyproject.toml",
        "CLAUDE.md",
        ".claude",
    ] {
        let full = cwd.join(path);
        if full.exists() {
            let mode = if full.is_dir() {
                RecursiveMode::Recursive
            } else {
                RecursiveMode::NonRecursive
            };
            let _ = watcher.watch(&full, mode);
        }
    }

    // Also watch the cwd for new files (non-recursive to avoid noise)
    watcher.watch(&cwd, RecursiveMode::NonRecursive)?;

    // Initial apply
    let index = Index::build(config)?;
    let fingerprint = Scanner::scan(&cwd)?;
    let recommendations = matcher::recommend(&fingerprint, &index, false, &config.ai)?;
    symlinker::apply(config, resolved, &recommendations)?;
    println!("[watch] Initial apply done.");

    // Debounce: wait for changes, then re-apply
    loop {
        // Block until a change event
        rx.recv()?;

        // Drain any queued events (debounce)
        std::thread::sleep(Duration::from_millis(500));
        while rx.try_recv().is_ok() {}

        // Re-scan and re-apply
        match Scanner::scan(&cwd) {
            Ok(fingerprint) => {
                match Index::build(config) {
                    Ok(index) => {
                        match matcher::recommend(&fingerprint, &index, false, &config.ai) {
                            Ok(recommendations) => {
                                if let Err(e) = symlinker::apply(config, resolved, &recommendations) {
                                    eprintln!("[watch] Apply error: {}", e);
                                } else {
                                    println!("[watch] Re-applied after change.");
                                }
                            }
                            Err(e) => eprintln!("[watch] Recommend error: {}", e),
                        }
                    }
                    Err(e) => eprintln!("[watch] Index error: {}", e),
                }
            }
            Err(e) => eprintln!("[watch] Scan error: {}", e),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::path::PathBuf;

    #[test]
    fn scanner_detects_rust_project() {
        let dir = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
        let fingerprint = Scanner::scan(&dir).unwrap();
        assert!(fingerprint.languages.iter().any(|l| l.name == "rust"));
    }

    #[test]
    fn scanner_empty_dir_returns_empty_fingerprint() {
        let dir = std::env::temp_dir().join("cctx-test-empty");
        let _ = std::fs::create_dir_all(&dir);
        let fingerprint = Scanner::scan(&dir).unwrap();
        assert!(fingerprint.languages.is_empty());
        let _ = std::fs::remove_dir_all(&dir);
    }

    #[test]
    fn config_loads_defaults() {
        let config = AppConfig::load().unwrap();
        assert!(!config.base.skills.is_empty());
        assert!(!config.base.agents.is_empty());
        assert!(!config.base.mcp.is_empty());
        assert!(!config.cli_registry.is_empty());
        assert!(!config.ai.enabled);
    }

    #[test]
    fn config_has_claude_cli() {
        let config = AppConfig::load().unwrap();
        let names: Vec<&str> = config.cli_registry.iter().map(|c| c.name.as_str()).collect();
        assert!(names.contains(&"claude"));
    }

    #[test]
    fn cli_entries_have_scopes_field() {
        let config = AppConfig::load().unwrap();
        for cli in &config.cli_registry {
            assert!(
                !cli.scopes.is_empty(),
                "CLI '{}' has empty scopes",
                cli.name
            );
            assert!(
                cli.scopes.contains(&"global".to_string()),
                "CLI '{}' must support at least global scope",
                cli.name
            );
        }
    }

    #[test]
    fn cost_estimation_nonzero_for_nonempty_status() {
        let status = symlinker::ProjectStatus {
            skills: vec!["test-skill".to_string()],
            agents: vec!["test-agent".to_string()],
            commands: vec![],
            rules: vec!["rust".to_string()],
            mcp: vec!["context7".to_string()],
            plugins: vec![],
            detected_clis: vec!["claude".to_string()],
            scope: scope::Scope::Project,
        };
        let estimate = cost::estimate(&status);
        assert!(estimate.project_total > 0);
        assert!(estimate.global_total > estimate.project_total);
    }

    #[test]
    fn cost_estimation_zero_for_empty_status() {
        let status = symlinker::ProjectStatus {
            skills: vec![],
            agents: vec![],
            commands: vec![],
            rules: vec![],
            mcp: vec![],
            plugins: vec![],
            detected_clis: vec![],
            scope: scope::Scope::Project,
        };
        let estimate = cost::estimate(&status);
        assert_eq!(estimate.project_total, 0);
    }

    #[test]
    fn matcher_scores_relevant_higher() {
        let config = AppConfig::load().unwrap();
        if let Ok(index) = Index::build(&config) {
            let dir = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
            let fingerprint = Scanner::scan(&dir).unwrap();
            let recs = matcher::recommend(&fingerprint, &index, false, &config.ai).unwrap();

            if !recs.skills.is_empty() {
                assert!(recs.skills.len() > 0);
            }
        }
    }

    #[test]
    fn trim_analyze_nonexistent_file_returns_error() {
        let result = trim::analyze("/nonexistent/file.md");
        assert!(result.is_err());
    }

    #[test]
    fn fingerprint_all_tags_includes_languages() {
        let dir = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
        let fingerprint = Scanner::scan(&dir).unwrap();
        let tags = fingerprint.all_tags();
        assert!(tags.contains(&"rust".to_string()));
    }
}
